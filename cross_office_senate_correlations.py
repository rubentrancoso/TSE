#!/usr/bin/env python3
"""Correlacao ecologica de voto presidencial e voto no Senado (2026).

Duas escolhas para senador por eleitor: taxa de apoio de um senador
= votos desse candidato / (total de votos senatoriais da secao / 2).
Denominador presidencial = todos os votos para Presidente, inclusive
brancos/nulos. NAO inferir combinacoes individuais de voto.

Le somente CSVs de BU por candidato ja extraidos, com SHA-256 verificado;
nao abre SQLite ou muda arquivos originais.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import json
import os
from pathlib import Path

from cross_office_candidate_correlations import Moments, pearson, rows, source
from reconcile_stream import sha256
from urnas import root_path

VERSION = "cross-office-senate-v1"
INVALID = {"95", "96"}
COLS = ("UF", "turno", "presidente", "senador", "secoes_com_dois_cargos",
        "correlacao_bruta_pearson", "correlacao_dentro_municipio_zona",
        "zonas_com_variacao", "votos_senador", "interpretacao")


def select_candidates(paths, turn, max_senators):
    presidential = Counter()
    senators = defaultdict(Counter)
    total_keys = 0
    for i, path in enumerate(paths, 1):
        for record in rows(path):
            total_keys += 1
            if record["turno"] != turn or record["cargo"] not in ("1", "5"):
                continue
            candidate = record["votavel"]
            if candidate in INVALID:
                continue
            votes = int(record["votos_BU"])
            if votes < 0:
                raise RuntimeError("Numero de votos negativo na entrada")
            if record["cargo"] == "1":
                presidential[candidate] += votes
            else:
                senators[record["UF"]][candidate] += votes
        if i <= 2 or i % 20 == 0 or i == len(paths):
            print(f"[SENADO RANKING {i}/{len(paths)}] "
                  f"{total_keys:,} linhas validadas", flush=True)
    selected_president = [candidate for candidate, _ in presidential.most_common(2)]
    if len(selected_president) != 2:
        raise RuntimeError("Dois presidenciaveis nao encontrados")
    selected_senators = {}
    for uf, candidates in senators.items():
        ranked = sorted(candidates, key=lambda x: (-candidates[x], 0 if x.isdecimal() else 1, int(x) if x.isdecimal() else x))
        selected_senators[uf] = ranked[:max_senators] if max_senators else ranked
    return selected_president, selected_senators, senators, total_keys


def add_centered(zone, within):
    for key, m in zone.items():
        if m.n < 2:
            continue
        xy, xx, yy = m.centered()
        current = within[key]
        current[0] += xy
        current[1] += xx
        current[2] += yy
        current[3] += 1


def compute(paths, president, senators, turn):
    raw = defaultdict(Moments)
    within = defaultdict(lambda: [0.0, 0.0, 0.0, 0])
    present = Counter()
    included = Counter()
    senator_votes = Counter()

    for i, path in enumerate(paths, 1):
        current_section = None
        current_zone = None
        zone_moments = defaultdict(Moments)
        pres_votes = {}
        sen_votes = {}
        total_pres = total_sen = 0
        has_pres = has_sen = False

        def finish_section():
            if current_section is None:
                return
            uf, _, _, _, t = current_section
            if t != turn or not has_pres or not has_sen or uf not in senators:
                return
            present[uf] += 1
            if total_pres <= 0 or total_sen <= 0 or total_sen % 2:
                return
            # Voto por candidato nao pode superar numero de pessoas
            # que fizeram duas escolhas senatoriais nessa secao.
            elig = total_sen // 2
            if any(n > elig for n in sen_votes.values()):
                raise RuntimeError("Senador excede comparecimento estimado: "
                                   + repr(current_section))
            included[uf] += 1
            for p in president:
                x = pres_votes.get(p, 0) / total_pres
                for s in senators[uf]:
                    y = sen_votes.get(s, 0) / elig
                    key = (uf, turn, p, s)
                    raw[key].add(x, y)
                    zone_moments[key].add(x, y)

        for r in rows(path):
            section = (r["UF"], r["municipio"], r["zona"], r["secao"], r["turno"])
            zone = section[:3] + (section[4],)
            if current_section != section:
                finish_section()
                if current_zone != zone:
                    add_centered(zone_moments, within)
                    zone_moments = defaultdict(Moments)
                    current_zone = zone
                current_section = section
                pres_votes, sen_votes = {}, {}
                total_pres = total_sen = 0
                has_pres = has_sen = False
            if r["turno"] != turn:
                continue
            cargo, candidate = r["cargo"], r["votavel"]
            if cargo not in ("1", "5"):
                continue
            n = int(r["votos_BU"])
            if n < 0:
                raise RuntimeError("Numero de votos negativo na entrada")
            if cargo == "1":
                has_pres = True
                total_pres += n
                if candidate in president:
                    pres_votes[candidate] = pres_votes.get(candidate, 0) + n
            else:
                has_sen = True
                total_sen += n
                if candidate not in INVALID:
                    senator_votes[(r["UF"], candidate)] += n
                if candidate in senators.get(r["UF"], ()):
                    sen_votes[candidate] = sen_votes.get(candidate, 0) + n
        finish_section()
        add_centered(zone_moments, within)
        if i <= 2 or i % 20 == 0 or i == len(paths):
            print(f"[SENADO PARES {i}/{len(paths)}] "
                  f"secoes aproveitadas={sum(included.values()):,}", flush=True)
    return raw, within, present, included, senator_votes


def results_table(raw, within, candidate_votes):
    data = []
    for key in sorted(raw):
        uf, turn, p, s = key
        raw_coeff = pearson(raw[key].centered())
        local = within[key]
        adjusted = pearson(local[:3])
        data.append({
            "UF": uf, "turno": turn, "presidente": p, "senador": s,
            "secoes_com_dois_cargos": raw[key].n,
            "correlacao_bruta_pearson": (
                round(raw_coeff, 6) if raw_coeff is not None else ""),
            "correlacao_dentro_municipio_zona": (
                round(adjusted, 6) if adjusted is not None else ""),
            "zonas_com_variacao": local[3],
            "votos_senador": candidate_votes[(uf, s)],
            "interpretacao": (
                "Fracoes de eleitores por cargo; Senado usa duas escolhas. "
                "Correlacao de secoes nao identifica voto individual nem fraude."),
        })
    return data


def run(root, turn="1", max_senators=0):
    if max_senators < 0 or max_senators > 200:
        raise ValueError("--top-senators deve ser 0 (todos) ou 1..200")
    folder, original, paths = source(root)
    print("SENADO: BU originais derivados de particoes SHA-256 verificadas",
          flush=True)
    pres, selected, candidate_votes, count = select_candidates(
        paths, turn, max_senators)
    if count != original["candidate_keys"]:
        raise RuntimeError(f"Linhas BU esperadas {original['candidate_keys']}, "
                           f"obtidas {count}")
    print("Presidenciaveis:", pres,
          "| UFs senador:", len(selected),
          "| candidaturas ao Senado:",
          sum(len(v) for v in selected.values()), flush=True)
    raw, within, present, valid, votes = compute(paths, pres, selected, turn)
    table = results_table(raw, within, votes)
    dest = folder / "correlacao_presidente_senado"
    dest.mkdir(exist_ok=True)
    output = dest / "pares_por_uf.csv"
    tmp = Path(str(output) + ".part")
    try:
        with tmp.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=COLS, delimiter=";",
                                    lineterminator="\n")
            writer.writeheader()
            writer.writerows(table)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, output)
    finally:
        if tmp.exists():
            tmp.unlink()
    report = {
        "version": VERSION, "status": "DESCRITIVO_CONCLUIDO",
        "fingerprint": original["source_fingerprint"], "turno": turn,
        "presidente_top2": pres,
        "senadores_por_uf": {uf: list(items) for uf, items in sorted(selected.items())},
        "senadores_total": sum(len(items) for items in selected.values()),
        "candidate_keys_checked": count,
        "paired_sections_by_uf": dict(sorted(present.items())),
        "valid_sections_by_uf": dict(sorted(valid.items())),
        "pairs_compared": len(table),
        "csv": str(output), "csv_sha256": sha256(output),
        "denominators": {
            "presidente": "votos presidenciais totais, incluidos 95 branco e 96 nulo",
            "senador": "(total de votos senatoriais incluindo branco e nulo)/2",
        },
        "limitations": [
            "Dados agregados por secao, sem informacao de combinacao individual de votos",
            "Correlacao bruta confunde diferencas territoriais; controle de zona e descritivo",
            "Numero de votos senatoriais pode ser 2 vezes o eleitorado habilitado",
            "Apoio de candidato ao Senado nao e soma de votos de varios senadores",
            "Nao classifica bloco ideologico nem constitui evidencia isolada de fraude",
        ],
    }
    summary = dest / "summary.json"
    temp_summary = Path(str(summary) + ".part")
    try:
        temp_summary.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        os.replace(temp_summary, summary)
    finally:
        if temp_summary.exists():
            temp_summary.unlink()
    print("CORRELACAO PRESIDENCIA X SENADO CONCLUIDA")
    print(json.dumps({
        "presidenciaveis": pres,
        "senadores_total": report["senadores_total"],
        "secoes_pareadas": sum(present.values()),
        "secoes_com_percentuais": sum(valid.values()),
        "pares": len(table),
        "csv": str(output), "sha256": report["csv_sha256"],
    }, indent=2, ensure_ascii=False), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", help="Diretorio do acervo H:")
    parser.add_argument("--top-senators", type=int, default=0,
                        help="0=todas candidaturas (padrao); N=top N por UF")
    args = parser.parse_args()
    run(root_path(args.root), max_senators=args.top_senators)


if __name__ == "__main__":
    main()
