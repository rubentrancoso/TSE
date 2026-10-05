#!/usr/bin/env python3
"""Fase 3A — teste de viabilidade temporal usando EA16.

Objetivo:
- verificar se os campos da/ha atuais do EA16 ainda preservam uma cronologia
  útil da chegada dos arquivos de urna;
- produzir somente artefatos derivados compactos para versionamento.

Fontes:
- EA16 oficial de todas as UFs (dados brutos ficam em data/forensics/phase3/raw)
- histórico presidencial independente já usado no projeto, quando disponível

Saídas:
  data/forensics/analysis/phase3_arrivals_summary.json
  data/forensics/analysis/phase3_arrivals_by_minute.csv
  data/forensics/analysis/phase3_arrivals_by_uf.csv
"""

import csv
import json
import hashlib
import os
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

BASE = "https://resultados.tse.jus.br/oficial/ele2026"
PLEITO = "3220"
PLEITO_CODE = "003220"
UFS = (
    "ac","al","am","ap","ba","ce","df","es","go","ma","mg","ms","mt","pa",
    "pb","pe","pi","pr","rj","rn","ro","rr","rs","sc","se","sp","to"
)
USER_AGENT = "TSE-forensics-phase3-arrivals/1.0"

ROOT = Path("data/forensics")
RAW = ROOT / "phase3" / "raw" / "ea16"
OUT = ROOT / "analysis"


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    with tmp.open("wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def fetch(url, path):
    if path.exists() and path.stat().st_size:
        data = path.read_bytes()
        return data, True
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Cache-Control": "no-cache"}
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        data = r.read()
    atomic_write(path, data)
    return data, False


def parse_dt(da, ha):
    da = (da or "").strip()
    ha = (ha or "").strip()
    if not da or not ha:
        return None
    fmts = (
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
    )
    raw = f"{da} {ha}"
    for fmt in fmts:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            pass
    return None


def iter_principal_sections(data, uf):
    abrs = data.get("abr", []) or []
    abr = next((x for x in abrs if str(x.get("cd", "")).lower() == uf), None)
    if abr is None and len(abrs) == 1:
        abr = abrs[0]
    if not abr:
        return
    for mu in abr.get("mu", []) or []:
        mcode = str(mu.get("cd", "")).zfill(5)
        for zon in mu.get("zon", []) or []:
            zcode = str(zon.get("cd", "")).zfill(4)
            for sec in zon.get("sec", []) or []:
                if sec.get("nsp"):
                    continue
                yield {
                    "uf": uf.upper(),
                    "municipality_code": mcode,
                    "zone": zcode,
                    "section": str(sec.get("ns", "")).zfill(4),
                    "da": sec.get("da", ""),
                    "ha": sec.get("ha", ""),
                }


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)

    minute_counter = Counter()
    uf_stats = defaultdict(lambda: {
        "sections": 0,
        "with_timestamp": 0,
        "without_timestamp": 0,
        "earliest": None,
        "latest": None,
    })
    sources = []
    parse_failures = 0

    for uf in UFS:
        url = f"{BASE}/arquivo-urna/{PLEITO}/config/{uf}/{uf}-p{PLEITO_CODE}-cs.json"
        path = RAW / f"{uf}-p{PLEITO_CODE}-cs.json"
        try:
            data_bytes, reused = fetch(url, path)
            data = json.loads(data_bytes.decode("utf-8-sig"))
        except Exception as exc:
            sources.append({"uf": uf.upper(), "url": url, "error": str(exc)})
            print(f"- {uf.upper()}: ERRO {exc}")
            continue

        sources.append({
            "uf": uf.upper(),
            "url": url,
            "path": str(path),
            "sha256": sha256(data_bytes),
            "bytes": len(data_bytes),
            "reused": reused,
        })

        for sec in iter_principal_sections(data, uf):
            st = uf_stats[uf.upper()]
            st["sections"] += 1
            dt = parse_dt(sec["da"], sec["ha"])
            if dt is None:
                if sec["da"] or sec["ha"]:
                    parse_failures += 1
                st["without_timestamp"] += 1
                continue
            st["with_timestamp"] += 1
            minute = dt.replace(second=0)
            key = minute.strftime("%Y-%m-%d %H:%M")
            minute_counter[key] += 1
            iso = dt.isoformat()
            if st["earliest"] is None or iso < st["earliest"]:
                st["earliest"] = iso
            if st["latest"] is None or iso > st["latest"]:
                st["latest"] = iso

        print(
            f"- {uf.upper()}: {uf_stats[uf.upper()]['sections']} seções principais · "
            f"{uf_stats[uf.upper()]['with_timestamp']} com da/ha"
        )

    minute_rows = []
    cumulative = 0
    for minute in sorted(minute_counter):
        count = minute_counter[minute]
        cumulative += count
        minute_rows.append({
            "minute": minute,
            "sections_generated": count,
            "cumulative_sections": cumulative,
        })

    uf_rows = []
    for uf in sorted(uf_stats):
        st = uf_stats[uf]
        uf_rows.append({
            "uf": uf,
            "sections": st["sections"],
            "with_timestamp": st["with_timestamp"],
            "without_timestamp": st["without_timestamp"],
            "timestamp_coverage_pct": (
                100.0 * st["with_timestamp"] / st["sections"] if st["sections"] else 0.0
            ),
            "earliest": st["earliest"] or "",
            "latest": st["latest"] or "",
        })

    write_csv(
        OUT / "phase3_arrivals_by_minute.csv",
        minute_rows,
        ["minute","sections_generated","cumulative_sections"],
    )
    write_csv(
        OUT / "phase3_arrivals_by_uf.csv",
        uf_rows,
        ["uf","sections","with_timestamp","without_timestamp","timestamp_coverage_pct","earliest","latest"],
    )

    total_sections = sum(x["sections"] for x in uf_stats.values())
    total_ts = sum(x["with_timestamp"] for x in uf_stats.values())

    peak_minutes = sorted(
        (
            {"minute": minute, "sections_generated": count}
            for minute, count in minute_counter.items()
        ),
        key=lambda x: x["sections_generated"],
        reverse=True,
    )[:30]

    all_times = list(minute_counter)
    summary = {
        "format": "tse-forensics-phase3-arrivals-v1",
        "pleito": PLEITO,
        "principal_sections": total_sections,
        "sections_with_timestamp": total_ts,
        "sections_without_timestamp": total_sections - total_ts,
        "timestamp_coverage_pct": 100.0 * total_ts / total_sections if total_sections else 0.0,
        "parse_failures": parse_failures,
        "earliest_minute": min(all_times) if all_times else None,
        "latest_minute": max(all_times) if all_times else None,
        "distinct_minutes": len(all_times),
        "peak_minutes": peak_minutes,
        "ufs": dict(uf_stats),
        "sources": sources,
        "interpretation_rule": (
            "EA16 será considerado temporalmente útil apenas se a distribuição de da/ha "
            "mostrar progressão compatível com a noite eleitoral. Se houver concentração "
            "artificial em poucos minutos posteriores, esses campos não serão usados como "
            "substituto de snapshots históricos."
        ),
    }
    (OUT / "phase3_arrivals_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("\nFASE 3A — viabilidade temporal EA16")
    print(f"- seções principais: {total_sections}")
    print(f"- com da/ha: {total_ts} ({summary['timestamp_coverage_pct']:.2f}%)")
    print(f"- minutos distintos: {summary['distinct_minutes']}")
    print(f"- primeiro minuto: {summary['earliest_minute']}")
    print(f"- último minuto: {summary['latest_minute']}")
    if peak_minutes:
        print("- maiores concentrações:")
        for x in peak_minutes[:10]:
            print(f"  {x['minute']}: {x['sections_generated']} seções")
    print(f"- resumo: {OUT / 'phase3_arrivals_summary.json'}")
    print(f"- histograma: {OUT / 'phase3_arrivals_by_minute.csv'}")
    print(f"- UFs: {OUT / 'phase3_arrivals_by_uf.csv'}")


if __name__ == "__main__":
    main()
