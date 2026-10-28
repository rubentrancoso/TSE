#!/usr/bin/env python3
"""Fase 5P / menu T — previsao FORA DA AMOSTRA da cauda BWEB de 2026 (1T).

Treina exclusivamente nas secoes com DT_BU_RECEBIDO < 20:04:39 BRT.
Testa nas secoes recebidas em/apos 20:04:39, inclusive segunda parte
do minuto 20:04, respeitando segundos exatos de cada BU.

Compara (i) baseline BR, (ii) UF pre-corte, (iii) municipio pre-corte
com shrinkage determinado ANTES de examinar a cauda e (iv) perfil
municipal FINAL como referencia circular / vazamento, NAO previsao.

Os resultados EA20 (PUBLICACAO) e BWEB (RECEBIMENTO) nao sao a mesma
cronologia: os valores por segmento NAO devem ser igualados.
Somente CSV e manifestos H/M, e a Fase S; nao abre ZIP/SQLite/rede/2022.
"""
from __future__ import annotations
from collections import Counter, defaultdict
import argparse
import json
import math
from pathlib import Path

from urnas import root_path
from reconcile_stream import sha256
from analyze_operational_curve_2026 import (
    BASE, CUT, NATIONAL, atomic_csv, atomic_json, ea20_rows,
    load_sources, read_receipt_data, stamp,
)

VERSION="phase5p-out-of-sample-geography-2026-v1"
PRIOR_VOTES=1000  # fixed shrinkage votes, independent of post-cut outcomes
MIN_POST_BATCH=5000
MIN_MUNICIPAL_POST=2000
MODELS=("BR_pre","UF_pre","MUNICIPIO_pre","MUNICIPIO_final_IN_SAMPLE")
COLUMNS=("brt_minute","d_valid","d_lula","d_flavio",
         "cum_post_valid","cum_post_lula","cum_post_flavio",
         "real_batch_lula_pct","real_cum_post_lula_pct",
         "real_cum_post_flavio_pct",
         "br_pre_batch_lula_pct","uf_pre_batch_lula_pct",
         "municipio_pre_batch_lula_pct","municipio_final_batch_lula_pct",
         "br_pre_cum_lula_pct","uf_pre_cum_lula_pct",
         "municipio_pre_cum_lula_pct","municipio_final_cum_lula_pct",
         "br_pre_cum_flavio_pct","uf_pre_cum_flavio_pct",
         "municipio_pre_cum_flavio_pct","municipio_final_cum_flavio_pct")
UF_FIELDS=("UF","pre_valid","post_valid","post_lula","post_flavio",
           "pre_lula_pct","post_lula_pct","model_pre_lula_pct",
           "error_lula_pp","unseen_post_valid","unseen_post_pct")
MUN_FIELDS=("UF","municipio","pre_valid","post_valid","post_lula",
            "post_flavio","observed_post_lula_pct",
            "predicted_post_lula_pct","error_pp","pre_available")


def pct(v,n):
    return 100*v/n if n else None


