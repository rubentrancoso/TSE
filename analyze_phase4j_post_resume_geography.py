#!/usr/bin/env python3
"""Fase 4J — reconstrução geográfica quase completa do pool pós-20:04.

Fonte de corte
==============
Usa a captura independente preservada em:
  vitoropereira/eleicoes2026
  commit 3f4d7442dd601eb1b11afb8e9510d1373c495e7c
  marcos/75pct/comparacao_fontes.json

Esse arquivo contém, para as 28 abrangências (27 UFs + ZZ), os totais exatos
capturados em 04/10/2026 20:05:57 BRT:
- seções totalizadas;
- votos válidos;
- Flávio;
- Lula.

A captura ocorre 78 segundos depois da retomada nacional de 20:04:39.
Ela soma 100.819.887 votos válidos nas UFs.

Fonte final
===========
Usa o snapshot local final em data/forensics/runs, cuja soma das UFs já foi
reconciliada com o nacional.

Objetivo
========
Reconstruir por UF o conjunto de votos incorporados entre 20:05:57 e o final,
compará-lo ao pool nacional pós-20:04 da Fase 4G e medir exatamente a pequena
fração ainda não coberta entre 20:04:39 e 20:05:57.

Saídas
======
  data/forensics/analysis/phase4j_post_resume_by_uf.csv
  data/forensics/analysis/phase4j_summary.json
"""

import csv
import hashlib
import json
import os
import urllib.request
from pathlib import Path

ROOT = Path("data/forensics")
RUNS = ROOT / "runs"
RAW = ROOT / "external"
OUT = ROOT / "analysis"
PHASE4G = OUT / "phase4g_summary.json"

VITOR_COMMIT = "3f4d7442dd601eb1b11afb8e9510d1373c495e7c"
VITOR_URL = (
    "https://raw.githubusercontent.com/vitoropereira/eleicoes2026/"
    f"{VITOR_COMMIT}/marcos/75pct/comparacao_fontes.json"
)
VITOR_PATH = (
    RAW / "vitoropereira-eleicoes2026" / VITOR_COMMIT / "comparacao_fontes.json"
)
CAPTURE_BRT = "2026-10-04 20:05:57"
RESUME_BRT = "2026-10-04 20:04:39"
LULA = "13"
FLAVIO = "22"
UA = "TSE-forensics-phase4j/1.0"


def n(v):
    try:
        return int(str(v or 0).replace(".", ""))
    except Exception:
        return 0


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


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def fetch_vitor():
    if VITOR_PATH.exists() and VITOR_PATH.stat().st_size:
        data = VITOR_PATH.read_bytes()
        reused = True
    else:
        req = urllib.request.Request(
            VITOR_URL,
            headers={"User-Agent": UA, "Cache-Control": "no-cache"},
        )
        with urllib.request.urlopen(req, timeout=90) as r:
            data = r.read()
        atomic_write(VITOR_PATH, data)
        reused = False

    obj = json.loads(data.decode("utf-8-sig"))
    return obj, {
        "url": VITOR_URL,
        "path": str(VITOR_PATH),
        "sha256": sha256(data),
        "bytes": len(data),
        "reused": reused,
    }


def parse_result(path):
    d = read_json(path)
    cand = {}
    for cargo in d.get("carg", []):
        if str(cargo.get("cd", "1")) != "1":
            continue
        for agr in cargo.get("agr", []):
            for par in agr.get("par", []):
                for c in par.get("cand", []):
                    cand[str(c.get("n", ""))] = n(c.get("vap"))
    s, v = d.get("s", {}), d.get("v", {})
    return {
        "st": n(s.get("st")),
        "ts": n(s.get("ts")),
        "vv": n(v.get("vv")),
        "cand": cand,
    }


def pct(v, total):
    return 100.0 * v / total if total else None


def latest_final_run():
    candidates = []
    for run in RUNS.glob("*"):
        if not run.is_dir():
            continue
        br = run / "live" / "br.json"
        if not br.exists():
            continue
        x = parse_result(br)
        candidates.append((x["st"], x["vv"], run.name, run, x))
    if not candidates:
        raise SystemExit("Nenhum snapshot local nacional encontrado.")
    candidates.sort()
    return candidates[-1][3], candidates[-1][4]


