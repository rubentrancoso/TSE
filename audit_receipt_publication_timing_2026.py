#!/usr/bin/env python3
"""Fase 5T (menu Y): comparação operacional de recebimento BWEB e publicação EA20.

Alinha CRONOLOGIAS diferentes somente por timestamp declarado, sem jamais
atribuir BU específico a lote publicado. Testa condições necessárias para
a hipótese simplificada 'BU recebido ANTES de publicado', com a hipótese
adicional de que os dois relógios compartilham referência temporal.
Valida SHA de H/M e usa apenas 1T/2026; sem download, ZIP, SQLite, 2022.
"""
from __future__ import annotations

import argparse
from bisect import bisect_left, bisect_right
from collections import defaultdict
import csv
from datetime import datetime, timedelta
import json
from pathlib import Path

from analyze_operational_curve_2026 import (
    BASE, NATIONAL, CUT, atomic_csv, atomic_json, ea20_rows, load_sources
)
from analyze_bweb_seconds_2026 import parse_original_second
from extract_bweb_received_2026 import UFs, norm
from correct_bweb_28_periodicity_2026 import VERSION as M_VERSION
from reconcile_stream import sha256
from urnas import root_path

VERSION="phase5t-bweb-received-versus-ea20-published-2026-v1"
COLUMNS=(
    "ea20_brt","st_published","valid_published","lula_published","flavio_published",
    "valid_received_by_then","lula_received_by_then","flavio_received_by_then",
    "sections_received_by_then",
    "valid_received_minus_published","lula_received_minus_published",
    "flavio_received_minus_published",
    "constraint_valid_ok","constraint_lula_ok","constraint_flavio_ok",
    "all_three_constraints_ok",
    "latest_necessary_receipt_time","aggregate_rank_slack_seconds",
)
OFFSETS=(0,-300,300,-10800,10800)  # Segundos, predefinidos; nao calibrar.
OFF_COLUMNS=(
    "offset_seconds_applied_to_bweb","ea20_snapshots","snapshots_published_exceeds_received_valid",
    "snapshots_published_exceeds_received_lula",
    "snapshots_published_exceeds_received_flavio",
    "snapshots_any_excess","max_valid_excess_votes","max_lula_excess_votes",
    "max_flavio_excess_votes","first_any_excess_brt","final_valid_received",
    "final_valid_published",
)


def check_number(r, *keys):
    v = [int(r[k]) for k in keys]
    if any(n<0 for n in v) or v[1]+v[2]>v[0]:
        raise RuntimeError("Contagens BWEB incoerentes: "+str(v))
    return v


