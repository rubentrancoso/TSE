#!/usr/bin/env python3
"""Fase 2: localizar as seções que explicam divergências UF x municípios.

Usa a configuração oficial EA16 do pleito 3220 e, quando necessário,
arquivos EA20 por zona e EA18 por seção. Preserva os JSONs brutos localmente
(com SHA-256 no resumo), mas versiona apenas os relatórios derivados em
data/forensics/analysis/.

Não conclui causa política ou fraude; apenas localiza a diferença de
abrangência/totalização de forma reproduzível.
"""

import csv
import hashlib
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

RESULTS_BASE = "https://resultados.tse.jus.br/oficial/ele2026"
ELECTION_ID = "6257"
ELECTION_CODE = "006257"
OFFICE_CODE = "0001"
PLEITO = "3220"
PLEITO_CODE = "003220"
TARGET_UFS = ("ba", "mg")
USER_AGENT = "TSE-forensics-phase2/1.0"

ROOT = Path("data/forensics")
RUNS = ROOT / "runs"
RAW = ROOT / "section-config"
OUT = ROOT / "analysis"


def iso_utc():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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
        return json.loads(data.decode("utf-8-sig")), {
            "url": url, "path": str(path), "sha256": sha256(data), "reused": True
        }
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Cache-Control": "no-cache"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    obj = json.loads(data.decode("utf-8-sig"))
    atomic_write(path, data)
    return obj, {
        "url": url, "path": str(path), "sha256": sha256(data), "reused": False
    }


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


def result_meta(path):
    d = json.loads(path.read_text(encoding="utf-8-sig"))
    s = d.get("s", {})
    return {
        "st": n(s.get("st")),
        "ts": n(s.get("ts")),
        "pst": p(s.get("pstn") or s.get("pst")),
        "dt": d.get("dt") or d.get("dg") or "",
        "ht": d.get("ht") or d.get("hg") or "",
    }


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def section_counts(sections):
    all_count = len(sections)
    principal_count = sum(1 for sec in sections if not sec.get("nsp"))
    aux_count = sum(1 for sec in sections if sec.get("da") and sec.get("ha"))
    return all_count, principal_count, aux_count


