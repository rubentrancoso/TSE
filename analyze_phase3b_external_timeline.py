#!/usr/bin/env python3
"""Fase 3B — reconstrução temporal por capturas independentes contemporâneas.

Baixa e preserva cópias fixadas por commit de dois coletores públicos
independentes que acompanharam a divulgação do TSE em 04/10/2026:

1) ArvorCo/PNAD — linha do tempo derivada de um SQLite de auditoria que
   registrou versões, horários, hashes e requisições.
2) vitoropereira/eleicoes2026 — snapshots e comparação nacional x soma UFs
   preservados durante a noite.

Objetivo: quantificar a defasagem do EA20 nacional de Presidente, segmentar
a janela em fases e verificar concordância entre fontes independentes.

IMPORTANTE: estas são capturas independentes de respostas do TSE, não
substituem os artefatos oficiais assinados. Servem como evidência temporal
secundária porque o endpoint atual não oferece versões históricas.

Saídas versionáveis:
  data/forensics/analysis/phase3b_summary.json
  data/forensics/analysis/phase3b_lag_by_minute.csv
  data/forensics/analysis/phase3b_phases.csv
  data/forensics/analysis/phase3b_crosscheck.csv

Brutos preservados (ignorados pelo Git):
  data/forensics/external/...
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
UA = "TSE-forensics-phase3b/1.0"

ARVOR_COMMIT = "beb3bec9ae5c25e2868ee2f2cefb9e6dccd91415"
VITOR_COMMIT = "3f4d7442dd601eb1b11afb8e9510d1373c495e7c"

SOURCES = {
    "arvor_linha_do_tempo": (
        f"https://raw.githubusercontent.com/ArvorCo/PNAD/{ARVOR_COMMIT}/"
        "analysis/apuracao_2026/dados/linha_do_tempo.json",
        RAW / "ArvorCo-PNAD" / ARVOR_COMMIT / "linha_do_tempo.json",
    ),
    "vitor_comparacao_fontes": (
        f"https://raw.githubusercontent.com/vitoropereira/eleicoes2026/{VITOR_COMMIT}/"
        "marcos/75pct/comparacao_fontes.json",
        RAW / "vitoropereira-eleicoes2026" / VITOR_COMMIT / "comparacao_fontes.json",
    ),
    "vitor_historico": (
        f"https://raw.githubusercontent.com/vitoropereira/eleicoes2026/{VITOR_COMMIT}/"
        "historico.json",
        RAW / "vitoropereira-eleicoes2026" / VITOR_COMMIT / "historico.json",
    ),
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


def fetch_json(name):
    url, path = SOURCES[name]
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
    obj = json.loads(data.decode("utf-8-sig"))
    return obj, {
        "name": name,
        "url": url,
        "path": str(path),
        "sha256": sha256(data),
        "bytes": len(data),
        "reused": reused,
    }


def table_rows(table):
    cols = table.get("colunas", [])
    return [dict(zip(cols, row)) for row in table.get("linhas", [])]


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def find_national_version(arvor, st):
    rows = table_rows(arvor["nacional"]["versoes"])
    candidates = [r for r in rows if int(r.get("st") or 0) == st]
    if not candidates:
        return None
    # Prefer a genuine/non-regressive row with the newest generation time.
    candidates.sort(key=lambda r: (bool(r.get("marcada_regressiva")), r.get("gerado_em") or ""))
    return candidates[-1]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    raw_meta = []

    arvor, m = fetch_json("arvor_linha_do_tempo")
    raw_meta.append(m)
    vitor, m = fetch_json("vitor_comparacao_fontes")
    raw_meta.append(m)
    vitor_hist, m = fetch_json("vitor_historico")
    raw_meta.append(m)

    # ----- minuto a minuto: nacional x soma das UFs -----
    lag = table_rows(arvor["divergencia_soma_ufs"]["minutos"])
    lag_fields = [
        "hora_brt",
        "nacional_st_visivel",
        "soma_ufs_st_visivel",
        "diferenca_visivel",
        "nacional_gerado_brt_visivel",
        "nacional_st_gerado",
        "soma_ufs_st_gerado",
        "diferenca_gerado",
        "nacional_gerado_brt_gerado",
        "andamento_br_st_visivel",
    ]
    write_csv(OUT / "phase3b_lag_by_minute.csv", lag, lag_fields)

    # ----- travamentos e fases -----
    freezes = arvor["travamentos"]["nacional"]
    major = [x for x in freezes if x["de_brt"].startswith("2026-10-04 18:48") or
             x["de_brt"].startswith("2026-10-04 19:14")]
    major.sort(key=lambda x: x["de_brt"])
    if len(major) < 2:
        raise RuntimeError("Não foi possível localizar os dois travamentos principais.")

    f1, f2 = major[0], major[1]
    gap = arvor["pausa_geral"]["lacunas"][0]

    phases = [
        {
            "phase": "A",
            "start_brt": f1["de_brt"],
            "end_brt": f1["ate_brt"],
            "minutes": f1["minutos"],
            "description": "EA20 nacional de Presidente sem nova versão; UFs/lower layers continuam avançando.",
            "national_sections_start": f1["st_de"],
            "national_sections_end": f1["st_ate"],
            "all_u_result_generation_paused": "no",
        },
        {
            "phase": "B",
            "start_brt": f2["de_brt"],
            "end_brt": gap["de_brt"],
            "minutes": round(
                (
                    __import__("datetime").datetime.fromisoformat(gap["de_brt"]) -
                    __import__("datetime").datetime.fromisoformat(f2["de_brt"])
                ).total_seconds() / 60, 2
            ),
            "description": "Nacional de Presidente segue congelado; soma das UFs e monitoramento continuam avançando.",
            "national_sections_start": f2["st_de"],
            "national_sections_end": f2["st_de"],
            "all_u_result_generation_paused": "no",
        },
        {
            "phase": "C",
            "start_brt": gap["de_brt"],
            "end_brt": gap["ate_brt"],
            "minutes": gap["minutos"],
            "description": "Lacuna geral: nenhuma nova geração de arquivo EA20 (-u) de qualquer cargo/nível; EA14/EA15 (-ab) ainda têm uma rodada nova.",
            "national_sections_start": f2["st_de"],
            "national_sections_end": f2["st_de"],
            "all_u_result_generation_paused": "yes",
        },
        {
            "phase": "D",
            "start_brt": gap["ate_brt"],
            "end_brt": f2["ate_brt"],
            "minutes": round(
                (
                    __import__("datetime").datetime.fromisoformat(f2["ate_brt"]) -
                    __import__("datetime").datetime.fromisoformat(gap["ate_brt"])
                ).total_seconds() / 60, 2
            ),
            "description": "Arquivos de resultado voltam a ser gerados; nacional de Presidente ainda aguarda até publicar o lote acumulado.",
            "national_sections_start": f2["st_de"],
            "national_sections_end": f2["st_ate"],
            "all_u_result_generation_paused": "no",
        },
    ]
    write_csv(
        OUT / "phase3b_phases.csv",
        phases,
        [
            "phase","start_brt","end_brt","minutes","description",
            "national_sections_start","national_sections_end",
            "all_u_result_generation_paused",
        ],
    )

    # ----- landmarks do nacional -----
    frozen = find_national_version(arvor, 323539)
    unlocked = find_national_version(arvor, 424153)
    if not frozen or not unlocked:
        raise RuntimeError("Landmarks nacionais esperados não encontrados.")

    # ----- cross-check com segundo coletor independente -----
    vl = vitor["leituras"]
    v_frozen = next(x for x in vl if "TRAVADO" in x.get("fonte", ""))
    v_uf = next(x for x in vl if x.get("fonte") == "soma das UFs (usada no marco 75%)")
    v_unlock = next(x for x in vl if "destravado" in x.get("fonte", ""))

    cross = [
        {
            "metric": "national_frozen_sections",
            "arvor_value": frozen["st"],
            "vitor_value": v_frozen["secoes_apuradas"],
            "difference": int(frozen["st"]) - int(v_frozen["secoes_apuradas"]),
            "note": "Mesmo estado nacional congelado em dois coletores.",
        },
        {
            "metric": "national_frozen_valid_votes",
            "arvor_value": frozen["vv"],
            "vitor_value": v_frozen["votos_validos"],
            "difference": int(frozen["vv"]) - int(v_frozen["votos_validos"]),
            "note": "Votos válidos do estado congelado.",
        },
        {
            "metric": "national_unlocked_sections",
            "arvor_value": unlocked["st"],
            "vitor_value": v_unlock["secoes_apuradas"],
            "difference": int(unlocked["st"]) - int(v_unlock["secoes_apuradas"]),
            "note": "Primeiro grande estado nacional após destravamento.",
        },
        {
            "metric": "national_unlocked_valid_votes",
            "arvor_value": unlocked["vv"],
            "vitor_value": v_unlock["votos_validos"],
            "difference": int(unlocked["vv"]) - int(v_unlock["votos_validos"]),
            "note": "Votos válidos do primeiro grande estado após destravamento.",
        },
        {
            "metric": "uf_sum_landmark_sections",
            "arvor_value": 423988,
            "vitor_value": v_uf["secoes_apuradas"],
            "difference": 423988 - int(v_uf["secoes_apuradas"]),
            "note": "Soma das UFs no patamar ~84,93%; horário de visibilidade difere entre coletores.",
        },
    ]
    write_csv(
        OUT / "phase3b_crosscheck.csv",
        cross,
        ["metric","arvor_value","vitor_value","difference","note"],
    )

    max_lag = arvor["divergencia_soma_ufs"]["maior_diferenca_visivel"]
    national_batch = {
        "sections": int(unlocked["d_st"]),
        "valid_votes": int(unlocked["d_vv"]),
        "flavio_votes": int(unlocked["d_flavio"]),
        "lula_votes": int(unlocked["d_lula"]),
        "flavio_pct_of_batch": float(unlocked["lote_pct_flavio"]),
        "lula_pct_of_batch": float(unlocked["lote_pct_lula"]),
    }

    general_gap = {
        "start_brt": gap["de_brt"],
        "end_brt": gap["ate_brt"],
        "minutes": gap["minutos"],
        "fetches_during_gap": gap["leituras_no_intervalo"],
        "ab_versions_during_gap": len(gap.get("versoes_de_andamento_ab_no_intervalo", [])),
    }

    summary = {
        "format": "tse-forensics-phase3b-external-timeline-v1",
        "sources": raw_meta,
        "source_status": (
            "capturas independentes/derivadas de respostas públicas do TSE; "
            "evidência temporal secundária, não artefato oficial assinado"
        ),
        "independent_crosscheck_all_zero": all(int(x["difference"]) == 0 for x in cross),
        "presidential_national_freeze": {
            "start_brt": f2["de_brt"],
            "end_brt": f2["ate_brt"],
            "minutes": f2["minutos"],
            "sections_start": f2["st_de"],
            "sections_end": f2["st_ate"],
            "http_reads": f2["leituras_no_intervalo"],
        },
        "maximum_visible_national_vs_uf_lag": max_lag,
        "unlock_batch": national_batch,
        "general_result_generation_gap": general_gap,
        "phase_segmentation": phases,
        "vitor_observations": vitor.get("observacoes", []),
        "vitor_history": vitor_hist,
        "interpretation": [
            "A defasagem do EA20 nacional de Presidente é reproduzida por duas capturas independentes.",
            "Antes da lacuna geral, os arquivos de UF/monitoramento avançavam enquanto o nacional de Presidente permanecia atrás.",
            "Entre 19:32:47 e 20:01:55 há evidência independente de uma pausa mais ampla na geração de EA20 (-u) de todos os cargos/níveis; portanto a alegação de que Governador continuou normalmente durante toda a pausa presidencial precisa ser dividida por fases.",
            "O grande lote nacional posterior deve ser auditado contra os conjuntos estaduais/seções correspondentes; sua existência isoladamente não determina a causa da defasagem.",
        ],
    }
    (OUT / "phase3b_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("\nFASE 3B — timeline independente da defasagem presidencial")
    print(f"- fontes preservadas: {len(raw_meta)}")
    print(f"- cross-check independente: {'OK (todas diferenças zero)' if summary['independent_crosscheck_all_zero'] else 'DIVERGÊNCIAS'}")
    print(
        f"- maior defasagem visível: {max_lag['secoes']} seções "
        f"({max_lag['pp_do_total']:.2f}% do total), às {max_lag['hora_brt']}"
    )
    print(
        f"- lote do destravamento: {national_batch['sections']} seções · "
        f"{national_batch['valid_votes']:,} válidos"
    )
    print(
        f"- pausa geral EA20 (-u): {general_gap['start_brt']} -> "
        f"{general_gap['end_brt']} ({general_gap['minutes']:.2f} min)"
    )
    print(f"- resumo: {OUT / 'phase3b_summary.json'}")
    print(f"- timeline: {OUT / 'phase3b_lag_by_minute.csv'}")
    print(f"- fases: {OUT / 'phase3b_phases.csv'}")
    print(f"- cross-check: {OUT / 'phase3b_crosscheck.csv'}")


if __name__ == "__main__":
    main()
