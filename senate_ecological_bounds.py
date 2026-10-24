#!/usr/bin/env python3
"""Limites matematicos de sobreposicao Presidente x Senador, por secao.

Para votos P de um presidenciavel, S de um senador (cada eleitor
pode escolher um senador uma vez) e N votos presidenciais da mesma secao:
  max(0, P+S-N) <= pessoas com ambas escolhas <= min(P,S).
As margens NAO identificam como cada eleitor votou. Uma escolha
senatorial e uma pessoa; duas vagas NAO duplicam o eleitorado.

Examina apenas nove candidaturas previamente documentadas, compara
a lista com as inversoes existentes e verifica hash dos 256 CSVs BU.
Nao abre SQLite nem altera artefatos anteriores.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import json
import os
from pathlib import Path

from cross_office_candidate_correlations import source, rows
from reconcile_stream import sha256
from urnas import root_path

VERSION = "senate-ecological-bounds-v1"
PRESIDENTS = ("13", "22")
HEADERS = (
    "UF", "senador", "nome_urna", "partido", "presidente",
    "secoes_validas", "secoes_com_senador", "votos_senador",
    "votos_presidenciais_do_candidato", "comparecimento_presidencial",
    "eleitorado_senado_naquelas_secoes", "sobreposicao_minima",
    "sobreposicao_maxima", "senador_fora_do_presidente_minimo",
    "secoes_com_sobreposicao_obrigatoria",
    "pct_minima_dos_votos_senador", "pct_maxima_dos_votos_senador",
)


def mapping(path):
    if not path.is_file():
        raise RuntimeError("Falta mapeamento publicado: " + str(path))
    result = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        columns = {"UF", "turno", "cargo", "numero", "nome_urna",
                   "partido", "fonte"}
        if not columns <= set(reader.fieldnames or []):
            raise RuntimeError("Cabecalho do mapeamento inesperado")
        for row in reader:
            key = (row["UF"], str(int(row["numero"])))
            if (row["turno"] != "1" or row["cargo"] != "5" or
                    key in result or not all(row.get(x) for x in
                                             ("nome_urna", "partido", "fonte"))):
                raise RuntimeError("Mapeamento invalido/repetido: " + repr(key))
            result[key] = row
    if not result:
        raise RuntimeError("Nenhum senador documentado")
    return result


def validate_selected(folder, fp, selected):
    report = folder / "diagnostico_conjunto" / "revisao_inversoes" / "summary.json"
    item = json.loads(report.read_text("utf-8"))
    if item.get("input_fingerprint") != fp:
        raise RuntimeError("Fingerprint do relatorio de inversoes difere da origem")
    expected = {
        (r["UF"], str(int(r["senador"])))
        for r in item.get("senado_pares_invertidos", [])
    }
    if len(expected) != item.get("senadores_distintos_em_inversoes"):
        raise RuntimeError("Quantidade de senadores distintos nao coincide")
    if set(selected) != expected:
        raise RuntimeError(
            "Mapeamento deve corresponder exatamente aos candidatos "
            f"com inversoes: faltam {sorted(expected-set(selected))}; "
            f"excedem {sorted(set(selected)-expected)}")
    return report, sha256(report)


def bounds(p, s, n):
    if not (isinstance(p, int) and isinstance(s, int) and
            isinstance(n, int) and 0 <= p <= n and 0 <= s <= n):
        raise RuntimeError(f"Margens fora do universo: P={p}, S={s}, N={n}")
    return max(0, p+s-n), min(p, s), max(0, s-p)


def calc(files, selected, show_progress=True):
    by_uf = defaultdict(set)
    for uf, n in selected:
        by_uf[uf].add(n)
    totals = defaultdict(Counter)
    seen_rows = 0
    for i, path in enumerate(files, 1):
        section = None
        p = {}
        s = {}
        total_p = total_s = 0
        has_p = has_s = False

        def flush():
            if section is None:
                return
            uf, mu, zone, sec, turn = section
            if turn != "1" or uf not in by_uf or not has_p or not has_s:
                return
            if total_s % 2 or total_p < total_s//2:
                raise RuntimeError("Totais P/S inconsistentes: " + repr(section))
            n_local = total_s // 2
            for sen in by_uf[uf]:
                amount = s.get(sen, 0)
                if amount > n_local:
                    raise RuntimeError("Votos de senador > eleitores elegiveis "
                                       + repr((section, sen)))
                for president in PRESIDENTS:
                    count = p.get(president, 0)
                    low, high, not_pres = bounds(count, amount, total_p)
                    st = totals[(uf, sen, president)]
                    st["secoes_validas"] += 1
                    st["secoes_com_senador"] += amount > 0
                    st["votos_senador"] += amount
                    st["votos_presidenciais_do_candidato"] += count
                    st["comparecimento_presidencial"] += total_p
                    st["eleitorado_senado_naquelas_secoes"] += n_local
                    st["sobreposicao_minima"] += low
                    st["sobreposicao_maxima"] += high
                    st["senador_fora_do_presidente_minimo"] += not_pres
                    st["secoes_com_sobreposicao_obrigatoria"] += low > 0

        for rec in rows(path):
            seen_rows += 1
            key = (rec["UF"], rec["municipio"], rec["zona"],
                   rec["secao"], rec["turno"])
            if section != key:
                flush()
                section = key
                p, s = {}, {}
                total_p = total_s = 0
                has_p = has_s = False
            if rec["turno"] != "1" or rec["UF"] not in by_uf:
                continue
            cargo = rec["cargo"]
            if cargo not in ("1", "5"):
                continue
            votes = int(rec["votos_BU"])
            if votes < 0:
                raise RuntimeError("Votos negativos: " + repr(key))
            candidate = str(int(rec["votavel"])) if rec["votavel"].isdecimal() else rec["votavel"]
            if cargo == "1":
                has_p = True
                total_p += votes
                if candidate in PRESIDENTS:
                    p[candidate] = p.get(candidate, 0) + votes
            else:
                has_s = True
                total_s += votes
                if candidate in by_uf[rec["UF"]]:
                    s[candidate] = s.get(candidate, 0) + votes
        flush()
        if show_progress and (i <= 2 or i % 20 == 0 or i == len(files)):
            print(f"[LIMITES {i}/{len(files)}] "
                  f"{seen_rows:,} chaves BU verificadas", flush=True)
    return totals, seen_rows


def export(folder, selected, data, fingerprint, mapping_hash,
           reversal_hash, key_count):
    directory = folder / "limites_presidencia_senado_inversoes"
    directory.mkdir(exist_ok=True)
    table = []
    for (uf, sen, president), st in sorted(data.items()):
        cand = selected[(uf, sen)]
        votes = st["votos_senador"]
        item = {"UF": uf, "senador": sen,
                "nome_urna": cand["nome_urna"], "partido": cand["partido"],
                "presidente": president}
        item.update({h: st.get(h, 0) for h in HEADERS[5:-2]})
        item["pct_minima_dos_votos_senador"] = (
            round(100*st["sobreposicao_minima"]/votes, 4) if votes else "")
        item["pct_maxima_dos_votos_senador"] = (
            round(100*st["sobreposicao_maxima"]/votes, 4) if votes else "")
        table.append(item)
    expected = {(uf, sen, p) for uf, sen in selected for p in PRESIDENTS}
    if set(data) != expected:
        raise RuntimeError("Faltam pares no resultado dos limites")
    output = directory / "limites_por_senador_presidente.csv"
    part = Path(str(output) + ".part")
    try:
        with part.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=HEADERS, delimiter=";",
                                    lineterminator="\n")
            writer.writeheader()
            writer.writerows(table)
            f.flush()
            os.fsync(f.fileno())
        os.replace(part, output)
    finally:
        if part.exists():
            part.unlink()
    summary = {
        "version": VERSION, "status": "LIMITES_CALCULADOS",
        "source_fingerprint": fingerprint,
        "source_bu_candidate_keys": key_count,
        "candidate_mapping_sha256": mapping_hash,
        "review_summary_sha256": reversal_hash,
        "candidatos_distintos": len(selected),
        "pares_presidencia_senado": len(table),
        "csv": str(output), "csv_sha256": sha256(output),
        "por_candidato": table,
        "interpretacao": (
            "Limites exatos de intersecao possivel de conjuntos de eleitores "
            "por secao; nao identifica como cada eleitor votou. "
            "N=comparecimento presidencial na secao, incluindo possiveis "
            "eleitores em transito. O limite inferior e conservador. "
            "O Senado tem duas escolhas por eleitor, mas o voto num senador "
            "representa no maximo uma pessoa.")
    }
    dest = directory / "summary.json"
    temp = Path(str(dest) + ".part")
    try:
        temp.write_text(json.dumps(summary, ensure_ascii=False, indent=2)
                        + "\n", encoding="utf-8")
        os.replace(temp, dest)
    finally:
        if temp.exists():
            temp.unlink()
    return summary


def run(root, mapping_path=None):
    if mapping_path is None:
        mapping_path = Path(__file__).resolve().parent / (
            "docs/CANDIDATOS_SENADO_INVERSOES_2026.csv")
    mapping_path = Path(mapping_path)
    selected = mapping(mapping_path)
    folder, original, files = source(root)
    report_path, review_hash = validate_selected(
        folder, original["source_fingerprint"], selected)
    print("LIMITES ECOLOGICOS: 9 candidatos senatoriais (ou fixture), "
          "por secao, sem SQLite")
    print("Mapa:", mapping_path, "| SHA-256:", sha256(mapping_path))
    print("Revisao:", report_path, "| SHA-256:", review_hash)
    results, scanned = calc(files, selected)
    if scanned != original["candidate_keys"]:
        raise RuntimeError("Total de chaves BU mudou ao examinar os limites")
    summary = export(
        folder, selected, results, original["source_fingerprint"],
        sha256(mapping_path), review_hash, scanned)
    print("LIMITES PRESIDENTE X SENADO CONCLUIDOS")
    print(json.dumps({
        "candidatos_distintos": summary["candidatos_distintos"],
        "pares": summary["pares_presidencia_senado"],
        "limites": [{
            "UF": r["UF"], "senador": r["senador"], "nome": r["nome_urna"],
            "presidente": r["presidente"], "votos_senador": r["votos_senador"],
            "sobreposicao_minima": r["sobreposicao_minima"],
            "sobreposicao_maxima": r["sobreposicao_maxima"],
        } for r in summary["por_candidato"]],
        "csv": summary["csv"], "sha256": summary["csv_sha256"],
    }, ensure_ascii=False, indent=2), flush=True)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", help="Diretorio raiz do acervo TSE")
    parser.add_argument("--mapping", help="Mapa de candidatos para teste/controle")
    args = parser.parse_args()
    run(root_path(args.root), args.mapping)
