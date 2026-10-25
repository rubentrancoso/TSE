"""Leitura de BU 2026 para robustez do Senado; sem SQLite ou rede.

Reconstrucao com o mesmo denominador de cross_office_senate_correlations.py.
"""
import csv
import json
from pathlib import Path

from reconcile_stream import sha256
from cross_office_candidate_correlations import rows


def load_cases(folder, fingerprint):
    v2 = folder / "correlacao_presidente_senado_v2"
    meta = json.loads((v2 / "summary.json").read_text("utf-8"))
    comp = json.loads((v2 / "comparacao_metodologica" / "summary.json").read_text("utf-8"))
    source = Path(meta["csv"])
    comparison = Path(comp["output"])
    if (meta.get("fingerprint") != fingerprint or
        comp.get("fingerprint") != fingerprint or
        meta.get("version") != "cross-office-senate-v2" or
        comp.get("source_v2_sha256") != meta.get("csv_sha256") or
        not source.is_file() or sha256(source) != meta["csv_sha256"] or
        not comparison.is_file() or sha256(comparison) != comp["output_sha256"]):
        raise RuntimeError("Senado v2 ou comparacao ausente/invalida")
    entries = {}
    with source.open("r", newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f, delimiter=";"):
            key = row["UF"], row["presidente"], row["senador"]
            if key in entries:
                raise RuntimeError("Par repetido no Senado v2")
            entries[key] = row
    cases = {}
    for case in comp["v2_pares_com_inversao"]:
        key = case["UF"], case["presidente"], case["senador"]
        if key in cases or key not in entries:
            raise RuntimeError("Inversao duplicada ou inexistente")
        row = entries[key]
        raw = float(row["correlacao_bruta_pearson"])
        adjusted = float(row["correlacao_dentro_municipio_zona"])
        if (abs(raw-float(case["r_bruto"])) > 1e-6 or
            abs(adjusted-float(case["r_ajustado"])) > 1e-6):
            raise RuntimeError("Coeficientes de comparacao divergentes")
        cases[key] = {
            "n": int(row["secoes_com_dois_cargos"]),
            "z": int(row["zonas_com_variacao"]),
            "raw": raw, "adjusted": adjusted
        }
    if not cases or comp["totals"]["v2_inversoes"] != len(cases):
        raise RuntimeError("Quantidade de inversoes inconsistente")
    return cases, meta["csv_sha256"], comp["output_sha256"]


def aggregate_shard(path, cases):
    """Momentos [n,sx,sy,sxx,syy,sxy] por zona e par candidato."""
    wanted = {}
    for uf, p, s in cases:
        wanted.setdefault(uf, set()).add((p,s))
    wanted = {uf: tuple(sorted(pairs)) for uf,pairs in wanted.items()}
    senators = {uf: {s for _,s in pairs} for uf,pairs in wanted.items()}
    moments = {}
    current = None
    pres, sen = {}, {}
    np = ns = 0
    hp = hs = False

    def flush():
        if current is None:
            return
        uf, mu, zo, _se, turn = current
        if (turn != "1" or uf not in wanted or not hp or not hs
            or np <= 0 or ns <= 0 or ns % 2):
            return
        eligible = ns//2
        for p,s in wanted[uf]:
            x = pres.get(p,0)/np
            votes = sen.get(s,0)
            if votes > eligible:
                raise RuntimeError("Senador com votos acima do eleitorado")
            y = votes/eligible
            key = (uf,mu,zo,turn,p,s)
            m = moments.setdefault(key,[0,0.,0.,0.,0.,0.])
            m[0] += 1
            m[1] += x
            m[2] += y
            m[3] += x*x
            m[4] += y*y
            m[5] += x*y

    for row in rows(path):
        section = (row["UF"],row["municipio"],row["zona"],
                   row["secao"],row["turno"])
        if section != current:
            flush()
            current = section
            pres, sen = {}, {}
            np = ns = 0
            hp = hs = False
        if section[4] != "1" or section[0] not in wanted:
            continue
        cargo = row["cargo"]
        if cargo not in ("1","5"):
            continue
        n = int(row["votos_BU"])
        if n < 0:
            raise RuntimeError("Voto negativo em BU")
        if cargo == "1":
            hp = True
            np += n
            if row["votavel"] in ("13","22"):
                pres[row["votavel"]] = pres.get(row["votavel"],0)+n
        else:
            hs = True
            ns += n
            if row["votavel"] in senators[section[0]]:
                sen[row["votavel"]] = sen.get(row["votavel"],0)+n
    flush()
    return moments
