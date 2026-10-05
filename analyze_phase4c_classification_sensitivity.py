#!/usr/bin/env python3
"""Fase 4C — sensibilidade da classificação ideológica.

Objetivo
=======
Testar se os achados da Fase 4B dependem fortemente da fronteira escolhida
entre "direita", "centro-direita" e "centro".

Entrada
=======
- data/forensics/analysis/phase4b_candidate_inventory.csv
- data/forensics/analysis/phase4b_uf_blocks.csv

Cenários
========
1) strict_symmetric
   Gov: direita
   Pres: direita

2) broad_symmetric
   Gov: direita + centro-direita
   Pres: direita + centro-direita
   (reproduz a Fase 4B)

3) nonleft_symmetric
   Gov: direita + centro-direita + centro
   Pres: direita + centro-direita + centro

4) stress_min_violation
   Gov: direita
   Pres: direita + centro-direita + centro

O cenário 4 é propositalmente assimétrico e conservador para a hipótese de
"violação": reduz o conjunto de Governador-direita e amplia ao máximo o
conjunto de Presidente-direita dentro da taxonomia da fonte. Se G > P ainda
assim, o resultado é robusto à fronteira direita/CD/centro adotada aqui.

Para cada UF e cenário:
- G = votos válidos no bloco de Governador do cenário;
- P = votos válidos no bloco presidencial do cenário;
- L = Lula;
- N = comparecimento presidencial oficial.

Métricas:
- violação mínima: max(0, G - P)
- overlap mínimo Gov-bloco x Lula: max(0, G + L - N)

Nota sobre comparecimento
=========================
O comparecimento presidencial pode ser maior que o de Governador porque
eleitores em trânsito fora do estado de domicílio votam apenas para Presidente.
Usar N = comparecimento presidencial cria um universo maior e, portanto,
torna o limite Gov x Lula mais conservador (menor ou igual ao que resultaria
de um universo restrito aos elegíveis a Governador).

Saídas
======
- data/forensics/analysis/phase4c_sensitivity_by_uf.csv
- data/forensics/analysis/phase4c_summary.json
"""

import csv
import json
import os
from collections import defaultdict
from pathlib import Path

ROOT = Path("data/forensics/analysis")
INVENTORY = ROOT / "phase4b_candidate_inventory.csv"
UF_BLOCKS = ROOT / "phase4b_uf_blocks.csv"
OUT_CSV = ROOT / "phase4c_sensitivity_by_uf.csv"
OUT_JSON = ROOT / "phase4c_summary.json"

SCENARIOS = {
    "strict_symmetric": {
        "gov_fields": {"direita"},
        "pres_fields": {"direita"},
        "description": "direita em ambos os cargos",
    },
    "broad_symmetric": {
        "gov_fields": {"direita", "centro-direita"},
        "pres_fields": {"direita", "centro-direita"},
        "description": "direita + centro-direita em ambos",
    },
    "nonleft_symmetric": {
        "gov_fields": {"direita", "centro-direita", "centro"},
        "pres_fields": {"direita", "centro-direita", "centro"},
        "description": "direita + centro-direita + centro em ambos",
    },
    "stress_min_violation": {
        "gov_fields": {"direita"},
        "pres_fields": {"direita", "centro-direita", "centro"},
        "description": (
            "teste conservador: Governador somente direita; Presidente inclui "
            "direita + centro-direita + centro"
        ),
    },
}


def truthy(s):
    return str(s).strip().lower() in {"1", "true", "yes", "y", "sim"}


