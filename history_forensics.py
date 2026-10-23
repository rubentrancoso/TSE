#!/usr/bin/env python3
"""Preservacao versionada, verificavel e economica dos relatorios forenses.

Sem dependencia externa. Resultados no H: tem snapshots imutaveis com
armazenamento por SHA-256 (deduplicacao): nenhum relatorio anterior e
sobrescrito, mesmo quando o arquivo 'latest' e regenerado.
Os arquivos brutos e o banco SQLite NAO sao duplicados aqui: registramos
SHA-256/identificadores de entradas e hashes do codigo, quando disponiveis.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


CODE_FILES = (
    "urnas.py", "statistical_forensics.py", "history_forensics.py",
    "collect_forensics.py", "start_windows.bat",
)
REPORT_SUFFIXES = {".csv", ".json", ".jsonl", ".md"}


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def digest_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(2 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def git_version():
    try:
        root = Path(__file__).resolve().parent
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root,
            timeout=4, stderr=subprocess.DEVNULL, text=True).strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None


def source_rows(root):
    """Recibos das fontes importadas; tabela pequena, nunca le os votos aqui."""
    db_path = root / "analysis" / "urna_2026.sqlite3"
    if not db_path.is_file():
        return []
    con = None
    try:
        con = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
        return [
            {"resource": key, "sha256": digest, "rows": rows, "files": files}
            for key, digest, rows, files in con.execute(
                "SELECT resource_key,sha256,rows,files FROM imports ORDER BY resource_key")
        ]
    except sqlite3.DatabaseError:
        return [{"status": "unavailable", "reason": "imports nao legiveis"}]
    finally:
        if con is not None:
            con.close()


def eligible_reports(root):
    """Somente relatorios finais, sem banco vivo, bruto, temporarios ou history."""
    root = Path(root)
    analysis = root / "analysis"
    if not analysis.exists():
        return []
    selected = []
    for folder in (analysis, analysis / "estatistica"):
        if not folder.exists():
            continue
        for path in sorted(folder.iterdir()):
            if path.is_file() and path.suffix.lower() in REPORT_SUFFIXES:
                selected.append((path, path.relative_to(root).as_posix()))
    for name in ("download_manifest_latest.json", "catalogo_latest.json",
                 "repair_manifest_latest.json"):
        path = root / name
        if path.is_file():
            selected.append((path, name))
    return selected


def atomic_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    part = Path(str(path) + ".part")
    with part.open("w", encoding="utf-8") as stream:
        json.dump(obj, stream, indent=2, ensure_ascii=False, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(part, path)


def store_object(file_path, obj_root, sha):
    dest = obj_root / (sha + ".gz")
    if dest.is_file():
        return dest
    obj_root.mkdir(parents=True, exist_ok=True)
    part = obj_root / (sha + "." + uuid.uuid4().hex + ".part")
    try:
        with file_path.open("rb") as src, part.open("wb") as binary:
            with gzip.GzipFile(fileobj=binary, mode="wb", filename="", mtime=0) as zipped:
                shutil.copyfileobj(src, zipped, length=2 * 1024 * 1024)
            binary.flush()
            os.fsync(binary.fileno())
        os.replace(part, dest)
        return dest
    finally:
        if part.exists():
            part.unlink()


def snapshot(root, stage, *, context=None, allow_empty=False):
    """Cria entrada historica consistente. Nunca reescreve runs antigos."""
    root = Path(root)
    reports = eligible_reports(root)
    if not reports and not allow_empty:
        return None
    archive_root = root / "analysis" / "history"
    archive_root.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid.uuid4().hex[:10]
    records = []
    objects = archive_root / "objects"
    print(f"HISTORICO {stage}: preservando {len(reports)} relatorios.", flush=True)
    for index, (path, relative) in enumerate(reports, 1):
        print(f"  HISTORICO [{index}/{len(reports)}] {relative} "
              f"({path.stat().st_size:,} bytes)", flush=True)
        checksum = digest_file(path)
        stored = store_object(path, objects, checksum)
        records.append({
            "path": relative,
            "bytes": path.stat().st_size,
            "sha256": checksum,
            "object_gzip": stored.relative_to(archive_root).as_posix()
        })
    source = Path(__file__).resolve().parent
    source_code = [
        {"path": name, "sha256": digest_file(source / name)}
        for name in CODE_FILES if (source / name).exists()
    ]
    manifest = {
        "schema": "tse-analysis-history-v1", "run_id": run_id,
        "stage": stage, "captured_utc": utc_now(),
        "status": "snapshot", "git_commit": git_version(),
        "root": str(root), "reports": records, "code": source_code,
        "sources_imported": source_rows(root), "context": context or {},
        "caveats": [
            "Este manifesto comprova os bytes preservados de cada relatorio, "
            "nao a veracidade independente dos dados eleitorais.",
            "O arquivo SQLite em uso nao e copiado: registrar suas fontes importadas "
            "nao equivale a preservacao de todas as linhas do banco em cada etapa.",
            "Snapshots nao demonstram por si sós cobertura nacional completa."
        ]
    }
    dest = archive_root / "runs" / (run_id + ".json")
    atomic_json(dest, manifest)
    log_path = archive_root / "ledger.jsonl"
    with log_path.open("ab") as log:
        log.write((json.dumps({
            "run_id": run_id, "captured_utc": manifest["captured_utc"],
            "stage": stage, "git_commit": manifest["git_commit"],
            "reports": len(records), "manifest": dest.name
        }, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"))
        log.flush()
        os.fsync(log.fileno())
    print("HISTORICO: " + str(dest), flush=True)
    return manifest


def restore(root, run_id, output, *, overwrite=False):
    """Reconstitui relatórios antigos em uma pasta SEPARADA."""
    root, output = Path(root), Path(output)
    history = root / "analysis" / "history"
    if not run_id or any(x in run_id for x in ("/", "\\", "..")):
        raise ValueError("Identificador invalido")
    manifest_path = history / "runs" / (run_id + ".json")
    record = json.loads(manifest_path.read_text(encoding="utf-8"))
    count = 0
    for item in record["reports"]:
        rel = Path(item["path"])
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError("Caminho inseguro: " + str(rel))
        dest = output / rel
        if dest.exists() and not overwrite:
            raise FileExistsError("Destino existente: " + str(dest))
        src = history / item["object_gzip"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        temp = Path(str(dest) + ".restore.part")
        try:
            with gzip.open(src, "rb") as stream, temp.open("wb") as out:
                shutil.copyfileobj(stream, out, length=2 * 1024 * 1024)
            if digest_file(temp) != item["sha256"]:
                raise ValueError("SHA-256 incorreto apos restauracao: " + item["path"])
            os.replace(temp, dest)
            count += 1
        finally:
            if temp.exists():
                temp.unlink()
    return count


def main():
    parser = argparse.ArgumentParser(description="Consultar/restaurar historico das analises")
    parser.add_argument("action", choices=("list", "restore", "snapshot"))
    parser.add_argument("--root", default=("H:/TSE/forensics/urnas" if os.name == "nt"
                                          else "data/forensics/urnas"))
    parser.add_argument("--run-id")
    parser.add_argument("--output")
    parser.add_argument("--stage", default="manual")
    opts = parser.parse_args()
    root = Path(opts.root)
    if opts.action == "snapshot":
        snapshot(root, opts.stage)
    elif opts.action == "list":
        path = root / "analysis" / "history" / "ledger.jsonl"
        print(path.read_text(encoding="utf-8") if path.exists() else "Sem snapshots.")
    else:
        if not opts.run_id or not opts.output:
            parser.error("restore exige --run-id e --output")
        print("Relatorios restaurados:", restore(root, opts.run_id, opts.output))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, sqlite3.DatabaseError) as e:
        print("FALHA NO HISTORICO:", e, file=sys.stderr)
        sys.exit(1)
