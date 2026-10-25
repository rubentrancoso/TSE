#!/usr/bin/env python3
"""Teste de robustez territorial de inversoes Presidente x Senado, 2026.

Reutiliza exclusivamente particoes BU SHA-256 conferidas; nunca abre SQLite,
baixa arquivos ou modifica dados originais. Estatistica DESCRITIVA.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
from collections import defaultdict

from cross_office_candidate_correlations import source
from reconcile_stream import sha256
from senate_robustness_io_2026 import load_cases, aggregate_shard
from senate_robustness_stats_2026 import analyze
from urnas import root_path

VERSION = "senate-robustness-2026-v1"
COLUMNS = ("UF","presidente","senador","secoes","zonas_n2",
           "r_bruto","r_ajustado","r_zonas_n5","r_zonas_n10",
           "pct_loo_mesmo_sinal","pct_boot_mesmo_sinal",
           "pct_boot_mesmo_sinal_e_modulo_010",
           "bootstrap_p025","bootstrap_p975","bootstrap_validos")


def save(path, data):
    part = Path(str(path)+".part")
    try:
        part.write_text(json.dumps(data, ensure_ascii=False, indent=2,
                                   sort_keys=True)+"\n",encoding="utf-8")
        os.replace(part,path)
    finally:
        if part.exists():
            part.unlink()


def run(root, replicacoes=400):
    folder, original, paths = source(root)  # verifica SHA-256 dos CSVs
    fp = original["source_fingerprint"]
    cases, hash_v2, hash_comparison = load_cases(folder, fp)
    outdir = folder/"correlacao_presidente_senado_v2"/"robustez_inversoes_2026"
    cache = outdir/"checkpoints"
    cache.mkdir(parents=True, exist_ok=True)
    identity = {"version":VERSION,"fingerprint":fp,
                "v2_sha256":hash_v2,"comparison_sha256":hash_comparison}
    statefile = cache/"state.json"
    if statefile.exists():
        state = json.loads(statefile.read_text("utf-8"))
        if state.get("identity") != identity:
            raise RuntimeError("Checkpoint de origem/metodo diferente")
    else:
        state = {"identity":identity,"completed":{}}
        save(statefile,state)
    source_state=json.loads((folder/"state.json").read_text("utf-8"))
    merged = {}
    reused = 0
    for i,path in enumerate(paths):
        source_hash=source_state["completed"][str(i)]["candidate_sha256"]
        partial=cache/f"bucket-{i:04d}.json"
        previous=state["completed"].get(str(i))
        if previous:
            if (not partial.is_file() or previous["source"]!=source_hash or
                sha256(partial)!=previous["sha256"]):
                raise RuntimeError("Checkpoint alterado ou ausente "+str(partial))
            payload=json.loads(partial.read_text("utf-8"))
            reused+=1
        else:
            stats=aggregate_shard(path,cases)
            payload={"source":source_hash,
                     "groups":[list(k)+v for k,v in sorted(stats.items())]}
            save(partial,payload)
            state["completed"][str(i)]={"source":source_hash,
                                         "sha256":sha256(partial)}
            save(statefile,state)
        if payload.get("source")!=source_hash:
            raise RuntimeError("Fingerprint de checkpoint incorreto")
        for row in payload["groups"]:
            zone=tuple(row[:6])
            target=merged.setdefault(zone,[0,0.,0.,0.,0.,0.])
            if len(row)!=12:
                raise RuntimeError("Momento salvo malformado")
            for j,value in enumerate(row[6:]):
                target[j]+=value
        if i<2 or (i+1)%20==0 or i+1==len(paths):
            print(f"[ROBUSTEZ {i+1}/{len(paths)}] checkpoints reutilizados={reused}",flush=True)
    by_pair=defaultdict(list)
    for key,moment in sorted(merged.items()):
        by_pair[(key[0],key[4],key[5])].append(moment)
    results=[]
    for key,ref in sorted(cases.items()):
        seed=int.from_bytes(hashlib.sha256(
            (VERSION+"|"+"|".join(key)).encode("utf-8")).digest()[:8],"big")
        result=analyze(by_pair[key],ref["n"],ref["z"],ref["raw"],
                       ref["adjusted"],seed,replicacoes)
        record={"UF":key[0],"presidente":key[1],"senador":key[2],**result}
        results.append(record)
        print(f"[PAR {key}] r={record['r_ajustado']:+.4f}; "
              f"LOO={record['pct_loo_mesmo_sinal']}%; "
              f"bootstrap={record['pct_boot_mesmo_sinal']}%",flush=True)
    csv_path=outdir/"pares_robustez.csv"
    temp=Path(str(csv_path)+".part")
    try:
        with temp.open("w",encoding="utf-8",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=COLUMNS,delimiter=";",
                                  lineterminator="\n")
            writer.writeheader()
            writer.writerows(results)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp,csv_path)
    finally:
        if temp.exists():
            temp.unlink()
    summary={
        "version":VERSION,"status":"EXPLORATORIO_CONCLUIDO",
        "fingerprint":fp,"pares":len(results),
        "replicacoes_bootstrap":replicacoes,
        "particoes":len(paths),"checkpoints_reutilizados":reused,
        "v2_sha256":hash_v2,"comparacao_sha256":hash_comparison,
        "csv":str(csv_path),"csv_sha256":sha256(csv_path),
        "results":results,
        "limites":[
            "Os pares foram selecionados depois da triagem de 616 comparacoes: vies de selecao",
            "Bootstrap zonal nao controla autocorrelacao espacial nem multipla comparacao",
            "Intervalos sao exploratorios: nao interpretar como probabilidades de fraude",
            "Sem BU original independente nao e possivel medir D=Y-X",
            "Somente dados de 2026; nenhuma inferencia de voto individual"]
    }
    save(outdir/"summary.json",summary)
    print("ROBUSTEZ SENADO 2026 CONCLUIDA",flush=True)
    print(json.dumps({"pares":len(results),"reutilizados":reused,
                      "csv":str(csv_path),"sha256":summary["csv_sha256"],
                      "resultados":results},ensure_ascii=False,indent=2),flush=True)
    return summary


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",help="Diretorio do acervo local H:")
    parser.add_argument("--replicacoes",type=int,default=400)
    args=parser.parse_args()
    run(root_path(args.root),args.replicacoes)
