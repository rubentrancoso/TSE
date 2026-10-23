#!/usr/bin/env python3
"""Reconciliação externa por varredura sequencial e partições retomáveis.

Lê votes apenas em ordem de rowid, cria arquivos compactos por hash da
localidade e compara cada partição em memória. Não modifica o SQLite de
origem. Checkpoints com offsets permitem interromper qualquer etapa.
"""
from __future__ import annotations

import csv
from contextlib import contextmanager
import hashlib
import io
import json
import os
import re
import shutil
import sqlite3
import time
import zlib
from datetime import datetime, timezone
from pathlib import Path

VERSION = "reconcile-stream-v1"
HEADER = ["UF", "municipio", "zona", "secao", "turno", "cargo",
          "votavel", "votos_BU", "votos_secao", "diferenca", "situacao"]
SOURCES = ("bu", "secao", "secao_nacional")
INT_PREFIX = re.compile(r"^\s*([+-]?\d+)")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def numeric(value):
    """Equivalente do CAST(... AS INTEGER) usado no reconciliador SQL."""
    found = INT_PREFIX.match(str(value or ""))
    return str(int(found.group(1))) if found else "0"


def votable(value):
    value = str(value).strip()
    if value and all("0" <= char <= "9" for char in value):
        return str(int(value))
    return value.upper()


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save_state(path, state):
    temporary = path.with_suffix(".json.tmp")
    with open(temporary, "w", encoding="utf-8") as file:
        json.dump(state, file, ensure_ascii=False, indent=2, sort_keys=True)
        file.flush()
        os.fsync(file.fileno())
    os.replace(temporary, path)


def identity(db, ufs, turn, buckets):
    resources = list(db.execute(
        """SELECT resource_key,sha256,rows,parser_version
           FROM imports WHERE resource_key LIKE 'bu:%'
           OR resource_key LIKE 'secao:%'
           OR resource_key LIKE 'secao_nacional:%'
           ORDER BY resource_key"""))
    partial = list(db.execute(
        "SELECT resource_key,sha256,updated_utc "
        "FROM import_progress ORDER BY resource_key"))
    data = {"engine": VERSION, "resources": resources, "partial": partial,
            "ufs": sorted(ufs), "turn": turn, "buckets": buckets}
    digest = hashlib.sha256(
        json.dumps(data, sort_keys=True, ensure_ascii=False)
        .encode("utf-8")).hexdigest()
    return digest, data


def normalize(row, ufs, turn):
    rowid, origin, uf, mu, zone, sec, turno, cargo, candidate, votes = row
    if origin not in SOURCES or votes is None:
        return None
    if any(value is None or not str(value).strip()
           for value in (uf, mu, zone, sec, turno, cargo, candidate)):
        return None
    u = str(uf).strip().upper()
    if ufs and u not in ufs:
        return None
    t = numeric(turno)
    if turn is not None and t != str(turn):
        return None
    c = str(cargo).strip().lower()
    if origin == "secao_nacional" and c != "1":
        return None
    return (u, numeric(mu), numeric(zone), numeric(sec), t,
            c, votable(candidate), origin, str(int(votes)))


def bucket_for(record, bucket_count):
    # Todas as chaves da mesma zona são enviadas à mesma partição.
    key = "|".join((record[0], record[1], record[2], record[4]))
    return zlib.crc32(key.encode("utf-8")) % bucket_count


def load_state(path, fingerprint, bucket_count):
    if path.exists():
        state = json.loads(path.read_text(encoding="utf-8"))
        if state.get("fingerprint") != fingerprint:
            raise RuntimeError("Fingerprint dos dados difere do checkpoint")
        if len(state.get("offsets", [])) != bucket_count:
            raise RuntimeError("Checkpoint de particoes possui formato incompativel")
        return state
    state = {"fingerprint": fingerprint, "created_utc": now(),
             "last_rowid": 0, "rows_scanned": 0, "rows_eligible": 0,
             "offsets": [0] * bucket_count, "scan_complete": False,
             "completed_parts": {}}
    save_state(path, state)
    return state


@contextmanager
def exclusive_run(workspace):
    """Lock interprocesso, solto automaticamente quando o processo termina."""
    lockpath = workspace / "stream.lock"
    with open(lockpath, "a+b") as handle:
        if handle.tell() == 0 and lockpath.stat().st_size == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError(
                "Outra reconciliacao stream esta usando o mesmo checkpoint; "
                "encerre a execucao anterior antes de prosseguir") from exc
        try:
            yield
        finally:
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def partition_files(directory, bucket_count):
    directory.mkdir(parents=True, exist_ok=True)
    return [directory / f"bucket-{i:04d}.tsv"
            for i in range(bucket_count)]


