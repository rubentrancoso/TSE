#!/usr/bin/env python3
"""Fase 3F — benchmark por janelas agregadas de tamanho comparável.

Objetivo:
Comparar os dois grandes catch-ups presidenciais com janelas "normais"
formadas pela soma de lotes consecutivos, evitando a comparação injusta com
lotes muito menores.

Referência:
- versões nacionais genuínas e não regressivas da mesma noite;
- janelas não podem conter os dois catch-ups;
- a soma de votos válidos da janela deve ficar entre 80% e 120% do tamanho
  do catch-up-alvo;
- uma lacuna interna > 15 minutos encerra a janela candidata.

As janelas se sobrepõem. Portanto os percentis são descritivos e NÃO são
p-valores nem observações independentes.

Saídas:
  data/forensics/analysis/phase3f_matched_windows.csv
  data/forensics/analysis/phase3f_targets.csv
  data/forensics/analysis/phase3f_summary.json
"""

import csv
import json
import hashlib
import math
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
UA = "TSE-forensics-phase3f/1.0"

MINOR = ["cury", "renan", "caiado", "outros"]
ALL = ["flavio", "lula"] + MINOR
TARGETS = {
    "catchup_1": "2026-10-04 19:14:08",
    "catchup_2": "2026-10-04 20:04:39",
}
LOW = 0.80
HIGH = 1.20
MAX_INTERNAL_GAP_MIN = 15.0


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


