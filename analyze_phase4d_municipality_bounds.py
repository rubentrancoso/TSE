#!/usr/bin/env python3
"""Fase 4D — decomposição municipal dos estados robustos da Fase 4C.

Estados-alvo:
  MG, MT, RR

Motivo:
Essas três UFs mantiveram violação mínima G>P até no stress test:
  Governador = somente "direita"
  Presidente = "direita + centro-direita + centro"

Esta fase desce para MUNICÍPIO e repete os quatro cenários da Fase 4C.

Por município:
  G = votos no bloco de Governador do cenário
  P = votos no bloco presidencial do cenário
  L = votos em Lula
  N = comparecimento presidencial

Métricas:
  violação mínima = max(0, G - P)
  overlap mínimo Gov-bloco x Lula = max(0, G + L - N)

Como municípios são universos de votação disjuntos, a soma dos mínimos
municipais é um limite inferior válido e pode ser MAIOR que o mínimo estadual,
pois déficits e superávits entre municípios deixam de se cancelar.

Controle de qualidade:
- soma municipal de G/P/L/N comparada ao total estadual;
- reconciliação de votos válidos por arquivo;
- divergência de comparecimento Pres x Gov mantida como informação, não erro.

Fontes:
- configuração municipal do TSE (eleição 6257);
- EA20 municipal final de Presidente (6257/cargo 1);
- EA20 municipal final de Governador (6259/cargo 3);
- classificação partidária ArvorCo/PNAD, commit fixado.

Saídas:
  data/forensics/analysis/phase4d_municipality_bounds.csv
  data/forensics/analysis/phase4d_state_summary.csv
  data/forensics/analysis/phase4d_summary.json
"""

import csv
import hashlib
import json
import os
import time
import unicodedata
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path("data/forensics")
RAW = ROOT / "external"
OUT = ROOT / "analysis"
UA = "TSE-forensics-phase4d/1.0"

TARGET_UFS = {"MG", "MT", "RR"}

ARVOR_COMMIT = "beb3bec9ae5c25e2868ee2f2cefb9e6dccd91415"
CLASSIFIER_URL = (
    "https://raw.githubusercontent.com/ArvorCo/PNAD/"
    f"{ARVOR_COMMIT}/apuracao/public/campos.json"
)
CLASSIFIER_PATH = RAW / "ArvorCo-PNAD" / ARVOR_COMMIT / "campos.json"

PRES_BASE = "https://resultados.tse.jus.br/oficial/ele2026/6257"
GOV_BASE = "https://resultados.tse.jus.br/oficial/ele2026/6259"
PRES_CODE = "006257"
GOV_CODE = "006259"
PRES_OFFICE = "0001"
GOV_OFFICE = "0003"

CONFIG_URL = f"{PRES_BASE}/config/mun-e{PRES_CODE}-cm.json"
CONFIG_PATH = RAW / "tse-final" / "phase4d" / "municipios.json"

SCENARIOS = {
    "strict_symmetric": {
        "gov_fields": {"direita"},
        "pres_fields": {"direita"},
    },
    "broad_symmetric": {
        "gov_fields": {"direita", "centro-direita"},
        "pres_fields": {"direita", "centro-direita"},
    },
    "nonleft_symmetric": {
        "gov_fields": {"direita", "centro-direita", "centro"},
        "pres_fields": {"direita", "centro-direita", "centro"},
    },
    "stress_min_violation": {
        "gov_fields": {"direita"},
        "pres_fields": {"direita", "centro-direita", "centro"},
    },
}


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


def fetch_bytes(url, path, attempts=3):
    if path.exists() and path.stat().st_size:
        return path.read_bytes(), True

    last = None
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": UA, "Cache-Control": "no-cache"},
            )
            with urllib.request.urlopen(req, timeout=90) as r:
                data = r.read()
            atomic_write(path, data)
            return data, False
        except Exception as exc:
            last = exc
            if attempt + 1 < attempts:
                time.sleep(1.0 + attempt)
    raise last


def fetch_json(url, path):
    data, reused = fetch_bytes(url, path)
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


def norm_key(s):
    x = unicodedata.normalize("NFKD", str(s or ""))
    x = "".join(ch for ch in x if not unicodedata.combining(ch))
    return x.upper().strip()


def make_classifier(doc):
    parties = doc.get("partidos", {}) or {}
    return {
        "parties": parties,
        "parties_norm": {norm_key(k): v for k, v in parties.items()},
        "exceptions": doc.get("excecoes", {}) or {},
    }


