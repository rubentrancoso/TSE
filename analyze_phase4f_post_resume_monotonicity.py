#!/usr/bin/env python3
"""Fase 4F — monotonicidade pós-retomada da apuração presidencial.

Alegação externa recebida:
"Depois que o site do TSE saiu do travamento, a cada 15 segundos Lula sobe
0,01%, Flávio desce 0,01%; Lula nunca desce, só sobe."

Esta fase separa três afirmações:
1) direção: Lula nunca cai / Flávio nunca sobe;
2) tamanho do passo: exatamente ±0,01 pp;
3) cadência: exatamente 15 segundos.

Fonte fixa:
ArvorCo/PNAD, linha_do_tempo.json, commit
beb3bec9ae5c25e2868ee2f2cefb9e6dccd91415.

Usamos apenas versões nacionais não regressivas com d_vv > 0.

Janelas:
- "imagem": 20:04:39 → 20:30:35;
- "pós-retomada": 20:04:39 → última versão 100%.

Também calculamos:
- maior sequência monotônica antes da retomada;
- condição marginal de cada lote:
    share_lote_Lula >= share_acumulada_Lula_anterior
    share_lote_Flávio <= share_acumulada_Flávio_anterior

Saídas:
  data/forensics/analysis/phase4f_post_resume_transitions.csv
  data/forensics/analysis/phase4f_summary.json
"""

import csv
import hashlib
import json
import math
import os
import statistics
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path("data/forensics")
RAW = ROOT / "external" / "ArvorCo-PNAD"
OUT = ROOT / "analysis"
UA = "TSE-forensics-phase4f/1.0"

COMMIT = "beb3bec9ae5c25e2868ee2f2cefb9e6dccd91415"
URL = (
    "https://raw.githubusercontent.com/ArvorCo/PNAD/"
    f"{COMMIT}/analysis/apuracao_2026/dados/linha_do_tempo.json"
)
RAW_PATH = RAW / COMMIT / "linha_do_tempo.json"

RESUME = "2026-10-04 20:04:39"
IMAGE_END = "2026-10-04 20:30:35"


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


def parse_dt(s):
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")


def rounded2(x):
    return round(float(x) + 1e-12, 2)


def transition(prev, cur):
    dt_sec = (parse_dt(cur["gerado_brt"]) - parse_dt(prev["gerado_brt"])).total_seconds()

    l0 = float(prev["pct_lula"])
    l1 = float(cur["pct_lula"])
    f0 = float(prev["pct_flavio"])
    f1 = float(cur["pct_flavio"])

    d_lula_pp = l1 - l0
    d_flavio_pp = f1 - f0

    display_l0 = rounded2(l0)
    display_l1 = rounded2(l1)
    display_f0 = rounded2(f0)
    display_f1 = rounded2(f1)

    d_vv = int(cur["d_vv"])
    batch_lula_pct = 100.0 * int(cur["d_lula"]) / d_vv
    batch_flavio_pct = 100.0 * int(cur["d_flavio"]) / d_vv

    return {
        "from_brt": prev["gerado_brt"],
        "to_brt": cur["gerado_brt"],
        "seconds_since_previous": dt_sec,
        "d_valid_votes": d_vv,
        "d_sections": int(cur["d_st"]),
        "lula_pct_before": l0,
        "lula_pct_after": l1,
        "lula_change_pp": d_lula_pp,
        "flavio_pct_before": f0,
        "flavio_pct_after": f1,
        "flavio_change_pp": d_flavio_pp,
        "lula_display_2d_before": display_l0,
        "lula_display_2d_after": display_l1,
        "lula_display_change_pp": round(display_l1 - display_l0, 2),
        "flavio_display_2d_before": display_f0,
        "flavio_display_2d_after": display_f1,
        "flavio_display_change_pp": round(display_f1 - display_f0, 2),
        "batch_lula_pct": batch_lula_pct,
        "batch_flavio_pct": batch_flavio_pct,
        "batch_lula_ge_previous_cumulative": batch_lula_pct >= l0,
        "batch_flavio_le_previous_cumulative": batch_flavio_pct <= f0,
    }


