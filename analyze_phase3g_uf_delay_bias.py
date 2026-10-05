#!/usr/bin/env python3
"""Fase 3G — viés geográfico: vantagem de Lula x atrasos/retomadas por UF.

Pergunta levantada externamente:
"Os estados em que Lula/PT tinha vantagem foram justamente os que atrasaram
mais, e quando voltaram a atualizar Lula ganhou enquanto a oposição caiu?"

Este script NÃO assume que a afirmação é verdadeira nem falsa. Ele operacionaliza
a hipótese com fontes contemporâneas já preservadas:

- ArvorCo/PNAD: eventos de travamento detectados por UF;
- vitoropereira/eleicoes2026: snapshots por UF em 18:32, 19:06, 19:32 e 20:47.

Métricas por UF:
- margem Lula - Flávio no snapshot de 19:06;
- sobreposição dos eventos de travamento da UF com:
    W1 = 18:48:59–19:14:08
    W2 = 19:14:08–19:32:47
- progresso percentual de seções entre snapshots;
- swing relativo Lula-vs-Flávio:
    Δ[(Lula %) - (Flávio %)]
- correlações de Spearman descritivas.

Importante:
- os eventos "travamentos.ufs" são os eventos detectados pela fonte com o seu
  próprio critério; não equivalem a "toda pausa possível";
- os horários internos das UFs podem refletir fusos/gerações diferentes, por isso
  o eixo de comparação principal são os snapshots contemporâneos;
- as correlações são descritivas, não p-valores causais.

Saídas:
  data/forensics/analysis/phase3g_uf_delay_bias.csv
  data/forensics/analysis/phase3g_summary.json
"""

import csv
import json
import hashlib
import math
import os
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path("data/forensics")
RAW = ROOT / "external"
OUT = ROOT / "analysis"
UA = "TSE-forensics-phase3g/1.0"

ARVOR_COMMIT = "beb3bec9ae5c25e2868ee2f2cefb9e6dccd91415"
# Primeiro commit verificado que contém os quatro snapshots usados abaixo.
# O commit anterior (3f4d744...) ainda não continha o snapshot de 20:47.
VITOR_COMMIT = "10c03a7d52058a2650836953b612939ba02a3235"

ARVOR_URL = (
    "https://raw.githubusercontent.com/ArvorCo/PNAD/"
    f"{ARVOR_COMMIT}/analysis/apuracao_2026/dados/linha_do_tempo.json"
)

SNAPSHOTS = [
    (
        "s1832",
        "snapshots/2026-10-04_1832_36.6pct/dados.json",
        "18:32",
    ),
    (
        "s1906",
        "snapshots/2026-10-04_1906_64.8pct/dados.json",
        "19:06",
    ),
    (
        "s1932",
        "snapshots/2026-10-04_1932_84.9pct/dados.json",
        "19:32",
    ),
    (
        "s2047",
        "snapshots/2026-10-04_2047_93.2pct/dados.json",
        "20:47",
    ),
]

WINDOWS = {
    "w1": ("2026-10-04 18:48:59", "2026-10-04 19:14:08"),
    "w2": ("2026-10-04 19:14:08", "2026-10-04 19:32:47"),
}


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


def fetch_json(url, path):
    if path.exists() and path.stat().st_size:
        data = path.read_bytes()
        reused = True
    else:
        req = urllib.request.Request(
            url, headers={"User-Agent": UA, "Cache-Control": "no-cache"}
        )
        with urllib.request.urlopen(req, timeout=90) as r:
            data = r.read()
        atomic_write(path, data)
        reused = False
    return json.loads(data.decode("utf-8-sig")), {
        "url": url,
        "path": str(path),
        "sha256": sha256(data),
        "bytes": len(data),
        "reused": reused,
    }


def parse_brt(s):
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")


def overlap_minutes(a1, a2, b1, b2):
    start = max(a1, b1)
    end = min(a2, b2)
    return max(0.0, (end - start).total_seconds() / 60.0)


