#!/usr/bin/env python3
"""Diagnostico conjunto de 162 pares Presidente x Governador e 616 x Senado.

Somente leitura dos dois CSVs de coeficientes ja produzidos. Revalida
SHA-256, universo de pares e fingerprint. Nao toca BU/SQLite.
Os denominadores de Governador e Senado DIFEREM: comparar apenas
estrutura de sinais e disponibilidade, nunca interpretar coeficientes
como medida de voto individual ou como prova de fraude.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import json
import os
from pathlib import Path

from audit_senate_correlations import coefficient, integer, atomic_csv
from reconcile_stream import sha256
from urnas import root_path

VERSION = "audit-cross-office-correlations-v1"
OFFICES = {
    "governador": {
        "folder": "correlacao_presidente_governador",
        "candidate_field": "governador",
        "candidate_set": "governador_top_por_uf",
        "votes_field": None,
        "sections_field": "secoes_pareadas_validas",
        "zones_field": "grupos_com_variacao_interna",
        "csv_field": "correlation_csv",
        "hash_field": "correlation_csv_sha256",
    },
    "senador": {
        "folder": "correlacao_presidente_senado",
        "candidate_field": "senador",
        "candidate_set": "senadores_por_uf",
        "votes_field": "votos_senador",
        "sections_field": "secoes_com_dois_cargos",
        "zones_field": "zonas_com_variacao",
        "csv_field": "csv",
        "hash_field": "csv_sha256",
    },
}
DETAIL_FIELDS = [
    "cargo", "UF", "turno", "presidente", "candidato",
    "secoes", "grupos_geograficos_com_variacao",
    "votos_candidato_disponiveis", "r_bruto", "r_ajustado",
    "abs_mudanca", "apto_criterios_comuns", "apto_com_filtro_de_votos",
    "sinal_oposto", "mudanca_pelo_menos_020", "sem_coeficiente",
]


def locate(root):
    analysis = root / "analysis"
    national = json.loads(
        (analysis / "reconciliacao_bu_secao.summary.json").read_text("utf-8"))
    fingerprint = national["fingerprint"]
    found = {}
    for office, spec in OFFICES.items():
        matched = []
        pattern = "*/" + spec["folder"] + "/summary.json"
        for path in (analysis / "entre_cargos").glob(pattern):
            item = json.loads(path.read_text("utf-8"))
            if item.get("fingerprint") == fingerprint and item.get("status") == "DESCRITIVO_CONCLUIDO":
                matched.append((path, item))
        if len(matched) != 1:
            raise RuntimeError(
                f"Esperado exatamente um relatorio para {office} "
                f"do fingerprint nacional; encontrados {len(matched)}")
        found[office] = matched[0]
    folders = {p.parent.parent for p, _ in found.values()}
    if len(folders) != 1:
        raise RuntimeError("Os modulos foram produzidos em matrizes distintas")
    if set(found["governador"][1]["presidente_top2"]) != set(
            found["senador"][1]["presidente_top2"]):
        raise RuntimeError("As candidaturas presidenciais de origem diferem")
    return fingerprint, next(iter(folders)), found


def inspect_one(path, metadata, office, *, min_sections=1000, min_zones=10,
                min_senate_votes=1000):
    spec = OFFICES[office]
    source_file = Path(metadata[spec["csv_field"]])
    if not source_file.is_file():
        raise RuntimeError("CSV nao encontrado: " + str(source_file))
    digest = sha256(source_file)
    if digest != metadata.get(spec["hash_field"]):
        raise RuntimeError(f"SHA-256 divergente no arquivo de {office}")
    selected = metadata.get(spec["candidate_set"])
    presidents = metadata.get("presidente_top2")
    if not isinstance(selected, dict) or not isinstance(presidents, list) or len(set(presidents)) != 2:
        raise RuntimeError("Metadados incompletos: " + office)
    expected = {
        (uf, str(p), str(candidate))
        for uf, chosen in selected.items()
        for p in presidents for candidate in chosen
    }
    if len(expected) != int(metadata.get("pairs_compared", -1)):
        raise RuntimeError("Quantidade esperada de pares incoerente em " + office)
    if not expected:
        raise RuntimeError("Nenhum par em " + office)

    required = {
        "UF", "turno", "presidente", spec["candidate_field"],
        spec["sections_field"], spec["zones_field"],
        "correlacao_bruta_pearson", "correlacao_dentro_municipio_zona",
    }
    if spec["votes_field"]:
        required.add(spec["votes_field"])
    seen = set()
    rows = []
    with source_file.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, delimiter=";")
        if not required.issubset(reader.fieldnames or []):
            raise RuntimeError("Colunas obrigatorias ausentes em " + office)
        for line in reader:
            key = (line["UF"], line["presidente"],
                   line[spec["candidate_field"]])
            if key not in expected or key in seen:
                raise RuntimeError("Par repetido ou desconhecido: " + str(key))
            seen.add(key)
            if line["turno"] != str(metadata.get("turno")):
                raise RuntimeError("Turno diferente do resumo")
            n = integer(line[spec["sections_field"]], "secoes")
            z = integer(line[spec["zones_field"]], "zonas")
            if z > n:
                raise RuntimeError("Mais grupos geograficos do que secoes")
            votes = (integer(line[spec["votes_field"]], "votos")
                     if spec["votes_field"] else None)
            r0 = coefficient(line["correlacao_bruta_pearson"], "r_bruto")
            r1 = coefficient(line["correlacao_dentro_municipio_zona"],
                             "r_ajustado")
            common = (n >= min_sections and z >= min_zones and
                      r0 is not None and r1 is not None)
            vote_eligible = (common and (votes is None or
                                        votes >= min_senate_votes))
            flip = bool(vote_eligible and
                        abs(r0) >= 0.1 and abs(r1) >= 0.1 and r0*r1 < 0)
            large = bool(vote_eligible and abs(r0-r1) >= 0.2)
            rows.append({
                "cargo": office, "UF": key[0], "turno": line["turno"],
                "presidente": key[1], "candidato": key[2],
                "secoes": n, "grupos_geograficos_com_variacao": z,
                "votos_candidato_disponiveis": (
                    votes if votes is not None else ""),
                "r_bruto": r0 if r0 is not None else "",
                "r_ajustado": r1 if r1 is not None else "",
                "abs_mudanca": (
                    round(abs(r0-r1), 6)
                    if r0 is not None and r1 is not None else ""),
                "apto_criterios_comuns": int(common),
                "apto_com_filtro_de_votos": int(vote_eligible),
                "sinal_oposto": int(flip),
                "mudanca_pelo_menos_020": int(large),
                "sem_coeficiente": int(r0 is None or r1 is None),
            })
    if seen != expected:
        raise RuntimeError("Faltam pares em " + office + ": "
                           + str(len(expected - seen)))
    return rows, {"path": str(source_file), "sha256": digest,
                  "expected_pairs": len(expected)}


def summaries(rows):
    per_office = defaultdict(Counter)
    per_uf = defaultdict(Counter)
    for row in rows:
        for counter in (per_office[row["cargo"]],
                        per_uf[(row["cargo"], row["UF"])]):
            counter["pares"] += 1
            counter["aptos_comuns"] += row["apto_criterios_comuns"]
            counter["aptos_filtro_votos"] += row["apto_com_filtro_de_votos"]
            counter["sem_coeficiente"] += row["sem_coeficiente"]
            counter["sinais_opostos"] += row["sinal_oposto"]
            counter["mudancas_020"] += row["mudanca_pelo_menos_020"]
            if row["apto_com_filtro_de_votos"]:
                r = row["r_ajustado"]
                counter["ajustados_positivos_010"] += r >= 0.1
                counter["ajustados_negativos_010"] += r <= -0.1
                counter["ajustados_entre_menos010_e_010"] += -0.1 < r < 0.1
    fields = ["pares", "aptos_comuns", "aptos_filtro_votos",
              "sem_coeficiente", "sinais_opostos", "mudancas_020",
              "ajustados_positivos_010", "ajustados_negativos_010",
              "ajustados_entre_menos010_e_010"]
    totals = {kind: {field: values.get(field, 0) for field in fields}
              for kind, values in sorted(per_office.items())}
    regions = [{"cargo": kind, "UF": uf,
                **{field: values.get(field, 0) for field in fields}}
               for (kind, uf), values in sorted(per_uf.items())]
    return totals, regions, ["cargo", "UF", *fields]


def run(root, min_sections=1000, min_zones=10, min_senate_votes=1000):
    if min(min_sections, min_zones, min_senate_votes) < 1:
        raise ValueError("Minimos de cobertura devem ser positivos")
    fingerprint, folder, found = locate(root)
    results = []
    origin = {}
    for office in ("governador", "senador"):
        path, obj = found[office]
        lines, trace = inspect_one(
            path, obj, office, min_sections=min_sections,
            min_zones=min_zones, min_senate_votes=min_senate_votes)
        results.extend(lines)
        origin[office] = trace
    totals, by_uf, fields = summaries(results)
    target_dir = folder / "diagnostico_conjunto"
    target_dir.mkdir(exist_ok=True)
    details_path = target_dir / "todos_os_pares.csv"
    uf_path = target_dir / "por_uf_cargo.csv"
    atomic_csv(details_path, DETAIL_FIELDS, sorted(
        results, key=lambda r: (
            r["cargo"], r["UF"], r["presidente"], r["candidato"])))
    atomic_csv(uf_path, fields, by_uf)
    output = {
        "version": VERSION, "status": "DESCRITIVO_CONCLUIDO",
        "fingerprint": fingerprint, "sources": origin,
        "pairs": len(results),
        "thresholds_exploratorios": {
            "min_sections": min_sections, "min_zones": min_zones,
            "min_senate_votes": min_senate_votes,
            "robust_sign_flip": "|r_bruto|>=0.1 e |r_ajustado|>=0.1 em sinais contrarios",
            "large_shift": "|r_bruto-r_ajustado|>=0.2",
        },
        "totals_by_office": totals,
        "outputs": {
            "todos_os_pares.csv": sha256(details_path),
            "por_uf_cargo.csv": sha256(uf_path),
        },
        "interpretation": (
            "Descritivo, exploratorio e sem significancia estatistica "
            "calibrada. Governador usa participacao em votos validos do cargo; "
            "Senado usa votos por eleitor com duas vagas e inclui branco/nulo "
            "no denominador; coeficientes de cargos nao sao diretamente "
            "equivalentes. Nao identifica voto individual, nao demonstra fraude."),
    }
    dest = target_dir / "summary.json"
    tmp = Path(str(dest) + ".part")
    try:
        tmp.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8")
        os.replace(tmp, dest)
    finally:
        if tmp.exists():
            tmp.unlink()
    print("DIAGNOSTICO CONJUNTO PRESIDENTE X GOVERNADOR E SENADO CONCLUIDO")
    print(json.dumps({"pares": len(results),
                      "totais_por_cargo": totals,
                      "por_uf": [
                          {"cargo": row["cargo"], "UF": row["UF"],
                           "sinais_opostos": row["sinais_opostos"],
                           "mudancas_020": row["mudancas_020"]}
                          for row in by_uf if row["sinais_opostos"] or row["mudancas_020"]
                      ],
                      "relatorio": str(dest)},
                     indent=2, ensure_ascii=False), flush=True)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", help="Acervo raiz (Windows: H:)")
    parser.add_argument("--min-sections", type=int, default=1000)
    parser.add_argument("--min-zones", type=int, default=10)
    parser.add_argument("--min-senate-votes", type=int, default=1000)
    args = parser.parse_args()
    run(root_path(args.root), args.min_sections,
        args.min_zones, args.min_senate_votes)


if __name__ == "__main__":
    main()