def summarize(transitions, first_row, last_row):
    cad = [r["seconds_since_previous"] for r in transitions]

    return {
        "versions": len(transitions) + 1,
        "transitions": len(transitions),
        "first_brt": first_row["gerado_brt"],
        "last_brt": last_row["gerado_brt"],
        "start_lula_pct": float(first_row["pct_lula"]),
        "end_lula_pct": float(last_row["pct_lula"]),
        "net_lula_change_pp": (
            float(last_row["pct_lula"]) - float(first_row["pct_lula"])
        ),
        "start_flavio_pct": float(first_row["pct_flavio"]),
        "end_flavio_pct": float(last_row["pct_flavio"]),
        "net_flavio_change_pp": (
            float(last_row["pct_flavio"]) - float(first_row["pct_flavio"])
        ),
        "exact_direction": {
            "lula_up": sum(r["lula_change_pp"] > 0 for r in transitions),
            "lula_flat": sum(r["lula_change_pp"] == 0 for r in transitions),
            "lula_down": sum(r["lula_change_pp"] < 0 for r in transitions),
            "flavio_down": sum(r["flavio_change_pp"] < 0 for r in transitions),
            "flavio_flat": sum(r["flavio_change_pp"] == 0 for r in transitions),
            "flavio_up": sum(r["flavio_change_pp"] > 0 for r in transitions),
        },
        "display_2_decimals": {
            "lula_plus_0_01": sum(
                math.isclose(r["lula_display_change_pp"], 0.01, abs_tol=1e-12)
                for r in transitions
            ),
            "lula_zero": sum(
                math.isclose(r["lula_display_change_pp"], 0.0, abs_tol=1e-12)
                for r in transitions
            ),
            "lula_greater_than_0_01": sum(
                r["lula_display_change_pp"] > 0.01 for r in transitions
            ),
            "lula_negative": sum(
                r["lula_display_change_pp"] < 0 for r in transitions
            ),
            "flavio_minus_0_01": sum(
                math.isclose(r["flavio_display_change_pp"], -0.01, abs_tol=1e-12)
                for r in transitions
            ),
            "flavio_zero": sum(
                math.isclose(r["flavio_display_change_pp"], 0.0, abs_tol=1e-12)
                for r in transitions
            ),
            "flavio_less_than_minus_0_01": sum(
                r["flavio_display_change_pp"] < -0.01 for r in transitions
            ),
            "flavio_positive": sum(
                r["flavio_display_change_pp"] > 0 for r in transitions
            ),
        },
        "cadence_seconds": {
            "min": min(cad) if cad else None,
            "median": statistics.median(cad) if cad else None,
            "mean": statistics.mean(cad) if cad else None,
            "max": max(cad) if cad else None,
            "exactly_15_seconds": sum(
                math.isclose(x, 15.0, abs_tol=1e-12) for x in cad
            ),
        },
        "batch_condition": {
            "lula_batch_share_ge_previous_cumulative": sum(
                r["batch_lula_ge_previous_cumulative"] for r in transitions
            ),
            "flavio_batch_share_le_previous_cumulative": sum(
                r["batch_flavio_le_previous_cumulative"] for r in transitions
            ),
            "both": sum(
                r["batch_lula_ge_previous_cumulative"]
                and r["batch_flavio_le_previous_cumulative"]
                for r in transitions
            ),
        },
    }


