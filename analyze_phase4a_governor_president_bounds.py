#!/usr/bin/env python3
"""Fase 4A — triagem Governador-direita/centro-direita x Presidente.

Hipótese de trabalho:
eleitores que votam em candidatura classificada como direita/centro-direita
para Governador tendem a votar também à direita para Presidente.

Esta fase NÃO tenta reconstruir o voto individual. Ela calcula limites
matemáticos inevitáveis no agregado de cada UF para candidaturas a Governador
classificadas como "direita" ou "centro-direita" pela fonte ArvorCo/PNAD.

Para cada candidatura G:
- N = comparecimento presidencial na UF;
- L = votos em Lula;
- F = votos em Flávio Bolsonaro;
- G = votos na candidatura a Governador.

Limites:
- sobreposição mínima Governador G x Lula:
      max(0, G + L - N)
- sobreposição máxima:
      min(G, L)
- mínimo de eleitores de G que NÃO podem estar contidos no conjunto de votos
  de Flávio:
      max(0, G - F)

O último limite é específico a Flávio, não ao conceito amplo "Presidente de
direita", pois outros presidenciáveis podem também ser classificados à direita.

Classificação:
- cenário A = campo atribuído pela fonte ArvorCo/PNAD;
- entram "direita" e "centro-direita";
- a classificação é preservada explicitamente no CSV para futura análise de
  sensibilidade.

A fonte de Governador traz apenas a candidatura eleita ou o par do 2º turno
em ufs[].candidatos; portanto esta fase é uma TRIAGEM de candidaturas
principais, não ainda o bloco completo de todos os candidatos de direita.

Saídas:
  data/forensics/analysis/phase4a_governor_president_bounds.csv
  data/forensics/analysis/phase4a_summary.json
"""

import csv
import hashlib
import json
import os
import urllib.request
from pathlib import Path

ROOT = Path("data/forensics")
RAW = ROOT / "external"
OUT = ROOT / "analysis"
UA = "TSE-forensics-phase4a/1.0"

ARVOR_COMMIT = "beb3bec9ae5c25e2868ee2f2cefb9e6dccd91415"
GOV_URL = (
    "https://raw.githubusercontent.com/ArvorCo/PNAD/"
    f"{ARVOR_COMMIT}/analysis/apuracao_2026/dados/governadores.json"
)
GOV_PATH = RAW / "ArvorCo-PNAD" / ARVOR_COMMIT / "governadores.json"

TSE_BASE = "https://resultados.tse.jus.br/oficial/ele2026/6257/dados"
ELECTION_CODE = "006257"
PRES_OFFICE = "0001"

RIGHT_FIELDS = {"direita", "centro-direita"}


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
        with urllib.request.urlopen(req, timeout=90) as r:
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