def create_forecasts(split,post_minutes,mun_final,prior_votes=PRIOR_VOTES):
    """No rate ever uses post data except explicitly labelled oracle."""
    if prior_votes<=0:raise ValueError("Shrinkage prior must be >0")
    pre_uf=defaultdict(lambda:[0,0,0])
    global_pre=[0,0,0]
    for (uf,mu),entry in split.items():
        pre=entry[:3]
        for i in range(3):
            pre_uf[uf][i]+=pre[i]
            global_pre[i]+=pre[i]
    if global_pre[0]<=0:
        raise ValueError("No pre-cut ballots; cannot predict holdout")
    pre_br=(global_pre[1]/global_pre[0],global_pre[2]/global_pre[0])
    rates={}
    unseen=set()
    for key,stat in split.items():
        uf=key[0]
        a=stat[:3]
        u=pre_uf[uf]
        if u[0]>0:
            uf_rate=(u[1]/u[0],u[2]/u[0])
        else:
            uf_rate=pre_br
        if a[0]<=0 and sum(stat[3:])>0:unseen.add(key)
        mu_rate=(
           (a[1]+prior_votes*uf_rate[0])/(a[0]+prior_votes),
           (a[2]+prior_votes*uf_rate[1])/(a[0]+prior_votes))
        final=mun_final[key]
        oracle=(final[1]/final[0],final[2]/final[0]) if final[0] else uf_rate
        rates[key]={"BR_pre":pre_br,"UF_pre":uf_rate,
                    "MUNICIPIO_pre":mu_rate,
                    "MUNICIPIO_final_IN_SAMPLE":oracle}
    rows=[]
    cum=[0.,0.,0.]
    cumul_pred={model:[0.,0.] for model in MODELS}
    minute_evaluation={name:{"abs_lula_weighted":0.,"sq_lula_weighted":0.,
                             "weight":0.,"points":0} for name in MODELS}
    uf_performance=defaultdict(lambda:[0.,0.,0.,0.,0.])
    mu_performance=defaultdict(lambda:[0.,0.,0.,0.,0.])
    for when,by_mu in sorted(post_minutes.items()):
        batch=[0.,0.,0.]
        predicted={k:[0.,0.] for k in MODELS}
        for key,vals in by_mu.items():
            if key not in rates:raise RuntimeError("Unknown municipality in post-cut group")
            v,l,f=vals
            for i,x in enumerate(vals):batch[i]+=x
            for model in MODELS:
                rate=rates[key][model]
                predicted[model][0]+=v*rate[0]
                predicted[model][1]+=v*rate[1]
            agg=uf_performance[key[0]]
            agg[0]+=v;agg[1]+=l;agg[2]+=f
            agg[3]+=v*rates[key]["MUNICIPIO_pre"][0]
            if key in unseen:agg[4]+=v
            aggregate=mu_performance[key]
            aggregate[0]+=v;aggregate[1]+=l;aggregate[2]+=f
            aggregate[3]+=v*rates[key]["MUNICIPIO_pre"][0]
            if key in unseen:aggregate[4]+=v
        if batch[0]<=0:continue
        for i,x in enumerate(batch):cum[i]+=x
        for model in MODELS:
            for i in range(2):cumul_pred[model][i]+=predicted[model][i]
            if batch[0]>=MIN_POST_BATCH:
                error=100*(batch[1]-predicted[model][0])/batch[0]
                metrics=minute_evaluation[model]
                metrics["points"]+=1
                metrics["weight"]+=batch[0]
                metrics["abs_lula_weighted"]+=batch[0]*abs(error)
                metrics["sq_lula_weighted"]+=batch[0]*error*error
        r={"brt_minute":when,
           "d_valid":round(batch[0]),"d_lula":round(batch[1]),
           "d_flavio":round(batch[2]),
           "cum_post_valid":round(cum[0]),"cum_post_lula":round(cum[1]),
           "cum_post_flavio":round(cum[2]),
           "real_batch_lula_pct":pct(batch[1],batch[0]),
           "real_cum_post_lula_pct":pct(cum[1],cum[0]),
           "real_cum_post_flavio_pct":pct(cum[2],cum[0])}
        for prefix,model in (("br_pre","BR_pre"),
                              ("uf_pre","UF_pre"),
                              ("municipio_pre","MUNICIPIO_pre"),
                              ("municipio_final","MUNICIPIO_final_IN_SAMPLE")):
            r[prefix+"_batch_lula_pct"]=pct(predicted[model][0],batch[0])
            r[prefix+"_cum_lula_pct"]=pct(cumul_pred[model][0],cum[0])
            r[prefix+"_cum_flavio_pct"]=pct(cumul_pred[model][1],cum[0])
        rows.append(r)
    if not rows:raise ValueError("No post-cut BWEB minutes")
    total_by_minute=rows[-1]
    expected_post=[sum(x[3+i] for x in split.values()) for i in range(3)]
    if expected_post!=[total_by_minute["cum_post_valid"],total_by_minute["cum_post_lula"],total_by_minute["cum_post_flavio"]]:
        raise RuntimeError("Post-cut second-based tally differs from minutes")
    forecast_metrics={}
    for model in MODELS:
        evaluation=minute_evaluation[model]
        n=total_by_minute["cum_post_valid"]
        forecast_metrics[model]={
            "pred_lula_pct":pct(cumul_pred[model][0],n),
            "pred_flavio_pct":pct(cumul_pred[model][1],n),
            "actual_lula_pct":pct(cum[1],n),
            "actual_flavio_pct":pct(cum[2],n),
            "lula_final_error_pp":pct(cumul_pred[model][0]-cum[1],n),
            "flavio_final_error_pp":pct(cumul_pred[model][1]-cum[2],n),
            "weighted_minute_mae_lula_pp":evaluation["abs_lula_weighted"]/evaluation["weight"] if evaluation["weight"] else None,
            "weighted_minute_rmse_lula_pp":math.sqrt(evaluation["sq_lula_weighted"]/evaluation["weight"]) if evaluation["weight"] else None,
            "minute_bins_ge_5000_valids":evaluation["points"],
            "minute_valids_evaluated":int(evaluation["weight"])}
    ufs=[]
    for uf,v in sorted(uf_performance.items()):
        pre=pre_uf[uf]
        ufs.append({"UF":uf,"pre_valid":pre[0],"post_valid":int(v[0]),
            "post_lula":int(v[1]),"post_flavio":int(v[2]),
            "pre_lula_pct":pct(pre[1],pre[0]),
            "post_lula_pct":pct(v[1],v[0]),
            "model_pre_lula_pct":pct(v[3],v[0]),
            "error_lula_pp":pct(v[3]-v[1],v[0]),
            "unseen_post_valid":int(v[4]),
            "unseen_post_pct":pct(v[4],v[0])})
    municipalities=[]
    for (uf,mu),v in mu_performance.items():
        pre=split[(uf,mu)][0]
        municipalities.append({"UF":uf,"municipio":mu,
             "pre_valid":pre,"post_valid":int(v[0]),
             "post_lula":int(v[1]),"post_flavio":int(v[2]),
             "observed_post_lula_pct":pct(v[1],v[0]),
             "predicted_post_lula_pct":pct(v[3],v[0]),
             "error_pp":pct(v[3]-v[1],v[0]),
             "pre_available":pre>0})
    eligible=sorted((r for r in municipalities if r["post_valid"]>=MIN_MUNICIPAL_POST),
                    key=lambda r:-abs(r["error_pp"]))
    status={
        "training_pre_cut_valid":global_pre[0],
        "training_pre_cut_lula":global_pre[1],
        "training_pre_cut_flavio":global_pre[2],
        "holdout_post_cut_valid":int(cum[0]),
        "holdout_post_cut_lula":int(cum[1]),
        "holdout_post_cut_flavio":int(cum[2]),
        "municipalities_with_post_votes":len(municipalities),
        "municipalities_without_pre_cut_voting":sum(not r["pre_available"] for r in municipalities),
        "post_votes_from_unseen_municipalities":sum(int(v[4]) for v in uf_performance.values()),
        "unseen_municipality_post_vote_fraction":sum(v[4] for v in uf_performance.values())/cum[0],
        "shrinkage_prior_votes":prior_votes,
        "forecast_models":forecast_metrics,
        "largest_errors_municipalities_ge_2000_votes":eligible[:25]}
    return rows,ufs,municipalities,status


