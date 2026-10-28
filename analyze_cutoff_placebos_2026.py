#!/usr/bin/env python3
"""Fase 5R (menu W): placebos temporais do deslocamento de votos DENTRO das zonas.

Varia o corte por segundos em horários fixados previamente e mede, nas mesmas
zonas, proporção de Lula/Flávio antes/depois. Reusa caches H/M e V com SHA.
Não é teste aleatorizado: resultados não têm valor-p de fraude.
Recebimento BWEB != publicação EA20. Primeiro turno 2026.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import argparse
import csv
import json
from pathlib import Path

from analyze_operational_curve_2026 import BASE, CUT, atomic_csv, atomic_json, load_sources
from analyze_bweb_seconds_2026 import parse_original_second
from extract_bweb_received_2026 import UFs, norm
from correct_bweb_28_periodicity_2026 import VERSION as M_VERSION
from reconcile_stream import sha256
from urnas import root_path

VERSION = "phase5r-within-zone-time-placebos-2026-v1"
CUTOFFS = (
    "2026-10-04 18:00:00",
    "2026-10-04 18:30:00",
    "2026-10-04 19:00:00",
    "2026-10-04 19:30:00",
    "2026-10-04 19:45:00",
    "2026-10-04 20:00:00",
    CUT,
    "2026-10-04 20:15:00",
    "2026-10-04 20:30:00",
    "2026-10-04 21:00:00",
)
MIN_SIDE = 1000
COLUMNS = ("cutoff_brt", "all_pre_valid", "all_post_valid",
           "paired_zones", "paired_post_valid", "paired_post_fraction",
           "positive_zone_count", "negative_zone_count", "zero_zone_count",
           "positive_zone_fraction", "weighted_shift_lula_pp",
           "weighted_shift_flavio_pp", "unweighted_median_shift_lula_pp",
           "lula_pre_paired_pct", "lula_post_paired_pct")
UF_COLS = ("UF", "paired_zones", "paired_post_valid",
           "paired_pre_valid", "weighted_shift_lula_pp", "positive_zones")
RANK_COLS = ("UF","municipio","zona","pre_valid","post_valid",
             "pre_lula_pct","post_lula_pct","shift_lula_pp","shift_flavio_pp")


def pct(n,den):
    return 100*n/den if den else None


def read_multicut(folder, manifest, corrected, cutoffs=CUTOFFS, ufs=UFs):
    """Uma passagem nos shards verificados, sem ordenar BUs com mesmo segundo."""
    if tuple(sorted(set(cutoffs))) != tuple(cutoffs):
        raise ValueError("Cortes devem ser ordenados e unicos")
    if any(datetime.strptime(x,"%Y-%m-%d %H:%M:%S").year!=2026 for x in cutoffs):
        raise ValueError("Cortes fora do pleito")
    # key UF/municipio/zona -> [total v,l,f; pre[cutoff] v,l,f...]
    records = defaultdict(lambda: [0] * (3 + 3 * len(cutoffs)))
    totals = [0, 0, 0, 0]
    hashes = {}
    for uf in ufs:
        shard = folder / f"received-{uf}.csv"
        nrfile = folder / f"phase5h_nr28_sections_{uf}.csv"
        nrmeta = folder / f"phase5h_nr28_sections_{uf}.json"
        info=manifest["ufs"][uf]
        trusted=corrected["checkpoint_sources"][uf]
        if not shard.is_file() or sha256(shard)!=info["shard_sha256"]:
            raise RuntimeError("SHA BWEB errado: "+uf)
        if not nrfile.is_file() or not nrmeta.is_file():
            raise RuntimeError("Checkpoint NR28 faltante: "+uf)
        metadata=json.loads(nrmeta.read_text(encoding="utf-8"))
        nrhash=sha256(nrfile)
        if (metadata.get("version")!=M_VERSION
            or metadata.get("csv_sha256")!=nrhash
            or trusted.get("csv_sha256")!=nrhash
            or metadata.get("archive_sha256")!=info["source_sha256"]):
            raise RuntimeError("SHA NR28 errado: "+uf)
        nr={}
        with nrfile.open(newline="",encoding="utf-8-sig") as f:
            for row in csv.DictReader(f,delimiter=";"):
                sec=tuple(norm(row[k]) for k in ("municipio","zona","secao"))
                if sec in nr:
                    raise RuntimeError("NR28 duplicado")
                nr[sec]=int(row["votos_28"])
        if sum(nr.values())!=metadata["votes_28"]:
            raise RuntimeError("Somatorio NR28 nao confere")
        seen=set()
        count=0
        with shard.open(newline="",encoding="utf-8-sig") as f:
            for row in csv.DictReader(f,delimiter=";"):
                if row["UF"]!=uf or norm(row["turno"])!="1":
                    raise RuntimeError("BU de outra UF/turno")
                municipal, zone, section = [norm(row[k]) for k in ("municipio","zona","secao")]
                sec=(municipal,zone,section)
                if sec in seen:
                    raise RuntimeError("Secao duplicada: "+str((uf,*sec)))
                seen.add(sec)
                valid=int(row["votos_pres_validos"])-nr.pop(sec,0)
                lula=int(row["votos_13"])
                flavio=int(row["votos_22"])
                if min(valid,lula,flavio)<0 or lula+flavio>valid:
                    raise RuntimeError("BWEB individual incoerente")
                seconds,precise=parse_original_second(row["DT_BU_RECEBIDO"])
                if not precise or seconds[:16]!=row["recebimento_minuto"]:
                    raise RuntimeError("Segundo de recepcao BWEB invalido")
                key=(uf,municipal,zone)
                v=records[key]
                values=(valid,lula,flavio)
                for i,x in enumerate(values):
                    v[i]+=x
                for j,cut in enumerate(cutoffs):
                    if seconds>=cut:
                        continue
                    offset=3+3*j
                    for i,x in enumerate(values):
                        v[offset+i]+=x
                totals[0]+=1
                for i,x in enumerate(values):
                    totals[i+1]+=x
                count+=1
        if nr:
            raise RuntimeError("NR28 sem secao correspondente")
        if count!=info["sections"]:
            raise RuntimeError("Contagem de secoes divergente")
        hashes[uf]={"BWEB_SHA256":info["shard_sha256"],"NR28_SHA256":nrhash}
        print(f"[UF {uf}] {count:,} secoes; todos os cortes processados",flush=True)
    return records, totals, hashes


def median(a):
    if not a:
        return None
    arr=sorted(a)
    n=len(arr)
    return (arr[(n-1)//2]+arr[n//2])/2


def measure_cutoffs(records, cutoffs=CUTOFFS, min_side=MIN_SIDE):
    """Soma de zonas com minimo pre E pos; impede viés de amostras pequenas.

    A cada corte, a coorte de zonas elegiveis pode mudar; reportamos cobertura.
    """
    if min_side<=0:
        raise ValueError("min_side invalido")
    rows=[]
    per_uf_focus={}
    focus_zones=[]
    focus_uf_extremes={}
    for j,cut in enumerate(cutoffs):
        offset=3+3*j
        all_pre=0
        all_post=0
        eligible=[]
        for (uf,municipal,zone),a in records.items():
            pre=a[offset:offset+3]
            post=[a[i]-pre[i] for i in range(3)]
            all_pre+=pre[0]
            all_post+=post[0]
            if pre[0]>=min_side and post[0]>=min_side:
                sh_lula=100*(post[1]/post[0]-pre[1]/pre[0])
                sh_flavio=100*(post[2]/post[0]-pre[2]/pre[0])
                eligible.append((uf,municipal,zone,pre,post,sh_lula,sh_flavio))
        weight=sum(e[4][0] for e in eligible)
        positive=sum(e[5]>0 for e in eligible)
        negative=sum(e[5]<0 for e in eligible)
        zeros=len(eligible)-positive-negative
        if all_pre+all_post<=0:
            raise RuntimeError("Nenhum voto")
        if weight:
            weighted_lula=sum(e[4][0]*e[5] for e in eligible)/weight
            weighted_flavio=sum(e[4][0]*e[6] for e in eligible)/weight
            pair_pre=sum(e[3][0] for e in eligible)
            pair_pre_lula=sum(e[3][1] for e in eligible)
            pair_post_lula=sum(e[4][1] for e in eligible)
        else:
            weighted_lula=weighted_flavio=None
            pair_pre=pair_pre_lula=pair_post_lula=0
        rows.append(dict(cutoff_brt=cut, all_pre_valid=all_pre,
            all_post_valid=all_post, paired_zones=len(eligible),
            paired_post_valid=weight, paired_post_fraction=weight/all_post if all_post else None,
            positive_zone_count=positive,negative_zone_count=negative,
            zero_zone_count=zeros,
            positive_zone_fraction=positive/len(eligible) if eligible else None,
            weighted_shift_lula_pp=weighted_lula,
            weighted_shift_flavio_pp=weighted_flavio,
            unweighted_median_shift_lula_pp=median([e[5] for e in eligible]),
            lula_pre_paired_pct=pct(pair_pre_lula,pair_pre),
            lula_post_paired_pct=pct(pair_post_lula,weight)))
        if cut==CUT:
            by_uf=defaultdict(list)
            for item in eligible:
                by_uf[item[0]].append(item)
                uf,mu,zo,pre,post,sh_l,sh_f=item
                focus_zones.append(dict(UF=uf,municipio=mu,zona=zo,
                    pre_valid=pre[0],post_valid=post[0],
                    pre_lula_pct=pct(pre[1],pre[0]),post_lula_pct=pct(post[1],post[0]),
                    shift_lula_pp=sh_l,shift_flavio_pp=sh_f))
            for uf, items in sorted(by_uf.items()):
                w=sum(v[4][0] for v in items)
                p=sum(v[3][0] for v in items)
                per_uf_focus[uf]=dict(UF=uf,paired_zones=len(items),
                    paired_post_valid=w,paired_pre_valid=p,
                    weighted_shift_lula_pp=sum(v[4][0]*v[5] for v in items)/w,
                    positive_zones=sum(v[5]>0 for v in items))
            leave_one=[]
            for uf in sorted(by_uf):
                remaining=[e for e in eligible if e[0]!=uf]
                w=sum(e[4][0] for e in remaining)
                leave_one.append({"excluded_UF":uf,"weighted_shift_lula_pp":
                    sum(e[4][0]*e[5] for e in remaining)/w if w else None,
                    "paired_post_valid":w})
            focus_uf_extremes={"leave_one_UF_out":leave_one}
    return rows, list(per_uf_focus.values()), focus_zones, focus_uf_extremes


def run(root):
    folder=root/BASE
    h,m,sha_h,sha_m=load_sources(folder)
    vpath=folder/"phase5q_zone_holdout_2026_summary.json"
    if not vpath.is_file():
        raise RuntimeError("Fase V nao encontrada; execute V antes de W")
    v=json.loads(vpath.read_text(encoding="utf-8"))
    if v.get("status")!="ZONA_PRE_CORTE_TESTADA_NA_CAUDA_BWEB_2026":
        raise RuntimeError("Fase V invalida")
    original,totals,hashes=read_multicut(folder,h,m)
    if totals!=[499206,119300788,53879538,56104503]:
        raise RuntimeError("Totais nacionais BWEB nao conciliados")
    rows,ufs,zones,robustness=measure_cutoffs(original)
    focus=next(r for r in rows if r["cutoff_brt"]==CUT)
    if (focus["all_pre_valid"]!=v["valid_pre"]
        or focus["all_post_valid"]!=v["valid_post"]
        or focus["paired_zones"]!=v["paired_zones_with_1000_pre_and_post"]
        or abs(focus["weighted_shift_lula_pp"]-
               v["paired_zones_weighted_delta_post_minus_pre_lula_pp"])>1e-8):
        raise RuntimeError("W nao reproduz corte principal da V")
    if focus["paired_post_valid"]!=v["paired_zones_post_valid"]:
        raise RuntimeError("W nao reproduz cobertura de zonas pareadas da V")
    dest={
        "cutoffs":("phase5r_cutoff_placebos_2026.csv",COLUMNS,rows),
        "ufs":("phase5r_uf_paired_zones_2026.csv",UF_COLS,ufs),
        "zones":("phase5r_paired_zones_2026.csv",RANK_COLS,zones)
    }
    files={}
    for label,(name,cols,data) in dest.items():
        p=folder/name
        atomic_csv(p,cols,data)
        files[label]={"path":str(p),"sha256":sha256(p),"rows":len(data)}
    summary={"version":VERSION,"status":"PLACEBOS_TEMPORAIS_INTRA_ZONA_2026",
        "year":2026,"round":1,"cutoff_primary":CUT,"min_valids_each_side":MIN_SIDE,
        "total_sections":totals[0],"total_valid":totals[1],
        "total_lula":totals[2],"total_flavio":totals[3],
        "cutoffs":rows,"focus":focus,
        "robustness":robustness,"output_files":files,
        "source_sha256":{"H_summary":sha_h,"M_summary":sha_m,"V_summary":sha256(vpath),
                         "H_M_per_UF":hashes},
        "limitations":[
            "Os cortes alternativos nao sao experimentos aleatorios; sao controles descritivos.",
            "A composicao de zonas elegiveis pode mudar com o horario; cobertura e explicitada.",
            "BWEB DT_BU_RECEBIDO nao e log independente nem momento de publicacao EA20.",
            "Pre e post de uma zona nao sao necessariamente amostras aleatorias de eleitores.",
            "Nenhum desvio descritivo isolado demonstra alteracao de votos.",
            "Sem downloads, ZIP, SQLite, 2022 ou segundo turno."]}
    report=folder/"phase5r_cutoff_placebos_2026_summary.json"
    atomic_json(report,summary)
    print(json.dumps({
        "status":summary["status"],
        "placebo_cutoffs":[{"time":r["cutoff_brt"],
          "paired_zones":r["paired_zones"],
          "paired_post_fraction":r["paired_post_fraction"],
          "shift_lula_pp":r["weighted_shift_lula_pp"],
          "positive_fraction":r["positive_zone_fraction"]}
          for r in rows],
        "primary":focus,
        "leave_one_UF_out_minmax":[
            min(e["weighted_shift_lula_pp"] for e in robustness["leave_one_UF_out"]
                if e["weighted_shift_lula_pp"] is not None),
            max(e["weighted_shift_lula_pp"] for e in robustness["leave_one_UF_out"]
                if e["weighted_shift_lula_pp"] is not None),
        ],
        "report":str(report)},ensure_ascii=False,indent=2),flush=True)
    return summary


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root")
    args=parser.parse_args()
    run(root_path(args.root))
