#!/usr/bin/env python3
"""Fase 3H — atraso de conclusão por UF e composição geográfica tardia.

Pergunta:
Mesmo que os eventos técnicos de "travamento" por UF não tenham sido maiores
nos estados pró-Lula, os estados em que Lula liderava estavam menos avançados
na apuração e, portanto, carregavam mais resultado relativo para entrar depois?

Este teste usa quatro snapshots contemporâneos preservados por
vitoropereira/eleicoes2026:
- 18:32
- 19:06
- 19:32
- 20:47

Métricas:
- percentual de seções apuradas por UF em cada snapshot;
- percentual ainda não apurado;
- comparação Lula-led x Flavio-led;
- correlação de Spearman entre margem Lula-Flavio e percentual apurado;
- proxy de "eleitorado ainda em UFs incompletas":
      eleitorado_total * (1 - pst/100)
  IMPORTANTE: isso NÃO é número de votos faltantes; é só um proxy de escala;
- swing posterior Lula-vs-Flavio.

Saídas:
  data/forensics/analysis/phase3h_late_counting_by_uf.csv
  data/forensics/analysis/phase3h_summary.json
"""

import csv
import hashlib
import json
import math
import os
import urllib.request
from pathlib import Path

ROOT = Path("data/forensics")
RAW = ROOT / "external" / "vitoropereira-eleicoes2026"
OUT = ROOT / "analysis"
UA = "TSE-forensics-phase3h/1.0"

