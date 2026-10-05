#!/usr/bin/env python3
"""Coleta evidências públicas do TSE para análise eleitoral posterior.

Usa somente a biblioteca padrão do Python. Os downloads são gravados de forma
atômica, recebem SHA-256 local e são descritos em manifestos JSON/JSONL.
"""

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ELECTION_ID = "6257"
ELECTION_CODE = "006257"
OFFICE_CODE = "0001"
RESULTS_BASE = f"https://resultados.tse.jus.br/oficial/ele2026/{ELECTION_ID}"
CATALOG_API = "https://dadosabertos.tse.jus.br/api/3/action"
USER_AGENT = "TSE-forensics-collector/1.0"


def utc_stamp():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def iso_utc():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def request(url, timeout=60):
    return urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Cache-Control": "no-cache"},
    )


def fetch_bytes(url, retries=3, timeout=60):
    last_error = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request(url, timeout), timeout=timeout) as response:
                return response.read()
        except Exception as exc:
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(1.5 * (attempt + 1))
    raise last_error


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    with temporary.open("wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def json_record(kind, url, path, data, **extra):
    return {
        "kind": kind,
        "url": url,
        "path": str(path),
        "bytes": len(data),
        "sha256": sha256_bytes(data),
        "captured_at_utc": iso_utc(),
        **extra,
    }


def fetch_json_file(kind, url, path, **extra):
    try:
        data = fetch_bytes(url)
        json.loads(data.decode("utf-8-sig"))
        atomic_write(path, data)
        return json_record(kind, url, path, data, **extra)
    except Exception as exc:
        return {"kind": kind, "url": url, "path": str(path), "error": str(exc), **extra}


def write_manifest(path, records):
    payload = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records)
    atomic_write(path, payload.encode("utf-8"))


def collect_live(output, workers):
    run_dir = output / "runs" / utc_stamp()
    run_dir.mkdir(parents=True, exist_ok=True)
    records = []

    config_url = f"{RESULTS_BASE}/config/mun-e{ELECTION_CODE}-cm.json"
    config_data = fetch_bytes(config_url)
    config = json.loads(config_data.decode("utf-8-sig"))
    config_path = run_dir / "config" / "municipios.json"
    atomic_write(config_path, config_data)
    records.append(json_record("config", config_url, config_path, config_data))

    national_url = f"{RESULTS_BASE}/dados/br/br-c{OFFICE_CODE}-e{ELECTION_CODE}-u.json"
    records.append(fetch_json_file("national", national_url, run_dir / "live" / "br.json"))

    jobs = []
    for region in config.get("abr", []):
        uf = str(region.get("cd", "")).lower()
        if not re.fullmatch(r"[a-z]{2}", uf):
            continue
        state_url = f"{RESULTS_BASE}/dados/{uf}/{uf}-c{OFFICE_CODE}-e{ELECTION_CODE}-u.json"
        jobs.append(("state", state_url, run_dir / "live" / "uf" / f"{uf}.json", {"uf": uf}))
        for city in region.get("mu", []):
            code = str(city.get("cd", ""))
            if not code.isdigit():
                continue
            city_url = f"{RESULTS_BASE}/dados/{uf}/{uf}{code}-c{OFFICE_CODE}-e{ELECTION_CODE}-u.json"
            jobs.append((
                "municipality",
                city_url,
                run_dir / "live" / "municipio" / uf / f"{code}.json",
                {"uf": uf, "municipality_code": code, "municipality_name": city.get("nm", "")},
            ))

    total = len(jobs)
    completed = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = [pool.submit(fetch_json_file, kind, url, path, **extra) for kind, url, path, extra in jobs]
        for future in concurrent.futures.as_completed(futures):
            records.append(future.result())
            completed += 1
            if completed % 250 == 0 or completed == total:
                print(f"JSONs oficiais: {completed}/{total}", flush=True)

    write_manifest(run_dir / "manifest.jsonl", records)
    errors = [row for row in records if row.get("error")]
    summary = {
        "format": "tse-forensics-live-v1",
        "created_at_utc": iso_utc(),
        "election_id": ELECTION_ID,
        "run_directory": str(run_dir),
        "files_ok": len(records) - len(errors),
        "files_error": len(errors),
        "errors": errors,
    }
    atomic_write(run_dir / "summary.json", json.dumps(summary, ensure_ascii=False, indent=2).encode("utf-8"))
    return summary


