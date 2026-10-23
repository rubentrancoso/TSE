#!/usr/bin/env python3
"""Comparacao BU x secao em UMA busca indexada por zona.

Evita o SQL antigo que criava varias tabelas temporarias e JOINs por zona.
NAO altera votos originais nem muda a semantica do relatorio de divergencias.
"""
from __future__ import annotations

import csv
import os
import sqlite3
import time
from pathlib import Path

HEADER = ["UF", "municipio", "zona", "secao", "turno", "cargo",
          "votavel", "votos_BU", "votos_secao", "diferenca", "situacao"]


def numeric_sqlite(value):
    """CAST SQLite AS INTEGER para codigos normalmente numericos."""
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return 0


def canonical_candidate(value):
    raw = str(value).strip()
    return str(int(raw)) if raw.isdecimal() else raw.upper()


def select_indexed(task):
    """Index existente: idx_votes_lookup(uf, municipio, zona, ...)."""
    args = []
    filters = []
    for field, candidates in (
        ("uf", task["ufs"]),
        ("municipio", task["municipios"]),
        ("zona", task["zonas"]),
        ("turno", task["turnos"]),
    ):
        originals = sorted(candidates)
        filters.append(field + " IN (" + ",".join("?" for _ in originals) + ")")
        args.extend(originals)
    sql = (
        "SELECT source_kind,uf,municipio,zona,secao,turno,cargo,votavel,votos "
        "FROM votes INDEXED BY idx_votes_lookup WHERE "
        + " AND ".join(filters)
        + " AND source_kind IN ('bu','secao','secao_nacional') "
        + "AND votos IS NOT NULL AND TRIM(votavel) != '' "
        + "AND TRIM(cargo) != '' AND TRIM(secao) != ''"
    )
    return sql, args


def compare_task_fast(db, task, path):
    """Uma busca SQLite indexada + agrupamento em memoria por chave da zona."""
    sql, args = select_indexed(task)
    # Em cada chave, acumular fontes em campos separados. Nunca somar
    # fonte estadual e nacional: a estadual tem prioridade por chave.
    totals = {}
    start = time.monotonic()
    counted = 0
    next_log = start + 20
    print(f"[WORKER BUSCA] pid={os.getpid()} zona={'/'.join(task['key'])}; "
          "executando SELECT indexado.", flush=True)
    for kind, uf, mu, zo, sec, turn, cargo, candidate, votes in db.execute(sql, args):
        counted += 1
        moment = time.monotonic()
        if moment >= next_log:
            print(f"[WORKER LENDO] pid={os.getpid()} zona={'/'.join(task['key'])}; "
                  f"{counted:,} linhas lidas; {moment-start:.1f}s.",
                  flush=True)
            next_log = moment + 20
        ca = str(cargo).strip().lower()
        if kind == "secao_nacional" and ca != "1":
            continue
        key = (
            str(uf).strip().upper(), numeric_sqlite(mu),
            numeric_sqlite(zo), numeric_sqlite(sec),
            numeric_sqlite(turn), ca, canonical_candidate(candidate)
        )
        by_source = totals.setdefault(key, {})
        by_source[kind] = by_source.get(kind, 0) + int(votes)

    print(f"[WORKER LEITURA OK] pid={os.getpid()} zona={'/'.join(task['key'])}; "
          f"{counted:,} linhas em {time.monotonic()-start:.1f}s; "
          f"{len(totals):,} chaves. Gravando divergencias.",
          flush=True)
    checked = different = missing_bu = missing_section = 0
    with Path(path).open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow(HEADER)
        for key, data in sorted(totals.items()):
            checked += 1
            b = data.get("bu")
            # Diferenciar valor zero de ausencia por meio de 'in'.
            s = data.get("secao") if "secao" in data else data.get("secao_nacional")
            if b is None:
                status = "SEM_BU"
                missing_bu += 1
            elif s is None:
                status = "SEM_SECAO"
                missing_section += 1
            elif b != s:
                status = "DIFERENTE"
            else:
                continue
            different += 1
            writer.writerow((*key, b if b is not None else "",
                             s if s is not None else "",
                             b-s if b is not None and s is not None else "",
                             status))
        file.flush()
        os.fsync(file.fileno())
    print(f"[WORKER OK] pid={os.getpid()} zona={'/'.join(task['key'])}; "
          f"{checked:,} chaves, {different:,} divergencias; "
          f"{time.monotonic()-start:.1f}s.", flush=True)
    return checked, different, missing_bu, missing_section


def process_task(database_path, task, part_path):
    """Worker independente, seguro para multiprocessing no Windows."""
    db_path = Path(database_path)
    uri = db_path.resolve().as_uri() + "?mode=ro"
    print(f"[WORKER INICIADO] pid={os.getpid()} "
          f"zona={'/'.join(task['key'])}; abrindo SQLite leitura.", flush=True)
    with sqlite3.connect(uri, uri=True, timeout=30) as db:
        db.execute("PRAGMA query_only=ON")
        print(f"[WORKER SQLITE OK] pid={os.getpid()} "
              f"zona={'/'.join(task['key'])}.", flush=True)
        vm_last = [time.monotonic()]
        def sqlite_vm_activity():
            moment = time.monotonic()
            if moment - vm_last[0] >= 20:
                vm_last[0] = moment
                print(f"[WORKER SQLITE ATIVO] pid={os.getpid()} "
                      f"zona={'/'.join(task['key'])}; "
                      "SQLite executa instrucoes, ainda sem concluir a busca.",
                      flush=True)
            return 0
        db.set_progress_handler(sqlite_vm_activity, 100000)
        return compare_task_fast(db, task, part_path)
