#!/usr/bin/env python3
"""Confere os BU de Fernando de Noronha com o JSON oficial da eleicao 6261.

Le somente o CSV ja reconciliado (228 chaves) e baixa no maximo um
resultado agregado oficial (zona 4, cargo 25). Nao abre nem altera SQLite,
checkpoints ou o CSV nacional. Guarda JSON bruto e SHA-256 para auditoria.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request

from urnas import root_path

OFFICIAL = (
    "https://resultados.tse.jus.br/oficial/ele2026/6261/dados/pe/"
    "pe30015-z0004-c0025-e006261-u.json"
)
LOCATION = ("PE", "30015", "4", "1", "25")
VOTES = 2445
SECTIONS = 10
ISSUES = 228


def number(raw):
    text = str(raw).strip()
    if not text or not text.lstrip("+-").isdigit():
        raise ValueError("Valor nao inteiro: " + repr(raw))
    return int(text)


def save_json_once(path, object_value):
    """Cria um relatorio versionado, sem sobrescrever os anteriores."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(object_value, indent=2, ensure_ascii=False)
               + "\n").encode("utf-8")
    if path.is_file():
        if path.read_bytes() != payload:
            raise RuntimeError("Relatorio preexistente diferente: " + str(path))
    else:
        with path.open("xb") as f:
            f.write(payload)


def read_bu(csv_path):
    by_candidate = defaultdict(int)
    sections = set()
    unique = set()
    rows = 0
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        required = {"UF", "municipio", "zona", "secao", "turno", "cargo",
                    "votavel", "votos_BU", "situacao"}
        if not required.issubset(reader.fieldnames or []):
            raise RuntimeError("CSV sem as colunas esperadas")
        for row in reader:
            if row["situacao"] != "SEM_SECAO":
                raise RuntimeError("Situacao inesperada no CSV: " + row["situacao"])
            location = (row["UF"], row["municipio"], row["zona"],
                        row["turno"], row["cargo"])
            if location != LOCATION:
                raise RuntimeError("CSV tem outra localidade/cargo: " + repr(location))
            key = (row["secao"], row["votavel"])
            if key in unique:
                raise RuntimeError("Chave duplicada: " + repr(key))
            unique.add(key)
            rows += 1
            sections.add(row["secao"])
            by_candidate[str(number(row["votavel"]))] += number(row["votos_BU"])
    total = sum(by_candidate.values())
    if (rows, len(sections), total) != (ISSUES, SECTIONS, VOTES):
        raise RuntimeError("Dados BU diferentes do diagnostico esperado: "
                           f"chaves={rows}, secoes={len(sections)}, votos={total}")
    return dict(by_candidate), sorted(sections, key=int), rows


