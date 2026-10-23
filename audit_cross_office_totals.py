#!/usr/bin/env python3
"""Auditoria dos totais BU de Presidente x Governador, por secao e UF.

Somente leitura da matriz entre cargos, com verificação SHA-256.
Nao identifica voto individual, transferencias politicas nem fraude.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import heapq
import json
import os
from pathlib import Path

from urnas import root_path

VERSION = "audit-cross-office-totals-v1"
TOP_N = 50
OFFICE = {"P": "votos_presidente", "G": "votos_governador",
          "S": "votos_senado"}


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def to_int(row, field):
    raw = row.get(field, "")
    if raw == "" or raw is None:
        return None
    value = int(raw)
    if value < 0:
        raise ValueError("Valor negativo em " + field)
    return value


def new_stat():
    return {"secoes": 0, "com_presidente": 0, "com_governador": 0,
            "com_senado": 0, "presidente_governador_pareados": 0,
            "totais_iguais": 0, "totais_diferentes": 0,
            "presidente_maior": 0, "governador_maior": 0,
            "soma_presidente_em_pares": 0, "soma_governador_em_pares": 0,
            "soma_delta": 0, "soma_abs_delta": 0, "maior_abs_delta": 0}


def apply(stat, president, governor, senator):
    stat["secoes"] += 1
    stat["com_presidente"] += president is not None
    stat["com_governador"] += governor is not None
    stat["com_senado"] += senator is not None
    if president is None or governor is None:
        return
    delta = president - governor
    stat["presidente_governador_pareados"] += 1
    stat["soma_presidente_em_pares"] += president
    stat["soma_governador_em_pares"] += governor
    stat["soma_delta"] += delta
    stat["soma_abs_delta"] += abs(delta)
    stat["maior_abs_delta"] = max(stat["maior_abs_delta"], abs(delta))
    if delta == 0:
        stat["totais_iguais"] += 1
    else:
        stat["totais_diferentes"] += 1
        stat["presidente_maior"] += delta > 0
        stat["governador_maior"] += delta < 0


def atomic_csv(dest, fieldnames, records):
    temp = Path(str(dest) + ".part")
    try:
        with temp.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, delimiter=";", fieldnames=fieldnames,
                                    lineterminator="\n")
            writer.writeheader()
            writer.writerows(records)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp, dest)
    finally:
        if temp.exists():
            temp.unlink()


def evaluate(matrix, expected, top_n=TOP_N):
    if top_n < 1:
        raise ValueError("top_n deve ser positivo")
    total = new_stat()
    by_uf_turn = defaultdict(new_stat)
    by_municipality = defaultdict(new_stat)
    magnitudes = Counter()
    heap = []
    unique_keys = set()
    with matrix.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source, delimiter=";")
        fields = set(reader.fieldnames or [])
        necessary = {"UF", "municipio", "zona", "secao", "turno",
                     "tem_presidente", "tem_governador", "tem_senado",
                     *OFFICE.values()}
        if not necessary <= fields:
            raise RuntimeError("Matriz sem colunas obrigatorias")
        for row in reader:
            key = (row["UF"], row["municipio"], row["zona"],
                   row["secao"], row["turno"])
            if key in unique_keys:
                raise RuntimeError("Secao repetida: " + repr(key))
            unique_keys.add(key)
            values = {k: to_int(row, field)
                      for k, field in OFFICE.items()}
            p, g, s = (values[x] for x in ("P", "G", "S"))
            for label, value in (("tem_presidente", p),
                                 ("tem_governador", g), ("tem_senado", s)):
                if (row[label] not in ("0", "1") or
                        (row[label] == "1") != (value is not None)):
                    raise RuntimeError("Indicador cargo inconsistente: " + repr(key))
            apply(total, p, g, s)
            apply(by_uf_turn[(row["UF"], row["turno"])], p, g, s)
            apply(by_municipality[(row["UF"], row["municipio"], row["turno"])], p, g, s)
            if p is None or g is None:
                continue
            delta = p - g
            if delta:
                magnitude = abs(delta)
                for limit, label in ((1, "1"), (2, "2"), (5, "3-5"),
                                     (10, "6-10"), (50, "11-50"),
                                     (100, "51-100")):
                    if magnitude <= limit:
                        magnitudes[label] += 1
                        break
                else:
                    magnitudes["101+"] += 1
                entry = (magnitude, key, p, g, delta)
                if len(heap) < top_n:
                    heapq.heappush(heap, entry)
                elif entry > heap[0]:
                    heapq.heapreplace(heap, entry)
    checks = {
        "distinct_sections": total["secoes"],
        "paired_president_governor_sections": total["presidente_governador_pareados"],
        "president_governor_totals_unequal": total["totais_diferentes"],
    }
    discrepancies = {k: (v, expected.get(k)) for k, v in checks.items()
                     if v != expected.get(k)}
    if discrepancies:
        raise RuntimeError("Matriz e resumo nao coincidem: " + repr(discrepancies))
    cases = [{"UF": key[0], "municipio": key[1], "zona": key[2],
              "secao": key[3], "turno": key[4],
              "votos_presidente": p, "votos_governador": g,
              "delta_presidente_menos_governador": delta,
              "abs_delta": magnitude}
             for magnitude, key, p, g, delta in sorted(heap, reverse=True)]
    return total, by_uf_turn, by_municipality, magnitudes, cases


def run(root, top_n=TOP_N):
    analysis = root / "analysis"
    national = json.loads((analysis / "reconciliacao_bu_secao.summary.json")
                          .read_text("utf-8"))
    summaries = sorted((analysis / "entre_cargos").glob("*/summary.json"))
    candidates = []
    for path in summaries:
        data = json.loads(path.read_text("utf-8"))
        if (data.get("status") == "concluido" and
                data.get("source_fingerprint") == national.get("fingerprint")):
            candidates.append((path, data))
    if len(candidates) != 1:
        raise RuntimeError("Esperava uma matriz nacional da mesma fonte; "
                           f"encontrei {len(candidates)}")
    summary_path, existing = candidates[0]
    matrix = Path(existing["matrix"])
    if not matrix.is_file() or digest(matrix) != existing.get("matrix_sha256"):
        raise RuntimeError("SHA-256 da matriz nao confere; nao prosseguir")
    print("ENTRE CARGOS: auditoria descritiva de totais, somente leitura")
    print("MATRIZ VERIFICADA:", matrix)
    print("SHA-256:", existing["matrix_sha256"])
    total, by_uf, by_mu, bins, cases = evaluate(matrix, existing, top_n=top_n)
    dest = summary_path.parent / "auditoria_totais"
    dest.mkdir(parents=True, exist_ok=True)
    cols = list(new_stat())
    state_uf = [{"UF": uf, "turno": turno, **stat}
                for (uf, turno), stat in sorted(by_uf.items())]
    state_mu = [{"UF": uf, "municipio": mu, "turno": turno, **stat}
                for (uf, mu, turno), stat in sorted(by_mu.items())]
    atomic_csv(dest / "por_uf_turno.csv", ["UF", "turno", *cols], state_uf)
    atomic_csv(dest / "por_municipio_turno.csv",
               ["UF", "municipio", "turno", *cols], state_mu)
    case_cols = ["UF", "municipio", "zona", "secao", "turno",
                 "votos_presidente", "votos_governador",
                 "delta_presidente_menos_governador", "abs_delta"]
    atomic_csv(dest / "maiores_diferencas.csv", case_cols, cases)
    report = {
        "version": VERSION, "status": "ANALISE_DESCRITIVA_CONCLUIDA",
        "matrix_sha256": existing["matrix_sha256"],
        "source_fingerprint": existing["source_fingerprint"],
        "input_summary_path": str(summary_path), "total": total,
        "magnitude_distribution": dict(sorted(bins.items())),
        "top_ufs": sorted(state_uf,
                          key=lambda x: x["totais_diferentes"], reverse=True)[:12],
        "top_cases": cases[:12],
        "files": {p.name: {"sha256": digest(p), "bytes": p.stat().st_size}
                  for p in sorted(dest.glob("*.csv"))},
        "limitations": [
            "Compara somas BU de dois cargos; nao dois resultados para o mesmo cargo",
            "Votos cruzados individuais nao sao inferiveis das margens agregadas",
            "Diferencas podem decorrer de regra eleitoral ou dados de comparecimento/escopo",
            "Investigar cada causa com registros independentes antes de atribuir origem",
            "Nenhuma conclusao automatica de fraude",
        ]}
    temp = dest / "summary.json.tmp"
    try:
        temp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        os.replace(temp, dest / "summary.json")
    finally:
        if temp.exists():
            temp.unlink()
    print("DIAGNOSTICO ENTRE CARGOS CONCLUIDO")
    print(json.dumps({
        "total": total, "magnitude_distribution": report["magnitude_distribution"],
        "top_ufs": [{"UF": x["UF"], "turno": x["turno"],
                     "diferentes": x["totais_diferentes"],
                     "soma_delta": x["soma_delta"]}
                    for x in report["top_ufs"]],
        "output": str(dest)}, ensure_ascii=False, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", help="Diretorio principal de dados")
    parser.add_argument("--top", type=int, default=TOP_N,
                        help="Numero de maiores diferencas por secao")
    args = parser.parse_args()
    run(root_path(args.root), top_n=args.top)


if __name__ == "__main__":
    main()