def rollback_buckets(paths, offsets):
    """Descarta escrita não consolidada depois do último checkpoint."""
    for path, offset in zip(paths, offsets):
        if not path.exists():
            if offset:
                raise RuntimeError(f"Parte ausente ou perdida: {path}")
            path.touch()
        size = path.stat().st_size
        if size < offset:
            raise RuntimeError(f"Parte menor que checkpoint: {path}")
        if size > offset:
            with open(path, "r+b") as file:
                file.truncate(offset)


def sequential_scan(db, workspace, state, ufs, turn, bucket_count,
                    chunk_rows=1000000, after_chunk=None, pilot_rows=0):
    if state["scan_complete"]:
        print("VARREDURA: integralmente preservada em checkpoint; "
              "nenhuma releitura do SQLite.", flush=True)
        return
    if chunk_rows < 1 or pilot_rows < 0:
        raise ValueError("chunk_rows positivo e pilot_rows nao negativo")
    if pilot_rows:
        chunk_rows = min(chunk_rows, pilot_rows)
        print(f"PILOTO: no maximo {pilot_rows:,} linhas adicionais; "
              "gravar checkpoint e sair sem substituir o relatorio.",
              flush=True)
    files = partition_files(workspace / "buckets", bucket_count)
    rollback_buckets(files, state["offsets"])
    from_rowid = int(state["last_rowid"])
    print(f"VARREDURA SEQUENCIAL: retomando depois de rowid={from_rowid:,}; "
          f"{state['rows_scanned']:,} linhas previamente examinadas; "
          f"{bucket_count} particoes.", flush=True)
    upper = db.execute("SELECT rowid FROM votes ORDER BY rowid DESC LIMIT 1")
    last = upper.fetchone()
    max_rowid = int(last[0]) if last else 0
    query = """SELECT rowid,source_kind,uf,municipio,zona,secao,
                      turno,cargo,votavel,votos
               FROM votes NOT INDEXED WHERE rowid>? ORDER BY rowid"""
    streams = [open(path, "ab", buffering=256 * 1024) for path in files]
    buffers = [io.StringIO() for _ in files]
    writers = [csv.writer(buf, delimiter="\t", lineterminator="\n")
               for buf in buffers]
    count = relevant = 0
    latest_rowid = from_rowid
    first = time.monotonic()
    chunks = 0

    def persist_chunk():
        nonlocal count, relevant, chunks
        if not count:
            return
        for i, buf in enumerate(buffers):
            value = buf.getvalue()
            if value:
                streams[i].write(value.encode("utf-8"))
                buf.seek(0)
                buf.truncate(0)
        # Selo de durabilidade ANTES de avançar o cursor no checkpoint.
        for file in streams:
            file.flush()
            os.fsync(file.fileno())
        state["offsets"] = [file.tell() for file in streams]
        state["last_rowid"] = latest_rowid
        state["rows_scanned"] += count
        state["rows_eligible"] += relevant
        save_state(workspace / "state.json", state)
        chunks += 1
        elapsed = max(time.monotonic() - first, 0.001)
        approx_percent = (100 * latest_rowid / max_rowid
                          if max_rowid else 100)
        print(f"[SCAN CHECKPOINT {chunks}] rowid={latest_rowid:,}/{max_rowid:,} "
              f"(~{approx_percent:.1f}% do intervalo); "
              f"lidas={state['rows_scanned']:,}; "
              f"elegiveis={state['rows_eligible']:,}; "
              f"{int((state['rows_scanned']-initial_scanned)/elapsed):,} "
              "linhas/s nesta execucao.", flush=True)
        count = relevant = 0
        if after_chunk:
            after_chunk(chunks, state)

    initial_scanned = state["rows_scanned"]
    try:
        cursor = db.execute(query, (from_rowid,))
        while True:
            batch = cursor.fetchmany(10000)
            if not batch:
                break
            for row in batch:
                latest_rowid = int(row[0])
                count += 1
                normalized = normalize(row, ufs, turn)
                if normalized is not None:
                    number = bucket_for(normalized, bucket_count)
                    writers[number].writerow(normalized)
                    relevant += 1
                if count >= chunk_rows:
                    persist_chunk()
                    if pilot_rows and state["rows_scanned"] - initial_scanned >= pilot_rows:
                        print(f"PILOTO CONCLUIDO: {state['rows_scanned']-initial_scanned:,} "
                              "linhas novas, checkpoint persistido; "
                              "varredura nacional ainda incompleta.",
                              flush=True)
                        return
        persist_chunk()
        print("SELAGEM: calculando SHA-256 das particoes, "
              "para detectar danos ou alteracoes posteriores.", flush=True)
        bucket_hashes = []
        for i, path in enumerate(files):
            digest = sha256(path)
            bucket_hashes.append(digest)
            if (i+1) % 64 == 0:
                print(f"[SELAGEM] {i+1}/{bucket_count} particoes com hash.",
                      flush=True)
        state["bucket_hashes"] = bucket_hashes
        state["scan_complete"] = True
        state["scan_finished_utc"] = now()
        save_state(workspace / "state.json", state)
        print(f"VARREDURA CONCLUIDA: {state['rows_scanned']:,} linhas examinadas; "
              f"{state['rows_eligible']:,} elegiveis. "
              "Particoes fechadas e preservadas.", flush=True)
    finally:
        for file in streams:
            file.close()


