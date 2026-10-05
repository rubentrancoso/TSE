#!/usr/bin/env python3
"""Fase 3K — efeito temporal residual de 2026 controlado pela geografia de 2022.

Objetivo:
Separar o que é "zona tardia historicamente pró-Lula" do que seria um efeito
adicional específico de 2026.

Entrada:
  data/forensics/analysis/phase3j_zone_rows.csv

Para cada zona com dados de 2022:
- margem26 = Lula - Flávio, em pp dos válidos;
- margem22 = Lula - Bolsonaro, em pp dos válidos;
- delta_margem = margem26 - margem22.

Por UF:
- Spearman(hora de conclusão, delta_margem);
- comparação do quartil que concluiu primeiro com o quartil que concluiu por
  último;
- delta-do-gradiente:
    (late-early em 2026) - (late-early em 2022).

Também é produzido um agregado nacional formado por quartis definidos DENTRO
de cada UF, para não confundir composição entre estados.

Interpretação:
- delta-do-gradiente > 0: o viés pró-Lula das zonas tardias ficou mais forte
  em 2026 que em 2022;
- delta-do-gradiente < 0: o viés tardio já existia e ficou mais fraco em 2026;
- Spearman positivo de delta_margem: zonas mais tardias se moveram mais em
  direção a Lula, relativamente a 2022.

Isto é descritivo. Mudanças de candidatos, comparecimento, terceiros e
rezoneamento podem afetar a comparação entre eleições.

Saídas:
  data/forensics/analysis/phase3k_zone_change_rows.csv
  data/forensics/analysis/phase3k_by_uf.csv
  data/forensics/analysis/phase3k_summary.json
"""

import csv
import json
import math
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path

IN = Path("data/forensics/analysis/phase3j_zone_rows.csv")
OUT = Path("data/forensics/analysis")


def mean(xs):
    return sum(xs) / len(xs) if xs else None


def median(xs):
    xs = sorted(xs)
    if not xs:
        return None
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2.0


def ranks(values):
    indexed = sorted(enumerate(values), key=lambda x: x[1])
    out = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i
        while j + 1 < len(indexed) and indexed[j + 1][1] == indexed[i][1]:
            j += 1
        rank = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            out[indexed[k][0]] = rank
        i = j + 1
    return out


def pearson(x, y):
    if len(x) < 2:
        return None
    mx, my = mean(x), mean(y)
    dx = [a - mx for a in x]
    dy = [b - my for b in y]
    den = math.sqrt(sum(a*a for a in dx) * sum(b*b for b in dy))
    if den == 0:
        return None
    return sum(a*b for a, b in zip(dx, dy)) / den


def spearman(x, y):
    return pearson(ranks(x), ranks(y)) if len(x) >= 2 else None


def margin_pp(lula, direita, validos):
    return 100.0 * (lula - direita) / validos if validos else None


def parse_dt(s):
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")


def atomic_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    try:
        with tmp.open("w", encoding="utf-8", newline="") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


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


def aggregate(rows, year):
    if year == 2026:
        vv = sum(r["validos"] for r in rows)
        l = sum(r["lula"] for r in rows)
        d = sum(r["flavio"] for r in rows)
    else:
        vv = sum(r["validos_2022_1t"] for r in rows)
        l = sum(r["lula_2022_1t"] for r in rows)
        d = sum(r["bolsonaro_2022_1t"] for r in rows)
    return {
        "validos": vv,
        "lula": l,
        "direita": d,
        "margem_lula_menos_direita_pp": margin_pp(l, d, vv),
    }


