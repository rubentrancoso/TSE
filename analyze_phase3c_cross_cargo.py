#!/usr/bin/env python3
"""Fase 3C — comparação contemporânea Presidente x cargos estaduais.

Usa uma terceira captura independente, preservada no repositório
madebysandro/apuracao-2026, que contém respostas brutas reais do TSE em
vários ciclos de 04/10/2026.

A captura é especialmente útil porque, no MESMO ciclo de gravação, contém:
- Presidente nacional (BR);
- Presidente no Pará (PA);
- Governador PA;
- Senador PA;
- Deputado Federal PA;
- Deputado Estadual PA.

Isso permite medir se os arquivos dos diferentes cargos estaduais estavam
trabalhando sobre praticamente o mesmo conjunto de seções e comparar esse
andamento com o Presidente no mesmo estado e com o agregado nacional.

Limitação importante: os ciclos preservados saltam de ~18:44 para ~20:16 BRT.
Logo, esta fonte não cobre diretamente toda a janela 18:49–19:32; ela serve
como evidência independente de alinhamento entre cargos imediatamente antes
e depois do período crítico.

Saídas:
  data/forensics/analysis/phase3c_cross_cargo_cycles.csv
  data/forensics/analysis/phase3c_pa_alignment.csv
  data/forensics/analysis/phase3c_summary.json

Brutos preservados (ignorados pelo Git):
  data/forensics/external/madebysandro-apuracao-2026/...
"""

import csv
import hashlib
import json
import os
import statistics
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path("data/forensics")
RAW = ROOT / "external"
OUT = ROOT / "analysis"
UA = "TSE-forensics-phase3c/1.0"

SOURCE_COMMIT = "8917e32edb3aafd72664dc47a5ba53f576575197"
SOURCE_REPO = "madebysandro/apuracao-2026"

CYCLES = [
    "2026-10-04T21-36-05-598Z",
    "2026-10-04T21-38-48-884Z",
    "2026-10-04T21-39-46-908Z",
    "2026-10-04T21-44-49-070Z",
    "2026-10-04T23-17-25-721Z",
    "2026-10-05T00-01-02-086Z",
]

FILES = {
    "presidente_br": ("presidente.json", "Presidente", "BR", "6257"),
    "presidente_pa": ("pres-pa.json", "Presidente", "PA", "6257"),
    "governador_pa": ("governador.json", "Governador", "PA", "6259"),
    "senador_pa": ("senador.json", "Senador", "PA", "6259"),
    "depfed_pa": ("depfed.json", "Deputado Federal", "PA", "6259"),
    "depest_pa": ("depest.json", "Deputado Estadual", "PA", "6259"),
}

STATE_KEYS = ["governador_pa", "senador_pa", "depfed_pa", "depest_pa"]


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


def raw_url(cycle, filename):
    return (
        f"https://raw.githubusercontent.com/{SOURCE_REPO}/{SOURCE_COMMIT}/"
        f"fixtures/tse-provisorio/{cycle}/{filename}"
    )


