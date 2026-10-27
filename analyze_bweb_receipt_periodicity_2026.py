#!/usr/bin/env python3
"""Fase 5C — teste dos vales de 2026 usando um BU PRESIDENCIAL por secao.

SOMENTE dados 2026. Le shards locais gerados de BWEB com
DT_BU_RECEBIDO e votos de cada secao, todos SHA-256 auditados.
Ordena MINUTOS de recebimento, nunca inventa ordem dos BUs empatados.
Mede vales e periodicidade em dois eixos: tempo e BU acumulados.
Nao abre SQLite, nao baixa arquivos e nao usa dados de 2022.
"""
from __future__ import annotations
import argparse
from collections import defaultdict, Counter
import csv
import hashlib
import json
import os
from pathlib import Path

from analyze_periodicity_2026 import (
    prepare, templates, maximum_periodic_r2,
    Mulberry32, permutations, find_valleys
)
from reconcile_stream import sha256
from urnas import root_path
from extract_bweb_received_2026 import VERSION as INPUT_VERSION

VERSION="phase5c-bu-reception-periodicity-2026-v1"
FINAL={"valid":119300788,"flavio":56104503,"lula":53879538}


def atomic_json(path,details):
    tmp=Path(str(path)+".part")
    try:
        with tmp.open("w",encoding="utf-8") as f:
            json.dump(details,f,ensure_ascii=False,indent=2)
            f.write("\n");f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if tmp.exists():tmp.unlink()


def save_csv(path,header,values):
    tmp=Path(str(path)+".part")
    try:
        with tmp.open("w",encoding="utf-8",newline="") as f:
            w=csv.DictWriter(f,fieldnames=header,delimiter=";",
                             extrasaction="ignore",lineterminator="\n")
            w.writeheader();w.writerows(values)
            f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if tmp.exists():tmp.unlink()


def read_sections(base):
    provenance=base/"summary.json"
    if not provenance.is_file():
        raise RuntimeError("Primeiro execute extract_bweb_received_2026.py; nada sera baixado")
    source=json.loads(provenance.read_text("utf-8"))
    if source["version"]!=INPUT_VERSION:
        raise RuntimeError("Origem BWEB de versao diferente")
    records=source["ufs"]
    complete={}
    bucket=defaultdict(lambda:[0,0,0,0])
    stats=Counter()
    uniques=set()
    times_by_uf=defaultdict(list)
    total=Counter()
    for uf,info in sorted(records.items()):
        path=base/f"received-{uf}.csv"
        if not path.is_file() or sha256(path)!=info["shard_sha256"]:
            raise RuntimeError("SHA de secao recebido divergente: "+str(path))
        count=0
        with path.open(encoding="utf-8-sig",newline="") as f:
            for row in csv.DictReader(f,delimiter=";"):
                ident=tuple(row[x] for x in ("UF","municipio","zona","secao","turno"))
                if ident in uniques:
                    raise RuntimeError("BU duplicado "+repr(ident))
                uniques.add(ident)
                if ident[0]!=uf or ident[4]!="1":
                    raise RuntimeError("UF/turno do BWEB divergente")
                minute=row["recebimento_minuto"]
                if not minute:
                    stats["sem_hora"]+=1
                    count+=1
                    continue
                if not (len(minute)==16 and minute[4]=="-" and minute[10]==" "):
                    raise RuntimeError("Minuto malformado: "+repr(minute))
                v,fv,lv=[int(row[col]) for col in
                    ("votos_pres_validos","votos_22","votos_13")]
                if v<0 or min(fv,lv)<0 or fv+lv>v:
                    raise RuntimeError("Votos inconsistentes "+repr(ident))
                values=bucket[minute]
                values[0]+=1;values[1]+=v;values[2]+=fv;values[3]+=lv
                stats["com_hora"]+=1
                times_by_uf[uf].append(minute)
                total["valid"]+=v;total["flavio"]+=fv;total["lula"]+=lv
                count+=1
        if count!=info["sections"]:
            raise RuntimeError("Contagem de secoes divergente do checkpoint "+uf)
        complete[uf]=count
        print(f"[JUNCAO {uf}] {count:,} BUs com arquivo BWEB SHA valido",flush=True)
    if len(complete)!=source["shard_count"]:
        raise RuntimeError("UFs nao coincidem com fonte")
    if len(uniques)!=source["sections"]:
        raise RuntimeError("Contagem total de secoes unica divergente")
    quality={}
    short=0
    for uf,minutes in times_by_uf.items():
        duration=(__import__("datetime").datetime.fromisoformat(max(minutes))-
                  __import__("datetime").datetime.fromisoformat(min(minutes))).total_seconds()/60
        short+=len(minutes) if duration<5 else 0
        quality[uf]={"minutes_min":min(minutes),"minutes_max":max(minutes),
                     "span_minutes":round(duration,2),
                     "sections":len(minutes),
                     "distinct_minutes":len(set(minutes))}
    return bucket,{"sections_total":len(uniques),
                   "sections_timestamped":stats["com_hora"],
                   "sections_no_time":stats["sem_hora"],
                   "per_uf_sections":complete,
                   "total_in_timed_sections":dict(total),
                   "total_compare_with_official":{
                       name:{"BU_with_time":int(total[name]),
                             "national_final":official,
                             "difference":int(total[name])-official}
                       for name,official in FINAL.items()},
                   "per_uf_receipt_window":quality,
                   "fraction_sections_in_UF_span_under_5min":
                      round(short/max(1,stats["com_hora"]),6)}