def main():
    if not IN.exists():
        raise RuntimeError(
            f"Arquivo de entrada ausente: {IN}. Execute primeiro a Fase 3J."
        )

    rows = []
    with IN.open("r", encoding="utf-8-sig", newline="") as f:
        for x in csv.DictReader(f):
            if not x.get("validos_2022_1t"):
                continue
            if not x.get("margin_lula_minus_bolsonaro_2022_pp"):
                continue

            r = {
                "uf": x["uf"],
                "cd_tse": x["cd_tse"],
                "municipio": x["municipio"],
                "zona": x["zona"],
                "completa_gerado_brt": x["completa_gerado_brt"],
                "complete_epoch": parse_dt(x["completa_gerado_brt"]).timestamp(),
                "validos": int(x["validos"]),
                "flavio": int(x["flavio"]),
                "lula": int(x["lula"]),
                "margin26_pp": float(x["margin_lula_minus_flavio_2026_pp"]),
                "validos_2022_1t": int(x["validos_2022_1t"]),
                "bolsonaro_2022_1t": int(x["bolsonaro_2022_1t"]),
                "lula_2022_1t": int(x["lula_2022_1t"]),
                "margin22_pp": float(x["margin_lula_minus_bolsonaro_2022_pp"]),
            }
            r["delta_margin_2026_minus_2022_pp"] = r["margin26_pp"] - r["margin22_pp"]
            rows.append(r)

    by_uf = defaultdict(list)
    for r in rows:
        by_uf[r["uf"]].append(r)

    uf_rows = []
    pooled_early = []
    pooled_late = []

    for uf in sorted(by_uf):
        group = sorted(by_uf[uf], key=lambda r: r["complete_epoch"])
        n = len(group)
        if n < 4:
            continue

        q = max(1, n // 4)
        early = group[:q]
        late = group[-q:]
        pooled_early.extend(early)
        pooled_late.extend(late)

        e26 = aggregate(early, 2026)
        l26 = aggregate(late, 2026)
        e22 = aggregate(early, 2022)
        l22 = aggregate(late, 2022)

        grad26 = (
            l26["margem_lula_menos_direita_pp"]
            - e26["margem_lula_menos_direita_pp"]
        )
        grad22 = (
            l22["margem_lula_menos_direita_pp"]
            - e22["margem_lula_menos_direita_pp"]
        )

        uf_rows.append({
            "uf": uf,
            "n_zonas": n,
            "spearman_complete_vs_delta_margin_pp": spearman(
                [r["complete_epoch"] for r in group],
                [r["delta_margin_2026_minus_2022_pp"] for r in group],
            ),
            "early_margin_2026_pp": e26["margem_lula_menos_direita_pp"],
            "late_margin_2026_pp": l26["margem_lula_menos_direita_pp"],
            "late_minus_early_2026_pp": grad26,
            "early_margin_2022_pp": e22["margem_lula_menos_direita_pp"],
            "late_margin_2022_pp": l22["margem_lula_menos_direita_pp"],
            "late_minus_early_2022_pp": grad22,
            "delta_of_late_gradient_2026_minus_2022_pp": grad26 - grad22,
        })

    pe26 = aggregate(pooled_early, 2026)
    pl26 = aggregate(pooled_late, 2026)
    pe22 = aggregate(pooled_early, 2022)
    pl22 = aggregate(pooled_late, 2022)

    pooled_grad26 = (
        pl26["margem_lula_menos_direita_pp"]
        - pe26["margem_lula_menos_direita_pp"]
    )
    pooled_grad22 = (
        pl22["margem_lula_menos_direita_pp"]
        - pe22["margem_lula_menos_direita_pp"]
    )

    rhos = [
        r["spearman_complete_vs_delta_margin_pp"]
        for r in uf_rows
        if r["spearman_complete_vs_delta_margin_pp"] is not None
    ]
    dgrad = [r["delta_of_late_gradient_2026_minus_2022_pp"] for r in uf_rows]

    summary = {
        "format": "tse-forensics-phase3k-residual-timing-v1",
        "input": str(IN),
        "usable_zones_with_2022": len(rows),
        "n_ufs": len(uf_rows),
        "spearman_delta_margin": {
            "median": median(rhos),
            "positive_ufs": sum(1 for x in rhos if x > 0),
            "negative_ufs": sum(1 for x in rhos if x < 0),
        },
        "delta_of_gradient_by_uf": {
            "median_pp": median(dgrad),
            "positive_ufs": sum(1 for x in dgrad if x > 0),
            "negative_ufs": sum(1 for x in dgrad if x < 0),
        },
        "pooled_within_uf_quartiles": {
            "early_2026": pe26,
            "late_2026": pl26,
            "late_minus_early_2026_pp": pooled_grad26,
            "early_2022": pe22,
            "late_2022": pl22,
            "late_minus_early_2022_pp": pooled_grad22,
            "delta_of_late_gradient_2026_minus_2022_pp": pooled_grad26 - pooled_grad22,
        },
        "key_ufs": [
            r for r in uf_rows
            if r["uf"] in {"AM","BA","CE","MA","MG","PA","PE","SP"}
        ],
        "largest_positive_delta_gradient": sorted(
            uf_rows,
            key=lambda r: r["delta_of_late_gradient_2026_minus_2022_pp"],
            reverse=True,
        )[:10],
        "largest_negative_delta_gradient": sorted(
            uf_rows,
            key=lambda r: r["delta_of_late_gradient_2026_minus_2022_pp"],
        )[:10],
        "interpretation_rules": [
            (
                "Pooled delta-of-gradient <= 0 means the late-zone Lula advantage "
                "was no stronger in 2026 than in the same geographic ordering in 2022."
            ),
            (
                "Positive Spearman for delta_margin means later zones shifted more "
                "toward Lula relative to 2022; this can coexist with a pooled "
                "delta-of-gradient that is negative because zone sizes differ."
            ),
            (
                "This is a historical-control test, not causal proof. Candidate field, "
                "turnout, third-party vote and rezoneamento differ across elections."
            ),
        ],
    }

    zone_out = [
        {
            "uf": r["uf"],
            "cd_tse": r["cd_tse"],
            "municipio": r["municipio"],
            "zona": r["zona"],
            "completa_gerado_brt": r["completa_gerado_brt"],
            "margin_lula_minus_flavio_2026_pp": r["margin26_pp"],
            "margin_lula_minus_bolsonaro_2022_pp": r["margin22_pp"],
            "delta_margin_2026_minus_2022_pp": r["delta_margin_2026_minus_2022_pp"],
        }
        for r in rows
    ]

    write_csv_atomic(
        OUT / "phase3k_zone_change_rows.csv",
        zone_out,
        [
            "uf","cd_tse","municipio","zona","completa_gerado_brt",
            "margin_lula_minus_flavio_2026_pp",
            "margin_lula_minus_bolsonaro_2022_pp",
            "delta_margin_2026_minus_2022_pp",
        ],
    )

    write_csv_atomic(
        OUT / "phase3k_by_uf.csv",
        uf_rows,
        [
            "uf","n_zonas","spearman_complete_vs_delta_margin_pp",
            "early_margin_2026_pp","late_margin_2026_pp",
            "late_minus_early_2026_pp",
            "early_margin_2022_pp","late_margin_2022_pp",
            "late_minus_early_2022_pp",
            "delta_of_late_gradient_2026_minus_2022_pp",
        ],
    )

    atomic_text(
        OUT / "phase3k_summary.json",
        json.dumps(summary, ensure_ascii=False, indent=2),
    )

    print("\nFASE 3K — efeito temporal residual controlado por 2022")
    print(f"- zonas utilizáveis com 2022: {len(rows)}")
    print(
        "- mediana Spearman conclusão x mudança de margem 26-22: "
        f"{summary['spearman_delta_margin']['median']:.3f}"
    )
    print(
        "- UFs com rho positivo/negativo: "
        f"{summary['spearman_delta_margin']['positive_ufs']}/"
        f"{summary['spearman_delta_margin']['negative_ufs']}"
    )
    print(
        "- quartis dentro das UFs: late-early 2026="
        f"{pooled_grad26:+.2f} pp · 2022={pooled_grad22:+.2f} pp · "
        f"delta={pooled_grad26 - pooled_grad22:+.2f} pp"
    )
    print(f"- por UF: {OUT / 'phase3k_by_uf.csv'}")
    print(f"- zonas: {OUT / 'phase3k_zone_change_rows.csv'}")
    print(f"- resumo: {OUT / 'phase3k_summary.json'}")


if __name__ == "__main__":
    main()
