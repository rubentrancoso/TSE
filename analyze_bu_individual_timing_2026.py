#!/usr/bin/env python3
"""Fase 5B — tabela de BU presidenciais individuais 2026 e auditoria da ordem.

SOMENTE 2026. Nao baixa nada e nao abre SQLite. Reusa 256 CSV BU ja
derivados, com SHA-256 e checkpoints retomaveis. Tenta associar EA16 local
por UF/municipio/zona/secao, mas NAO considera da/ha prova de recepcao
individual. Bloqueia inferencia cronologica se horarios forem agrupados
artificialmente. Nao transforma ordem numerica de secao em tempo.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
from datetime import datetime
import json
import os
from pathlib import Path

from analyze_phase3_arrivals import parse_dt
from cross_office_candidate_correlations import source, rows
from reconcile_stream import sha256
from urnas import root_path

VERSION = "phase5b-bu-section-timing-2026-v1"
ELECTION_TURN = "1"
EA16_FILES = "{uf}-p003220-cs.json"
UFs = tuple("AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO".split())
HEAD = ("UF","municipio","zona","secao","turno","votos_validos_pres",
        "votos_totais_pres","votos_13","votos_22","brancos","nulos")
JOIN_HEAD = HEAD + ("ea16_da","ea16_ha","ea16_timestamp","status_tempo")
BATCH_HEAD = ("UF","municipio","zona","secao","turno","votos_validos_pres",
              "votos_totais_pres","votos_13","votos_22","brancos","nulos")


def numeric_code(value):
    if value is None or not str(value).strip():
        raise ValueError("Codigo de secao vazio")
    return str(int(value))


def key(uf,mu,zo,se,turn="1"):
    return (str(uf).upper(),numeric_code(mu),numeric_code(zo),
            numeric_code(se),numeric_code(turn))


def atomic_json(path,payload):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=Path(str(path)+".part")
    try:
        with tmp.open("w",encoding="utf-8") as f:
            json.dump(payload,f,ensure_ascii=False,indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if tmp.exists():tmp.unlink()


def atomic_csv(path,header,items):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=Path(str(path)+".part")
    count=0
    try:
        with tmp.open("w",encoding="utf-8",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=list(header),delimiter=";",
                                  lineterminator="\n",extrasaction="ignore")
            writer.writeheader()
            for item in items:
                writer.writerow(item)
                count+=1
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if tmp.exists():tmp.unlink()
    return count


def timestamp_sources(root,repo_root):
    """Somente EA16 existente: nunca solicita arquivos pela rede."""
    locations=(repo_root/"data"/"forensics"/"phase3"/"raw"/"ea16",
               root/"phase3"/"raw"/"ea16",
               root/"ea16")
    for folder in locations:
        if all((folder/EA16_FILES.format(uf=u.lower())).is_file()
               for u in UFs):
            return folder
    return None


def extract_ea16(data,uf):
    abr=next((x for x in data.get("abr",[]) if str(x.get("cd","")).lower()==uf.lower()),None)
    if abr is None and len(data.get("abr",[]))==1:
        abr=data["abr"][0]
    if abr is None:
        raise RuntimeError("EA16 sem abrangencia esperada: "+uf)
    for municipality in abr.get("mu",[]):
        for zona in municipality.get("zon",[]):
            for sec in zona.get("sec",[]):
                if sec.get("nsp"):
                    continue
                k=key(uf,municipality["cd"],zona["cd"],sec["ns"])
                da,ha=sec.get("da",""),sec.get("ha","")
                dt=parse_dt(da,ha)
                yield k,{"da":da,"ha":ha,"time":dt.isoformat() if dt else ""}


def load_ea16(folder,reference):
    """Confere os 27 hashes previamente documentados em 2026."""
    known={x["uf"]:x["sha256"] for x in reference.get("sources",[])
           if "sha256" in x}
    if set(known)!=set(UFs):
        raise RuntimeError("Inventario EA16 nao cobre as 27 UFs")
    timeline={}
    byuf=Counter()
    byufsec={}
    sourcehashes={}
    for uf in UFs:
        path=folder/EA16_FILES.format(uf=uf.lower())
        observed=sha256(path)
        if observed!=known[uf]:
            raise RuntimeError("EA16 alterado, SHA divergente: "+str(path))
        sourcehashes[uf]=observed
        document=json.loads(path.read_text(encoding="utf-8-sig"))
        timestamps=[]
        for k,item in extract_ea16(document,uf):
            if k in timeline:
                raise RuntimeError("Secao EA16 duplicada: "+repr(k))
            timeline[k]=item
            byuf[uf]+=1
            if item["time"]:
                timestamps.append(item["time"])
        byufsec[uf]=timestamps
        print(f"[EA16 {uf}] {byuf[uf]:,} secoes, SHA valido",flush=True)
    details={}
    bad=0
    for uf in UFs:
        times=byufsec[uf]
        if times:
            earliest,latest=min(times),max(times)
            delta=(datetime.fromisoformat(latest)-datetime.fromisoformat(earliest)).total_seconds()
        else:
            earliest=latest=""
            delta=None
        short=delta is not None and delta<300
        bad+=byuf[uf] if short else 0
        details[uf]={"sections":byuf[uf],
                     "timestamp_coverage":len(times),
                     "earliest":earliest,"latest":latest,
                     "span_seconds":delta,"all_in_under_5_min":short,
                     "distinct_timestamps":len(set(times))}
    ratio=bad/max(1,sum(byuf.values()))
    status=("EA16_CONCENTRACAO_EM_MASSA_INCOMPATIVEL_COM_ORDEM_INDIVIDUAL"
            if ratio>=.80 else "EA16_ORDEM_INDIVIDUAL_NAO_AUTENTICADA")
    return timeline,{"status":status,
        "sections":sum(byuf.values()),
        "sections_in_uf_bursts_under_5_min":bad,
        "fraction_in_bursts":round(ratio,6),
        "by_uf":details,"sha256_by_uf":sourcehashes}


def extract_president_bucket(source_csv,out_csv):
    """Reconstroi SOMENTE votos presidenciais, por chave real de secao."""
    prev=None
    counts=Counter()
    produced=0
    votes=Counter()
    def flush():
        nonlocal produced
        if prev is None or not counts:return None
        total=sum(counts.values())
        blank=counts.get("95",0)
        null=counts.get("96",0)
        valid=total-blank-null
        f=counts.get("22",0)
        l=counts.get("13",0)
        if min(total,valid,f,l,blank,null)<0 or f+l>valid:
            raise RuntimeError("Contagem presidencial BU impossivel")
        produced+=1
        votes["pres_valid"]+=valid
        votes["pres_total"]+=total
        votes["pres_13"]+=l
        votes["pres_22"]+=f
        return dict(zip(HEAD,(*prev,valid,total,l,f,blank,null)))

    def iterate():
        nonlocal prev
        for row in rows(source_csv):
            if row["turno"]!=ELECTION_TURN or row["cargo"]!="1":
                continue
            k=key(row["UF"],row["municipio"],row["zona"],
                  row["secao"],row["turno"])
            if k!=prev:
                entry=flush()
                if entry is not None:yield entry
                counts.clear()
                prev=k
            n=int(row["votos_BU"])
            if n<0:raise RuntimeError("Votos BU negativos")
            counts[numeric_code(row["votavel"])]+=n
        last=flush()
        if last is not None:yield last
    n=atomic_csv(out_csv,HEAD,iterate())
    if n!=produced:raise RuntimeError("Numero de secoes divergente")
    return {"sections":n,"totals":dict(votes),
            "sha256":sha256(out_csv)}


def merge_sections(bucket_paths,ea16,dest):
    observed=set()
    matched=unmatched=0
    raw_totals=Counter()
    timestamps=Counter()
    def generate():
        nonlocal matched,unmatched
        for p in bucket_paths:
            with p.open("r",encoding="utf-8",newline="") as f:
                for row in csv.DictReader(f,delimiter=";"):
                    k=key(row["UF"],row["municipio"],row["zona"],
                          row["secao"],row["turno"])
                    if k in observed:
                        raise RuntimeError("BU de Presidente duplicado "+repr(k))
                    observed.add(k)
                    raw_totals["secoes"]+=1
                    for col in HEAD[5:]:
                        raw_totals[col]+=int(row[col])
                    timing=ea16.get(k)
                    if timing:
                        matched+=1
                        status="EA16_NAO_VALIDADO_COMO_RECEPCAO"
                        timestamps[timing["time"] or "SEM_DATA"]+=1
                    else:
                        unmatched+=1
                        status="SEM_EA16_PARA_CHAVE"
                    yield {**row,"ea16_da":timing["da"] if timing else "",
                           "ea16_ha":timing["ha"] if timing else "",
                           "ea16_timestamp":timing["time"] if timing else "",
                           "status_tempo":status}
    n=atomic_csv(dest,JOIN_HEAD,generate())
    return {"bu_pres_sections":n,"matched_ea16":matched,
            "without_ea16":unmatched,
            "coverage_matched_pct":round(100*matched/max(1,n),5),
            "distinct_ea16_seconds":len(timestamps),
            "biggest_one_second_group":max(timestamps.values(),default=0),
            "totals":dict(raw_totals),"csv_sha256":sha256(dest)}


def run(root,repo_root=Path(".")):
    repo_root=repo_root.resolve()
    analysis=root/"analysis"
    published=repo_root/"data"/"forensics"/"analysis"/"phase3_arrivals_summary.json"
    if not published.is_file():
        raise RuntimeError("Resumo historico EA16 nao existe no repositorio; sem coleta automatica")
    ref=json.loads(published.read_text(encoding="utf-8-sig"))
    folder,base,inputs=source(root)
    dest=folder/"periodicidade_bu_individual_2026"
    dest.mkdir(parents=True,exist_ok=True)
    meta={"version":VERSION,"fingerprint":base["source_fingerprint"],
          "count":len(inputs),"candidate_sha256":base["source_fingerprint"]}
    original=dest/"checkpoint.json"
    if original.is_file():
        checkpoint=json.loads(original.read_text(encoding="utf-8"))
        if checkpoint.get("identity")!=meta:
            raise RuntimeError("Checkpoint de outro acervo ou versao")
    else:
        checkpoint={"identity":meta,"completed":{}}
    local=timestamp_sources(root,repo_root)
    if local:
        ea16,quality=load_ea16(local,ref)
    else:
        ea16={}
        quality={"status":"EA16_27_ARQUIVOS_NAO_LOCALIZADOS",
                 "historical_sections":ref.get("principal_sections"),
                 "historical_source":"phase3_arrivals_summary.json",
                 "historical_timestamp_coverage":ref.get("timestamp_coverage_pct"),
                 "historical_uf_burst_examples":{
                     uf:ref.get("ufs",{}).get(uf)
                     for uf in ("AC","BA","SP","AM")}}
    print("[QUALIDADE DA ORDEM]",quality["status"],flush=True)
    target=dest/"bucket_pres"
    target.mkdir(exist_ok=True)
    files=[]
    totals=Counter()
    for i,src in enumerate(inputs):
        shard=target/f"bucket-{i:04d}.csv"
        record=checkpoint["completed"].get(str(i))
        if record and shard.is_file() and sha256(shard)==record["sha256"]:
            current=record
        else:
            current=extract_president_bucket(src,shard)
            checkpoint["completed"][str(i)]=current
            atomic_json(original,checkpoint)
        files.append(shard)
        totals["secoes"]+=current["sections"]
        for k,v in current["totals"].items():totals[k]+=v
        if i<2 or (i+1)%16==0 or i+1==len(inputs):
            print(f"[BU {i+1}/{len(inputs)}] secoes acumuladas={totals['secoes']:,}",flush=True)
    merged=dest/"presidente_por_secao_com_metadados_ea16.csv"
    joined=merge_sections(files,ea16,merged)
    status=("CRONOLOGIA_INVALIDA_NAO_REALIZAR_PERIODOGRAMA"
            if quality["status"]!="RECEPCAO_AUTENTICADA_INDIVIDUAL" else
            "PRONTO_PARA_ANALISE_DE_ORDEM")
    report={"version":VERSION,"status":status,
            "fingerprint":base["source_fingerprint"],
            "bu_buckets_sha_verified":len(inputs),
            "bu_totals":dict(totals),
            "ea16_clock_quality":quality,
            "matching":joined,
            "csv":str(merged),
            "methodology":[
                "Dados 2026: Presidente, BU por secao e turno 1",
                "Usa arquivos selados de candidatos sem rede ou SQLite",
                "Votos BU reconstituidos e timestamps EA16 associados por chave eleitoral completa",
                "EA16 da/ha e tempo do auxiliar, NAO prova de recebimento individual",
                "Ordem numerica de secao e desempate de mesmo timestamp nao sao ordem real de envio",
                "Sem log de recepcao por secao validado nao fazer teste de vales temporais nem alegar ausencia de periodicidade",
                "Nao importar microdados de 2022 nem converter anomalia em prova de fraude"]}
    atomic_json(dest/"summary.json",report)
    print("FASE 5B CONCLUIDA: "+status,flush=True)
    print(json.dumps({"BU_secoes":totals["secoes"],"EA16_matching":joined["matched_ea16"],
       "quality":quality["status"],"source_files":len(inputs),
       "result":str(dest/"summary.json")},
       ensure_ascii=False,indent=2),flush=True)
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",help="Acervo BU existente em H:")
    parser.add_argument("--repo",type=Path,default=Path("."))
    args=parser.parse_args()
    run(root_path(args.root),args.repo)
