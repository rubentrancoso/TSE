#!/usr/bin/env python3
"""Fase 4B — bloco completo Governador-direita/CD x Presidente-direita/CD.

Objetivo
=======
Testar em TODAS as 27 UFs a hipótese de alinhamento ideológico usando todos os
candidatos válidos a Governador e Presidente, não apenas os principais.

Classificação
=============
Usa o classificador explícito de partidos do ArvorCo/PNAD no commit fixado:
  apuracao/public/campos.json

Cenário A:
  direita + centro-direita = bloco "direita ampliada".

Exceções por sqcand definidas na própria fonte têm precedência sobre o partido.

Conjuntos por UF
================
N   = comparecimento presidencial
G_R = votos válidos em TODOS os candidatos a Governador classificados
      direita/centro-direita
P_R = votos válidos em TODOS os candidatos a Presidente classificados
      direita/centro-direita
L   = votos em Lula

Como cada eleitor pode votar em no máximo um Governador e um Presidente:

- mínimo de eleitores Governador-direita que NÃO podem estar no conjunto
  Presidente-direita:
      max(0, G_R - P_R)

- sobreposição mínima Governador-direita x Presidente-direita:
      max(0, G_R + P_R - N)

- sobreposição máxima Governador-direita x Presidente-direita:
      min(G_R, P_R)

- sobreposição mínima Governador-direita x Lula:
      max(0, G_R + L - N)

- sobreposição máxima Governador-direita x Lula:
      min(G_R, L)

Esses são limites de conjuntos, não reconstrução de voto individual.

Fontes
======
- TSE final por UF, Governador:
  /oficial/ele2026/6259/dados/{uf}/{uf}-c0003-e006259-u.json
- TSE final por UF, Presidente:
  /oficial/ele2026/6257/dados/{uf}/{uf}-c0001-e006257-u.json
- classificador:
  ArvorCo/PNAD apuracao/public/campos.json

Saídas
======
  data/forensics/analysis/phase4b_uf_blocks.csv
  data/forensics/analysis/phase4b_candidate_inventory.csv
  data/forensics/analysis/phase4b_summary.json
"""

import csv
import hashlib
import json
import os
import unicodedata
import urllib.request
from pathlib import Path

ROOT = Path("data/forensics")
RAW = ROOT / "external"
OUT = ROOT / "analysis"
UA = "TSE-forensics-phase4b/1.0"

ARVOR_COMMIT = "beb3bec9ae5c25e2868ee2f2cefb9e6dccd91415"
CLASSIFIER_URL = (
    "https://raw.githubusercontent.com/ArvorCo/PNAD/"
    f"{ARVOR_COMMIT}/apuracao/public/campos.json"
)
CLASSIFIER_PATH = RAW / "ArvorCo-PNAD" / ARVOR_COMMIT / "campos.json"

TSE_BASE = "https://resultados.tse.jus.br/oficial/ele2026"
PRES_ELECTION = "6257"
PRES_ELECTION_CODE = "006257"
PRES_OFFICE = "0001"
GOV_ELECTION = "6259"
GOV_ELECTION_CODE = "006259"
GOV_OFFICE = "0003"

UFS = [
    "ac","al","am","ap","ba","ce","df","es","go","ma","mg","ms","mt",
    "pa","pb","pe","pi","pr","rj","rn","ro","rr","rs","sc","se","sp","to",
]

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


def norm_party(s):
    s = str(s or "").strip()
    # Keep accents for exact map first; provide simple fallback aliases too.
    return s


def class_for_candidate(cand, party, classifier):
    exceptions = classifier.get("excecoes", {}) or {}
    sq = str(cand.get("sqcand", "") or "")
    if sq in exceptions:
        return exceptions[sq], "exception"

    parties = classifier.get("partidos", {}) or {}
    p = norm_party(party)
    if p in parties:
        return parties[p], "party"

    # conservative fallback only for accent/case formatting differences
    def key(x):
        x = unicodedata.normalize("NFKD", str(x))
        x = "".join(ch for ch in x if not unicodedata.combining(ch))
        return x.upper().strip()

    target = key(p)
    matches = {key(k): v for k, v in parties.items()}
    if target in matches:
        return matches[target], "party_normalized"

    return "indefinido", "unclassified"


