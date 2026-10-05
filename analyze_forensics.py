#!/usr/bin/env python3
"""Fase 1 da auditoria: reconciliação dos JSONs EA20 já coletados.

Não exige BU por seção. Usa somente os snapshots locais em data/forensics/runs.

Testes:
1) fechamento interno: soma dos candidatos == votos válidos;
2) Brasil == soma das UFs (incluindo ZZ, quando presente);
3) em snapshot final: UF == soma dos municípios, quando há cobertura municipal;
4) mede a janela real de coleta de cada snapshot pelo manifest, para não confundir
   defasagem de aquisição com discrepância eleitoral.

Saídas:
  data/forensics/analysis/phase1_summary.json
  data/forensics/analysis/snapshots.csv
  data/forensics/analysis/municipality_reconciliation.csv
  data/forensics/analysis/accounting_errors.csv
"""

import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path("data/forensics")
RUNS = ROOT / "runs"
OUT = ROOT / "analysis"


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
                    num = str(c.get("n", ""))
                    cand[num] = n(c.get("vap"))
    s, v, e = d.get("s", {}), d.get("v", {}), d.get("e", {})
    return {
        "path": str(path),
        "cand": cand,
        "vv": n(v.get("vv")),
        "vb": n(v.get("vb")),
        "vn": n(v.get("tvn") or v.get("vn")),
        "tv": n(v.get("tv")),
        "comparecimento": n(e.get("c")),
        "eleitorado": n(e.get("te")),
        "abstencao": n(e.get("a")),
        "st": n(s.get("st")),
        "ts": n(s.get("ts")),
        "pst": p(s.get("pstn") or s.get("pst")),
        "dt": d.get("dt") or d.get("dg") or "",
        "ht": d.get("ht") or d.get("hg") or "",
    }


def add_results(items):
    out = {
        "cand": defaultdict(int), "vv": 0, "vb": 0, "vn": 0, "tv": 0,
        "comparecimento": 0, "eleitorado": 0, "abstencao": 0, "st": 0, "ts": 0,
    }
    for x in items:
        for num, votes in x["cand"].items():
            out["cand"][num] += votes
        for key in ("vv", "vb", "vn", "tv", "comparecimento", "eleitorado", "abstencao", "st", "ts"):
            out[key] += x[key]
    out["cand"] = dict(out["cand"])
    return out


def candidate_diff(a, b):
    nums = sorted(set(a) | set(b), key=lambda x: int(x) if x.isdigit() else x)
    return {num: a.get(num, 0) - b.get(num, 0) for num in nums}


def manifest_spread(run_dir):
    path = run_dir / "manifest.jsonl"
    if not path.exists():
        return None, None, None
    times = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except Exception:
            continue
        if row.get("kind") not in ("national", "state", "municipality"):
            continue
        ts = row.get("captured_at_utc")
        if not ts:
            continue
        try:
            times.append(datetime.fromisoformat(ts.replace("Z", "+00:00")))
        except Exception:
            pass
    if not times:
        return None, None, None
    lo, hi = min(times), max(times)
    return lo.isoformat(), hi.isoformat(), (hi - lo).total_seconds()