def fetch(cycle, key, filename):
    path = RAW / "madebysandro-apuracao-2026" / SOURCE_COMMIT / cycle / filename
    url = raw_url(cycle, filename)
    if path.exists() and path.stat().st_size:
        data = path.read_bytes()
        reused = True
    else:
        req = urllib.request.Request(
            url, headers={"User-Agent": UA, "Cache-Control": "no-cache"}
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                data = r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None, {
                    "cycle": cycle,
                    "key": key,
                    "url": url,
                    "status": 404,
                }
            raise
        atomic_write(path, data)
        reused = False
    return json.loads(data.decode("utf-8-sig")), {
        "cycle": cycle,
        "key": key,
        "url": url,
        "path": str(path),
        "sha256": sha256(data),
        "bytes": len(data),
        "reused": reused,
        "status": 200,
    }


def n(v):
    if v is None or v == "":
        return None
    try:
        return int(str(v).replace(".", ""))
    except ValueError:
        return float(str(v).replace(",", "."))


def f(v):
    if v is None or v == "":
        return None
    return float(str(v).replace(",", "."))


def extract(cycle, key, role, scope, election, obj, meta):
    s = obj.get("s", {})
    v = obj.get("v", {})
    return {
        "cycle_utc": cycle,
        "source_key": key,
        "cargo": role,
        "scope": scope,
        "eleicao": election,
        "dg": obj.get("dg"),
        "hg": obj.get("hg"),
        "dt": obj.get("dt"),
        "ht": obj.get("ht"),
        "idg": obj.get("idg"),
        "ts": n(s.get("ts")),
        "st": n(s.get("st")),
        "pst": f(s.get("pstn") or s.get("pst")),
        "tv": n(v.get("tv")),
        "vv": n(v.get("vv")),
        "sha256": meta.get("sha256"),
    }


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as fobj:
        w = csv.DictWriter(fobj, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    manifests = []
    by_cycle = {}

    for cycle in CYCLES:
        by_cycle[cycle] = {}
        for key, (filename, role, scope, election) in FILES.items():
            obj, meta = fetch(cycle, key, filename)
            manifests.append(meta)
            if obj is None:
                continue
            rec = extract(cycle, key, role, scope, election, obj, meta)
            records.append(rec)
            by_cycle[cycle][key] = rec

    write_csv(
        OUT / "phase3c_cross_cargo_cycles.csv",
        records,
        [
            "cycle_utc","source_key","cargo","scope","eleicao","dg","hg","dt","ht",
            "idg","ts","st","pst","tv","vv","sha256",
        ],
    )

    alignment = []
    for cycle in CYCLES:
        items = by_cycle[cycle]
        pres_pa = items.get("presidente_pa")
        pres_br = items.get("presidente_br")
        state = [items[k] for k in STATE_KEYS if k in items]
        if not pres_pa or not state:
            continue
        sts = [int(x["st"]) for x in state]
        med = statistics.median(sts)
        alignment.append({
            "cycle_utc": cycle,
            "pres_br_st": pres_br["st"] if pres_br else None,
            "pres_br_hg": pres_br["hg"] if pres_br else None,
            "pres_pa_st": pres_pa["st"],
            "pres_pa_hg": pres_pa["hg"],
            "state_cargos_n": len(state),
            "state_st_min": min(sts),
            "state_st_max": max(sts),
            "state_st_spread": max(sts) - min(sts),
            "state_st_median": med,
            "pres_pa_minus_state_median": int(pres_pa["st"] - med),
            "abs_pres_pa_minus_state_median": abs(int(pres_pa["st"] - med)),
            "governador_st": items.get("governador_pa", {}).get("st"),
            "senador_st": items.get("senador_pa", {}).get("st"),
            "depfed_st": items.get("depfed_pa", {}).get("st"),
            "depest_st": items.get("depest_pa", {}).get("st"),
        })

    write_csv(
        OUT / "phase3c_pa_alignment.csv",
        alignment,
        [
            "cycle_utc","pres_br_st","pres_br_hg","pres_pa_st","pres_pa_hg",
            "state_cargos_n","state_st_min","state_st_max","state_st_spread",
            "state_st_median","pres_pa_minus_state_median",
            "abs_pres_pa_minus_state_median","governador_st","senador_st",
            "depfed_st","depest_st",
        ],
    )

    state_spreads = [r["state_st_spread"] for r in alignment]
    pres_state_abs = [r["abs_pres_pa_minus_state_median"] for r in alignment]

    # Landmarks mais úteis para leitura humana.
    landmarks = []
    for row in alignment:
        if row["cycle_utc"] in (
            "2026-10-04T21-36-05-598Z",
            "2026-10-04T21-39-46-908Z",
            "2026-10-04T21-44-49-070Z",
            "2026-10-04T23-17-25-721Z",
            "2026-10-05T00-01-02-086Z",
        ):
            landmarks.append(row)

    summary = {
        "format": "tse-forensics-phase3c-cross-cargo-v1",
        "source": {
            "repo": SOURCE_REPO,
            "commit": SOURCE_COMMIT,
            "description": (
                "fixtures reais do TSE extraídas de uma gravação contemporânea; "
                "respostas brutas preservadas por ciclo"
            ),
        },
        "manifest": manifests,
        "cycles_requested": len(CYCLES),
        "records_loaded": len(records),
        "alignment_cycles": len(alignment),
        "pa_state_cargo_alignment": {
            "max_spread_sections_among_6259_cargos": max(state_spreads) if state_spreads else None,
            "max_abs_president_pa_vs_state_median_sections": max(pres_state_abs) if pres_state_abs else None,
            "landmarks": landmarks,
        },
        "interpretation": [
            (
                "Nos ciclos preservados, Governador/Senador/Deputados do Pará operam "
                "sobre contagens de seções iguais ou quase iguais entre si; isso é "
                "compatível com a origem comum nos mesmos boletins/seções."
            ),
            (
                "O arquivo de Presidente do Pará acompanha os cargos estaduais com "
                "diferenças pequenas de dezenas de seções, explicáveis pela geração "
                "assíncrona dos arquivos dentro do mesmo ciclo de captura."
            ),
            (
                "A fonte preserva ciclos imediatamente antes (~18:36–18:44) e depois "
                "(~20:16 e ~21:00) do período crítico, mas não contém ciclos entre "
                "~18:44 e ~20:16; portanto não mede diretamente Governador durante "
                "18:49–19:32."
            ),
            (
                "O resultado fortalece a premissa técnica de que, quando uma seção "
                "está disponível na camada estadual, os diferentes cargos do mesmo "
                "estado avançam em conjunto; a próxima busca deve procurar snapshots "
                "adicionais especificamente dentro de 18:49–19:32."
            ),
        ],
    }

    (OUT / "phase3c_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("\nFASE 3C — Presidente x cargos estaduais (captura contemporânea)")
    print(f"- registros carregados: {len(records)}")
    print(f"- ciclos com comparação PA: {len(alignment)}")
    if state_spreads:
        print(
            "- maior dispersão entre Governador/Senador/Deputados no mesmo ciclo: "
            f"{max(state_spreads)} seções"
        )
    if pres_state_abs:
        print(
            "- maior |Presidente PA - mediana cargos estaduais|: "
            f"{max(pres_state_abs)} seções"
        )
    print(f"- resumo: {OUT / 'phase3c_summary.json'}")
    print(f"- ciclos: {OUT / 'phase3c_cross_cargo_cycles.csv'}")
    print(f"- alinhamento: {OUT / 'phase3c_pa_alignment.csv'}")


if __name__ == "__main__":
    main()
