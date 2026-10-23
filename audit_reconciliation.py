#!/usr/bin/env python3
"""Auditoria somente-leitura do CSV final de reconciliacao BU x secao.

Nao abre SQLite, nao altera checkpoints nem relatorios originais.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path

from urnas import root_path

KEYS = ("UF", "municipio", "zona", "secao", "turno", "cargo", "votavel")
VALID = {"SEM_BU", "SEM_SECAO", "DIFERENTE"}


def audit(csv_path: Path, show_all: bool = False) -> int:
    summary_path = csv_path.with_suffix(".summary.json")
    if not csv_path.is_file() or not summary_path.is_file():
        raise SystemExit("CSV ou resumo ausente: " + str(csv_path))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    with csv_path.open("rb") as source:
        checksum = hashlib.file_digest(source, "sha256").hexdigest()
    with csv_path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source, delimiter=";")
        expected = {*KEYS, "votos_BU", "votos_secao", "diferenca", "situacao"}
        if not expected.issubset(reader.fieldnames or []):
            raise SystemExit("Colunas inesperadas: " + str(reader.fieldnames))
        rows = list(reader)
    statuses = Counter(row["situacao"] for row in rows)
    by_uf = Counter(row["UF"] for row in rows)
    by_office = Counter((row["turno"], row["cargo"]) for row in rows)
    by_uf_office = Counter((row["UF"], row["turno"], row["cargo"])
                           for row in rows)
    by_zone = Counter((row["UF"], row["municipio"], row["zona"],
                       row["turno"]) for row in rows)
    by_candidate = Counter((row["turno"], row["cargo"], row["votavel"])
                           for row in rows)
    locations = {(r["UF"], r["municipio"], r["zona"], r["secao"], r["turno"])
                 for r in rows}
    keys = [tuple(r[k] for k in KEYS) for r in rows]
    duplicate_keys = len(keys) - len(set(keys))
    print("AUDITORIA SOMENTE-LEITURA: nenhum arquivo foi modificado")
    print("CSV:", csv_path)
    print("SHA-256 do CSV:", checksum)
    print("Fingerprint:", summary.get("fingerprint"))
    print("Chaves comparadas:", f"{summary.get('keys_compared', 0):,}")
    print("Linhas de anomalia no CSV:", len(rows))
    print("Situacoes:", dict(sorted(statuses.items())))
    print("Secoes eleitorais distintas envolvidas:", len(locations))
    print("Chaves repetidas no CSV:", duplicate_keys)
    print("Por UF:", dict(sorted(by_uf.items())))
    print("Por turno/cargo:", {"/".join(k): v
                               for k, v in sorted(by_office.items())})
    print("Por UF/turno/cargo:", {"/".join(k): v
                                  for k, v in sorted(by_uf_office.items())})
    print("Zonas com mais ocorrencias:", by_zone.most_common(15))
    print("Votaveis com mais ocorrencias:", by_candidate.most_common(15))
    try:
        votos_bu = sum(int(r["votos_BU"]) for r in rows
                       if r["situacao"] == "SEM_SECAO" and r["votos_BU"].strip())
        print("Soma dos votos BU nas chaves SEM_SECAO:", f"{votos_bu:,}")
    except ValueError:
        print("AVISO: votos_BU contem valor nao inteiro")
    mismatches = []
    for status, key in (("SEM_BU", "missing_bu"),
                        ("SEM_SECAO", "missing_section")):
        if statuses[status] != summary.get(key):
            mismatches.append(f"{status}: CSV={statuses[status]}, resumo={summary.get(key)}")
    if len(rows) != summary.get("different_or_missing"):
        mismatches.append("Total do CSV difere de different_or_missing")
    if duplicate_keys:
        mismatches.append("Chaves duplicadas no CSV")
    if any(status not in VALID for status in statuses):
        mismatches.append("Situacao desconhecida no CSV")
    print("Conferencia CSV x resumo:", "OK" if not mismatches else "; ".join(mismatches))
    limit = len(rows) if show_all else 12
    print(f"Casos individuais (ate {limit}):")
    for r in sorted(rows, key=lambda r: tuple(r[k] for k in KEYS))[:limit]:
        print(" | ".join(r[k] for k in (*KEYS, "votos_BU", "votos_secao", "situacao")))
    return 1 if mismatches else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", help="Diretorio do acervo TSE")
    parser.add_argument("--csv", type=Path, help="CSV de divergencias especifico")
    parser.add_argument("--all", action="store_true",
                        help="Mostrar todas as linhas de anomalia")
    args = parser.parse_args()
    target = args.csv or (root_path(args.root) / "analysis" /
                          "reconciliacao_bu_secao.csv")
    return audit(target, show_all=args.all)


if __name__ == "__main__":
    raise SystemExit(main())
