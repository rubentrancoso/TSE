#!/usr/bin/env python3
"""Matriz por secao/cargo/candidato usando particoes BU ja seladas.

Nao acessa SQLite, nao altera BU, checkpoints originais ou reconciliacao.
Gera CSVs de candidatos por bucket e uma matriz compacta por secao.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import os
from pathlib import Path

from reconcile_stream import sha256, save_state
from urnas import root_path

VERSION = "cross-office-sections-v1"
OFFICES = ("1", "3", "5", "6", "7", "8")
OFFICE_NAMES = {"1": "Presidente", "3": "Governador",
                "5": "Senador", "6": "Deputado federal",
                "7": "Deputado estadual", "8": "Deputado distrital"}
CANDIDATE_HEADER = ["UF", "municipio", "zona", "secao", "turno",
                    "cargo", "votavel", "votos_BU"]
SECTION_HEADER = ["UF", "municipio", "zona", "secao", "turno",
                  "tem_presidente", "tem_governador", "tem_senado",
                  "votos_presidente", "votos_governador", "votos_senado",
                  "delta_presidente_menos_governador"]


def atomic_csv(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(path) + ".part")
    try:
        with temp.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, delimiter=";", lineterminator="\n")
            writer.writerow(header)
            for row in rows:
                writer.writerow(row)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def extract_bucket(src, candidates_out, sections_out):
    """Consolida so registros BU; nao mistura fontes TSE de secao."""
    totals = defaultdict(int)
    raw_bu = 0
    skipped = 0
    with src.open("r", encoding="utf-8", newline="") as stream:
        for row in csv.reader(stream, delimiter="\t"):
            if len(row) != 9:
                raise RuntimeError("Particao malformada: " + str(src))
            uf, mu, zo, se, tu, ca, vo, origin, votes = row
            if origin != "bu" or ca not in OFFICES:
                skipped += 1
                continue
            n = int(votes)
            if n < 0:
                raise RuntimeError("Votacao negativa na fonte: " + str(src))
            totals[(uf, mu, zo, se, tu, ca, vo)] += n
            raw_bu += 1
    sorted_keys = sorted(totals)
    atomic_csv(candidates_out, CANDIDATE_HEADER,
               ((*key, totals[key]) for key in sorted_keys))

    per_section = defaultdict(dict)
    for key in sorted_keys:
        sec_key = key[:5]
        cargo = key[5]
        amounts = per_section[sec_key]
        amounts[cargo] = amounts.get(cargo, 0) + totals[key]
    section_keys = sorted(per_section)
    count_cargos = Counter()
    paired = unequal = 0

    def section_rows():
        nonlocal paired, unequal
        for key in section_keys:
            amounts = per_section[key]
            count_cargos.update(amounts.keys())
            pres, gov, sen = (amounts.get(c) for c in ("1", "3", "5"))
            if pres is not None and gov is not None:
                paired += 1
                unequal += pres != gov
            yield (*key, int(pres is not None), int(gov is not None),
                   int(sen is not None),
                   pres if pres is not None else "",
                   gov if gov is not None else "",
                   sen if sen is not None else "",
                   pres - gov if pres is not None and gov is not None else "")
    atomic_csv(sections_out, SECTION_HEADER, section_rows())
    return {"raw_bu": raw_bu, "skipped_input": skipped,
            "candidate_keys": len(totals), "sections": len(section_keys),
            "by_office_sections": dict(count_cargos),
            "paired_pres_gov": paired, "pres_gov_unequal": unequal,
            "candidate_sha256": sha256(candidates_out),
            "section_sha256": sha256(sections_out)}


def consolidate_section_matrix(target, bucket_dir, count):
    """CSV unico de secoes; arquivos por candidato continuam particionados."""
    temp = Path(str(target) + ".part")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with temp.open("w", encoding="utf-8", newline="") as dest:
            writer = csv.writer(dest, delimiter=";", lineterminator="\n")
            writer.writerow(SECTION_HEADER)
            for i in range(count):
                src = bucket_dir / f"bucket-{i:04d}.csv"
                with src.open("r", encoding="utf-8", newline="") as handle:
                    reader = csv.reader(handle, delimiter=";")
                    if next(reader) != SECTION_HEADER:
                        raise RuntimeError("Cabecalho de particao inesperado: " + str(src))
                    writer.writerows(reader)
            dest.flush()
            os.fsync(dest.fileno())
        os.replace(temp, target)
    finally:
        if temp.exists():
            temp.unlink()


def run(root, pilot_buckets=0):
    if pilot_buckets < 0:
        raise ValueError("--pilot-buckets nao pode ser negativo")
    analysis = root / "analysis"
    national = analysis / "reconciliacao_bu_secao.summary.json"
    national_data = json.loads(national.read_text(encoding="utf-8"))
    if national_data.get("status") != "concluido":
        raise RuntimeError("Reconciliacao nacional ainda nao foi concluida")
    fingerprint = national_data["fingerprint"]
    n_buckets = int(national_data["partitions_total"])
    workspace = analysis / "reconciliacao_checkpoints" / "stream" / fingerprint
    source_state = json.loads((workspace / "state.json").read_text(encoding="utf-8"))
    hashes = source_state.get("bucket_hashes")
    offsets = source_state.get("offsets")
    if (not source_state.get("scan_complete") or
            source_state.get("fingerprint") != fingerprint or
            not hashes or len(hashes) != n_buckets or
            not offsets or len(offsets) != n_buckets):
        raise RuntimeError("Particoes originais nao foram seladas corretamente")
    key = hashlib.sha256((VERSION + ":" + fingerprint + ":" +
                          ",".join(OFFICES)).encode("utf-8")).hexdigest()[:16]
    dest = analysis / "entre_cargos" / (fingerprint[:16] + "-" + key)
    dest.mkdir(parents=True, exist_ok=True)
    local_state_file = dest / "state.json"
    if local_state_file.exists():
        progress = json.loads(local_state_file.read_text(encoding="utf-8"))
        if progress.get("input_fingerprint") != fingerprint or progress.get("version") != VERSION:
            raise RuntimeError("Checkpoint derivado incompativel")
    else:
        progress = {"version": VERSION, "input_fingerprint": fingerprint,
                    "offices": list(OFFICES), "completed": {}}
        save_state(local_state_file, progress)
    completed = progress["completed"]
    candidate_dir = dest / "candidatos"
    section_dir = dest / "secoes"
    candidate_dir.mkdir(exist_ok=True)
    section_dir.mkdir(exist_ok=True)
    processed_now = 0
    print("ENTRE CARGOS:", VERSION, "| 256 buckets originais preservados")
    print("Fingerprint:", fingerprint)
    for i in range(n_buckets):
        source = workspace / "buckets" / f"bucket-{i:04d}.tsv"
        if not source.is_file() or source.stat().st_size != offsets[i]:
            raise RuntimeError("Tamanho da particao alterado: " + str(source))
        if sha256(source) != hashes[i]:
            raise RuntimeError("SHA-256 de particao alterado: " + str(source))
        cand = candidate_dir / f"bucket-{i:04d}.csv"
        sec = section_dir / f"bucket-{i:04d}.csv"
        saved = completed.get(str(i))
        if saved and cand.exists() and sec.exists():
            if (sha256(cand) == saved["candidate_sha256"] and
                    sha256(sec) == saved["section_sha256"]):
                continue
        if pilot_buckets and processed_now >= pilot_buckets:
            print(f"PILOTO CONCLUIDO: {processed_now} novas particoes; "
                  "nenhum relatorio final alterado.")
            return {"status": "piloto", "folder": str(dest)}
        result = extract_bucket(source, cand, sec)
        completed[str(i)] = result
        save_state(local_state_file, progress)
        processed_now += 1
        if processed_now <= 3 or (i+1) % 10 == 0 or i+1 == n_buckets:
            print(f"[CARGO {i+1}/{n_buckets}] BU={result['raw_bu']:,}; "
                  f"chaves={result['candidate_keys']:,}; "
                  f"secoes={result['sections']:,}; checkpoint OK", flush=True)
    if len(completed) != n_buckets:
        raise RuntimeError("Ainda faltam particoes de origem")
    count = Counter()
    office_section_counts = Counter()
    for result in completed.values():
        for key in ("raw_bu", "candidate_keys", "sections",
                    "paired_pres_gov", "pres_gov_unequal"):
            count[key] += result[key]
        office_section_counts.update(result["by_office_sections"])
    matrix = dest / "secoes_por_cargo.csv"
    consolidate_section_matrix(matrix, section_dir, n_buckets)
    report = {
        "version": VERSION, "status": "concluido",
        "source_fingerprint": fingerprint,
        "input_rows_eligible": source_state["rows_eligible"],
        "offices": list(OFFICES), "offices_description": OFFICE_NAMES,
        "source_bu_rows_selected": count["raw_bu"],
        "candidate_keys": count["candidate_keys"],
        "distinct_sections": count["sections"],
        "sections_by_office": dict(sorted(office_section_counts.items())),
        "paired_president_governor_sections": count["paired_pres_gov"],
        "president_governor_totals_unequal": count["pres_gov_unequal"],
        "partitions": n_buckets, "matrix": str(matrix),
        "matrix_sha256": sha256(matrix), "candidates_dir": str(candidate_dir),
        "note": ("Dados apenas BU por secao; discrepancia de totais "
                 "entre cargos nao implica fraude. Inferencia ideologica "
                 "e voto cruzado exigem classificacao externa, controle "
                 "de regras dos cargos e testes de robustez.")
    }
    save_state(dest / "summary.json", report)
    print("MATRIZ ENTRE CARGOS CONCLUIDA")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", help="Diretorio raiz do acervo TSE")
    parser.add_argument("--pilot-buckets", type=int, default=0,
                        help="Processar apenas N buckets novos e salvar checkpoint")
    args = parser.parse_args()
    run(root_path(args.root), args.pilot_buckets)


if __name__ == "__main__":
    main()