COMMIT = "10c03a7d52058a2650836953b612939ba02a3235"
SNAPSHOTS = [
    ("s1832", "snapshots/2026-10-04_1832_36.6pct/dados.json", "18:32"),
    ("s1906", "snapshots/2026-10-04_1906_64.8pct/dados.json", "19:06"),
    ("s1932", "snapshots/2026-10-04_1932_84.9pct/dados.json", "19:32"),
    ("s2047", "snapshots/2026-10-04_2047_93.2pct/dados.json", "20:47"),
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


def mean(xs):
    return sum(xs) / len(xs) if xs else None


def median(xs):
    xs = sorted(xs)
    if not xs:
        return None
    n = len(xs)
    if n % 2:
        return xs[n // 2]
    return (xs[n // 2 - 1] + xs[n // 2]) / 2.0


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

    snapshots = {}
    sources = []
    for key, relpath, label in SNAPSHOTS:
        url = (
            "https://raw.githubusercontent.com/vitoropereira/eleicoes2026/"
            f"{COMMIT}/{relpath}"
        )
        obj, meta = fetch_json(
            url,
            RAW / COMMIT / f"{key}.json",
        )
        meta["label"] = label
        snapshots[key] = obj
        sources.append(meta)

    by_uf = {}
    for key, obj in snapshots.items():
        for st in obj.get("states", []):
            uf = st.get("uf")
            if not uf or uf == "ZZ":
                continue
            by_uf.setdefault(uf, {})[key] = {
                "pst": float(st.get("pst", 0)),
                "te": int(st.get("te", 0)),
                "flavio": float(st.get("f", 0)),
                "lula": float(st.get("l", 0)),
                "ht": st.get("ht", ""),
            }

    rows = []
    for uf in sorted(by_uf):
        x = by_uf[uf]
        if not all(k in x for k, _, _ in SNAPSHOTS):
            continue

        base = x["s1906"]
        leader = (
            "Lula" if base["lula"] > base["flavio"]
            else "Flavio" if base["flavio"] > base["lula"]
            else "Empate"
        )
        margin = base["lula"] - base["flavio"]

        r = {
            "uf": uf,
            "leader_1906": leader,
            "lula_minus_flavio_1906_pp": margin,
            "electorate": base["te"],
        }

        for key, _, label in SNAPSHOTS:
            r[f"pst_{key}"] = x[key]["pst"]
            r[f"unreported_pct_{key}"] = 100.0 - x[key]["pst"]
            r[f"proxy_unreported_electorate_{key}"] = (
                base["te"] * (100.0 - x[key]["pst"]) / 100.0
            )

        for a, b, tag in [
            ("s1832", "s1906", "1832_1906"),
            ("s1906", "s1932", "1906_1932"),
            ("s1932", "s2047", "1932_2047"),
        ]:
            r[f"progress_pst_{tag}"] = x[b]["pst"] - x[a]["pst"]
            margin_a = x[a]["lula"] - x[a]["flavio"]
            margin_b = x[b]["lula"] - x[b]["flavio"]
            r[f"swing_lula_minus_flavio_{tag}_pp"] = margin_b - margin_a

        rows.append(r)

    lula = [r for r in rows if r["leader_1906"] == "Lula"]
    flavio = [r for r in rows if r["leader_1906"] == "Flavio"]

    def group_stats(group):
        total_electorate = sum(r["electorate"] for r in group)
        return {
            "n": len(group),
            "electorate_total": total_electorate,
            "pst_1906_mean": mean([r["pst_s1906"] for r in group]),
            "pst_1906_median": median([r["pst_s1906"] for r in group]),
            "pst_1932_mean": mean([r["pst_s1932"] for r in group]),
            "pst_1932_median": median([r["pst_s1932"] for r in group]),
            "unreported_pct_1906_median": median(
                [r["unreported_pct_s1906"] for r in group]
            ),
            "unreported_pct_1932_median": median(
                [r["unreported_pct_s1932"] for r in group]
            ),
            "progress_1906_1932_median": median(
                [r["progress_pst_1906_1932"] for r in group]
            ),
            "swing_1906_1932_median_pp": median(
                [r["swing_lula_minus_flavio_1906_1932_pp"] for r in group]
            ),
            "swing_1932_2047_median_pp": median(
                [r["swing_lula_minus_flavio_1932_2047_pp"] for r in group]
            ),
            "proxy_unreported_electorate_1906_sum": sum(
                r["proxy_unreported_electorate_s1906"] for r in group
            ),
            "proxy_unreported_electorate_1932_sum": sum(
                r["proxy_unreported_electorate_s1932"] for r in group
            ),
        }

    margins = [r["lula_minus_flavio_1906_pp"] for r in rows]
    pst1906 = [r["pst_s1906"] for r in rows]
    pst1932 = [r["pst_s1932"] for r in rows]
    un1906 = [r["unreported_pct_s1906"] for r in rows]
    un1932 = [r["unreported_pct_s1932"] for r in rows]
    swing12 = [r["swing_lula_minus_flavio_1906_1932_pp"] for r in rows]
    swing23 = [r["swing_lula_minus_flavio_1932_2047_pp"] for r in rows]

    summary = {
        "format": "tse-forensics-phase3h-late-counting-v1",
        "sources": sources,
        "question": (
            "UFs com Lula na frente estavam proporcionalmente menos apuradas e "
            "portanto tinham mais resultado relativo para entrar depois?"
        ),
        "groups": {
            "lula_led": group_stats(lula),
            "flavio_led": group_stats(flavio),
        },
        "correlations": {
            "spearman_lula_margin_vs_pst_1906": spearman(margins, pst1906),
            "spearman_lula_margin_vs_pst_1932": spearman(margins, pst1932),
            "spearman_unreported_1906_vs_swing_1906_1932": spearman(
                un1906, swing12
            ),
            "spearman_unreported_1932_vs_swing_1932_2047": spearman(
                un1932, swing23
            ),
        },
        "largest_unreported_pct_1906": sorted(
            [
                {
                    "uf": r["uf"],
                    "leader": r["leader_1906"],
                    "unreported_pct": r["unreported_pct_s1906"],
                    "margin_lula_minus_flavio_pp": r["lula_minus_flavio_1906_pp"],
                }
                for r in rows
            ],
            key=lambda x: x["unreported_pct"],
            reverse=True,
        )[:10],
        "interpretation_rules": [
            (
                "Menor pst nas UFs Lula-led sustenta uma forma de 'apuração tardia' "
                "geográfica, mesmo que não haja mais eventos técnicos de freeze."
            ),
            (
                "Proxy_unreported_electorate não é número de votos faltantes; serve "
                "apenas para comparar escala potencial entre grupos."
            ),
            (
                "Correlação entre parte não apurada e swing posterior mede associação "
                "descritiva, não causalidade."
            ),
        ],
    }

    fields = [
        "uf","leader_1906","lula_minus_flavio_1906_pp","electorate",
        "pst_s1832","unreported_pct_s1832","proxy_unreported_electorate_s1832",
        "pst_s1906","unreported_pct_s1906","proxy_unreported_electorate_s1906",
        "pst_s1932","unreported_pct_s1932","proxy_unreported_electorate_s1932",
        "pst_s2047","unreported_pct_s2047","proxy_unreported_electorate_s2047",
        "progress_pst_1832_1906","swing_lula_minus_flavio_1832_1906_pp",
        "progress_pst_1906_1932","swing_lula_minus_flavio_1906_1932_pp",
        "progress_pst_1932_2047","swing_lula_minus_flavio_1932_2047_pp",
    ]
    write_csv_atomic(OUT / "phase3h_late_counting_by_uf.csv", rows, fields)
    atomic_write(
        OUT / "phase3h_summary.json",
        json.dumps(summary, ensure_ascii=False, indent=2).encode("utf-8"),
    )

    print("\nFASE 3H — apuração tardia por composição geográfica")
    print(f"- UFs analisadas: {len(rows)}")
    print(
        f"- Lula-led: pst 19:06 mediana="
        f"{summary['groups']['lula_led']['pst_1906_median']:.2f}% · "
        f"pst 19:32 mediana={summary['groups']['lula_led']['pst_1932_median']:.2f}%"
    )
    print(
        f"- Flavio-led: pst 19:06 mediana="
        f"{summary['groups']['flavio_led']['pst_1906_median']:.2f}% · "
        f"pst 19:32 mediana={summary['groups']['flavio_led']['pst_1932_median']:.2f}%"
    )
    print(
        "- Spearman margem Lula x % apurado 19:06: "
        f"{summary['correlations']['spearman_lula_margin_vs_pst_1906']:.3f}"
    )
    print(
        "- Spearman margem Lula x % apurado 19:32: "
        f"{summary['correlations']['spearman_lula_margin_vs_pst_1932']:.3f}"
    )
    print(
        "- Spearman % não apurado 19:32 x swing 19:32→20:47: "
        f"{summary['correlations']['spearman_unreported_1932_vs_swing_1932_2047']:.3f}"
    )
    print(f"- CSV: {OUT / 'phase3h_late_counting_by_uf.csv'}")
    print(f"- resumo: {OUT / 'phase3h_summary.json'}")


if __name__ == "__main__":
    main()
