#!/usr/bin/env python3
"""Fase 5K: cotejo nacional EA16 x BWEB por chave; identificacao do nivel de 42.

Usa somente EA16 preexistentes com SHA da fase 3A e received-UF.csv com
SHA da fase H. Opcionalmente le snapshots UF/BR da coleta ja arquivada,
sem rede, sem ZIP BWEB e sem SQLite. Dados SOMENTE de 2026.
Contador ST nao traz a lista de secoes: nao converta divergencia de
contadores em supostas chaves eleitorais ausentes.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
import json
import os
from pathlib import Path

from extract_bweb_received_2026 import UFs,VERSION as H_VERSION
from reconcile_stream import sha256
from urnas import root_path

VERSION="phase5k-national-ea16-bweb-2026-v1"
LOC=Path("analysis/periodicidade_bweb_2026")
EXPECTED=499206
SNAPSHOT_ST=499248
VALID_FINAL=119300788
HEAD=("UF","EA16_principal","BWEB_secoes","chaves_EA16_sem_BWEB",
      "chaves_BWEB_sem_EA16","EA16_bruto_status",
      "EA20_UF_st_arquivado","EA20_UF_ts_arquivado",
      "EA20_UF_st_menos_BWEB","EA20_UF_ts_menos_BWEB","EA20_UF_gerado_em")

def norm(raw):
    return int(str(raw).strip())

def row_key(uf,m,z,s):
    return (uf,norm(m),norm(z),norm(s))

def sha_safe(path,expected):
    if not path.is_file():
        return False
    if sha256(path)!=expected:
        raise RuntimeError("SHA de arquivo anteriormente certificado divergente: "+str(path))
    return True

def ea16_candidates(repo,archive_root,uf):
    name=f"{uf.lower()}-p003220-cs.json"
    return (
        repo/"data"/"forensics"/"phase3"/"raw"/"ea16"/name,
        repo/"data"/"forensics"/"section-config"/"ea16"/name,
        archive_root/"phase3"/"raw"/"ea16"/name,
        archive_root/"section-config"/"ea16"/name
    )

def parse_ea16(path,uf):
    data=json.loads(path.read_text(encoding="utf-8-sig"))
    abr=next((x for x in data.get("abr",[])
              if str(x.get("cd","")).casefold()==uf.lower()),None)
    if abr is None and len(data.get("abr",[]))==1:
        abr=data["abr"][0]
    if abr is None: raise RuntimeError("UF faltando em EA16 "+uf)
    principal=set()
    aggregated=set()
    for mu in abr.get("mu",[]):
        for zo in mu.get("zon",[]):
            for sec in zo.get("sec",[]):
                k=row_key(uf,mu["cd"],zo["cd"],sec["ns"])
                if k in principal or k in aggregated:
                    raise RuntimeError("Seção duplicada em EA16: "+str(k))
                (aggregated if sec.get("nsp") else principal).add(k)
    return principal,aggregated

def parse_bweb_shard(path,uf):
    keys=set()
    with path.open(encoding="utf-8-sig",newline="") as f:
        reader=csv.DictReader(f,delimiter=";")
        for r in reader:
            if r["UF"]!=uf or norm(r["turno"])!=1:
                raise RuntimeError("UF/turno inesperado no shard "+uf)
            k=row_key(uf,r["municipio"],r["zona"],r["secao"])
            if k in keys:
                raise RuntimeError("Chave BU duplicada: "+str(k))
            keys.add(k)
    return keys

def atomic_csv(path,fields,rows):
    tmp=Path(str(path)+".part")
    try:
        with tmp.open("w",encoding="utf-8",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=fields,delimiter=";",
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
            json.dump(obj,f,indent=2,ensure_ascii=False)
            f.write("\n");f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if tmp.exists():tmp.unlink()

def count_snapshot(path):
    raw=json.loads(path.read_text(encoding="utf-8-sig"))
    s=raw.get("s",{})
    if "st" not in s or "ts" not in s:
        raise RuntimeError("Snapshot EA20 sem st/ts: "+str(path))
    return {"st":int(str(s["st"]).replace(".","")),
            "ts":int(str(s["ts"]).replace(".","")),
            "date":str(raw.get("dt") or raw.get("dg") or ""),
            "time":str(raw.get("ht") or raw.get("hg") or ""),
            "path":str(path),"sha256":sha256(path)}

def run(root,repo=Path(".")):
    repo=repo.resolve()
    source3=repo/"data/forensics/analysis/phase3_arrivals_summary.json"
    source2=repo/"data/forensics/analysis/phase2_sections_summary.json"
    frozen=repo/"data/forensics/analysis/phase5a_presidential_national_2026.csv"
    for f in (source3,source2,frozen):
        if not f.is_file():
            raise RuntimeError("Falta referencia versionada: "+str(f))
    third=json.loads(source3.read_text(encoding="utf-8"))
    phase2=json.loads(source2.read_text(encoding="utf-8"))
    with frozen.open(encoding="utf-8-sig",newline="") as f:
        snapshots=list(csv.DictReader(f))
    if not snapshots or int(snapshots[-1]["st"])!=SNAPSHOT_ST or int(snapshots[-1]["vv"])!=VALID_FINAL:
        raise RuntimeError("Snapshot final diferente da referencia 2026")
    folder=root/LOC
    h=folder/"summary.json"
    if not h.is_file():raise RuntimeError("Cache H nao encontrado")
    manifest=json.loads(h.read_text(encoding="utf-8"))
    if manifest.get("version")!=H_VERSION or manifest.get("sections")!=EXPECTED:
        raise RuntimeError("Manifesto H inesperado")
    if set(manifest.get("ufs",{}))!=set(UFs):
        raise RuntimeError("Manif. H nao cobre 27 UFs + ZZ")
    hashes={r["uf"]:r["sha256"] for r in third["sources"] if r.get("sha256")}
    if set(UFs)-{"ZZ"}!=set(hashes):
        raise RuntimeError("Inventario EA16 da fase 3 nao cobre 27 UFs")
    run_dir=repo/"data"/"forensics"/"runs"/phase2["latest_snapshot"]/"live"/"uf"
    found_uf_files=0
    rows=[]
    anomalies=[]
    snapshots_summary={}
    ea16_sum=0
    bweb_sum=0
    matched_uf=0
    missing_sources=[]
    uf_st_total=0
    uf_bweb_for_st=0
    for uf in UFs:
        shard=folder/f"received-{uf}.csv"
        info=manifest["ufs"][uf]
        if not sha_safe(shard,info["shard_sha256"]):
            raise RuntimeError("Falta cache BWEB ou SHA: "+str(shard))
        bweb=parse_bweb_shard(shard,uf)
        if len(bweb)!=info["sections"]:
            raise RuntimeError("Contagem BWEB difere do checkpoint "+uf)
        bweb_sum+=len(bweb)
        original=""
        ea_keys=None
        status="NAO_APLICAVEL_EXTERIOR" if uf=="ZZ" else "EA16_LOCAL_NAO_ENCONTRADO"
        if uf!="ZZ":
            ea16_sum+=third["ufs"][uf]["sections"]
            for p in ea16_candidates(repo,root,uf):
                if p.is_file():
                    if not sha_safe(p,hashes[uf]):
                        raise RuntimeError("SHA arquivo EA16 nao confere")
                    original=str(p)
                    ea_keys,others=parse_ea16(p,uf)
                    if len(ea_keys)!=third["ufs"][uf]["sections"]:
                        raise RuntimeError(f"EA16 {uf} difere da fase 3A")
                    status="EA16_SHA_VALIDADO"
                    break
            if ea_keys is None:
                missing_sources.append(uf)
        else:
            others=set()

        missing=sorted(ea_keys-bweb) if ea_keys is not None else []
        extra=sorted(bweb-ea_keys) if ea_keys is not None else []
        if ea_keys is not None:
            matched_uf+=1
            for k in missing:
                anomalies.append({"UF":uf,"municipio":k[1],"zona":k[2],
                                  "secao":k[3],"tipo":"EA16_SEM_BWEB"})
            for k in extra:
                anomalies.append({"UF":uf,"municipio":k[1],"zona":k[2],
                                  "secao":k[3],"tipo":"BWEB_SEM_EA16"})
        ea_st=ea_ts=delta_st=delta_ts=""
        time_label=""
        snapshot=run_dir/f"{uf.lower()}.json"
        if snapshot.is_file():
            values=count_snapshot(snapshot)
            found_uf_files+=1
            uf_st_total+=values["st"]
            uf_bweb_for_st+=len(bweb)
            ea_st=values["st"];ea_ts=values["ts"]
            delta_st=ea_st-len(bweb)
            delta_ts=ea_ts-len(bweb)
            time_label=f"{values['date']} {values['time']}".strip()
            snapshots_summary[uf]=values
        rows.append(dict(zip(HEAD,(uf,len(ea_keys) if ea_keys is not None else "",
            len(bweb),len(missing) if ea_keys is not None else "",
            len(extra) if ea_keys is not None else "",status,
            ea_st,ea_ts,delta_st,delta_ts,time_label))))
        print(f"[CHAVES {uf}] BU={len(bweb):,}, "
              f"EA16={'OK' if ea_keys is not None else status}, "
              f"dif={(len(missing)+len(extra)) if ea_keys is not None else '?'}; "
              f"EA20_st={ea_st if ea_st!='' else 'NAO_ARQUIVADO'}",flush=True)
    if bweb_sum!=EXPECTED or ea16_sum+manifest["ufs"]["ZZ"]["sections"]!=EXPECTED:
        raise RuntimeError("Somatorios EA16 + ZZ e BWEB nao conciliados")
    if any(x["UF"] in {"BA","MG"} and x["EA16_bruto_status"]!="EA16_SHA_VALIDADO" for x in rows):
        raise RuntimeError("BA/MG tinham EA16 original verificado na Fase O e nao foram encontrados")
    state=("PARCIAL_EA16_LOCAL" if missing_sources else
           "DIVERGENCIA_CHAVES_EA16_BWEB" if anomalies else
           "TODOS_EA16_CONFERIDOS_CHAVES_IGUAIS")
    result={"version":VERSION,
        "status":state,
        "scope":"Presidente turno 1 2026, chaves eleitorais; ZIP/SQLite nao lidos",
        "original_files_sha256":{"phase3_summary":sha256(source3),
                                 "phase2_summary":sha256(source2),
                                 "national_snapshots":sha256(frozen),
                                 "bweb_h_manifest":sha256(h)},
        "national":{
           "BR_st_final":SNAPSHOT_ST,
           "BR_validos_final":VALID_FINAL,
           "BWEB_28ufs_e_ZZ":bweb_sum,
           "EA16_principais_27ufs":ea16_sum,
           "BWEB_exterior_ZZ":manifest["ufs"]["ZZ"]["sections"],
           "BR_st_menos_BWEB":SNAPSHOT_ST-bweb_sum,
           "ufs_com_EA16_SHA_verificado":matched_uf,
           "ufs_EA16_nao_localizadas":missing_sources,
           "chaves_diferentes_nas_ufs_verificadas":len(anomalies),
           "snapshots_EA20_UF_localizados":found_uf_files,
           "EA20_st_UFs_arquivadas":uf_st_total if found_uf_files==len(UFs) else None,
           "EA20_st_UFs_vs_BWEB_mesmas_UFs":uf_st_total-uf_bweb_for_st if found_uf_files else None,
           "EA20_UF_coverage_note":"A soma parcial nao substitui o nacional; confrontar apenas se todas 28 UFs presentes",
           "BR_st_vs_soma_UF_st":SNAPSHOT_ST-uf_st_total if found_uf_files==len(UFs) else None,
        },
        "UF_detail":rows,
        "UF_snapshots_read":snapshots_summary,
        "observed_key_differences":anomalies,
        "limitations":[
            "ST e TS nao identificam quais secoes compõem diferenca de contador",
            "Uniao de hashes provenientes do mesmo ecossistema TSE nao constitui auditoria independente do BU impresso",
            "Arquivos EA20 estaduais arquivados podem ter sido gerados em momentos diferentes do snapshot nacional",
            "Zero diferencias de chave EA16 x BWEB nao explica por si o contador BR de 499248",
            "UFs sem EA16 bruto local sao relatadas como cobertura parcial, nunca inventadas",
            "Sem downloads ou acesso a ZIP de BWEB, SQLite ou dados de 2022"]}
    atomic_csv(folder/"phase5k_all_uf_section_keys_2026.csv",HEAD,rows)
    result["uf_csv_sha256"]=sha256(folder/"phase5k_all_uf_section_keys_2026.csv")
    keyfile=folder/"phase5k_ea16_bweb_key_mismatches_2026.csv"
    atomic_csv(keyfile,("UF","municipio","zona","secao","tipo"),anomalies)
    result["key_mismatch_csv_sha256"]=sha256(keyfile)
    out=folder/"phase5k_national_section_key_certificate_2026_summary.json"
    atomic_json(out,result)
    print(json.dumps({"status":result["status"],"national":result["national"],
         "path":str(out)},ensure_ascii=False,indent=2),flush=True)
    return result

if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root",help="raiz local do acervo em H")
    ap.add_argument("--repo",type=Path,default=Path(__file__).resolve().parent)
    args=ap.parse_args()
    run(root_path(args.root),args.repo)
