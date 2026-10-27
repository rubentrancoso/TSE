#!/usr/bin/env python3
"""Fase 5F: reconciliacao BWEB x apuracao por UF dos votos validos de 2026.

Somente artefatos existentes: H:/.../analysis/periodicidade_bweb_2026/received-UF.csv
e data/forensics/analysis/uf_candidate_reconciliation.csv no repositorio.
Nao reabre ZIP, nao baixa, nao usa SQLite, nao le microdados de 2022.

A classe 'outros' e uma SUBTRACAO de todos os votos validos
menos candidatos 13 e 22. Divergencia nao prova adulteracao.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
import hashlib
import json
import os
from pathlib import Path

from reconcile_stream import sha256
from urnas import root_path
from extract_bweb_received_2026 import VERSION as INPUT_VERSION

VERSION="bweb-vs-uf-totals-2026-v1"
DEFAULT_REFERENCE=Path("data/forensics/analysis/uf_candidate_reconciliation.csv")
EXPECTED_NATIONAL={"valid":119300788,"13":53879538,"22":56104503}
COLUMNS=("UF","secoes_BWEB","validos_BWEB","validos_UF_oficial",
         "diferenca_validos","votos_13_BWEB","votos_13_UF_oficial",
         "diferenca_13","votos_22_BWEB","votos_22_UF_oficial",
         "diferenca_22","demais_BWEB","demais_UF_oficial",
         "diferenca_demais","brancos_BWEB","nulos_BWEB")


def official(reference):
    if not reference.is_file():
        raise RuntimeError("Tabela oficial por UF nao existe no repo: "+str(reference))
    uf_candidates={}
    with reference.open(encoding="utf-8-sig",newline="") as f:
        for row in csv.DictReader(f):
            uf=row["uf"].strip().upper()
            candidate=str(int(row["candidate"]))
            key=(uf,candidate)
            if key in uf_candidates:
                raise RuntimeError("Candidato por UF duplicado em referencia: "+repr(key))
            votes=int(row["uf_votes"])
            if votes<0 or votes!=int(row["sum_municipal_votes"]):
                raise RuntimeError("Total de votos invalido na referencia: "+repr(key))
            uf_candidates[key]=votes
    groups={}
    for (uf,candidate),value in uf_candidates.items():
        groups.setdefault(uf,Counter())[candidate]+=value
    if len(groups)!=28:
        raise RuntimeError("A referencia 2026 nao cobre 27 UFs + ZZ")
    totals=Counter()
    for votes in groups.values():totals.update(votes)
    if (sum(totals.values())!=EXPECTED_NATIONAL["valid"] or
        totals["13"]!=EXPECTED_NATIONAL["13"] or
        totals["22"]!=EXPECTED_NATIONAL["22"]):
        raise RuntimeError("Referencia diverge da ultima apuracao 2026")
    return groups,sha256(reference)


def sum_bweb(base):
    summaryfile=base/"summary.json"
    if not summaryfile.is_file():
        raise RuntimeError("Opcao H nao executada: fonte individual inexistente")
    summary=json.loads(summaryfile.read_text("utf-8"))
    if summary.get("version")!=INPUT_VERSION:
        raise RuntimeError("Versao de checkpoints diferente da opcao H")
    groups={}
    for uf,info in sorted(summary["ufs"].items()):
        shard=base/f"received-{uf}.csv"
        if not shard.is_file() or sha256(shard)!=info["shard_sha256"]:
            raise RuntimeError("Arquivo BWEB ou SHA divergente: "+str(shard))
        cnt=Counter()
        with shard.open(encoding="utf-8-sig",newline="") as f:
            for row in csv.DictReader(f,delimiter=";"):
                if row["UF"]!=uf or str(int(row["turno"]))!="1":
                    raise RuntimeError("UF ou turno divergente do shard "+uf)
                valid=int(row["votos_pres_validos"])
                allvotes=int(row["votos_pres_total"])
                l=int(row["votos_13"])
                fav=int(row["votos_22"])
                blank=int(row["brancos"])
                null=int(row["nulos"])
                if (min(valid,allvotes,l,fav,blank,null)<0 or
                    allvotes!=valid+blank+null or l+fav>valid):
                    raise RuntimeError("Contagem impossivel em "+uf+"/"+row["secao"])
                cnt.update({"sections":1,"valid":valid,"13":l,"22":fav,
                            "other":valid-l-fav,"blank":blank,"null":null})
        if cnt["sections"]!=info["sections"]:
            raise RuntimeError("Numero de secoes difere do cache de H: "+uf)
        groups[uf]=cnt
    if sum(x["sections"] for x in groups.values())!=summary["sections"]:
        raise RuntimeError("Total de secoes nacional difere de H")
    return groups,sha256(summaryfile)


def compare(bweb,refs):
    rows=[]
    for uf in sorted(set(bweb)|set(refs)):
        if uf not in bweb or uf not in refs:
            raise RuntimeError("Referencia e BU nao cobrem mesmas UFs: "+uf)
        b=bweb[uf]
        off=refs[uf]
        official_total=sum(off.values())
        official_other=official_total-off["13"]-off["22"]
        rows.append(dict(zip(COLUMNS,(
            uf,b["sections"],b["valid"],official_total,b["valid"]-official_total,
            b["13"],off["13"],b["13"]-off["13"],
            b["22"],off["22"],b["22"]-off["22"],
            b["other"],official_other,b["other"]-official_other,
            b["blank"],b["null"]))))
    return rows


def write_csv(path,rows):
    tmp=Path(str(path)+".part")
    try:
        with tmp.open("w",encoding="utf-8",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=COLUMNS,delimiter=";",
                                  lineterminator="\n")
            writer.writeheader();writer.writerows(rows)
            f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if tmp.exists():tmp.unlink()


def atomic_json(path,obj):
    tmp=Path(str(path)+".part")
    try:
        with tmp.open("w",encoding="utf-8") as f:
            json.dump(obj,f,ensure_ascii=False,indent=2)
            f.write("\n");f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if tmp.exists():tmp.unlink()


def run(root,reference=DEFAULT_REFERENCE):
    folder=root/"analysis"/"periodicidade_bweb_2026"
    off,ref_sha=official(reference)
    bu,manifest_sha=sum_bweb(folder)
    rows=compare(bu,off)
    national={column:sum(row[column] for row in rows)
              for column in COLUMNS if column!="UF"}
    national["diff_sections_vs_snapshot_499248"]=national["secoes_BWEB"]-499248
    national["expected_valid_diff"]=5246
    if (national["validos_BWEB"]-national["validos_UF_oficial"]
        !=national["diferenca_validos"] or
        national["diferenca_validos"]!=national["diferenca_demais"]+
        national["diferenca_13"]+national["diferenca_22"]):
        raise RuntimeError("Reconciliacao interna de votos impossivel")
    path=folder/"phase5f_reconciliation_by_uf_2026.csv"
    write_csv(path,rows)
    ordered=sorted(rows,key=lambda x:(-abs(x["diferenca_validos"]),x["UF"]))
    summary={
        "version":VERSION,
        "status":"CONCLUIDO_CONFERENCIA_POR_UF",
        "reference":str(reference),"reference_sha256":ref_sha,
        "source_H_sha256":manifest_sha,
        "by_uf_csv":str(path),"by_uf_sha256":sha256(path),
        "national":national,
        "ufs_with_nonzero_valid_difference":sum(
            row["diferenca_validos"]!=0 for row in rows),
        "largest_uf_differences":ordered[:10],
        "limitations":[
            "Votos 'demais' sao validos totais menos 13 e 22, sem identificar motivo/candidato",
            "O codigo anterior classificou apenas Branco/Nulo como invalidos; outros DS_TIPO_VOTAVEL poderiam exigir classificacao diferenciada",
            "A diferenca de 42 secoes compara contagem BWEB e st final e pode ter escopo distinto",
            "Nao concluir causa da divergencia sem conferir categorias originais e cobertura por UF",
            "Nao relê ZIPs, nao baixa nada, nao abre SQLite, nao acessa dados de 2022"]}
    pathj=folder/"phase5f_reconciliation_2026_summary.json"
    atomic_json(pathj,summary)
    print("FASE 5F — VOTOS PRESIDENCIAIS 2026, POR UF",flush=True)
    for row in ordered:
        if any(row[x] for x in
               ("diferenca_validos","diferenca_13","diferenca_22")):
            print(f"{row['UF']}: validos {row['diferenca_validos']:+,} "
                  f"(13={row['diferenca_13']:+,};22={row['diferenca_22']:+,}; "
                  f"demais={row['diferenca_demais']:+,}), "
                  f"BU={row['secoes_BWEB']:,}",flush=True)
    print(json.dumps({"status":summary["status"],"national":national,
           "ufs_com_diferencas":summary["ufs_with_nonzero_valid_difference"],
           "file":str(pathj)},ensure_ascii=False,indent=2),flush=True)
    return summary


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",help="Raiz local H: ja existente")
    parser.add_argument("--reference",type=Path,default=DEFAULT_REFERENCE)
    args=parser.parse_args()
    run(root_path(args.root),args.reference)