def pct(a, b):
    return 100.0 * a / b if b else None


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    with tmp.open("wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def write_csv_atomic(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    try:
        with tmp.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def main():
    if not INVENTORY.exists() or not UF_BLOCKS.exists():
        raise RuntimeError(
            "Entradas da Fase 4B ausentes. Execute primeiro "
            "analyze_phase4b_full_right_blocks.py."
        )

    inventory = []
    with INVENTORY.open("r", encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if not truthy(r.get("is_valid_candidate_vote")):
                continue
            r["votes"] = int(r["votes"])
            inventory.append(r)

    base = {}
    with UF_BLOCKS.open("r", encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            base[r["uf"]] = {
                "president_turnout": int(r["president_turnout"]),
                "governor_turnout": int(r["governor_turnout"]),
                "lula_votes": int(r["lula_votes"]),
                "turnout_difference_gov_minus_pres": int(
                    r["turnout_difference_gov_minus_pres"]
                ),
            }

    by = defaultdict(list)
    for r in inventory:
        by[(r["uf"], r["office"])].append(r)

    rows = []
    scenario_summaries = {}

    for scenario, cfg in SCENARIOS.items():
        scenario_rows = []

        for uf in sorted(base):
            gov_rows = by[(uf, "Governor")]
            pres_rows = by[(uf, "President")]

            g = sum(
                r["votes"] for r in gov_rows
                if r["field_classification"] in cfg["gov_fields"]
            )
            p = sum(
                r["votes"] for r in pres_rows
                if r["field_classification"] in cfg["pres_fields"]
            )

            n = base[uf]["president_turnout"]
            l = base[uf]["lula_votes"]

            min_violation = max(0, g - p)
            min_lula = max(0, g + l - n)

            row = {
                "scenario": scenario,
                "scenario_description": cfg["description"],
                "uf": uf,
                "gov_fields": "+".join(sorted(cfg["gov_fields"])),
                "pres_fields": "+".join(sorted(cfg["pres_fields"])),
                "governor_block_votes": g,
                "president_block_votes": p,
                "lula_votes": l,
                "president_turnout": n,
                "governor_turnout": base[uf]["governor_turnout"],
                "turnout_difference_gov_minus_pres": (
                    base[uf]["turnout_difference_gov_minus_pres"]
                ),
                "min_alignment_violation": min_violation,
                "min_alignment_violation_pct_of_governor_block": pct(
                    min_violation, g
                ),
                "min_overlap_governor_block_x_lula": min_lula,
                "min_overlap_lula_pct_of_governor_block": pct(min_lula, g),
            }
            rows.append(row)
            scenario_rows.append(row)

        viol = [r for r in scenario_rows if r["min_alignment_violation"] > 0]
        lula = [
            r for r in scenario_rows
            if r["min_overlap_governor_block_x_lula"] > 0
        ]

        scenario_summaries[scenario] = {
            "description": cfg["description"],
            "gov_fields": sorted(cfg["gov_fields"]),
            "pres_fields": sorted(cfg["pres_fields"]),
            "ufs_with_min_alignment_violation": len(viol),
            "ufs_with_forced_lula_overlap": len(lula),
            "sum_min_alignment_violation": sum(
                r["min_alignment_violation"] for r in viol
            ),
            "sum_min_lula_overlap": sum(
                r["min_overlap_governor_block_x_lula"] for r in lula
            ),
            "top_alignment_violation": sorted(
                viol,
                key=lambda r: r["min_alignment_violation"],
                reverse=True,
            )[:15],
            "top_forced_lula_overlap": sorted(
                lula,
                key=lambda r: r["min_overlap_governor_block_x_lula"],
                reverse=True,
            )[:15],
        }

    # Robustness: UFs with positive violation in every symmetric scenario.
    symmetric = [
        "strict_symmetric",
        "broad_symmetric",
        "nonleft_symmetric",
    ]
    by_scenario_uf = {
        (r["scenario"], r["uf"]): r
        for r in rows
    }

    robust_all_symmetric = []
    stress_positive = []
    for uf in sorted(base):
        if all(
            by_scenario_uf[(s, uf)]["min_alignment_violation"] > 0
            for s in symmetric
        ):
            robust_all_symmetric.append(uf)

        if (
            by_scenario_uf[
                ("stress_min_violation", uf)
            ]["min_alignment_violation"] > 0
        ):
            stress_positive.append(uf)

    summary = {
        "format": "tse-forensics-phase4c-classification-sensitivity-v1",
        "inputs": [str(INVENTORY), str(UF_BLOCKS)],
        "scenarios": scenario_summaries,
        "robustness": {
            "ufs_positive_in_all_symmetric_scenarios": robust_all_symmetric,
            "n_positive_in_all_symmetric_scenarios": len(
                robust_all_symmetric
            ),
            "ufs_positive_even_in_stress_min_violation": stress_positive,
            "n_positive_even_in_stress_min_violation": len(stress_positive),
        },
        "turnout_note": {
            "all_ufs_president_turnout_ge_governor": all(
                v["president_turnout"] >= v["governor_turnout"]
                for v in base.values()
            ),
            "total_president_minus_governor_turnout": sum(
                v["president_turnout"] - v["governor_turnout"]
                for v in base.values()
            ),
            "interpretation": (
                "Compatível com voto em trânsito: fora da UF de domicílio, "
                "a pessoa vota apenas para Presidente. O uso do comparecimento "
                "presidencial como N é conservador para o limite Gov x Lula."
            ),
        },
        "limitations": [
            (
                "Os cenários usam a taxonomia de campos da fonte; não resolvem "
                "disputas sobre a classificação ideológica de candidatos individuais."
            ),
            (
                "O cenário stress_min_violation é propositalmente assimétrico e "
                "serve apenas como teste de robustez, não como definição política."
            ),
            (
                "Somatórios de mínimos entre UFs são descritivos; cada UF é um "
                "universo eleitoral separado."
            ),
        ],
    }

    fields = [
        "scenario","scenario_description","uf","gov_fields","pres_fields",
        "governor_block_votes","president_block_votes","lula_votes",
        "president_turnout","governor_turnout",
        "turnout_difference_gov_minus_pres",
        "min_alignment_violation",
        "min_alignment_violation_pct_of_governor_block",
        "min_overlap_governor_block_x_lula",
        "min_overlap_lula_pct_of_governor_block",
    ]
    write_csv_atomic(OUT_CSV, rows, fields)
    atomic_write(
        OUT_JSON,
        json.dumps(summary, ensure_ascii=False, indent=2).encode("utf-8"),
    )

    print("\nFASE 4C — sensibilidade da classificação ideológica")
    for name in SCENARIOS:
        s = scenario_summaries[name]
        print(
            f"- {name}: violação mínima em "
            f"{s['ufs_with_min_alignment_violation']} UFs · "
            f"Gov×Lula mínimo em {s['ufs_with_forced_lula_overlap']} UFs"
        )
    print(
        "- positivas em TODOS os cenários simétricos: "
        f"{len(robust_all_symmetric)} · "
        f"{', '.join(robust_all_symmetric) if robust_all_symmetric else 'nenhuma'}"
    )
    print(
        "- positivas até no stress test Gov=direita / Pres=não-esquerda: "
        f"{len(stress_positive)} · "
        f"{', '.join(stress_positive) if stress_positive else 'nenhuma'}"
    )
    print(f"- CSV: {OUT_CSV}")
    print(f"- resumo: {OUT_JSON}")


if __name__ == "__main__":
    main()
