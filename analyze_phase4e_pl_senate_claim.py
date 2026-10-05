#!/usr/bin/env python3
"""Fase 4E — alegação "votos do PL no Senado > votos de Flávio".

Pergunta pública
================
Foi alegado que a soma nacional dos votos dos candidatos do PL ao Senado
(aprox. 58,1 milhões na postagem recebida) deveria ser comparável diretamente
aos votos de Flávio Bolsonaro para Presidente e que a diferença implicaria
"votos roubados".

Essa comparação direta mistura unidades diferentes:
- Presidente: 1 voto por eleitor;
- Senado em 2026: 2 escolhas por eleitor, para candidatos diferentes.

Logo "votos de candidatos ao Senado" são VOTOS-CANDIDATO, não número de
ELEITORES únicos.

Esta fase mede a alegação corretamente.

Por UF
======
Para todos os candidatos válidos do PL ao Senado:
- S = soma de votos-candidato PL;
- candidatos PL = C1, C2 (quando houver dois);
- limite inferior de eleitores únicos que votaram em pelo menos um PL:
      U_min = max(votos dos candidatos PL)
  porque a mesma pessoa pode ter votado nos dois;
- limite superior:
      U_max = min(comparecimento Senado, S)

Comparação com Presidente:
- F = votos em Flávio;
- L = votos em Lula;
- N = comparecimento presidencial.

Limites conservadores:
- mínimo de eleitores PL-Senado que necessariamente NÃO podem estar no
  conjunto Flávio:
      max(0, U_min - F)
- mínimo de sobreposição PL-Senado x Lula:
      max(0, U_min + L - N)

Como o comparecimento presidencial pode incluir voto em trânsito de pessoas
que não votam para Senado naquela UF, usar N presidencial torna o segundo
limite mais conservador.

Fontes oficiais
===============
- Senado: eleição 6259, cargo 0005
- Presidente: eleição 6257, cargo 0001

Saídas
======
  data/forensics/analysis/phase4e_pl_senate_by_uf.csv
  data/forensics/analysis/phase4e_pl_senate_candidates.csv
  data/forensics/analysis/phase4e_summary.json
"""

import csv
import hashlib
import json
import math
import os
import urllib.request
from pathlib import Path

ROOT = Path("data/forensics")
RAW = ROOT / "external" / "tse-final" / "phase4e"
OUT = ROOT / "analysis"
UA = "TSE-forensics-phase4e/1.0"

BASE = "https://resultados.tse.jus.br/oficial/ele2026"
SEN_ELECTION = "6259"
SEN_CODE = "006259"
SEN_OFFICE = "0005"
PRES_ELECTION = "6257"
PRES_CODE = "006257"
PRES_OFFICE = "0001"

UFS = [
    "ac","al","am","ap","ba","ce","df","es","go","ma","mg","ms","mt",
    "pa","pb","pe","pi","pr","rj","rn","ro","rr","rs","sc","se","sp","to",
]


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


