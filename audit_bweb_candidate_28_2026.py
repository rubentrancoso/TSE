#!/usr/bin/env python3
"""Fase 5G - causa exata dos +5246 votos: numero 28 no BWEB 2026.

Le SOMENTE ZIPs BWEB de 2026 JA BAIXADOS em H:, verifica os SHA-256
dos manifestos, cruza somas por UF e chave de secao com relatorio K.
Sem downloads, sem SQLite, sem dados de 2022. Nao altera os caches H/J/K.

O NR_VOTAVEL=28 foi identificado em fonte independente (soma 5.246),
mas o script NAO assume essa soma: recalcula os votos 28 dos BWEB reais
e exige confronto UF por UF. Uma falha de conciliacao nao e ocultada.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import io
import json
import os
from pathlib import Path
import zipfile

from extract_bweb_received_2026 import UFs, discover_archive, norm
from reconcile_stream import sha256
from urnas import root_path

VERSION="phase5g-candidate-28-reconciliation-2026-v1"
HEAD=("UF","votos_28_BWEB","secoes_com_voto_28","diferenca_validos_K",
      "diferenca_demais_K","diferenca_13_K","diferenca_22_K",
      "residuo_sem_28","status")


def atomic_csv(path, data):
    tmp=Path(str(path)+".part")
    try:
        with tmp.open("w",encoding="utf-8",newline="") as f:
            w=csv.DictWriter(f,fieldnames=HEAD,delimiter=";",
                             lineterminator="\n")
            w.writeheader()
            w.writerows(data)
            f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if tmp.exists():tmp.unlink()


def atomic_json(path, obj):
    tmp=Path(str(path)+".part")
    try:
        with tmp.open("w",encoding="utf-8") as f:
            json.dump(obj,f,indent=2,ensure_ascii=False)
            f.write("\n");f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if tmp.exists():tmp.unlink()


def read_k_report(folder):
    summary=folder/"phase5f_reconciliation_2026_summary.json"
    if not summary.is_file():
        raise RuntimeError("Execute K primeiro: conciliacao UF indisponivel")
    meta=json.loads(summary.read_text("utf-8"))
    report=folder/"phase5f_reconciliation_by_uf_2026.csv"
    if not report.is_file() or sha256(report)!=meta["by_uf_sha256"]:
        raise RuntimeError("Dados K ausentes ou SHA divergente")
    data={}
    with report.open(encoding="utf-8-sig",newline="") as f:
        for row in csv.DictReader(f,delimiter=";"):
            uf=row["UF"]
            if uf in data:
                raise RuntimeError("UF repetida no resultado K")
            data[uf]=row
    if set(data)!=set(UFs):
        raise RuntimeError("Cobranca K nao cobre 27 UFs + ZZ")
    return data,sha256(report)


def scan_28(zip_path,uf):
    """Le somente colunas necessarias, e somente linhas Presidente/turno 1."""
    summed=Counter()
    per_section=Counter()
    types=Counter()
    lines=0
    with zipfile.ZipFile(zip_path) as archive:
        members=[name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(members)!=1:
            raise RuntimeError("ZIP nao possui um unico CSV: "+str(zip_path))
        with archive.open(members[0]) as stream:
            text=io.TextIOWrapper(stream,encoding="latin-1",errors="replace",newline="")
            reader=csv.DictReader(text,delimiter=";")
            headers={str(k).strip().replace("ï»¿","").replace("\ufeff",""):k
                     for k in (reader.fieldnames or [])}
            needed=("NR_TURNO","SG_UF","DS_CARGO_PERGUNTA","NR_VOTAVEL",
                    "QT_VOTOS","DS_TIPO_VOTAVEL","CD_MUNICIPIO","NR_ZONA","NR_SECAO")
            if any(x not in headers for x in needed):
                raise RuntimeError("BWEB incompleto: "+str(zip_path))
            for row in reader:
                lines+=1
                val=lambda c:row[headers[c]]
                if (val("NR_TURNO").strip()!="1" or
                    val("DS_CARGO_PERGUNTA").strip().casefold()!="presidente" or
                    val("NR_VOTAVEL").strip()!="28"):
                    continue
                if val("SG_UF").strip().upper()!=uf:
                    raise RuntimeError("NR_VOTAVEL 28 encontrado em UF errada")
                n=int(val("QT_VOTOS"))
                if n<0:
                    raise RuntimeError("Numero de votos negativo")
                ident=(uf,norm(val("CD_MUNICIPIO")),norm(val("NR_ZONA")),
                       norm(val("NR_SECAO")))
                per_section[ident]+=n
                typ=val("DS_TIPO_VOTAVEL").strip() or "(vazio)"
                types[typ]+=n
                summed["votes"]+=n
                summed["rows"]+=1
    return {
        "votos_28":summed["votes"],
        "registros_28":summed["rows"],
        "secoes_com_28":sum(n>0 for n in per_section.values()),
        "DS_TIPO_VOTAVEL_28":dict(sorted(types.items())),
        "total_rows_scanned":lines,
    }


def run(root):
    folder=root/"analysis"/"periodicidade_bweb_2026"
    k,known_hash=read_k_report(folder)
    rows=[]
    evidence={}
    for uf in UFs:
        archive,archive_sha=discover_archive(root,uf)
        detail=scan_28(archive,uf)
        official=k[uf]
        excess=int(official["diferenca_validos"])
        excess_other=int(official["diferenca_demais"])
        delta13=int(official["diferenca_13"])
        delta22=int(official["diferenca_22"])
        residual=excess-detail["votos_28"]
        ok=(residual==0 and excess_other==detail["votos_28"]
            and delta13==0 and delta22==0)
        status="RECONCILIADO_NR_28" if ok else "DIVERGENCIA_A_INVESTIGAR"
        rows.append(dict(zip(HEAD,(
            uf,detail["votos_28"],detail["secoes_com_28"],excess,
            excess_other,delta13,delta22,residual,status))))
        evidence[uf]={"source":str(archive),"sha256":archive_sha,**detail}
        print(f"[NR28 {uf}] BWEB={detail['votos_28']:,} "
              f"excedente_K={excess:,} residuo={residual:+,} "
              f"status={status}",flush=True)

    total=sum(row["votos_28_BWEB"] for row in rows)
    expected=sum(int(row["diferenca_validos"]) for row in k.values())
    correct=all(row["status"]=="RECONCILIADO_NR_28" for row in rows)
    fname=folder/"phase5g_nr28_by_uf_2026.csv"
    atomic_csv(fname,rows)
    summary={
        "version":VERSION,
        "status":"CONCILIACAO_COMPLETA_NR_28" if correct else "RESTAM_DIVERGENCIAS",
        "scope":"Presidente 1 turno 2026, todas as 27 UFs + ZZ",
        "source":"BWEB 2026 originais ja existentes localmente, SHA original conferido",
        "reference_K_sha256":known_hash,
        "votes_28_total_BWEB":total,
        "excess_valid_k":expected,
        "difference_after_excluding_nr_28":expected-total,
        "ufs_reconciled":sum(row["status"]=="RECONCILIADO_NR_28" for row in rows),
        "ufs_total":len(rows),
        "rows_file":str(fname),
        "rows_sha256":sha256(fname),
        "by_uf":rows,
        "sources_by_uf":evidence,
        "interpretation":[
            "Numero 28 foi votavel BWEB mas nao integra candidatos validos oficiais 2026",
            "O extrator H marcou como valido todo voto diferente de Branco/Nulo, incluindo o 28",
            "NR_VOTAVEL 28 nao pode ser presumido valido depois de renuncia/indeferimento",
            "Os 5246 votos sao diferenca de classificacao, nao transferencia entre votos 13 e 22",
            "A comparacao de 499206 vs 499248 secoes e independente desta reconciliacao",
        ],
        "limitations":[
            "Os ZIPs originais locais foram reabertos apenas para conferir nominal 28",
            "DS_TIPO_VOTAVEL descreve forma do registro BWEB, nao destino juridico do voto",
            "BWEB e resultado oficial nao sao capturas fisicas independentes",
            "Nenhum download, SQLite ou microdado de 2022 foi utilizado"
        ]
    }
    output=folder/"phase5g_nr28_reconciliation_2026_summary.json"
    atomic_json(output,summary)
    print(json.dumps({
        "status":summary["status"],"votos_28":total,
        "excedente_K":expected,"residuo":expected-total,
        "ufs_reconciled":summary["ufs_reconciled"],
        "csv":str(fname),"summary":str(output)},
        ensure_ascii=False,indent=2),flush=True)
    return summary


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",help="Raiz H: do arquivo forense existente")
    args=parser.parse_args()
    run(root_path(args.root))
