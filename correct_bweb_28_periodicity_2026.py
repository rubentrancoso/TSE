#!/usr/bin/env python3
"""Fase 5H: corrigir nulos tecnicos NR_VOTAVEL 28 e refazer periodicidade 2026.

Proveniencia: opcoes H, K e L ja concluídas. Reabre SOMENTE ZIP BWEB
locais para extrair a distribuicao POR SECAO do voto 28, com checkpoints
SHA por UF (uma passagem unica, nao 28 downloads). Os 499206 BU
individuais originais sao reutilizados a partir dos CSV SHA H.
Nunca sobrescreve derivados H/J/K/L; escreve apenas phase5h_*.
Nao consulta SQLite nem dados 2022.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime
import io
import json
import os
from pathlib import Path
import zipfile

from audit_bweb_candidate_28_2026 import read_k_report
from analyze_bweb_receipt_periodicity_2026 import score as minute_score
from analyze_bweb_seconds_2026 import (
    parse_original_second, group_to_series, test_periodicity, write_csv
)
from extract_bweb_received_2026 import (
    UFs, discover_archive, norm, VERSION as H_VERSION
)
from reconcile_stream import sha256
from urnas import root_path

VERSION = "phase5h-periodicity-corrected-v1"
FIELDS_28=("UF","municipio","zona","secao","votos_28")
EXPECTED={"valid":119300788,"13":53879538,"22":56104503,"number28":5246}
SIZES=(500,1000,2000)


def atomic_json(path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=Path(str(path)+".part")
    try:
        with tmp.open("w",encoding="utf-8") as f:
            json.dump(data,f,ensure_ascii=False,indent=2)
            f.write("\n");f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if tmp.exists():tmp.unlink()


def extract_nr28(zip_path,uf):
    """Uma passagem, somente linhas de Presidente/turno 1/numero 28."""
    counts=Counter()
    with zipfile.ZipFile(zip_path) as archive:
        members=[x for x in archive.namelist() if x.lower().endswith(".csv")]
        if len(members)!=1:
            raise RuntimeError("BWEB sem CSV unico: "+str(zip_path))
        with archive.open(members[0]) as stream:
            text=io.TextIOWrapper(stream,encoding="latin-1",
                                  errors="replace",newline="")
            reader=csv.DictReader(text,delimiter=";")
            headers={str(k).strip().replace("ï»¿","").replace("\ufeff",""):k
                     for k in reader.fieldnames or []}
            mandatory=("NR_TURNO","SG_UF","DS_CARGO_PERGUNTA","NR_VOTAVEL",
                       "QT_VOTOS","CD_MUNICIPIO","NR_ZONA","NR_SECAO")
            if not all(c in headers for c in mandatory):
                raise RuntimeError("Campos obrigatorios BWEB faltando em "+str(zip_path))
            get=lambda row,k:row[headers[k]]
            for row in reader:
                if (get(row,"NR_TURNO").strip()!="1"
                    or get(row,"DS_CARGO_PERGUNTA").strip().casefold()!="presidente"
                    or get(row,"NR_VOTAVEL").strip()!="28"):
                    continue
                if get(row,"SG_UF").strip().upper()!=uf:
                    raise RuntimeError("UF divergente no BWEB")
                ident=(uf,*[norm(get(row,k)) for k in
                            ("CD_MUNICIPIO","NR_ZONA","NR_SECAO")])
                amount=int(get(row,"QT_VOTOS"))
                if amount<0: raise RuntimeError("Votos de 28 negativos")
                counts[ident]+=amount
    return {k:v for k,v in counts.items() if v>0}


def write_nr28(path,rows):
    tmp=Path(str(path)+".part")
    try:
        with tmp.open("w",encoding="utf-8",newline="") as f:
            w=csv.writer(f,delimiter=";",lineterminator="\n")
            w.writerow(FIELDS_28)
            for ident,n in sorted(rows.items()):
                w.writerow((*ident,n))
            f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if tmp.exists():tmp.unlink()


def load_or_build_nr28(root,base,uf,expected_archive_sha,expected_votes):
    """Cache por UF vinculado ao SHA do ZIP e ao hash do resultado L."""
    data=base/f"phase5h_nr28_sections_{uf}.csv"
    manifest=base/f"phase5h_nr28_sections_{uf}.json"
    if data.is_file() and manifest.is_file():
        info=json.loads(manifest.read_text("utf-8"))
        if (info.get("version")==VERSION and
            info.get("archive_sha256")==expected_archive_sha and
            info.get("votes_28")==expected_votes and
            info.get("csv_sha256")==sha256(data)):
            counts={}
            with data.open(encoding="utf-8",newline="") as f:
                for row in csv.DictReader(f,delimiter=";"):
                    ident=(row["UF"],norm(row["municipio"]),norm(row["zona"]),
                           norm(row["secao"]))
                    if ident in counts or ident[0]!=uf:
                        raise RuntimeError("Duplicata ou UF incorreta no cache nr28")
                    counts[ident]=int(row["votos_28"])
            if sum(counts.values())!=expected_votes:
                raise RuntimeError("Votos nr28 do cache nao batem com L")
            print(f"[NR28 {uf}] cache SHA OK; votos={expected_votes:,}",flush=True)
            return counts,info
        raise RuntimeError("Checkpoint NR28 existe mas nao confere: "+str(manifest))
    archive,sha=discover_archive(root,uf)  # hash original do ZIP, sem rede
    if sha!=expected_archive_sha:
        raise RuntimeError("SHA ZIP BWEB diverge do relatorio L: "+uf)
    counts=extract_nr28(archive,uf)
    if sum(counts.values())!=expected_votes:
        raise RuntimeError(f"{uf}: nr28 por secao diverge da auditoria L")
    write_nr28(data,counts)
    info={"version":VERSION,"UF":uf,"archive_sha256":sha,
          "csv_sha256":sha256(data),"votes_28":sum(counts.values()),
          "sections_with_28":len(counts)}
    atomic_json(manifest,info)
    print(f"[NR28 {uf}] secoes com 28={len(counts):,}, votos={expected_votes:,}",flush=True)
    return counts,info


def corrected_bins(base,uf,number28):
    """Une os nulos tecnicos aos dados H pela chave eleitoral verdadeira."""
    reference=json.loads((base/"summary.json").read_text("utf-8"))
    if reference.get("version")!=H_VERSION:
        raise RuntimeError("Fonte H de versao desconhecida")
    info=reference["ufs"][uf]
    shard=base/f"received-{uf}.csv"
    if not shard.is_file() or sha256(shard)!=info["shard_sha256"]:
        raise RuntimeError("Cache BU alterado na UF "+uf)
    seconds=defaultdict(lambda:[0,0,0,0])
    minutes=defaultdict(lambda:[0,0,0,0])
    sec_times=0
    counted=Counter()
    keys_seen=set()
    with shard.open(encoding="utf-8-sig",newline="") as f:
        for row in csv.DictReader(f,delimiter=";"):
            if row["UF"]!=uf or row["turno"]!="1":
                raise RuntimeError("BU UF/turno invalido")
            ident=(uf,*[norm(row[k]) for k in ("municipio","zona","secao")])
            if ident in keys_seen:
                raise RuntimeError("BU duplicado em "+uf)
            keys_seen.add(ident)
            v28=number28.pop(ident,0)
            raw=int(row["votos_pres_validos"])
            value=raw-v28
            f22=int(row["votos_22"])
            l13=int(row["votos_13"])
            if min(value,f22,l13)<0 or f22+l13>value:
                raise RuntimeError("Correcao de validos impossivel na secao "+str(ident))
            stamp,precise=parse_original_second(row["DT_BU_RECEBIDO"])
            if not stamp or not precise:
                raise RuntimeError("Recepcao sem segundos explicitos em "+str(ident))
            if row["recebimento_minuto"]!=stamp[:16]:
                raise RuntimeError("Minutos do BU incoerentes")
            sec_times+=1
            for bucket,key in ((seconds,stamp),(minutes,stamp[:16])):
                target=bucket[key]
                for j,n in enumerate((1,value,f22,l13)):
                    target[j]+=n
            counted.update(sections=1,valid=value,flavio=f22,
                           lula=l13,nr28=v28)
    if counted["sections"]!=info["sections"]:
        raise RuntimeError("Numero de BU da UF nao bate com H")
    if number28:
        raise RuntimeError(f"{uf}: nr28 em secao inexistente na fonte H: {list(number28)[:3]}")
    return minutes,seconds,counted


def merge_group(target,source):
    for time,values in source.items():
        slot=target[time]
        for i,n in enumerate(values):
            slot[i]+=n


def run(root,minute_simulations=1000,second_simulations=200):
    if minute_simulations<100 or second_simulations<100:
        raise ValueError("Numero insuficiente de simulacoes")
    base=root/"analysis"/"periodicidade_bweb_2026"
    k,k_hash=read_k_report(base)
    lpath=base/"phase5g_nr28_reconciliation_2026_summary.json"
    if not lpath.is_file():
        raise RuntimeError("Execute a opcao L primeiro")
    l=json.loads(lpath.read_text("utf-8"))
    if (l.get("status")!="CONCILIACAO_COMPLETA_NR_28"
        or l.get("ufs_reconciled")!=len(UFs)
        or l.get("difference_after_excluding_nr_28")!=0):
        raise RuntimeError("Auditoria L ainda nao conciliou todas as UFs")
    minutes=defaultdict(lambda:[0,0,0,0])
    seconds=defaultdict(lambda:[0,0,0,0])
    totals=Counter()
    input_infos={}
    for uf in UFs:
        source=l["sources_by_uf"][uf]
        expected=int(k[uf]["diferenca_validos"])
        if source["votos_28"]!=expected:
            raise RuntimeError("Diferenca entre K e L na UF "+uf)
        n28,info=load_or_build_nr28(
            root,base,uf,source["sha256"],expected)
        byminute,bysecond,counter=corrected_bins(base,uf,n28)
        merge_group(minutes,byminute); merge_group(seconds,bysecond)
        totals.update(counter)
        input_infos[uf]=info
        print(f"[CORRIGIDO {uf}] validos={counter['valid']:,}; "
              f"nulos tecnicos={counter['nr28']:,}; secoes={counter['sections']:,}",flush=True)
    original_report=json.loads((base/"summary.json").read_text("utf-8"))
    if totals["sections"]!=original_report["sections"] or any(
        totals[raw]!=expected for raw,expected in
        (("valid",EXPECTED["valid"]),("flavio",EXPECTED["22"]),
         ("lula",EXPECTED["13"]),("nr28",EXPECTED["number28"]))):
        raise RuntimeError("Somas finais corrigidas nao batem com o TSE 2026")

    minute_trace=group_to_series(
        {k:v for k,v in minutes.items()})  # ordena por minuto; mesmos segundos nao separam BU
    second_trace=group_to_series(seconds)
    minute_path=base/"phase5h_minute_corrected_2026.csv"
    sec_path=base/"phase5h_second_corrected_2026.csv"
    write_csv(minute_path,minute_trace);write_csv(sec_path,second_trace)
    print(f"[MINUTOS CORRIGIDOS] {len(minute_trace)} pontos; calculando controles",flush=True)
    try:
        minute_test,_=minute_score(minute_trace,10000,minute_simulations,20261027)
    except ValueError as exc:
        minute_test={"status":"AMOSTRA_INSUFICIENTE","reason":str(exc)}
    groups={}
    for target in SIZES:
        batches=group_to_series(seconds,target)
        f=base/f"phase5h_blocks_{target}_corrected_2026.csv"
        write_csv(f,batches)
        try:
            outcome=test_periodicity(batches,10000,15,second_simulations,20261027)
        except ValueError as exc:
            outcome={"status":"AMOSTRA_INSUFICIENTE","reason":str(exc)}
        groups[str(target)]={"blocks":len(batches),
             "series_csv":str(f),"series_sha256":sha256(f),
             "periodicity":outcome}
        print(f"[BLOCO CORRIGIDO {target}] n={len(batches)}, "
              f"R2={outcome.get('period',{}).get('r2')}, "
              f"p_bloco={outcome.get('p_empirical',{}).get('blocks5')}",flush=True)
    summary={"version":VERSION,"status":"VALIDOS_PRESIDENCIAIS_CORRIGIDOS",
             "scope":"Somente Presidente turno 1 2026",
             "corrected_totals":dict(totals),
             "difference_valid_vs_official":totals["valid"]-EXPECTED["valid"],
             "delta_from_old_valids":-totals["nr28"],
             "initial_sections":totals["sections"],"distinct_minutes":len(minute_trace),
             "distinct_seconds":len(second_trace),
             "checkpoint_sources":input_infos,
             "source_K_sha256":k_hash,
             "source_L_sha256":sha256(lpath),
             "corrected_minutes_csv":str(minute_path),
             "corrected_minutes_sha256":sha256(minute_path),
             "corrected_seconds_csv":str(sec_path),
             "corrected_seconds_sha256":sha256(sec_path),
             "corrected_minute_periodicity":minute_test,
             "corrected_block_periodicities":groups,
             "limitations":[
               "Nao e fonte independente: BWEB e snapshots oficiais do TSE",
               "Nao inventa ordem entre BU recebidos no mesmo segundo",
               "A diferenca de 42 secoes exige conciliacao independente",
               "P-valores sao exploratorios e controles nao preservam toda geografia",
               "Dados originais H/J/K/L nao sao sobrescritos",
               "Uma unica leitura de ZIP BWEB ja baixado por UF na primeira execucao; checkpoints usados depois"
             ]}
    output=base/"phase5h_corrected_periodicity_2026_summary.json"
    atomic_json(output,summary)
    print(json.dumps({"status":summary["status"],
       "secoes":totals["sections"],
       "validos":totals["valid"],
       "nr28_reclassificados":totals["nr28"],
       "diferenca_validos_final":summary["difference_valid_vs_official"],
       "minute":minute_test,
       "blocks":{k:v["periodicity"] for k,v in groups.items()},
       "summary":str(output)},ensure_ascii=False,indent=2),flush=True)
    return summary


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root")
    parser.add_argument("--permutacoes-minuto",type=int,default=1000)
    parser.add_argument("--permutacoes-blocos",type=int,default=200)
    args=parser.parse_args()
    run(root_path(args.root),args.permutacoes_minuto,args.permutacoes_blocos)