def longest_monotonic_run(rows):
    best = None
    current = None

    for i in range(1, len(rows)):
        prev = rows[i - 1]
        cur = rows[i]
        good = (
            float(cur["pct_lula"]) >= float(prev["pct_lula"])
            and float(cur["pct_flavio"]) <= float(prev["pct_flavio"])
        )

        if good:
            if current is None:
                current = {
                    "start_brt": prev["gerado_brt"],
                    "end_brt": cur["gerado_brt"],
                    "transitions": 1,
                }
            else:
                current["end_brt"] = cur["gerado_brt"]
                current["transitions"] += 1

            current["duration_seconds"] = (
                parse_dt(current["end_brt"]) - parse_dt(current["start_brt"])
            ).total_seconds()

            if (
                best is None
                or current["transitions"] > best["transitions"]
                or (
                    current["transitions"] == best["transitions"]
                    and current["duration_seconds"] > best["duration_seconds"]
                )
            ):
                best = dict(current)
        else:
            current = None

    return best


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

    rows = [
        r for r in table_rows(data["nacional"]["versoes"])
        if not r.get("marcada_regressiva")
        and r.get("d_vv") is not None
        and int(r["d_vv"]) > 0
    ]

    resume_idx = next(
        (i for i, r in enumerate(rows) if r["gerado_brt"] == RESUME),
        None,
    )
    if resume_idx is None:
        raise RuntimeError(f"Versão de retomada {RESUME} não encontrada.")

    image_rows = [
        r for r in rows
        if RESUME <= r["gerado_brt"] <= IMAGE_END
    ]
    post_rows = rows[resume_idx:]
    pre_rows = rows[: resume_idx + 1]

    image_transitions = [
        transition(image_rows[i - 1], image_rows[i])
        for i in range(1, len(image_rows))
    ]
    post_transitions = [
        transition(post_rows[i - 1], post_rows[i])
        for i in range(1, len(post_rows))
    ]

    image_summary = summarize(
        image_transitions, image_rows[0], image_rows[-1]
    )
    post_summary = summarize(
        post_transitions, post_rows[0], post_rows[-1]
    )

    summary = {
        "format": "tse-forensics-phase4f-post-resume-monotonicity-v1",
        "source": source,
        "claim_test": {
            "claim_direction_lula_never_down_flavio_never_up": {
                "image_window_supported": (
                    image_summary["exact_direction"]["lula_down"] == 0
                    and image_summary["exact_direction"]["flavio_up"] == 0
                ),
                "post_resume_to_final_supported": (
                    post_summary["exact_direction"]["lula_down"] == 0
                    and post_summary["exact_direction"]["flavio_up"] == 0
                ),
            },
            "claim_exactly_0_01_each_update": {
                "image_window_supported": (
                    image_summary["display_2_decimals"]["lula_plus_0_01"]
                    == image_summary["transitions"]
                    and image_summary["display_2_decimals"]["flavio_minus_0_01"]
                    == image_summary["transitions"]
                ),
                "post_resume_to_final_supported": (
                    post_summary["display_2_decimals"]["lula_plus_0_01"]
                    == post_summary["transitions"]
                    and post_summary["display_2_decimals"]["flavio_minus_0_01"]
                    == post_summary["transitions"]
                ),
            },
            "claim_every_15_seconds": {
                "image_window_supported": (
                    image_summary["cadence_seconds"]["exactly_15_seconds"]
                    == image_summary["transitions"]
                ),
                "post_resume_to_final_supported": (
                    post_summary["cadence_seconds"]["exactly_15_seconds"]
                    == post_summary["transitions"]
                ),
            },
            "claim_same_as_2022": {
                "status": "not_tested",
                "reason": (
                    "Esta fonte contém cronologia fina de 2026, não uma série "
                    "temporal nacional equivalente de 2022."
                ),
            },
        },
        "image_window": image_summary,
        "post_resume_to_final": post_summary,
        "benchmark": {
            "longest_monotonic_run_before_resume": longest_monotonic_run(
                pre_rows
            ),
            "monotonic_run_after_resume": longest_monotonic_run(post_rows),
        },
        "interpretation": [
            (
                "A afirmação direcional é literalmente verdadeira na série "
                "nacional preservada: após 20:04:39 não há versão genuína em "
                "que Lula perca percentual nem em que Flávio ganhe percentual."
            ),
            (
                "A afirmação de +0,01/-0,01 em todo update é falsa: em duas "
                "casas decimais há muitos passos 0,00 e vários maiores que 0,01."
            ),
            (
                "A afirmação de atualização a cada 15 s é falsa para as horas "
                "de geração das novas versões do arquivo nacional; polling do "
                "site pode ocorrer em frequência diferente."
            ),
            (
                "Monotonicidade de participação acumulada significa que quase "
                "todos os lotes posteriores tinham share Lula acima do acumulado "
                "anterior e share Flávio abaixo; isso descreve a composição dos "
                "lotes, não identifica a causa."
            ),
            (
                "Fases 3J/3K já mostraram ordenação geográfica tardia pró-Lula "
                "também em 2022; isso deve ser considerado ao interpretar a "
                "sequência monotônica de 2026."
            ),
        ],
    }

    fields = [
        "from_brt","to_brt","seconds_since_previous","d_valid_votes",
        "d_sections","lula_pct_before","lula_pct_after","lula_change_pp",
        "flavio_pct_before","flavio_pct_after","flavio_change_pp",
        "lula_display_2d_before","lula_display_2d_after",
        "lula_display_change_pp","flavio_display_2d_before",
        "flavio_display_2d_after","flavio_display_change_pp",
        "batch_lula_pct","batch_flavio_pct",
        "batch_lula_ge_previous_cumulative",
        "batch_flavio_le_previous_cumulative",
    ]
    write_csv_atomic(
        OUT / "phase4f_post_resume_transitions.csv",
        post_transitions,
        fields,
    )
    atomic_write(
        OUT / "phase4f_summary.json",
        json.dumps(summary, ensure_ascii=False, indent=2).encode("utf-8"),
    )

    print("\nFASE 4F — monotonicidade pós-retomada")
    print(
        f"- imagem até 20:30: {image_summary['transitions']} transições · "
        f"Lula ↓={image_summary['exact_direction']['lula_down']} · "
        f"Flávio ↑={image_summary['exact_direction']['flavio_up']}"
    )
    print(
        "- imagem: passos exatamente +0,01 Lula="
        f"{image_summary['display_2_decimals']['lula_plus_0_01']}/"
        f"{image_summary['transitions']} · exatamente -0,01 Flávio="
        f"{image_summary['display_2_decimals']['flavio_minus_0_01']}/"
        f"{image_summary['transitions']}"
    )
    print(
        "- imagem: cadência novas versões min/mediana/max="
        f"{image_summary['cadence_seconds']['min']:.0f}/"
        f"{image_summary['cadence_seconds']['median']:.0f}/"
        f"{image_summary['cadence_seconds']['max']:.0f}s"
    )
    print(
        f"- até 100%: {post_summary['transitions']} transições · "
        f"Lula ↑={post_summary['exact_direction']['lula_up']}, "
        f"= {post_summary['exact_direction']['lula_flat']}, "
        f"↓={post_summary['exact_direction']['lula_down']} · "
        f"Flávio ↓={post_summary['exact_direction']['flavio_down']}, "
        f"= {post_summary['exact_direction']['flavio_flat']}, "
        f"↑={post_summary['exact_direction']['flavio_up']}"
    )
    print(
        f"- movimento 20:04→final: Lula "
        f"{post_summary['net_lula_change_pp']:+.4f} pp · Flávio "
        f"{post_summary['net_flavio_change_pp']:+.4f} pp"
    )
    print(
        "- maior sequência pré-retomada: "
        f"{summary['benchmark']['longest_monotonic_run_before_resume']['transitions']} "
        "transições; pós-retomada: "
        f"{summary['benchmark']['monotonic_run_after_resume']['transitions']}"
    )
    print(f"- CSV: {OUT / 'phase4f_post_resume_transitions.csv'}")
    print(f"- resumo: {OUT / 'phase4f_summary.json'}")


if __name__ == "__main__":
    main()
