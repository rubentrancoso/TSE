#!/usr/bin/env python3
"""Fase 3E — benchmark empírico dos lotes presidenciais.

Pergunta:
Os dois grandes lotes de atualização nacional foram estatisticamente
"anormais" porque os candidatos fora do top 2 quase não mudaram em
percentual enquanto os dois primeiros mudaram bastante?

Em vez de assumir uma distribuição multinomial aleatória, este teste usa
como referência EMPÍRICA todos os lotes nacionais genuínos preservados na
mesma noite eleitoral. Isso evita a hipótese falsa de que seções chegam em
ordem aleatória.

Métricas por lote:
- RMS da mudança em pontos percentuais dos candidatos fora do top 2;
- maior mudança absoluta entre candidatos fora do top 2;
- RMS da mudança dos dois primeiros;
- razão top2_RMS / minor_RMS;
- percentil empírico dos dois catch-ups entre todos os lotes e entre lotes
  grandes (>= 1 milhão de votos válidos adicionados).

Saídas:
  data/forensics/analysis/phase3e_batch_benchmark.csv
  data/forensics/analysis/phase3e_target_percentiles.csv
  data/forensics/analysis/phase3e_summary.json
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
UA = "TSE-forensics-phase3e/1.0"

MINOR = ["cury", "renan", "caiado", "outros"]
ALL = ["flavio", "lula"] + MINOR

TARGETS = {
    "catchup_1": "2026-10-04 19:14:08",
    "catchup_2": "2026-10-04 20:04:39",
}

LARGE_THRESHOLD = 1_000_000


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


def percentile_le(values, x):
    if not values:
        return None
    return 100.0 * sum(1 for v in values if v <= x) / len(values)


def compute_metrics(row):
    d_vv = int(row["d_vv"])
    vv = int(row["vv"])
    prev_vv = vv - d_vv
    if d_vv <= 0 or prev_vv <= 0:
        return None

    pp = {}
    for g in ALL:
        end = int(row[g])
        delta = int(row[f"d_{g}"])
        start = end - delta
        prior_share = 100.0 * start / prev_vv
        batch_share = 100.0 * delta / d_vv
        pp[g] = batch_share - prior_share

    minor_rms = math.sqrt(sum(pp[g] ** 2 for g in MINOR) / len(MINOR))
    top2_rms = math.sqrt((pp["flavio"] ** 2 + pp["lula"] ** 2) / 2)
    minor_max = max(abs(pp[g]) for g in MINOR)

    return {
        "generated_brt": row["gerado_brt"],
        "d_sections": int(row["d_st"]),
        "d_valid_votes": d_vv,
        "minutes_since_previous": row["minutos_desde_anterior"],
        "minor_rms_pp": minor_rms,
        "minor_max_abs_pp": minor_max,
        "top2_rms_pp": top2_rms,
        "top2_to_minor_rms_ratio": top2_rms / minor_rms if minor_rms else None,
        "flavio_change_pp": pp["flavio"],
        "lula_change_pp": pp["lula"],
        "cury_change_pp": pp["cury"],
        "renan_change_pp": pp["renan"],
        "caiado_change_pp": pp["caiado"],
        "others_change_pp": pp["outros"],
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data, source = fetch()

    versions = table_rows(data["nacional"]["versoes"])
    batches = []
    for row in versions:
        if row.get("marcada_regressiva"):
            continue
        m = compute_metrics(row)
        if m:
            batches.append(m)

    if not batches:
        raise RuntimeError("Nenhum lote válido encontrado.")

    large = [b for b in batches if b["d_valid_votes"] >= LARGE_THRESHOLD]

    write_csv(
        OUT / "phase3e_batch_benchmark.csv",
        batches,
        [
            "generated_brt","d_sections","d_valid_votes","minutes_since_previous",
            "minor_rms_pp","minor_max_abs_pp","top2_rms_pp",
            "top2_to_minor_rms_ratio","flavio_change_pp","lula_change_pp",
            "cury_change_pp","renan_change_pp","caiado_change_pp",
            "others_change_pp",
        ],
    )

    all_minor = [b["minor_rms_pp"] for b in batches]
    all_ratio = [b["top2_to_minor_rms_ratio"] for b in batches if b["top2_to_minor_rms_ratio"] is not None]
    large_minor = [b["minor_rms_pp"] for b in large]
    large_ratio = [b["top2_to_minor_rms_ratio"] for b in large if b["top2_to_minor_rms_ratio"] is not None]

    targets = []
    for name, when in TARGETS.items():
        b = next((x for x in batches if x["generated_brt"] == when), None)
        if not b:
            raise RuntimeError(f"Lote alvo não encontrado: {when}")
        row = dict(b)
        row.update({
            "target": name,
            "minor_rms_percentile_all": percentile_le(all_minor, b["minor_rms_pp"]),
            "minor_rms_percentile_large": percentile_le(large_minor, b["minor_rms_pp"]),
            "ratio_percentile_all": percentile_le(all_ratio, b["top2_to_minor_rms_ratio"]),
            "ratio_percentile_large": percentile_le(large_ratio, b["top2_to_minor_rms_ratio"]),
        })
        targets.append(row)

    write_csv(
        OUT / "phase3e_target_percentiles.csv",
        targets,
        [
            "target","generated_brt","d_sections","d_valid_votes",
            "minor_rms_pp","minor_max_abs_pp","top2_rms_pp",
            "top2_to_minor_rms_ratio",
            "minor_rms_percentile_all","minor_rms_percentile_large",
            "ratio_percentile_all","ratio_percentile_large",
            "flavio_change_pp","lula_change_pp","cury_change_pp",
            "renan_change_pp","caiado_change_pp","others_change_pp",
        ],
    )

    summary = {
        "format": "tse-forensics-phase3e-batch-benchmark-v1",
        "source": source,
        "reference_population": {
            "genuine_non_regressive_batches": len(batches),
            "large_batches_threshold_valid_votes": LARGE_THRESHOLD,
            "large_batches": len(large),
        },
        "targets": targets,
        "interpretation": [
            (
                "Percentil baixo de minor_rms significa que os candidatos menores "
                "mudaram menos em pontos percentuais do que na maioria dos lotes; "
                "percentil alto significa o contrário."
            ),
            (
                "A razão top2/minor mede quanto a redistribuição entre os dois "
                "primeiros dominou a mudança percentual em relação aos menores."
            ),
            (
                "Este benchmark usa a própria noite eleitoral como controle empírico "
                "e não presume ordem aleatória das seções."
            ),
            (
                "Mesmo assim, o benchmark nacional não substitui o teste condicionado "
                "por UF/município/seção; composição geográfica pode produzir diferenças "
                "grandes entre lotes."
            ),
        ],
    }

    (OUT / "phase3e_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("\nFASE 3E — benchmark empírico dos lotes nacionais")
    print(f"- lotes genuínos analisados: {len(batches)}")
    print(f"- lotes >= {LARGE_THRESHOLD:,} válidos: {len(large)}")
    for t in targets:
        print(
            f"- {t['target']} {t['generated_brt']}: "
            f"minor RMS={t['minor_rms_pp']:.4f} pp "
            f"(percentil {t['minor_rms_percentile_large']:.1f} entre grandes) · "
            f"top2/minor={t['top2_to_minor_rms_ratio']:.2f} "
            f"(percentil {t['ratio_percentile_large']:.1f} entre grandes)"
        )
    print(f"- CSV lotes: {OUT / 'phase3e_batch_benchmark.csv'}")
    print(f"- CSV alvos: {OUT / 'phase3e_target_percentiles.csv'}")
    print(f"- resumo: {OUT / 'phase3e_summary.json'}")


if __name__ == "__main__":
    main()