def run(root,repo=Path(__file__).resolve().parent):
    repo=repo.resolve()
    base=root/BASE
    h,m,sha_h,sha_m=load_sources(base)
    ea=ea20_rows(repo/NATIONAL)
    _,all_uf,mun_all,per_uf,hashes,split,minutes=read_receipt_data(
        base,h,m,include_holdout=True)
    rows,ufs,muns,stat=create_forecasts(split,minutes,mun_all)
    # Tie every post/pre sum to the previously validated S national totals.
    pre=stat["training_pre_cut_valid"]
    post=stat["holdout_post_cut_valid"]
    if pre+post!=119300788:
        raise RuntimeError("Before+after BWEB cutoff does not reconcile official valid votes")
    if (stat["training_pre_cut_lula"]+stat["holdout_post_cut_lula"]!=53879538
        or stat["training_pre_cut_flavio"]+stat["holdout_post_cut_flavio"]!=56104503):
        raise RuntimeError("Holdout candidate totals do not reconcile with M")
    if post!=sum(stats[3] for stats in per_uf.values()):
        raise RuntimeError("Holdout tally not equal to previous S aggregation")
    initial=next(x for x in ea if x["brt"]==CUT)
    last=ea[-1]
    public_delta={
       "ea20_cutoff_valid":initial["valid"],
       "ea20_added_valid_to_final":last["valid"]-initial["valid"],
       "bweb_received_after_cutoff_valid":post,
       "non_comparable_difference_valid":
           (last["valid"]-initial["valid"])-post,
       "warning":"A diferença subtrai votos publicados depois de 20:04 de votos BWEB RECEBIDOS depois de 20:04. Não representa votos desaparecidos, pois os eventos são diferentes."}
    filename=base/"phase5p_holdout_receipt_curve_2026.csv"
    ufs_path=base/"phase5p_holdout_by_uf_2026.csv"
    mun_path=base/"phase5p_holdout_by_municipality_2026.csv"
    atomic_csv(filename,COLUMNS,rows)
    atomic_csv(ufs_path,UF_FIELDS,ufs)
    atomic_csv(mun_path,MUN_FIELDS,muns)
    output={
      "version":VERSION,"status":"PREVISAO_BWEB_FORA_DA_AMOSTRA_1T_2026",
      "cutoff":"2026-10-04 20:04:39 BRT (segundos exatos)",
      "year":2026,"round":1,
      "data":stat,
      "EA20_versus_BWEB_different_events":public_delta,
      "source_sha256":{
         "EA20_national":sha256(repo/NATIONAL),
         "H_summary":sha_h,"M_summary":sha_m,
         "BU_uf":hashes},
      "output_files":{
          "post_cut_curve":{"path":str(filename),"sha256":sha256(filename)},
          "per_UF":{"path":str(ufs_path),"sha256":sha256(ufs_path)},
          "per_municipality":{"path":str(mun_path),"sha256":sha256(mun_path)}},
      "limits":[
          "Modelos BR_pre, UF_pre, MUNICIPIO_pre usam somente dados recebidos ANTES de 20:04:39",
          "MUNICIPIO_final_IN_SAMPLE usa dados FUTUROS; e auditoria de vazamento, jamais previsão",
          "Municipios sem votos pre-corte usam apenas a taxa pre-corte da UF; UF sem votos pre-corte usa taxa BR pre",
          "Pesos de municipio pre-corte sao shrinkados com 1000 validos de referencia da UF",
          "O erro e medido nas proporcoes do conjunto BWEB RECEBIDO apos o corte, nao na curva publicada EA20",
          "Nenhuma comparacao direta em instante comum e valida sem modelo independente de buffering",
          "BU de segundo turno, ZIP, SQLite, fontes online e dados de 2022 NAO utilizados"]}
    summary_path=base/"phase5p_holdout_geographic_curve_2026_summary.json"
    atomic_json(summary_path,output)
    print(json.dumps({"status":output["status"],
      "holdout":{k:stat[k] for k in ("training_pre_cut_valid",
                                  "holdout_post_cut_valid",
                                  "holdout_post_cut_lula",
                                  "holdout_post_cut_flavio",
                                  "municipalities_without_pre_cut_voting",
                                  "post_votes_from_unseen_municipalities")},
      "models":stat["forecast_models"],
      "EA20_comparison":public_delta,
      "worst_municipalities":stat["largest_errors_municipalities_ge_2000_votes"][:5],
      "report":str(summary_path)},indent=2,ensure_ascii=False),flush=True)
    return output

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root")
    args=parser.parse_args()
    run(root_path(args.root))
