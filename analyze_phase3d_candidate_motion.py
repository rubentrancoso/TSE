#!/usr/bin/env python3
"""Fase 3D — movimento dos candidatos nos grandes lotes presidenciais.

Testa a observação de que, quando o agregado nacional de Presidente voltou a
ser atualizado, apenas os dois primeiros colocados teriam mudado de forma
material enquanto os demais teriam ficado praticamente parados.

Fonte temporal:
  ArvorCo/PNAD, linha_do_tempo.json, commit fixado.

O teste é descritivo e reprodutível:
- calcula deltas absolutos por grupo de candidatos nos dois grandes lotes;
- calcula participação de cada grupo no lote;
- compara a participação do lote com a participação acumulada imediatamente
  antes do lote;
- mede o movimento conjunto dos candidatos fora do top 2.

Não usa teste de hipótese ingênuo de multinomial, porque as seções não chegam
em ordem aleatória: a composição geográfica do lote importa.

Saídas:
  data/forensics/analysis/phase3d_candidate_batches.csv
  data/forensics/analysis/phase3d_candidate_motion_summary.json
"""

import csv
import json
import hashlib
import os
import urllib.request
from pathlib import Path

ROOT = Path("data/forensics")
RAW = ROOT / "external" / "ArvorCo-PNAD"
OUT = ROOT / "analysis"

COMMIT = "beb3bec9ae5c25e2868ee2f2cefb9e6dccd91415"
URL = (
    "https://raw.githubusercontent.com/ArvorCo/PNAD/"
    f"{COMMIT}/analysis/apuracao_2026/dados/linha_do_tempo.json"
)
RAW_PATH = RAW / COMMIT / "linha_do_tempo.json"
UA = "TSE-forensics-phase3d/1.0"

GROUPS = [
    ("flavio", "Flávio Bolsonaro", True),
    ("lula", "Lula", True),
    ("cury", "Augusto Cury", False),
    ("renan", "Renan Santos", False),
    ("caiado", "Ronaldo Caiado", False),
    ("outros", "Demais candidatos agrupados", False),
]

