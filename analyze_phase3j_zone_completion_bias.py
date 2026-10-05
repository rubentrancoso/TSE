#!/usr/bin/env python3
"""Fase 3J — viés político do horário de conclusão das zonas eleitorais.

Pergunta:
Dentro da MESMA UF, zonas que concluíram mais tarde eram mais favoráveis a
Lula? E, se eram, esse padrão já existia em 2022?

A comparação dentro de cada UF reduz o efeito de composição entre estados que
a Fase 3H/3I mostrou ser importante.

Fonte:
ArvorCo/PNAD, zonas.json, commit fixado. O produto contém 6.106 pares
município-zona, resultado final de Presidente, horários de primeira seção e de
conclusão do arquivo da zona, e resultado de 2022 quando disponível.

Métricas por UF:
- Spearman: hora de conclusão x margem Lula-Flávio em 2026;
- Spearman: hora de conclusão x margem Lula-Bolsonaro no 1º turno de 2022;
- comparação do quartil de zonas que terminou primeiro com o quartil que
  terminou por último, somando votos (não média simples de percentuais).

Interpretação:
- correlação positiva em 2026 => zonas que concluem mais tarde tendem a ser
  relativamente mais Lula;
- se a mesma direção aparece em 2022, há evidência de uma ordenação geográfica
  estrutural pré-existente;
- se aparece apenas em 2026, o padrão merece aprofundamento.

Limitação:
"hora de conclusão da zona" é o instante em que entrou a última seção daquela
zona. Não informa o horário individual de chegada de todas as suas seções e
não permite atribuir exatamente uma zona inteira a um lote histórico.

Saídas:
  data/forensics/analysis/phase3j_zone_completion_by_uf.csv
  data/forensics/analysis/phase3j_zone_rows.csv
  data/forensics/analysis/phase3j_summary.json
"""

import csv
import hashlib
import json
import math
import os
import urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path("data/forensics")
RAW = ROOT / "external" / "ArvorCo-PNAD"
OUT = ROOT / "analysis"

COMMIT = "beb3bec9ae5c25e2868ee2f2cefb9e6dccd91415"
URL = (
    "https://raw.githubusercontent.com/ArvorCo/PNAD/"
    f"{COMMIT}/analysis/apuracao_2026/dados/zonas.json"
)
RAW_PATH = RAW / COMMIT / "zonas.json"
UA = "TSE-forensics-phase3j/1.0"

KEY_UFS = {"BA", "CE", "PE", "MA", "SP", "MG", "PA", "AM"}


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


def as_int(v):
    if v is None or v == "":
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def parse_dt(v):
    if not v:
        return None
    return datetime.strptime(v, "%Y-%m-%d %H:%M:%S")


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
    if len(x) < 2:
        return None
    return pearson(ranks(x), ranks(y))


def margin_pp(a, b, validos):
    if not validos:
        return None
    return 100.0 * (a - b) / validos