def class_for_candidate(cand, party, classifier):
    sq = str(cand.get("sqcand", "") or "")
    if sq in classifier["exceptions"]:
        return classifier["exceptions"][sq]

    p = str(party or "").strip()
    if p in classifier["parties"]:
        return classifier["parties"][p]
    return classifier["parties_norm"].get(norm_key(p), "indefinido")


def parse_office(data, office_code, classifier):
    rows = []
    for cargo in data.get("carg", []) or []:
        if str(cargo.get("cd", "")) not in (str(int(office_code)), office_code):
            continue
        for agr in cargo.get("agr", []) or []:
            for par in agr.get("par", []) or []:
                party = par.get("sg", "")
                for cand in par.get("cand", []) or []:
                    valid = str(cand.get("dvt", "") or "") == "Válido"
                    rows.append({
                        "number": str(cand.get("n", "") or ""),
                        "party": party,
                        "field": class_for_candidate(cand, party, classifier),
                        "votes": n(cand.get("vap")),
                        "valid": valid,
                    })
    return rows


def sum_block(rows, fields):
    return sum(
        r["votes"] for r in rows
        if r["valid"] and r["field"] in fields
    )


def valid_sum(rows):
    return sum(r["votes"] for r in rows if r["valid"])


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


def municipality_jobs(config):
    jobs = []
    for region in config.get("abr", []):
        uf = str(region.get("cd", "")).upper()
        if uf not in TARGET_UFS:
            continue
        for city in region.get("mu", []):
            code = str(city.get("cd", ""))
            if not code.isdigit():
                continue
            jobs.append({
                "uf": uf,
                "code": code,
                "name": city.get("nm", ""),
            })
    return jobs