def reconcile_bucket(path, output):
    """Compara todas as fontes da particao sem acesso ao SQLite original."""
    grouped = {}
    raw_rows = 0
    with open(path, "r", encoding="utf-8", newline="") as source:
        for record in csv.reader(source, delimiter="\t"):
            if len(record) != 9:
                raise ValueError(f"Linha invalida na particao {path}: {record[:2]}")
            uf, mu, zo, se, turn, cargo, candidate, origin, votes = record
            key = (uf, mu, zo, se, turn, cargo, candidate)
            totals = grouped.setdefault(key, {})
            totals[origin] = totals.get(origin, 0) + int(votes)
            raw_rows += 1
    checked = diff = missing_bu = missing_sec = 0
    with open(output, "w", encoding="utf-8", newline="") as sink:
        writer = csv.writer(sink, delimiter=";", lineterminator="\n")
        writer.writerow(HEADER)
        for key in sorted(grouped):
            totals = grouped[key]
            b = totals.get("bu")
            sec = (totals["secao"] if "secao" in totals
                   else totals.get("secao_nacional"))
            checked += 1
            if b is None:
                status = "SEM_BU"
                missing_bu += 1
            elif sec is None:
                status = "SEM_SECAO"
                missing_sec += 1
            elif b != sec:
                status = "DIFERENTE"
            else:
                continue
            diff += 1
            writer.writerow((*key, b if b is not None else "",
                             sec if sec is not None else "",
                             b-sec if b is not None and sec is not None else "",
                             status))
        sink.flush()
        os.fsync(sink.fileno())
    return {"checked": checked, "different": diff,
            "missing_bu": missing_bu, "missing_section": missing_sec,
            "raw_rows": raw_rows, "digest": sha256(output)}


def reconcile_parts(workspace, state, bucket_count, after_part=None):
    paths = partition_files(workspace / "buckets", bucket_count)
    expected_hashes = state.get("bucket_hashes")
    if not expected_hashes or len(expected_hashes) != bucket_count:
        raise RuntimeError("Particoes sem selo SHA-256: nao reconciliar")
    for i, path in enumerate(paths):
        if path.stat().st_size != state["offsets"][i]:
            raise RuntimeError(f"Particao modificada desde checkpoint: {path}")
        if sha256(path) != expected_hashes[i]:
            raise RuntimeError(f"Particao alterada ou corrompida: {path}")
    print(f"INTEGRIDADE: {bucket_count} particoes verificadas por SHA-256.",
          flush=True)
    differences = workspace / "differences"
    differences.mkdir(exist_ok=True)
    parts = state["completed_parts"]
    for i, path in enumerate(paths):
        label = str(i)
        dest = differences / f"bucket-{i:04d}.csv"
        old = parts.get(label)
        if old and dest.exists() and sha256(dest) == old["digest"]:
            continue
        started = time.monotonic()
        temp = dest.with_suffix(".csv.part")
        try:
            result = reconcile_bucket(path, temp)
            os.replace(temp, dest)
            parts[label] = result
            save_state(workspace / "state.json", state)
        finally:
            if temp.exists():
                temp.unlink()
        if i < 3 or (i+1) % 10 == 0 or i+1 == bucket_count:
            print(f"[PARTICAO {i+1}/{bucket_count}] "
                  f"{result['checked']:,} chaves; "
                  f"{result['different']:,} diferencas; "
                  f"{time.monotonic()-started:.1f}s; "
                  "checkpoint confirmado.", flush=True)
        if after_part:
            after_part(i, state)
    return parts


