#!/usr/bin/env python3
"""Compara os coeficientes senatoriais de ajuste geografico v1 e v2 (2026).

v1 centralizou municipios/zonas dentro de cada bucket SHA isoladamente.
v2 reune todos os buckets antes de remover as medias territoriais.
Nao le BU nem SQLite; verifica integridade dos dois CSVs e compara
616 pares sem supor que as antigas 13 inversoes persistem.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import argparse
import csv
import json
import os
from pathlib import Path

from audit_senate_correlations import coefficient, integer
from reconcile_stream import sha256
from urnas import root_path

VERSION = "compare-senate-geo-v1-v2-2026-v1"
COLS = ("UF", "turno", "presidente", "senador",
        "secoes_com_dois_cargos", "correlacao_bruta_pearson",
        "correlacao_dentro_municipio_zona", "zonas_com_variacao",
        "votos_senador")
OUT_FIELDS = ("UF", "turno", "presidente", "senador", "secoes",
              "votos_senador", "r_bruto", "r_zona_v1", "r_zona_v2",
              "diferenca_ajuste", "qualificado_v1",
              "qualificado_v2", "inversao_v1", "inversao_v2")


def read_one(folder, expected_fp):
    meta = json.loads((folder / "summary.json").read_text("utf-8"))
    if (meta["status"] != "DESCRITIVO_CONCLUIDO" or
            meta["fingerprint"] != expected_fp):
        raise RuntimeError("Versao ou fingerprint inesperado: " + str(folder))
    csv_path = Path(meta["csv"])
    if not csv_path.is_file() or sha256(csv_path) != meta["csv_sha256"]:
        raise RuntimeError("SHA-256 divergente em " + str(folder))
    indexed = {}
    with csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter=";")
        if not set(COLS).issubset(reader.fieldnames or []):
            raise RuntimeError("CSV de Senado com colunas inesperadas")
        for rec in reader:
            key = (rec["UF"], rec["turno"], rec["presidente"], rec["senador"])
            if key in indexed:
                raise RuntimeError("Par repetido: " + repr(key))
            n = integer(rec["secoes_com_dois_cargos"], "secoes")
            z = integer(rec["zonas_com_variacao"], "zonas")
            v = integer(rec["votos_senador"], "votos")
            if z > n:
                raise RuntimeError("Grupos geograficos acima de secoes")
            indexed[key] = {
                "n": n, "zones": z, "votes": v,
                "raw": coefficient(rec["correlacao_bruta_pearson"], "bruto"),
                "adjusted": coefficient(
                    rec["correlacao_dentro_municipio_zona"], "ajustado"),
            }
    if len(indexed) != meta["pairs_compared"]:
        raise RuntimeError("Numero de pares nao fecha: " + str(folder))
    return meta, indexed


def qualifies(data):
    return (data["n"] >= 1000 and data["zones"] >= 10 and
            data["votes"] >= 1000 and data["raw"] is not None and
            data["adjusted"] is not None)


def sign_reverse(data):
    if not qualifies(data):
        return False
    a, b = data["raw"], data["adjusted"]
    return abs(a) >= 0.1 and abs(b) >= 0.1 and a*b < 0


def compare(first, second, fp):
    old_meta, old_rows = read_one(first, fp)
    new_meta, new_rows = read_one(second, fp)
    if (set(old_rows) != set(new_rows) or
            old_meta["presidente_top2"] != new_meta["presidente_top2"] or
            old_meta["senadores_por_uf"] != new_meta["senadores_por_uf"] or
            old_meta["candidate_keys_checked"] != new_meta["candidate_keys_checked"]):
        raise RuntimeError("Universos de candidaturas ou chaves diferentes")
    if new_meta["version"] != "cross-office-senate-v2":
        raise RuntimeError("Relatorio v2 nao apresenta versao corrigida")
    result = []
    counts = Counter()
    by_uf = defaultdict(Counter)
    for key in sorted(old_rows):
        old, new = old_rows[key], new_rows[key]
        if (old["n"] != new["n"] or old["votes"] != new["votes"] or
                old["raw"] != new["raw"]):
            raise RuntimeError("Dados brutos nao podem mudar: " + repr(key))
        flip_old, flip_new = sign_reverse(old), sign_reverse(new)
        diff = (abs(old["adjusted"] - new["adjusted"])
                if old["adjusted"] is not None and new["adjusted"] is not None
                else None)
        row = {
            "UF": key[0], "turno": key[1],
            "presidente": key[2], "senador": key[3],
            "secoes": old["n"], "votos_senador": old["votes"],
            "r_bruto": old["raw"] if old["raw"] is not None else "",
            "r_zona_v1": old["adjusted"] if old["adjusted"] is not None else "",
            "r_zona_v2": new["adjusted"] if new["adjusted"] is not None else "",
            "diferenca_ajuste": round(diff, 6) if diff is not None else "",
            "qualificado_v1": int(qualifies(old)),
            "qualificado_v2": int(qualifies(new)),
            "inversao_v1": int(flip_old),
            "inversao_v2": int(flip_new),
        }
        result.append(row)
        for accum in (counts, by_uf[key[0]]):
            accum["pares"] += 1
            accum["v1_inversoes"] += flip_old
            accum["v2_inversoes"] += flip_new
            accum["persistentes"] += bool(flip_old and flip_new)
            accum["apenas_v1"] += bool(flip_old and not flip_new)
            accum["novas_v2"] += bool(flip_new and not flip_old)
            accum["coeficientes_alterados"] += bool(diff is not None and diff > 0.000001)
    return result, counts, dict(by_uf), old_meta, new_meta


def run(root):
    analysis = root / "analysis"
    fp = json.loads(
        (analysis / "reconciliacao_bu_secao.summary.json").read_text("utf-8")
    )["fingerprint"]
    matches = []
    for p in (analysis / "entre_cargos").glob("*/correlacao_presidente_senado_v2/summary.json"):
        obj = json.loads(p.read_text("utf-8"))
        if obj.get("fingerprint") == fp:
            matches.append(p.parent.parent)
    if len(matches) != 1:
        raise RuntimeError("Esperada uma unica matriz Senado v2: " + str(len(matches)))
    parent = matches[0]
    old = parent / "correlacao_presidente_senado"
    new = parent / "correlacao_presidente_senado_v2"
    data, total, by_uf, meta_old, meta_new = compare(old, new, fp)
    dest = new / "comparacao_metodologica"
    dest.mkdir(exist_ok=True)
    csv_path = dest / "todos_pares_v1_v2.csv"
    tmp = Path(str(csv_path)+".part")
    try:
        with tmp.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, delimiter=";",
                                    fieldnames=OUT_FIELDS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, csv_path)
    finally:
        if tmp.exists():
            tmp.unlink()
    report = {
        "version": VERSION, "status": "COMPARACAO_CONCLUIDA",
        "fingerprint": fp,
        "source_v1_sha256": meta_old["csv_sha256"],
        "source_v2_sha256": meta_new["csv_sha256"],
        "pairs_compared": len(data),
        "totals": dict(total),
        "by_uf": {uf: dict(c) for uf, c in sorted(by_uf.items())},
        "v2_pares_com_inversao": [
            {"UF": r["UF"], "presidente": r["presidente"],
             "senador": r["senador"], "r_bruto": r["r_bruto"],
             "r_ajustado": r["r_zona_v2"], "secoes": r["secoes"],
             "votos_senador": r["votos_senador"]}
            for r in data if r["inversao_v2"]],
        "output": str(csv_path), "output_sha256": sha256(csv_path),
        "limites": [
            "A analise v1 de 13 inversoes estava baseada no controle geometrico por bucket e nao deve ser reutilizada",
            "Mudar sinal por ajuste geográfico nao demonstra fraude",
            "Dados de 2022 nao foram utilizados",
        ],
    }
    json_path = dest / "summary.json"
    part = Path(str(json_path)+".part")
    try:
        part.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n",
                        encoding="utf-8")
        os.replace(part, json_path)
    finally:
        if part.exists():
            part.unlink()
    print("COMPARACAO DE SENADO v1 x v2 CONCLUIDA")
    print(json.dumps({
        "pares": len(data), "comparacao": dict(total),
        "ufs": {uf: c["v2_inversoes"] for uf, c in sorted(by_uf.items())
                if c["v2_inversoes"]},
        "pares_v2_invertidos": report["v2_pares_com_inversao"],
        "csv": str(csv_path), "sha256": report["output_sha256"]
    }, ensure_ascii=False, indent=2), flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", help="Pasta do acervo H:")
    args = parser.parse_args()
    run(root_path(args.root))
