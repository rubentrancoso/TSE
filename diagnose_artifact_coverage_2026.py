#!/usr/bin/env python3
"""Diagnostico de cobertura dos ZIPs de transmissao TSE 2026, sem baixar nada.

Examina somente metadados locais: catalogo_latest.json, arquivos sob
raw/artefatos e tabelas imports/archive_entries do SQLite em mode=ro.
NAO abre ZIPs, NAO percorre csv de votos e NAO usa dados de 2022.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import sqlite3

from urnas import root_path, resource_path, select_resources

VERSION = "diagnose-artifact-coverage-2026-v1"


def catalog_local(root):
    path = root / "catalogo_latest.json"
    if not path.is_file():
        return {"status": "CATALOGO_SALVO_AUSENTE", "resources": 0,
                "local": 0, "missing": 0, "sample_missing": [],
                "nota": "Sem catalogo salvo; comando urnas.py status --kind artefatos consulta o catalogo oficial sem baixar ZIP"}
    obj = json.loads(path.read_text("utf-8"))
    archive = obj.get("datasets", {}).get("artefatos")
    if not archive:
        return {"status": "CONJUNTO_ARTEFATOS_AUSENTE_NO_CATALOGO_SALVO",
                "resources": 0, "local": 0, "missing": 0,
                "sample_missing": []}
    resources = select_resources({"artefatos": archive}, ["artefatos"], [], None)
    count_local = 0
    missing = []
    sizes = 0
    sample_present = []
    for kind, uf, resource in resources:
        local = resource_path(root, kind, uf, resource)
        if local.is_file():
            count_local += 1
            sizes += local.stat().st_size
            if len(sample_present) < 4:
                sample_present.append({"UF": uf, "file": str(local),
                                       "bytes": local.stat().st_size})
        elif len(missing) < 35:
            missing.append({"UF": uf, "file": str(local),
                            "resource_id": resource.get("id")})
    return {
        "status": "CATALOGO_SALVO_CONSULTADO",
        "last_checked_utc": obj.get("checked_at_utc"),
        "resources": len(resources),
        "local": count_local,
        "missing": len(resources) - count_local,
        "bytes_local": sizes,
        "sample_present": sample_present,
        "sample_missing": missing,
        "nota": "Existencia de arquivo local nao confirma conteudo ou hash; leitura de ZIP nao realizada",
    }


def disk_artefacts(root):
    base = root / "raw" / "artefatos"
    if not base.is_dir():
        return {"status": "PASTA_AUSENTE", "files": 0, "zips": 0,
                "partials": 0, "bytes": 0, "ufs": [],
                "samples": []}
    counts = Counter()
    ufs = Counter()
    samples = []
    for item in base.iterdir():
        if not item.is_dir():
            continue
        for file in item.iterdir():
            if not file.is_file():
                continue
            name = file.name.lower()
            if name.endswith(".meta.json"):
                counts["manifests"] += 1
                continue
            if name.endswith(".part"):
                counts["partials"] += 1
            elif name.endswith(".zip"):
                counts["zips"] += 1
            else:
                counts["others"] += 1
            counts["files"] += 1
            counts["bytes"] += file.stat().st_size
            ufs[item.name] += 1
            if len(samples) < 12:
                samples.append({"UF": item.name, "name": file.name,
                                "bytes": file.stat().st_size})
    return {
        "status": "PASTA_INSPECIONADA",
        "files": counts["files"], "zips": counts["zips"],
        "partials": counts["partials"], "others": counts["others"],
        "manifests": counts["manifests"],
        "bytes": counts["bytes"],
        "ufs": dict(sorted(ufs.items())), "samples": samples,
    }


def sqlite_catalog(root):
    dbpath = root / "analysis" / "urna_2026.sqlite3"
    if not dbpath.is_file():
        return {"status": "BANCO_AUSENTE", "imports_por_tipo": {},
                "entradas_por_tipo": {}, "extensoes": {}}
    conn = sqlite3.connect(dbpath.resolve().as_uri()+"?mode=ro",
                           uri=True, timeout=30)
    try:
        conn.execute("PRAGMA query_only=ON")
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        imported = Counter()
        indexed = Counter()
        extensions = Counter()
        for table in ("imports", "archive_entries"):
            if table not in tables:
                continue
            sql = ("SELECT resource_key FROM "+table
                   if table == "imports" else
                   "SELECT resource_key, extensao FROM archive_entries")
            # SQL agrupa por prefixo; nao traz milhões de linhas ao Python.
            query = ("SELECT CASE WHEN INSTR(resource_key,':')>0 "
                     "THEN SUBSTR(resource_key,1,INSTR(resource_key,':')-1) "
                     "ELSE 'INDEFINIDO' END tipo, COUNT(*) FROM "+table+
                     " GROUP BY tipo")
            dest = imported if table == "imports" else indexed
            for kind, amount in conn.execute(query):
                dest[kind] += amount
        if "archive_entries" in tables:
            for ext, amount in conn.execute(
                    "SELECT LOWER(COALESCE(extensao,'')),COUNT(*) "
                    "FROM archive_entries GROUP BY LOWER(COALESCE(extensao,''))"):
                extensions[ext if ext else "(sem extensao)"] += amount
        return {
            "status": "BANCO_CONSULTADO",
            "imports_por_tipo": dict(sorted(imported.items())),
            "entradas_por_tipo": dict(sorted(indexed.items())),
            "extensoes": dict(sorted(extensions.items())),
            "nota": "imports=recursos indexados, entradas=arquivos internos de ZIP; nenhum registro de votos lido",
        }
    finally:
        conn.close()


def run(root, write=True):
    root = Path(root)
    recorded = {
        "version": VERSION,
        "escopo": "2026_SOMENTE",
        "catalogo_oficial_salvo": catalog_local(root),
        "disco_zip_transmissao": disk_artefacts(root),
        "indice_sqlite": sqlite_catalog(root),
    }
    if write:
        output = root / "analysis" / "evidencia_material_2026" / "diagnostico_cobertura.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        part = Path(str(output)+".part")
        try:
            part.write_text(json.dumps(recorded, ensure_ascii=False, indent=2)+"\n",
                            encoding="utf-8")
            os.replace(part, output)
        finally:
            if part.exists():
                part.unlink()
        recorded["output"] = str(output)
    print("DIAGNOSTICO DE COBERTURA DE ZIP TSE 2026 CONCLUIDO")
    print(json.dumps(recorded, ensure_ascii=False, indent=2), flush=True)
    return recorded


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", help="Acervo de dados, padrao H:")
    args = p.parse_args()
    run(root_path(args.root))


if __name__ == "__main__":
    main()