def accounting_check(scope, key, x, errors):
    cand_sum = sum(x["cand"].values())
    if cand_sum != x["vv"]:
        errors.append({
            "scope": scope,
            "key": key,
            "path": x["path"],
            "test": "sum_candidates_eq_valid_votes",
            "expected": x["vv"],
            "observed": cand_sum,
            "difference": cand_sum - x["vv"],
        })
    if x["comparecimento"] and (x["vv"] or x["vb"] or x["vn"]):
        vote_components = x["vv"] + x["vb"] + x["vn"]
        if vote_components != x["comparecimento"]:
            errors.append({
                "scope": scope,
                "key": key,
                "path": x["path"],
                "test": "valid_blank_null_eq_turnout",
                "expected": x["comparecimento"],
                "observed": vote_components,
                "difference": vote_components - x["comparecimento"],
            })


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    run_dirs = sorted([p for p in RUNS.glob("*") if p.is_dir()])
    if not run_dirs:
        raise SystemExit("Nenhum snapshot encontrado em data/forensics/runs")

    snapshot_rows = []
    muni_rows = []
    uf_candidate_rows = []
    municipality_completion_rows = []
    accounting_errors = []
    candidate_diffs = {}

    for run_dir in run_dirs:
        br_path = run_dir / "live" / "br.json"
        if not br_path.exists():
            continue
        br = parse_result(br_path)
        accounting_check("BR", run_dir.name, br, accounting_errors)

        state_paths = sorted((run_dir / "live" / "uf").glob("*.json"))
        states = []
        for path in state_paths:
            x = parse_result(path)
            states.append(x)
            accounting_check("UF", path.stem.upper(), x, accounting_errors)

        state_sum = add_results(states)
        diff = candidate_diff(br["cand"], state_sum["cand"])
        candidate_diffs[run_dir.name] = diff
        cap_start, cap_end, cap_spread = manifest_spread(run_dir)

        snapshot_rows.append({
            "snapshot": run_dir.name,
            "dt": br["dt"],
            "ht": br["ht"],
            "pst_br": br["pst"],
            "states_found": len(states),
            "br_sections": br["st"],
            "sum_uf_sections": state_sum["st"],
            "diff_sections": br["st"] - state_sum["st"],
            "br_valid_votes": br["vv"],
            "sum_uf_valid_votes": state_sum["vv"],
            "diff_valid_votes": br["vv"] - state_sum["vv"],
            "max_candidate_abs_diff": max((abs(v) for v in diff.values()), default=0),
            "capture_start_utc": cap_start or "",
            "capture_end_utc": cap_end or "",
            "capture_spread_seconds": cap_spread if cap_spread is not None else "",
        })

    # Reconcilia UF x municípios somente no snapshot mais recente.
    latest = run_dirs[-1]
    state_by_uf = {}
    for path in sorted((latest / "live" / "uf").glob("*.json")):
        state_by_uf[path.stem.lower()] = parse_result(path)

    city_root = latest / "live" / "municipio"
    for uf, state in sorted(state_by_uf.items()):
        city_paths = sorted((city_root / uf).glob("*.json"))
        if not city_paths:
            muni_rows.append({
                "snapshot": latest.name, "uf": uf.upper(), "municipalities": 0,
                "uf_sections": state["st"], "sum_municipal_sections": "", "diff_sections": "",
                "uf_total_sections": state["ts"], "sum_municipal_total_sections": "", "diff_total_sections": "",
                "incomplete_municipalities": "",
                "uf_valid_votes": state["vv"], "sum_municipal_valid_votes": "", "diff_valid_votes": "",
                "uf_blank_votes": state["vb"], "sum_municipal_blank_votes": "", "diff_blank_votes": "",
                "uf_null_votes": state["vn"], "sum_municipal_null_votes": "", "diff_null_votes": "",
                "uf_turnout": state["comparecimento"], "sum_municipal_turnout": "", "diff_turnout": "",
                "max_candidate_abs_diff": "", "status": "sem_cobertura_municipal",
            })
            continue
        cities = [parse_result(pth) for pth in city_paths]
        for path, x in zip(city_paths, cities):
            accounting_check("MUNICIPIO", f"{uf.upper()}:{path.stem}", x, accounting_errors)
            if x["st"] != x["ts"] or x["pst"] < 100:
                municipality_completion_rows.append({
                    "snapshot": latest.name,
                    "uf": uf.upper(),
                    "municipality_code": path.stem,
                    "st": x["st"],
                    "ts": x["ts"],
                    "missing_sections": x["ts"] - x["st"],
                    "pst": x["pst"],
                    "dt": x["dt"],
                    "ht": x["ht"],
                    "path": x["path"],
                })
        city_sum = add_results(cities)
        diff = candidate_diff(state["cand"], city_sum["cand"])
        status = "ok" if state["vv"] == city_sum["vv"] and all(v == 0 for v in diff.values()) else "divergencia"
        muni_rows.append({
            "snapshot": latest.name,
            "uf": uf.upper(),
            "municipalities": len(cities),
            "uf_sections": state["st"],
            "sum_municipal_sections": city_sum["st"],
            "diff_sections": state["st"] - city_sum["st"],
            "uf_total_sections": state["ts"],
            "sum_municipal_total_sections": city_sum["ts"],
            "diff_total_sections": state["ts"] - city_sum["ts"],
            "incomplete_municipalities": sum(1 for x in cities if x["st"] != x["ts"] or x["pst"] < 100),
            "uf_valid_votes": state["vv"],
            "sum_municipal_valid_votes": city_sum["vv"],
            "diff_valid_votes": state["vv"] - city_sum["vv"],
            "uf_blank_votes": state["vb"],
            "sum_municipal_blank_votes": city_sum["vb"],
            "diff_blank_votes": state["vb"] - city_sum["vb"],
            "uf_null_votes": state["vn"],
            "sum_municipal_null_votes": city_sum["vn"],
            "diff_null_votes": state["vn"] - city_sum["vn"],
            "uf_turnout": state["comparecimento"],
            "sum_municipal_turnout": city_sum["comparecimento"],
            "diff_turnout": state["comparecimento"] - city_sum["comparecimento"],
            "max_candidate_abs_diff": max((abs(v) for v in diff.values()), default=0),
            "status": status,
        })
        for num in sorted(set(state["cand"]) | set(city_sum["cand"]), key=lambda x: int(x) if x.isdigit() else x):
            uf_candidate_rows.append({
                "snapshot": latest.name,
                "uf": uf.upper(),
                "candidate": num,
                "uf_votes": state["cand"].get(num, 0),
                "sum_municipal_votes": city_sum["cand"].get(num, 0),
                "difference": state["cand"].get(num, 0) - city_sum["cand"].get(num, 0),
                "uf_status": status,
            })

    snapshot_fields = [
        "snapshot","dt","ht","pst_br","states_found","br_sections","sum_uf_sections",
        "diff_sections","br_valid_votes","sum_uf_valid_votes","diff_valid_votes",
        "max_candidate_abs_diff","capture_start_utc","capture_end_utc","capture_spread_seconds"
    ]
    muni_fields = [
        "snapshot","uf","municipalities","uf_sections","sum_municipal_sections","diff_sections",
        "uf_total_sections","sum_municipal_total_sections","diff_total_sections","incomplete_municipalities",
        "uf_valid_votes","sum_municipal_valid_votes","diff_valid_votes",
        "uf_blank_votes","sum_municipal_blank_votes","diff_blank_votes",
        "uf_null_votes","sum_municipal_null_votes","diff_null_votes",
        "uf_turnout","sum_municipal_turnout","diff_turnout",
        "max_candidate_abs_diff","status"
    ]
    uf_candidate_fields = [
        "snapshot","uf","candidate","uf_votes","sum_municipal_votes","difference","uf_status"
    ]
    municipality_completion_fields = [
        "snapshot","uf","municipality_code","st","ts","missing_sections","pst","dt","ht","path"
    ]
    error_fields = ["scope","key","path","test","expected","observed","difference"]

    write_csv(OUT / "snapshots.csv", snapshot_rows, snapshot_fields)
    write_csv(OUT / "municipality_reconciliation.csv", muni_rows, muni_fields)
    write_csv(OUT / "uf_candidate_reconciliation.csv", uf_candidate_rows, uf_candidate_fields)
    write_csv(OUT / "municipality_completion_anomalies.csv", municipality_completion_rows, municipality_completion_fields)
    write_csv(OUT / "accounting_errors.csv", accounting_errors, error_fields)

    summary = {
        "format": "tse-forensics-phase1-v1",
        "snapshots_analyzed": len(snapshot_rows),
        "latest_snapshot": latest.name,
        "latest_br_vs_uf": snapshot_rows[-1] if snapshot_rows else None,
        "uf_municipality_divergences": [x for x in muni_rows if x["status"] == "divergencia"],
        "uf_candidate_differences": [
            x for x in uf_candidate_rows
            if x["uf_status"] == "divergencia" and x["difference"] != 0
        ],
        "municipality_completion_anomalies": municipality_completion_rows,
        "accounting_error_count": len(accounting_errors),
        "candidate_differences_by_snapshot": candidate_diffs,
        "limitations": [
            "Snapshots live não são necessariamente atômicos: nacional, UFs e municípios foram baixados em instantes diferentes. capture_spread_seconds mede essa janela.",
            "Sem BU/votação por seção ainda não é possível fazer a reconciliação urna por urna nem comparar o mesmo conjunto de seções entre cargos.",
            "O snapshot final a 100% é o melhor teste disponível agora para reconciliação BR↔UF↔município, pois a totalização já estava estabilizada.",
        ],
    }
    (OUT / "phase1_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("\nFASE 1 — reconciliação dos JSONs coletados")
    print(f"- snapshots analisados: {len(snapshot_rows)}")
    if snapshot_rows:
        last = snapshot_rows[-1]
        print(f"- snapshot final: {last['snapshot']} · {last['pst_br']:.2f}%")
        print(f"- BR - soma UFs (votos válidos): {last['diff_valid_votes']:+d}")
        print(f"- maior diferença por candidato BR - soma UFs: {last['max_candidate_abs_diff']}")
    divergent = [x for x in muni_rows if x["status"] == "divergencia"]
    print(f"- UFs com divergência UF x soma municípios: {len(divergent)}")
    print(f"- falhas de fechamento contábil encontradas: {len(accounting_errors)}")
    print(f"- relatório: {OUT / 'phase1_summary.json'}")
    print(f"- CSV snapshots: {OUT / 'snapshots.csv'}")
    print(f"- CSV UF x municípios: {OUT / 'municipality_reconciliation.csv'}")
    print(f"- municípios ainda não 100% no snapshot: {len(municipality_completion_rows)}")
    print(f"- CSV diferenças por candidato: {OUT / 'uf_candidate_reconciliation.csv'}")
    print(f"- CSV municípios incompletos: {OUT / 'municipality_completion_anomalies.csv'}")
    print(f"- CSV fechamento: {OUT / 'accounting_errors.csv'}")


if __name__ == "__main__":
    main()
