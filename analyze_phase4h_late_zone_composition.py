#!/usr/bin/env python3
"""Fase 4H — composição política das zonas que terminam mais tarde.

Objetivo
=======
Explicar geograficamente o resultado da Fase 4G:

- após 20:04:39, Lula sobe em 152/152 atualizações exatas;
- Flávio cai em 152/152;
- os mesmos 152 lotes seriam monotônicos em QUALQUER ordem.

A pergunta passa a ser:
  as zonas que ainda demoravam para concluir eram estruturalmente mais
  favoráveis a Lula?

Fonte
=====
ArvorCo/PNAD, zonas.json, commit fixado:
  beb3bec9ae5c25e2868ee2f2cefb9e6dccd91415

Para vários cortes horários, dividimos as zonas completas em:
- EARLY: zona já havia concluído até o corte;
- LATE: zona concluiu depois do corte.

Calculamos, ponderado por votos válidos:
- Lula, Flávio e margem Lula-Flávio em 2026;
- Lula, Bolsonaro e margem Lula-Bolsonaro no 1º turno de 2022
  para as MESMAS zonas com referência histórica disponível.

Importante
==========
"Zona concluiu depois de T" NÃO significa que todos os votos daquela zona
entraram depois de T. A zona pode já ter publicado muitas seções antes do
horário e apenas a última seção ter chegado depois.

Portanto esta fase mede COMPOSIÇÃO GEOGRÁFICA DO CONJUNTO TARDIO; não tenta
reconstruir exatamente os 18,8 milhões de votos que entraram após 20:04:39.

Saídas
======
  data/forensics/analysis/phase4h_late_zone_thresholds.csv
  data/forensics/analysis/phase4h_summary.json
"""

import csv
import hashlib
import json
import os
import urllib.request
from pathlib import Path

ROOT = Path("data/forensics")
RAW = ROOT / "external" / "ArvorCo-PNAD"
OUT = ROOT / "analysis"
UA = "TSE-forensics-phase4h/1.0"

COMMIT = "beb3bec9ae5c25e2868ee2f2cefb9e6dccd91415"
URL = (
    "https://raw.githubusercontent.com/ArvorCo/PNAD/"
    f"{COMMIT}/analysis/apuracao_2026/dados/zonas.json"
)
RAW_PATH = RAW / COMMIT / "zonas.json"
PHASE4G = OUT / "phase4g_summary.json"