def load_one(job, classifier):
    uf = job["uf"]
    ufl = uf.lower()
    code = job["code"]

    pres_url = (
        f"{PRES_BASE}/dados/{ufl}/"
        f"{ufl}{code}-c{PRES_OFFICE}-e{PRES_CODE}-u.json"
    )
    gov_url = (
        f"{GOV_BASE}/dados/{ufl}/"
        f"{ufl}{code}-c{GOV_OFFICE}-e{GOV_CODE}-u.json"
    )

    pres, pmeta = fetch_json(
        pres_url,
        RAW / "tse-final" / "phase4d" / "president" / ufl / f"{code}.json",
    )
    gov, gmeta = fetch_json(
        gov_url,
        RAW / "tse-final" / "phase4d" / "governor" / ufl / f"{code}.json",
    )

    pres_rows = parse_office(pres, PRES_OFFICE, classifier)
    gov_rows = parse_office(gov, GOV_OFFICE, classifier)

    p_turnout = n((pres.get("e") or {}).get("c"))
    g_turnout = n((gov.get("e") or {}).get("c"))
    p_vv = n((pres.get("v") or {}).get("vv"))
    g_vv = n((gov.get("v") or {}).get("vv"))
    lula = sum(
        r["votes"] for r in pres_rows
        if r["valid"] and r["number"] == "13"
    )

    base = {
        "uf": uf,
        "municipality_code": code,
        "municipality": job["name"],
        "president_turnout": p_turnout,
        "governor_turnout": g_turnout,
        "turnout_difference_gov_minus_pres": g_turnout - p_turnout,
        "lula_votes": lula,
        "president_valid_reported": p_vv,
        "president_valid_sum": valid_sum(pres_rows),
        "president_valid_recon_error": valid_sum(pres_rows) - p_vv,
        "governor_valid_reported": g_vv,
        "governor_valid_sum": valid_sum(gov_rows),
        "governor_valid_recon_error": valid_sum(gov_rows) - g_vv,
    }

    rows = []
    for scenario, cfg in SCENARIOS.items():
        g = sum_block(gov_rows, cfg["gov_fields"])
        p = sum_block(pres_rows, cfg["pres_fields"])
        violation = max(0, g - p)
        min_lula = max(0, g + lula - p_turnout)

        rows.append({
            **base,
            "scenario": scenario,
            "governor_block_votes": g,
            "president_block_votes": p,
            "min_alignment_violation": violation,
            "min_alignment_violation_pct_of_governor_block": pct(violation, g),
            "min_overlap_governor_block_x_lula": min_lula,
            "min_overlap_lula_pct_of_governor_block": pct(min_lula, g),
        })

    return rows, [pmeta, gmeta]


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    classifier_doc, classifier_meta = fetch_json(
        CLASSIFIER_URL, CLASSIFIER_PATH
    )
    classifier = make_classifier(classifier_doc)

    config, config_meta = fetch_json(CONFIG_URL, CONFIG_PATH)
    jobs = municipality_jobs(config)

    print("\nFASE 4D — decomposição municipal dos estados robustos")
    print(
        f"- municípios-alvo: {len(jobs)} "
        f"({', '.join(sorted(TARGET_UFS))})"
    )
    print("- downloads são idempotentes; arquivos já locais serão reutilizados.")

    all_rows = []
    source_meta = [classifier_meta, config_meta]
    errors = []

    workers = min(12, max(1, len(jobs)))
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_map = {
            pool.submit(load_one, job, classifier): job
            for job in jobs
        }
        for fut in as_completed(future_map):
            job = future_map[fut]
            try:
                rows, metas = fut.result()
                all_rows.extend(rows)
                source_meta.extend(metas)
            except Exception as exc:
                errors.append({
                    "uf": job["uf"],
                    "municipality_code": job["code"],
                    "municipality": job["name"],
                    "error": repr(exc),
                })
            done += 1
            if done % 100 == 0 or done == len(jobs):
                print(
                    f"- processados: {done}/{len(jobs)} · erros={len(errors)}",
                    flush=True,
                )

    if errors:
        raise RuntimeError(
            f"Fase 4D teve {len(errors)} erros; primeiro: {errors[0]}"
        )

    all_rows.sort(
        key=lambda r: (
            r["scenario"], r["uf"], r["municipality_code"]
        )
    )

    state_rows = []
    for scenario in SCENARIOS:
        for uf in sorted(TARGET_UFS):
            subset = [
                r for r in all_rows
                if r["scenario"] == scenario and r["uf"] == uf
            ]
            if not subset:
                continue

            g = sum(r["governor_block_votes"] for r in subset)
            p = sum(r["president_block_votes"] for r in subset)
            l = sum(r["lula_votes"] for r in subset)
            n_pres = sum(r["president_turnout"] for r in subset)
            n_gov = sum(r["governor_turnout"] for r in subset)

            state_min = max(0, g - p)
            sum_muni_min = sum(
                r["min_alignment_violation"] for r in subset
            )
            state_lula_min = max(0, g + l - n_pres)
            sum_muni_lula_min = sum(
                r["min_overlap_governor_block_x_lula"]
                for r in subset
            )

            state_rows.append({
                "scenario": scenario,
                "uf": uf,
                "municipalities": len(subset),
                "sum_governor_block_votes": g,
                "sum_president_block_votes": p,
                "sum_lula_votes": l,
                "sum_president_turnout": n_pres,
                "sum_governor_turnout": n_gov,
                "state_level_min_alignment_violation_from_muni_totals": state_min,
                "sum_municipality_min_alignment_violation": sum_muni_min,
                "localization_gain_alignment_violation": (
                    sum_muni_min - state_min
                ),
                "state_level_min_lula_overlap_from_muni_totals": state_lula_min,
                "sum_municipality_min_lula_overlap": sum_muni_lula_min,
                "localization_gain_lula_overlap": (
                    sum_muni_lula_min - state_lula_min
                ),
                "municipalities_with_positive_violation": sum(
                    1 for r in subset
                    if r["min_alignment_violation"] > 0
                ),
                "municipalities_with_positive_lula_overlap": sum(
                    1 for r in subset
                    if r["min_overlap_governor_block_x_lula"] > 0
                ),
                "pres_valid_recon_errors": sum(
                    1 for r in subset
                    if r["president_valid_recon_error"] != 0
                ),
                "gov_valid_recon_errors": sum(
                    1 for r in subset
                    if r["governor_valid_recon_error"] != 0
                ),
            })

    stress = [
        r for r in all_rows
        if r["scenario"] == "stress_min_violation"
    ]

    summary = {
        "format": "tse-forensics-phase4d-municipality-v1",
        "target_ufs": sorted(TARGET_UFS),
        "municipalities": len(jobs),
        "scenarios": {
            k: {
                "gov_fields": sorted(v["gov_fields"]),
                "pres_fields": sorted(v["pres_fields"]),
            }
            for k, v in SCENARIOS.items()
        },
        "state_summary": state_rows,
        "stress_test": {
            "municipalities_with_positive_violation": sum(
                1 for r in stress
                if r["min_alignment_violation"] > 0
            ),
            "municipalities_with_positive_lula_overlap": sum(
                1 for r in stress
                if r["min_overlap_governor_block_x_lula"] > 0
            ),
            "top_violation_municipalities": sorted(
                [
                    r for r in stress
                    if r["min_alignment_violation"] > 0
                ],
                key=lambda r: r["min_alignment_violation"],
                reverse=True,
            )[:30],
            "top_lula_overlap_municipalities": sorted(
                [
                    r for r in stress
                    if r["min_overlap_governor_block_x_lula"] > 0
                ],
                key=lambda r: r["min_overlap_governor_block_x_lula"],
                reverse=True,
            )[:30],
        },
        "quality": {
            "errors": errors,
            "president_valid_recon_error_rows": sum(
                1 for r in all_rows
                if r["scenario"] == "stress_min_violation"
                and r["president_valid_recon_error"] != 0
            ),
            "governor_valid_recon_error_rows": sum(
                1 for r in all_rows
                if r["scenario"] == "stress_min_violation"
                and r["governor_valid_recon_error"] != 0
            ),
            "note": (
                "Comparecimento presidencial > governador pode incluir voto em "
                "trânsito de eleitores de outra UF; N presidencial mantém o "
                "limite Gov×Lula conservador."
            ),
        },
        "sources": source_meta,
        "interpretation": [
            (
                "sum_municipality_min_alignment_violation >= state_level_min "
                "porque déficits locais não podem ser compensados por superávits "
                "de outro município quando se exige alinhamento do mesmo eleitor."
            ),
            (
                "Um município com overlap mínimo Gov-direita×Lula > 0 prova "
                "apenas uma interseção combinatória agregada naquele município."
            ),
            (
                "A próxima etapa deve selecionar os municípios com maiores "
                "mínimos e descer para zona/seção."
            ),
        ],
    }

    muni_fields = [
        "scenario","uf","municipality_code","municipality",
        "president_turnout","governor_turnout",
        "turnout_difference_gov_minus_pres","lula_votes",
        "president_valid_reported","president_valid_sum",
        "president_valid_recon_error","governor_valid_reported",
        "governor_valid_sum","governor_valid_recon_error",
        "governor_block_votes","president_block_votes",
        "min_alignment_violation",
        "min_alignment_violation_pct_of_governor_block",
        "min_overlap_governor_block_x_lula",
        "min_overlap_lula_pct_of_governor_block",
    ]
    write_csv_atomic(
        OUT / "phase4d_municipality_bounds.csv",
        all_rows,
        muni_fields,
    )

    state_fields = [
        "scenario","uf","municipalities",
        "sum_governor_block_votes","sum_president_block_votes",
        "sum_lula_votes","sum_president_turnout","sum_governor_turnout",
        "state_level_min_alignment_violation_from_muni_totals",
        "sum_municipality_min_alignment_violation",
        "localization_gain_alignment_violation",
        "state_level_min_lula_overlap_from_muni_totals",
        "sum_municipality_min_lula_overlap",
        "localization_gain_lula_overlap",
        "municipalities_with_positive_violation",
        "municipalities_with_positive_lula_overlap",
        "pres_valid_recon_errors","gov_valid_recon_errors",
    ]
    write_csv_atomic(
        OUT / "phase4d_state_summary.csv",
        state_rows,
        state_fields,
    )

    atomic_write(
        OUT / "phase4d_summary.json",
        json.dumps(summary, ensure_ascii=False, indent=2).encode("utf-8"),
    )

    print("\nRESULTADO 4D")
    for r in state_rows:
        if r["scenario"] != "stress_min_violation":
            continue
        print(
            f"- {r['uf']} stress: estado >= "
            f"{r['state_level_min_alignment_violation_from_muni_totals']:,} · "
            f"soma mínimos municipais >= "
            f"{r['sum_municipality_min_alignment_violation']:,} · "
            f"Gov×Lula municipal >= "
            f"{r['sum_municipality_min_lula_overlap']:,}"
        )
    print(
        "- municípios stress com violação positiva: "
        f"{summary['stress_test']['municipalities_with_positive_violation']}"
    )
    print(
        "- municípios stress com Gov×Lula mínimo positivo: "
        f"{summary['stress_test']['municipalities_with_positive_lula_overlap']}"
    )
    print(f"- CSV municípios: {OUT / 'phase4d_municipality_bounds.csv'}")
    print(f"- CSV estados: {OUT / 'phase4d_state_summary.csv'}")
    print(f"- resumo: {OUT / 'phase4d_summary.json'}")


if __name__ == "__main__":
    main()
