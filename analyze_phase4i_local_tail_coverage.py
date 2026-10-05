#!/usr/bin/env python3
"""Fase 4I — cobertura local e reconstrução geográfica da cauda pós-20:04.

Objetivo
========
A Fase 4G estabeleceu que, após 20:04:39 BRT, restavam 18.809.656 votos
válidos no arquivo nacional. A Fase 4H mostrou que zonas que concluíam tarde
eram estruturalmente mais pró-Lula, também em 2022, mas não reconstruiu o pool
real porque zonas ainda incompletas já haviam contribuído votos antes do corte.

Esta fase responde primeiro a uma pergunta de cadeia de custódia:
  quanto desse pool está efetivamente coberto pelos snapshots locais em
  data/forensics/runs?

Se não houver snapshot local no corte de 20:04:39, o script NÃO extrapola.
Ele:
1. identifica o primeiro snapshot nacional local posterior ao corte;
2. mede a lacuna temporal e de votos entre 20:04:39 e esse snapshot;
3. reconstrói por UF apenas a cauda realmente preservada localmente;
4. compara a soma dos deltas das UFs com o delta nacional do mesmo intervalo;
5. grava explicitamente se a reconstrução completa do pool é possível ou não.

Saídas
======
  data/forensics/analysis/phase4i_local_tail_by_uf.csv
  data/forensics/analysis/phase4i_summary.json
"""

import csv
import json
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path("data/forensics")
RUNS = ROOT / "runs"
OUT = ROOT / "analysis"
PHASE4G = OUT / "phase4g_summary.json"

TARGET_BRT = datetime(2026, 10, 4, 20, 4, 39)
LULA = "13"
FLAVIO = "22"


def n(v):
    try:
        return int(str(v or 0).replace(".", ""))
    except Exception:
        return 0


def p(v):
    try:
        return float(str(v or 0).replace(",", "."))
    except Exception:
        return 0.0


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


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
    s, v, e = d.get("s", {}), d.get("v", {}), d.get("e", {})
    return {
        "cand": cand,
        "vv": n(v.get("vv")),
        "st": n(s.get("st")),
        "ts": n(s.get("ts")),
        "comparecimento": n(e.get("c")),
        "dt": d.get("dt") or d.get("dg") or "",
        "ht": d.get("ht") or d.get("hg") or "",
    }


def parse_brt(dt, ht):
    if not dt or not ht:
        return None
    text = f"{dt} {ht}"
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    return None


def pct(v, total):
    return 100.0 * v / total if total else None


def load_runs():
    rows = []
    for run_dir in sorted(p for p in RUNS.glob("*") if p.is_dir()):
        br_path = run_dir / "live" / "br.json"
        if not br_path.exists():
            continue
        br = parse_result(br_path)
        generated = parse_brt(br["dt"], br["ht"])
        if generated is None:
            continue
        rows.append({"run_dir": run_dir, "name": run_dir.name, "br": br, "generated": generated})
    return rows


