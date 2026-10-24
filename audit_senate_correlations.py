#!/usr/bin/env python3
"""Auditoria descritiva dos 616 pares Presidente x Senador ja calculados.

Somente leitura dos CSVs de correlacao e SHA-256. NAO relê os 67,8 M
registros BU, SQLite ou 256 particoes. Emite contagens por UF e um CSV
de diagnosticos com todos os pares; nao produz indicios/probabilidade
de fraude nem inferencia de voto individual.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import json
import math
import os
from pathlib import Path

from reconcile_stream import sha256
from urnas import root_path

VERSION = "audit-senate-correlations-v1"
COLUMNS = ("UF", "turno", "presidente", "senador", "secoes_com_dois_cargos",
           "correlacao_bruta_pearson", "correlacao_dentro_municipio_zona",
           "zonas_com_variacao", "votos_senador")
DERIVED = ("uf", "turno", "presidente", "senador", "secoes",
           "zonas_variaveis", "votos_senador", "r_bruto", "r_ajustado",
           "abs_mudanca", "sinal_oposto_robusto", "mudanca_020",
           "amostra_suficiente_descritiva")


def coefficient(value, label):
    if value is None or str(value).strip() == "":
        return None
    number = float(value)
    if not math.isfinite(number) or abs(number) > 1.000001:
        raise RuntimeError("Coeficiente Pearson fora do intervalo: " + label)
    return number


def integer(value, label):
    s = str(value).strip()
    if not s.isdecimal():
        raise RuntimeError("Contagem invalida: " + label + "=" + repr(value))
    return int(s)


def atomic_csv(path, columns, rows):
    temp = Path(str(path) + ".part")
    try:
        with temp.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns,
                                    delimiter=";", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def audit(path, metadata, min_sections=1000, min_zones=10, min_votes=1000):
    """Amostra minima e regra de reversao sao criterios DESCRITIVOS."""
    if min(min_sections, min_zones, min_votes) < 1:
        raise ValueError("Minimos devem ser positivos")
    if sha256(path) != metadata.get("csv_sha256"):
        raise RuntimeError("Hash do CSV de correlacoes nao coincide com o resumo")
    presidents = set(str(p) for p in metadata["presidente_top2"])
    expected = {
        (uf, str(p), str(s))
        for uf, senators in metadata["senadores_por_uf"].items()
        for p in presidents for s in senators
    }
    summary_count = metadata.get("pairs_compared")
    if len(expected) != summary_count or len(presidents) != 2:
        raise RuntimeError("Candidaturas/pares no resumo sao inconsistentes")

    records = []
    seen = set()
    totals = Counter()
    regions = defaultdict(Counter)
    unexplained = defaultdict(list)

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        if not set(COLUMNS).issubset(reader.fieldnames or []):
            raise RuntimeError("Colunas inesperadas no CSV de correlacoes")
        for row in reader:
            uf, t, p, s = (row["UF"], row["turno"],
                            row["presidente"], row["senador"])
            key = (uf, p, s)
            if key not in expected or key in seen:
                raise RuntimeError("Par desconhecido ou repetido: " + repr(key))
            seen.add(key)
            n = integer(row["secoes_com_dois_cargos"], "secoes")
            z = integer(row["zonas_com_variacao"], "zonas")
            v = integer(row["votos_senador"], "votos_senador")
            if z > n or (n == 0 and z != 0):
                raise RuntimeError("Contagem de zonas incoerente")
            r0 = coefficient(row["correlacao_bruta_pearson"], "bruto")
            r1 = coefficient(row["correlacao_dentro_municipio_zona"], "ajustado")
            eligible = (n >= min_sections and z >= min_zones
                        and v >= min_votes and r0 is not None and r1 is not None)
            opposite = (eligible and abs(r0) >= 0.1 and abs(r1) >= 0.1
                        and r0 * r1 < 0)
            large_shift = eligible and abs(r0 - r1) >= 0.2
            delta = abs(r0 - r1) if r0 is not None and r1 is not None else None
            rec = {"uf": uf, "turno": t, "presidente": p, "senador": s,
                   "secoes": n, "zonas_variaveis": z,
                   "votos_senador": v, "r_bruto": r0 if r0 is not None else "",
                   "r_ajustado": r1 if r1 is not None else "",
                   "abs_mudanca": round(delta, 6) if delta is not None else "",
                   "sinal_oposto_robusto": int(opposite),
                   "mudanca_020": int(large_shift),
                   "amostra_suficiente_descritiva": int(eligible)}
            records.append(rec)
            counts = (totals, regions[uf])
            for count in counts:
                count["pares"] += 1
                count["sem_coeficiente_bruto"] += r0 is None
                count["sem_coeficiente_ajustado"] += r1 is None
                count["amostra_suficiente"] += eligible
                count["amostra_insuficiente"] += not eligible
                count["sinais_opostos_robustos"] += opposite
                count["alteracao_absoluta_020"] += large_shift
                if eligible:
                    count["ajustado_positivo_010"] += r1 >= 0.1
                    count["ajustado_negativo_010"] += r1 <= -0.1
                    count["ajustado_proximo_zero"] += -0.1 < r1 < 0.1
            if opposite:
                unexplained[uf].append((p, s))
    if seen != expected:
        raise RuntimeError("Faltam pares no CSV: " + str(len(expected - seen)))
    if len(records) != summary_count:
        raise RuntimeError("Contador de pares nao fecha")
    by_uf = [{"UF": uf, **{field: counts.get(field, 0) for field in
                 ("pares", "amostra_suficiente", "amostra_insuficiente",
                  "sem_coeficiente_bruto", "sem_coeficiente_ajustado",
                  "sinais_opostos_robustos", "alteracao_absoluta_020",
                  "ajustado_positivo_010", "ajustado_negativo_010",
                  "ajustado_proximo_zero")}}
             for uf, counts in sorted(regions.items())]
    return records, by_uf, dict(totals)


def run(root, min_sections=1000, min_zones=10, min_votes=1000):
    analysis = root / "analysis"
    national = json.loads(
        (analysis / "reconciliacao_bu_secao.summary.json").read_text("utf-8"))
    matching = []
    for summary in (analysis / "entre_cargos").glob("*/correlacao_presidente_senado/summary.json"):
        data = json.loads(summary.read_text("utf-8"))
        if (data.get("fingerprint") == national["fingerprint"] and
                data.get("status") == "DESCRITIVO_CONCLUIDO"):
            matching.append((summary.parent, data))
    if len(matching) != 1:
        raise RuntimeError("Esperado um resumo nacional de Senado; obtidos: "
                           + str(len(matching)))
    directory, meta = matching[0]
    csv_path = Path(meta["csv"])
    print("AUDITORIA SENADO: usando apenas o CSV de correlacoes")
    print("Arquivo original:", csv_path)
    records, by_uf, counts = audit(
        csv_path, meta, min_sections=min_sections,
        min_zones=min_zones, min_votes=min_votes)
    dest = directory / "diagnostico"
    dest.mkdir(exist_ok=True)
    details = dest / "todos_pares.csv"
    regions = dest / "por_uf.csv"
    atomic_csv(details, DERIVED, sorted(
        records, key=lambda r: (r["uf"], r["presidente"], r["senador"])))
    atomic_csv(regions, list(by_uf[0]) if by_uf else ["UF"], by_uf)
    result = {
        "version": VERSION, "status": "DESCRITIVO_CONCLUIDO",
        "source_csv_sha256": meta["csv_sha256"],
        "source_fingerprint": meta["fingerprint"],
        "pares_avaliados": len(records),
        "ufs": len(by_uf),
        "thresholds_predefinidos": {
            "min_secoes": min_sections, "min_zonas": min_zones,
            "min_votos_senador": min_votes,
            "sinais_opostos": "|r_bruto|>=0.1 e |r_ajustado|>=0.1 com sinais contrarios",
            "mudanca_grande": "|r_bruto-r_ajustado|>=0.2",
        },
        "contagens": {field: counts.get(field, 0) for field in
                     ("pares", "amostra_suficiente", "amostra_insuficiente",
                      "sem_coeficiente_bruto", "sem_coeficiente_ajustado",
                      "sinais_opostos_robustos", "alteracao_absoluta_020",
                      "ajustado_positivo_010", "ajustado_negativo_010",
                      "ajustado_proximo_zero")},
        "ufs_com_sinal_oposto": [
            {"UF": item["UF"], "pares": item["sinais_opostos_robustos"]}
            for item in by_uf if item["sinais_opostos_robustos"] > 0],
        "files": {
            "todos_pares.csv": {"sha256": sha256(details), "path": str(details)},
            "por_uf.csv": {"sha256": sha256(regions), "path": str(regions)},
        },
        "limitations": [
            "Efeito ecologico: correlacao por secao nao prova voto individual",
            "Reversao de sinal e alteracao de magnitude nao sao evidencias de fraude",
            "Limiar de tamanho e estatistica sao regras descritivas, nao p-valores",
            "Correlacoes foram calculadas em escala de eleitores para Senado com duas escolhas",
            "Sem comparacao com pesquisas, resultados historicos ou assinaturas nesta etapa",
        ],
    }
    out = dest / "summary.json"
    tmp = Path(str(out) + ".part")
    try:
        tmp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
        os.replace(tmp, out)
    finally:
        if tmp.exists():
            tmp.unlink()
    print("DIAGNOSTICO DOS 616 PARES CONCLUIDO")
    print(json.dumps({
        "pares_avaliados": len(records), "ufs": len(by_uf),
        "contagens": result["contagens"],
        "ufs_com_sinal_oposto": result["ufs_com_sinal_oposto"],
        "relatorio": str(out),
    }, ensure_ascii=False, indent=2), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", help="Pasta base do acervo (Windows H:)")
    parser.add_argument("--min-sections", type=int, default=1000)
    parser.add_argument("--min-zones", type=int, default=10)
    parser.add_argument("--min-votes", type=int, default=1000)
    args = parser.parse_args()
    run(root_path(args.root), args.min_sections, args.min_zones, args.min_votes)


if __name__ == "__main__":
    main()