def minute_series(bucket):
    accumulated=[0,0,0,0]
    out=[]
    if not bucket:raise RuntimeError("Nao existe minuto com votos e horarios")
    from datetime import datetime
    start=datetime.fromisoformat(min(bucket))
    for minute in sorted(bucket):
        c,v,f,l=bucket[minute]
        before_v,before_f,before_l=accumulated[1:]
        for j,val in enumerate((c,v,f,l)):
            accumulated[j]+=val
        old=100*before_f/before_v if before_v else None
        new=100*accumulated[2]/accumulated[1] if accumulated[1] else None
        row={"brt":minute,"sections":accumulated[0],
             "minutes":(datetime.fromisoformat(minute)-start).total_seconds()/60,
             "d_sections":c,"d_valid":v,"d_flavio":f,
             "d_lula":l,
             "batch_share_pct":100*f/v if v else 0,
             "cum_share_pct":new,
             "cum_delta_pp":new-old if old is not None else None,
             "lula_cum_pct":100*accumulated[3]/accumulated[1]
                              if accumulated[1] else None}
        out.append(row)
    return out


def score(series,minimum_votes=10000,simulations=1000,seed=20261027):
    if simulations<100:
        raise ValueError("Exigir >=100 simulacoes")
    selected=prepare(series,minimum_votes)
    y=[x["residual_pp"] for x in selected]
    patterns=templates(selected)
    top=maximum_periodic_r2(y,patterns)
    parts=[[] for _ in range(4)]
    for i in range(len(y)):
        parts[min(3,i*4//len(y))].append(i)
    rng=Mulberry32(seed)
    results={"individual":0,"blocks":0}
    for _ in range(simulations):
        for mode in results:
            random_y=permutations(y,parts,rng,mode)
            peak=maximum_periodic_r2(random_y,patterns)["r2"]
            results[mode]+=peak>=top["r2"]
    valleys=find_valleys(selected)
    return {"batches_selected":len(selected),
            "batches_original":len(series),
            "min_vote_filter":minimum_votes,
            "valley_threshold_prominence_pp":8,
            "valleys_count":len(valleys),
            "valleys_top10":sorted(valleys,
                key=lambda x:-x["prominence_pp"])[:10],
            "best_period":{
                "axis":top["axis"],"length":round(top["period"],6),
                "r2":round(top["r2"],8)},
            "null_simulations":simulations,"seed":seed,
            "permutation_max_period_p":{
                mode:round((1+hits)/(1+simulations),7)
                for mode,hits in results.items()}},selected


def run(root,simulations=1000,min_vote=10000):
    raw=root/"analysis"/"periodicidade_bweb_2026"
    minute,source=read_sections(raw)
    if source["sections_timestamped"]<.90*source["sections_total"]:
        status="COBERTURA_TEMPO_INSUFICIENTE"
    elif source["fraction_sections_in_UF_span_under_5min"]>.8:
        status="HORARIOS_BWEB_AGRUPADOS_NAO_APLICAR_ORDEM"
    else:
        status="APURACAO_POR_MINUTO_ANALISADA"
    series=minute_series(minute)
    dst=root/"analysis"/"periodicidade_bweb_2026"
    traced=dst/"serie_2026_por_minuto.csv"
    save_csv(traced,list(series[0]),series)
    outcome={"version":VERSION,"status":status,
             "source_version":INPUT_VERSION,
             "input_summary_sha256":sha256(raw/"summary.json"),
             "match_and_coverage":source,
             "minute_bins":len(series),"timeline":str(traced),
             "timeline_sha256":sha256(traced),
             "description":"Curva por MINUTO DT_BU_RECEBIDO do BWEB; nao ordena secoes empatadas"}
    if status=="APURACAO_POR_MINUTO_ANALISADA":
        try:
            tests,residuals=score(series,min_vote,simulations)
            outcome["periodicity"]=tests
            trace=dst/"residuos_2026_por_minuto.csv"
            save_csv(trace,list(residuals[0]),residuals)
            outcome["residual_trace_sha256"]=sha256(trace)
            outcome["residual_trace"]=str(trace)
        except ValueError as exc:
            outcome["status"]="MINUTOS_INSUFICIENTES_PARA_TESTE"
            outcome["periodicity_not_executed_reason"]=str(exc)
    else:
        outcome["periodicity_not_executed_reason"]=(
            "Qualidade/cobertura temporal insuficiente; evitar periodicidade ilusoria")
    outcome["limitations"]=[
        "O timestamp BWEB e de recepcao declarado pelo TSE, NAO um registro independente",
        "Minutos empatados podem conter milhares de urnas em ordem interna desconhecida",
        "Serie por minuto NAO reproduz a ordem individual exata dos BUs no video",
        "Nao se pode transformar p de residuo em probabilidade de fraude",
        "Comparar totais com nacional e explicar secoes ausentes antes de inferir",
        "O nulo por permutacao local de residuos nao controla integralmente a composicao geografica",
        "Somente BU primeiro turno 2026, sem downloads ou SQLite"]
    atomic_json(dst/"phase5c_summary.json",outcome)
    print(json.dumps({"status":outcome["status"],
        "secoes":source["sections_total"],
        "com_hora":source["sections_timestamped"],
        "minutos":len(series),
        "coverage":source["fraction_sections_in_UF_span_under_5min"],
        "periodicity":outcome.get("periodicity"),
        "result":str(dst/"phase5c_summary.json")},
        ensure_ascii=False,indent=2),flush=True)
    return outcome


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root")
    parser.add_argument("--permutacoes",type=int,default=1000)
    parser.add_argument("--minimo-votos",type=int,default=10000)
    args=parser.parse_args()
    run(root_path(args.root),args.permutacoes,args.minimo_votos)
