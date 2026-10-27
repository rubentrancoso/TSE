#!/usr/bin/env python3
"""Fase 5D — sensibilidade da periodicidade no BWEB 2026, SOMENTE cache local.

Nao abre ZIPs, nao baixa, nao acessa SQLite, nao importa dados de 2022.
Reusa a serie por minuto e o SHA-256 da Fase 5C.
Varia volume minimo de votos, mediana local e profundidade de vales.
Teste exploratorio de robustez: nao interpretar menor p obtido como
confirmacao sem correcao adicional pela grade de parametros.
"""
from __future__ import annotations
import argparse
import csv
import json
import os
from pathlib import Path

from analyze_periodicity_2026 import (
    prepare, templates, maximum_periodic_r2,
    Mulberry32, permutations, find_valleys
)
from reconcile_stream import sha256
from urnas import root_path

VERSION="phase5d-periodicity-2026-sensitivity-v2"
# Definidos ANTES de analisar os resultados da fase 5D.
CONFIGS=((1000,15),(5000,9),(5000,21),
         (10000,9),(10000,21),(20000,15))
THRESHOLDS=(4.0,8.0,12.0)


def read_verified_series(folder,corrected=False):
    if corrected:
        previous=json.loads((folder/"phase5h_corrected_periodicity_2026_summary.json").read_text("utf-8"))
        if previous.get("status")!="VALIDOS_PRESIDENCIAIS_CORRIGIDOS" or previous.get("difference_valid_vs_official")!=0:
            raise RuntimeError("A fase M nao conciliou os validos")
        trace=folder/"phase5h_minute_corrected_2026.csv"
        digest=previous.get("corrected_minutes_sha256")
        n_expected=previous["distinct_minutes"]
        sections_expected=previous["initial_sections"]
        valid_expected=previous["corrected_totals"]["valid"]
    else:
        previous=json.loads((folder/"phase5c_summary.json").read_text("utf-8"))
        if previous.get("status")!="APURACAO_POR_MINUTO_ANALISADA":
            raise RuntimeError("Fase 5C nao autorizou teste temporal")
        trace=folder/"serie_2026_por_minuto.csv"
        digest=previous.get("timeline_sha256")
        n_expected=previous["minute_bins"]
        sections_expected=previous["match_and_coverage"]["sections_timestamped"]
        valid_expected=previous["match_and_coverage"]["total_in_timed_sections"]["valid"]
    if not trace.is_file() or sha256(trace)!=digest:
        raise RuntimeError("Serie por minuto danificada ou nao verificada")
    rows=[]
    with trace.open(encoding="utf-8-sig",newline="") as f:
        for item in csv.DictReader(f,delimiter=";"):
            for field in ("sections","minutes","d_sections","d_valid",
                          "d_flavio","d_lula","batch_share_pct",
                          "cum_share_pct"):
                item[field]=(float(item[field]) if field in
                    ("minutes","batch_share_pct","cum_share_pct")
                    else int(item[field]))
            rows.append(item)
    if len(rows)!=n_expected or not rows:
        raise RuntimeError("Quantidade de minutos alterada")
    last_sections=rows[-1]["sections"]
    count=sum(r["d_sections"] for r in rows)
    voters=sum(r["d_valid"] for r in rows)
    if (count!=last_sections or
        count!=sections_expected or
        voters!=valid_expected or
        any(x["d_valid"]<0 for x in rows)):
        raise RuntimeError("Contagens da serie nao batem com Fase 5C")
    return rows,previous


