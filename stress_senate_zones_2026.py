#!/usr/bin/env python3
"""Stress test zonal 2026: retira varias zonas dos 13 pares exploratorios.

Somente checkpoints verificados da opcao C. Sem BU, SQLite ou download.
Nao e teste de adulteracao ou significancia confirmatoria.
"""
from __future__ import annotations
import argparse
import csv
import json
import os
from collections import defaultdict
from pathlib import Path
from reconcile_stream import sha256
from senate_robustness_io_2026 import load_cases
from analyze_senate_zone_drivers_2026 import find_folder, read_cache
from senate_zone_stress_stats_2026 import stress
from urnas import root_path

VERSION="stress-zone-2026-v1"


def save_json(path,object_):
    tmp=Path(str(path)+".part")
    try:
        tmp.write_text(json.dumps(object_,ensure_ascii=False,indent=2)+"\n",
                       encoding="utf-8")
        os.replace(tmp,path)
    finally:
        if tmp.exists():
            tmp.unlink()


def write_csv(path,data):
    if not data:
        raise RuntimeError("Tabela vazia")
    tmp=Path(str(path)+".part")
    try:
        with tmp.open("w",encoding="utf-8",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=list(data[0]),delimiter=";",
                                  lineterminator="\n")
            writer.writeheader()
            writer.writerows(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if tmp.exists():
            tmp.unlink()


def run(root,replicacoes=400):
    folder,fp=find_folder(root)
    cases,v2sha,compsha=load_cases(folder,fp)
    moments,buckets=read_cache(folder,fp,cases,v2sha,compsha)
    by_pair=defaultdict(list)
    for key,m in moments.items():
        by_pair[(key[0],key[4],key[5])].append((key,m))
    rows,selected=[],[]
    for key,ref in sorted(cases.items()):
        one,critical=stress(key,by_pair[key],ref,replicacoes)
        rows.append(one)
        selected.extend(critical)
        print(f"[STRESS {key}] r={one['r_original']:+.4f} "
              f"sem_top5_cov={one['r_sem_top5_cov_abs']:+.4f} "
              f"sem_top5_impacto={one['r_sem_top5_impacto_individual']:+.4f} "
              f"aleatoria_mesmo_sinal={one['rand5_pct_mesmo_sinal']}%",
              flush=True)
    target=folder/"correlacao_presidente_senado_v2"/"robustez_inversoes_2026"/"stress_zonas"
    target.mkdir(parents=True,exist_ok=True)
    resultpath=target/"stress_pares.csv"
    chosenpath=target/"top5_por_criterio.csv"
    write_csv(resultpath,rows)
    write_csv(chosenpath,selected)
    report={
        "version":VERSION,"status":"EXPLORATORIO_CONCLUIDO",
        "fingerprint":fp,"pares":len(rows),
        "checkpoints_verificados":buckets,
        "replicacoes_aleatorias":replicacoes,
        "hash_v2":v2sha,"hash_comparacao":compsha,
        "files":{
            "pares":{"path":str(resultpath),"sha256":sha256(resultpath),
                     "rows":len(rows)},
            "top5":{"path":str(chosenpath),"sha256":sha256(chosenpath),
                    "rows":len(selected)}},
        "results":rows,
        "limitations":[
            "13 pares escolhidos depois de observar 616: estatistica pos-selecao",
            "Amostras aleatorias de zonas nao sao p-valores nem corrigem autocorrelacao espacial",
            "Remover zonas de maior impacto e teste adversarial, nao estimativa de fraude",
            "Nao existe fonte de BU independente para aferir D=Y-X",
            "Usa somente 2026 e apenas momentos zonais ja calculados"]}
    save_json(target/"summary.json",report)
    print("STRESS CONJUNTO DE ZONAS 2026 CONCLUIDO",flush=True)
    print(json.dumps({"pares":len(rows),"checkpoints":buckets,
                      "files":report["files"],"results":rows},
                     ensure_ascii=False,indent=2),flush=True)
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",help="Acervo existente em H:")
    parser.add_argument("--replicacoes",type=int,default=400)
    args=parser.parse_args()
    run(root_path(args.root),args.replicacoes)