def safe_filename(value):
    value = urllib.parse.unquote(value or "arquivo")
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
    return value or "arquivo"


def download_resource(url, path):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not (parsed.hostname or "").endswith("tse.jus.br"):
        raise ValueError("recurso fora de domínio oficial do TSE")
    if path.exists() and path.stat().st_size:
        return path.stat().st_size, sha256_file(path), True
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    digest = hashlib.sha256()
    size = 0
    try:
        with urllib.request.urlopen(request(url, 180), timeout=180) as response, temporary.open("wb") as stream:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                stream.write(chunk)
                digest.update(chunk)
                size += len(chunk)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        return size, digest.hexdigest(), False
    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise


def collect_portal(output, download_files):
    portal_dir = output / "portal"
    portal_dir.mkdir(parents=True, exist_ok=True)
    query = urllib.parse.urlencode({"q": "resultados 2026", "rows": 100})
    catalog_url = f"{CATALOG_API}/package_search?{query}"
    catalog_data = fetch_bytes(catalog_url)
    catalog = json.loads(catalog_data.decode("utf-8"))
    datasets = [
        item for item in catalog.get("result", {}).get("results", [])
        if str(item.get("name", "")).startswith("resultados-2026")
    ]
    atomic_write(portal_dir / "catalog.json", json.dumps(catalog, ensure_ascii=False, indent=2).encode("utf-8"))

    records = []
    for dataset in datasets:
        slug = safe_filename(dataset.get("name", "dataset"))
        metadata_path = portal_dir / "metadata" / f"{slug}.json"
        metadata_data = json.dumps(dataset, ensure_ascii=False, indent=2).encode("utf-8")
        atomic_write(metadata_path, metadata_data)
        records.append(json_record("portal-metadata", catalog_url, metadata_path, metadata_data, dataset=slug))
        if not download_files:
            continue
        for resource in dataset.get("resources", []):
            url = resource.get("url") or ""
            basename = safe_filename(Path(urllib.parse.urlparse(url).path).name)
            resource_id = safe_filename(str(resource.get("id", "")))[:12]
            path = portal_dir / "files" / slug / f"{resource_id}--{basename}"
            try:
                size, digest, reused = download_resource(url, path)
                records.append({
                    "kind": "portal-resource",
                    "dataset": slug,
                    "resource_id": resource.get("id"),
                    "resource_name": resource.get("name"),
                    "format": resource.get("format"),
                    "url": url,
                    "path": str(path),
                    "bytes": size,
                    "sha256": digest,
                    "official_hash": resource.get("hash") or None,
                    "reused": reused,
                    "captured_at_utc": iso_utc(),
                })
                print(f"Portal: {slug} / {resource.get('name')}", flush=True)
            except Exception as exc:
                records.append({"kind": "portal-resource", "dataset": slug, "url": url, "path": str(path), "error": str(exc)})

    write_manifest(portal_dir / "manifest.jsonl", records)
    errors = [row for row in records if row.get("error")]
    summary = {
        "format": "tse-forensics-portal-v1",
        "created_at_utc": iso_utc(),
        "datasets_found": [item.get("name") for item in datasets],
        "download_files": download_files,
        "records_ok": len(records) - len(errors),
        "records_error": len(errors),
        "errors": errors,
    }
    atomic_write(portal_dir / "summary.json", json.dumps(summary, ensure_ascii=False, indent=2).encode("utf-8"))
    return summary


def main():
    parser = argparse.ArgumentParser(description="Coleta dados públicos oficiais do TSE com hashes e manifestos.")
    parser.add_argument("command", choices=("snapshot", "portal", "all"))
    parser.add_argument("--output", default="data/forensics", help="diretório de saída")
    parser.add_argument("--workers", type=int, default=8, help="downloads simultâneos dos JSONs municipais")
    parser.add_argument("--download-portal-files", action="store_true", help="baixa também ZIP/CSV do portal; pode ocupar muitos GB")
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    summaries = []
    if args.command in ("snapshot", "all"):
        summaries.append(collect_live(output, args.workers))
    if args.command in ("portal", "all"):
        summaries.append(collect_portal(output, args.download_portal_files))
    print(json.dumps(summaries, ensure_ascii=False, indent=2))
    return 1 if any(item.get("files_error", 0) or item.get("records_error", 0) for item in summaries) else 0


if __name__ == "__main__":
    sys.exit(main())
