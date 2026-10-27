#!/usr/bin/env python3
"""Fase 5L: localizar diferença 42 em ZZ (eleitorado exterior), 1º turno 2026.

SEM download, SEM SQLite, SEM ZIP. Compara a contagem EA20 UF ZZ
(st=1351) à contagem BWEB ZZ (1309) e aos arquivos EA20 de
municípios/locais do exterior já guardados pela coleta original.
Se possível, confirma SHA-256 do manifesto antigo. Este teste
não pressupõe que um contador ST descreva votos válidos nem
individualiza seções que não estejam listadas em sua fonte.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
import json
import os
from pathlib import Path

from extract_bweb_received_2026 import VERSION as H_VERSION
from reconcile_stream import sha256
from urnas import root_path
from certify_2026_all_section_keys import count_snapshot

VERSION="phase5l-exterior-zz-section-gap-2026-v1"
EXPECTED_BWEB=1309
EXPECTED_UF_ST=1351
EXPECTED_DELTA=42
SOURCE_RUN=Path("data/forensics/runs")
CACHE=Path("analysis/periodicidade_bweb_2026")
HEAD=("municipio","nome_configuracao","BWEB_secoes",
      "EA20_municipal_st","EA20_municipal_ts",
      "diferenca_st_menos_BWEB","diferenca_ts_menos_BWEB",
      "EA20_municipal_dia","EA20_municipal_hora","SHA_verificado",
      "arquivo_ea20")


def as_int(raw):
    return int(str(raw).replace(".","").strip())


def atomic_json(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    part=Path(str(path)+".part")
    try:
        with part.open("w",encoding="utf-8") as f:
            json.dump(obj,f,ensure_ascii=False,indent=2)
            f.write("\n");f.flush();os.fsync(f.fileno())
        os.replace(part,path)
    finally:
        if part.exists():part.unlink()


def atomic_csv(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    part=Path(str(path)+".part")
    try:
        with part.open("w",encoding="utf-8",newline="") as f:
            w=csv.DictWriter(f,fieldnames=HEAD,delimiter=";",
                             lineterminator="\n")
            w.writeheader();w.writerows(rows)
            f.flush();os.fsync(f.fileno())
        os.replace(part,path)
    finally:
        if part.exists():part.unlink()


def manifest_index(path):
    if not path.is_file():
        raise RuntimeError("Manifesto da coleta original nao encontrado: "+str(path))
    records={}
    with path.open(encoding="utf-8-sig") as f:
        for line in f:
            if not line.strip():continue
            record=json.loads(line)
            kind=record.get("kind")
            if record.get("uf")!="zz" or kind not in ("state","municipality"):
                continue
            if record.get("error"): continue
            key=("uf",0) if kind=="state" else ("mu",as_int(record["municipality_code"]))
            if key in records:
                raise RuntimeError("Manifesto possui item ZZ duplicado "+str(key))
            digest=record.get("sha256","")
            if len(digest)!=64:
                raise RuntimeError("Item de manifesto sem hash SHA "+str(key))
            records[key]=digest
    if ("uf",0) not in records:
        raise RuntimeError("Manifesto original nao contem EA20 estadual ZZ")
    return records


def configured_localities(path):
    """Nomes auxiliares da configuracao; nao e fonte de numero de secoes."""
    if not path.is_file():
        return {}
    data=json.loads(path.read_text(encoding="utf-8-sig"))
    region=next((x for x in data.get("abr",[])
                 if str(x.get("cd","")).lower()=="zz"),None)
    return {as_int(x["cd"]):str(x.get("nm",""))
            for x in region.get("mu",[])} if region else {}


def bweb_group(shard):
    counts=Counter()
    sections=set()
    with shard.open(encoding="utf-8-sig",newline="") as f:
        for row in csv.DictReader(f,delimiter=";"):
            if row["UF"]!="ZZ" or as_int(row["turno"])!=1:
                raise RuntimeError("BWEB ZZ possui UF ou turno diferente")
            municipality=as_int(row["municipio"])
            identity=(municipality,as_int(row["zona"]),as_int(row["secao"]))
            if identity in sections:
                raise RuntimeError("Chave BWEB ZZ duplicada "+repr(identity))
            sections.add(identity)
            counts[municipality]+=1
    if len(sections)!=EXPECTED_BWEB:
        raise RuntimeError("BWEB exterior numero de secoes inesperado")
    return counts


def verify(path,digest):
    if not path.is_file():
        raise RuntimeError("Fonte original arquivada nao encontrada "+str(path))
    if sha256(path)!=digest:
        raise RuntimeError("SHA-256 divergente do manifesto original: "+str(path))


def run(root,repo=Path(".")):
    repo=repo.resolve()
    meta=repo/"data/forensics/analysis/phase2_sections_summary.json"
    if not meta.is_file():
        raise RuntimeError("Fase 2 versionada indisponivel")
    record=json.loads(meta.read_text(encoding="utf-8"))
    parent=repo/SOURCE_RUN/record["latest_snapshot"]
    cache=root/CACHE
    h=cache/"summary.json"
    if not h.is_file():
        raise RuntimeError("A opcao H precisa ter sido executada")
    src=json.loads(h.read_text(encoding="utf-8"))
    if src.get("version")!=H_VERSION or src["ufs"]["ZZ"]["sections"]!=EXPECTED_BWEB:
        raise RuntimeError("Caderno BWEB H nao e o original 2026 esperado")
    shard=cache/"received-ZZ.csv"
    verify(shard,src["ufs"]["ZZ"]["shard_sha256"])
    bweb=bweb_group(shard)
    seals=manifest_index(parent/"manifest.jsonl")
    uf=parent/"live/uf/zz.json"
    verify(uf,seals[("uf",0)])
    state=count_snapshot(uf)
    if state["st"]!=EXPECTED_UF_ST or state["st"]-EXPECTED_BWEB!=EXPECTED_DELTA:
        raise RuntimeError("Diferenca UF ZZ de 42 nao confirmada")
    if state["ts"]<state["st"]:
        raise RuntimeError("Contador total de seções ZZ menor do que totalizado")

    names=configured_localities(parent/"config/municipios.json")
    municipality_dir=parent/"live/municipio/zz"
    files={}
    if municipality_dir.is_dir():
        for p in municipality_dir.glob("*.json"):
            m=as_int(p.stem)
            if m in files:
                raise RuntimeError("Codigo de municipio ZZ duplicado")
            files[m]=p
    all_codes=sorted(set(bweb)|set(files)|set(names))
    results=[]
    sums=Counter()
    counts=Counter()
    records_ok=0
    for code in all_codes:
        file=files.get(code)
        if file is not None:
            if ("mu",code) in seals:
                verify(file,seals[("mu",code)])
                seal="SIM"
                records_ok+=1
            else:
                seal="SEM_MANIFESTO_ORIGINAL"
            observed=count_snapshot(file)
            municipal_st=observed["st"]
            municipal_ts=observed["ts"]
            dt=observed["date"]; ht=observed["time"]
            sums["municipal_st"]+=municipal_st
            sums["municipal_ts"]+=municipal_ts
            counts["files"]+=1
            if seal!="SIM":counts["unsealed"]+=1
        else:
            municipal_st=municipal_ts=""
            dt=ht=""
            seal="EA20_NAO_ARQUIVADO"
            counts["missing"]+=1
        n=bweb.get(code,0)
        sums["bweb"]+=n
        gap=municipal_st-n if municipal_st!="" else ""
        if gap!="":
            sums["signed_deltas"]+=gap
            if gap>0:counts["positive_delta"]+=1
            if gap<0:counts["negative_delta"]+=1
            if gap:counts["municipios_com_diferenca"]+=1
        results.append(dict(zip(HEAD,(
            str(code).zfill(5),names.get(code,""),n,
            municipal_st,municipal_ts,gap,
            municipal_ts-n if municipal_ts!="" else "",
            dt,ht,seal,str(file) if file else ""))))
    if sums["bweb"]!=EXPECTED_BWEB:
        raise RuntimeError("Soma de BU por municipio ZZ nao e 1309")
    fully_covered=(all(x["EA20_municipal_st"]!="" for x in results)
                   and counts["unsealed"]==0)
    if fully_covered and sums["signed_deltas"]!=sums["municipal_st"]-EXPECTED_BWEB:
        raise RuntimeError("Identidade municipal incorreta")
    national={
        "ZZ_st_UF":state["st"],"ZZ_ts_UF":state["ts"],
        "ZZ_BWEB_sections":EXPECTED_BWEB,
        "ZZ_st_UF_minus_BWEB":EXPECTED_DELTA,
        "EA20_municipal_st_sum":sums["municipal_st"],
        "EA20_municipal_ts_sum":sums["municipal_ts"],
        "UF_st_minus_municipal_st_sum":state["st"]-sums["municipal_st"]
          if fully_covered else None,
        "municipal_st_sum_minus_BWEB":sums["municipal_st"]-EXPECTED_BWEB
          if fully_covered else None,
        "municipal_st_minus_BWEB_partial":sums["signed_deltas"],
        "EA20_municipal_files":counts["files"],
        "EA20_municipal_archived_SHA_validated":records_ok,
        "EA20_municipal_sources_missing_or_unsealed":counts["missing"]+counts["unsealed"],
        "municipalities_with_any_st_discrepancy":counts["municipios_com_diferenca"],
        "municipalities_with_st_greater_than_BWEB":counts["positive_delta"],
        "municipalities_with_st_less_than_BWEB":counts["negative_delta"],
        "all_municipal_counters_compared":fully_covered
    }
    if not fully_covered:
        status="COBERTURA_MUNICIPAL_INCOMPLETA"
    elif state["st"]-sums["municipal_st"]==EXPECTED_DELTA and sums["municipal_st"]==EXPECTED_BWEB:
        status="DIFERENCA_APENAS_NO_AGREGADO_ZZ"
    elif sums["municipal_st"]-EXPECTED_BWEB==EXPECTED_DELTA and state["st"]==sums["municipal_st"]:
        status="DIFERENCA_LOCALIZADA_NOS_CONTADORES_MUNICIPAIS_ZZ"
    else:
        status="DIFERENCA_DIVIDIDA_ENTRE_NIVEIS_ZZ"
    output={
        "version":VERSION,"status":status,
        "scope":"1o turno 2026 exterior ZZ, snapshots locais anteriores",
        "input_provenance":{
            "phase2_sha256":sha256(meta),
            "original_manifest_sha256":sha256(parent/"manifest.jsonl"),
            "bweb_h_manifest_sha256":sha256(h),
            "bweb_zz_shard_sha256":sha256(shard),
            "EA20_ZZ_state_sha256":sha256(uf)},
        "state":state,"national":national,
        "municipal_detail":results,
        "limitations":[
            "EA20 ST e TS sao contadores, nao identificadores de secoes",
            "Municipio/local de votacao BWEB e municipio de EA20 devem ser semanticamente comparaveis",
            "Se contadores vieram de momentos distintos, gaps podem refletir instante de captura",
            "Nulo tecnico do numero 28 ja foi conciliado; nao implica 42 seções inexistentes",
            "Sem ZZ-EA16 de referencia SHA, nao construir lista artificial de 42 chaves",
            "Nao usa rede, SQLite, ZIP BWEB nem dados 2022"]}
    out_csv=cache/"phase5l_zz_municipal_counter_breakdown_2026.csv"
    atomic_csv(out_csv,results)
    output["municipal_csv"]=str(out_csv)
    output["municipal_csv_sha256"]=sha256(out_csv)
    summary=cache/"phase5l_zz_42_sections_2026_summary.json"
    atomic_json(summary,output)
    print("[ZZ] 1.351 EA20 versus 1.309 BWEB = +42, por municipio:",flush=True)
    for row in sorted(results,key=lambda x:(
            -abs(x["diferenca_st_menos_BWEB"]) if x["diferenca_st_menos_BWEB"]!="" else 0,x["municipio"])):
        if row["diferenca_st_menos_BWEB"] not in ("",0):
            print(f"  {row['municipio']} {row['nome_configuracao']}: "
                  f"EA20={row['EA20_municipal_st']}, BWEB={row['BWEB_secoes']}, "
                  f"gap={row['diferenca_st_menos_BWEB']:+}, "
                  f"snapshot={row['EA20_municipal_dia']} {row['EA20_municipal_hora']}",flush=True)
    print(json.dumps({"status":status,"national":national,
        "file":str(summary)},ensure_ascii=False,indent=2),flush=True)
    return output


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root")
    parser.add_argument("--repo",type=Path,default=Path(__file__).resolve().parent)
    args=parser.parse_args()
    run(root_path(args.root),args.repo)