def consolidate(workspace, state, bucket_count, output, provenance):
    difference_dir = workspace / "differences"
    partial = Path(str(output) + ".part")
    totals = {"keys_compared": 0, "different_or_missing": 0,
              "missing_bu": 0, "missing_section": 0}
    try:
        with open(partial, "w", encoding="utf-8-sig", newline="") as file:
            writer = csv.writer(file, delimiter=";", lineterminator="\n")
            writer.writerow(HEADER)
            for i in range(bucket_count):
                path = difference_dir / f"bucket-{i:04d}.csv"
                result = state["completed_parts"][str(i)]
                if sha256(path) != result["digest"]:
                    raise RuntimeError(f"Arquivo de particao danificado: {path}")
                for src, target in (("checked", "keys_compared"),
                                    ("different", "different_or_missing"),
                                    ("missing_bu", "missing_bu"),
                                    ("missing_section", "missing_section")):
                    totals[target] += result[src]
                with open(path, "r", encoding="utf-8", newline="") as source:
                    next(source)
                    shutil.copyfileobj(source, file)
            file.flush()
            os.fsync(file.fileno())
        os.replace(partial, output)
    finally:
        if partial.exists():
            partial.unlink()
    report = {
        "created_at_utc": now(), "engine": VERSION,
        "status": ("calculado_com_importacoes_incompletas"
                   if provenance["partial"] else "concluido"),
        "cobertura_nacional_confirmada": False,
        "imports_incomplete": provenance["partial"],
        "fingerprint": state["fingerprint"],
        "rows_scanned": state["rows_scanned"],
        "source_rows_planned": state["rows_eligible"],
        "partitions_completed": bucket_count,
        "partitions_total": bucket_count,
        "keys_compared": totals["keys_compared"],
        "different_or_missing": totals["different_or_missing"],
        "missing_bu": totals["missing_bu"],
        "missing_section": totals["missing_section"],
        "matches": totals["keys_compared"] - totals["different_or_missing"],
        "csv": str(output), "checkpoint_folder": str(workspace),
        "source_priority": "secao estadual por chave; nacional apenas Presidente",
        "limitations": "Comparacao de duas fontes do TSE, nao uma "
                       "verificacao fisica independente das urnas."
    }
    from reconcile_incremental import atomic_json
    atomic_json(output.with_suffix(".summary.json"), report)
    print("RECONCILIACAO STREAM CONCLUIDA", flush=True)
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    return report


def reconcile_stream(db, output, ufs=None, turn=None, buckets=256,
                     chunk_rows=1000000, after_chunk=None, after_part=None,
                     pilot_rows=0):
    """API retomável. after_chunk/after_part usados apenas por testes."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    ufs = {str(uf).upper() for uf in (ufs or [])}
    if buckets < 2 or buckets > 256:
        raise ValueError("O numero de particoes deve ficar entre 2 e 256")
    if chunk_rows < 1 or pilot_rows < 0:
        raise ValueError("Parametros de chunk/piloto invalidos")
    disk_free = shutil.disk_usage(output.parent).free
    if disk_free < 5 * 1024**3:
        raise RuntimeError("Espaco livre insuficiente: exige ao menos 5 GiB "
                           "antes de gerar particoes; preserve os dados")
    fingerprint, provenance = identity(db, ufs, turn, buckets)
    workspace = (output.parent / "reconciliacao_checkpoints" /
                 "stream" / fingerprint)
    workspace.mkdir(parents=True, exist_ok=True)
    with exclusive_run(workspace):
        state = load_state(workspace / "state.json", fingerprint, buckets)
        print(f"RECONCILIACAO STREAM: {buckets} particoes; "
              "leitura sequencial ROWID, sem alterar tabela votes.", flush=True)
        print(f"FONTE: {len(provenance['resources'])} importacoes; "
              f"fingerprint {fingerprint[:16]}; "
              f"checkpoint: {workspace}", flush=True)
        sequential_scan(db, workspace, state, ufs, turn, buckets,
                        chunk_rows=chunk_rows, after_chunk=after_chunk,
                        pilot_rows=pilot_rows)
        if pilot_rows:
            return {"status": "piloto_checkpoint_salvo", "engine": VERSION,
                    "fingerprint": fingerprint, "checkpoint_folder": str(workspace),
                    "rows_scanned": state["rows_scanned"],
                    "rows_eligible": state["rows_eligible"],
                    "scan_complete": state["scan_complete"]}
        if not state["scan_complete"]:
            raise RuntimeError("Particionamento nao finalizado")
        reconcile_parts(workspace, state, buckets, after_part=after_part)
        return consolidate(workspace, state, buckets, output, provenance)