def load_ufs(run_dir):
    out = {}
    for path in sorted((run_dir / "live" / "uf").glob("*.json")):
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
        tmp.replace(path)
    finally:
        if tmp.exists():
            tmp.unlink()


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    if not PHASE4G.exists():
        raise SystemExit("Falta data/forensics/analysis/phase4g_summary.json")

    g = read_json(PHASE4G)
    target_pool = int(g["remaining_pool"]["valid_votes"])
    target_lula = int(g["remaining_pool"]["lula_votes"])
    target_flavio = int(g["remaining_pool"]["flavio_votes"])

    runs = load_runs()
    if not runs:
        raise SystemExit("Nenhum snapshot local utilizável em data/forensics/runs")

    before_or_at = [r for r in runs if r["generated"] <= TARGET_BRT]
    after = [r for r in runs if r["generated"] > TARGET_BRT]

    exact_start_available = bool(before_or_at)
    if before_or_at:
        start = max(before_or_at, key=lambda r: r["generated"])
        start_relation = "latest_at_or_before_target"
    else:
        if not after:
            raise SystemExit("Não há snapshot local no ou após o corte 20:04:39.")
        start = min(after, key=lambda r: r["generated"])
        start_relation = "earliest_after_target"

    final = max(runs, key=lambda r: (r["br"]["st"], r["generated"]))

    if final["generated"] < start["generated"]:
        raise SystemExit("Snapshot final anterior ao snapshot inicial selecionado.")

    b0, b1 = start["br"], final["br"]
    delta_br_vv = b1["vv"] - b0["vv"]
    delta_br_lula = b1["cand"].get(LULA, 0) - b0["cand"].get(LULA, 0)
    delta_br_flavio = b1["cand"].get(FLAVIO, 0) - b0["cand"].get(FLAVIO, 0)
    delta_br_sections = b1["st"] - b0["st"]

    u0 = load_ufs(start["run_dir"])
    u1 = load_ufs(final["run_dir"])
    common = sorted(set(u0) & set(u1))

    rows = []
    for uf in common:
        a, b = u0[uf], u1[uf]
        dvv = b["vv"] - a["vv"]
        dl = b["cand"].get(LULA, 0) - a["cand"].get(LULA, 0)
        df = b["cand"].get(FLAVIO, 0) - a["cand"].get(FLAVIO, 0)
        rows.append({
            "uf": uf,
            "start_sections": a["st"],
            "final_sections": b["st"],
            "d_sections": b["st"] - a["st"],
            "d_valid_votes": dvv,
            "d_lula": dl,
            "d_flavio": df,
            "lula_share_tail_pct": pct(dl, dvv),
            "flavio_share_tail_pct": pct(df, dvv),
            "lula_minus_flavio_tail_pp": (
                pct(dl, dvv) - pct(df, dvv) if dvv else None
            ),
        })

    sum_uf_vv = sum(r["d_valid_votes"] for r in rows)
    sum_uf_lula = sum(r["d_lula"] for r in rows)
    sum_uf_flavio = sum(r["d_flavio"] for r in rows)
    sum_uf_sections = sum(r["d_sections"] for r in rows)

    gap_minutes = (start["generated"] - TARGET_BRT).total_seconds() / 60.0
    covered_fraction = delta_br_vv / target_pool if target_pool else None
    missing_target_vv = target_pool - delta_br_vv
    missing_target_lula = target_lula - delta_br_lula
    missing_target_flavio = target_flavio - delta_br_flavio

    complete_pool_reconstructable = (
        start["generated"] == TARGET_BRT
        and len(common) == 28
        and sum_uf_vv == delta_br_vv
        and sum_uf_lula == delta_br_lula
        and sum_uf_flavio == delta_br_flavio
    )

    summary = {
        "format": "tse-forensics-phase4i-local-tail-coverage-v1",
        "target": {
            "cutoff_brt": TARGET_BRT.strftime("%Y-%m-%d %H:%M:%S"),
            "phase4g_remaining_valid_votes": target_pool,
            "phase4g_remaining_lula_votes": target_lula,
            "phase4g_remaining_flavio_votes": target_flavio,
        },
        "local_coverage": {
            "local_runs": len(runs),
            "exact_snapshot_at_or_before_target_available": exact_start_available,
            "selected_start_relation": start_relation,
            "selected_start_run": start["name"],
            "selected_start_generated_brt": start["generated"].strftime("%Y-%m-%d %H:%M:%S"),
            "final_run": final["name"],
            "final_generated_brt": final["generated"].strftime("%Y-%m-%d %H:%M:%S"),
            "gap_target_to_selected_start_minutes": gap_minutes,
            "target_pool_covered_by_local_tail_fraction": covered_fraction,
            "target_pool_covered_by_local_tail_pct": (
                100.0 * covered_fraction if covered_fraction is not None else None
            ),
        },
        "national_local_tail": {
            "d_sections": delta_br_sections,
            "d_valid_votes": delta_br_vv,
            "d_lula": delta_br_lula,
            "d_flavio": delta_br_flavio,
            "lula_share_pct": pct(delta_br_lula, delta_br_vv),
            "flavio_share_pct": pct(delta_br_flavio, delta_br_vv),
            "lula_minus_flavio_margin_pp": (
                pct(delta_br_lula, delta_br_vv) - pct(delta_br_flavio, delta_br_vv)
                if delta_br_vv else None
            ),
        },
        "uf_reconciliation": {
            "ufs_common": len(common),
            "sum_d_sections": sum_uf_sections,
            "sum_d_valid_votes": sum_uf_vv,
            "sum_d_lula": sum_uf_lula,
            "sum_d_flavio": sum_uf_flavio,
            "br_minus_sum_ufs_valid_votes": delta_br_vv - sum_uf_vv,
            "br_minus_sum_ufs_lula": delta_br_lula - sum_uf_lula,
            "br_minus_sum_ufs_flavio": delta_br_flavio - sum_uf_flavio,
            "note": (
                "Snapshots locais não são atômicos: arquivos BR e UF foram capturados "
                "ao longo de uma janela de minutos. Pequena diferença não implica "
                "discrepância eleitoral."
            ),
        },
        "uncovered_target_segment": {
            "valid_votes": missing_target_vv,
            "lula_votes_if_using_national_identity_only": missing_target_lula,
            "flavio_votes_if_using_national_identity_only": missing_target_flavio,
            "warning": (
                "Esses votos são uma diferença nacional aritmética. Sem versões "
                "geográficas preservadas no corte, não podem ser atribuídos de forma "
                "determinística a UFs/municípios/zonas."
            ),
        },
        "complete_post_2004_geographic_reconstruction_possible_from_local_snapshots": (
            complete_pool_reconstructable
        ),
        "next_required_evidence": (
            "Histórico de versões por UF/município/zona cobrindo 20:04:39 "
            "(por exemplo, banco bruto do coletor contemporâneo ou fonte temporal equivalente)."
        ),
    }

    fields = [
        "uf","start_sections","final_sections","d_sections","d_valid_votes",
        "d_lula","d_flavio","lula_share_tail_pct","flavio_share_tail_pct",
        "lula_minus_flavio_tail_pp",
    ]
    write_csv_atomic(OUT / "phase4i_local_tail_by_uf.csv", rows, fields)
    (OUT / "phase4i_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\nFASE 4I — cobertura local do pool pós-20:04")
    print(f"- snapshots locais utilizáveis: {len(runs)}")
    print(
        f"- primeiro snapshot selecionado: {start['generated']:%H:%M:%S} BRT "
        f"({start['name']})"
    )
    print(f"- lacuna após 20:04:39: {gap_minutes:.2f} min")
    print(
        f"- cauda local: {delta_br_vv:,} válidos · "
        f"{100.0 * covered_fraction:.2f}% do pool de {target_pool:,}"
    )
    print(
        f"- cauda local Lula={pct(delta_br_lula, delta_br_vv):.2f}% · "
        f"Flávio={pct(delta_br_flavio, delta_br_vv):.2f}%"
    )
    print(
        f"- reconciliação UF: BR-somaUF válidos={delta_br_vv - sum_uf_vv:+,} · "
        f"Lula={delta_br_lula - sum_uf_lula:+,} · "
        f"Flávio={delta_br_flavio - sum_uf_flavio:+,}"
    )
    print(
        "- reconstrução geográfica completa 20:04→final com snapshots locais: "
        f"{complete_pool_reconstructable}"
    )
    print(f"- CSV: {OUT / 'phase4i_local_tail_by_uf.csv'}")
    print(f"- resumo: {OUT / 'phase4i_summary.json'}")


if __name__ == "__main__":
    main()