def fetch_json(url, path):
    if path.exists() and path.stat().st_size:
        data = path.read_bytes()
        reused = True
    else:
        req = urllib.request.Request(
            url, headers={"User-Agent": UA, "Cache-Control": "no-cache"}
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            data = r.read()
        atomic_write(path, data)
        reused = False

    return json.loads(data.decode("utf-8-sig")), {
        "url": url,
        "path": str(path),
        "sha256": sha256(data),
        "bytes": len(data),
        "reused": reused,
    }


def n(v):
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


def candidates(data, office_code):
    out = []
    for cargo in data.get("carg", []) or []:
        if str(cargo.get("cd", "")) not in (
            str(int(office_code)), office_code
        ):
            continue
        for agr in cargo.get("agr", []) or []:
            for par in agr.get("par", []) or []:
                party = str(par.get("sg", "") or "")
                for cand in par.get("cand", []) or []:
                    out.append({
                        "number": str(cand.get("n", "") or ""),
                        "candidate": cand.get("nmu") or cand.get("nm"),
                        "full_name": cand.get("nm"),
                        "party": party,
                        "votes": n(cand.get("vap")),
                        "status": str(cand.get("dvt", "") or ""),
                        "valid": str(cand.get("dvt", "") or "") == "Válido",
                    })
    return out


def presidential_votes(rows, number):
    vals = [
        r["votes"] for r in rows
        if r["valid"] and r["number"] == str(number)
    ]
    if not vals:
        raise RuntimeError(f"Candidato presidencial {number} ausente.")
    return sum(vals)


def pct(a, b):
    return 100.0 * a / b if b else None


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

    uf_rows = []
    candidate_rows = []
    sources = []

    for uf in UFS:
        sen_url = (
            f"{BASE}/{SEN_ELECTION}/dados/{uf}/"
            f"{uf}-c{SEN_OFFICE}-e{SEN_CODE}-u.json"
        )
        pres_url = (
            f"{BASE}/{PRES_ELECTION}/dados/{uf}/"
            f"{uf}-c{PRES_OFFICE}-e{PRES_CODE}-u.json"
        )

        sen, smeta = fetch_json(
            sen_url, RAW / "senate" / f"{uf}.json"
        )
        pres, pmeta = fetch_json(
            pres_url, RAW / "president" / f"{uf}.json"
        )
        smeta.update({"scope": uf.upper(), "office": "Senate"})
        pmeta.update({"scope": uf.upper(), "office": "President"})
        sources.extend([smeta, pmeta])

        sen_rows = candidates(sen, SEN_OFFICE)
        pres_rows = candidates(pres, PRES_OFFICE)

        pl = [
            r for r in sen_rows
            if r["valid"] and r["party"].upper() == "PL"
        ]

        for r in pl:
            candidate_rows.append({
                "uf": uf.upper(),
                "candidate": r["candidate"],
                "full_name": r["full_name"],
                "number": r["number"],
                "party": r["party"],
                "votes": r["votes"],
            })

        senate_turnout = n((sen.get("e") or {}).get("c"))
        president_turnout = n((pres.get("e") or {}).get("c"))
        senate_total_vote_slots = n((sen.get("v") or {}).get("tv"))
        senate_valid_candidate_votes = n((sen.get("v") or {}).get("vv"))

        flavio = presidential_votes(pres_rows, "22")
        lula = presidential_votes(pres_rows, "13")

        pl_votes = [r["votes"] for r in pl]
        pl_candidate_votes = sum(pl_votes)
        unique_lb = max(pl_votes) if pl_votes else 0
        unique_ub = min(senate_turnout, pl_candidate_votes)

        forced_not_flavio = max(0, unique_lb - flavio)
        forced_x_flavio = max(
            0, unique_lb + flavio - president_turnout
        )
        forced_x_lula = max(
            0, unique_lb + lula - president_turnout
        )

        uf_rows.append({
            "uf": uf.upper(),
            "pl_senate_candidates": len(pl),
            "pl_senate_candidate_votes": pl_candidate_votes,
            "senate_turnout": senate_turnout,
            "senate_total_vote_slots": senate_total_vote_slots,
            "senate_valid_candidate_votes": senate_valid_candidate_votes,
            "president_turnout": president_turnout,
            "flavio_votes": flavio,
            "lula_votes": lula,
            "unique_pl_senate_voters_lower_bound": unique_lb,
            "unique_pl_senate_voters_upper_bound": unique_ub,
            "raw_pl_candidate_votes_minus_flavio": (
                pl_candidate_votes - flavio
            ),
            "min_unique_pl_senate_voters_not_flavio": forced_not_flavio,
            "min_unique_pl_senate_x_flavio_overlap": forced_x_flavio,
            "min_unique_pl_senate_x_lula_overlap": forced_x_lula,
            "min_not_flavio_pct_of_unique_lower_bound": pct(
                forced_not_flavio, unique_lb
            ),
            "min_lula_overlap_pct_of_unique_lower_bound": pct(
                forced_x_lula, unique_lb
            ),
        })

    # BR final President, to avoid relying only on sum of UFs.
    br_url = (
        f"{BASE}/{PRES_ELECTION}/dados/br/"
        f"br-c{PRES_OFFICE}-e{PRES_CODE}-u.json"
    )
    br, brmeta = fetch_json(br_url, RAW / "president" / "br.json")
    sources.append({
        **brmeta,
        "scope": "BR",
        "office": "President",
    })
    br_rows = candidates(br, PRES_OFFICE)
    br_flavio = presidential_votes(br_rows, "22")
    br_lula = presidential_votes(br_rows, "13")

    total_pl_candidate_votes = sum(
        r["pl_senate_candidate_votes"] for r in uf_rows
    )
    total_unique_lb = sum(
        r["unique_pl_senate_voters_lower_bound"] for r in uf_rows
    )
    total_unique_ub = sum(
        r["unique_pl_senate_voters_upper_bound"] for r in uf_rows
    )
    total_forced_not_flavio = sum(
        r["min_unique_pl_senate_voters_not_flavio"] for r in uf_rows
    )
    total_forced_x_lula = sum(
        r["min_unique_pl_senate_x_lula_overlap"] for r in uf_rows
    )
    total_forced_x_flavio = sum(
        r["min_unique_pl_senate_x_flavio_overlap"] for r in uf_rows
    )

    summary = {
        "format": "tse-forensics-phase4e-pl-senate-claim-v1",
        "question": (
            "É válido comparar a soma dos votos dos candidatos do PL ao Senado "
            "diretamente com os votos de Flávio para Presidente?"
        ),
        "answer_structure": {
            "senate_2026_choices_per_voter": 2,
            "same_senate_candidate_twice": (
                "segundo voto na mesma candidatura é nulo"
            ),
            "unit_warning": (
                "PL Senate total is candidate-votes; President total is "
                "one candidate-vote per voter. They are not the same unit."
            ),
        },
        "national": {
            "pl_senate_candidate_votes": total_pl_candidate_votes,
            "flavio_official_final_votes": br_flavio,
            "lula_official_final_votes": br_lula,
            "raw_candidate_vote_difference_pl_senate_minus_flavio": (
                total_pl_candidate_votes - br_flavio
            ),
            "unique_pl_senate_voters_lower_bound": total_unique_lb,
            "unique_pl_senate_voters_upper_bound": total_unique_ub,
            "min_unique_pl_senate_voters_not_flavio_by_uf_sum": (
                total_forced_not_flavio
            ),
            "min_unique_pl_senate_x_flavio_overlap_by_uf_sum": (
                total_forced_x_flavio
            ),
            "min_unique_pl_senate_x_lula_overlap_by_uf_sum": (
                total_forced_x_lula
            ),
        },
        "quality": {
            "ufs": len(uf_rows),
            "ufs_with_no_valid_pl_senate_candidate": sum(
                1 for r in uf_rows if r["pl_senate_candidates"] == 0
            ),
            "ufs_with_one_valid_pl_senate_candidate": sum(
                1 for r in uf_rows if r["pl_senate_candidates"] == 1
            ),
            "ufs_with_two_valid_pl_senate_candidates": sum(
                1 for r in uf_rows if r["pl_senate_candidates"] == 2
            ),
            "ufs_with_more_than_two_valid_pl_senate_candidates": sum(
                1 for r in uf_rows if r["pl_senate_candidates"] > 2
            ),
            "senate_tv_equals_2x_turnout_all_ufs": all(
                r["senate_total_vote_slots"] == 2 * r["senate_turnout"]
                for r in uf_rows
            ),
            "sum_uf_flavio": sum(r["flavio_votes"] for r in uf_rows),
            "br_flavio": br_flavio,
            "flavio_reconciliation_difference": (
                sum(r["flavio_votes"] for r in uf_rows) - br_flavio
            ),
        },
        "top_raw_candidate_vote_excess": sorted(
            uf_rows,
            key=lambda r: r["raw_pl_candidate_votes_minus_flavio"],
            reverse=True,
        )[:15],
        "top_forced_not_flavio": sorted(
            [
                r for r in uf_rows
                if r["min_unique_pl_senate_voters_not_flavio"] > 0
            ],
            key=lambda r: r["min_unique_pl_senate_voters_not_flavio"],
            reverse=True,
        )[:15],
        "top_forced_lula_overlap": sorted(
            [
                r for r in uf_rows
                if r["min_unique_pl_senate_x_lula_overlap"] > 0
            ],
            key=lambda r: r["min_unique_pl_senate_x_lula_overlap"],
            reverse=True,
        )[:15],
        "method": {
            "unique_PL_voters_lower_bound_per_uf": (
                "max(votes of valid PL Senate candidates)"
            ),
            "unique_PL_voters_upper_bound_per_uf": (
                "min(Senate turnout, sum of PL Senate candidate-votes)"
            ),
            "min_PL_not_Flavio": "max(0, U_min - F)",
            "min_PL_x_Flavio": "max(0, U_min + F - N_pres)",
            "min_PL_x_Lula": "max(0, U_min + L - N_pres)",
        },
        "limitations": [
            (
                "U_min is a lower bound on unique PL-Senate voters, not an "
                "exact count; when PL has two candidates, overlap between their "
                "voter sets is unknown."
            ),
            (
                "Cross-office bounds use presidential turnout as the universe, "
                "which is conservative because President can include out-of-UF "
                "transit voters who were not eligible to vote for Senate there."
            ),
            (
                "No cross-office individual ticket is reconstructed."
            ),
        ],
        "sources": sources,
    }

    uf_fields = [
        "uf","pl_senate_candidates","pl_senate_candidate_votes",
        "senate_turnout","senate_total_vote_slots",
        "senate_valid_candidate_votes","president_turnout",
        "flavio_votes","lula_votes",
        "unique_pl_senate_voters_lower_bound",
        "unique_pl_senate_voters_upper_bound",
        "raw_pl_candidate_votes_minus_flavio",
        "min_unique_pl_senate_voters_not_flavio",
        "min_unique_pl_senate_x_flavio_overlap",
        "min_unique_pl_senate_x_lula_overlap",
        "min_not_flavio_pct_of_unique_lower_bound",
        "min_lula_overlap_pct_of_unique_lower_bound",
    ]
    write_csv_atomic(
        OUT / "phase4e_pl_senate_by_uf.csv", uf_rows, uf_fields
    )

    write_csv_atomic(
        OUT / "phase4e_pl_senate_candidates.csv",
        candidate_rows,
        ["uf","candidate","full_name","number","party","votes"],
    )

    atomic_write(
        OUT / "phase4e_summary.json",
        json.dumps(summary, ensure_ascii=False, indent=2).encode("utf-8"),
    )

    print("\nFASE 4E — alegação PL Senado x Flávio")
    print(
        f"- votos-candidato PL Senado: {total_pl_candidate_votes:,}"
    )
    print(f"- Flávio final oficial: {br_flavio:,}")
    print(
        "- diferença bruta (UNIDADES NÃO COMPARÁVEIS): "
        f"{total_pl_candidate_votes - br_flavio:+,}"
    )
    print(
        "- eleitores únicos PL-Senado possíveis: "
        f"[{total_unique_lb:,}, {total_unique_ub:,}]"
    )
    print(
        "- mínimo obrigatório PL-Senado que não cabe no conjunto Flávio "
        f"(soma UF): {total_forced_not_flavio:,}"
    )
    print(
        "- mínimo obrigatório PL-Senado x Lula (soma UF): "
        f"{total_forced_x_lula:,}"
    )
    print(
        "- Senado tv == 2 x comparecimento em todas as UFs: "
        f"{summary['quality']['senate_tv_equals_2x_turnout_all_ufs']}"
    )
    print(f"- UFs: {OUT / 'phase4e_pl_senate_by_uf.csv'}")
    print(f"- candidatos: {OUT / 'phase4e_pl_senate_candidates.csv'}")
    print(f"- resumo: {OUT / 'phase4e_summary.json'}")


if __name__ == "__main__":
    main()