TARGET_UPDATES = [
    ("catchup_1", "2026-10-04 19:14:08"),
    ("catchup_2", "2026-10-04 20:04:39"),
]


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    with tmp.open("wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def fetch():
    if RAW_PATH.exists() and RAW_PATH.stat().st_size:
        data = RAW_PATH.read_bytes()
        reused = True
    else:
        req = urllib.request.Request(
            URL, headers={"User-Agent": UA, "Cache-Control": "no-cache"}
        )
        with urllib.request.urlopen(req, timeout=90) as r:
            data = r.read()
        atomic_write(RAW_PATH, data)
        reused = False
    return json.loads(data.decode("utf-8-sig")), {
        "url": URL,
        "path": str(RAW_PATH),
        "sha256": sha256(data),
        "bytes": len(data),
        "reused": reused,
    }


def table_rows(table):
    cols = table.get("colunas", [])
    return [dict(zip(cols, row)) for row in table.get("linhas", [])]


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def pct(num, den):
    return 100.0 * num / den if den else 0.0


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data, source = fetch()
    rows = table_rows(data["nacional"]["versoes"])
    by_time = {r.get("gerado_brt"): r for r in rows}

    out = []
    summaries = []

    for batch_name, end_time in TARGET_UPDATES:
        end = by_time.get(end_time)
        if not end:
            raise RuntimeError(f"Atualização não encontrada: {end_time}")

        d_vv = int(end["d_vv"])
        previous_vv = int(end["vv"]) - d_vv

        top2_delta = 0
        minor_delta = 0
        group_rows = []

        for key, label, top2 in GROUPS:
            end_votes = int(end[key])
            delta_votes = int(end[f"d_{key}"])
            start_votes = end_votes - delta_votes

            prior_share = pct(start_votes, previous_vv)
            batch_share = pct(delta_votes, d_vv)
            expected_at_prior_share = d_vv * prior_share / 100.0
            observed_minus_expected = delta_votes - expected_at_prior_share

            row = {
                "batch": batch_name,
                "generated_brt": end_time,
                "candidate_group": key,
                "candidate_label": label,
                "is_top2": "yes" if top2 else "no",
                "start_votes": start_votes,
                "end_votes": end_votes,
                "delta_votes": delta_votes,
                "growth_pct_vs_start": pct(delta_votes, start_votes),
                "prior_cumulative_share_pct": prior_share,
                "batch_share_pct": batch_share,
                "batch_minus_prior_share_pp": batch_share - prior_share,
                "expected_votes_if_prior_share": round(expected_at_prior_share, 3),
                "observed_minus_expected": round(observed_minus_expected, 3),
                "observed_expected_ratio": (
                    delta_votes / expected_at_prior_share
                    if expected_at_prior_share else None
                ),
            }
            group_rows.append(row)
            if top2:
                top2_delta += delta_votes
            else:
                minor_delta += delta_votes

        out.extend(group_rows)
        summaries.append({
            "batch": batch_name,
            "generated_brt": end_time,
            "sections_added": int(end["d_st"]),
            "valid_votes_added": d_vv,
            "top2_votes_added": top2_delta,
            "non_top2_votes_added": minor_delta,
            "top2_share_of_batch_pct": pct(top2_delta, d_vv),
            "non_top2_share_of_batch_pct": pct(minor_delta, d_vv),
            "non_top2_groups_with_zero_delta": sum(
                1 for r in group_rows
                if r["is_top2"] == "no" and r["delta_votes"] == 0
            ),
            "smallest_non_top2_delta": min(
                r["delta_votes"] for r in group_rows if r["is_top2"] == "no"
            ),
            "largest_non_top2_delta": max(
                r["delta_votes"] for r in group_rows if r["is_top2"] == "no"
            ),
        })

    fields = [
        "batch","generated_brt","candidate_group","candidate_label","is_top2",
        "start_votes","end_votes","delta_votes","growth_pct_vs_start",
        "prior_cumulative_share_pct","batch_share_pct",
        "batch_minus_prior_share_pp","expected_votes_if_prior_share",
        "observed_minus_expected","observed_expected_ratio"
    ]
    write_csv(OUT / "phase3d_candidate_batches.csv", out, fields)

    summary = {
        "format": "tse-forensics-phase3d-candidate-motion-v1",
        "source": source,
        "batches": summaries,
        "interpretation_rules": [
            (
                "Delta absoluto pequeno em candidato pequeno não implica ausência de "
                "movimento; comparar também a participação no lote."
            ),
            (
                "Estabilidade percentual dos candidatos menores pode coexistir com "
                "centenas de milhares de votos adicionais se sua participação no lote "
                "for parecida com a participação acumulada anterior."
            ),
            (
                "A comparação 'esperado se mantivesse a participação anterior' é "
                "descritiva, não um teste probabilístico válido, porque os lotes têm "
                "composição geográfica não aleatória."
            ),
            (
                "Qualquer alegação de anomalia estatística forte deve depois ser "
                "condicionada por UF/município/seção."
            ),
        ],
    }
    (OUT / "phase3d_candidate_motion_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("\nFASE 3D — movimento dos candidatos nos lotes presidenciais")
    for b in summaries:
        print(
            f"- {b['batch']} @ {b['generated_brt']}: "
            f"{b['valid_votes_added']:,} válidos · "
            f"top2 {b['top2_share_of_batch_pct']:.3f}% · "
            f"demais {b['non_top2_share_of_batch_pct']:.3f}% · "
            f"demais com delta zero: {b['non_top2_groups_with_zero_delta']}"
        )
    print(f"- CSV: {OUT / 'phase3d_candidate_batches.csv'}")
    print(f"- resumo: {OUT / 'phase3d_candidate_motion_summary.json'}")


if __name__ == "__main__":
    main()