def read_second_events(folder, manifest, corrected, ufs=UFs):
    """Agrupa seções por segundos sem ordenar empates arbitrariamente."""
    events=defaultdict(lambda:[0,0,0,0])
    global_totals=[0,0,0,0]
    hashes={}
    for uf in ufs:
        source=folder/f"received-{uf}.csv"
        nr_path=folder/f"phase5h_nr28_sections_{uf}.csv"
        nrmeta=folder/f"phase5h_nr28_sections_{uf}.json"
        info=manifest["ufs"][uf]
        trust=corrected["checkpoint_sources"][uf]
        if not source.is_file() or sha256(source)!=info["shard_sha256"]:
            raise RuntimeError("SHA BWEB invalido na UF "+uf)
        if not nr_path.is_file() or not nrmeta.is_file():
            raise RuntimeError("NR28/manifesto ausente "+uf)
        metadata=json.loads(nrmeta.read_text(encoding="utf-8"))
        nrsha=sha256(nr_path)
        if (metadata.get("version")!=M_VERSION or
            metadata.get("csv_sha256")!=nrsha or
            trust["csv_sha256"]!=nrsha or
            metadata.get("archive_sha256")!=info["source_sha256"] or
            metadata.get("votes_28")!=trust["votes_28"]):
            raise RuntimeError("Manifesto NR28 nao confere "+uf)
        nr28={}
        with nr_path.open("r",encoding="utf-8-sig",newline="") as f:
            for row in csv.DictReader(f,delimiter=";"):
                key=tuple(norm(row[k]) for k in ("municipio","zona","secao"))
                if key in nr28:
                    raise RuntimeError("NR28 duplicado "+str((uf,key)))
                nr28[key]=int(row["votos_28"])
        if sum(nr28.values())!=metadata["votes_28"]:
            raise RuntimeError("NR28 sem soma coerente "+uf)
        seen=set()
        count=0
        with source.open("r",encoding="utf-8-sig",newline="") as f:
            for r in csv.DictReader(f,delimiter=";"):
                if r["UF"]!=uf or norm(r["turno"])!="1":
                    raise RuntimeError("UF/turno invalido "+uf)
                key=tuple(norm(r[k]) for k in ("municipio","zona","secao"))
                if key in seen:
                    raise RuntimeError("Chave de secao duplicada "+str((uf,key)))
                seen.add(key)
                n28=nr28.pop(key,0)
                v,l,f22=check_number({
                    "v":int(r["votos_pres_validos"])-n28,
                    "l":r["votos_13"],"f":r["votos_22"]},"v","l","f")
                when,precise=parse_original_second(r["DT_BU_RECEBIDO"])
                if not precise or when[:16]!=r["recebimento_minuto"]:
                    raise RuntimeError("Timestamp BWEB sem precisao de segundo "+str((uf,key)))
                item=events[when]
                for i,n in enumerate((1,v,l,f22)):
                    item[i]+=n
                    global_totals[i]+=n
                count+=1
        if nr28:
            raise RuntimeError("NR28 sem chave BWEB "+uf)
        if count!=info["sections"]:
            raise RuntimeError("Secoes/manifesto H nao fecham "+uf)
        hashes[uf]={"BWEB_SHA256":info["shard_sha256"],"NR28_SHA256":nrsha}
        print(f"[UF {uf}] {count:,} secoes; recebimento por segundo validado",flush=True)
    return events,global_totals,hashes


def cumulative_events(events):
    if not events:
        raise ValueError("Nao ha timestamps BWEB")
    seconds=sorted(events)
    cumulative=[]
    count=[0,0,0,0]
    for s in seconds:
        for i,val in enumerate(events[s]):
            count[i]+=val
        cumulative.append(tuple(count))
    return seconds,cumulative


def receipt_index_at(time_str, seconds, offset_seconds=0):
    shifted=(datetime.strptime(time_str,"%Y-%m-%d %H:%M:%S")-
             timedelta(seconds=offset_seconds)).strftime("%Y-%m-%d %H:%M:%S")
    return bisect_right(seconds,shifted)-1