def aggregate(rows, year):
    if year == 2026:
        vv = sum(r["validos"] for r in rows)
        l = sum(r["lula"] for r in rows)
        f = sum(r["flavio"] for r in rows)
        return {
            "validos": vv,
            "lula": l,
            "right": f,
            "margin_lula_minus_right_pp": margin_pp(l, f, vv),
        }

    usable = [r for r in rows if r["validos_2022_1t"] is not None]
    vv = sum(r["validos_2022_1t"] for r in usable)
    l = sum(r["lula_2022_1t"] for r in usable)
    b = sum(r["bolsonaro_2022_1t"] for r in usable)
    return {
        "validos": vv,
        "lula": l,
        "right": b,
        "margin_lula_minus_right_pp": margin_pp(l, b, vv),
        "n_zonas": len(usable),
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

    raw_rows = table_rows(data["zonas"])
    rows = []

    for x in raw_rows:
        complete_dt = parse_dt(x.get("completa_gerado_brt"))
        vv = as_int(x.get("validos"))
        f = as_int(x.get("flavio"))
        l = as_int(x.get("lula"))
        if not x.get("completo") or complete_dt is None or not vv or f is None or l is None:
            continue

        vv22 = as_int(x.get("validos_2022_1t"))
        b22 = as_int(x.get("bolsonaro_2022_1t"))
        l22 = as_int(x.get("lula_2022_1t"))

        row = {
            "uf": x["uf"],
            "cd_tse": x["cd_tse"],
            "municipio": x["municipio"],
            "zona": x["zona"],
            "secoes": as_int(x.get("secoes")),
            "eleitores": as_int(x.get("eleitores")),
            "validos": vv,
            "flavio": f,
            "lula": l,
            "margin_lula_minus_flavio_2026_pp": margin_pp(l, f, vv),
            "primeira_secao_gerado_brt": x.get("primeira_secao_gerado_brt"),
            "completa_gerado_brt": x.get("completa_gerado_brt"),
            "complete_epoch": complete_dt.timestamp(),
            "validos_2022_1t": vv22,
            "bolsonaro_2022_1t": b22,
            "lula_2022_1t": l22,
            "margin_lula_minus_bolsonaro_2022_pp": (
                margin_pp(l22, b22, vv22)
                if vv22 and b22 is not None and l22 is not None
                else None
            ),
        }
        rows.append(row)

    by_uf = defaultdict(list)
    for r in rows:
        by_uf[r["uf"]].append(r)

    uf_rows = []
    national_early = []
    national_late = []

    for uf in sorted(by_uf):
        group = sorted(by_uf[uf], key=lambda r: r["complete_epoch"])
        n = len(group)
        if n < 4:
            continue

        q = max(1, n // 4)
        early = group[:q]
        late = group[-q:]
        national_early.extend(early)
        national_late.extend(late)

        sp26 = spearman(
            [r["complete_epoch"] for r in group],
            [r["margin_lula_minus_flavio_2026_pp"] for r in group],
        )

        g22 = [r for r in group if r["margin_lula_minus_bolsonaro_2022_pp"] is not None]
        sp22 = (
            spearman(
                [r["complete_epoch"] for r in g22],
                [r["margin_lula_minus_bolsonaro_2022_pp"] for r in g22],
            )
            if len(g22) >= 4 else None
        )

        e26 = aggregate(early, 2026)
        l26 = aggregate(late, 2026)
        e22 = aggregate(early, 2022)
        l22 = aggregate(late, 2022)

        uf_rows.append({
            "uf": uf,
            "n_zonas": n,
            "n_zonas_2022": len(g22),
            "first_complete_brt": group[0]["completa_gerado_brt"],
            "last_complete_brt": group[-1]["completa_gerado_brt"],
            "spearman_complete_vs_lula_margin_2026": sp26,
            "spearman_complete_vs_lula_margin_2022": sp22,
            "early_q_validos_2026": e26["validos"],
            "early_q_margin_lula_minus_flavio_2026_pp": e26["margin_lula_minus_right_pp"],
            "late_q_validos_2026": l26["validos"],
            "late_q_margin_lula_minus_flavio_2026_pp": l26["margin_lula_minus_right_pp"],
            "late_minus_early_margin_2026_pp": (
                l26["margin_lula_minus_right_pp"] - e26["margin_lula_minus_right_pp"]
            ),
            "early_q_validos_2022": e22["validos"],
            "early_q_margin_lula_minus_bolsonaro_2022_pp": e22["margin_lula_minus_right_pp"],
            "late_q_validos_2022": l22["validos"],
            "late_q_margin_lula_minus_bolsonaro_2022_pp": l22["margin_lula_minus_right_pp"],
            "late_minus_early_margin_2022_pp": (
                l22["margin_lula_minus_right_pp"] - e22["margin_lula_minus_right_pp"]
                if e22["margin_lula_minus_right_pp"] is not None
                and l22["margin_lula_minus_right_pp"] is not None
                else None
            ),
        })

    agg_e26 = aggregate(national_early, 2026)
    agg_l26 = aggregate(national_late, 2026)
    agg_e22 = aggregate(national_early, 2022)
    agg_l22 = aggregate(national_late, 2022)

    valid_sp26 = [r["spearman_complete_vs_lula_margin_2026"] for r in uf_rows if r["spearman_complete_vs_lula_margin_2026"] is not None]
    valid_sp22 = [r["spearman_complete_vs_lula_margin_2022"] for r in uf_rows if r["spearman_complete_vs_lula_margin_2022"] is not None]

    summary = {
        "format": "tse-forensics-phase3j-zone-completion-bias-v1",
        "source": source,
        "source_metadata": {
            "n_zonas_reported": data.get("n"),
            "n_incompletas_reported": data.get("n_incompletas"),
            "n_sem_2022_reported": data.get("n_sem_2022"),
            "usable_complete_zones": len(rows),
        },
        "uf_summary": {
            "n_ufs": len(uf_rows),
            "median_spearman_complete_vs_lula_margin_2026": median(valid_sp26),
            "ufs_positive_spearman_2026": sum(1 for x in valid_sp26 if x > 0),
            "ufs_negative_spearman_2026": sum(1 for x in valid_sp26 if x < 0),
            "median_spearman_complete_vs_lula_margin_2022": median(valid_sp22),
            "ufs_positive_spearman_2022": sum(1 for x in valid_sp22 if x > 0),
            "ufs_negative_spearman_2022": sum(1 for x in valid_sp22 if x < 0),
        },
        "pooled_within_uf_quartiles": {
            "early_2026": agg_e26,
            "late_2026": agg_l26,
            "late_minus_early_2026_pp": (
                agg_l26["margin_lula_minus_right_pp"] - agg_e26["margin_lula_minus_right_pp"]
            ),
            "early_2022": agg_e22,
            "late_2022": agg_l22,
            "late_minus_early_2022_pp": (
                agg_l22["margin_lula_minus_right_pp"] - agg_e22["margin_lula_minus_right_pp"]
            ),
        },
        "key_ufs": [
            r for r in uf_rows if r["uf"] in KEY_UFS
        ],
        "largest_positive_2026_late_minus_early": sorted(
            uf_rows, key=lambda r: r["late_minus_early_margin_2026_pp"], reverse=True
        )[:10],
        "largest_negative_2026_late_minus_early": sorted(
            uf_rows, key=lambda r: r["late_minus_early_margin_2026_pp"]
        )[:10],
        "interpretation_rules": [
            (
                "Positive late_minus_early_margin_2026_pp means zones finishing later "
                "were more Lula-favorable than zones finishing earlier within that UF."
            ),
            (
                "A similar sign and magnitude in 2022 supports a structural geographic "
                "ordering explanation rather than a pattern unique to 2026."
            ),
            (
                "Completion time is not the arrival time of every section; this phase "
                "tests geographic ordering, not exact membership of the 19:14/20:04 batches."
            ),
        ],
    }

    write_csv_atomic(
        OUT / "phase3j_zone_completion_by_uf.csv",
        uf_rows,
        [
            "uf","n_zonas","n_zonas_2022","first_complete_brt","last_complete_brt",
            "spearman_complete_vs_lula_margin_2026",
            "spearman_complete_vs_lula_margin_2022",
            "early_q_validos_2026","early_q_margin_lula_minus_flavio_2026_pp",
            "late_q_validos_2026","late_q_margin_lula_minus_flavio_2026_pp",
            "late_minus_early_margin_2026_pp",
            "early_q_validos_2022","early_q_margin_lula_minus_bolsonaro_2022_pp",
            "late_q_validos_2022","late_q_margin_lula_minus_bolsonaro_2022_pp",
            "late_minus_early_margin_2022_pp",
        ],
    )

    zone_rows_out = [
        {k: v for k, v in r.items() if k != "complete_epoch"}
        for r in rows
    ]
    write_csv_atomic(
        OUT / "phase3j_zone_rows.csv",
        zone_rows_out,
        [
            "uf","cd_tse","municipio","zona","secoes","eleitores","validos",
            "flavio","lula","margin_lula_minus_flavio_2026_pp",
            "primeira_secao_gerado_brt","completa_gerado_brt",
            "validos_2022_1t","bolsonaro_2022_1t","lula_2022_1t",
            "margin_lula_minus_bolsonaro_2022_pp",
        ],
    )

    atomic_write(
        OUT / "phase3j_summary.json",
        json.dumps(summary, ensure_ascii=False, indent=2).encode("utf-8"),
    )

    u = summary["uf_summary"]
    p = summary["pooled_within_uf_quartiles"]
    print("\\nFASE 3J — conclusão das zonas x inclinação presidencial")
    print(f"- zonas completas utilizáveis: {len(rows)}")
    print(
        f"- UFs Spearman positivo em 2026: {u['ufs_positive_spearman_2026']}/"
        f"{u['n_ufs']} · mediana rho={u['median_spearman_complete_vs_lula_margin_2026']:.3f}"
    )
    if u["median_spearman_complete_vs_lula_margin_2022"] is not None:
        print(
            f"- UFs Spearman positivo em 2022: {u['ufs_positive_spearman_2022']}/"
            f"{u['n_ufs']} · mediana rho={u['median_spearman_complete_vs_lula_margin_2022']:.3f}"
        )
    print(
        "- quartis dentro das UFs, 2026: late-early="
        f"{p['late_minus_early_2026_pp']:+.2f} pp de margem Lula-direita"
    )
    print(
        "- mesmas zonas, 2022: late-early="
        f"{p['late_minus_early_2022_pp']:+.2f} pp de margem Lula-direita"
    )
    print(f"- por UF: {OUT / 'phase3j_zone_completion_by_uf.csv'}")
    print(f"- zonas: {OUT / 'phase3j_zone_rows.csv'}")
    print(f"- resumo: {OUT / 'phase3j_summary.json'}")


if __name__ == "__main__":
    main()
