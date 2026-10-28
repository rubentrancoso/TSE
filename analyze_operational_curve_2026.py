#!/usr/bin/env python3
"""Fase 5O / menu S — reconstrução operacional da curva de 2026 (1T).

Eixos físicos, votos INTEIROS, comparação de escala por atualização
versus relógio real e contrafactuais geográficos UF / município de
recebimento dos BU. A cronologia pública EA20 e a cronologia BWEB
de DT_BU_RECEBIDO são fontes DIFERENTES: não alinhar lotes por minuto
nem alegar que receberam/publicaram no mesmo momento.

Usa somente CSV EA20 nacional versionado, caches H/M com SHA e
tabelas por seção BWEB H + números 28 da M, sem ZIP, rede, SQLite.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
import argparse
import csv
import json
import math
import os
from pathlib import Path

from extract_bweb_received_2026 import UFs, VERSION as H_VERSION, norm
from correct_bweb_28_periodicity_2026 import VERSION as M_VERSION
from reconcile_stream import sha256
from urnas import root_path
from analyze_bweb_seconds_2026 import parse_original_second

VERSION="phase5o-operational-curve-2026-v1"
BASE=Path("analysis/periodicidade_bweb_2026")
CUT="2026-10-04 20:04:39"
NATIONAL=Path("data/forensics/analysis/phase5a_presidential_national_2026.csv")
EA_COLUMNS=("brt","st","valid","lula","flavio","share_lula_pct","share_flavio_pct",
            "d_seconds","d_sections","d_valid","d_lula","d_flavio",
            "batch_lula_pct","batch_flavio_pct")
BU_COLUMNS=("brt_minute","d_sections","d_valid","d_lula","d_flavio",
            "cum_sections","cum_valid","cum_lula","cum_flavio",
            "share_lula_pct","share_flavio_pct",
            "model_uf_lula_pct","model_mun_lula_pct",
            "model_uf_flavio_pct","model_mun_flavio_pct",
            "delta_lula_mun_pp","delta_flavio_mun_pp")
UF_COLUMNS=("UF","pre_valid","pre_lula","pre_flavio",
            "post_valid","post_lula","post_flavio",
            "all_valid","all_lula","all_flavio",
            "share_lula_post_pct","share_flavio_post_pct")


def stamp(raw):
    return datetime.strptime(raw,"%Y-%m-%d %H:%M:%S")

def minute(raw):
    return datetime.strptime(raw,"%Y-%m-%d %H:%M")

def atomic_csv(path,columns,items):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=Path(str(path)+".part")
    try:
        with temporary.open("w",newline="",encoding="utf-8") as out:
            writer=csv.DictWriter(out,fieldnames=columns,delimiter=";",
                                  extrasaction="ignore",lineterminator="\n")
            writer.writeheader()
            writer.writerows(items)
            out.flush();os.fsync(out.fileno())
        os.replace(temporary,path)
    finally:
        if temporary.exists():temporary.unlink()

def atomic_json(path,item):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=Path(str(path)+".part")
    try:
        with temporary.open("w",encoding="utf-8") as out:
            json.dump(item,out,ensure_ascii=False,indent=2)
            out.write("\n");out.flush();os.fsync(out.fileno())
        os.replace(temporary,path)
    finally:
        if temporary.exists():temporary.unlink()

def line_fit(xs,ys):
    """Descriptive OLS line fit (no chance/fraud interpretation)."""
    if len(xs)<3 or len(xs)!=len(ys):return None
    origin=xs[0]
    x=[float(v-origin) for v in xs]
    mx=sum(x)/len(x)
    my=sum(ys)/len(ys)
    xx=sum((v-mx)**2 for v in x)
    if xx<=0:return None
    slope=sum((v-mx)*(y-my) for v,y in zip(x,ys))/xx
    intercept=my-slope*mx
    residual=[y-(intercept+slope*v) for v,y in zip(x,ys)]
    se=sum(v*v for v in residual)
    sy=sum((y-my)**2 for y in ys)
    return {"points":len(ys),"slope_per_xunit":slope,
            "rmse_pp":math.sqrt(se/len(ys)),
            "max_abs_deviation_pp":max(map(abs,residual)),
            "r2":(1-se/sy if sy else None)}

def ea20_rows(source):
    with source.open(encoding="utf-8-sig",newline="") as f:
        raw=list(csv.DictReader(f))
    if len(raw)<150:raise RuntimeError("Poucos snapshots nacionais EA20")
    rows=[]
    for i,r in enumerate(raw):
        dt=stamp(r["gerado_brt"])
        item={"brt":r["gerado_brt"],"st":int(r["st"]),
              "valid":int(r["vv"]),"lula":int(r["lula"]),
              "flavio":int(r["flavio"])}
        if item["lula"]+item["flavio"]>item["valid"]:
            raise RuntimeError("Candidatos > validos no EA20")
        if rows:
            previous=rows[-1]
            if dt<=stamp(previous["brt"]):
                raise RuntimeError("Snapshot EA20 em ordem temporal inconsistente")
            for col in ("st","valid","lula","flavio"):
                if item[col]<previous[col]:
                    raise RuntimeError("Regressao EA20 em contagem cumulativa")
            seconds=(dt-stamp(previous["brt"])).total_seconds()
            item.update({"d_seconds":seconds,
               "d_sections":item["st"]-previous["st"],
               "d_valid":item["valid"]-previous["valid"],
               "d_lula":item["lula"]-previous["lula"],
               "d_flavio":item["flavio"]-previous["flavio"]})
        else:
            item.update({"d_seconds":"","d_sections":"","d_valid":"",
                         "d_lula":"","d_flavio":""})
        item["share_lula_pct"]=100*item["lula"]/item["valid"]
        item["share_flavio_pct"]=100*item["flavio"]/item["valid"]
        item["batch_lula_pct"]=(100*item["d_lula"]/item["d_valid"]
                                 if item["d_valid"] not in ("",0) else "")
        item["batch_flavio_pct"]=(100*item["d_flavio"]/item["d_valid"]
                                   if item["d_valid"] not in ("",0) else "")
        rows.append(item)
    if (rows[-1]["st"]!=499248 or rows[-1]["valid"]!=119300788
        or rows[-1]["lula"]!=53879538 or rows[-1]["flavio"]!=56104503):
        raise RuntimeError("EA20 nacional nao atinge o certificado final")
    if CUT not in {r["brt"] for r in rows}:
        raise RuntimeError("EA20 sem corte exato 20:04:39 BRT")
    return rows

def describe_line(rows,field,axis):
    xs=([stamp(r["brt"]).timestamp() for r in rows] if axis=="clock"
        else list(range(len(rows))) if axis=="updates"
        else [r["st"] for r in rows])
    return line_fit(xs,[r[field] for r in rows])

def load_sources(folder):
    h=folder/"summary.json"
    m=folder/"phase5h_corrected_periodicity_2026_summary.json"
    if not h.is_file() or not m.is_file():
        raise RuntimeError("Necessarias H e M previamente concluidas")
    a=json.loads(h.read_text(encoding="utf-8"))
    b=json.loads(m.read_text(encoding="utf-8"))
    if (a.get("version")!=H_VERSION or a.get("sections")!=499206
        or set(a.get("ufs",{}))!=set(UFs)
        or b.get("version")!=M_VERSION
        or b.get("status")!="VALIDOS_PRESIDENCIAIS_CORRIGIDOS"
        or b.get("difference_valid_vs_official")!=0
        or b["corrected_totals"]["valid"]!=119300788):
        raise RuntimeError("Os manifestos H/M nao correspondem ao 1T 2026")
    return a,b,sha256(h),sha256(m)

def read_receipt_data(folder,manifest,corrected):
    """Only already SHA-verified, per-section CSVs; also verify each NR28 cache."""
    batches=defaultdict(lambda:defaultdict(lambda:[0,0,0,0]))
    uf_all=defaultdict(lambda:[0,0,0])
    mu_all=defaultdict(lambda:[0,0,0])
    timing=defaultdict(lambda:[0,0,0,0,0,0])
    hashes={}
    for uf in UFs:
        src=folder/f"received-{uf}.csv"
        nrpath=folder/f"phase5h_nr28_sections_{uf}.csv"
        nrmeta=folder/f"phase5h_nr28_sections_{uf}.json"
        if not src.is_file() or sha256(src)!=manifest["ufs"][uf]["shard_sha256"]:
            raise RuntimeError("SHA BWEB H incorreto: "+uf)
        if not nrpath.is_file() or not nrmeta.is_file():
            raise RuntimeError("Checkpoint NR28 M incompleto: "+uf)
        state=json.loads(nrmeta.read_text(encoding="utf-8"))
        trusted=corrected["checkpoint_sources"][uf]
        if (state.get("version")!=M_VERSION or
            state.get("csv_sha256")!=sha256(nrpath) or
            state.get("csv_sha256")!=trusted["csv_sha256"] or
            state.get("archive_sha256")!=manifest["ufs"][uf]["source_sha256"]):
            raise RuntimeError("Manifesto NR28 nao coincide com H/M: "+uf)
        nr={}
        with nrpath.open(encoding="utf-8-sig",newline="") as f:
            for r in csv.DictReader(f,delimiter=";"):
                key=tuple(norm(r[k]) for k in ("municipio","zona","secao"))
                if key in nr:raise RuntimeError("Duplicata no numero 28")
                nr[key]=int(r["votos_28"])
        if sum(nr.values())!=state["votes_28"]:
            raise RuntimeError("NR28 nao concilia com M na UF "+uf)
        count=0
        with src.open(encoding="utf-8-sig",newline="") as f:
            for r in csv.DictReader(f,delimiter=";"):
                if r["UF"]!=uf or norm(r["turno"])!="1":
                    raise RuntimeError("UF/turno inesperado no cache H")
                key=tuple(norm(r[k]) for k in ("municipio","zona","secao"))
                n28=nr.pop(key,0)
                v=int(r["votos_pres_validos"])-n28
                l=int(r["votos_13"]);f22=int(r["votos_22"])
                if min(v,l,f22)<0 or l+f22>v:
                    raise RuntimeError("Votos BU negativos ou inconsistentes")
                when=r["recebimento_minuto"]
                if not when or len(when)!=16:
                    raise RuntimeError("BU sem minuto de recebimento")
                minute(when)
                second_stamp,precise=parse_original_second(r["DT_BU_RECEBIDO"])
                if not precise or second_stamp[:16]!=when:
                    raise RuntimeError("Timestamp BU H nao confere com minuto/segundo")
                # municipality key is explicit; do not mix municipalities across UFs
                district=(uf,key[0])
                increment=batches[when][district]
                for k,qty in enumerate((1,v,l,f22)):increment[k]+=qty
                for dest in (uf_all[uf],mu_all[district]):
                    dest[0]+=v;dest[1]+=l;dest[2]+=f22
                before=second_stamp < CUT
                tim=timing[uf]
                start=0 if before else 3
                tim[start]+=v;tim[start+1]+=l;tim[start+2]+=f22
                count+=1
        if nr:raise RuntimeError("NR28 nao encontrou secao em H "+uf)
        if count!=manifest["ufs"][uf]["sections"]:
            raise RuntimeError("Seções por UF não batem com H: "+uf)
        hashes[uf]={"BWEB_SHA256":manifest["ufs"][uf]["shard_sha256"],
                    "NR28_SHA256":state["csv_sha256"]}
        print(f"[UF {uf}] {count:,} secoes; BWEB + NR28 hashes validados",flush=True)
    return batches,uf_all,mu_all,timing,hashes

def make_reception_curve(batches,uf_all,mu_all):
    """Observed series and geography-only counterfactuals.

    Counterfactual uses final shares within UF/municipality and actual
    observed vote volumes by receipt minute for each municipality.
    It is an in-sample decomposition, NOT an independent causal forecast.
    """
    cumulative=[0,0,0,0]
    geo=[0.,0.,0.,0.]
    rows=[]
    for when in sorted(batches):
        item=batches[when]
        increments=[0,0,0,0]
        predict=[0.,0.,0.,0.]
        for (uf,mu),numbers in item.items():
            for j,x in enumerate(numbers):increments[j]+=x
            v=numbers[1]
            uv,ul,ufl=uf_all[uf]
            mv,ml,mfl=mu_all[(uf,mu)]
            if v and (uv<=0 or mv<=0):raise RuntimeError("Geografia sem votos totais")
            predict[0]+=v*ul/uv if uv else 0
            predict[1]+=v*ml/mv if mv else 0
            predict[2]+=v*ufl/uv if uv else 0
            predict[3]+=v*mfl/mv if mv else 0
        for j,x in enumerate(increments):cumulative[j]+=x
        for j,x in enumerate(predict):geo[j]+=x
        n,v,l,f=cumulative
        if v<=0:continue
        p=lambda x:100*x/v
        rows.append({
            "brt_minute":when,"d_sections":increments[0],
            "d_valid":increments[1],"d_lula":increments[2],
            "d_flavio":increments[3],"cum_sections":n,
            "cum_valid":v,"cum_lula":l,"cum_flavio":f,
            "share_lula_pct":p(l),"share_flavio_pct":p(f),
            "model_uf_lula_pct":p(geo[0]),
            "model_mun_lula_pct":p(geo[1]),
            "model_uf_flavio_pct":p(geo[2]),
            "model_mun_flavio_pct":p(geo[3]),
            "delta_lula_mun_pp":p(l-geo[1]),
            "delta_flavio_mun_pp":p(f-geo[3])})
    return rows,cumulative,geo

def rmse_gap(rows,observed,estimated):
    return math.sqrt(sum((r[observed]-r[estimated])**2 for r in rows)/len(rows)) if rows else None

def build(root,repo):
    repo=repo.resolve()
    national=repo/NATIONAL
    if not national.is_file():raise RuntimeError("Snapshots EA20 versionados indisponiveis")
    ea=ea20_rows(national)
    folder=root/BASE
    manifest,corrected,h_sha,m_sha=load_sources(folder)
    batches,ufs,municipalities,timing,hashes=read_receipt_data(folder,manifest,corrected)
    received,tot,geo=make_reception_curve(batches,ufs,municipalities)
    if (tot!=[499206,119300788,53879538,56104503]
        or sum(x[1] for x in ufs.values())!=53879538
        or abs(geo[1]-53879538)>1e-5
        or abs(geo[3]-56104503)>1e-5):
        raise RuntimeError("BWEB recebido, EA20 final ou modelos geograficos nao conciliados")
    ref=folder/"phase5h_minute_corrected_2026.csv"
    if not ref.is_file() or sha256(ref)!=corrected["corrected_minutes_sha256"]:
        raise RuntimeError("Série corrigida da M nao bate com SHA")
    by_minutes={r["brt_minute"]:r for r in received}
    with ref.open(encoding="utf-8-sig",newline="") as f:
        prior=list(csv.DictReader(f,delimiter=";"))
    if len(prior)!=len(received):raise RuntimeError("Numero de minutos difere da M")
    for item in prior:
        r=by_minutes.get(item["brt"])
        if r is None or any(r[a]!=int(item[b]) for a,b in
            (("d_valid","d_valid"),("d_lula","d_lula"),
             ("d_flavio","d_flavio"),("d_sections","d_sections"))):
            raise RuntimeError("Curva geográfica diferente da M no minuto "+item["brt"])

    after=[x for x in ea if x["brt"]>=CUT]
    if len(after)!=153:
        raise RuntimeError(f"Numero de snapshots pos-20:04 incomum: {len(after)}")
    r_after=[x for x in received if x["brt_minute"]>=CUT[:16]]
    if len(r_after)<10:raise RuntimeError("BWEB apos corte sem pontos suficientes")
    line_ea={f"{field}_{axis}":describe_line(after,field,axis)
          for field in ("share_lula_pct","share_flavio_pct")
          for axis in ("clock","updates","sections")}
    def receipt_fit(rows,field):
        xs=[minute(r["brt_minute"]).timestamp() for r in rows]
        return line_fit(xs,[r[field] for r in rows])
    line_bweb={name:receipt_fit(r_after,name)
               for name in ("share_lula_pct","share_flavio_pct",
                            "model_uf_lula_pct","model_mun_lula_pct")}
    line_bweb_by_sections={name:line_fit([r["cum_sections"] for r in r_after],
                                        [r[name] for r in r_after])
               for name in ("share_lula_pct","share_flavio_pct",
                            "model_uf_lula_pct","model_mun_lula_pct")}
    geography={
        "UF_only_rmse_lula_pp":rmse_gap(r_after,"share_lula_pct","model_uf_lula_pct"),
        "Municipality_rmse_lula_pp":rmse_gap(r_after,"share_lula_pct","model_mun_lula_pct"),
        "UF_only_rmse_flavio_pp":rmse_gap(r_after,"share_flavio_pct","model_uf_flavio_pct"),
        "Municipality_rmse_flavio_pp":rmse_gap(r_after,"share_flavio_pct","model_mun_flavio_pct"),
        "counterfactual_note":"Taxas finais por UF/municipio extraidas da MESMA eleicao; decomposicao in-sample, nao prevendo resultado de forma independente."}
    uf_rows=[]
    for uf in UFs:
        a=timing[uf];v,l,f,all_v,all_l,all_f=(*a[:3],*a[3:])
        post=(all_v,all_l,all_f)
        full=ufs[uf]
        uf_rows.append(dict(zip(UF_COLUMNS,(uf,v,l,f,*post,*full,
                            100*all_l/all_v if all_v else "",
                            100*all_f/all_v if all_v else ""))))
    geography["post_receipt_valids_by_UF"]=sum(r["post_valid"] for r in uf_rows)
    geography["post_receipt_lula_by_UF"]=sum(r["post_lula"] for r in uf_rows)
    geography["post_receipt_flavio_by_UF"]=sum(r["post_flavio"] for r in uf_rows)
    return {
        "ea_rows":ea,"bweb_rows":received,"uf_rows":uf_rows,
        "summary":{
            "version":VERSION,"status":"CURVAS_OPERACIONAIS_RECONSTRUIDAS_2026",
            "cutoff_brt":CUT,"source_year":2026,"round":1,
            "ea20_snapshot_count":len(ea),
            "ea20_post_resume_points":len(after),
            "ea20_post_resume_transitions":len(after)-1,
            "ea20_post_resume_trajectory":line_ea,
            "bweb_receipt_minute_count":len(received),
            "bweb_post_resume_minutes":len(r_after),
            "bweb_trajectory_by_clock":line_bweb,
            "bweb_trajectory_by_sections":line_bweb_by_sections,
            "bweb_geo_composition":geography,
            "all_votes_reconciled":{"sections":tot[0],"valid":tot[1],
                                    "lula":tot[2],"flavio":tot[3]},
            "sha256_sources":{"ea20_national":sha256(national),
                  "H_summary":h_sha,"M_summary":m_sha,
                  "M_corrected_minute_series":sha256(ref)},
            "per_UF_verified_shards":hashes,
            "warning":[
               "Regressao linear descritiva mede lisura em cada eixo, nao gera valor-p de fraude",
               "As capturas EA20 medem PUBLICACAO e o BWEB mede campo RECEBIMENTO: tempos nao equivalem",
               "O modelo geografico usa participacoes finais da propria eleicao e volumes observados; nao comprova causalidade",
               "Mistura de municipios nao preserva efeito intra-municipio nem fluxo operacional de buffering",
               "Classificacao antes/depois do corte usa SEGUNDOS exatos do BU, mas curva exportada tem resolucao de MINUTO",
               "Eixo 'updates' equidistante nao e o mesmo que tempo real",
               "Nenhum registro de segundo turno utilizado"
            ]
        }
    }

def run(root,repo=Path(__file__).resolve().parent):
    results=build(root,repo)
    folder=root/BASE
    outputs={
        "ea20_timeline":"phase5o_ea20_time_axes_2026.csv",
        "bweb_geography":"phase5o_bweb_receipt_geo_2026.csv",
        "uf_receipt_breakdown":"phase5o_uf_receipt_breakdown_2026.csv"}
    for key,filename in outputs.items():
        columns={"ea20_timeline":EA_COLUMNS,"bweb_geography":BU_COLUMNS,
                 "uf_receipt_breakdown":UF_COLUMNS}[key]
        rows={"ea20_timeline":results["ea_rows"],
              "bweb_geography":results["bweb_rows"],
              "uf_receipt_breakdown":results["uf_rows"]}[key]
        path=folder/filename
        atomic_csv(path,columns,rows)
        results["summary"][key]={"path":str(path),"sha256":sha256(path)}
    path=folder/"phase5o_operational_curve_2026_summary.json"
    atomic_json(path,results["summary"])
    print(json.dumps({
       "status":results["summary"]["status"],
       "EA20_post_resume":results["summary"]["ea20_post_resume_points"],
       "curve_EA20_real_clock":results["summary"]["ea20_post_resume_trajectory"]["share_lula_pct_clock"],
       "curve_EA20_equal_updates":results["summary"]["ea20_post_resume_trajectory"]["share_lula_pct_updates"],
       "BWEB_geographic_model":results["summary"]["bweb_geo_composition"],
       "report":str(path)
    },ensure_ascii=False,indent=2),flush=True)
    return results["summary"]

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root")
    args=parser.parse_args()
    run(root_path(args.root))
