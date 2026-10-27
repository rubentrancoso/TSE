#!/usr/bin/env python3
"""Fase 5C — extrair DT_BU_RECEBIDO dos BWEB 2026 ja arquivados.

NAO baixa arquivos, NAO usa SQLite ou dados 2022. Cada recurso ZIP
deve ter .meta.json com SHA-256, registrado pela coleta original.
Preserva a resolucao observada dos instantes: não inventa ordem em empates.
Os timestamps BWEB sao campos publicados pelo TSE e nao um log
independente de recepcao. Um horario so e tratado como campo recebido,
nao evidencia independente de autenticidade da urna.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
import io
import json
import os
from pathlib import Path
from datetime import datetime
import zipfile

from reconcile_stream import sha256
from urnas import root_path

VERSION="bweb-reception-per-section-2026-v1"
UFs=tuple("AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO ZZ".split())
HEAD=("UF","municipio","zona","secao","turno","DT_BU_RECEBIDO",
      "recebimento_minuto","arquivo_sha256")


def atomic_json(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=Path(str(path)+".part")
    try:
        with tmp.open("w",encoding="utf-8") as f:
            json.dump(obj,f,ensure_ascii=False,indent=2)
            f.write("\n");f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if tmp.exists():tmp.unlink()


def norm(v):
    return str(int(str(v).strip()))


def time_normalized(value):
    raw=str(value or "").strip()
    if not raw:
        return ""
    fmts=("%d/%m/%Y %H:%M:%S","%d/%m/%Y %H:%M",
          "%Y-%m-%d %H:%M:%S","%Y-%m-%d %H:%M")
    for fmt in fmts:
        try:
            t=datetime.strptime(raw,fmt)
            if t.year!=2026:
                raise ValueError("Timestamp fora de 2026")
            return t.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            pass
    raise ValueError("DT_BU_RECEBIDO invalido: "+repr(raw))


def discover_archive(root,uf):
    directory=root/"raw"/"bu"/uf
    archives=sorted(p for p in directory.glob("*.zip")
                    if "bweb_1t_" in p.name.lower()
                    and ("_"+uf.lower()+"_" in p.name.lower()))
    if len(archives)!=1:
        raise RuntimeError(f"{uf}: esperado UM BWEB primeiro turno existente; encontrados {len(archives)}")
    path=archives[0]
    manifest=Path(str(path)+".meta.json")
    if not manifest.is_file():
        raise RuntimeError("Sem manifesto SHA anterior, nao presumir origem: "+str(path))
    details=json.loads(manifest.read_text("utf-8"))
    h=str(details.get("sha256",""))
    if len(h)!=64 or not all(c in "0123456789abcdef" for c in h):
        raise RuntimeError("Manifesto sem SHA-256: "+str(manifest))
    if sha256(path)!=h:
        raise RuntimeError("ZIP BWEB nao coincide com SHA-256 original: "+str(path))
    return path,h


def extract_archive(path,uf,digest):
    """Streaming dentro do zip; retorna uma linha por BU presidencial."""
    timestamps={}
    observed=Counter()
    with zipfile.ZipFile(path) as z:
        members=[x for x in z.namelist() if x.lower().endswith(".csv")]
        if len(members)!=1:
            raise RuntimeError("BWEB esperado com um CSV: "+str(path))
        with z.open(members[0]) as binary:
            text=io.TextIOWrapper(binary,encoding="latin-1",
                                  newline="",errors="replace")
            reader=csv.DictReader(text,delimiter=";")
            headers={str(k).strip().replace("ï»¿","").replace("\ufeff",""):k
                     for k in reader.fieldnames or []}
            required={"NR_TURNO","SG_UF","CD_MUNICIPIO","NR_ZONA","NR_SECAO",
                      "DS_CARGO_PERGUNTA","DT_BU_RECEBIDO"}
            if not required.issubset(headers):
                raise RuntimeError("Sem campos BWEB obrigatorios: "+str(sorted(required-set(headers))))
            col=lambda row,k:row[headers[k]]
            for r in reader:
                observed["rows"]+=1
                if col(r,"DS_CARGO_PERGUNTA").strip().casefold()!="presidente":
                    continue
                if norm(col(r,"NR_TURNO"))!="1":
                    continue
                if col(r,"SG_UF").strip().upper()!=uf:
                    raise RuntimeError("UF divergente no CSV "+str(path))
                ident=(uf,*[norm(col(r,k)) for k in
                            ("CD_MUNICIPIO","NR_ZONA","NR_SECAO")],"1")
                raw=col(r,"DT_BU_RECEBIDO").strip()
                normalized=time_normalized(raw)
                if ident in timestamps:
                    old=timestamps[ident]
                    if old[6]!=normalized:
                        raise RuntimeError("Mesmo BU tem distintos minutos de recepcao: "+repr(ident))
                    observed["repeated_rows"]+=1
                else:
                    timestamps[ident]=(*ident,raw,normalized,digest)
                    observed["unique_sections"]+=1
                    if not normalized:
                        observed["without_time"]+=1
    return timestamps,dict(observed)


def serialize(path,items):
    tmp=Path(str(path)+".part")
    try:
        with tmp.open("w",encoding="utf-8",newline="") as f:
            writer=csv.writer(f,delimiter=";",lineterminator="\n")
            writer.writerow(HEAD)
            for k in sorted(items):
                writer.writerow(items[k])
            f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if tmp.exists():tmp.unlink()


def run(root):
    dest=root/"analysis"/"periodicidade_bweb_2026"
    dest.mkdir(parents=True,exist_ok=True)
    counts=Counter()
    summaries={}
    shards=[]
    for uf in UFs:
        path,digest=discover_archive(root,uf)
        shard=dest/f"received-{uf}.csv"
        state=dest/f"received-{uf}.summary.json"
        if state.is_file() and shard.is_file():
            previous=json.loads(state.read_text("utf-8"))
            if (previous.get("version")==VERSION and
                previous.get("source_sha256")==digest and
                previous.get("shard_sha256")==sha256(shard)):
                info=previous
                print(f"[BWEB {uf}] cache SHA OK, secoes={info['sections']:,}",flush=True)
            else:
                raise RuntimeError("Checkpoint BWEB incoerente: "+str(state))
        else:
            sections,observed=extract_archive(path,uf,digest)
            serialize(shard,sections)
            info={"version":VERSION,"UF":uf,"archive":str(path),
                  "source_sha256":digest,"shard":str(shard),
                  "shard_sha256":sha256(shard),
                  "sections":len(sections),"stats":observed,
                  "distinct_minutes":len(set(x[6] for x in sections.values() if x[6])),
                  "without_time":sum(not x[6] for x in sections.values())}
            atomic_json(state,info)
            print(f"[BWEB {uf}] extraidas {len(sections):,} secoes com recepcao; SHA OK",flush=True)
        summaries[uf]=info
        shards.append(shard)
        counts["sections"]+=info["sections"]
        counts["without_time"]+=info["without_time"]

    # Preserva as fontes por UF; nao cria ordenacao arbitraria para empates.
    report={"version":VERSION,"status":"EXTRAIDOS_METADADOS_RECEBIMENTO_2026",
            "source_kind":"DT_BU_RECEBIDO official TSE BWEB data",
            "round":1,"ufs":summaries,
            "sections":counts["sections"],"without_time":counts["without_time"],
            "shard_count":len(shards),
            "join_key":"UF/municipio/zona/secao/turno",
            "shards":[str(p) for p in shards],
            "limitations":["O campo BWEB nao e captura independente do sistema oficial",
                "Tempo pode ter precisao de minuto; empate de urnas nao tem ordem conhecida",
                "BWEB nao define automaticamente o instante de publicacao nacional",
                "Somente dados 2026 e ZIPs preexistentes; sem novo download ou indice SQLite"]}
    atomic_json(dest/"summary.json",report)
    print("DT_BU_RECEBIDO extraido; secoes:",counts["sections"],
          "faltando horario:",counts["without_time"],flush=True)
    print("Resumo:",dest/"summary.json",flush=True)
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root")
    args=parser.parse_args()
    run(root_path(args.root))