def median(values):
    xs = sorted(values)
    if not xs:
        return None
    n = len(xs)
    if n % 2:
        return xs[n // 2]
    return (xs[n // 2 - 1] + xs[n // 2]) / 2.0


def mean(values):
    return sum(values) / len(values) if values else None


def ranks(values):
    indexed = sorted(enumerate(values), key=lambda x: x[1])
    out = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i
        while j + 1 < len(indexed) and indexed[j + 1][1] == indexed[i][1]:
            j += 1
        r = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            out[indexed[k][0]] = r
        i = j + 1
    return out


def pearson(x, y):
    if len(x) < 2:
        return None
    mx, my = mean(x), mean(y)
    dx = [v - mx for v in x]
    dy = [v - my for v in y]
    den = math.sqrt(sum(v * v for v in dx) * sum(v * v for v in dy))
    if den == 0:
        return None
    return sum(a * b for a, b in zip(dx, dy)) / den


def spearman(x, y):
    if len(x) < 2:
        return None
    return pearson(ranks(x), ranks(y))


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

    arvor, arvor_meta = fetch_json(
        ARVOR_URL,
        RAW / "ArvorCo-PNAD" / ARVOR_COMMIT / "linha_do_tempo.json",
    )

    snapshots = {}
    source_meta = [arvor_meta]
    for key, relpath, label in SNAPSHOTS:
        url = (
            "https://raw.githubusercontent.com/vitoropereira/eleicoes2026/"
            f"{VITOR_COMMIT}/{relpath}"
        )
        obj, meta = fetch_json(
            url,
            RAW / "vitoropereira-eleicoes2026" / VITOR_COMMIT / Path(relpath).name.replace(
                "dados.json", f"{key}.json"
            ),
        )
        snapshots[key] = obj
        meta["label"] = label
        source_meta.append(meta)

    by_uf = {}
    for key, obj in snapshots.items():
        for st in obj.get("states", []):
            uf = st.get("uf")
            if not uf or uf == "ZZ":
                continue
            by_uf.setdefault(uf, {})[key] = {
                "pst": float(st.get("pst", 0)),
                "flavio": float(st.get("f", 0)),
                "lula": float(st.get("l", 0)),
                "source_ht": st.get("ht", ""),
            }

    freezes = arvor.get("travamentos", {}).get("ufs", []) or []

    rows = []
    for uf in sorted(by_uf):
        x = by_uf[uf]
        if not all(k in x for k, _, _ in SNAPSHOTS):
            continue

        r = {
            "uf": uf,
            "baseline_1906_flavio_pct": x["s1906"]["flavio"],
            "baseline_1906_lula_pct": x["s1906"]["lula"],
            "baseline_1906_lula_minus_flavio_pp": (
                x["s1906"]["lula"] - x["s1906"]["flavio"]
            ),
            "baseline_leader": (
                "Lula"
                if x["s1906"]["lula"] > x["s1906"]["flavio"]
                else "Flavio"
                if x["s1906"]["flavio"] > x["s1906"]["lula"]
                else "Empate"
            ),
        }

        for wname, (wstart, wend) in WINDOWS.items():
            b1, b2 = parse_brt(wstart), parse_brt(wend)
            overlaps = []
            for fr in freezes:
                if fr.get("arquivo") != uf:
                    continue
                ov = overlap_minutes(
                    parse_brt(fr["de_brt"]),
                    parse_brt(fr["ate_brt"]),
                    b1,
                    b2,
                )
                if ov > 0:
                    overlaps.append(ov)
            r[f"{wname}_freeze_events"] = len(overlaps)
            r[f"{wname}_freeze_total_min"] = sum(overlaps)
            r[f"{wname}_freeze_longest_min"] = max(overlaps) if overlaps else 0.0

        for a, b, label in [
            ("s1832", "s1906", "1832_1906"),
            ("s1906", "s1932", "1906_1932"),
            ("s1932", "s2047", "1932_2047"),
        ]:
            r[f"progress_pst_{label}"] = x[b]["pst"] - x[a]["pst"]
            margin_a = x[a]["lula"] - x[a]["flavio"]
            margin_b = x[b]["lula"] - x[b]["flavio"]
            r[f"swing_lula_minus_flavio_{label}_pp"] = margin_b - margin_a
            r[f"delta_lula_{label}_pp"] = x[b]["lula"] - x[a]["lula"]
            r[f"delta_flavio_{label}_pp"] = x[b]["flavio"] - x[a]["flavio"]

        rows.append(r)

    lula_led = [r for r in rows if r["baseline_leader"] == "Lula"]
    flavio_led = [r for r in rows if r["baseline_leader"] == "Flavio"]

    def group_stats(group):
        return {
            "n": len(group),
            "w1_freeze_total_mean_min": mean([r["w1_freeze_total_min"] for r in group]),
            "w1_freeze_total_median_min": median([r["w1_freeze_total_min"] for r in group]),
            "w2_freeze_total_mean_min": mean([r["w2_freeze_total_min"] for r in group]),
            "w2_freeze_total_median_min": median([r["w2_freeze_total_min"] for r in group]),
            "swing_1906_1932_mean_pp": mean(
                [r["swing_lula_minus_flavio_1906_1932_pp"] for r in group]
            ),
            "swing_1906_1932_median_pp": median(
                [r["swing_lula_minus_flavio_1906_1932_pp"] for r in group]
            ),
            "swing_1932_2047_mean_pp": mean(
                [r["swing_lula_minus_flavio_1932_2047_pp"] for r in group]
            ),
            "swing_1932_2047_median_pp": median(
                [r["swing_lula_minus_flavio_1932_2047_pp"] for r in group]
            ),
        }

    margins = [r["baseline_1906_lula_minus_flavio_pp"] for r in rows]
    w2delay = [r["w2_freeze_total_min"] for r in rows]
    swing12 = [r["swing_lula_minus_flavio_1906_1932_pp"] for r in rows]
    swing23 = [r["swing_lula_minus_flavio_1932_2047_pp"] for r in rows]

    summary = {
        "format": "tse-forensics-phase3g-uf-delay-bias-v1",
        "sources": source_meta,
        "hypothesis": (
            "UFs com vantagem de Lula/PT tiveram maior atraso/pausa de atualização "
            "e, na retomada, tenderam a produzir swing adicional em favor de Lula."
        ),
        "operationalization": {
            "baseline_leader_snapshot": "s1906",
            "w1": WINDOWS["w1"],
            "w2": WINDOWS["w2"],
            "delay_measure": (
                "minutos de sobreposição entre os eventos travamentos.ufs da fonte "
                "ArvorCo e a janela crítica"
            ),
            "swing_measure": "delta de (Lula% - Flavio%) entre snapshots",
        },
        "groups": {
            "lula_led": group_stats(lula_led),
            "flavio_led": group_stats(flavio_led),
        },
        "correlations": {
            "spearman_baseline_lula_margin_vs_w2_delay": spearman(margins, w2delay),
            "spearman_w2_delay_vs_swing_1906_1932": spearman(w2delay, swing12),
            "spearman_w2_delay_vs_swing_1932_2047": spearman(w2delay, swing23),
        },
        "w1_ufs_with_any_detected_freeze": [
            {
                "uf": r["uf"],
                "minutes": r["w1_freeze_total_min"],
                "baseline_leader": r["baseline_leader"],
                "baseline_margin_pp": r["baseline_1906_lula_minus_flavio_pp"],
            }
            for r in rows
            if r["w1_freeze_total_min"] > 0
        ],
        "top_w2_delay_ufs": sorted(
            [
                {
                    "uf": r["uf"],
                    "minutes": r["w2_freeze_total_min"],
                    "baseline_leader": r["baseline_leader"],
                    "baseline_margin_pp": r["baseline_1906_lula_minus_flavio_pp"],
                    "swing_1906_1932_pp": r["swing_lula_minus_flavio_1906_1932_pp"],
                }
                for r in rows
            ],
            key=lambda x: x["minutes"],
            reverse=True,
        )[:10],
        "interpretation_rules": [
            (
                "Se UFs Lula-led apresentarem sistematicamente maior atraso que UFs "
                "Flavio-led, isso sustenta a associação descritiva levantada."
            ),
            (
                "Se atrasos forem semelhantes ou maiores no grupo Flavio-led, a forma "
                "forte da hipótese não é sustentada por esta métrica."
            ),
            (
                "Swing positivo significa aumento da vantagem relativa de Lula; swing "
                "negativo significa movimento relativo em favor de Flávio."
            ),
            (
                "Associação entre atraso e swing não identifica mecanismo nem prova "
                "alteração de votos; serve para localizar padrões a aprofundar."
            ),
        ],
    }

    fields = [
        "uf","baseline_1906_flavio_pct","baseline_1906_lula_pct",
        "baseline_1906_lula_minus_flavio_pp","baseline_leader",
        "w1_freeze_events","w1_freeze_total_min","w1_freeze_longest_min",
        "w2_freeze_events","w2_freeze_total_min","w2_freeze_longest_min",
        "progress_pst_1832_1906","swing_lula_minus_flavio_1832_1906_pp",
        "delta_lula_1832_1906_pp","delta_flavio_1832_1906_pp",
        "progress_pst_1906_1932","swing_lula_minus_flavio_1906_1932_pp",
        "delta_lula_1906_1932_pp","delta_flavio_1906_1932_pp",
        "progress_pst_1932_2047","swing_lula_minus_flavio_1932_2047_pp",
        "delta_lula_1932_2047_pp","delta_flavio_1932_2047_pp",
    ]
    write_csv_atomic(OUT / "phase3g_uf_delay_bias.csv", rows, fields)

    atomic_write(
        OUT / "phase3g_summary.json",
        json.dumps(summary, ensure_ascii=False, indent=2).encode("utf-8"),
    )

    print("\nFASE 3G — vantagem Lula x atrasos/retomadas por UF")
    print(f"- UFs analisadas: {len(rows)}")
    print(
        f"- Lula-led: {len(lula_led)} · "
        f"W2 mediana atraso={summary['groups']['lula_led']['w2_freeze_total_median_min']:.2f} min"
    )
    print(
        f"- Flavio-led: {len(flavio_led)} · "
        f"W2 mediana atraso={summary['groups']['flavio_led']['w2_freeze_total_median_min']:.2f} min"
    )
    print(
        "- Spearman margem Lula x atraso W2: "
        f"{summary['correlations']['spearman_baseline_lula_margin_vs_w2_delay']:.3f}"
    )
    print(
        "- Spearman atraso W2 x swing 19:06→19:32: "
        f"{summary['correlations']['spearman_w2_delay_vs_swing_1906_1932']:.3f}"
    )
    print(f"- CSV: {OUT / 'phase3g_uf_delay_bias.csv'}")
    print(f"- resumo: {OUT / 'phase3g_summary.json'}")


if __name__ == "__main__":
    main()
