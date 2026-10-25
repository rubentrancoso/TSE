#!/usr/bin/env python3
"""Falsificacao exploratoria de formula fixa de votos presidenciais em 2026.

H_F: votos de um presidenciavel na secao = round(alpha * N),
onde N e o TOTAL de votos presidenciais (inclui invalidos).
Alpha e estimado apenas no TREINO; validacao em secoes distintas,
sem usar nenhum resultado eleitoral de 2022. Comparar erro da
formula unica nacional com taxas por UF e por municipio+zona.
Uma formula que nao prevê secoes nao explica adequadamente seus dados.
Uma que prevê nao prova fraude: geografia e voto natural tambem
podem produzir alta previsibilidade.

Fonte: 256 CSVs de BU por candidato ja criados, SHA-256 confirmado.
Sem SQLite, sem downloads, sem alterar dados originais.
"""
from __future__ import annotations

from collections import defaultdict
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path

from cross_office_candidate_correlations import rows, source
from reconcile_stream import sha256
from urnas import root_path

VERSION = "formula-proporcao-fixa-holdout-2026-v1"
CANDIDATES = ("13", "22")
MIN_VOTES = 50
HOLDOUT_MODULUS = 5  # ~20% das secoes, atribuidas por hash
MIN_ZONE_TRAIN = 3
FIELDS = (
    "UF", "presidente", "modelo", "secoes_validacao",
    "exatas", "diferenca_ate_1", "erro_absoluto_total",
    "erro_quadratico_total", "pct_exatas", "pct_ate_1",
    "erro_absoluto_medio", "raiz_erro_quadratico_medio",
)


def holdout(section_key):
    """Particao deterministica por SECAO; independe de ordem/bucket."""
    raw = "|".join(section_key).encode("utf-8")
    return hashlib.sha256(raw).digest()[0] % HOLDOUT_MODULUS == 0


def record_stats():
    # n secoes, N votos totais, votos13, votos22
    return [0, 0, 0, 0]


def add_stats(stat, total, a, b):
    stat[0] += 1
    stat[1] += total
    stat[2] += a
    stat[3] += b


def alpha(stat, index):
    if stat[1] <= 0:
        return None
    return stat[index] / stat[1]


def predict(n, rate):
    if not 0.0 <= rate <= 1.0:
        raise RuntimeError("Taxa candidata fora dos limites [0,1]")
    return min(n, max(0, int(math.floor(rate*n+0.5))))


def extract(paths, progress=True, min_votes=MIN_VOTES):
    """Uma passagem pelos BU verificados, separando treino e validacao."""
    global_train = record_stats()
    uf_train = defaultdict(record_stats)
    zone_train = defaultdict(record_stats)
    heldout = []
    counts = defaultdict(int)
    keys_seen = 0
    for ix, path in enumerate(paths, 1):
        current = None
        total = a = b = 0
        has_p = False

        def flush():
            if current is None or current[-1] != "1" or not has_p:
                return
            uf, mu, zona, sec, _ = current
            if total <= 0 or a < 0 or b < 0 or a+b > total:
                raise RuntimeError("Totais presidenciais impossiveis: "+repr(current))
            counts["secoes_presidenciais"] += 1
            if total < min_votes:
                counts["excluidas_por_comparecimento"] += 1
                return
            counts["qualificadas"] += 1
            if holdout(current):
                heldout.append((uf, mu, zona, sec, total, a, b))
                counts["validacao"] += 1
            else:
                add_stats(global_train, total, a, b)
                add_stats(uf_train[uf], total, a, b)
                add_stats(zone_train[(uf, mu, zona)], total, a, b)
                counts["treino"] += 1

        for item in rows(path):
            keys_seen += 1
            key = (item["UF"], item["municipio"], item["zona"],
                   item["secao"], item["turno"])
            if key != current:
                flush()
                current = key
                total = a = b = 0
                has_p = False
            if item["turno"] != "1" or item["cargo"] != "1":
                continue
            votes = int(item["votos_BU"])
            if votes < 0:
                raise RuntimeError("Votos negativos: " + repr(key))
            has_p = True
            total += votes
            if item["votavel"] == "13":
                a += votes
            elif item["votavel"] == "22":
                b += votes
        flush()
        if progress and (ix <= 2 or ix % 20 == 0 or ix == len(paths)):
            print(f"[FORMULA BU {ix}/{len(paths)}] {keys_seen:,} chaves lidas; "
                  f"treino={counts['treino']:,} validacao={counts['validacao']:,}",
                  flush=True)
    if not global_train[0] or not heldout:
        raise RuntimeError("Nao existe treino e validacao suficientes")
    return global_train, uf_train, zone_train, heldout, counts, keys_seen


def metrics():
    return [0, 0, 0, 0, 0]


