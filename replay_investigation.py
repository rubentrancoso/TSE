#!/usr/bin/env python3
"""Reexecução e auditoria de proveniência da investigação TSE.

Uso:
  python replay_investigation.py --list
  python replay_investigation.py --check
  python replay_investigation.py --phase 4J
  python replay_investigation.py --from-phase 3B
  python replay_investigation.py --all
  python replay_investigation.py --all --dry-run
"""

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROV = ROOT / "provenance"
SOURCES_PATH = PROV / "SOURCES.json"
PHASES_PATH = PROV / "PHASES.json"
REPLAY_OUT = ROOT / "data" / "forensics" / "analysis" / "replay_latest.json"
NONPRIMARY_CLASSES = {"derived_capture", "public_capture"}


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_head():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return None


def source_map():
    data = load_json(SOURCES_PATH)
    return {s["id"]: s for s in data["sources"]}


def phases():
    return load_json(PHASES_PATH)["phases"]


def primary_gap(source):
    return bool(
        source.get("primary_replacement_needed")
        and source.get("class") in NONPRIMARY_CLASSES
    )


def existing_exact_paths(source):
    rows = []
    for rel in source.get("local_paths", []):
        p = ROOT / rel
        item = {
            "path": rel,
            "exists": p.exists(),
            "bytes": p.stat().st_size if p.exists() and p.is_file() else None,
        }
        if p.exists() and p.is_file():
            item["sha256"] = sha256_file(p)
            expected = source.get("sha256")
            item["sha256_expected"] = expected
            item["sha256_matches"] = (
                item["sha256"] == expected if expected else None
            )
        rows.append(item)
    return rows


def existing_roots(source):
    return [
        {"path": rel, "exists": (ROOT / rel).exists()}
        for rel in source.get("local_roots", [])
    ]


def source_status(source):
    return {
        "id": source["id"],
        "class": source.get("class"),
        "status": source.get("status"),
        "primary_gap": primary_gap(source),
        "exact_paths": existing_exact_paths(source),
        "roots": existing_roots(source),
    }


def phase_status(phase, smap):
    script = ROOT / phase["script"]
    sources = [smap[sid] for sid in phase.get("sources", [])]
    outputs = []
    for rel in phase.get("outputs", []):
        p = ROOT / rel
        outputs.append({
            "path": rel,
            "exists": p.exists(),
            "sha256": sha256_file(p) if p.exists() and p.is_file() else None,
        })
    return {
        "id": phase["id"],
        "script": phase["script"],
        "script_exists": script.exists(),
        "sources": [
            {
                "id": s["id"],
                "class": s.get("class"),
                "primary_gap": primary_gap(s),
            }
            for s in sources
        ],
        "primary_replay_ready": not any(primary_gap(s) for s in sources),
        "outputs": outputs,
    }


def print_list(phs, smap):
    print("Fases da investigação:")
    for ph in phs:
        srcs = [smap[s] for s in ph.get("sources", [])]
        gaps = [s["id"] for s in srcs if primary_gap(s)]
        state = "PRIMARY-READY" if not gaps else "PRIMARY-GAP: " + ",".join(gaps)
        print(f"- {ph['id']:>3}  {ph['script']}  [{state}]")


def do_check(phs, smap):
    print("CHECK DE PROVENIÊNCIA E REPLAY\n")
    missing_scripts = 0
    primary_gap_phases = 0

    for ph in phs:
        st = phase_status(ph, smap)
        if not st["script_exists"]:
            missing_scripts += 1
        if not st["primary_replay_ready"]:
            primary_gap_phases += 1

    print(f"- fases registradas: {len(phs)}")
    print(f"- scripts ausentes: {missing_scripts}")
    print(
        "- fases ainda dependentes de captura/derivado não primário: "
        f"{primary_gap_phases}"
    )

    print("\nFontes:")
    for sid, src in smap.items():
        st = source_status(src)
        gap = " · PRECISA REPLAY PRIMÁRIO" if st["primary_gap"] else ""
        print(f"- {sid}: {st['class']} · {st['status']}{gap}")
        for p in st["exact_paths"]:
            extra = ""
            if p.get("sha256_matches") is False:
                extra = " · HASH DIFERENTE"
            elif p.get("sha256_matches") is True:
                extra = " · hash OK"
            print(
                f"    arquivo {p['path']}: "
                f"{'OK' if p['exists'] else 'ausente'}{extra}"
            )
        for p in st["roots"]:
            print(
                f"    raiz {p['path']}: "
                f"{'OK' if p['exists'] else 'ausente'}"
            )

    print("\nAusência local não significa ausência da fonte; significa que um replay")
    print("congelado/offline ainda não está garantido nesta máquina.")


