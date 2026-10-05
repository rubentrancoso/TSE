#!/usr/bin/env python3
"""Fase 4G — certificado determinístico da monotonicidade pós-retomada.

Pergunta
========
A sequência pós-20:04:39 (Lula sempre sobe; Flávio sempre desce) exige uma
ordem específica de publicação dos lotes ou é consequência da composição dos
próprios lotes que restavam?

Fonte
=====
ArvorCo/PNAD, linha_do_tempo.json, commit fixado:
beb3bec9ae5c25e2868ee2f2cefb9e6dccd91415

Usamos versões nacionais genuínas (não regressivas) e DERIVAMOS os incrementos
diretamente dos totais cumulativos consecutivos:
  d_vv = vv_t - vv_(t-1)
  d_lula = lula_t - lula_(t-1)
  d_flavio = flavio_t - flavio_(t-1)

Isso evita depender de campos de delta produzidos por outra sequência de
linhas e elimina o arredondamento de pct_lula/pct_flavio.

Certificado de ordem
====================
Para Lula, uma nova batelada reduz a participação acumulada somente se:
  share_lote_Lula < share_acumulada_anterior.

O caso mais adverso para uma batelada de share baixo é publicar antes dela
todas as bateladas de share Lula MAIOR. Portanto ordenamos as bateladas por
share Lula decrescente e verificamos se TODAS ainda elevam o acumulado.

Se isso for verdadeiro, qualquer outra permutação também é monotônica para
Lula.

Para Flávio, o caso adverso é o inverso: ordenamos as bateladas por share
Flávio crescente, que minimiza o acumulado antes de cada batelada de share
maior. Se mesmo assim cada lote reduz o acumulado, qualquer permutação também
reduz.

Saídas
======
  data/forensics/analysis/phase4g_post_resume_batches.csv
  data/forensics/analysis/phase4g_summary.json
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
UA = "TSE-forensics-phase4g/1.0"

COMMIT = "beb3bec9ae5c25e2868ee2f2cefb9e6dccd91415"
URL = (
    "https://raw.githubusercontent.com/ArvorCo/PNAD/"
    f"{COMMIT}/analysis/apuracao_2026/dados/linha_do_tempo.json"
)
RAW_PATH = RAW / COMMIT / "linha_do_tempo.json"
RESUME = "2026-10-04 20:04:39"


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


def simulate_order(start_vv, start_votes, batches, candidate, descending):
    share_key = f"{candidate}_batch_share_pct"
    vote_key = f"d_{candidate}"

    ordered = sorted(
        batches,
        key=lambda r: r[share_key],
        reverse=descending,
    )

    vv = start_vv
    votes = start_votes
    failures = []
    minimum_headroom_pp = None

    for pos, b in enumerate(ordered, start=1):
        cumulative_before = pct(votes, vv)
        batch_share = b[share_key]

        if candidate == "lula":
            headroom = batch_share - cumulative_before
            good = headroom > 0
        else:
            headroom = cumulative_before - batch_share
            good = headroom > 0

        if minimum_headroom_pp is None or headroom < minimum_headroom_pp:
            minimum_headroom_pp = headroom

        if not good:
            failures.append({
                "position": pos,
                "generated_brt": b["generated_brt"],
                "cumulative_before_pct": cumulative_before,
                "batch_share_pct": batch_share,
                "headroom_pp": headroom,
            })

        vv += b["d_vv"]
        votes += b[vote_key]

    return {
        "candidate": candidate,
        "adversarial_sort": (
            "batch share descending"
            if descending
            else "batch share ascending"
        ),
        "batches": len(ordered),
        "failures": failures,
        "failure_count": len(failures),
        "minimum_headroom_pp": minimum_headroom_pp,
        "final_simulated_pct": pct(votes, vv),
    }


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
        raise RuntimeError(f"Retomada {RESUME} não encontrada.")

    post = rows[resume_idx:]
    start = post[0]
    final = post[-1]

    start_vv = int(start["vv"])
    start_lula = int(start["lula"])
    start_flavio = int(start["flavio"])

    batches = []
    for i in range(1, len(post)):
        prev = post[i - 1]
        cur = post[i]

        d_vv = int(cur["vv"]) - int(prev["vv"])
        d_lula = int(cur["lula"]) - int(prev["lula"])
        d_flavio = int(cur["flavio"]) - int(prev["flavio"])
        d_st = int(cur["st"]) - int(prev["st"])

        if min(d_vv, d_lula, d_flavio, d_st) < 0:
            raise RuntimeError(
                f"Delta negativo entre {prev['gerado_brt']} e "
                f"{cur['gerado_brt']}"
            )
        if d_vv <= 0:
            raise RuntimeError(
                f"Delta vv não positivo em {cur['gerado_brt']}: {d_vv}"
            )

        lula_batch = pct(d_lula, d_vv)
        flavio_batch = pct(d_flavio, d_vv)

        lula_before = pct(int(prev["lula"]), int(prev["vv"]))
        lula_after = pct(int(cur["lula"]), int(cur["vv"]))
        flavio_before = pct(int(prev["flavio"]), int(prev["vv"]))
        flavio_after = pct(int(cur["flavio"]), int(cur["vv"]))

        batches.append({
            "from_brt": prev["gerado_brt"],
            "generated_brt": cur["gerado_brt"],
            "d_sections": d_st,
            "d_vv": d_vv,
            "d_lula": d_lula,
            "d_flavio": d_flavio,
            "lula_batch_share_pct": lula_batch,
            "flavio_batch_share_pct": flavio_batch,
            "lula_minus_flavio_batch_margin_pp": lula_batch - flavio_batch,
            "lula_exact_pct_before": lula_before,
            "lula_exact_pct_after": lula_after,
            "lula_exact_change_pp": lula_after - lula_before,
            "flavio_exact_pct_before": flavio_before,
            "flavio_exact_pct_after": flavio_after,
            "flavio_exact_change_pp": flavio_after - flavio_before,
            "lula_increases_exact": lula_after > lula_before,
            "flavio_decreases_exact": flavio_after < flavio_before,
        })

    start_lula_pct = pct(start_lula, start_vv)
    start_flavio_pct = pct(start_flavio, start_vv)
    final_lula_pct = pct(int(final["lula"]), int(final["vv"]))
    final_flavio_pct = pct(int(final["flavio"]), int(final["vv"]))

    remaining_vv = int(final["vv"]) - start_vv
    remaining_lula = int(final["lula"]) - start_lula
    remaining_flavio = int(final["flavio"]) - start_flavio

    cert_lula = simulate_order(
        start_vv, start_lula, batches, "lula", descending=True
    )
    cert_flavio = simulate_order(
        start_vv, start_flavio, batches, "flavio", descending=False
    )

    summary = {
        "format": "tse-forensics-phase4g-order-invariance-v1",
        "source": source,
        "window": {
            "start_brt": start["gerado_brt"],
            "end_brt": final["gerado_brt"],
            "batches": len(batches),
            "start_valid_votes": start_vv,
            "final_valid_votes": int(final["vv"]),
            "remaining_valid_votes": remaining_vv,
        },
        "exact_cumulative": {
            "lula_start_pct": start_lula_pct,
            "lula_final_pct": final_lula_pct,
            "lula_strict_increases": sum(
                r["lula_increases_exact"] for r in batches
            ),
            "lula_non_increases": sum(
                not r["lula_increases_exact"] for r in batches
            ),
            "flavio_start_pct": start_flavio_pct,
            "flavio_final_pct": final_flavio_pct,
            "flavio_strict_decreases": sum(
                r["flavio_decreases_exact"] for r in batches
            ),
            "flavio_non_decreases": sum(
                not r["flavio_decreases_exact"] for r in batches
            ),
            "note": (
                "Percentuais recalculados dos votos inteiros cumulativos. "
                "Os 2 'empates' da Fase 4F eram arredondamento do campo pct "
                "a quatro casas; nos totais exatos são mudanças estritas."
            ),
        },
        "remaining_pool": {
            "valid_votes": remaining_vv,
            "lula_votes": remaining_lula,
            "flavio_votes": remaining_flavio,
            "lula_share_pct": pct(remaining_lula, remaining_vv),
            "flavio_share_pct": pct(remaining_flavio, remaining_vv),
            "lula_minus_flavio_margin_pp": (
                pct(remaining_lula, remaining_vv)
                - pct(remaining_flavio, remaining_vv)
            ),
        },
        "batch_distribution": {
            "all_batches_lula_gt_flavio": all(
                r["lula_batch_share_pct"] > r["flavio_batch_share_pct"]
                for r in batches
            ),
            "batches_lula_gt_flavio": sum(
                r["lula_batch_share_pct"] > r["flavio_batch_share_pct"]
                for r in batches
            ),
            "min_lula_batch_share_pct": min(
                r["lula_batch_share_pct"] for r in batches
            ),
            "max_lula_batch_share_pct": max(
                r["lula_batch_share_pct"] for r in batches
            ),
            "min_flavio_batch_share_pct": min(
                r["flavio_batch_share_pct"] for r in batches
            ),
            "max_flavio_batch_share_pct": max(
                r["flavio_batch_share_pct"] for r in batches
            ),
            "min_lula_minus_flavio_batch_margin_pp": min(
                r["lula_minus_flavio_batch_margin_pp"] for r in batches
            ),
        },
        "order_invariance_certificate": {
            "lula_adversarial_order": cert_lula,
            "flavio_adversarial_order": cert_flavio,
            "monotonic_for_any_permutation": (
                cert_lula["failure_count"] == 0
                and cert_flavio["failure_count"] == 0
            ),
            "logic": [
                (
                    "Para Lula, ordenar os lotes por share Lula decrescente "
                    "maximiza o acumulado antes de cada lote de share menor. "
                    "Se nem nessa ordem um lote reduz o acumulado, nenhuma "
                    "outra ordem reduz."
                ),
                (
                    "Para Flávio, ordenar por share Flávio crescente minimiza "
                    "o acumulado antes de cada lote de share maior. Se nem "
                    "nessa ordem um lote eleva o acumulado, nenhuma outra "
                    "ordem eleva."
                ),
            ],
        },
        "interpretation": [
            (
                "A sequência de 152 mudanças no mesmo sentido é real quando "
                "calculada diretamente dos votos inteiros."
            ),
            (
                "Condicionando ao conjunto exato de lotes que restou após "
                "20:04:39, a monotonicidade não depende da ordem observada se "
                "o certificado adversarial fechar sem falhas."
            ),
            (
                "Nesse caso não faz sentido aplicar (1/2)^152 como probabilidade "
                "de uma 'sequência aleatória de caras/coroas': os lotes não são "
                "eventos equiprováveis nem independentes e têm composição "
                "geográfica sistemática."
            ),
            (
                "A pergunta causal relevante passa a ser por que o conjunto "
                "remanescente era tão mais favorável a Lula. Fases 3J/3K "
                "mostraram que zonas tardias já tinham viés pró-Lula em 2022."
            ),
        ],
    }

    fields = [
        "from_brt","generated_brt","d_sections","d_vv","d_lula","d_flavio",
        "lula_batch_share_pct","flavio_batch_share_pct",
        "lula_minus_flavio_batch_margin_pp",
        "lula_exact_pct_before","lula_exact_pct_after","lula_exact_change_pp",
        "flavio_exact_pct_before","flavio_exact_pct_after",
        "flavio_exact_change_pp","lula_increases_exact",
        "flavio_decreases_exact",
    ]
    write_csv_atomic(
        OUT / "phase4g_post_resume_batches.csv",
        batches,
        fields,
    )
    atomic_write(
        OUT / "phase4g_summary.json",
        json.dumps(summary, ensure_ascii=False, indent=2).encode("utf-8"),
    )

    print("\nFASE 4G — certificado da monotonicidade pós-retomada")
    print(
        f"- lotes: {len(batches)} · Lula sobe exato "
        f"{summary['exact_cumulative']['lula_strict_increases']}/{len(batches)} "
        f"· Flávio desce exato "
        f"{summary['exact_cumulative']['flavio_strict_decreases']}/{len(batches)}"
    )
    print(
        "- pool restante: Lula="
        f"{summary['remaining_pool']['lula_share_pct']:.4f}% · "
        "Flávio="
        f"{summary['remaining_pool']['flavio_share_pct']:.4f}%"
    )
    print(
        "- shares dos lotes: Lula min="
        f"{summary['batch_distribution']['min_lula_batch_share_pct']:.4f}% · "
        "Flávio max="
        f"{summary['batch_distribution']['max_flavio_batch_share_pct']:.4f}%"
    )
    print(
        "- todos os lotes Lula>Flávio: "
        f"{summary['batch_distribution']['all_batches_lula_gt_flavio']}"
    )
    print(
        "- certificado qualquer permutação monotônica: "
        f"{summary['order_invariance_certificate']['monotonic_for_any_permutation']}"
    )
    print(
        "- headroom adversarial mínimo Lula="
        f"{cert_lula['minimum_headroom_pp']:.6f} pp · "
        "Flávio="
        f"{cert_flavio['minimum_headroom_pp']:.6f} pp"
    )
    print(f"- CSV: {OUT / 'phase4g_post_resume_batches.csv'}")
    print(f"- resumo: {OUT / 'phase4g_summary.json'}")


if __name__ == "__main__":
    main()
