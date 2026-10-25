#!/usr/bin/env python3
"""Diagnostico de influencia por zona nas 13 inversoes Senado, somente 2026.

Consome SOMENTE checkpoints selados da etapa de robustez; nao le BU,
nao acessa SQLite e nao baixa arquivos. Estatisticas descritivas, pos-selecao.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import csv
import json
import math
import os
from pathlib import Path

from reconcile_stream import sha256
from senate_robustness_io_2026 import load_cases
from senate_robustness_stats_2026 import centered, pearson, sum_cov
from urnas import root_path

VERSION = "senate-zone-drivers-2026-v1"
DETAIL_FIELDS = ("UF","municipio","zona","turno","presidente","senador",
                 "secoes","r_zona","cov_xy_intra","cov_xx_intra",
                 "cov_yy_intra","r_sem_zona","delta_r_ao_excluir",
                 "abs_delta_r_ao_excluir")
SUMMARY_FIELDS = ("UF","presidente","senador","secoes","zonas_n2",
                  "r_ajustado","zonas_cov_pos","zonas_cov_neg",
                  "zonas_cov_zero","zonas_sinal_alinhado","zonas_sinal_oposto",
                  "pct_zonas_sinal_alinhado","maior_abs_delta_r",
                  "maior_zona_municipio","maior_zona_numero",
                  "top1_fracao_cov_abs_pct","top5_fracao_cov_abs_pct")


def atomic_csv(path, fields, records):
    tmp = Path(str(path)+".part")
    try:
        with tmp.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields, delimiter=";",
                                    lineterminator="\n")
            writer.writeheader()
            writer.writerows(records)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def atomic_json(path, value):
    tmp = Path(str(path)+".part")
    try:
        tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n",
                       encoding="utf-8")
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def find_folder(root):
    analysis = root/"analysis"
    national = json.loads(
        (analysis/"reconciliacao_bu_secao.summary.json").read_text("utf-8"))
    fp = national["fingerprint"]
    found = []
    for path in (analysis/"entre_cargos").glob(
            "*/correlacao_presidente_senado_v2/summary.json"):
        meta = json.loads(path.read_text("utf-8"))
        if meta.get("fingerprint") == fp:
            found.append(path.parent.parent)
    if len(found) != 1:
        raise RuntimeError("Era esperado um unico resultado Senado v2: "
                           + str(len(found)))
    return found[0], fp


def read_cache(folder, fp, cases, v2sha, compsha):
    derived = folder/"correlacao_presidente_senado_v2"/"robustez_inversoes_2026"
    cache = derived/"checkpoints"
    state = json.loads((cache/"state.json").read_text("utf-8"))
    expected = {"version":"senate-robustness-2026-v1","fingerprint":fp,
                "v2_sha256":v2sha,"comparison_sha256":compsha}
    if state.get("identity") != expected:
        raise RuntimeError("Checkpoint produzido por outra versao/fonte")
    original = json.loads((folder/"state.json").read_text("utf-8"))
    completed = original.get("completed",{})
    verified = state.get("completed",{})
    if (not completed or set(completed) != set(verified) or
            set(completed) != {str(i) for i in range(len(completed))}):
        raise RuntimeError("Particoes ausentes, incompletas ou inesperadas")
    groups = {}
    for i in range(len(completed)):
        name = str(i)
        candidate_sha = completed[name]["candidate_sha256"]
        checkpoint = verified[name]
        path = cache/f"bucket-{i:04d}.json"
        if (checkpoint.get("source") != candidate_sha or
            not path.is_file() or sha256(path) != checkpoint.get("sha256")):
            raise RuntimeError("SHA de checkpoint divergente: "+str(path))
        data = json.loads(path.read_text("utf-8"))
        if data.get("source") != candidate_sha:
            raise RuntimeError("Origem do checkpoint divergente: "+str(path))
        for entry in data["groups"]:
            if len(entry)!=12:
                raise RuntimeError("Momento de zona malformado")
            key = tuple(entry[:6])
            if (key[0],key[4],key[5]) not in cases:
                raise RuntimeError("Par nao selecionado no checkpoint")
            m = entry[6:]
            if (not isinstance(m[0],int) or m[0]<1 or
                    any(not isinstance(v,(int,float)) or
                        not math.isfinite(v) for v in m)):
                raise RuntimeError("Valores invalidos no checkpoint")
            sums = groups.setdefault(key,[0,0.,0.,0.,0.,0.])
            for j,value in enumerate(m):
                sums[j] += value
        if i<2 or (i+1)%32==0 or i+1==len(completed):
            print(f"[ZONAS {i+1}/{len(completed)}] SHA-256 conferido",flush=True)
    return groups, len(completed)


def analyze_pair(key, records, ref):
    records = sorted(records, key=lambda v:(v[0][1],v[0][2],v[0][3]))
    n = sum(v[1][0] for v in records)
    active = [(k,m,centered(m)) for k,m in records if m[0]>=2]
    if n!=ref["n"] or len(active)!=ref["z"]:
        raise RuntimeError("Seções ou zonas diferentes da v2: "+repr(key))
    base = sum_cov(item[2] for item in active)
    r = pearson(base)
    if r is None or abs(r-ref["adjusted"])>0.00002:
        raise RuntimeError("Correlacao nao reproduz v2: "+repr(key))
    details=[]
    sign = 1 if r>0 else -1
    positive=negative=zero=aligned=opposite=0
    for region,m,cov in active:
        cv=cov[0]
        if cv>1e-12:
            positive+=1
        elif cv<-1e-12:
            negative+=1
        else:
            zero+=1
        if cv*sign>1e-12:
            aligned+=1
        elif cv*sign<-1e-12:
            opposite+=1
        alt=pearson(tuple(base[j]-cov[j] for j in range(3)))
        if alt is None:
            raise RuntimeError("Deixar uma zona gerou variancia zero: "+repr(key))
        delta=alt-r
        details.append({
            "UF":region[0],"municipio":region[1],"zona":region[2],
            "turno":region[3],"presidente":region[4],"senador":region[5],
            "secoes":m[0],
            "r_zona": round(pearson(cov),6) if pearson(cov) is not None else "",
            "cov_xy_intra":round(cv,8),"cov_xx_intra":round(cov[1],8),
            "cov_yy_intra":round(cov[2],8),
            "r_sem_zona":round(alt,6),
            "delta_r_ao_excluir":round(delta,6),
            "abs_delta_r_ao_excluir":round(abs(delta),6)
        })
    ranked=sorted(details,key=lambda x:(-x["abs_delta_r_ao_excluir"],
                                         x["municipio"],x["zona"]))
    magnitudes=sorted((abs(c[0]) for _,_,c in active),reverse=True)
    denominator=math.fsum(magnitudes)
    top=ranked[0]
    stats={
        "UF":key[0],"presidente":key[1],"senador":key[2],
        "secoes":n,"zonas_n2":len(active),"r_ajustado":round(r,6),
        "zonas_cov_pos":positive,"zonas_cov_neg":negative,
        "zonas_cov_zero":zero,
        "zonas_sinal_alinhado":aligned,
        "zonas_sinal_oposto":opposite,
        "pct_zonas_sinal_alinhado":round(100*aligned/len(active),3),
        "maior_abs_delta_r":top["abs_delta_r_ao_excluir"],
        "maior_zona_municipio":top["municipio"],
        "maior_zona_numero":top["zona"],
        "top1_fracao_cov_abs_pct":round(100*magnitudes[0]/denominator,3)
                              if denominator else "",
        "top5_fracao_cov_abs_pct":round(100*math.fsum(magnitudes[:5])/denominator,3)
                              if denominator else ""
    }
    return stats, details, ranked[:5]


def run(root):
    folder, fp = find_folder(root)
    cases,v2sha,compsha=load_cases(folder,fp)
    groups,buckets=read_cache(folder,fp,cases,v2sha,compsha)
    by_pair=defaultdict(list)
    for k,m in groups.items():
        by_pair[(k[0],k[4],k[5])].append((k,m))
    summaries,detail,top=[],[],[]
    for key,ref in sorted(cases.items()):
        stats,rows,top5=analyze_pair(key,by_pair[key],ref)
        summaries.append(stats)
        detail.extend(rows)
        top.extend(top5)
        print(f"[PAR {key}] zonas={stats['zonas_n2']} "
              f"alinhadas={stats['zonas_sinal_alinhado']} "
              f"opostas={stats['zonas_sinal_oposto']} "
              f"max_delta_r={stats['maior_abs_delta_r']:.4f}",flush=True)
    dest=folder/"correlacao_presidente_senado_v2"/"robustez_inversoes_2026"/"drivers_zonais"
    dest.mkdir(parents=True,exist_ok=True)
    files={
        "resumo":(dest/"resumo_pares.csv",SUMMARY_FIELDS,summaries),
        "zonas":(dest/"zonas_por_par.csv",DETAIL_FIELDS,detail),
        "top5":(dest/"top5_zonas_influentes.csv",DETAIL_FIELDS,top)
    }
    metadata={}
    for label,(path,cols,data) in files.items():
        atomic_csv(path,cols,data)
        metadata[label]={"path":str(path),"sha256":sha256(path),"rows":len(data)}
    report={"version":VERSION,"status":"EXPLORATORIO_CONCLUIDO",
            "fingerprint":fp,"pares":len(summaries),
            "checkpoints_sha_verificados":buckets,
            "v2_sha256":v2sha,"comparacao_sha256":compsha,
            "files":metadata,"results":summaries,
            "limits":[
                "Contribuicao de covariancia por zona nao identifica individuo",
                "Par foi escolhido apos 616 comparacoes: sem controle confirmatorio",
                "As zonas nao sao unidades independentes de geografia vizinha",
                "Efeito local e influencia estatistica nao demonstram alteracao de votos",
                "Sem BU fisico independente nao existe diferenca D=Y-X medida"
            ]}
    atomic_json(dest/"summary.json",report)
    print("DRIVERS ZONAIS 2026 CONCLUIDOS")
    print(json.dumps({"pares":len(summaries),"zonas":len(detail),
                      "checkpoints_reutilizados":buckets,"files":metadata,
                      "results":summaries},ensure_ascii=False,indent=2),flush=True)
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",help="Diretorio local do acervo H:")
    args=parser.parse_args()
    run(root_path(args.root))
