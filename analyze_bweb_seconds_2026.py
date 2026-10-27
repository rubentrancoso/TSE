#!/usr/bin/env python3
"""Fase 5E: BU de 2026 por segundo e blocos consecutivos de 500-2000 urnas.

SOMENTE shards recebidos pela Fase 5C, SHA-256 validados.
Nao abre ZIP, nao le SQLite, nao baixa, nao usa eleicoes de 2022.
NAO inventa ordem entre urnas com o mesmo DT_BU_RECEBIDO:
todos os BUs daquele segundo entram como uma unidade atomica.
Os periodogramas sao exploratorios, sob nulos restritos.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime
import json
import os
from pathlib import Path

from analyze_periodicity_2026 import (
    find_valleys, prepare, templates, maximum_periodic_r2,
    permutations, Mulberry32
)
from reconcile_stream import sha256
from urnas import root_path
from extract_bweb_received_2026 import VERSION as EXTRACT_VERSION

VERSION="phase5e-second-bu-series-2026-v1"
TARGET_BINS=(500,1000,2000)


def parse_original_second(raw):
    value=str(raw or "").strip()
    formats=(("%d/%m/%Y %H:%M:%S",True),
             ("%Y-%m-%d %H:%M:%S",True),
             ("%d/%m/%Y %H:%M",False),
             ("%Y-%m-%d %H:%M",False))
    for fmt,exact in formats:
        try:
            moment=datetime.strptime(value,fmt)
            if moment.year!=2026:
                raise ValueError("Outro ano em BWEB")
            return moment.strftime("%Y-%m-%d %H:%M:%S"),exact
        except ValueError:
            pass
    if not value:
        return "",False
    raise RuntimeError("DT_BU_RECEBIDO BWEB invalido: "+repr(value))


def atomic_json(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=Path(str(path)+".part")
    try:
        with tmp.open("w",encoding="utf-8") as f:
            json.dump(obj,f,ensure_ascii=False,indent=2)
            f.write("\n")
            f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if tmp.exists():tmp.unlink()


def write_csv(path,rows):
    if not rows:
        raise RuntimeError("Serie vazia")
    tmp=Path(str(path)+".part")
    try:
        with tmp.open("w",encoding="utf-8",newline="") as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter=";",
                             lineterminator="\n",extrasaction="ignore")
            w.writeheader();w.writerows(rows)
            f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if tmp.exists():tmp.unlink()


def read_seconds(cache):
    reference=cache/"summary.json"
    if not reference.is_file():
        raise RuntimeError("Execute primeiro a opcao H: nao ha shards no H:")
    data=json.loads(reference.read_text("utf-8"))
    if data.get("version")!=EXTRACT_VERSION:
        raise RuntimeError("Versao incompatível do cache BWEB")
    sec=defaultdict(lambda:[0,0,0,0])
    counts=Counter()
    source_file_hashes={}
    per_uf=Counter()
    for uf,info in sorted(data["ufs"].items()):
        path=cache/f"received-{uf}.csv"
        if not path.is_file() or sha256(path)!=info["shard_sha256"]:
            raise RuntimeError("SHA-256 de cache individual invalido: "+str(path))
        source_file_hashes[uf]=info["shard_sha256"]
        with path.open(encoding="utf-8-sig",newline="") as f:
            rows=csv.DictReader(f,delimiter=";")
            required={"DT_BU_RECEBIDO","recebimento_minuto",
                      "UF","turno","votos_pres_validos","votos_13","votos_22"}
            if not required.issubset(set(rows.fieldnames or [])):
                raise RuntimeError("Colunas BU necessarias ausentes")
            for row in rows:
                if row["UF"]!=uf or row["turno"]!="1":
                    raise RuntimeError("UF/turno inesperados")
                stamp,precision=parse_original_second(row["DT_BU_RECEBIDO"])
                if not stamp:
                    counts["sem_tempo"]+=1
                    per_uf[uf]+=1
                    continue
                if row["recebimento_minuto"]!=stamp[:16]:
                    raise RuntimeError("Minuto nao coincide com segundo original")
                n=int(row["votos_pres_validos"])
                f22=int(row["votos_22"])
                l13=int(row["votos_13"])
                if n<0 or f22<0 or l13<0 or f22+l13>n:
                    raise RuntimeError("Votos impossiveis por secao")
                slot=sec[stamp]
                for j,value in enumerate((1,n,f22,l13)):
                    slot[j]+=value
                counts["secoes"]+=1
                counts["validos"]+=n
                counts["flavio"]+=f22
                counts["lula"]+=l13
                counts["segundos_explicitos"]+=int(precision)
                per_uf[uf]+=1
        if per_uf[uf]!=info["sections"]:
            raise RuntimeError(f"{uf}: numero de secoes no shard mudou")
        print(f"[SEGUNDOS {uf}] {per_uf[uf]:,} BU, SHA OK",flush=True)
    if sum(per_uf.values())!=data["sections"]:
        raise RuntimeError("Total de BU distinto do relatorio H")
    return sec,{"input_shards":len(source_file_hashes),
       "source_sha256_by_uf":source_file_hashes,
       "sections":counts["secoes"],"without_timestamp":counts["sem_tempo"],
       "sections_explicit_second":counts["segundos_explicitos"],
       "seconds_coverage":round(counts["segundos_explicitos"]/max(1,data["sections"]),6),
       "valid_votes":counts["validos"],
       "flavio_votes":counts["flavio"],"lula_votes":counts["lula"],
       "total_source_sections":data["sections"],
       "n_distinct_seconds":len(sec),
       "max_sections_in_same_second":max((x[0] for x in sec.values()),default=0)}


def group_to_series(timegroups,target_sections=1):
    """Um mesmo segundo nunca e repartido entre blocos."""
    if not timegroups:
        raise ValueError("Sem registros de recepcao")
    start=datetime.fromisoformat(min(timegroups))
    accum=[0,0,0,0]
    pending=[0,0,0,0]
    first=None
    records=[]
    def commit(stamp):
        old_vote=accum[1]
        old_f=accum[2]
        for j,value in enumerate(pending):
            accum[j]+=value
        now_vote=accum[1]
        if now_vote<=0:
            raise RuntimeError("Contagem presidencial valida acumulada nula")
        dt=(datetime.fromisoformat(stamp)-start).total_seconds()
        return {"brt":stamp,"sections":accum[0],
            "minutes":dt/60,
            "d_sections":pending[0],"d_valid":pending[1],
            "d_flavio":pending[2],"d_lula":pending[3],
            "batch_share_pct":100*pending[2]/pending[1] if pending[1] else 0,
            "cum_share_pct":100*accum[2]/now_vote,
            "lula_cum_pct":100*accum[3]/now_vote,
            "cum_delta_pp":(100*accum[2]/now_vote-100*old_f/old_vote
                            if old_vote>0 else None)}
    for stamp in sorted(timegroups):
        nums=timegroups[stamp]
        for j,v in enumerate(nums):
            pending[j]+=v
        if pending[0]>=target_sections:
            records.append(commit(stamp))
            pending=[0,0,0,0]
    if pending[0]:
        records.append(commit(max(timegroups)))
    if records[-1]["sections"]!=sum(x[0] for x in timegroups.values()):
        raise RuntimeError("Secoes perdidas nos blocos")
    return records


def test_periodicity(batches,minimum_votes,window,simulations,seed):
    selected=prepare(batches,minimum_votes=minimum_votes,width=window)
    y=[r["residual_pp"] for r in selected]
    patterns=templates(selected)
    best=maximum_periodic_r2(y,patterns)
    strat=[[] for _ in range(4)]
    for i in range(len(y)):
        strat[min(3,i*4//len(y))].append(i)
    rng=Mulberry32(seed)
    hits={"individual":0,"blocks":0}
    for _ in range(simulations):
        for mode in hits:
            vals=permutations(y,strat,rng,mode)
            hits[mode]+=maximum_periodic_r2(vals,patterns)["r2"]>=best["r2"]
    valleys=find_valleys(selected,threshold=8.)
    return {"points_analyzed":len(selected),
        "median_window":window,"minimum_votes":minimum_votes,
        "valleys_8pp":len(valleys),
        "valley_top10":sorted(valleys,key=lambda x:-x["prominence_pp"])[:10],
        "period":{"axis":best["axis"],"length":round(best["period"],6),
                  "r2":round(best["r2"],8)},
        "null_simulations":simulations,
        "p_empirical":{"individual":round((hits["individual"]+1)/(simulations+1),7),
                       "blocks5":round((hits["blocks"]+1)/(simulations+1),7)}}


def run(root,simulations=200):
    if simulations<100:
        raise ValueError("Exigir pelo menos 100 simulacoes")
    base=root/"analysis"/"periodicidade_bweb_2026"
    groups,coverage=read_seconds(base)
    previous=base/"phase5c_summary.json"
    if previous.is_file():
        earlier=json.loads(previous.read_text("utf-8"))
        matched=earlier.get("match_and_coverage",{})
        reference=matched.get("total_in_timed_sections",{})
        for k,field in (("valid","valid_votes"),("flavio","flavio_votes"),
                        ("lula","lula_votes")):
            if k in reference and reference[k]!=coverage[field]:
                raise RuntimeError("Totais da Fase 5E divergentes da Fase 5C")
        coverage["national_vote_reconciliation"]=matched.get(
            "total_compare_with_official",{})
    tsec=group_to_series(groups)
    secondpath=base/"phase5e_por_segundo_2026.csv"
    write_csv(secondpath,tsec)
    report={"version":VERSION,"status":"AUDITORIA_INICIADA",
            "coverage":coverage,"second_bins":len(tsec),
            "second_trace":str(secondpath),
            "second_trace_sha256":sha256(secondpath),
            "tests":[],
            "methodology":[
                "BU do primeiro turno 2026: SHA dos derivados recebidos opcao H",
                "Usa segundo EXPLICITO do DT_BU_RECEBIDO, sem preencher segundos desconhecidos",
                "Mesmo segundo e grupo atomico: ordem interna das urnas nao e inventada",
                "Blocos acumulam ao menos 500, 1000 ou 2000 secoes sem quebrar segundo",
                "Periodograma de residuo do percentual do lote ajustado por mediana de 15 blocos",
                "Variacao de volume e parametros e exploratoria, sem controle do maximo entre variantes"],
            "limitations":[
                "TSE nao e fonte independente e seu timestamp de recepcao pode nao ser entrega publica",
                "Ordem interna de BUs que compartilham o mesmo segundo permanece indeterminada",
                "Permutacao estratificada nao garante controle de geografia ou dependencia temporal",
                "Periodo detectado nao demonstra transferencia ou falsificacao de votos",
                "Sem ZIP, rede, SQLite ou microdados de 2022"]}
    if coverage["seconds_coverage"]<.9:
        report["status"]="PRECISAO_SEGUNDO_INSUFICIENTE"
        report["reason"]="Menos de 90% das secoes com segundo explicitamente registrado"
    else:
        report["status"]="TESTE_EXPLORATORIO_DE_SEGUNDOS_E_BLOCOS"
        for target in TARGET_BINS:
            timeline=group_to_series(groups,target)
            out=base/f"phase5e_blocos_{target}_2026.csv"
            write_csv(out,timeline)
            result={"target_sections":target,"blocks":len(timeline),
                    "maximum_sections_one_bin":max(t["d_sections"] for t in timeline),
                    "max_sections_same_second":coverage["max_sections_in_same_second"],
                    "csv_sha256":sha256(out),"file":str(out)}
            try:
                result["periodicity"]=test_periodicity(timeline,
                    minimum_votes=10000,window=15,
                    simulations=simulations,seed=20261027)
            except ValueError as e:
                result["not_executed_reason"]=str(e)
            report["tests"].append(result)
            best=result.get("periodicity",{})
            print(f"[BU BLOCO {target}] blocos={len(timeline)} "
                  f"melhor={best.get('period')} "
                  f"vales={best.get('valleys_8pp')}",flush=True)
    file=base/"phase5e_high_resolution_2026_summary.json"
    atomic_json(file,report)
    print(json.dumps({"status":report["status"],
        "secs":coverage["n_distinct_seconds"],
        "secoes":coverage["sections"],
        "precisao":coverage["seconds_coverage"],
        "diferencas_votos_versus_nacional":coverage.get("national_vote_reconciliation",{}),
        "tests":[{"target_sections":t["target_sections"],
                  "blocks":t["blocks"],
                  "periodicity":t.get("periodicity")}
                 for t in report["tests"]],
        "report":str(file)},ensure_ascii=False,indent=2),flush=True)
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root")
    parser.add_argument("--permutacoes",type=int,default=200)
    args=parser.parse_args()
    run(root_path(args.root),args.permutacoes)
