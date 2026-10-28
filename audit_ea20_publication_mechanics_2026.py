#!/usr/bin/env python3
"""Fase 5S / opção X — mecanismos observáveis da curva publicada EA20 2026.

Testa se a linearidade cumulativa no eixo de seções pode surgir apenas
de (i) volumes físicos efetivamente publicados por atualização e
(ii) proporção constante dos lotes finais. Compara com uma previsão
sem lookahead treinada APENAS nos dez primeiros incrementos pós-corte.
Gera diagnóstico por lote e grupos consecutivos de volumes semelhantes.
O modelo com proporção FINAL da cauda é ORACULO e não prova causalidade.
Somente EA20 nacional PRIMEIRO TURNO já versionado; não usa BWEB nem ZIP.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from analyze_operational_curve_2026 import (
    BASE, CUT, NATIONAL, atomic_csv, atomic_json, ea20_rows, stamp, line_fit
)
from reconcile_stream import sha256
from urnas import root_path

VERSION = "phase5s-ea20-publication-mechanics-2026-v1"
EARLY_TRAIN_UPDATES = 10
POST_EXPECTED = 153
BATCH_COLUMNS = (
    "brt", "d_seconds", "d_sections", "d_valid", "d_lula", "d_flavio",
    "batch_lula_pct", "batch_flavio_pct", "cum_sections",
    "cum_valid", "actual_cum_lula_pct", "oracle_cum_lula_pct",
    "oracle_residual_pp", "early_forecast_cum_lula_pct",
    "early_forecast_residual_pp", "endpoint_line_target_lula_pct",
    "required_batch_lula_pct_for_endpoint_line",
    "deviation_batch_lula_votes_from_endpoint_line",
)
BLOCK_COLUMNS = (
    "block", "updates", "valid", "lula", "flavio", "d_sections",
    "first_brt", "last_brt", "lula_pct", "flavio_pct",
)


def safe_share(x, n):
    return 100 * x / n if n else None


def rmse(a, b):
    if len(a) != len(b) or not a:
        raise ValueError("Series de comprimentos diferentes ou vazias")
    return math.sqrt(sum((x-y)**2 for x,y in zip(a,b))/len(a))


def describe(ea, training_updates=EARLY_TRAIN_UPDATES, expected_post=None):
    rows=[r for r in ea if r["brt"]>=CUT]
    if expected_post is not None and len(rows)!=expected_post:
        raise RuntimeError("Numero inesperado de snapshots EA20 pos-corte")
    if len(rows)<training_updates+3 or training_updates<=0:
        raise ValueError("Poucos pontos para calibracao e validacao")
    if rows[0]["brt"]!=CUT:
        raise RuntimeError("O primeiro ponto deve ser corte exato do EA20")
    first=rows[0]
    last=rows[-1]
    total_valid=last["valid"]-first["valid"]
    total_lula=last["lula"]-first["lula"]
    total_flavio=last["flavio"]-first["flavio"]
    if total_valid<=0:
        raise ValueError("Nenhum voto adicionado")
    oracle=total_lula/total_valid
    anchor=rows[training_updates]
    train_v=anchor["valid"]-first["valid"]
    train_l=anchor["lula"]-first["lula"]
    train_f=anchor["flavio"]-first["flavio"]
    if train_v<=0:
        raise ValueError("Treino sem votos")
    pre_rate=train_l/train_v

    actual=[100*r["lula"]/r["valid"] for r in rows]
    fixed=[safe_share(first["lula"]+oracle*(r["valid"]-first["valid"]), r["valid"])
           for r in rows]
    section_x=[r["st"] for r in rows]
    valid_x=[r["valid"] for r in rows]
    clock_x=[(stamp(r["brt"])-stamp(first["brt"])).total_seconds() for r in rows]
    fit={}
    for key, xx in (("sections",section_x),("valid",valid_x),("clock",clock_x)):
        fit[key]={"actual":line_fit(xx,actual), "constant_tail_oracle":line_fit(xx,fixed)}

    # Uma reta pelos dois extremos é diagnóstico geométrico, não previsão.
    first_share=first["lula"]/first["valid"]
    final_share=last["lula"]/last["valid"]
    b=(final_share-first_share)/(last["st"]-first["st"])
    def ideal(r):
        return first_share + b*(r["st"]-first["st"])

    batches=[]
    previous=first
    for i,current in enumerate(rows[1:],start=1):
        dv=current["valid"]-previous["valid"]
        dl=current["lula"]-previous["lula"]
        df=current["flavio"]-previous["flavio"]
        ds=current["st"]-previous["st"]
        if dv<=0 or dl<0 or df<0 or ds<=0 or dl+df>dv:
            raise RuntimeError("Incrementos EA20 nao fisicos em "+current["brt"])
        if current["d_valid"]!=dv or current["d_lula"]!=dl or current["d_flavio"]!=df:
            raise RuntimeError("Serie EA20 de incrementos internos inconsistente")
        seconds=(stamp(current["brt"])-stamp(previous["brt"])).total_seconds()
        if seconds<=0:
            raise RuntimeError("Cronologia EA20 nao monotona")
        expected_from_line=ideal(current)*current["valid"]-ideal(previous)*previous["valid"]
        predicted_lula=first["lula"]+oracle*(current["valid"]-first["valid"])
        early_pred=(anchor["lula"]+pre_rate*(current["valid"]-anchor["valid"])
                    if i>=training_updates else None)
        batches.append(dict(
            brt=current["brt"],d_seconds=int(seconds),d_sections=ds,
            d_valid=dv,d_lula=dl,d_flavio=df,
            batch_lula_pct=safe_share(dl,dv),batch_flavio_pct=safe_share(df,dv),
            cum_sections=current["st"],cum_valid=current["valid"],
            actual_cum_lula_pct=safe_share(current["lula"],current["valid"]),
            oracle_cum_lula_pct=safe_share(predicted_lula,current["valid"]),
            oracle_residual_pp=safe_share(current["lula"]-predicted_lula,current["valid"]),
            early_forecast_cum_lula_pct=safe_share(early_pred,current["valid"])
                if early_pred is not None else None,
            early_forecast_residual_pp=safe_share(current["lula"]-early_pred,current["valid"])
                if early_pred is not None else None,
            endpoint_line_target_lula_pct=100*ideal(current),
            required_batch_lula_pct_for_endpoint_line=safe_share(expected_from_line,dv),
            deviation_batch_lula_votes_from_endpoint_line=dl-expected_from_line,
        ))
        previous=current

    # Blocos inteiros de atualizacoes, volumes aproximados de 1/4 da cauda.
    # Nao repartimos um lote publicado em duas partes hipoteticas.
    blocks=[]
    buffer=[]
    for r in batches:
        buffer.append(r)
        if sum(x["d_valid"] for x in buffer)>=total_valid/4 and len(blocks)<3:
            blocks.append(buffer)
            buffer=[]
    blocks.append(buffer)
    if any(not block for block in blocks):
        raise RuntimeError("Blocos vazios")
    block_rows=[]
    for i,block in enumerate(blocks,start=1):
        valid=sum(r["d_valid"] for r in block)
        lula=sum(r["d_lula"] for r in block)
        flavio=sum(r["d_flavio"] for r in block)
        block_rows.append(dict(
            block=i,updates=len(block),valid=valid,lula=lula,flavio=flavio,
            d_sections=sum(r["d_sections"] for r in block),
            first_brt=block[0]["brt"],last_brt=block[-1]["brt"],
            lula_pct=safe_share(lula,valid),flavio_pct=safe_share(flavio,valid)))

    horizon=rows[training_updates:]
    predicted_later=[
        safe_share(anchor["lula"]+pre_rate*(r["valid"]-anchor["valid"]),r["valid"])
        for r in horizon]
    actual_later=[safe_share(r["lula"],r["valid"]) for r in horizon]
    feasible=[r for r in batches
              if r["required_batch_lula_pct_for_endpoint_line"]<0
              or r["required_batch_lula_pct_for_endpoint_line"]>100]
    last20=batches[-20:]
    last20_valid=sum(x["d_valid"] for x in last20)
    result={
        "version":VERSION,"status":"MECANISMO_DA_CURVA_PUBLICADA_EA20_2026",
        "round":1,"year":2026,"cutoff_brt":CUT,"post_points":len(rows),
        "post_transitions":len(batches),
        "at_cutoff":{"sections":first["st"],"valid":first["valid"],
                     "lula":first["lula"],"flavio":first["flavio"]},
        "at_final":{"sections":last["st"],"valid":last["valid"],
                    "lula":last["lula"],"flavio":last["flavio"]},
        "published_tail":{"valid":total_valid,"lula":total_lula,"flavio":total_flavio,
            "lula_pct":safe_share(total_lula,total_valid),
            "flavio_pct":safe_share(total_flavio,total_valid)},
        "fits":fit,
        "constant_tail_oracle":{
            "name":"ORACULO_COM_TAXA_FINAL_DA_CAUDA_IN_SAMPLE",
            "vote_rate_lula_pct":100*oracle,
            "rmse_actual_minus_oracle_cumulative_pp":rmse(actual,fixed),
            "max_abs_actual_minus_oracle_cumulative_pp":max(abs(a-b) for a,b in zip(actual,fixed)),
            "warning":"Usa taxa de votos final FUTURA, nao explica causalidade ou recepcao BWEB.",
        },
        "early_ten_update_training":{
            "updates":training_updates,"training_valid":train_v,
            "training_fraction_tail":train_v/total_valid,
            "training_lula_pct":safe_share(train_l,train_v),
            "training_flavio_pct":safe_share(train_f,train_v),
            "after_training_points":len(horizon),
            "forecast_final_lula_pct":predicted_later[-1],
            "actual_final_lula_pct":actual_later[-1],
            "forecast_final_error_pp":predicted_later[-1]-actual_later[-1],
            "forecast_rmse_lula_cumulative_pp":rmse(predicted_later,actual_later),
            "warning":"Taxa treinada com primeiros 10 lotes apos o corte; sem usar os votos de teste.",
        },
        "block_approx_equal_valids":block_rows,
        "endpoint_line_diagnostic":{
            "unphysical_required_batch_shares":len(feasible),
            "unphysical_first_examples":feasible[:5],
            "note":"Uma reta entre o ponto inicial e final permite calcular taxa necessaria por lote usando V e st efetivamente publicados. E diagnostico retrospectivo.",
        },
        "last_20_updates":{"valid":last20_valid,"fraction_of_tail":last20_valid/total_valid,
                           "lula_pct":safe_share(sum(r["d_lula"] for r in last20),last20_valid)},
        "limitations":[
            "O controle de taxa final e circular; R2 alto deste controle nao prova que lotes reais tiveram composicao constante.",
            "O treino dos primeiros 10 updates e apenas uma previsao descritiva condicional aos volumes posteriormente publicados.",
            "Numero de secoes e numero de validos publicados sao eixos altamente relacionados; nao equivalem ao relogio.",
            "Os lotes EA20 sao diferencas de snapshots publicados, nao pacotes com identidade individual de BU.",
            "Os dados aqui sao os snapshots EA20 capturados no repositorio; cobertura das capturas nao e log interno TSE.",
            "BWEB recebido e EA20 publicado sao eventos diferentes e nao foram alinhados por minuto.",
            "Nenhuma observacao desta fase isoladamente confirma nem descarta adulteracao eleitoral.",
            "Sem ZIP, SQLite, rede, 2022 ou segundo turno."
        ]
    }
    return batches,block_rows,result


def run(root, repo=Path(__file__).resolve().parent):
    repo=repo.resolve()
    source=repo/NATIONAL
    if not source.is_file():
        raise RuntimeError("Falta CSV versionado EA20: "+str(source))
    ea=ea20_rows(source)
    batches,blocks,summary=describe(ea,expected_post=POST_EXPECTED)
    if (summary["published_tail"]["valid"]!=18809656
        or summary["post_transitions"]!=152):
        raise RuntimeError("Lote EA20 diferente da série preservada/certificada")
    base=root/BASE
    filenames={
        "batches":("phase5s_ea20_batch_mechanics_2026.csv",BATCH_COLUMNS,batches),
        "blocks":("phase5s_ea20_equal_volume_blocks_2026.csv",BLOCK_COLUMNS,blocks),
    }
    summary["source_sha256"]={"EA20_national":sha256(source)}
    summary["output_files"]={}
    for key,(name,columns,items) in filenames.items():
        destination=base/name
        atomic_csv(destination,columns,items)
        summary["output_files"][key]={"path":str(destination),
                                       "sha256":sha256(destination),
                                       "rows":len(items)}
    target=base/"phase5s_ea20_publication_mechanics_2026_summary.json"
    atomic_json(target,summary)
    print(json.dumps({
        "status":summary["status"],
        "post_transitions":summary["post_transitions"],
        "observed_r2_by_sections":summary["fits"]["sections"]["actual"]["r2"],
        "constant_oracle_r2_by_sections":summary["fits"]["sections"]["constant_tail_oracle"]["r2"],
        "observed_r2_by_valids":summary["fits"]["valid"]["actual"]["r2"],
        "oracle_rmse_pp":summary["constant_tail_oracle"]["rmse_actual_minus_oracle_cumulative_pp"],
        "first_10_update_forecast":summary["early_ten_update_training"],
        "blocks":summary["block_approx_equal_valids"],
        "last_20_updates":summary["last_20_updates"],
        "report":str(target),
    },ensure_ascii=False,indent=2),flush=True)
    return summary


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root")
    args=p.parse_args()
    run(root_path(args.root))