def fetch_official(archive, offline=False):
    """Uma unica URL comprovadamente do dominio oficial; sem varrer 404."""
    archive.mkdir(parents=True, exist_ok=True)
    cache = archive / "oficial-6261-zona4.json"
    if cache.exists():
        body = cache.read_bytes()
        print("FONTE: JSON oficial ja preservado (sem acesso a rede).")
    elif offline:
        raise RuntimeError("Nao existe JSON local. Execute sem --offline.")
    else:
        request = urllib.request.Request(
            OFFICIAL, headers={"User-Agent": "TSE-forensics-6261/1.0",
                               "Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                if response.geturl() != OFFICIAL:
                    raise RuntimeError("Redirecionamento inesperado: " + response.geturl())
                body = response.read(5 * 1024 * 1024 + 1)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Site do TSE respondeu HTTP {exc.code} "
                               "para a URL de resultado da zona. "
                               "Nao tentarei URLs alternativas sem verificacao.") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise RuntimeError(f"Resultado oficial inacessivel: {exc}") from exc
        if len(body) > 5 * 1024 * 1024:
            raise RuntimeError("Arquivo oficial inesperadamente grande")
        # Verifica a sintaxe antes de selar o arquivo original.
        json.loads(body.decode("utf-8-sig"))
        with cache.open("xb") as out:
            out.write(body)
        print("FONTE: JSON da zona 4 obtido do dominio oficial e preservado.")
    digest = hashlib.sha256(body).hexdigest()
    obj = json.loads(body.decode("utf-8-sig"))
    return obj, digest, cache


def official_tallies(doc):
    if str(doc.get("ele")) != "6261":
        raise RuntimeError("JSON nao corresponde a eleicao 6261")
    if str(doc.get("tpabr", "")).lower() != "zona" or number(doc.get("cdabr")) != 4:
        raise RuntimeError("JSON nao corresponde a zona 4")
    cargos = [x for x in doc.get("carg", [])
              if str(x.get("cd", "")).lstrip("0") == "25"]
    if len(cargos) != 1:
        raise RuntimeError("JSON nao contem exatamente um cargo 25")
    expected = {}
    for agg in cargos[0].get("agr", []):
        for party in agg.get("par", []):
            for cand in party.get("cand", []):
                n = str(number(cand["n"]))
                if n in expected:
                    raise RuntimeError("Candidato repetido no resultado: " + n)
                expected[n] = number(cand["vap"])
    if not expected:
        raise RuntimeError("Nao foi possivel extrair votos oficiais por candidato")
    votes_summary = doc.get("v", {})
    # Na especificacao de resultados EA20, 'vb' indica votos brancos
    # e 'tvn' votos nulos totais. No BU, os votaveis especiais sao 95/96.
    if "vb" in votes_summary:
        expected["95"] = number(votes_summary["vb"])
    if "tvn" in votes_summary:
        expected["96"] = number(votes_summary["tvn"])
    return expected, votes_summary, doc.get("s", {})


def compare(bu, official):
    compared = []
    missing = []
    for candidate in sorted(set(bu) | set(official), key=int):
        b = bu.get(candidate, 0)
        v = official.get(candidate)
        if v is None:
            missing.append({"votavel": candidate, "BU": b,
                            "oficial": None, "situacao": "SEM_DADO_OFICIAL"})
        else:
            compared.append({"votavel": candidate, "BU": b,
                             "oficial": v, "diferenca": b - v,
                             "situacao": "OK" if b == v else "DIFERENTE"})
    return compared, missing


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", help="Diretorio do acervo (no Windows, H:)")
    parser.add_argument("--offline", action="store_true",
                        help="Usar somente JSON oficial ja arquivado")
    args = parser.parse_args()
    root = root_path(args.root)
    report = root / "analysis" / "reconciliacao_bu_secao.csv"
    if not report.is_file():
        raise SystemExit("CSV nacional ausente: " + str(report))
    print("ETAPA 6261: auditoria focal, sem reler ou alterar o SQLite")
    bu, sections, rows = read_bu(report)
    print(f"BU: {rows} chaves, {len(sections)} secoes, "
          f"{sum(bu.values()):,} votos, {len(bu)} votaveis.")
    folder = root / "analysis" / "validacao_6261"
    official, sha, cached = fetch_official(folder, offline=args.offline)
    expected, v, s = official_tallies(official)
    comparisons, unpaired = compare(bu, expected)
    different = [x for x in comparisons if x["situacao"] != "OK"]
    total_official = v.get("tv")
    count_official = s.get("st")
    print("URL oficial:", OFFICIAL)
    print("SHA-256 JSON oficial:", sha)
    print("Oficial: eleicao=6261, zona=4, cargo=25")
    print("Seções totalizadas na zona:", count_official)
    print("Votos totais oficiais ('v.tv'):", total_official)
    print(f"Comparacao por votavel: {len(comparisons)} pareados, "
          f"{len(different)} diferentes, {len(unpaired)} sem par.")
    for entry in comparisons:
        print(f"  {entry['votavel']:>4s}: BU={entry['BU']:>4} "
              f"TSE={entry['oficial']:>4} {entry['situacao']}")
    for entry in unpaired:
        print(f"  {entry['votavel']:>4s}: BU={entry['BU']:>4} "
              "sem par no JSON oficial")
    extra = [k for k, v in expected.items() if k not in bu and v != 0]
    if extra:
        print("AVISO: TSE traz votaveis nao presentes no CSV BU:", extra)
    totals_match = (total_official is not None and
                    number(total_official) == sum(bu.values()))
    secs_match = (count_official is not None and
                  number(count_official) == SECTIONS)
    complete = (not different and not unpaired and not extra
                and totals_match and secs_match)
    result = {
        "official_snapshot_utc": datetime.fromtimestamp(
            cached.stat().st_mtime, tz=timezone.utc).isoformat(),
        "status": "EQUIVALENCIA_AGREGADA_CONFIRMADA" if complete
                  else "VERIFICACAO_ADICIONAL_NECESSARIA",
        "method": "soma BU por votavel vs JSON oficial de resultado agregado por zona",
        "warning": "Nao representa comparacao oficial independente por secao",
        "election": 6261, "municipio": 30015, "zona": 4, "cargo": 25,
        "sections_BU": sections, "bu_rows": rows,
        "bu_total_votes": sum(bu.values()), "official_total_votes": total_official,
        "official_sections": count_official,
        "official_url": OFFICIAL, "official_json_sha256": sha,
        "official_local_path": str(cached),
        "candidate_comparisons": comparisons, "unpaired_BU": unpaired,
        "official_extra": extra, "totals_match": totals_match,
        "sections_match": secs_match,
    }
    # Relatorio imutavel por hash de fonte; preserva resultados anteriores.
    dest = folder / ("comparacao_" + sha[:16] + ".json")
    save_json_once(dest, result)
    print("RELATORIO:", dest)
    print("RESULTADO:", result["status"])
    return 0 if complete else 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError) as exc:
        print("FALHA CONTROLADA: " + str(exc), file=sys.stderr)
        sys.exit(1)