def select_phases(phs, phase_ids, from_phase, run_all):
    if run_all:
        return phs
    if from_phase:
        idx = next(
            (
                i
                for i, p in enumerate(phs)
                if p["id"].lower() == from_phase.lower()
            ),
            None,
        )
        if idx is None:
            raise SystemExit(f"Fase desconhecida: {from_phase}")
        return phs[idx:]
    if phase_ids:
        wanted = {x.lower() for x in phase_ids}
        selected = [p for p in phs if p["id"].lower() in wanted]
        missing = wanted - {p["id"].lower() for p in selected}
        if missing:
            raise SystemExit(
                "Fases desconhecidas: " + ", ".join(sorted(missing))
            )
        return selected
    raise SystemExit(
        "Escolha --list, --check, --phase, --from-phase ou --all."
    )


def output_hashes(phase):
    rows = []
    for rel in phase.get("outputs", []):
        p = ROOT / rel
        rows.append({
            "path": rel,
            "exists": p.exists(),
            "bytes": p.stat().st_size if p.exists() and p.is_file() else None,
            "sha256": sha256_file(p) if p.exists() and p.is_file() else None,
        })
    return rows


def run_selected(selected, smap, dry_run):
    manifest = {
        "format": "tse-investigation-replay-v1",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": git_head(),
        "python": sys.version,
        "platform": platform.platform(),
        "dry_run": dry_run,
        "phases": [],
    }

    for ph in selected:
        gaps = [
            sid
            for sid in ph.get("sources", [])
            if primary_gap(smap[sid])
        ]
        cmd = [sys.executable, ph["script"]]
        rec = {
            "phase": ph["id"],
            "script": ph["script"],
            "command": cmd,
            "sources": ph.get("sources", []),
            "primary_gaps": gaps,
            "outputs_before": output_hashes(ph),
        }

        print(f"\n=== FASE {ph['id']} · {ph['script']} ===")
        if gaps:
            print(
                "AVISO: ainda depende de fonte não primária: "
                + ", ".join(gaps)
            )

        if dry_run:
            rec["returncode"] = None
            rec["outputs_after"] = rec["outputs_before"]
            manifest["phases"].append(rec)
            continue

        env = os.environ.copy()
        env["TSE_REPLAY"] = "1"
        proc = subprocess.run(cmd, cwd=ROOT, env=env)
        rec["returncode"] = proc.returncode
        rec["outputs_after"] = output_hashes(ph)
        manifest["phases"].append(rec)

        if proc.returncode != 0:
            manifest["status"] = "failed"
            manifest["failed_phase"] = ph["id"]
            break
    else:
        manifest["status"] = "dry-run" if dry_run else "completed"

    manifest["finished_at_utc"] = datetime.now(timezone.utc).isoformat()

    if not dry_run:
        REPLAY_OUT.parent.mkdir(parents=True, exist_ok=True)
        REPLAY_OUT.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(
            "\nManifesto do replay: "
            f"{REPLAY_OUT.relative_to(ROOT)}"
        )

    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--phase", action="append", default=[])
    ap.add_argument("--from-phase")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    smap = source_map()
    phs = phases()

    for ph in phs:
        unknown = [
            x for x in ph.get("sources", [])
            if x not in smap
        ]
        if unknown:
            raise SystemExit(
                f"Fase {ph['id']} referencia fontes desconhecidas: {unknown}"
            )

    if args.list:
        print_list(phs, smap)
        return
    if args.check:
        do_check(phs, smap)
        return

    selected = select_phases(
        phs, args.phase, args.from_phase, args.all
    )
    run_selected(selected, smap, args.dry_run)


if __name__ == "__main__":
    main()