THRESHOLDS = [
    ("resume_200439", "2026-10-04 20:04:39"),
    ("image_end_203035", "2026-10-04 20:30:35"),
    ("2100", "2026-10-04 21:00:00"),
    ("2200", "2026-10-04 22:00:00"),
    ("midnight", "2026-10-05 00:00:00"),
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
        with urllib.request.urlopen(req, timeout=120) as r:
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


def pct(v, total):
    return 100.0 * v / total if total else None


def aggregate(rows):
    vv = sum(int(r.get("validos", 0) or 0) for r in rows)
    lula = sum(int(r.get("lula", 0) or 0) for r in rows)
    flavio = sum(int(r.get("flavio", 0) or 0) for r in rows)

    matched22 = [
        r for r in rows
        if int(r.get("validos_2022_1t", 0) or 0) > 0
    ]
    vv22 = sum(int(r.get("validos_2022_1t", 0) or 0) for r in matched22)
    lula22 = sum(int(r.get("lula_2022_1t", 0) or 0) for r in matched22)
    bolso22 = sum(int(r.get("bolsonaro_2022_1t", 0) or 0) for r in matched22)

    l26 = pct(lula, vv)
    f26 = pct(flavio, vv)
    l22 = pct(lula22, vv22)
    b22 = pct(bolso22, vv22)

    return {
        "zones": len(rows),
        "zones_with_2022": len(matched22),
        "valid_votes_2026": vv,
        "lula_votes_2026": lula,
        "flavio_votes_2026": flavio,
        "lula_pct_2026": l26,
        "flavio_pct_2026": f26,
        "lula_minus_flavio_pp_2026": (
            l26 - f26 if l26 is not None and f26 is not None else None
        ),
        "valid_votes_2022_matched": vv22,
        "lula_votes_2022_matched": lula22,
        "bolsonaro_votes_2022_matched": bolso22,
        "lula_pct_2022_matched": l22,
        "bolsonaro_pct_2022_matched": b22,
        "lula_minus_bolsonaro_pp_2022_matched": (
            l22 - b22 if l22 is not None and b22 is not None else None
        ),
    }


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
    OUT.mkdir(parents=True, exist_ok=True)
    data, source = fetch()

    zones = [
        r for r in table_rows(data["zonas"])
        if bool(r.get("completo")) and r.get("completa_gerado_brt")
    ]

    phase4g = None
    if PHASE4G.exists():
        phase4g = json.loads(PHASE4G.read_text(encoding="utf-8-sig"))

    rows = []
    threshold_summary = []

    for label, cutoff in THRESHOLDS:
        early = [r for r in zones if r["completa_gerado_brt"] <= cutoff]
        late = [r for r in zones if r["completa_gerado_brt"] > cutoff]

        a_early = aggregate(early)
        a_late = aggregate(late)

        delta_late_vs_early_26 = (
            a_late["lula_minus_flavio_pp_2026"]
            - a_early["lula_minus_flavio_pp_2026"]
        )
        delta_late_vs_early_22 = (
            a_late["lula_minus_bolsonaro_pp_2022_matched"]
            - a_early["lula_minus_bolsonaro_pp_2022_matched"]
        )
        historical_control_delta = (
            delta_late_vs_early_26 - delta_late_vs_early_22
        )

        for group_name, a in [("early", a_early), ("late", a_late)]:
            rows.append({
                "threshold_label": label,
                "threshold_brt": cutoff,
                "group": group_name,
                **a,
                "late_minus_early_margin_2026_pp": (
                    delta_late_vs_early_26 if group_name == "late" else None
                ),
                "late_minus_early_margin_2022_pp": (
                    delta_late_vs_early_22 if group_name == "late" else None
                ),
                "delta_of_late_gradient_2026_minus_2022_pp": (
                    historical_control_delta if group_name == "late" else None
                ),
            })

        threshold_summary.append({
            "label": label,
            "cutoff_brt": cutoff,
            "early": a_early,
            "late": a_late,
            "late_minus_early_margin_2026_pp": delta_late_vs_early_26,
            "late_minus_early_margin_2022_pp": delta_late_vs_early_22,
            "delta_of_late_gradient_2026_minus_2022_pp": historical_control_delta,
        })

    resume = threshold_summary[0]
    gref = None
    if phase4g:
        rp = phase4g.get("remaining_pool", {})
        gref = {
            "remaining_valid_votes": rp.get("valid_votes"),
            "remaining_lula_share_pct": rp.get("lula_share_pct"),
            "remaining_flavio_share_pct": rp.get("flavio_share_pct"),
            "remaining_lula_minus_flavio_margin_pp": rp.get(
                "lula_minus_flavio_margin_pp"
            ),
            "late_zone_final_valid_votes_at_200439": (
                resume["late"]["valid_votes_2026"]
            ),
            "late_zone_final_votes_div_remaining_pool": (
                resume["late"]["valid_votes_2026"] / rp["valid_votes"]
                if rp.get("valid_votes") else None
            ),
            "warning": (
                "Late-zone final vote totals are much larger than the actual "
                "post-20:04 remaining pool because many late-completing zones "
                "had already contributed sections before their completion time."
            ),
        }

    summary = {
        "format": "tse-forensics-phase4h-late-zone-composition-v1",
        "source": source,
        "coverage": {
            "complete_zones": len(zones),
            "reported_complete_zones_in_source": data.get("n"),
            "source_incomplete_zones": data.get("n_incompletas"),
            "source_without_2022": data.get("n_sem_2022"),
        },
        "thresholds": threshold_summary,
        "phase4g_reference": gref,
        "interpretation": [
            (
                "Se zonas que concluem depois do corte forem muito mais Lula "
                "em 2026, há uma base geográfica para o pool tardio ser pró-Lula."
            ),
            (
                "Se as MESMAS zonas também forem muito mais Lula em 2022, "
                "isso sustenta que a ordenação tardia tem componente estrutural "
                "pré-existente, não exclusivo de 2026."
            ),
            (
                "O horário de conclusão não permite atribuir todos os votos de "
                "uma zona ao período posterior ao corte. Esta análise é "
                "composicional, não uma reconstrução exata do lote."
            ),
            (
                "A comparação 2022 usa somente zonas com referência histórica "
                "disponível e pondera pelos votos válidos daquele ano."
            ),
        ],
    }

    fields = [
        "threshold_label","threshold_brt","group","zones","zones_with_2022",
        "valid_votes_2026","lula_votes_2026","flavio_votes_2026",
        "lula_pct_2026","flavio_pct_2026",
        "lula_minus_flavio_pp_2026",
        "valid_votes_2022_matched","lula_votes_2022_matched",
        "bolsonaro_votes_2022_matched","lula_pct_2022_matched",
        "bolsonaro_pct_2022_matched",
        "lula_minus_bolsonaro_pp_2022_matched",
        "late_minus_early_margin_2026_pp",
        "late_minus_early_margin_2022_pp",
        "delta_of_late_gradient_2026_minus_2022_pp",
    ]
    write_csv_atomic(
        OUT / "phase4h_late_zone_thresholds.csv",
        rows,
        fields,
    )
    atomic_write(
        OUT / "phase4h_summary.json",
        json.dumps(summary, ensure_ascii=False, indent=2).encode("utf-8"),
    )

    print("\nFASE 4H — composição das zonas de conclusão tardia")
    print(f"- zonas completas: {len(zones)}")
    for x in threshold_summary:
        late = x["late"]
        print(
            f"- após {x['cutoff_brt'][11:16]}: zonas={late['zones']} · "
            f"Lula={late['lula_pct_2026']:.2f}% · "
            f"Flávio={late['flavio_pct_2026']:.2f}% · "
            f"margem26={late['lula_minus_flavio_pp_2026']:+.2f} pp · "
            f"mesmas zonas 2022={late['lula_minus_bolsonaro_pp_2022_matched']:+.2f} pp"
        )
    if gref:
        print(
            "- referência 4G: pool real pós-20:04 Lula="
            f"{gref['remaining_lula_share_pct']:.2f}% · "
            f"Flávio={gref['remaining_flavio_share_pct']:.2f}%"
        )
        print(
            "- ATENÇÃO: votos finais das zonas tardias / pool real = "
            f"{gref['late_zone_final_votes_div_remaining_pool']:.2f}x; "
            "logo conclusão de zona NÃO reconstrói o pool."
        )
    print(f"- CSV: {OUT / 'phase4h_late_zone_thresholds.csv'}")
    print(f"- resumo: {OUT / 'phase4h_summary.json'}")


if __name__ == "__main__":
    main()