def as_int(v):
    if v is None or v == "":
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def as_float(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def valid_batch(row):
    if row.get("marcada_regressiva"):
        return False
    d_vv = as_int(row.get("d_vv"))
    vv = as_int(row.get("vv"))
    d_st = as_int(row.get("d_st"))
    if d_vv is None or vv is None or d_st is None or d_vv <= 0 or vv <= d_vv:
        return False
    for g in ALL:
        if as_int(row.get(g)) is None or as_int(row.get(f"d_{g}")) is None:
            return False
    return True


def metric_from_rows(rows):
    first = rows[0]
    last = rows[-1]
    d_vv = sum(as_int(r["d_vv"]) for r in rows)
    end_vv = as_int(last["vv"])
    start_vv = end_vv - d_vv
    d_st = sum(as_int(r["d_st"]) for r in rows)

    pp = {}
    deltas = {}
    for g in ALL:
        d = sum(as_int(r[f"d_{g}"]) for r in rows)
        end = as_int(last[g])
        start = end - d
        prior_share = 100.0 * start / start_vv
        window_share = 100.0 * d / d_vv
        pp[g] = window_share - prior_share
        deltas[g] = d

    minor_rms = math.sqrt(sum(pp[g] ** 2 for g in MINOR) / len(MINOR))
    top2_rms = math.sqrt((pp["flavio"] ** 2 + pp["lula"] ** 2) / 2.0)

    return {
        "start_brt": first["gerado_brt"],
        "end_brt": last["gerado_brt"],
        "n_batches": len(rows),
        "d_sections": d_st,
        "d_valid_votes": d_vv,
        "minor_rms_pp": minor_rms,
        "minor_max_abs_pp": max(abs(pp[g]) for g in MINOR),
        "top2_rms_pp": top2_rms,
        "top2_to_minor_rms_ratio": top2_rms / minor_rms if minor_rms else None,
        "flavio_change_pp": pp["flavio"],
        "lula_change_pp": pp["lula"],
        "cury_change_pp": pp["cury"],
        "renan_change_pp": pp["renan"],
        "caiado_change_pp": pp["caiado"],
        "others_change_pp": pp["outros"],
    }


def percentile_le(values, x):
    if not values:
        return None
    return 100.0 * sum(1 for v in values if v <= x) / len(values)


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

    versions = [r for r in table_rows(data["nacional"]["versoes"]) if valid_batch(r)]
    by_time = {r["gerado_brt"]: r for r in versions}
    target_times = set(TARGETS.values())

    target_metrics = {}
    for name, when in TARGETS.items():
        row = by_time.get(when)
        if not row:
            raise RuntimeError(f"Catch-up não encontrado: {when}")
        target_metrics[name] = metric_from_rows([row])

    all_window_rows = []
    target_rows = []

    for target_name, target in target_metrics.items():
        low = target["d_valid_votes"] * LOW
        high = target["d_valid_votes"] * HIGH
        refs = []

        for i in range(len(versions)):
            window = []
            total = 0

            for k in range(i, len(versions)):
                row = versions[k]

                if row["gerado_brt"] in target_times:
                    break

                gap = as_float(row.get("minutos_desde_anterior"))
                if window and gap is not None and gap > MAX_INTERNAL_GAP_MIN:
                    break

                window.append(row)
                total += as_int(row["d_vv"])

                if total >= low:
                    if total <= high:
                        refs.append(metric_from_rows(window))
                    break

        for idx, r in enumerate(refs, start=1):
            row = {
                "target": target_name,
                "reference_id": idx,
                **r,
            }
            all_window_rows.append(row)

        minor_vals = [r["minor_rms_pp"] for r in refs]
        top2_vals = [r["top2_rms_pp"] for r in refs]
        ratio_vals = [
            r["top2_to_minor_rms_ratio"] for r in refs
            if r["top2_to_minor_rms_ratio"] is not None
        ]

        target_rows.append({
            "target": target_name,
            **target,
            "reference_windows": len(refs),
            "minor_rms_percentile_matched": percentile_le(
                minor_vals, target["minor_rms_pp"]
            ),
            "top2_rms_percentile_matched": percentile_le(
                top2_vals, target["top2_rms_pp"]
            ),
            "ratio_percentile_matched": percentile_le(
                ratio_vals, target["top2_to_minor_rms_ratio"]
            ),
        })

    fields_windows = [
        "target","reference_id","start_brt","end_brt","n_batches",
        "d_sections","d_valid_votes","minor_rms_pp","minor_max_abs_pp",
        "top2_rms_pp","top2_to_minor_rms_ratio","flavio_change_pp",
        "lula_change_pp","cury_change_pp","renan_change_pp",
        "caiado_change_pp","others_change_pp",
    ]
    write_csv_atomic(
        OUT / "phase3f_matched_windows.csv", all_window_rows, fields_windows
    )

    fields_targets = [
        "target","start_brt","end_brt","n_batches","d_sections","d_valid_votes",
        "minor_rms_pp","minor_max_abs_pp","top2_rms_pp",
        "top2_to_minor_rms_ratio","reference_windows",
        "minor_rms_percentile_matched","top2_rms_percentile_matched",
        "ratio_percentile_matched","flavio_change_pp","lula_change_pp",
        "cury_change_pp","renan_change_pp","caiado_change_pp",
        "others_change_pp",
    ]
    write_csv_atomic(
        OUT / "phase3f_targets.csv", target_rows, fields_targets
    )

    summary = {
        "format": "tse-forensics-phase3f-matched-window-v1",
        "source": source,
        "matching_rule": {
            "low_fraction_of_target_votes": LOW,
            "high_fraction_of_target_votes": HIGH,
            "max_internal_gap_minutes": MAX_INTERNAL_GAP_MIN,
            "catchups_excluded_from_reference_windows": True,
            "windows_overlap": True,
        },
        "targets": target_rows,
        "interpretation": [
            (
                "Percentis são benchmarks descritivos; janelas sobrepostas não são "
                "amostras independentes."
            ),
            (
                "Percentil 100 de minor_rms significa que o movimento percentual dos "
                "candidatos menores no catch-up foi maior que em todas as janelas "
                "comparáveis, não que eles ficaram congelados."
            ),
            (
                "Percentil alto da razão top2/menores indica concentração relativa da "
                "mudança nos dois primeiros, mas não identifica causa."
            ),
            (
                "O controle ainda não condiciona por composição geográfica exata das "
                "seções; essa continua sendo a limitação principal."
            ),
        ],
    }

    atomic_write(
        OUT / "phase3f_summary.json",
        json.dumps(summary, ensure_ascii=False, indent=2).encode("utf-8"),
    )

    print("\nFASE 3F — janelas agregadas de tamanho comparável")
    for t in target_rows:
        print(
            f"- {t['target']}: refs={t['reference_windows']} · "
            f"minor RMS pct={t['minor_rms_percentile_matched']:.1f} · "
            f"top2 RMS pct={t['top2_rms_percentile_matched']:.1f} · "
            f"ratio pct={t['ratio_percentile_matched']:.1f}"
        )
    print(f"- janelas: {OUT / 'phase3f_matched_windows.csv'}")
    print(f"- alvos: {OUT / 'phase3f_targets.csv'}")
    print(f"- resumo: {OUT / 'phase3f_summary.json'}")


if __name__ == "__main__":
    main()
