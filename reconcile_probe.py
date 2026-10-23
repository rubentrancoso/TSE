#!/usr/bin/env python3
"""Teste curto e somente leitura da consulta de reconciliacao no SQLite real.

Usa plano de zonas JA salvo em analysis/reconciliacao_checkpoints/plans/.
Nunca altera votos, checkpoints ou relatorio final de reconciliacao.
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sqlite3
import tempfile
import time
from pathlib import Path

from reconcile_fast import compare_task_fast, select_indexed


def pick_samples(records):
    """Uma zona pequena e uma mediana; nao repetimos a mesma zona."""
    ordered = sorted((record for record in records if record["rows"] > 0),
                     key=lambda x: (x["rows"], tuple(x["key"])))
    if not ordered:
        raise ValueError("Plano sem zonas com registros")
    picked = [ordered[min(len(ordered)-1, max(0, len(ordered)//10))]]
    typical = ordered[len(ordered)//2]
    if tuple(typical["key"]) != tuple(picked[0]["key"]):
        picked.append(typical)
    return picked


def run_probe(root: Path, budget: float = 120):
    folder = root / "analysis" / "reconciliacao_checkpoints" / "plans"
    files = sorted(folder.glob("*.json.gz"), key=lambda p: p.stat().st_mtime,
                   reverse=True) if folder.is_dir() else []
    if not files:
        print("ERRO: plano salvo nao encontrado. Diagnostico nao inicia "
              "nova leitura nacional.", flush=True)
        return 2
    with gzip.open(files[0], "rt", encoding="utf-8") as stream:
        plan = json.load(stream)
    db_path = root / "analysis" / "urna_2026.sqlite3"
    if not db_path.is_file():
        print(f"ERRO: SQLite nao encontrado: {db_path}", flush=True)
        return 2
    samples = pick_samples(plan["tasks"])
    print("PROVA REAL DE EXECUCAO - leitura do banco H: sem alterar dados", flush=True)
    print(f"Plano: {files[0].name} | zonas no plano: "
          f"{len(plan['tasks']):,} | prazo maximo de SQL "
          f"por zona: {budget:g}s.", flush=True)
    print("Nao execute outro reconciliador em paralelo a este teste.", flush=True)
    uri = db_path.resolve().as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True, timeout=10) as db:
        db.execute("PRAGMA query_only=ON")
        with tempfile.TemporaryDirectory(prefix="tse-reconcile-probe-") as tempdir:
            for index, item in enumerate(samples, 1):
                task = {
                    "key": tuple(item["key"]),
                    "ufs": set(item["ufs"]), "municipios": set(item["municipios"]),
                    "zonas": set(item["zonas"]), "turnos": set(item["turnos"]),
                    "rows": item["rows"]
                }
                label = "/".join(task["key"])
                sql, params = select_indexed(task)
                plan_rows = db.execute("EXPLAIN QUERY PLAN " + sql, params).fetchall()
                print(f"ZONA {index}/{len(samples)}: {label}; "
                      f"{task['rows']:,} linhas no planejamento.", flush=True)
                print("PLANO SQL: " + " | ".join(str(r[-1]) for r in plan_rows),
                      flush=True)
                began = time.monotonic()
                expires = began + budget
                last = [began]
                def cancel_when_over_budget():
                    instant = time.monotonic()
                    if instant - last[0] >= 10:
                        print(f"[SQLITE ATIVO] {label}: "
                              f"{instant-began:.1f}s de processamento.",
                              flush=True)
                        last[0] = instant
                    return 1 if instant >= expires else 0
                db.set_progress_handler(cancel_when_over_budget, 10000)
                try:
                    result = compare_task_fast(
                        db, task, Path(tempdir) / f"amostra-{index}.csv")
                except sqlite3.OperationalError as exc:
                    print(f"FALHOU: {label} apos "
                          f"{time.monotonic()-began:.1f}s: {exc}. "
                          "O SQL nao terminou no limite informado.", flush=True)
                    return 1
                finally:
                    db.set_progress_handler(None, 0)
                elapsed = time.monotonic()-began
                print(f"ZONA REAL CONCLUIDA: {label}; "
                      f"{result[0]:,} chaves comparadas; "
                      f"{result[1]:,} diferencas; "
                      f"{elapsed:.1f}s de parede.", flush=True)
    print("DIAGNOSTICO CONCLUIDO: as zonas de amostra foram realmente "
          "calculadas. Isto nao mede o prazo da reconciliacao nacional.",
          flush=True)
    return 0


def main():
    parser = argparse.ArgumentParser(description="Verificar rendimento real da busca SQLite.")
    parser.add_argument("--root", default=("H:/TSE/forensics/urnas"
                                          if os.name == "nt"
                                          else "data/forensics/urnas"))
    parser.add_argument("--budget", type=float, default=120,
                        help="Limite de trabalho SQLite por zona em segundos")
    options = parser.parse_args()
    if options.budget <= 0:
        parser.error("--budget deve ser maior que zero")
    return run_probe(Path(options.root), options.budget)


if __name__ == "__main__":
    raise SystemExit(main())