def ea16_map(data, uf):
    result = {}
    abr = next(
        (x for x in data.get("abr", []) if str(x.get("cd", "")).lower() == uf),
        None,
    )
    if abr is None and len(data.get("abr", [])) == 1:
        abr = data["abr"][0]
    if not abr:
        return result
    for mu in abr.get("mu", []):
        code = str(mu.get("cd", "")).zfill(5)
        zones = {}
        for zon in mu.get("zon", []):
            z = str(zon.get("cd", "")).zfill(4)
            zones[z] = zon.get("sec", []) or []
        result[code] = {"name": mu.get("nm", ""), "zones": zones}
    return result


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    run_dirs = sorted(p for p in RUNS.glob("*") if p.is_dir())
    if not run_dirs:
        raise SystemExit("Nenhum snapshot local encontrado.")
    latest = run_dirs[-1]

    reconciliation = []
    zone_rows = []
    section_rows = []
    raw_sources = []
    summary_ufs = {}

    for uf in TARGET_UFS:
        config_url = (
            f"{RESULTS_BASE}/arquivo-urna/{PLEITO}/config/{uf}/"
            f"{uf}-p{PLEITO_CODE}-cs.json"
        )
        config_path = RAW / "ea16" / f"{uf}-p{PLEITO_CODE}-cs.json"
        try:
            config, src = fetch_json(config_url, config_path)
        except Exception as exc:
            summary_ufs[uf.upper()] = {
                "error": str(exc),
                "ea16_url": config_url,
            }
            continue

        src["kind"] = "EA16"
        src["uf"] = uf.upper()
        raw_sources.append(src)
        cmap = ea16_map(config, uf)

        city_dir = latest / "live" / "municipio" / uf
        city_results = {}
        for path in city_dir.glob("*.json"):
            city_results[path.stem.zfill(5)] = (path, result_meta(path))

        temp = []
        for code, info in sorted(cmap.items()):
            sections = [sec for secs in info["zones"].values() for sec in secs]
            all_count, principal_count, aux_count = section_counts(sections)
            result_path, r = city_results.get(code, (None, {"st": 0, "ts": 0, "pst": 0, "dt": "", "ht": ""}))
            row = {
                "uf": uf.upper(),
                "municipality_code": code,
                "municipality_name": info["name"],
                "ea20_st": r["st"],
                "ea20_ts": r["ts"],
                "ea20_pst": r["pst"],
                "ea20_dt": r["dt"],
                "ea20_ht": r["ht"],
                "ea16_all_sections": all_count,
                "ea16_principal_sections": principal_count,
                "ea16_with_aux_timestamp": aux_count,
                "diff_all_minus_ea20_ts": all_count - r["ts"],
                "diff_principal_minus_ea20_ts": principal_count - r["ts"],
                "ea20_path": str(result_path) if result_path else "",
            }
            temp.append((row, info))

        score_all = sum(abs(row["diff_all_minus_ea20_ts"]) for row, _ in temp)
        score_principal = sum(abs(row["diff_principal_minus_ea20_ts"]) for row, _ in temp)
        model = "all" if score_all <= score_principal else "principal"

        anomalous_municipalities = []
        for row, info in temp:
            config_count = (
                row["ea16_all_sections"] if model == "all"
                else row["ea16_principal_sections"]
            )
            row["selected_model"] = model
            row["selected_config_sections"] = config_count
            row["diff_config_minus_ea20_ts"] = config_count - row["ea20_ts"]
            reconciliation.append(row)

            if row["diff_config_minus_ea20_ts"] == 0 and row["ea20_st"] == row["ea20_ts"]:
                continue

            anomalous_municipalities.append(row["municipality_code"])
            for zone, secs in sorted(info["zones"].items()):
                z_all, z_principal, z_aux = section_counts(secs)
                z_config = z_all if model == "all" else z_principal
                zone_url = (
                    f"{RESULTS_BASE}/{ELECTION_ID}/dados/{uf}/"
                    f"{uf}{row['municipality_code']}-z{zone}-c{OFFICE_CODE}-e{ELECTION_CODE}-u.json"
                )
                zone_path = RAW / "zone-ea20" / uf / row["municipality_code"] / f"{zone}.json"
                try:
                    _, zsrc = fetch_json(zone_url, zone_path)
                    zr = result_meta(zone_path)
                    zsrc.update({"kind": "EA20-zone", "uf": uf.upper(), "municipality": row["municipality_code"], "zone": zone})
                    raw_sources.append(zsrc)
                except Exception as exc:
                    zr = {"st": 0, "ts": 0, "pst": 0, "dt": "", "ht": ""}
                    zsrc = {"error": str(exc)}

                zrow = {
                    "uf": uf.upper(),
                    "municipality_code": row["municipality_code"],
                    "municipality_name": row["municipality_name"],
                    "zone": zone,
                    "selected_model": model,
                    "ea16_config_sections": z_config,
                    "ea16_all_sections": z_all,
                    "ea16_principal_sections": z_principal,
                    "ea16_with_aux_timestamp": z_aux,
                    "ea20_zone_st": zr["st"],
                    "ea20_zone_ts": zr["ts"],
                    "ea20_zone_pst": zr["pst"],
                    "diff_config_minus_zone_ts": z_config - zr["ts"],
                    "fetch_error": zsrc.get("error", ""),
                }
                zone_rows.append(zrow)

                if zrow["diff_config_minus_zone_ts"] != 0 or zr["st"] != zr["ts"]:
                    for sec in secs:
                        if model == "principal" and sec.get("nsp"):
                            continue
                        ns = str(sec.get("ns", "")).zfill(4)
                        aux_url = (
                            f"{RESULTS_BASE}/arquivo-urna/{PLEITO}/dados/{uf}/"
                            f"{row['municipality_code']}/{zone}/{ns}/"
                            f"p{PLEITO_CODE}-{uf}-m{row['municipality_code']}-z{zone}-s{ns}-aux.json"
                        )
                        aux_path = RAW / "ea18" / uf / row["municipality_code"] / zone / ns / "aux.json"
                        aux_status = ""
                        hash_count = 0
                        file_types = []
                        aux_error = ""
                        if sec.get("da") and sec.get("ha"):
                            try:
                                aux, asrc = fetch_json(aux_url, aux_path)
                                asrc.update({"kind": "EA18", "uf": uf.upper(), "municipality": row["municipality_code"], "zone": zone, "section": ns})
                                raw_sources.append(asrc)
                                aux_status = str(aux.get("st", ""))
                                hashes = aux.get("hashes", []) or []
                                hash_count = len(hashes)
                                for hh in hashes:
                                    for arq in hh.get("arq", []) or []:
                                        tp = str(arq.get("tp", ""))
                                        if tp and tp not in file_types:
                                            file_types.append(tp)
                            except Exception as exc:
                                aux_error = str(exc)

                        section_rows.append({
                            "uf": uf.upper(),
                            "municipality_code": row["municipality_code"],
                            "municipality_name": row["municipality_name"],
                            "zone": zone,
                            "section": ns,
                            "is_aggregated": bool(sec.get("nsp")),
                            "principal_section": str(sec.get("nsp", "")),
                            "aggregated_sections": ",".join(str(x) for x in (sec.get("nsa") or [])),
                            "ea16_aux_date": sec.get("da", ""),
                            "ea16_aux_time": sec.get("ha", ""),
                            "ea18_status": aux_status,
                            "ea18_hash_count": hash_count,
                            "ea18_file_types": ",".join(file_types),
                            "ea18_url": aux_url,
                            "fetch_error": aux_error,
                        })

        state_path = latest / "live" / "uf" / f"{uf}.json"
        state = result_meta(state_path)
        selected_total = sum(
            (row["ea16_all_sections"] if model == "all" else row["ea16_principal_sections"])
            for row, _ in temp
        )
        municipal_ea20_ts = sum(row["ea20_ts"] for row, _ in temp)
        municipal_ea20_st = sum(row["ea20_st"] for row, _ in temp)

        summary_ufs[uf.upper()] = {
            "selected_section_count_model": model,
            "model_score_all": score_all,
            "model_score_principal": score_principal,
            "ea16_selected_sections_sum": selected_total,
            "ea20_state_ts": state["ts"],
            "ea20_state_st": state["st"],
            "ea20_municipal_ts_sum": municipal_ea20_ts,
            "ea20_municipal_st_sum": municipal_ea20_st,
            "state_ts_minus_municipal_ts": state["ts"] - municipal_ea20_ts,
            "state_st_minus_municipal_st": state["st"] - municipal_ea20_st,
            "ea16_minus_state_ts": selected_total - state["ts"],
            "anomalous_municipalities": anomalous_municipalities,
        }

    fields = [
        "uf","municipality_code","municipality_name","ea20_st","ea20_ts","ea20_pst",
        "ea20_dt","ea20_ht","ea16_all_sections","ea16_principal_sections",
        "ea16_with_aux_timestamp","diff_all_minus_ea20_ts",
        "diff_principal_minus_ea20_ts","selected_model","selected_config_sections",
        "diff_config_minus_ea20_ts","ea20_path"
    ]
    write_csv(OUT / "section_config_reconciliation.csv", reconciliation, fields)

    zone_fields = [
        "uf","municipality_code","municipality_name","zone","selected_model",
        "ea16_config_sections","ea16_all_sections","ea16_principal_sections",
        "ea16_with_aux_timestamp","ea20_zone_st","ea20_zone_ts","ea20_zone_pst",
        "diff_config_minus_zone_ts","fetch_error"
    ]
    write_csv(OUT / "zone_reconciliation.csv", zone_rows, zone_fields)

    section_fields = [
        "uf","municipality_code","municipality_name","zone","section",
        "is_aggregated","principal_section","aggregated_sections",
        "ea16_aux_date","ea16_aux_time","ea18_status","ea18_hash_count",
        "ea18_file_types","ea18_url","fetch_error"
    ]
    write_csv(OUT / "section_candidates.csv", section_rows, section_fields)

    summary = {
        "format": "tse-forensics-phase2-sections-v1",
        "created_at_utc": iso_utc(),
        "latest_snapshot": latest.name,
        "pleito": PLEITO,
        "election_id": ELECTION_ID,
        "ufs": summary_ufs,
        "raw_sources": raw_sources,
        "notes": [
            "O modelo de contagem EA16 (todas as seções ou apenas principais) é escolhido pela menor diferença global contra EA20 municipal.",
            "EA18 é consultado apenas para seções em zonas ainda anômalas e que já possuem data/hora auxiliar no EA16.",
            "A presença de BU/RDV/log no EA18 indica disponibilidade dos artefatos, mas este script não baixa os arquivos binários.",
        ],
    }
    (OUT / "phase2_sections_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("\nFASE 2 — localização das seções BA/MG")
    for uf, info in summary_ufs.items():
        if "error" in info:
            print(f"- {uf}: ERRO EA16: {info['error']}")
            print(f"  URL: {info['ea16_url']}")
            continue
        print(
            f"- {uf}: modelo EA16={info['selected_section_count_model']} · "
            f"UF ts={info['ea20_state_ts']} · soma municípios ts={info['ea20_municipal_ts_sum']} · "
            f"diferença={info['state_ts_minus_municipal_ts']:+d} · "
            f"municípios candidatos={len(info['anomalous_municipalities'])}"
        )
    print(f"- relatório: {OUT / 'phase2_sections_summary.json'}")
    print(f"- municípios: {OUT / 'section_config_reconciliation.csv'}")
    print(f"- zonas: {OUT / 'zone_reconciliation.csv'}")
    print(f"- seções candidatas: {OUT / 'section_candidates.csv'}")


if __name__ == "__main__":
    main()