def evaluate(ea, events, offsets=OFFSETS):
    """Inequacao cumulativa condicional; sem imputar identidade de urnas."""
    seconds,cumulative=cumulative_events(events)
    full=cumulative[-1]
    if full[1:]!=(ea[-1]["valid"],ea[-1]["lula"],ea[-1]["flavio"]):
        raise RuntimeError("Candidatos e validos finais EA20/BWEB nao coincidem")
    # In the BWEB row vector, indices are [sections,valid,lula,flavio].
    lower_bounds=[]
    for metric,idx in (("valid",1),("lula",2),("flavio",3)):
        levels=[x[idx] for x in cumulative]
        lower_bounds.append((metric,levels))

    def compute(offset, detailed=False):
        result=[]
        for r in ea:
            i=receipt_index_at(r["brt"],seconds,offset)
            recv=cumulative[i] if i>=0 else (0,0,0,0)
            differences=[recv[1]-r["valid"],recv[2]-r["lula"],
                         recv[3]-r["flavio"]]
            ok=[z>=0 for z in differences]
            latest=None
            slack=None
            if detailed:
                # Earliest time enough receipts existed in EACH category.
                thresholds=[]
                for field,values in lower_bounds:
                    required=r[field]
                    j=bisect_left(values,required)
                    if j>=len(seconds):
                        raise RuntimeError("EA20 final excede BWEB receipt universe")
                    thresholds.append(seconds[j])
                latest=max(thresholds)
                # These are lower bounds by count/rank, not matching BU-specific lags.
                lag=(datetime.strptime(r["brt"],"%Y-%m-%d %H:%M:%S")-
                     (datetime.strptime(latest,"%Y-%m-%d %H:%M:%S")+
                      timedelta(seconds=offset))).total_seconds()
                slack=int(lag)
            result.append({
                "ea20_brt":r["brt"], "st_published":r["st"],
                "valid_published":r["valid"],"lula_published":r["lula"],
                "flavio_published":r["flavio"],
                "sections_received_by_then":recv[0],
                "valid_received_by_then":recv[1],
                "lula_received_by_then":recv[2],
                "flavio_received_by_then":recv[3],
                "valid_received_minus_published":differences[0],
                "lula_received_minus_published":differences[1],
                "flavio_received_minus_published":differences[2],
                "constraint_valid_ok":ok[0],
                "constraint_lula_ok":ok[1],
                "constraint_flavio_ok":ok[2],
                "all_three_constraints_ok":all(ok),
                "latest_necessary_receipt_time":latest,
                "aggregate_rank_slack_seconds":slack,
            })
        return result

    rows=compute(0,detailed=True)
    offset_rows=[]
    for shift in offsets:
        d=rows if shift==0 else compute(shift)
        bad=[r for r in d if not r["all_three_constraints_ok"]]
        offset_rows.append({
            "offset_seconds_applied_to_bweb":shift,
            "ea20_snapshots":len(d),
            "snapshots_published_exceeds_received_valid":sum(
                not r["constraint_valid_ok"] for r in d),
            "snapshots_published_exceeds_received_lula":sum(
                not r["constraint_lula_ok"] for r in d),
            "snapshots_published_exceeds_received_flavio":sum(
                not r["constraint_flavio_ok"] for r in d),
            "snapshots_any_excess":len(bad),
            "max_valid_excess_votes":max(0,max(-r["valid_received_minus_published"] for r in d)),
            "max_lula_excess_votes":max(0,max(-r["lula_received_minus_published"] for r in d)),
            "max_flavio_excess_votes":max(0,max(-r["flavio_received_minus_published"] for r in d)),
            "first_any_excess_brt":bad[0]["ea20_brt"] if bad else None,
            "final_valid_received":d[-1]["valid_received_by_then"],
            "final_valid_published":d[-1]["valid_published"],
        })
    # Last receipt generally occurs after (or before) final publication snapshot.
    # Never silently assume the timestamps have an independently validated clock.
    early=rows[0]
    cut=next(r for r in rows if r["ea20_brt"]==CUT)
    negative=[r for r in rows if not r["all_three_constraints_ok"]]
    stats={
        "status":"BWEB_RECEBIMENTO_VS_PUBLICACAO_EA20_2026",
        "version":VERSION,"year":2026,"round":1,
        "hypothesis":"mesmo universo de votos; ambos relogios compartilham BRT; recepcao antecede publicacao",
        "source_events":{"unique_bweb_seconds":len(seconds),"first_bweb_second":seconds[0],
                         "last_bweb_second":seconds[-1],
                         "sections":full[0],"valid":full[1],"lula":full[2],"flavio":full[3]},
        "ea20_snapshots":len(rows),
        "baseline_offsets":{"applied_seconds_to_bweb":0,
            "all_constraints_held":not negative,
            "snapshot_violations":len(negative),
            "first_violating_brt":negative[0]["ea20_brt"] if negative else None,
            "worst_valid_shortfall":max(0,max(-r["valid_received_minus_published"] for r in rows)),
            "worst_lula_shortfall":max(0,max(-r["lula_received_minus_published"] for r in rows)),
            "worst_flavio_shortfall":max(0,max(-r["flavio_received_minus_published"] for r in rows)),
            "first_snapshot":{key:early[key] for key in ("ea20_brt",
                "valid_received_minus_published","lula_received_minus_published","flavio_received_minus_published")},
            "at_200439":{key:cut[key] for key in ("ea20_brt",
                "valid_received_minus_published","lula_received_minus_published","flavio_received_minus_published")},
            "last_snapshot":{key:rows[-1][key] for key in ("ea20_brt",
                "valid_received_minus_published","lula_received_minus_published","flavio_received_minus_published")},
        },
        "predeclared_offsets":offset_rows,
        "limitations":[
            "Recebimento BWEB e publicacao EA20 sao eventos distintos, nao e permitido alinhar BU a lote individual.",
            "A hipotese depende de ambos os timestamps representarem a mesma referencia temporal e de origem de dados compativel.",
            "Se os mesmos votos foram recebidos antes da publicacao e relogios estao sincronizados, cada contagem EA20 <= recebidos cumulativos no mesmo t e condicao NECESSARIA.",
            "Uma violacao da desigualdade testa o modelo de cronologia e pode resultar de diferencas de semantica/relógio, caches, ou publicacao; nao prova adulteracao.",
            "Uma desigualdade satisfeita NAO comprova buffering nem autenticidade; recepcao de voto agregado nao identifica os BU publicados.",
            "Slacks de rank sao limites de disponibilidade por CONTAGEM, nunca tempos de espera medidos para urnas individuais.",
            "Secoes EA20 vs BWEB diferem por 42 contadores de ZZ sem votos; NAO se comparou numeros de secoes como contagens fisicas equivalentes.",
            "Variacoes fixas de offset nao devem ser ajustadas para obter um resultado desejado ou alegadas como correcao validada.",
            "Snapshots EA20 sao pontos de captura; nao ha log interno por transacao.",
            "1T 2026, sem downloads, ZIP, SQLite, 2022 ou segundo turno.",
        ]
    }
    return rows,offset_rows,stats