def candidate_votes(data, number):
    total = 0
    found = False
    for cargo in data.get("carg", []) or []:
        if str(cargo.get("cd", "")) not in ("1", "0001"):
            continue
        for agr in cargo.get("agr", []) or []:
            for par in agr.get("par", []) or []:
                for cand in par.get("cand", []) or []:
                    if str(cand.get("n", "")) == str(number):
                        total += n(cand.get("vap"))
                        found = True
    if not found:
        raise RuntimeError(f"Candidato presidencial {number} não encontrado.")
    return total


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

    gov, gov_meta = fetch_json(GOV_URL, GOV_PATH)

    rows = []
    pres_sources = []

    for uf_item in gov.get("ufs", []):
        uf = str(uf_item.get("uf", "")).upper()
        if not uf:
            continue

        right_candidates = [
            c for c in (uf_item.get("candidatos") or [])
            if c.get("campo") in RIGHT_FIELDS
        ]
        if not right_candidates:
            continue

        ufl = uf.lower()
        pres_url = (
            f"{TSE_BASE}/{ufl}/"
            f"{ufl}-c{PRES_OFFICE}-e{ELECTION_CODE}-u.json"
        )
        pres, meta = fetch_json(
            pres_url,
            RAW / "tse-final" / "phase4a-president" / f"{ufl}.json",
        )
        meta["scope"] = uf
        pres_sources.append(meta)

        turnout = n((pres.get("e") or {}).get("c"))
        electorate = n((pres.get("e") or {}).get("te"))
        lula = candidate_votes(pres, "13")
        flavio = candidate_votes(pres, "22")

        if turnout <= 0:
            raise RuntimeError(f"{uf}: comparecimento presidencial inválido.")

        for cand in right_candidates:
            g = n(cand.get("votos"))
            min_lula = max(0, g + lula - turnout)
            max_lula = min(g, lula)
            min_not_flavio = max(0, g - flavio)

            rows.append({
                "uf": uf,
                "governor_source_status": uf_item.get("fonte"),
                "governor_decision": uf_item.get("decisao"),
                "candidate": cand.get("nome"),
                "party": cand.get("partido"),
                "field_classification": cand.get("campo"),
                "governor_votes": g,
                "governor_pct_valid_reported": cand.get("pct"),
                "president_turnout": turnout,
                "president_electorate": electorate,
                "lula_votes": lula,
                "flavio_votes": flavio,
                "governor_share_of_turnout_pct": pct(g, turnout),
                "lula_share_of_turnout_pct": pct(lula, turnout),
                "flavio_share_of_turnout_pct": pct(flavio, turnout),
                "min_overlap_governor_candidate_x_lula": min_lula,
                "max_overlap_governor_candidate_x_lula": max_lula,
                "min_overlap_pct_of_governor_votes": pct(min_lula, g),
                "max_overlap_pct_of_governor_votes": pct(max_lula, g),
                "min_governor_voters_not_flavio": min_not_flavio,
                "min_not_flavio_pct_of_governor_votes": pct(min_not_flavio, g),
                "candidate_minus_flavio_votes": g - flavio,
            })

    rows.sort(
        key=lambda r: (
            -r["min_overlap_governor_candidate_x_lula"],
            -r["min_governor_voters_not_flavio"],
            r["uf"],
        )
    )

    positive_overlap = [
        r for r in rows if r["min_overlap_governor_candidate_x_lula"] > 0
    ]
    positive_not_flavio = [
        r for r in rows if r["min_governor_voters_not_flavio"] > 0
    ]

    summary = {
        "format": "tse-forensics-phase4a-governor-president-bounds-v1",
        "hypothesis": (
            "Quem vota em candidatura a Governador classificada como direita/"
            "centro-direita tende a votar à direita para Presidente."
        ),
        "classification_scenario": {
            "name": "ArvorCo campo A",
            "included_fields": sorted(RIGHT_FIELDS),
            "source": gov_meta,
            "note": (
                "Classificação externa preservada como entrada explícita; "
                "não é tratada como verdade ontológica e poderá ser substituída "
                "por cenários alternativos."
            ),
        },
        "coverage": {
            "ufs_with_screened_candidates": len(set(r["uf"] for r in rows)),
            "screened_candidates": len(rows),
            "candidates_with_forced_minimum_lula_overlap": len(positive_overlap),
            "candidates_with_forced_minimum_not_flavio": len(positive_not_flavio),
            "governor_source_provisorio_rows": sum(
                1 for r in rows if r["governor_source_status"] == "provisorio"
            ),
        },
        "totals_descriptive": {
            "sum_minimum_lula_overlap_across_candidates": sum(
                r["min_overlap_governor_candidate_x_lula"]
                for r in rows
            ),
            "sum_minimum_not_flavio_across_candidates": sum(
                r["min_governor_voters_not_flavio"]
                for r in rows
            ),
            "warning": (
                "Somas entre candidaturas são apenas descritivas e não devem ser "
                "interpretadas como pessoas únicas, especialmente quando uma UF "
                "tem mais de uma candidatura filtrada."
            ),
        },
        "top_forced_lula_overlap": positive_overlap[:15],
        "top_forced_not_flavio": sorted(
            positive_not_flavio,
            key=lambda r: r["min_governor_voters_not_flavio"],
            reverse=True,
        )[:15],
        "method": {
            "min_overlap_governor_x_lula": "max(0, G + L - N)",
            "max_overlap_governor_x_lula": "min(G, L)",
            "min_governor_not_flavio": "max(0, G - F)",
            "N": "comparecimento presidencial oficial na UF",
            "G": "votos da candidatura a Governador na fonte de classificação",
            "L": "votos oficiais em Lula na UF",
            "F": "votos oficiais em Flávio Bolsonaro na UF",
        },
        "limitations": [
            (
                "Esta fase usa candidaturas principais em ufs[].candidatos "
                "(eleita ou par de 2º turno), não o bloco completo de todas as "
                "candidaturas de direita."
            ),
            (
                "Limite positivo Governador×Lula prova apenas que alguma "
                "sobreposição é matematicamente inevitável no agregado; não "
                "identifica indivíduos."
            ),
            (
                "min_governor_not_flavio não equivale a 'não votou em candidato "
                "presidencial de direita', pois há outros presidenciáveis além de Flávio."
            ),
            (
                "AL/AM podem aparecer como fonte provisória no produto externo; "
                "isso será tratado separadamente antes de qualquer conclusão forte."
            ),
        ],
        "president_sources": pres_sources,
    }

    fields = [
        "uf","governor_source_status","governor_decision","candidate","party",
        "field_classification","governor_votes","governor_pct_valid_reported",
        "president_turnout","president_electorate","lula_votes","flavio_votes",
        "governor_share_of_turnout_pct","lula_share_of_turnout_pct",
        "flavio_share_of_turnout_pct",
        "min_overlap_governor_candidate_x_lula",
        "max_overlap_governor_candidate_x_lula",
        "min_overlap_pct_of_governor_votes",
        "max_overlap_pct_of_governor_votes",
        "min_governor_voters_not_flavio",
        "min_not_flavio_pct_of_governor_votes",
        "candidate_minus_flavio_votes",
    ]
    write_csv_atomic(
        OUT / "phase4a_governor_president_bounds.csv",
        rows,
        fields,
    )
    atomic_write(
        OUT / "phase4a_summary.json",
        json.dumps(summary, ensure_ascii=False, indent=2).encode("utf-8"),
    )

    print("\nFASE 4A — Governador direita/CD x Presidente")
    print(f"- candidaturas triadas: {len(rows)}")
    print(
        "- com sobreposição mínima matemática Governador×Lula > 0: "
        f"{len(positive_overlap)}"
    )
    print(
        "- com mínimo de eleitores do Governador fora do conjunto Flávio > 0: "
        f"{len(positive_not_flavio)}"
    )
    if positive_overlap:
        print("- maiores sobreposições mínimas com Lula:")
        for r in positive_overlap[:10]:
            print(
                f"  {r['uf']} {r['candidate']}: "
                f">={r['min_overlap_governor_candidate_x_lula']:,} "
                f"({r['min_overlap_pct_of_governor_votes']:.2f}% dos votos do Gov.)"
            )
    print(f"- CSV: {OUT / 'phase4a_governor_president_bounds.csv'}")
    print(f"- resumo: {OUT / 'phase4a_summary.json'}")


if __name__ == "__main__":
    main()