def load_final_ufs(run):
    out = {}
    for path in sorted((run / "live" / "uf").glob("*.json")):
        out[path.stem.upper()] = parse_result(path)
    return out


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

    if not PHASE4G.exists():
        raise SystemExit("Falta phase4g_summary.json.")

    g = read_json(PHASE4G)
    pool = g["remaining_pool"]
    pool_vv = int(pool["valid_votes"])
    pool_lula = int(pool["lula_votes"])
    pool_flavio = int(pool["flavio_votes"])

    vitor, source = fetch_vitor()
    cut_rows = {str(x["uf"]).upper(): x for x in vitor.get("por_uf", [])}
    if len(cut_rows) != 28:
        raise RuntimeError(f"Esperadas 28 abrangências no corte; encontradas {len(cut_rows)}.")

    cut_vv = sum(int(x["vv"]) for x in cut_rows.values())
    cut_lula = sum(int(x["lula"]) for x in cut_rows.values())
    cut_flavio = sum(int(x["flavio"]) for x in cut_rows.values())
    cut_st = sum(int(x["st"]) for x in cut_rows.values())

    # Valor declarado pela própria fonte como soma das UFs no mesmo instante.
    declared = next(
        x for x in vitor.get("leituras", [])
        if x.get("fonte") == "soma das UFs"
    )
    declared_vv = int(declared["votos_validos"])
    declared_st = int(declared["secoes_apuradas"])

    if cut_vv != declared_vv or cut_st != declared_st:
        raise RuntimeError(
            "Soma por UF não fecha com o agregado declarado da captura: "
            f"vv {cut_vv} vs {declared_vv}; st {cut_st} vs {declared_st}"
        )

    final_run, final_br = latest_final_run()
    final_ufs = load_final_ufs(final_run)
    common = sorted(set(cut_rows) & set(final_ufs))
    if len(common) != 28:
        raise RuntimeError(
            f"Interseção corte/final deveria ter 28 abrangências; tem {len(common)}."
        )

    rows = []
    for uf in common:
        a = cut_rows[uf]
        b = final_ufs[uf]
        dvv = b["vv"] - int(a["vv"])
        dl = b["cand"].get(LULA, 0) - int(a["lula"])
        df = b["cand"].get(FLAVIO, 0) - int(a["flavio"])
        dst = b["st"] - int(a["st"])
        rows.append({
            "uf": uf,
            "cut_sections": int(a["st"]),
            "final_sections": b["st"],
            "d_sections": dst,
            "cut_valid_votes": int(a["vv"]),
            "final_valid_votes": b["vv"],
            "d_valid_votes": dvv,
            "d_lula": dl,
            "d_flavio": df,
            "lula_share_tail_pct": pct(dl, dvv),
            "flavio_share_tail_pct": pct(df, dvv),
            "lula_minus_flavio_tail_pp": (
                pct(dl, dvv) - pct(df, dvv) if dvv else None
            ),
            "cut_pct_apurado_source": a.get("pct_apurado"),
            "cut_ht_source": a.get("ht"),
        })

    tail_vv = sum(r["d_valid_votes"] for r in rows)
    tail_lula = sum(r["d_lula"] for r in rows)
    tail_flavio = sum(r["d_flavio"] for r in rows)
    tail_st = sum(r["d_sections"] for r in rows)

    # Confere o final por UFs com o nacional local.
    final_uf_vv = sum(x["vv"] for x in final_ufs.values())
    final_uf_lula = sum(x["cand"].get(LULA, 0) for x in final_ufs.values())
    final_uf_flavio = sum(x["cand"].get(FLAVIO, 0) for x in final_ufs.values())

    if final_uf_vv != final_br["vv"]:
        raise RuntimeError(
            f"Final UF não fecha com BR em válidos: {final_uf_vv} vs {final_br['vv']}"
        )

    uncovered_vv = pool_vv - tail_vv
    uncovered_lula = pool_lula - tail_lula
    uncovered_flavio = pool_flavio - tail_flavio
    coverage_pct = 100.0 * tail_vv / pool_vv if pool_vv else None

    rows.sort(key=lambda x: x["d_valid_votes"], reverse=True)

    summary = {
        "format": "tse-forensics-phase4j-post-resume-by-uf-v1",
        "source_cut": source,
        "cut": {
            "resume_brt": RESUME_BRT,
            "capture_brt": CAPTURE_BRT,
            "seconds_after_resume": 78,
            "ufs": len(cut_rows),
            "sections": cut_st,
            "valid_votes": cut_vv,
            "lula_votes": cut_lula,
            "flavio_votes": cut_flavio,
            "declared_sum_ufs_sections": declared_st,
            "declared_sum_ufs_valid_votes": declared_vv,
            "sum_matches_declared": True,
        },
        "final": {
            "run": final_run.name,
            "sections": final_br["st"],
            "valid_votes": final_br["vv"],
            "sum_ufs_valid_votes": final_uf_vv,
            "br_minus_ufs_valid_votes": final_br["vv"] - final_uf_vv,
            "br_minus_ufs_lula": final_br["cand"].get(LULA, 0) - final_uf_lula,
            "br_minus_ufs_flavio": final_br["cand"].get(FLAVIO, 0) - final_uf_flavio,
        },
        "reconstructed_tail_200557_to_final": {
            "sections": tail_st,
            "valid_votes": tail_vv,
            "lula_votes": tail_lula,
            "flavio_votes": tail_flavio,
            "lula_share_pct": pct(tail_lula, tail_vv),
            "flavio_share_pct": pct(tail_flavio, tail_vv),
            "lula_minus_flavio_margin_pp": (
                pct(tail_lula, tail_vv) - pct(tail_flavio, tail_vv)
                if tail_vv else None
            ),
        },
        "phase4g_pool_200439_to_final": {
            "valid_votes": pool_vv,
            "lula_votes": pool_lula,
            "flavio_votes": pool_flavio,
            "lula_share_pct": pool["lula_share_pct"],
            "flavio_share_pct": pool["flavio_share_pct"],
        },
        "coverage": {
            "covered_valid_votes": tail_vv,
            "covered_pct_of_phase4g_pool": coverage_pct,
            "uncovered_valid_votes": uncovered_vv,
            "uncovered_lula_votes": uncovered_lula,
            "uncovered_flavio_votes": uncovered_flavio,
            "uncovered_window": "20:04:39→20:05:57 BRT",
            "note": (
                "A parcela não coberta é a diferença entre o pool nacional da Fase 4G "
                "e a cauda geográfica iniciada na captura independente das 20:05:57."
            ),
        },
        "largest_uf_contributors_by_valid_votes": [
            {
                "uf": r["uf"],
                "d_valid_votes": r["d_valid_votes"],
                "d_lula": r["d_lula"],
                "d_flavio": r["d_flavio"],
                "lula_share_tail_pct": r["lula_share_tail_pct"],
                "flavio_share_tail_pct": r["flavio_share_tail_pct"],
            }
            for r in rows[:10]
        ],
        "interpretation": [
            (
                "A captura independente por UF ocorre apenas 78 segundos após a retomada "
                "nacional e permite reconstruir deterministicamente quase todo o pool "
                "posterior por geografia."
            ),
            (
                "A pequena parcela entre 20:04:39 e 20:05:57 permanece sem atribuição "
                "geográfica exata nesta fase."
            ),
            (
                "Como o corte por UF fecha internamente com o agregado declarado da própria "
                "fonte e o final fecha UF↔BR, o delta por UF é uma reconstrução aritmética "
                "direta do intervalo coberto."
            ),
        ],
    }

    fields = [
        "uf","cut_sections","final_sections","d_sections",
        "cut_valid_votes","final_valid_votes","d_valid_votes",
        "d_lula","d_flavio","lula_share_tail_pct","flavio_share_tail_pct",
        "lula_minus_flavio_tail_pp","cut_pct_apurado_source","cut_ht_source",
    ]
    write_csv_atomic(OUT / "phase4j_post_resume_by_uf.csv", rows, fields)
    atomic_write(
        OUT / "phase4j_summary.json",
        json.dumps(summary, ensure_ascii=False, indent=2).encode("utf-8"),
    )

    print("\nFASE 4J — reconstrução geográfica pós-retomada")
    print(
        f"- corte independente: {CAPTURE_BRT[11:]} BRT · "
        f"{cut_vv:,} válidos · {cut_st:,} seções"
    )
    print(
        f"- cauda reconstruída: {tail_vv:,} válidos · "
        f"{coverage_pct:.2f}% do pool pós-20:04"
    )
    print(
        f"- Lula={pct(tail_lula, tail_vv):.2f}% · "
        f"Flávio={pct(tail_flavio, tail_vv):.2f}% · "
        f"margem={pct(tail_lula, tail_vv)-pct(tail_flavio, tail_vv):+.2f} pp"
    )
    print(
        f"- não coberto 20:04:39→20:05:57: {uncovered_vv:,} válidos "
        f"({100.0*uncovered_vv/pool_vv:.2f}% do pool)"
    )
    print(
        f"- final UF↔BR válidos: diferença {final_br['vv']-final_uf_vv:+,}"
    )
    print("- maiores contribuições por válidos:")
    for r in rows[:10]:
        print(
            f"  {r['uf']}: {r['d_valid_votes']:,} · "
            f"Lula={r['lula_share_tail_pct']:.2f}% · "
            f"Flávio={r['flavio_share_tail_pct']:.2f}%"
        )
    print(f"- CSV: {OUT / 'phase4j_post_resume_by_uf.csv'}")
    print(f"- resumo: {OUT / 'phase4j_summary.json'}")


if __name__ == "__main__":
    main()
