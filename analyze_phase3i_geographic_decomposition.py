#!/usr/bin/env python3
"""Fase 3I — decomposição geográfica exata do movimento final F x Lula.

Objetivo:
Quantificar, por UF, quanto da redução posterior da margem Flávio−Lula veio
de cada estado e comparar isso com a projeção "se o restante da UF mantivesse
a mesma composição observada naquele snapshot".

Fontes:
- snapshots contemporâneos de vitoropereira/eleicoes2026 (19:06, 19:32, 20:47);
- resultado final oficial do TSE por UF e nacional.

Importante:
- nos snapshots, marg = round((Flavio_votes - Lula_votes) / 1000), portanto
  a margem histórica por UF tem erro máximo de arredondamento de ~500 votos;
- rem_net é uma PROJEÇÃO do coletor:
    rem * (share_F - share_L)
  com rem = vv / (pst/100) - vv.
  Não é voto observado;
- o resultado final oficial é usado apenas como destino da trajetória.

Saídas:
  data/forensics/analysis/phase3i_uf_final_decomposition.csv
  data/forensics/analysis/phase3i_snapshots.csv
  data/forensics/analysis/phase3i_summary.json
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
UA = "TSE-forensics-phase3i/1.0"

VITOR_COMMIT = "10c03a7d52058a2650836953b612939ba02a3235"
SNAPSHOTS = [
    ("s1906", "snapshots/2026-10-04_1906_64.8pct/dados.json", "19:06"),
    ("s1932", "snapshots/2026-10-04_1932_84.9pct/dados.json", "19:32"),
    ("s2047", "snapshots/2026-10-04_2047_93.2pct/dados.json", "20:47"),
]

TSE_BASE = "https://resultados.tse.jus.br/oficial/ele2026/6257/dados"
ELECTION_CODE = "006257"
OFFICE_CODE = "0001"
UFS = (
    "ac","al","am","ap","ba","ce","df","es","go","ma","mg","ms","mt","pa",
    "pb","pe","pi","pr","rj","rn","ro","rr","rs","sc","se","sp","to","zz"
)


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
                        total += int(cand.get("vap", 0) or 0)
                        found = True
    if not found:
        raise RuntimeError(f"Candidato {number} não encontrado.")
    return total


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

    source_meta = []
    snapshots = {}
    for key, relpath, label in SNAPSHOTS:
        url = (
            "https://raw.githubusercontent.com/vitoropereira/eleicoes2026/"
            f"{VITOR_COMMIT}/{relpath}"
        )
        obj, meta = fetch_json(
            url,
            RAW / "vitoropereira-eleicoes2026" / VITOR_COMMIT / f"{key}.json",
        )
        meta["label"] = label
        source_meta.append(meta)
        snapshots[key] = obj

    finals = {}
    for uf in UFS:
        url = (
            f"{TSE_BASE}/{uf}/"
            f"{uf}-c{OFFICE_CODE}-e{ELECTION_CODE}-u.json"
        )
        obj, meta = fetch_json(
            url,
            RAW / "tse-final" / "uf" / f"{uf}.json",
        )
        f_votes = candidate_votes(obj, "22")
        l_votes = candidate_votes(obj, "13")
        finals[uf.upper()] = {
            "flavio": f_votes,
            "lula": l_votes,
            "margin": f_votes - l_votes,
        }
        meta["scope"] = uf.upper()
        source_meta.append(meta)

    br_url = (
        f"{TSE_BASE}/br/"
        f"br-c{OFFICE_CODE}-e{ELECTION_CODE}-u.json"
    )
    br_obj, br_meta = fetch_json(
        br_url,
        RAW / "tse-final" / "br.json",
    )
    br_f = candidate_votes(br_obj, "22")
    br_l = candidate_votes(br_obj, "13")
    br_margin = br_f - br_l
    br_meta["scope"] = "BR"
    source_meta.append(br_meta)

    sum_uf_margin = sum(x["margin"] for x in finals.values())
    if sum_uf_margin != br_margin:
        raise RuntimeError(
            f"Final não fecha: soma UFs={sum_uf_margin}, BR={br_margin}"
        )

    uf_rows = []
    snap_rows = []

    for key, _, label in SNAPSHOTS:
        snap = snapshots[key]
        state_map = {x["uf"]: x for x in snap.get("states", [])}

        approx_current_sum = 0
        projected_remaining_sum = 0

        groups = {
            "Lula": {
                "actual_remaining_net": 0,
                "projected_remaining_net": 0,
                "projected_remaining_valid": 0,
                "n": 0,
            },
            "Flavio": {
                "actual_remaining_net": 0,
                "projected_remaining_net": 0,
                "projected_remaining_valid": 0,
                "n": 0,
            },
            "Empate": {
                "actual_remaining_net": 0,
                "projected_remaining_net": 0,
                "projected_remaining_valid": 0,
                "n": 0,
            },
        }

        for uf, final in sorted(finals.items()):
            st = state_map.get(uf)
            if st is None:
                raise RuntimeError(f"{key}: UF {uf} ausente no snapshot.")

            historical_margin_approx = int(st.get("marg", 0)) * 1000
            projected_remaining_net = int(st.get("rem_net", 0)) * 1000
            projected_remaining_valid = int(st.get("rem", 0)) * 1000
            actual_remaining_net = final["margin"] - historical_margin_approx
            projection_error = actual_remaining_net - projected_remaining_net

            f_pct = float(st.get("f", 0))
            l_pct = float(st.get("l", 0))
            leader = (
                "Lula" if l_pct > f_pct
                else "Flavio" if f_pct > l_pct
                else "Empate"
            )

            approx_current_sum += historical_margin_approx
            projected_remaining_sum += projected_remaining_net

            g = groups[leader]
            g["actual_remaining_net"] += actual_remaining_net
            g["projected_remaining_net"] += projected_remaining_net
            g["projected_remaining_valid"] += projected_remaining_valid
            g["n"] += 1

            uf_rows.append({
                "snapshot": key,
                "snapshot_label": label,
                "uf": uf,
                "pst": st.get("pst"),
                "flavio_pct": f_pct,
                "lula_pct": l_pct,
                "leader": leader,
                "historical_margin_flavio_minus_lula_approx": historical_margin_approx,
                "projected_remaining_net_flavio_minus_lula": projected_remaining_net,
                "projected_remaining_valid_votes": projected_remaining_valid,
                "final_margin_flavio_minus_lula_exact": final["margin"],
                "actual_remaining_net_to_final_approx": actual_remaining_net,
                "projection_error_actual_minus_projected": projection_error,
            })

        national_current_exact = int(snap["fv"]) - int(snap["lv"])
        current_rounding_gap = approx_current_sum - national_current_exact

        projected_final_margin = national_current_exact + projected_remaining_sum
        actual_remaining_national = br_margin - national_current_exact
        projection_error_final = br_margin - projected_final_margin

        explanation_fraction = (
            abs(projected_remaining_sum) / abs(actual_remaining_national)
            if actual_remaining_national != 0
            and projected_remaining_sum * actual_remaining_national > 0
            else None
        )

        snap_rows.append({
            "snapshot": key,
            "snapshot_label": label,
            "pst_national": snap.get("pst"),
            "national_margin_current_exact": national_current_exact,
            "sum_uf_historical_margin_approx": approx_current_sum,
            "rounding_gap_uf_approx_minus_national": current_rounding_gap,
            "projected_remaining_net_all_ufs": projected_remaining_sum,
            "actual_remaining_net_to_final": actual_remaining_national,
            "projected_final_margin": projected_final_margin,
            "actual_final_margin": br_margin,
            "projection_error_final_actual_minus_projected": projection_error_final,
            "same_share_projection_fraction_of_actual_remaining_abs": explanation_fraction,
            "lula_led_actual_remaining_net": groups["Lula"]["actual_remaining_net"],
            "lula_led_projected_remaining_net": groups["Lula"]["projected_remaining_net"],
            "lula_led_projected_remaining_valid": groups["Lula"]["projected_remaining_valid"],
            "flavio_led_actual_remaining_net": groups["Flavio"]["actual_remaining_net"],
            "flavio_led_projected_remaining_net": groups["Flavio"]["projected_remaining_net"],
            "flavio_led_projected_remaining_valid": groups["Flavio"]["projected_remaining_valid"],
        })

    write_csv_atomic(
        OUT / "phase3i_uf_final_decomposition.csv",
        uf_rows,
        [
            "snapshot","snapshot_label","uf","pst","flavio_pct","lula_pct","leader",
            "historical_margin_flavio_minus_lula_approx",
            "projected_remaining_net_flavio_minus_lula",
            "projected_remaining_valid_votes",
            "final_margin_flavio_minus_lula_exact",
            "actual_remaining_net_to_final_approx",
            "projection_error_actual_minus_projected",
        ],
    )

    write_csv_atomic(
        OUT / "phase3i_snapshots.csv",
        snap_rows,
        [
            "snapshot","snapshot_label","pst_national",
            "national_margin_current_exact","sum_uf_historical_margin_approx",
            "rounding_gap_uf_approx_minus_national",
            "projected_remaining_net_all_ufs","actual_remaining_net_to_final",
            "projected_final_margin","actual_final_margin",
            "projection_error_final_actual_minus_projected",
            "same_share_projection_fraction_of_actual_remaining_abs",
            "lula_led_actual_remaining_net","lula_led_projected_remaining_net",
            "lula_led_projected_remaining_valid",
            "flavio_led_actual_remaining_net","flavio_led_projected_remaining_net",
            "flavio_led_projected_remaining_valid",
        ],
    )

    summary = {
        "format": "tse-forensics-phase3i-geographic-decomposition-v1",
        "sources": source_meta,
        "final": {
            "flavio_votes": br_f,
            "lula_votes": br_l,
            "margin_flavio_minus_lula": br_margin,
            "sum_uf_margin": sum_uf_margin,
            "reconciliation_difference": sum_uf_margin - br_margin,
        },
        "snapshots": snap_rows,
        "largest_actual_lula_favoring_remaining_by_snapshot": {},
        "largest_actual_flavio_favoring_remaining_by_snapshot": {},
        "interpretation_rules": [
            (
                "actual_remaining_net_to_final < 0 significa que, daquele snapshot "
                "até o final, a UF contribuiu para reduzir a margem de Flávio em "
                "relação a Lula."
            ),
            (
                "projected_remaining_net usa a composição da própria UF naquele "
                "snapshot; não é voto observado."
            ),
            (
                "Se o sinal projetado e o real coincidirem, a composição geográfica "
                "já apontava para o sentido do movimento; a diferença de magnitude "
                "mede o quanto o voto tardio dentro das UFs se afastou da composição "
                "já observada."
            ),
            (
                "A margem histórica por UF é arredondada ao milhar na fonte; por isso "
                "a decomposição por UF é aproximada em até ~500 votos por UF, enquanto "
                "a margem nacional histórica é exata."
            ),
        ],
    }

    for key, _, _ in SNAPSHOTS:
        subset = [r for r in uf_rows if r["snapshot"] == key]
        summary["largest_actual_lula_favoring_remaining_by_snapshot"][key] = sorted(
            subset,
            key=lambda r: r["actual_remaining_net_to_final_approx"],
        )[:10]
        summary["largest_actual_flavio_favoring_remaining_by_snapshot"][key] = sorted(
            subset,
            key=lambda r: r["actual_remaining_net_to_final_approx"],
            reverse=True,
        )[:10]

    atomic_write(
        OUT / "phase3i_summary.json",
        json.dumps(summary, ensure_ascii=False, indent=2).encode("utf-8"),
    )

    print("\\nFASE 3I — decomposição geográfica do movimento até o final")
    print(
        f"- final oficial: Flávio={br_f:,} · Lula={br_l:,} · "
        f"margem={br_margin:+,}"
    )
    print(f"- reconciliação final BR vs soma UFs: {sum_uf_margin - br_margin:+d}")
    for r in snap_rows:
        frac = r["same_share_projection_fraction_of_actual_remaining_abs"]
        frac_txt = f"{100*frac:.1f}%" if frac is not None else "n/a"
        print(
            f"- {r['snapshot_label']}: margem={r['national_margin_current_exact']:+,} · "
            f"movimento real até final={r['actual_remaining_net_to_final']:+,} · "
            f"projeção mesma-share={r['projected_remaining_net_all_ufs']:+,} · "
            f"|projeção|/|real|={frac_txt}"
        )
    print(f"- UFs: {OUT / 'phase3i_uf_final_decomposition.csv'}")
    print(f"- snapshots: {OUT / 'phase3i_snapshots.csv'}")
    print(f"- resumo: {OUT / 'phase3i_summary.json'}")


if __name__ == "__main__":
    main()
