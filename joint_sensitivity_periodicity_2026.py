#!/usr/bin/env python3
"""Fase 5I — teste global de periodicidade nos dados CORRIGIDOS de 2026.

Reutiliza SOMENTE o CSV por minuto da opcao M, SHA verificado.
Corrige a busca conjunta entre SEIS parametrizacoes e 144 frequencias.
Os nulos embaralham as participacoes dos lotes por QUARTIL, uma unica
permutacao conjunta para todas as parametrizacoes, e RECALCULAM as
medianas/residuos em cada repeticao. No controle por blocos, preserva
trechos consecutivos de cinco minutos com votos por lote.

Nulos sao simplificacoes: nao preservam estrutura espacial/UF nem o
vinculo exato entre votos inteiros e tamanho do lote. O valor-p obtido
NAO e probabilidade de fraude nem teste de autenticidade do BWEB.
Nao reler ZIPs ou BU, nao baixar, nao SQLite, NAO dados de 2022.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path

from analyze_periodicity_2026 import (
    Mulberry32, find_valleys, maximum_periodic_r2, median,
    permutations, prepare, templates
)
from sensitivity_bweb_periodicity_2026 import CONFIGS, read_verified_series
from reconcile_stream import sha256
from urnas import root_path

VERSION="phase5i-joint-six-configuration-periodicity-2026-v1"
SEED=20261027


def specifications(rows):
    """Amostras/periodogramas dependem SOMENTE dos eixos e do filtro de votos."""
    specs=[]
    for minvotes,window in CONFIGS:
        selected=[i for i,r in enumerate(rows) if r["d_valid"]>=minvotes]
        if len(selected)<30:
            specs.append({"minimum_votes":minvotes,"median_window":window,
                          "indices":selected,"patterns":None})
            continue
        shape=[rows[i] for i in selected]
        specs.append({"minimum_votes":minvotes,"median_window":window,
                      "indices":selected,"patterns":templates(shape)})
    return specs


def score_all(shares,specs):
    result=[]
    for spec in specs:
        indices=spec["indices"]
        if spec["patterns"] is None:
            result.append({"minimum_votes":spec["minimum_votes"],
                  "median_window":spec["median_window"],
                  "points":len(indices),"status":"AMOSTRA_INSUFICIENTE"})
            continue
        sampled=[shares[i] for i in indices]
        h=spec["median_window"]//2
        residual=[v-median(sampled[max(0,j-h):min(len(sampled),j+h+1)])
                  for j,v in enumerate(sampled)]
        peak=maximum_periodic_r2(residual,spec["patterns"])
        result.append({"minimum_votes":spec["minimum_votes"],
                       "median_window":spec["median_window"],
                       "points":len(indices),
                       "axis":peak["axis"],"period":peak["period"],
                       "r2":peak["r2"]})
    return result


def max_stat(scores):
    found=[r["r2"] for r in scores if "r2" in r]
    if not found:
        raise ValueError("Nenhuma configuracao com amostra suficiente")
    return max(found)


def quartile_parts(size):
    if size<4:
        raise ValueError("Poucos instantes para particionar quartis")
    parts=[[] for _ in range(4)]
    for i in range(size):
        parts[min(3,4*i//size)].append(i)
    return parts


def simulate(shares,parts,rng,mode):
    """Uma permutacao COMPARTILHADA por todas as seis configuracoes."""
    return permutations(shares,parts,rng,mode)


def compute(rows,repetitions=300,seed=SEED):
    if repetitions<100:
        raise ValueError("Pelo menos 100 permutacoes para calibracao")
    shares=[float(r["batch_share_pct"]) for r in rows]
    specs=specifications(rows)
    observed=score_all(shares,specs)
    observed_max=max_stat(observed)
    by_type={}
    rng=Mulberry32(seed)
    parts=quartile_parts(len(rows))
    for mode in ("individual","blocks"):
        exceeds=0
        exceed_selected=0
        null_maxima=[]
        for j in range(repetitions):
            candidate=simulate(shares,parts,rng,mode)
            null_scores=score_all(candidate,specs)
            null_peak=max_stat(null_scores)
            null_maxima.append(null_peak)
            if null_peak>=observed_max:
                exceeds+=1
            # Comparacao do mesmo vencedor, sem varrer a grade na replicacao.
            winning=max(observed,key=lambda r:r.get("r2",-1))
            idx=next(i for i,r in enumerate(observed)
                     if r is winning)
            if null_scores[idx].get("r2",-1)>=winning["r2"]:
                exceed_selected+=1
            if (j+1)%100==0:
                print(f"[NULO {mode}] {j+1}/{repetitions} "
                      f"excedencias globais={exceeds}",flush=True)
        ordered=sorted(null_maxima)
        by_type[mode]={
            "p_global_grid_and_frequencies":round((exceeds+1)/(repetitions+1),8),
            "null_exceedances_global":exceeds,
            "p_postselected_configuration_uncorrected":round(
                 (exceed_selected+1)/(repetitions+1),8),
            "max_r2_null_median":round(ordered[len(ordered)//2],8),
            "max_r2_null_95th":round(ordered[min(repetitions-1,int(.95*repetitions))],8),
            "max_r2_null_99th":round(ordered[min(repetitions-1,int(.99*repetitions))],8)
        }
    return {
        "version":VERSION,"status":"TESTE_GLOBAL_EXPLORATORIO_2026",
        "scope":"Presidente, turno 1 2026, BWEB por MINUTO com nulos tecnicos corrigidos",
        "minutes":len(rows),"total_selected_configs":len(CONFIGS),
        "searched_periods_per_configuration":144,
        "simulations_each_null":repetitions,"seed":seed,
        "observed_per_configuration":[{
            k:round(v,8) if isinstance(v,float) else v
            for k,v in obj.items()} for obj in observed],
        "observed_global_max_r2":round(observed_max,8),
        "winning_configuration":max(observed,key=lambda r:r.get("r2",-1)),
        "joint_null_tests":by_type,
        "method":[
            "Configuracoes predefinidas da Fase I, nao selecionadas pelo melhor p desta rodada",
            "O maximo de R2 cobre todas as 6 configuracoes e seus 144 periodos",
            "Em cada nulidade uma UNICA permutacao das participacoes cobre todas as configuracoes",
            "Participacoes embaralhadas nos quartis cronologicos originais",
            "Medianas e residuos sao RECALCULADOS em cada serie embaralhada",
            "P global=(1+excedencias do maximo observado)/(1+numero de repeticoes)",
            "Controle em blocos reordena trechos de ate cinco instantes, sem destruir ordem interna"
        ],
        "limitations":[
            "Periodograma em minutos, NAO ordem individual das urnas empatadas por segundo",
            "Nao preserva padrao espacial UF/municipio ou volume-condicionado da participacao por minuto",
            "Sob nulo, a participacao e permutada independentemente do volume: nao sao novos votos inteiros artificiais",
            "Comparacoes anteriores que motivaram o teste nao podem ser tratadas como confirmacao pre-registrada",
            "O maximo sobre R2 de tamanhos amostrais distintos e calibrado por mesmo nulo conjunto",
            "A correcao abrange 6 parametrizacoes e 144 periodos em cada; nao abrange todas as analises anteriores",
            "P global nao e probabilidade de fraude/regularidade da apuracao"
        ]}


def atomic_json(path,result):
    tmp=Path(str(path)+".part")
    try:
        with tmp.open("w",encoding="utf-8") as f:
            json.dump(result,f,ensure_ascii=False,indent=2)
            f.write("\n");f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if tmp.exists():tmp.unlink()


def run(root,repetitions=300,seed=SEED):
    folder=root/"analysis"/"periodicidade_bweb_2026"
    rows,manifest=read_verified_series(folder,corrected=True)
    outcome=compute(rows,repetitions,seed)
    outcome["source_sha256"]=manifest["corrected_minutes_sha256"]
    former=folder/"phase5d_sensitivity_corrected_2026_summary.json"
    if former.is_file():
        earlier=json.loads(former.read_text(encoding="utf-8"))
        if earlier.get("source_2026_minute_series_sha256")!=outcome["source_sha256"]:
            raise RuntimeError("Referencia I nao coincide com serie corrigida M")
        outcome["phase_i_sha256"]=sha256(former)
        validated=[]
        for old,updated in zip(earlier["results"],outcome["observed_per_configuration"]):
            if (old["minimum_votes"]!=updated["minimum_votes"] or
                old["median_window"]!=updated["median_window"] or
                abs(old["periodicity"]["r2"]-updated["r2"])>2e-7):
                raise RuntimeError("Valor R2 diverge da Fase I em configuracao "+repr(old))
            validated.append(True)
        outcome["reproduced_previous_phase_i_configs"]=len(validated)
    output=folder/"phase5i_joint_periodicity_2026_summary.json"
    atomic_json(output,outcome)
    print(json.dumps({
        "status":outcome["status"],
        "observed_best":outcome["winning_configuration"],
        "global_corrected_p":outcome["joint_null_tests"],
        "source_sha256":outcome["source_sha256"],
        "output":str(output)
    },ensure_ascii=False,indent=2),flush=True)
    return outcome


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root")
    parser.add_argument("--permutacoes",type=int,default=300)
    parser.add_argument("--semente",type=int,default=SEED)
    args=parser.parse_args()
    run(root_path(args.root),args.permutacoes,args.semente)
