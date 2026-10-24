#!/usr/bin/env python3
"""Revisao dos pares com inversao geograficamente ajustada.

Le APENAS os CSVs pequenos do diagnostico conjunto (778 pares) e
seus resumos. Nao reprocessa BU nem acessa SQLite.
Registra candidaturas e coeficientes, sem inferir voto individual,
fraude ou transferencias politicas.
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

VERSION = "review-cross-office-correlations-v1"
FIELDS = (
    "cargo", "UF", "turno", "presidente", "candidato",
    "secoes", "grupos_geograficos_com_variacao",
    "votos_candidato_disponiveis", "r_bruto", "r_ajustado",
    "abs_mudanca", "apto_criterios_comuns", "apto_com_filtro_de_votos",
    "sinal_oposto", "mudanca_pelo_menos_020", "sem_coeficiente",
)


def atomic_csv(path, fields, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(path) + ".part")
    try:
        with temp.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(
                file, fieldnames=fields, delimiter=";",
                lineterminator="\n")
            writer.writeheader()
            writer.writerows(data)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def locate(root):
    base = root / "analysis"
    national = json.loads(
        (base / "reconciliacao_bu_secao.summary.json").read_text("utf-8"))
    fp = national["fingerprint"]
    results = []
    for report in (base / "entre_cargos").glob("*/diagnostico_conjunto/summary.json"):
        item = json.loads(report.read_text("utf-8"))
        if (item.get("fingerprint") == fp and
                item.get("status") == "DESCRITIVO_CONCLUIDO"):
            results.append((report, item))
    if len(results) != 1:
        raise RuntimeError("Esperado um unico diagnostico do fingerprint: "
                           + str(len(results)))
    return results[0]


def _finite_float(value, field):
    if value is None or str(value).strip() == "":
        return None
    v = float(value)
    if not math.isfinite(v) or abs(v) > 1.000001:
        raise RuntimeError("Coeficiente invalido: " + field)
    return v


def inspect_rows(path, metadata):
    if sha256(path) != metadata["outputs"]["todos_os_pares.csv"]:
        raise RuntimeError("SHA-256 nao confere: todos_os_pares.csv")
    rows = []
    seen = set()
    totals = defaultdict(Counter)
    thresholds = metadata.get("thresholds_exploratorios", {})
    min_sections = int(thresholds.get("min_sections", 1000))
    min_zones = int(thresholds.get("min_zones", 10))
    min_votes = int(thresholds.get("min_senate_votes", 1000))
    if min(min_sections, min_zones, min_votes) < 1:
        raise RuntimeError("Limiares invalidos no relatorio original")
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, delimiter=";")
        if not set(FIELDS).issubset(reader.fieldnames or ()):
            raise RuntimeError("CSV com colunas ausentes")
        for line in reader:
            if line["cargo"] not in ("senador", "governador"):
                raise RuntimeError("Cargo invalido em CSV")
            key = (line["cargo"], line["UF"], line["turno"],
                   line["presidente"], line["candidato"])
            if key in seen:
                raise RuntimeError("Par duplicado: " + repr(key))
            seen.add(key)
            n = int(line["secoes"])
            z = int(line["grupos_geograficos_com_variacao"])
            if n < 0 or z < 0 or z > n:
                raise RuntimeError("Contagens impossiveis em par " + repr(key))
            senator = line["cargo"] == "senador"
            v = int(line["votos_candidato_disponiveis"]) if senator else None
            if senator and v < 0:
                raise RuntimeError("Votos negativos na linha " + repr(key))
            raw = _finite_float(line["r_bruto"], "r_bruto")
            adjusted = _finite_float(line["r_ajustado"], "r_ajustado")
            common = int(n >= min_sections and z >= min_zones
                         and raw is not None and adjusted is not None)
            eligible = int(common and (not senator or v >= min_votes))
            flip = int(eligible and abs(raw) >= .1 and abs(adjusted) >= .1
                       and raw * adjusted < 0)
            shift = int(eligible and abs(raw - adjusted) >= .2)
            missing = int(raw is None or adjusted is None)
            for label, expected in (
                ("apto_criterios_comuns", common),
                ("apto_com_filtro_de_votos", eligible),
                ("sinal_oposto", flip),
                ("mudanca_pelo_menos_020", shift),
                ("sem_coeficiente", missing),
            ):
                if int(line[label]) != expected:
                    raise RuntimeError("Marcador inconsistente " + label
                                       + " em " + repr(key))
            if raw is not None and adjusted is not None:
                difference = abs(raw - adjusted)
                if abs(float(line["abs_mudanca"]) - difference) > 1.5e-6:
                    raise RuntimeError("Magnitude inconsistente: " + repr(key))
            elif line["abs_mudanca"] != "":
                raise RuntimeError("Magnitude com coeficiente ausente")
            totals[line["cargo"]]["pares"] += 1
            totals[line["cargo"]]["sinais_opostos"] += flip
            totals[line["cargo"]]["mudancas_020"] += shift
            totals[line["cargo"]]["aptos_comuns"] += common
            totals[line["cargo"]]["aptos_filtro_votos"] += eligible
            rows.append(dict(line))
    if len(rows) != metadata.get("pairs"):
        raise RuntimeError("Total de pares diferente do resumo")
    for office, expected in metadata["totals_by_office"].items():
        for item in ("pares", "sinais_opostos", "mudancas_020",
                     "aptos_comuns", "aptos_filtro_votos"):
            if totals[office][item] != expected[item]:
                raise RuntimeError("Resumo de " + office + " difere em " + item)
    return rows, totals


def run(root):
    source_report, report = locate(root)
    source_dir = source_report.parent
    all_pairs = source_dir / "todos_os_pares.csv"
    regions = source_dir / "por_uf_cargo.csv"
    if sha256(regions) != report["outputs"]["por_uf_cargo.csv"]:
        raise RuntimeError("SHA-256 nao confere: por_uf_cargo.csv")
    for kind, entry in report.get("sources", {}).items():
        original = Path(entry["path"])
        if not original.is_file() or sha256(original) != entry["sha256"]:
            raise RuntimeError("Origem " + kind + " alterada: " + str(original))
    rows, totals = inspect_rows(all_pairs, report)
    reversed_senate = sorted(
        (r for r in rows if r["cargo"] == "senador" and
         r["sinal_oposto"] == "1"),
        key=lambda r: (r["UF"], r["candidato"], r["presidente"]))
    reverse_governor = [
        r for r in rows if r["cargo"] == "governador" and r["sinal_oposto"] == "1"]
    shifts = sorted(
        (r for r in rows if r["mudanca_pelo_menos_020"] == "1"),
        key=lambda r: (-float(r["abs_mudanca"]),
                       r["cargo"], r["UF"], r["candidato"], r["presidente"]))
    uf_candidates = defaultdict(set)
    uf_pairs = Counter()
    for row in reversed_senate:
        uf_pairs[row["UF"]] += 1
        uf_candidates[row["UF"]].add(row["candidato"])
    states = sorted({r["UF"] for r in rows if r["cargo"] == "senador"})
    by_uf = [{"UF": uf, "pares_invertidos": uf_pairs[uf],
              "senadores_distintos": len(uf_candidates[uf])}
             for uf in states]

    output_dir = source_dir / "revisao_inversoes"
    output_dir.mkdir(exist_ok=True)
    senate_path = output_dir / "senado_pares_invertidos.csv"
    shifts_path = output_dir / "mudancas_020.csv"
    regions_path = output_dir / "senado_por_uf.csv"
    atomic_csv(senate_path, FIELDS, reversed_senate)
    atomic_csv(shifts_path, FIELDS, shifts)
    atomic_csv(regions_path,
               ["UF", "pares_invertidos", "senadores_distintos"], by_uf)

    summary = {
        "version": VERSION, "status": "DESCRITIVO_CONCLUIDO",
        "input_fingerprint": report["fingerprint"],
        "input_pairs_sha256": report["outputs"]["todos_os_pares.csv"],
        "pares_totais": len(rows),
        "pares_senado_com_inversao": len(reversed_senate),
        "pares_governador_com_inversao": len(reverse_governor),
        "senadores_distintos_em_inversoes": sum(
            len(names) for names in uf_candidates.values()),
        "ufs_com_inversao_senado": sum(1 for c in uf_pairs.values() if c),
        "mudancas_020_totais": len(shifts),
        "senado_inversoes_por_uf": [
            r for r in by_uf if r["pares_invertidos"]],
        "senado_pares_invertidos": [
            {"UF": r["UF"], "presidente": r["presidente"],
             "senador": r["candidato"], "r_bruto": r["r_bruto"],
             "r_ajustado": r["r_ajustado"],
             "secoes": int(r["secoes"]),
             "grupos_geograficos": int(
                 r["grupos_geograficos_com_variacao"]),
             "votos_senador": int(r["votos_candidato_disponiveis"])}
            for r in reversed_senate],
        "arquivos": {
            p.name: {"sha256": sha256(p), "path": str(p)}
            for p in (senate_path, shifts_path, regions_path)},
        "limites": [
            "Pares nao sao independentes: duas candidaturas presidenciais compartilham secoes",
            "Inversao de sinal pode refletir composicao territorial (paradoxo de Simpson)",
            "Dados agregados nao revelam combinacoes de votos individuais",
            "As duas escolhas ao Senado exigem cuidado com denominadores",
            "Esta analise nao comprova adulteracao nem fraude eleitoral",
        ],
    }
    dest = output_dir / "summary.json"
    temp = Path(str(dest) + ".part")
    try:
        temp.write_text(json.dumps(summary, ensure_ascii=False, indent=2)
                        + "\n", encoding="utf-8")
        os.replace(temp, dest)
    finally:
        if temp.exists():
            temp.unlink()
    print("REVISAO DAS INVERSOES CONCLUIDA")
    print(json.dumps({
        "pares": summary["pares_totais"],
        "senado_inversoes": summary["pares_senado_com_inversao"],
        "governador_inversoes": summary["pares_governador_com_inversao"],
        "senadores_distintos": summary["senadores_distintos_em_inversoes"],
        "ufs": summary["senado_inversoes_por_uf"],
        "casos": summary["senado_pares_invertidos"],
        "relatorio": str(dest),
    }, indent=2, ensure_ascii=False), flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", help="Acervo de dados (padrao Windows H:)")
    args = parser.parse_args()
    run(root_path(args.root))


if __name__ == "__main__":
    main()
