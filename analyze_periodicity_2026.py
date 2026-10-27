#!/usr/bin/env python3
"""Analise de vales/periodicidade na apuracao presidencial de 2026.

Analisa a cronologia nacional de 193 snapshots ja preservada em CSV no
repositorio. Nao baixa dados, nao abre SQLite, nao usa resultados de 2022.

ATENCAO: eixo X = secoes nacionais acumuladas, NAO ordem individual de BU.
Procura periodicidade em residuo da participacao de Flavio nos LOTES,
nao confunde 152 quedas da percentagem acumulada com pulsos periodicos.
Teste de permutacao estratificada e em blocos, EXPLORATORIO; nao prova fraude.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from datetime import datetime
from pathlib import Path

SOURCE = Path("data/forensics/analysis/phase5a_presidential_national_2026.csv")
OUT = Path("data/forensics/analysis")
VERSION = "phase5a-national-valleys-2026-v1"
SOURCE_ORIGIN = ("ArvorCo/PNAD, commit "
    "beb3bec9ae5c25e2868ee2f2cefb9e6dccd91415,"
    " analysis/apuracao_2026/dados/linha_do_tempo.json")
SOURCE_ORIGIN_SHA256 = "3e29b16d2827f88e407096d6fa494a3d1b862f8156633f1a7f905e799f70af73"


def read_csv(path, strict=True):
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows=list(csv.DictReader(f))
    if len(rows)<15:
        raise ValueError("Numero insuficiente de snapshots")
    obs=[]
    for row in rows:
        timestamp=datetime.fromisoformat(row["gerado_em"].replace("Z","+00:00")).timestamp()
        vals=[int(row[k]) for k in
              ("st","vv","flavio","lula","cury","renan","caiado","outros")]
        if any(v<0 for v in vals) or sum(vals[2:]) != vals[1]:
            raise ValueError("Totais impossiveis no snapshot")
        obs.append({"timestamp":timestamp, "brt":row["gerado_brt"],
                    "sections":vals[0],"valid":vals[1],
                    "flavio":vals[2],"lula":vals[3]})
    if any(b["timestamp"]<=a["timestamp"] or
           b["sections"]<a["sections"] or
           b["valid"]<=a["valid"] or
           b["flavio"]<a["flavio"] or
           b["lula"]<a["lula"]
           for a,b in zip(obs,obs[1:])):
        raise ValueError("Regresso temporal, secoes ou contagens")
    if strict and (len(obs)!=193 or obs[0]["sections"]!=6157 or
                   obs[-1]["sections"]!=499248 or
                   obs[-1]["valid"]!=119300788):
        raise ValueError("Cobertura diverge de fonte congelada 2026")
    return obs


def batches(obs):
    start=obs[0]["timestamp"]
    out=[]
    for a,b in zip(obs,obs[1:]):
        dv=b["valid"]-a["valid"]
        df=b["flavio"]-a["flavio"]
        out.append({
            "brt":b["brt"],"sections":b["sections"],
            "minutes":(b["timestamp"]-start)/60,
            "d_sections":b["sections"]-a["sections"],
            "d_valid":dv,"d_flavio":df,
            "batch_share_pct":100*df/dv,
            "cum_share_pct":100*b["flavio"]/b["valid"],
            "cum_delta_pp":100*(b["flavio"]/b["valid"]-
                                a["flavio"]/a["valid"])
        })
    return out


def median(numbers):
    x=sorted(numbers)
    half=len(x)//2
    return x[half] if len(x)%2 else (x[half-1]+x[half])/2


def prepare(bats, minimum_votes=10000, width=15):
    if width<3 or width%2!=1:
        raise ValueError("Janela da mediana deve ser impar >=3")
    chosen=[dict(row) for row in bats if row["d_valid"]>=minimum_votes]
    if len(chosen)<30:
        raise ValueError("Lotes insuficientes apos corte de tamanho")
    half=width//2
    for i,row in enumerate(chosen):
        neighborhood=chosen[max(0,i-half):min(len(chosen),i+half+1)]
        baseline=median([r["batch_share_pct"] for r in neighborhood])
        row["local_median_pct"]=baseline
        row["residual_pp"]=row["batch_share_pct"]-baseline
    return chosen


def period_grid(lo,hi,n=72):
    return [lo*math.exp(i*math.log(hi/lo)/(n-1)) for i in range(n)]


def templates(rows):
    result=[]
    for axis,periods in (
        ("sections",period_grid(2000,100000)),
        ("minutes",period_grid(2,120))
    ):
        xx=[float(row[axis]) for row in rows]
        for period in periods:
            s=[math.sin(2*math.pi*x/period) for x in xx]
            c=[math.cos(2*math.pi*x/period) for x in xx]
            means=sum(s)/len(s),sum(c)/len(c)
            s=[v-means[0] for v in s]
            c=[v-means[1] for v in c]
            ss=sum(v*v for v in s)
            cc=sum(v*v for v in c)
            sc=sum(a*b for a,b in zip(s,c))
            det=ss*cc-sc*sc
            if det>1e-8:
                result.append((axis,period,s,c,ss,cc,sc,det))
    return result


def maximum_periodic_r2(y,patterns):
    mean=sum(y)/len(y)
    yy=sum((v-mean)**2 for v in y)
    best={"axis":None,"period":None,"r2":0.0}
    if yy<=1e-15:
        return best
    for axis,period,s,c,ss,cc,sc,det in patterns:
        sy=sum(v*w for v,w in zip(y,s))
        cy=sum(v*w for v,w in zip(y,c))
        r2=(cc*sy*sy+ss*cy*cy-2*sc*sy*cy)/(det*yy)
        if r2>best["r2"]:
            best={"axis":axis,"period":period,"r2":r2}
    return best


class Mulberry32:
    """Gerador deterministico para reproduzir o piloto JS de 27/10/2026."""
    def __init__(self,seed):
        self.state=seed & 0xFFFFFFFF

    def random(self):
        mask=0xFFFFFFFF
        self.state=(self.state+0x6D2B79F5)&mask
        t=((self.state^(self.state>>15))*(1|self.state))&mask
        t=((t+(((t^(t>>7))*(61|t))&mask))&mask)^t
        return ((t^(t>>14))&mask)/4294967296

    def shuffle(self,values):
        for i in range(len(values)-1,0,-1):
            j=int(self.random()*(i+1))
            values[i],values[j]=values[j],values[i]
        return values


def permutations(y,parts,rng,mode):
    out=list(y)
    for positions in parts:
        if mode=="individual":
            vals=rng.shuffle([y[j] for j in positions])
        elif mode=="blocks":
            groups=[[y[k] for k in positions[i:i+5]]
                    for i in range(0,len(positions),5)]
            vals=[v for group in rng.shuffle(groups) for v in group]
        else:
            raise ValueError("Modo nulo invalido")
        for j,value in zip(positions,vals):
            out[j]=value
    return out


def find_valleys(rows,threshold=8.0):
    vals=[]
    for i in range(1,len(rows)-1):
        r=rows[i]
        y=r["residual_pp"]
        if not (y<rows[i-1]["residual_pp"] and
                y<=rows[i+1]["residual_pp"]):
            continue
        left=[p["residual_pp"] for p in rows[max(0,i-5):i]]
        right=[p["residual_pp"] for p in rows[i+1:min(len(rows),i+6)]]
        prom=min(max(left)-y,max(right)-y)
        if prom>=threshold:
            vals.append({"brt":r["brt"],"sections":r["sections"],
                         "d_valid":r["d_valid"],
                         "residual_pp":round(y,5),
                         "prominence_pp":round(prom,5)})
    return vals


def analyze(obs,replications=1000,seed=20261027,minimum_votes=10000):
    if replications<100:
        raise ValueError("Minimo 100 permutacoes")
    all_batches=batches(obs)
    selected=prepare(all_batches,minimum_votes)
    y=[r["residual_pp"] for r in selected]
    patterns=templates(selected)
    observed=maximum_periodic_r2(y,patterns)
    rng=Mulberry32(seed)
    parts=[[] for _ in range(4)]
    for i in range(len(y)):
        parts[min(3,i*4//len(y))].append(i)
    results={"individual":[],"blocks":[]}
    hits={"individual":0,"blocks":0}
    for _ in range(replications):
        for mode in ("individual","blocks"):
            null=maximum_periodic_r2(
                permutations(y,parts,rng,mode),patterns)["r2"]
            results[mode].append(null)
            hits[mode]+=null>=observed["r2"]
    pvals={mode:(hits[mode]+1)/(replications+1) for mode in hits}
    valleys=find_valleys(selected)
    report={
        "version":VERSION,"status":"EXPLORATORIO_NACIONAL_2026",
        "source_snapshots":len(obs),"batches":len(all_batches),
        "batches_minimum_votes":len(selected),
        "minimum_valid_votes_per_batch":minimum_votes,
        "local_median_window":15,
        "valley_threshold_prominence_pp":8.0,
        "valleys_found":len(valleys),
        "valleys":valleys,
        "periods_scanned":{"sections":[2000,100000,72],
                           "minutes":[2,120,72]},
        "best_period":{"axis":observed["axis"],
                       "period":round(observed["period"],8),
                       "r2":round(observed["r2"],8)},
        "replications":replications,"seed":seed,
        "max_frequency_scan_corrected_mc_p":{
            mode:round(pvals[mode],8) for mode in pvals},
        "null_max_r2_95th":{
            mode:round(sorted(results[mode])[int(.95*(replications-1))],8)
            for mode in pvals},
        "post_resume_direction":{
            "fall":sum(r["cum_delta_pp"]<0 for r in all_batches
                       if r["brt"]>"2026-10-04 20:04:39"),
            "increase":sum(r["cum_delta_pp"]>0 for r in all_batches
                           if r["brt"]>"2026-10-04 20:04:39")},
        "limitations":[
            "Resultados sao por ATUALIZACAO NACIONAL, nao por BU individual",
            "Sem horario de recepcao de cada secao nao reproduz ordenacao das urnas do video",
            "Permutacao em quartis e blocos controla somente parte da dependencia temporal",
            "Teste nao condiciona a geografia exata de cada lote; nao e veredito de fraude",
            "Analise exploratoria de parametros predefinidos neste script; testar robustez antes de inferencia confirmatoria"
        ]
    }
    return report,selected


def run(source=SOURCE,outdir=OUT,replications=1000,seed=20261027):
    obs=read_csv(source)
    report,selected=analyze(obs,replications,seed)
    report["source_csv"]=str(source)
    report["source_csv_sha256"]=hashlib.sha256(source.read_bytes()).hexdigest()
    report["upstream"]=SOURCE_ORIGIN
    report["upstream_sha256"]=SOURCE_ORIGIN_SHA256
    outdir.mkdir(parents=True,exist_ok=True)
    dest=outdir/"phase5a_periodicity_2026_summary.json"
    tmp=Path(str(dest)+".part")
    try:
        tmp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",
                       encoding="utf-8")
        os.replace(tmp,dest)
    finally:
        if tmp.exists():tmp.unlink()
    trace=outdir/"phase5a_periodicity_residuals_2026.csv"
    columns=("brt","sections","minutes","d_sections","d_valid",
             "batch_share_pct","cum_share_pct","cum_delta_pp",
             "local_median_pct","residual_pp")
    tmp=Path(str(trace)+".part")
    try:
        with tmp.open("w",encoding="utf-8",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=columns,lineterminator="\n",
                                  extrasaction="ignore")
            writer.writeheader()
            writer.writerows(selected)
            f.flush();os.fsync(f.fileno())
        os.replace(tmp,trace)
    finally:
        if tmp.exists():tmp.unlink()
    print(json.dumps({"status":report["status"],"n":len(selected),
        "valleys":report["valleys_found"],
        "best":report["best_period"],
        "permutation_p":report["max_frequency_scan_corrected_mc_p"],
        "summary":str(dest),"residuals":str(trace)},
        ensure_ascii=False,indent=2),flush=True)
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv",type=Path,default=SOURCE)
    parser.add_argument("--output",type=Path,default=OUT)
    parser.add_argument("--permutacoes",type=int,default=1000)
    parser.add_argument("--semente",type=int,default=20261027)
    args=parser.parse_args()
    run(args.csv,args.output,args.permutacoes,args.semente)
