#!/usr/bin/env python3
"""Fase 5J (opcao O): reconciliar os 42 contadores de secoes de 2026.

Usa somente CSV/JSON ja versionados e os received-BA/MG.csv da opcao H,
cujos SHA-256 constam no manifesto local. NAO baixa, NAO abre ZIP/SQLite.
Compara 3 niveis de EA20 (UF/municipio/zona), EA16 quando disponivel,
secoes de EA18 ja materializadas e BWEB por CHAVE eleitoral.

Crucial: igualdade de 42 em dois saldos nao prova serem as mesmas
42 secoes. Um contador agregado nao identifica as chaves ausentes.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
import json
import os
from pathlib import Path

from extract_bweb_received_2026 import VERSION as H_VERSION
from reconcile_stream import sha256
from urnas import root_path

VERSION="phase5j-42-section-counter-reconciliation-2026-v1"
LOCAL="analysis/periodicidade_bweb_2026"
OFFICIAL_PATH="data/forensics/analysis/phase5a_presidential_national_2026.csv"
STAGE2="data/forensics/analysis/phase2_sections_summary.json"
MUNICIPAL="data/forensics/analysis/section_config_reconciliation.csv"
ZONAL="data/forensics/analysis/zone_reconciliation.csv"
CANDIDATES="data/forensics/analysis/section_candidates.csv"
STAGE3="data/forensics/analysis/phase3_arrivals_summary.json"
UFS=("BA","MG")
ZONE_FIELDS=("UF","municipio","municipio_nome","zona",
             "ea20_zone_ts","ea20_zone_st","gap_zone_ts_minus_st",
             "ea16_principais_config","chaves_ea18_candidatas",
             "ea18_totalizadas","chaves_ea18_no_BWEB",
             "chaves_ea18_ausentes_BWEB",
             "BWEB_chaves_na_zona","EA16_principais_no_BWEB",
             "EA16_principais_ausentes_BWEB",
             "BWEB_chaves_ausentes_EA16",
             "identificacao_das_secoes_em_falta")


def key(uf,mu,zo,se):
    return (uf.upper(),int(mu),int(zo),int(se))


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


def atomic_csv(path,fields,records):
    path.parent.mkdir(parents=True,exist_ok=True)
    part=Path(str(path)+".part")
    try:
        with part.open("w",encoding="utf-8",newline="") as f:
            w=csv.DictWriter(f,fieldnames=fields,delimiter=";",
                             lineterminator="\n")
            w.writeheader();w.writerows(records)
            f.flush();os.fsync(f.fileno())
        os.replace(part,path)
    finally:
        if part.exists():part.unlink()


def csv_rows(path):
    with path.open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))


def resolve_inputs(repo):
    paths={n:repo/x for n,x in (("snapshot",OFFICIAL_PATH),
        ("phase2",STAGE2),("municipal",MUNICIPAL),
        ("zonal",ZONAL),("candidates",CANDIDATES),
        ("phase3",STAGE3))}
    missing=[n for n,path in paths.items() if not path.is_file()]
    if missing:
        raise RuntimeError("Relatorios ja versionados ausentes: "+", ".join(missing))
    return paths


def read_h(archive_root):
    folder=archive_root/LOCAL
    source=folder/"summary.json"
    if not source.is_file():
        raise RuntimeError("Execute H: cache BWEB por secao inexistente")
    manifest=json.loads(source.read_text(encoding="utf-8"))
    if manifest.get("version")!=H_VERSION:
        raise RuntimeError("Manifesto H com versao inesperada")
    if manifest.get("sections")!=499206 or len(manifest.get("ufs",{}))!=28:
        raise RuntimeError("Quantidade/cobertura do manifesto H diverge de 2026")
    all_section_sets={}
    summed=0
    for uf in UFS:
        shard=folder/f"received-{uf}.csv"
        if (not shard.is_file()
            or sha256(shard)!=manifest["ufs"][uf]["shard_sha256"]):
            raise RuntimeError(f"BWEB {uf}: SHA do cache H divergente")
        seen=set()
        rows=0
        with shard.open(encoding="utf-8-sig",newline="") as f:
            for row in csv.DictReader(f,delimiter=";"):
                if row["UF"]!=uf or str(int(row["turno"]))!="1":
                    raise RuntimeError("UF/turno incoerente no BWEB")
                identity=key(uf,row["municipio"],row["zona"],row["secao"])
                if identity in seen:
                    raise RuntimeError("Chave eleitoral BU duplicada "+repr(identity))
                seen.add(identity)
                rows+=1
        if rows!=manifest["ufs"][uf]["sections"]:
            raise RuntimeError(f"BWEB {uf}: secoes != manifesto")
        all_section_sets[uf]=seen
        summed+=rows
        print(f"[BU {uf}] {rows:,} chaves distintas, SHA verificado",flush=True)
    return manifest,all_section_sets,sha256(source)


def ea16_candidate_locations(repo,root,uf):
    filename=uf.lower()+"-p003220-cs.json"
    return [repo/"data"/"forensics"/"phase3"/"raw"/"ea16"/filename,
            repo/"data"/"forensics"/"section-config"/"ea16"/filename,
            root/"phase3"/"raw"/"ea16"/filename,
            root/"section-config"/"ea16"/filename]


def read_ea16(repo,root,reference):
    """Opcional; se presente, SHA da fase 3 e obrigatorio."""
    known={rec["uf"]:rec["sha256"] for rec in reference["sources"]
           if rec.get("sha256") and rec.get("uf") in UFS}
    if set(known)!=set(UFS):
        raise RuntimeError("Sem hashes EA16 BA/MG na fase 3 anterior")
    result={}
    details={}
    for uf in UFS:
        candidate=next((x for x in ea16_candidate_locations(repo,root,uf)
                        if x.is_file()),None)
        if candidate is None:
            details[uf]={"status":"EA16_BRUTO_LOCAL_NAO_ENCONTRADO",
                         "expected_sha256":known[uf]}
            continue
        if sha256(candidate)!=known[uf]:
            raise RuntimeError("SHA EA16 divergente no arquivo "+str(candidate))
        obj=json.loads(candidate.read_text(encoding="utf-8-sig"))
        abr=next((a for a in obj.get("abr",[])
                  if str(a.get("cd","")).lower()==uf.lower()),None)
        if abr is None and len(obj.get("abr",[]))==1:
            abr=obj["abr"][0]
        if abr is None:
            raise RuntimeError("EA16 sem abrangencia "+uf)
        grouped=defaultdict(set)
        principal=set()
        extras=set()
        for mu in abr.get("mu",[]):
            for zo in mu.get("zon",[]):
                for sec in zo.get("sec",[]):
                    ident=key(uf,mu["cd"],zo["cd"],sec["ns"])
                    bucket=extras if sec.get("nsp") else principal
                    if ident in principal or ident in extras:
                        raise RuntimeError("Chave duplicada na configuracao EA16")
                    bucket.add(ident)
                    if not sec.get("nsp"):
                        grouped[(uf,int(mu["cd"]),int(zo["cd"]))].add(ident)
        result[uf]={"principal":principal,"extra":extras,"grouped":grouped}
        details[uf]={"status":"EA16_SHA_VALIDADO",
                     "sha256":known[uf],
                     "principal_count":len(principal),
                     "aggregated_count":len(extras)}
        print(f"[EA16 {uf}] principais={len(principal):,}, "
              f"agregadas={len(extras):,}, SHA verificado",flush=True)
    return result,details


def build(repo,root):
    paths=resolve_inputs(repo)
    source=json.loads(paths["phase2"].read_text(encoding="utf-8"))
    phase3=json.loads(paths["phase3"].read_text(encoding="utf-8"))
    snapshot=csv_rows(paths["snapshot"])
    if not snapshot:
        raise RuntimeError("Snapshot final nao encontrado")
    final=snapshot[-1]
    if int(final["vv"])!=119300788:
        raise RuntimeError("Votos validos finais nao coincidem com referencia")
    final_st=int(final["st"])
    manifest,bweb,manifest_sha=read_h(root)
    ea16,ea16_details=read_ea16(repo,root,phase3)
    mun_rows=csv_rows(paths["municipal"])
    zon_rows=csv_rows(paths["zonal"])
    candidate_rows=csv_rows(paths["candidates"])
    municipal={(r["uf"],int(r["municipality_code"])):r for r in mun_rows
               if r["uf"] in UFS}
    zonal={(r["uf"],int(r["municipality_code"]),int(r["zone"])):r for r in zon_rows}
    ea18=defaultdict(list)
    for r in candidate_rows:
        if r["uf"] in UFS:
            k=key(r["uf"],r["municipality_code"],r["zone"],r["section"])
            ea18[k[:3]].append((k,r))
    if len(zonal)!=len(zon_rows):
        raise RuntimeError("Zonas da fase 2 duplicadas")
    if any(x["uf"] not in UFS for x in zon_rows):
        raise RuntimeError("UF inesperada na fase 2")

    affected={}
    zon_report=[]
    identities=[]
    muni_report=[]
    for uf in UFS:
        summary=source["ufs"][uf]
        mun_expected={int(c) for c in summary["anomalous_municipalities"]}
        observed_muni={
            m for (u,m),r in municipal.items()
            if u==uf and int(r["ea20_ts"])!=int(r["ea20_st"])
        }
        if mun_expected!=observed_muni:
            raise RuntimeError("Lista de municipios divergente da fase2: "+uf)
        for m in sorted(mun_expected):
            mi=municipal[(uf,m)]
            zones=[(identity,r) for identity,r in zonal.items()
                   if identity[:2]==(uf,m)]
            if not zones:
                raise RuntimeError(f"Municipio sem zona EA20: {uf}/{m}")
            if (sum(int(x["ea20_zone_ts"]) for _,x in zones)
                !=int(mi["ea20_ts"])):
                raise RuntimeError("Soma TS zonas diverge municipio "+uf+"/"+str(m))
            mun_zone_st=sum(int(x["ea20_zone_st"]) for _,x in zones)
            count_bweb=sum(k[1]==m for k in bweb[uf])
            ts=int(mi["ea20_ts"]);st=int(mi["ea20_st"])
            principal=int(mi["ea16_principal_sections"])
            if count_bweb!=principal:
                # Diferença de identidade deve ser investigada explicitamente,
                # não usar valor de contadores para imputar perda de voto.
                print(f"[ALERTA {uf}/{m}] BWEB={count_bweb} EA16 reportado={principal}",flush=True)
            exact_ea16=ea16.get(uf,{}).get("principal")
            config_muni=sum(k[1]==m for k in exact_ea16) if exact_ea16 is not None else None
            if config_muni is not None and config_muni!=principal:
                raise RuntimeError("EA16 completo diverge do resumo fase2")
            muni_report.append({
                "UF":uf,"municipio":str(m),"nome":mi["municipality_name"],
                "EA20_municipio_ts":ts,"EA20_municipio_st":st,
                "gap_municipio":ts-st,"EA20_zonas_st_soma":mun_zone_st,
                "gap_municipio_st_vs_zonas_st":mun_zone_st-st,
                "EA16_principais_referencia":principal,
                "EA16_principais_verificados":config_muni if config_muni is not None else "",
                "BWEB_secoes_com_BU_presidencial":count_bweb,
                "gap_BWEB_vs_EA16":count_bweb-principal})
            affected[(uf,m)]=st
            for (u,mu,z),zr in zones:
                keys_bweb={k for k in bweb[uf] if k[1:3]==(m,z)}
                exact=ea16.get(uf,{}).get("grouped",{}).get((uf,m,z))
                if exact is not None:
                    missing=sorted(exact-keys_bweb)
                    unexpected=sorted(keys_bweb-exact)
                    for identity in missing:
                        identities.append({"UF":uf,"municipio":m,"zona":z,
                                          "secao":identity[3],"situacao":"EA16_SEM_BU_BWEB"})
                    for identity in unexpected:
                        identities.append({"UF":uf,"municipio":m,"zona":z,
                                          "secao":identity[3],"situacao":"BU_BWEB_SEM_EA16"})
                else:
                    missing=unexpected=[]
                candidate=ea18.get((uf,m,z),[])
                candidate_present=[k for k,r in candidate if k in keys_bweb]
                ea18_total=sum(str(r["ea18_status"]).strip().casefold()=="totalizada"
                               for k,r in candidate)
                for k,r in candidate:
                    if k not in keys_bweb:
                        identities.append({"UF":uf,"municipio":m,"zona":z,
                                           "secao":k[3],"situacao":"EA18_CANDIDATA_SEM_BWEB"})
                zst=int(zr["ea20_zone_st"]);zts=int(zr["ea20_zone_ts"])
                zon_report.append(dict(zip(ZONE_FIELDS,(
                    uf,m,mi["municipality_name"],z,zts,zst,zts-zst,
                    int(zr["ea16_principal_sections"]),len(candidate),
                    ea18_total,len(candidate_present),
                    len(candidate)-len(candidate_present),
                    len(keys_bweb),
                    len(exact & keys_bweb) if exact is not None else "",
                    len(missing) if exact is not None else "",
                    len(unexpected) if exact is not None else "",
                    "NAO_IDENTIFICAVEL_POR_CONTADOR_ST"
                ))))
        print(f"[CONTADORES {uf}] municipios={len(mun_expected)}, "
              f"gap municipal={sum(x['gap_municipio'] for x in muni_report if x['UF']==uf)}",
              flush=True)
    municipal_gap=sum(x["gap_municipio"] for x in muni_report)
    zone_gap=sum(x["gap_zone_ts_minus_st"] for x in zon_report)
    inner_gap=sum(x["gap_municipio_st_vs_zonas_st"] for x in muni_report)
    if municipal_gap!=42 or zone_gap+inner_gap!=42:
        raise RuntimeError("As 42 secoes nao fecham entre contadores municipais/zonais")
    if int(phase3["principal_sections"])+manifest["ufs"]["ZZ"]["sections"]!=manifest["sections"]:
        raise RuntimeError("Contagem principal EA16+ZZ nao coincide com BWEB total")
    if (sum(int(x["sections"]) for x in manifest["ufs"].values())
        !=manifest["sections"]):
        raise RuntimeError("Soma de BU do manifesto nao coincide com total")
    if final_st-manifest["sections"]!=42:
        raise RuntimeError("Snapshot final e BWEB nao exibem diferenca de 42")
    nationwide={"snapshot_nacional_st":final_st,
        "bweb_presidential_distinct_sections":manifest["sections"],
        "national_snapshot_minus_bweb":final_st-manifest["sections"],
        "ea16_principal_sections_27ufs":int(phase3["principal_sections"]),
        "bweb_exterior_ZZ":int(manifest["ufs"]["ZZ"]["sections"]),
        "ea16_principals_plus_ZZ":int(phase3["principal_sections"])+int(manifest["ufs"]["ZZ"]["sections"]),
        "ba_mg_ea20_municipal_ts_minus_st":municipal_gap,
        "ba_mg_ea20_zonal_ts_minus_st":zone_gap,
        "ea20_zonal_st_minus_municipal_st":inner_gap,
        "candidate_bweb_key_difference_count":len(identities),
        "count_42_is_the_same_identified_sections":False}
    input_hashes={n:sha256(x) for n,x in paths.items()}
    output={"version":VERSION,"status":"CONTADORES_RECONCILIADOS_IDENTIDADE_NAO_DEDUZIDA",
        "scope":"Presidente turno 1 de 2026; BA/MG e total BR",
        "national":nationwide,
        "municipality_details":muni_report,
        "zone_details":zon_report,
        "bweb_cache_sha256":manifest_sha,
        "ea16_sha_and_availability":ea16_details,
        "inputs_sha256":input_hashes,
        "candidate_key_mismatches":identities,
        "caveats":[
            "ST e TS sao contadores agregados, nao listagens de identificadores das secoes faltantes",
            "A coincidencia 42 no nivel BR-BWEB e 42 no nivel UF-municipio nao demonstra mesma origem",
            "Quando os EA16 brutos estao ausentes, so o subconjunto EA18 pre-derivado pode ter chaves verificadas",
            "EA18 Totalizada e campo de status no momento do arquivo preservado, nao prova de transmissao externa",
            "Votos validos do BWEB corrigidos foram conciliados em outra etapa, nao representam perda de 42 urnas",
            "A divergencia de contadores nao representa por si so adulteracao, fraude ou inexistencia de BU"]}
    return output


def run(root,repo=Path(".")):
    repo=repo.resolve()
    outcome=build(repo,root)
    folder=root/LOCAL
    tables={
        "phase5j_municipal_42_2026.csv":outcome["municipality_details"],
        "phase5j_zonal_42_2026.csv":outcome["zone_details"],
        "phase5j_candidate_key_differences_2026.csv":outcome["candidate_key_mismatches"]
    }
    for filename,rows in tables.items():
        if filename.startswith("phase5j_municipal"):
            fields=list(rows[0]) if rows else []
        elif filename.startswith("phase5j_zonal"):
            fields=ZONE_FIELDS
        else:
            fields=("UF","municipio","zona","secao","situacao")
        atomic_csv(folder/filename,fields,rows)
        outcome[filename]={"file":str(folder/filename),"sha256":sha256(folder/filename)}
    path=folder/"phase5j_42_section_counter_reconciliation_2026_summary.json"
    atomic_json(path,outcome)
    print(json.dumps({
        "status":outcome["status"],
        "national":outcome["national"],
        "municipios_com_discrepancia":len(outcome["municipality_details"]),
        "zonas_da_fase2":len(outcome["zone_details"]),
        "chaves_com_diferenca_observavel":len(outcome["candidate_key_mismatches"]),
        "EA16":outcome["ea16_sha_and_availability"],
        "resultado":str(path)},ensure_ascii=False,indent=2),flush=True)
    return outcome


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",help="raiz local do acervo BWEB H:")
    parser.add_argument("--repo",type=Path,default=Path(__file__).resolve().parent)
    args=parser.parse_args()
    run(root_path(args.root),args.repo)