def permute_test(rows,replications,seed):
    residual=[row["residual_pp"] for row in rows]
    pats=templates(rows)
    peak=maximum_periodic_r2(residual,pats)
    segments=[[] for _ in range(4)]
    for i in range(len(residual)):
        segments[min(3,4*i//len(residual))].append(i)
    rng=Mulberry32(seed)
    hits={"individual":0,"blocks":0}
    for _ in range(replications):
        for mode in hits:
            candidate=permutations(residual,segments,rng,mode)
            hits[mode]+=maximum_periodic_r2(candidate,pats)["r2"]>=peak["r2"]
    return {
        "axis":peak["axis"],"period":round(peak["period"],6),
        "r2":round(peak["r2"],8),
        "p_empirical_individual":round((hits["individual"]+1)/(replications+1),7),
        "p_empirical_blocks5":round((hits["blocks"]+1)/(replications+1),7)
    }


def describe_valleys(rows,threshold):
    valleys=find_valleys(rows,threshold)
    # Reportar posicoes e proeminencia para verificar repeticoes reais,
    # evitando classificar automaticamente padrao politico.
    sorted_by_position=sorted(valleys,key=lambda v:v["sections"])
    spacings=[b["sections"]-a["sections"]
              for a,b in zip(sorted_by_position,sorted_by_position[1:])]
    return {
        "threshold_pp":threshold,
        "valleys":len(valleys),
        "min_section_gap":min(spacings) if spacings else None,
        "max_section_gap":max(spacings) if spacings else None,
        "positions":sorted_by_position
    }


def atomic_json(path,payload):
    tmp=Path(str(path)+".part")
    try:
        with tmp.open("w",encoding="utf-8") as f:
            json.dump(payload,f,ensure_ascii=False,indent=2)
            f.write("\n");f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if tmp.exists():tmp.unlink()


def run(root,permutations_count=300,seed=20261027,corrected=False):
    if permutations_count<100:
        raise ValueError("Minimo de 100 permutacoes")
    folder=root/"analysis"/"periodicidade_bweb_2026"
    data,report=read_verified_series(folder,corrected=corrected)
    result=[]
    for volume,window in CONFIGS:
        try:
            selected=prepare(data,minimum_votes=volume,width=window)
            periodic=permute_test(selected,permutations_count,seed)
            entry={"minimum_votes":volume,"median_window":window,
                   "minutes_selected":len(selected),
                   "periodicity":periodic,
                   "valley_sensitivity":{
                      str(int(level)):describe_valleys(selected,level)
                      for level in THRESHOLDS}}
            print(f"[SENSIBILIDADE] votos>={volume:,} mediana={window}: "
                  f"n={len(selected)}, R2={periodic['r2']:.4f}, "
                  f"p(indiv)={periodic['p_empirical_individual']:.4f}, "
                  f"p(blocos)={periodic['p_empirical_blocks5']:.4f}, "
                  f"vales(8pp)={entry['valley_sensitivity']['8']['valleys']}",
                  flush=True)
        except ValueError as exc:
            entry={"minimum_votes":volume,"median_window":window,
                   "status":"NAO_EXECUTADO","reason":str(exc)}
        result.append(entry)
    summary={"version":VERSION,"status":"EXPLORATORIO_CONCLUIDO",
             "source_mode":"CORRIGIDO_NR28" if corrected else "ORIGINAL_H",
             "source_2026_minute_series_sha256":report[
                "corrected_minutes_sha256" if corrected else "timeline_sha256"],
             "sections":report["initial_sections"] if corrected else report["match_and_coverage"]["sections_timestamped"],
             "minute_bins":report["distinct_minutes"] if corrected else report["minute_bins"],
             "seed":seed,"null_simulations_each":permutations_count,
             "parameter_grid":len(CONFIGS),
             "results":result,
             "limitations":[
              "Muitos testes sobre a MESMA serie: escolher menor p da grade sem ajuste constitui p-hacking",
              "Nenhuma configuracao reconstroi ordem individual das secoes empatadas por minuto",
              "Nulos por quartil nao preservam toda dependencia geografica do eleitorado",
              "Este teste parte dos dados oficiais publicados, nao audita BU impresso independente",
              "Resultado nao constitui probabilidade de fraude ou inocencia",
              "Sem microdados de 2022, sem rede, sem SQLite, sem releitura de ZIPs BU"]}
    path=folder/("phase5d_sensitivity_corrected_2026_summary.json" if corrected else "phase5d_sensitivity_2026_summary.json")
    atomic_json(path,summary)
    print("FASE 5D CONCLUIDA, relatorio:",path,flush=True)
    return summary


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root")
    parser.add_argument("--permutacoes",type=int,default=300)
    parser.add_argument("--corrigido",action="store_true",help="Usar denominadores da opcao M, sem reler ZIP")
    args=parser.parse_args()
    run(root_path(args.root),args.permutacoes,corrected=args.corrigido)