def score(heldout, national, by_uf, by_zone):
    result = defaultdict(metrics)
    fallback = defaultdict(int)
    for uf, mu, zona, sec, N, a, b in heldout:
        uf_stat = by_uf.get(uf, national)
        if not uf_stat[0]:
            uf_stat = national
            fallback["uf"] += 1
        zone_stat = by_zone.get((uf, mu, zona))
        if zone_stat is None or zone_stat[0] < MIN_ZONE_TRAIN:
            zone_stat = uf_stat
            fallback["zona"] += 1
        for index, (candidate, actual) in enumerate((("13", a), ("22", b)), 2):
            for name, stat in (("nacional", national),
                               ("UF", uf_stat),
                               ("municipio_zona", zone_stat)):
                proposed = predict(N, alpha(stat, index))
                diff = abs(actual - proposed)
                for key in ((uf, candidate, name),
                            ("BR", candidate, name)):
                    m = result[key]
                    m[0] += 1
                    m[1] += int(diff == 0)
                    m[2] += int(diff <= 1)
                    m[3] += diff
                    m[4] += diff*diff
    return result, dict(fallback)


def report_rows(scores):
    out = []
    for (uf, p, model), m in sorted(scores.items()):
        count, exact, close, absolute, squared = m
        out.append({
            "UF": uf, "presidente": p, "modelo": model,
            "secoes_validacao": count, "exatas": exact,
            "diferenca_ate_1": close,
            "erro_absoluto_total": absolute,
            "erro_quadratico_total": squared,
            "pct_exatas": round(100*exact/count, 6),
            "pct_ate_1": round(100*close/count, 6),
            "erro_absoluto_medio": round(absolute/count, 6),
            "raiz_erro_quadratico_medio": round(math.sqrt(squared/count), 6),
        })
    return out


def run(root, min_votes=MIN_VOTES):
    if not 1 <= min_votes <= 1000:
        raise ValueError("min_votes deve ser entre 1 e 1000")
    folder, original, paths = source(root)
    print("FORMULA HIPOTETICA 2026: teste de proporcao fixa fora da amostra")
    train, uf_train, geo_train, heldout, stats, keys = extract(
        paths, min_votes=min_votes)
    if keys != original["candidate_keys"]:
        raise RuntimeError("Contagem de chaves difere do manifesto BU")
    scores, fallback = score(heldout, train, uf_train, geo_train)
    data = report_rows(scores)
    destination = folder / "formula_fixa_presidencial_2026"
    destination.mkdir(exist_ok=True)
    out = destination / "predicao_fora_amostra.csv"
    temp = Path(str(out)+".part")
    try:
        with temp.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, delimiter=";",
                                    fieldnames=FIELDS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, out)
    finally:
        if temp.exists():
            temp.unlink()
    national = [r for r in data if r["UF"] == "BR"]
    simple_rule = {}
    for p in CANDIDATES:
        one = next(r for r in national
                   if r["presidente"] == p and r["modelo"] == "nacional")
        control = next(r for r in national
                       if r["presidente"] == p and r["modelo"] == "municipio_zona")
        # Criterio exploratorio predefinido, deliberadamente exigente:
        # >=95% contagens exatamente previsiveis na validacao
        # e modelo nacional NAO pior que modelo territorial.
        simple_rule[p] = bool(one["pct_exatas"] >= 95 and
                              one["erro_absoluto_medio"] <=
                              control["erro_absoluto_medio"])
    summary = {
        "version": VERSION, "status": "TESTE_DESCRITIVO_CONCLUIDO",
        "source_fingerprint": original["source_fingerprint"],
        "source_candidate_keys": keys,
        "min_votes": min_votes,
        "training": {
            "sections": train[0], "voters": train[1],
            "presidente_13_rate": round(alpha(train, 2), 10),
            "presidente_22_rate": round(alpha(train, 3), 10),
        },
        "validation_sections": len(heldout),
        "counts": dict(stats),
        "holdout": "SHA256(UF|municipio|zona|secao|turno)[0] modulo 5 == 0",
        "min_zone_training_sections": MIN_ZONE_TRAIN,
        "fallbacks": fallback,
        "national_results": national,
        "criterio_exploratorio_forma_simples_nao_refutada": simple_rule,
        "csv": str(out), "csv_sha256": sha256(out),
        "limitations": [
            "A forma P=round(alpha*N) e apenas UMA hipotese de formula, nao todas as possiveis",
            "Taxa de voto invariavel nao implica adulteracao; comportamentos naturais sao possiveis",
            "O modelo municipal-zonal e controle preditivo, nao modelo causal",
            "O teste de 95 por cento e criterio descritivo, nao p-valor",
            "Sem votos originais independentes, nao e possivel observar a transferencia D",
            "Nao usa dados de 2022 e nao infere voto individual",
        ],
    }
    path = destination / "summary.json"
    tmp = Path(str(path)+".part")
    try:
        tmp.write_text(json.dumps(summary, ensure_ascii=False, indent=2)+"\n",
                       encoding="utf-8")
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()
    print("TESTE DE FORMULA FIXA 2026 CONCLUIDO")
    print(json.dumps({
        "secoes_treino": train[0], "secoes_validacao": len(heldout),
        "taxas_estimada_treino": {
            "13": summary["training"]["presidente_13_rate"],
            "22": summary["training"]["presidente_22_rate"],
        },
        "comparacao_nacional": national,
        "forma_simples_nao_refutada": simple_rule,
        "csv": str(out), "sha256": summary["csv_sha256"],
    }, ensure_ascii=False, indent=2), flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", help="Pasta do acervo em H:")
    parser.add_argument("--min-votes", type=int, default=MIN_VOTES)
    args = parser.parse_args()
    run(root_path(args.root), args.min_votes)


if __name__ == "__main__":
    main()