def run(root, repo=Path(__file__).resolve().parent):
    repo=repo.resolve()
    folder=root/BASE
    manifest,corrected,h_sha,m_sha=load_sources(folder)
    ea_source=repo/NATIONAL
    ea=ea20_rows(ea_source)
    events,totals,hashes=read_second_events(folder,manifest,corrected)
    if totals!=[499206,119300788,53879538,56104503]:
        raise RuntimeError("BWEB por segundos nao fecha com contagens oficiais")
    rows,offsets,stats=evaluate(ea,events)
    baseline=stats["baseline_offsets"]
    out_paths={
        "timeline":("phase5t_receipt_vs_publication_timeline_2026.csv",COLUMNS,rows),
        "offsets":("phase5t_receipt_vs_publication_offsets_2026.csv",OFF_COLUMNS,offsets),
    }
    stats["source_sha256"]={"EA20_national":sha256(ea_source),
        "H_summary":h_sha,"M_summary":m_sha,"BU_uf":hashes}
    stats["output_files"]={}
    for key,(filename,columns,records) in out_paths.items():
        path=folder/filename
        atomic_csv(path,columns,records)
        stats["output_files"][key]={"path":str(path),"sha256":sha256(path),"rows":len(records)}
    dest=folder/"phase5t_receipt_vs_publication_2026_summary.json"
    atomic_json(dest,stats)
    print(json.dumps({
        "status":stats["status"],
        "source_events":stats["source_events"],
        "baseline_offsets":baseline,
        "predeclared_offsets":offsets,
        "report":str(dest),
    },ensure_ascii=False,indent=2),flush=True)
    return stats


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root")
    args=parser.parse_args()
    run(root_path(args.root))