def parse_candidates(data, office_code, office_label, uf, classifier):
    rows = []
    for cargo in data.get("carg", []) or []:
        if str(cargo.get("cd", "")) not in (str(int(office_code)), office_code):
            continue
        for agr in cargo.get("agr", []) or []:
            for par in agr.get("par", []) or []:
                party = par.get("sg", "")
                for cand in par.get("cand", []) or []:
                    field, class_source = class_for_candidate(
                        cand, party, classifier
                    )
                    dvt = str(cand.get("dvt", "") or "")
                    valid = dvt == "Válido"
                    rows.append({
                        "uf": uf.upper(),
                        "office": office_label,
                        "office_code": office_code,
                        "candidate_number": cand.get("n"),
                        "sqcand": cand.get("sqcand"),
                        "candidate": cand.get("nmu") or cand.get("nm"),
                        "candidate_full_name": cand.get("nm"),
                        "party": party,
                        "field_classification": field,
                        "classification_source": class_source,
                        "vote_status": dvt,
                        "is_valid_candidate_vote": valid,
                        "votes": n(cand.get("vap")),
                        "is_right_block": valid and field in RIGHT_FIELDS,
                    })
    return rows


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

    classifier_doc, classifier_meta = fetch_json(
        CLASSIFIER_URL, CLASSIFIER_PATH
    )
    classifier = {
        "partidos": classifier_doc.get("partidos", {}),
        "excecoes": classifier_doc.get("excecoes", {}),
    }

    inventory = []
    uf_rows = []
    source_meta = [classifier_meta]

    for uf in UFS:
        pres_url = (
            f"{TSE_BASE}/{PRES_ELECTION}/dados/{uf}/"
            f"{uf}-c{PRES_OFFICE}-e{PRES_ELECTION_CODE}-u.json"
        )
        gov_url = (
            f"{TSE_BASE}/{GOV_ELECTION}/dados/{uf}/"
            f"{uf}-c{GOV_OFFICE}-e{GOV_ELECTION_CODE}-u.json"
        )

        pres, pmeta = fetch_json(
            pres_url,
            RAW / "tse-final" / "phase4b" / "president" / f"{uf}.json",
        )
        gov, gmeta = fetch_json(
            gov_url,
            RAW / "tse-final" / "phase4b" / "governor" / f"{uf}.json",
        )
        pmeta["scope"] = uf.upper()
        pmeta["office"] = "President"
        gmeta["scope"] = uf.upper()
        gmeta["office"] = "Governor"
        source_meta.extend([pmeta, gmeta])

        pres_cands = parse_candidates(
            pres, PRES_OFFICE, "President", uf, classifier
        )
        gov_cands = parse_candidates(
            gov, GOV_OFFICE, "Governor", uf, classifier
        )
        inventory.extend(pres_cands)
        inventory.extend(gov_cands)

        p_turnout = n((pres.get("e") or {}).get("c"))
        g_turnout = n((gov.get("e") or {}).get("c"))
        electorate = n((pres.get("e") or {}).get("te"))
        p_vv = n((pres.get("v") or {}).get("vv"))
        g_vv = n((gov.get("v") or {}).get("vv"))

        pres_valid_sum = sum(
            r["votes"] for r in pres_cands if r["is_valid_candidate_vote"]
        )
        gov_valid_sum = sum(
            r["votes"] for r in gov_cands if r["is_valid_candidate_vote"]
        )

        g_right = sum(
            r["votes"] for r in gov_cands if r["is_right_block"]
        )
        p_right = sum(
            r["votes"] for r in pres_cands if r["is_right_block"]
        )
        lula = sum(
            r["votes"] for r in pres_cands
            if r["is_valid_candidate_vote"] and str(r["candidate_number"]) == "13"
        )
        flavio = sum(
            r["votes"] for r in pres_cands
            if r["is_valid_candidate_vote"] and str(r["candidate_number"]) == "22"
        )

        nbase = p_turnout
        min_not_pres_right = max(0, g_right - p_right)
        min_align = max(0, g_right + p_right - nbase)
        max_align = min(g_right, p_right)
        min_lula = max(0, g_right + lula - nbase)
        max_lula = min(g_right, lula)

        unclassified_gov = sum(
            r["votes"] for r in gov_cands
            if r["is_valid_candidate_vote"]
            and r["field_classification"] == "indefinido"
        )
        unclassified_pres = sum(
            r["votes"] for r in pres_cands
            if r["is_valid_candidate_vote"]
            and r["field_classification"] == "indefinido"
        )

        uf_rows.append({
            "uf": uf.upper(),
            "president_turnout": p_turnout,
            "governor_turnout": g_turnout,
            "turnout_difference_gov_minus_pres": g_turnout - p_turnout,
            "electorate": electorate,
            "president_valid_votes_reported": p_vv,
            "president_valid_candidate_sum": pres_valid_sum,
            "president_valid_reconciliation_error": pres_valid_sum - p_vv,
            "governor_valid_votes_reported": g_vv,
            "governor_valid_candidate_sum": gov_valid_sum,
            "governor_valid_reconciliation_error": gov_valid_sum - g_vv,
            "governor_right_block_votes": g_right,
            "president_right_block_votes": p_right,
            "lula_votes": lula,
            "flavio_votes": flavio,
            "governor_right_share_turnout_pct": pct(g_right, nbase),
            "president_right_share_turnout_pct": pct(p_right, nbase),
            "lula_share_turnout_pct": pct(lula, nbase),
            "min_governor_right_not_president_right": min_not_pres_right,
            "min_violation_pct_of_governor_right": pct(
                min_not_pres_right, g_right
            ),
            "min_overlap_governor_right_x_president_right": min_align,
            "max_overlap_governor_right_x_president_right": max_align,
            "min_alignment_pct_of_governor_right": pct(min_align, g_right),
            "max_alignment_pct_of_governor_right": pct(max_align, g_right),
            "min_overlap_governor_right_x_lula": min_lula,
            "max_overlap_governor_right_x_lula": max_lula,
            "min_lula_overlap_pct_of_governor_right": pct(min_lula, g_right),
            "max_lula_overlap_pct_of_governor_right": pct(max_lula, g_right),
            "unclassified_governor_valid_votes": unclassified_gov,
            "unclassified_president_valid_votes": unclassified_pres,
        })

    # Data-quality checks
    bad_turnout = [
        r for r in uf_rows
        if r["turnout_difference_gov_minus_pres"] != 0
    ]
    bad_pres_recon = [
        r for r in uf_rows
        if r["president_valid_reconciliation_error"] != 0
    ]
    bad_gov_recon = [
        r for r in uf_rows
        if r["governor_valid_reconciliation_error"] != 0
    ]

    forced_violation = [
        r for r in uf_rows
        if r["min_governor_right_not_president_right"] > 0
    ]
    forced_lula = [
        r for r in uf_rows
        if r["min_overlap_governor_right_x_lula"] > 0
    ]

    summary = {
        "format": "tse-forensics-phase4b-full-right-block-v1",
        "hypothesis": (
            "Quem vota no bloco Governador direita/centro-direita tende a votar "
            "no bloco Presidente direita/centro-direita."
        ),
        "classification": {
            "source": classifier_meta,
            "right_fields": sorted(RIGHT_FIELDS),
            "party_map_entries": len(classifier.get("partidos", {})),
            "candidate_exceptions": len(classifier.get("excecoes", {})),
        },
        "coverage": {
            "ufs": len(uf_rows),
            "candidate_inventory_rows": len(inventory),
            "ufs_forced_alignment_violation": len(forced_violation),
            "ufs_forced_governor_right_x_lula_overlap": len(forced_lula),
        },
        "data_quality": {
            "ufs_turnout_difference_nonzero": len(bad_turnout),
            "turnout_difference_rows": bad_turnout,
            "ufs_president_valid_reconciliation_error": len(bad_pres_recon),
            "president_reconciliation_rows": bad_pres_recon,
            "ufs_governor_valid_reconciliation_error": len(bad_gov_recon),
            "governor_reconciliation_rows": bad_gov_recon,
            "total_unclassified_governor_valid_votes": sum(
                r["unclassified_governor_valid_votes"] for r in uf_rows
            ),
            "total_unclassified_president_valid_votes": sum(
                r["unclassified_president_valid_votes"] for r in uf_rows
            ),
        },
        "top_forced_alignment_violation": sorted(
            forced_violation,
            key=lambda r: r["min_governor_right_not_president_right"],
            reverse=True,
        )[:15],
        "top_forced_lula_overlap": sorted(
            forced_lula,
            key=lambda r: r["min_overlap_governor_right_x_lula"],
            reverse=True,
        )[:15],
        "all_ufs": uf_rows,
        "method": {
            "min_violation": "max(0, G_R - P_R)",
            "min_alignment_overlap": "max(0, G_R + P_R - N)",
            "max_alignment_overlap": "min(G_R, P_R)",
            "min_lula_overlap": "max(0, G_R + L - N)",
            "max_lula_overlap": "min(G_R, L)",
            "N": "comparecimento presidencial oficial da UF",
        },
        "limitations": [
            (
                "Os limites são matemáticos para conjuntos agregados; não "
                "reconstroem o voto individual."
            ),
            (
                "A conclusão depende do cenário de classificação partidária. "
                "Outros cenários devem ser testados para sensibilidade."
            ),
            (
                "Votos de candidaturas com dvt diferente de 'Válido' são "
                "preservados no inventário, mas excluídos dos blocos."
            ),
        ],
        "sources": source_meta,
    }

    uf_fields = [
        "uf","president_turnout","governor_turnout",
        "turnout_difference_gov_minus_pres","electorate",
        "president_valid_votes_reported","president_valid_candidate_sum",
        "president_valid_reconciliation_error",
        "governor_valid_votes_reported","governor_valid_candidate_sum",
        "governor_valid_reconciliation_error",
        "governor_right_block_votes","president_right_block_votes",
        "lula_votes","flavio_votes","governor_right_share_turnout_pct",
        "president_right_share_turnout_pct","lula_share_turnout_pct",
        "min_governor_right_not_president_right",
        "min_violation_pct_of_governor_right",
        "min_overlap_governor_right_x_president_right",
        "max_overlap_governor_right_x_president_right",
        "min_alignment_pct_of_governor_right",
        "max_alignment_pct_of_governor_right",
        "min_overlap_governor_right_x_lula",
        "max_overlap_governor_right_x_lula",
        "min_lula_overlap_pct_of_governor_right",
        "max_lula_overlap_pct_of_governor_right",
        "unclassified_governor_valid_votes",
        "unclassified_president_valid_votes",
    ]
    write_csv_atomic(OUT / "phase4b_uf_blocks.csv", uf_rows, uf_fields)

    inv_fields = [
        "uf","office","office_code","candidate_number","sqcand","candidate",
        "candidate_full_name","party","field_classification",
        "classification_source","vote_status","is_valid_candidate_vote",
        "votes","is_right_block",
    ]
    write_csv_atomic(
        OUT / "phase4b_candidate_inventory.csv", inventory, inv_fields
    )

    atomic_write(
        OUT / "phase4b_summary.json",
        json.dumps(summary, ensure_ascii=False, indent=2).encode("utf-8"),
    )

    print("\nFASE 4B — bloco completo Gov-direita/CD x Pres-direita/CD")
    print(f"- UFs analisadas: {len(uf_rows)}")
    print(
        "- UFs com violação mínima obrigatória G_R→P_R > 0: "
        f"{len(forced_violation)}"
    )
    print(
        "- UFs com sobreposição mínima obrigatória G_R×Lula > 0: "
        f"{len(forced_lula)}"
    )
    print(
        "- qualidade: turnout divergente="
        f"{len(bad_turnout)} · recon Pres={len(bad_pres_recon)} · "
        f"recon Gov={len(bad_gov_recon)}"
    )
    if forced_violation:
        print("- maiores violações mínimas:")
        for r in sorted(
            forced_violation,
            key=lambda x: x["min_governor_right_not_president_right"],
            reverse=True,
        )[:10]:
            print(
                f"  {r['uf']}: >= {r['min_governor_right_not_president_right']:,} "
                f"({r['min_violation_pct_of_governor_right']:.2f}% de G_R)"
            )
    if forced_lula:
        print("- maiores sobreposições mínimas Gov-direita×Lula:")
        for r in sorted(
            forced_lula,
            key=lambda x: x["min_overlap_governor_right_x_lula"],
            reverse=True,
        )[:10]:
            print(
                f"  {r['uf']}: >= {r['min_overlap_governor_right_x_lula']:,} "
                f"({r['min_lula_overlap_pct_of_governor_right']:.2f}% de G_R)"
            )
    print(f"- UFs: {OUT / 'phase4b_uf_blocks.csv'}")
    print(f"- inventário: {OUT / 'phase4b_candidate_inventory.csv'}")
    print(f"- resumo: {OUT / 'phase4b_summary.json'}")


if __name__ == "__main__":
    main()
