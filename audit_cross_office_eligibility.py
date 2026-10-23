#!/usr/bin/env python3
"""Auditoria dos denominadores por cargo nos BU (sem SQLite).

Compara Presidente, Governador e duas vagas do Senado por secao.
Testa compatibilidade contabil com voto em transito fora da UF:
P >= G e Senado = 2*Governador, quando ambos cargos estao presentes.
Essa igualdade NAO comprova por si so voto em transito.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import json
import os
from pathlib import Path

from audit_cross_office_totals import digest, to_int
from urnas import root_path

VERSION = "audit-cross-office-eligibility-v1"
MAX_CASES = 100


def new_stats():
    return {
        "secoes": 0, "presente_presidente": 0,
        "presente_governador": 0, "presente_senado": 0,
        "presidente_sem_governador": 0,
        "votos_presidente_sem_governador": 0,
        "presidente_governador_pareados": 0,
        "presidente_igual_governador": 0,
        "presidente_maior_governador": 0,
        "governador_maior_presidente": 0,
        "votos_presidente_excedentes_nos_pares": 0,
        "governador_senado_pareados": 0,
        "senado_igual_dobro_governador": 0,
        "senado_diferente_dobro_governador": 0,
        "governador_sem_senado": 0,
        "soma_desvio_senado_menos_dobro_governador": 0,
    }


def examine(matrix, expected):
    totals = new_stats()
    per_uf = defaultdict(new_stats)
    unexpected = []
    with matrix.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        needed = {"UF", "municipio", "zona", "secao", "turno",
                  "tem_presidente", "tem_governador", "tem_senado",
                  "votos_presidente", "votos_governador", "votos_senado"}
        if not needed.issubset(reader.fieldnames or []):
            raise RuntimeError("Matriz incompleta ou com cabecalho errado")
        for r in reader:
            p, g, s = (to_int(r, key) for key in
                       ("votos_presidente", "votos_governador", "votos_senado"))
            flags = ("tem_presidente", "tem_governador", "tem_senado")
            for key, n in zip(flags, (p, g, s)):
                if r[key] not in ("0", "1") or (r[key] == "1") != (n is not None):
                    raise RuntimeError("Marcador de cargo incoerente: " + repr(r))
            k = (r["UF"], r["municipio"], r["zona"], r["secao"], r["turno"])
            for st in (totals, per_uf[(r["UF"], r["turno"])]):
                st["secoes"] += 1
                st["presente_presidente"] += p is not None
                st["presente_governador"] += g is not None
                st["presente_senado"] += s is not None
                if p is not None and g is None:
                    st["presidente_sem_governador"] += 1
                    st["votos_presidente_sem_governador"] += p
                if p is not None and g is not None:
                    st["presidente_governador_pareados"] += 1
                    st["presidente_igual_governador"] += p == g
                    st["presidente_maior_governador"] += p > g
                    st["governador_maior_presidente"] += g > p
                    st["votos_presidente_excedentes_nos_pares"] += p - g
                if g is not None and s is None:
                    st["governador_sem_senado"] += 1
                if g is not None and s is not None:
                    st["governador_senado_pareados"] += 1
                    st["senado_igual_dobro_governador"] += s == 2*g
                    st["senado_diferente_dobro_governador"] += s != 2*g
                    st["soma_desvio_senado_menos_dobro_governador"] += s - 2*g
            if len(unexpected) < MAX_CASES and (
                    (p is not None and g is not None and p < g) or
                    (g is not None and s is None) or
                    (g is not None and s is not None and s != 2*g)):
                unexpected.append({"UF":k[0], "municipio":k[1], "zona":k[2],
                                   "secao":k[3], "turno":k[4],
                                   "P":p, "G":g, "S":s,
                                   "P_menos_G":(p-g if p is not None and g is not None else ""),
                                   "S_menos_2G":(s-2*g if g is not None and s is not None else "")})
    checks = {"distinct_sections": totals["secoes"],
              "paired_president_governor_sections": totals["presidente_governador_pareados"],
              "president_governor_totals_unequal": (
                  totals["presidente_maior_governador"] +
                  totals["governador_maior_presidente"])}
    for key, actual in checks.items():
        if actual != expected.get(key):
            raise RuntimeError(f"Resumo/matriz incompatíveis: {key}, {actual} != {expected.get(key)}")
    return totals, per_uf, unexpected


def csv_out(path, fields, rows):
    temp = Path(str(path) + ".part")
    try:
        with temp.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, delimiter=";", lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def run(root):
    analysis = root / "analysis"
    national = json.loads((analysis / "reconciliacao_bu_secao.summary.json")
                          .read_text(encoding="utf-8"))
    options = []
    for path in (analysis / "entre_cargos").glob("*/summary.json"):
        obj = json.loads(path.read_text(encoding="utf-8"))
        if obj.get("status") == "concluido" and obj.get("source_fingerprint") == national["fingerprint"]:
            options.append((path, obj))
    if len(options) != 1:
        raise RuntimeError("Esperada exatamente uma matriz do fingerprint nacional")
    summary_path, original = options[0]
    matrix = Path(original["matrix"])
    if not matrix.is_file() or digest(matrix) != original["matrix_sha256"]:
        raise RuntimeError("SHA-256 de matriz diverge do resumo")
    print("AUDITORIA DE ELEGIBILIDADE POR CARGO: somente leitura")
    print("Matriz original SHA-256:", original["matrix_sha256"], flush=True)
    total, by_uf, anomalies = examine(matrix, original)
    dest = summary_path.parent / "auditoria_elegibilidade"
    dest.mkdir(exist_ok=True)
    by_uf_rows = [{"UF": uf, "turno": tu, **vals}
                  for (uf, tu), vals in sorted(by_uf.items())]
    uf_path = dest / "por_uf_turno.csv"
    errors = dest / "amostra_invariantes_quebradas.csv"
    csv_out(uf_path, ["UF", "turno", *new_stats()], by_uf_rows)
    cols = ["UF", "municipio", "zona", "secao", "turno",
            "P", "G", "S", "P_menos_G", "S_menos_2G"]
    csv_out(errors, cols, anomalies)
    out = {
        "version": VERSION, "status": "DESCRITIVO_CONCLUIDO",
        "matrix_sha256": original["matrix_sha256"],
        "source_fingerprint": original["source_fingerprint"],
        "totals": total,
        "por_uf": [{"UF": r["UF"], "turno": r["turno"],
                    "diferencas_P_maior_G": r["presidente_maior_governador"],
                    "excedente_P_G": r["votos_presidente_excedentes_nos_pares"],
                    "secoes_P_sem_G": r["presidente_sem_governador"],
                    "secoes_S_diferente_2G": r["senado_diferente_dobro_governador"]}
                   for r in by_uf_rows],
        "amostra_quebras": anomalies,
        "files": {p.name: {"sha256": digest(p), "bytes": p.stat().st_size}
                  for p in (uf_path, errors)},
        "interpretation": (
            "Compatibilidade com voto em transito fora da UF (apenas presidente) "
            "nao comprova atribuicao individual; requer lista oficial de seções "
            "habilitadas e dados de eleitorado/comparecimento por cargo. "
            "Para Senado em 2026 ha dois votos por eleitor; diferencas de 2G "
            "tambem exigem analise documental.")
    }
    tmp = dest / "summary.json.tmp"
    try:
        tmp.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
        os.replace(tmp, dest / "summary.json")
    finally:
        if tmp.exists():
            tmp.unlink()
    print("AUDITORIA DE ELEGIBILIDADE CONCLUIDA")
    print(json.dumps({"totals": total,
                      "maiores_ufs_com_excedente": sorted(
                          out["por_uf"], key=lambda v: v["excedente_P_G"], reverse=True)[:12],
                      "amostra_quebras": anomalies[:6],
                      "report": str(dest / "summary.json")},
                     ensure_ascii=False, indent=2), flush=True)
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", help="Diretorio dos dados (Windows: H:)")
    args = parser.parse_args()
    run(root_path(args.root))
