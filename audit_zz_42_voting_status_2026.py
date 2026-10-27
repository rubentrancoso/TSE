#!/usr/bin/env python3
"""Fase 5M: natureza eleitoral das 42 secoes ZZ sem correspondente BWEB (2026).

Somente JSON EA20 locais SHA-verificados pelo manifesto original e
resultado SHA da Q, nao ZIP, nao rede, nao SQLite, nao dados 2022.

Os campos sao observacoes da totalizacao: e.te (aptos), e.c
(comparecimento), e.a (abstencao), v.vv (validos), v.vb (brancos),
v.tvn (nulos). A presenca de ST nao prova que o BU foi produzido.
NAO presumir zero para campos inexistentes nem substituir o BU fisico.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
import json
import os
from pathlib import Path

from audit_zz_42_sections_2026 import (
    CACHE, SOURCE_RUN, as_int, manifest_index, verify,
)
from reconcile_stream import sha256
from urnas import root_path

VERSION="phase5m-zz42-election-metrics-2026-v1"
NEEDED=("e.te","e.c","e.a","e.est","v.vv","v.vb","v.tvn")
HEAD=("municipio","localidade","secoes_EA20","secoes_BWEB",
      "secoes_sem_BU","e.te","e.est","e.c","e.a",
      "v.vv","v.vb","v.tvn","classificacao","data","hora","sha256_ea20")
SOURCE_Q="phase5l_zz_42_sections_2026_summary.json"

def atom_json(path,obj):
    tmp=Path(str(path)+".part")
    try:
        with tmp.open("w",encoding="utf-8") as f:
            json.dump(obj,f,ensure_ascii=False,indent=2)
            f.write("\n");f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if tmp.exists():tmp.unlink()

def atom_csv(path,rows):
    tmp=Path(str(path)+".part")
    try:
        with tmp.open("w",encoding="utf-8",newline="") as f:
            w=csv.DictWriter(f,fieldnames=HEAD,delimiter=";",
                             lineterminator="\n")
            w.writeheader();w.writerows(rows)
            f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if tmp.exists():tmp.unlink()

def field(raw,part,name):
    values=raw.get(part)
    if not isinstance(values,dict):
        return None
    value=values.get(name)
    if value in (None,""):return None
    return as_int(value)

def classify(measures):
    c=measures["e.c"]
    values=[measures[x] for x in ("v.vv","v.vb","v.tvn")]
    if any(v is not None and v>0 for v in values) or (c is not None and c>0):
        return "EA20_REGISTRA_COMPARECIMENTO_OU_VOTOS"
    if c==0 and all(v is not None and v==0 for v in values):
        return "EA20_COMPARECIMENTO_E_VOTOS_ZERO"
    if c==0:
        return "EA20_COMPARECIMENTO_ZERO_VOTOS_INCOMPLETOS"
    return "CAMPOS_ESSENCIAIS_AUSENTES"

def audit(root,repo=Path(".")):
    repo=repo.resolve()
    q_file=root/CACHE/SOURCE_Q
    if not q_file.is_file():raise RuntimeError("Execute Q primeiro")
    q=json.loads(q_file.read_text(encoding="utf-8"))
    info=q["national"]
    if (q.get("status")!="DIFERENCA_LOCALIZADA_NOS_CONTADORES_MUNICIPAIS_ZZ"
        or info.get("ZZ_st_UF")!=1351 or info.get("ZZ_BWEB_sections")!=1309
        or info.get("EA20_municipal_st_sum")!=1351
        or info.get("municipal_st_sum_minus_BWEB")!=42
        or info.get("all_municipal_counters_compared") is not True
        or info.get("EA20_municipal_archived_SHA_validated")!=info.get("EA20_municipal_files")):
        raise RuntimeError("Resultado Q nao conciliou exterior integralmente")
    phase2=repo/"data/forensics/analysis/phase2_sections_summary.json"
    if sha256(phase2)!=q["input_provenance"]["phase2_sha256"]:
        raise RuntimeError("SHA do resumo fase2 diverge de Q")
    doc=json.loads(phase2.read_text(encoding="utf-8"))
    run=repo/SOURCE_RUN/doc["latest_snapshot"]
    mani=run/"manifest.jsonl"
    if sha256(mani)!=q["input_provenance"]["original_manifest_sha256"]:
        raise RuntimeError("Manifesto original foi alterado desde Q")
    hashes=manifest_index(mani)
    entries=q["municipal_detail"]
    selected=[x for x in entries if x["diferenca_st_menos_BWEB"]!="" and
              int(x["diferenca_st_menos_BWEB"])>0]
    if (len(selected)!=41 or
        sum(int(x["diferenca_st_menos_BWEB"]) for x in selected)!=42 or
        any(int(x["diferenca_st_menos_BWEB"])<0 for x in entries
            if x["diferenca_st_menos_BWEB"]!="")):
        raise RuntimeError("Dados da fase Q diferentes do certificado de 41 locais/42 secoes")
    rows=[]
    tally=Counter()
    for ref in selected:
        mu=as_int(ref["municipio"])
        path=run/"live"/"municipio"/"zz"/f"{mu}.json"
        if ("mu",mu) not in hashes:
            raise RuntimeError("JSON EA20 sem SHA anterior "+str(mu))
        verify(path,hashes[("mu",mu)])
        payload=json.loads(path.read_text(encoding="utf-8-sig"))
        measures={f:field(payload,*f.split(".")) for f in NEEDED}
        st=field(payload,"s","st");ts=field(payload,"s","ts")
        if st!=as_int(ref["EA20_municipal_st"]) or ts!=as_int(ref["EA20_municipal_ts"]):
            raise RuntimeError("Contadores municipais ZZ mudaram desde Q "+str(mu))
        classification=classify(measures)
        tally[classification]+=1
        tally["sections_"+classification]+=int(ref["diferenca_st_menos_BWEB"])
        for k,v in measures.items():
            if v is None:tally[k+"_missing"]+=1
        record={"municipio":str(mu).zfill(5),
                "localidade":ref["nome_configuracao"],
                "secoes_EA20":st,"secoes_BWEB":ref["BWEB_secoes"],
                "secoes_sem_BU":ref["diferenca_st_menos_BWEB"],
                **{k:(v if v is not None else "") for k,v in measures.items()},
                "classificacao":classification,
                "data":ref["EA20_municipal_dia"],
                "hora":ref["EA20_municipal_hora"],
                "sha256_ea20":hashes[("mu",mu)]}
        rows.append(record)
        print(f"[ZZ {str(mu).zfill(5)}] {ref['nome_configuracao']}: "
              f"gap=+{int(record['secoes_sem_BU'])}, "
              f"aptos={record['e.te']}, comparecimento={record['e.c']}, "
              f"validos={record['v.vv']}, brancos={record['v.vb']}, "
              f"nulos={record['v.tvn']}; {classification}",flush=True)
    csv_path=root/CACHE/"phase5m_zz_42_voting_status_by_locality_2026.csv"
    atom_csv(csv_path,rows)
    response={
        "version":VERSION,"status":"CAMPOS_EA20_ZZ_AUDITADOS",
        "scope":"Presidente 1 turno 2026, 41 localidades/42 secoes, ZZ",
        "localities":len(rows),"sections_without_corresponding_BWEB":42,
        "classification_counts":dict(tally),
        "input_Q_sha256":sha256(q_file),
        "input_manifest_sha256":sha256(mani),
        "rows_csv":str(csv_path),"rows_csv_sha256":sha256(csv_path),
        "key_findings":[
          "Contadores EA20 de ZZ possuem 42 secoes sem linha BWEB correspondente em 41 localidades",
          "Comparecimento ou voto positivo no EA20 sem BWEB nao pode ser explicado como secao sem votos",
          "Comparecimento e votos ZERO no EA20 sao compativeis com ausencia de urna votada, mas nao sao prova suficiente",
          "ST e TS e campos de votos podem ter semantics/proveniencia distintas: testar validacao independente",
          "Nao ha EA16 do exterior na fase 3A para listar chaves exatas",
          "Nenhuma coleta, ZIP, SQLite ou dados 2022 sao acessados"
        ],
        "limitations":[
          "Apenas campos existentes nos snapshots EA20, nao BU fisicos individuais",
          "Indicadores ausentes nao sao convertidos em zero",
          "O EA20 e o BWEB sao provenientes do mesmo ecossistema TSE",
          "Presenca de eleitores aptos nao confirma que a votacao ocorreu",
          "Estados de sessao como totalizada devem ser interpretados conforme especificacao EA20"
        ]}
    output=root/CACHE/"phase5m_zz_42_voting_status_2026_summary.json"
    atom_json(output,response)
    print(json.dumps({"status":response["status"],
                      "localidades":len(rows),
                      "secoes":42,
                      "classes":dict(tally),
                      "csv":str(csv_path),"summary":str(output)},
                      ensure_ascii=False,indent=2),flush=True)
    return response

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root")
    parser.add_argument("--repo",type=Path,default=Path(__file__).resolve().parent)
    args=parser.parse_args()
    audit(root_path(args.root),args.repo)
