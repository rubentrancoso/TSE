#!/usr/bin/env python3
"""Fase 5N: investigar empates e resultados IDENTICOS em secoes do 1T 2026.

Base: BWEB primeiro turno ja extraido em H e os 5.246 votos tecnicos 28
corrigidos na M. Nenhum download, ZIP, SQLite ou dados de 2022.
Tres hipoteses distintas:
(A) 13=22 NA MESMA secao, sem confundir com n=0;
(B) tres ou mais secoes com par IDENTICO (13,22);
(C) tres ou mais secoes com vetor presidencial completo IDENTICO.

Descreve repeticoes no Brasil inteiro, municipio e zona. Permuta pares
entre secoes do mesmo municipio e faixa de volume 13+22, preservando
exatamente o multiconjunto dos pares, e verifica se ha aglomeracao
desses pares em zonas acima do esperado SOB ESSE MODELO. Nao e um
teste de fraude nem de autenticidade da urna. Evidencia fisica requer
comparar BUs e RDV originais das secoes sinalizadas.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import json
import math
import os
from pathlib import Path
import random

from extract_bweb_received_2026 import VERSION as H_VERSION, UFs, norm
from correct_bweb_28_periodicity_2026 import VERSION as M_VERSION
from reconcile_stream import sha256
from urnas import root_path

VERSION="phase5n-repeated-presidential-votes-2026-v1"
BASE=Path("analysis/periodicidade_bweb_2026")
MIN_CANDIDATES=80
SEED=20261028
# Bins conservam municipio e ordem de grandeza do tamanho das secoes.
VOLUME_BINS=(80,120,160,200,240,280,320,400,500,650,1000)

def atomic_csv(path,fields,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=Path(str(path)+".part")
    try:
        with tmp.open("w",encoding="utf-8",newline="") as f:
            w=csv.DictWriter(f,fieldnames=fields,delimiter=";",
                             lineterminator="\n",extrasaction="ignore")
            w.writeheader();w.writerows(rows)
            f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if tmp.exists():tmp.unlink()

def atomic_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=Path(str(path)+".part")
    try:
        with tmp.open("w",encoding="utf-8") as f:
            json.dump(data,f,ensure_ascii=False,indent=2)
            f.write("\n");f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if tmp.exists():tmp.unlink()

def load28(folder,uf):
    meta=folder/f"phase5h_nr28_sections_{uf}.json"
    path=folder/f"phase5h_nr28_sections_{uf}.csv"
    if not meta.is_file() or not path.is_file():
        raise RuntimeError("Cache NR28 da opcao M ausente: "+uf)
    state=json.loads(meta.read_text("utf-8"))
    if state.get("version")!=M_VERSION or sha256(path)!=state["csv_sha256"]:
        raise RuntimeError("SHA/metadados NR28 invalidos: "+uf)
    found={}
    with path.open(encoding="utf-8-sig",newline="") as f:
        for r in csv.DictReader(f,delimiter=";"):
            k=(r["UF"],*[norm(r[c]) for c in ("municipio","zona","secao")])
            if k in found or k[0]!=uf:
                raise RuntimeError("NR28 secao duplicada ou UF errada")
            n=int(r["votos_28"])
            if n<0:raise RuntimeError("NR28 negativo")
            found[k]=n
    if sum(found.values())!=state["votes_28"]:
        raise RuntimeError("Soma nr28 difere da opcao M")
    return found,state

def verified_input(folder):
    h=folder/"summary.json"
    m=folder/"phase5h_corrected_periodicity_2026_summary.json"
    if not h.is_file() or not m.is_file():
        raise RuntimeError("Necessarias as opcoes H e M ja concluidas")
    ha=json.loads(h.read_text("utf-8"))
    ma=json.loads(m.read_text("utf-8"))
    if (ha.get("version")!=H_VERSION
        or ha.get("sections")!=499206
        or set(ha.get("ufs",{}))!=set(UFs)
        or ma.get("status")!="VALIDOS_PRESIDENCIAIS_CORRIGIDOS"
        or ma.get("difference_valid_vs_official")!=0
        or ma["corrected_totals"]["valid"]!=119300788):
        raise RuntimeError("Fontes H/M nao sao o certificado real do primeiro turno")
    return ha,ma,sha256(h),sha256(m)

def iter_sections(folder,uf,manifest):
    shard=folder/f"received-{uf}.csv"
    if not shard.is_file() or sha256(shard)!=manifest["ufs"][uf]["shard_sha256"]:
        raise RuntimeError("Cache H modificado na UF "+uf)
    n28,meta=load28(folder,uf)
    seen=set()
    totals=Counter()
    with shard.open(encoding="utf-8-sig",newline="") as f:
        for r in csv.DictReader(f,delimiter=";"):
            if r["UF"]!=uf or norm(r["turno"])!="1":
                raise RuntimeError("UF ou turno divergente no BWEB")
            key=(uf,*[norm(r[c]) for c in ("municipio","zona","secao")])
            if key in seen:raise RuntimeError("Seção duplicada "+repr(key))
            seen.add(key)
            technical=n28.pop(key,0)
            lula=int(r["votos_13"]);bolsonaro=int(r["votos_22"])
            raw=int(r["votos_pres_validos"])
            valid=raw-technical
            blank=int(r["brancos"]);null=int(r["nulos"])
            total=int(r["votos_pres_total"])
            others=valid-lula-bolsonaro
            if min(technical,lula,bolsonaro,valid,blank,null,others)<0:
                raise RuntimeError("BWEB valores inconsistentes "+repr(key))
            if total!=valid+technical+blank+null:
                raise RuntimeError("BU total != validos+brancos+nulos+28")
            totals.update(sections=1,valid=valid,lula=lula,
                          flavio=bolsonaro,technical=technical)
            yield {
                "UF":uf,"municipio":key[1],"zona":key[2],"secao":key[3],
                "lula_13":lula,"flavio_22":bolsonaro,"outros_validos":others,
                "brancos":blank,"nulos":null,"votos_28":technical,
                "validos":valid,"total":total,
                "n_dupla":lula+bolsonaro,
                "recebido":r["DT_BU_RECEBIDO"],
            }
    if n28:raise RuntimeError(f"{uf}: cache NR28 tem chaves sem BWEB")
    if totals["sections"]!=manifest["ufs"][uf]["sections"]:
        raise RuntimeError(f"{uf}: numero de secoes diverge do H")
    return totals

def read_all(folder,manifest,ma):
    records=[]
    totals=Counter()
    for uf in UFs:
        for r in iter_sections(folder,uf,manifest):
            records.append(r)
            totals.update(sections=1,valid=r["validos"],lula=r["lula_13"],
                          flavio=r["flavio_22"],technical=r["votos_28"])
        print(f"[UF {uf}] leitura de BU e hash H/M conferidos",flush=True)
    if dict(totals)!={
        "sections":499206,"valid":119300788,"lula":53879538,
        "flavio":56104503,"technical":5246
    }:
        raise RuntimeError("Somas nacionais por secao nao fecham com a Fase M: "+str(totals))
    return records,dict(totals)

def three_or_more(rows,keyfn,scopefn,minvotes=MIN_CANDIDATES):
    groups=defaultdict(list)
    for row in rows:
        if row["n_dupla"]<minvotes:continue
        key=(*scopefn(row),*keyfn(row))
        groups[key].append(row)
    return {k:v for k,v in groups.items() if len(v)>=3}

def profile(rows,minvotes=MIN_CANDIDATES):
    valid=[r for r in rows if r["n_dupla"]>=minvotes]
    tie=[r for r in valid if r["lula_13"]==r["flavio_22"]]
    zero=[r for r in rows if r["n_dupla"]==0]
    pair=lambda x:(x["lula_13"],x["flavio_22"])
    full=lambda x:(x["lula_13"],x["flavio_22"],x["outros_validos"],
                   x["brancos"],x["nulos"],x["votos_28"])
    same_zone=lambda x:(x["UF"],x["municipio"],x["zona"])
    same_mun=lambda x:(x["UF"],x["municipio"])
    global_scope=lambda x:()
    groups={}
    for name,scoper in (("zona",same_zone),("municipio",same_mun),
                        ("brasil",global_scope)):
        groups[name+"_par"]=three_or_more(rows,pair,scoper,minvotes)
        groups[name+"_vetor"]=three_or_more(rows,full,scoper,minvotes)
    return valid,tie,zero,groups

def zone_tie_expectation(rows,minvotes=MIN_CANDIDATES,prior_votes=1000):
    """E[empates] condicional a N=lula+flavio e p local suavizado.

    E[empate] = C(n,n/2)*p^(n/2)*(1-p)^(n/2) se n par.
    Estimativa p da zona leave-one-out, suavizada para UF; nao e
    p-valor definitivo pois votos individuais nao sao i.i.d.
    """
    zone_tot=defaultdict(lambda:[0,0])
    uf_tot=defaultdict(lambda:[0,0])
    for r in rows:
        z=(r["UF"],r["municipio"],r["zona"])
        zone_tot[z][0]+=r["lula_13"];zone_tot[z][1]+=r["n_dupla"]
        uf_tot[r["UF"]][0]+=r["lula_13"];uf_tot[r["UF"]][1]+=r["n_dupla"]
    expected=0.
    var=0.
    for r in rows:
        n=r["n_dupla"]
        if n<minvotes or n%2:continue
        z=(r["UF"],r["municipio"],r["zona"])
        ul,un=uf_tot[r["UF"]]
        zl,zn=zone_tot[z]
        puf=(ul+0.5)/(un+1)
        p=(zl-r["lula_13"]+prior_votes*puf)/(zn-n+prior_votes)
        if not 0<p<1:raise RuntimeError("p de zona fora da faixa")
        probability=math.exp(
            math.lgamma(n+1)-2*math.lgamma(n//2+1)
            +(n//2)*(math.log(p)+math.log1p(-p)))
        expected+=probability
        var+=probability*(1-probability)
    return {"model":"binomial condicional ao tamanho do lote 13+22, p da zona leave-one-out e prior UF 1000 votos",
        "expected_ties":expected,"approx_variance":var,
        "approx_sd":math.sqrt(var),
        "notes":"Somente referencia de plausibilidade; heterogeneidade intra-zona e dependencia entre eleitores nao sao representadas."}

def bucket(n):
    for i,edge in enumerate(VOLUME_BINS):
        if n<edge:return i
    return len(VOLUME_BINS)

def zone_triplet_stat(votes,zone_ids):
    counts=Counter(zip(zone_ids,votes))
    groups=sum(n>=3 for n in counts.values())
    combinations=sum(n*(n-1)*(n-2)//6 for n in counts.values() if n>=3)
    max_count=max(counts.values(),default=0)
    return (groups,combinations,max_count)

def spatial_test(rows,repetitions=199,seed=SEED,minvotes=MIN_CANDIDATES):
    """Permuta pares entre zonas de MESMO municipio e faixa n.
    Avalia concentracao de COPIAS do par dentro da mesma zona.
    Nao testa se os empates ou triplets nacionais sao anomalos.
    """
    if repetitions<99:raise ValueError("Permutacoes insuficientes")
    strata=defaultdict(list)
    for row in rows:
        if row["n_dupla"]<minvotes:continue
        k=(row["UF"],row["municipio"],bucket(row["n_dupla"]))
        strata[k].append(((row["UF"],row["municipio"],row["zona"]),
                   (row["lula_13"],row["flavio_22"])))
    active=[]
    baseline=(0,0,0)
    # Unidades nao permutaveis sao constantes em cada simulacao.
    fixed_counts=Counter()
    for values in strata.values():
        if len(values)<3 or len({z for z,pair in values})<2:
            fixed_counts.update(values)
        else:
            active.append(values)
    fixed_groups=sum(n>=3 for n in fixed_counts.values())
    fixed_combos=sum(n*(n-1)*(n-2)//6 for n in fixed_counts.values() if n>=3)
    fixed_max=max(fixed_counts.values(),default=0)
    observed=Counter()
    for group in active:
        observed.update(group)
    observed_groups=fixed_groups+sum(n>=3 for n in observed.values())
    observed_combos=fixed_combos+sum(n*(n-1)*(n-2)//6 for n in observed.values() if n>=3)
    rng=random.Random(seed)
    simulations=[]
    exceed=0
    for i in range(repetitions):
        sim=Counter()
        for group in active:
            zones=[zone for zone,pair in group]
            vote_pairs=[pair for zone,pair in group]
            rng.shuffle(vote_pairs)
            sim.update(zip(zones,vote_pairs))
        combos=fixed_combos+sum(n*(n-1)*(n-2)//6 for n in sim.values() if n>=3)
        simulations.append(combos)
        exceed+=combos>=observed_combos
        if (i+1)%100==0:
            print(f"[NULO espacial] {i+1}/{repetitions} excedencias={exceed}",flush=True)
    simulations.sort()
    return {
       "definition":"número de combinações de 3 seções da MESMA zona com par Lula/Flávio idêntico",
       "observed_zone_triplet_groups":observed_groups,
       "observed_triplet_combinations":observed_combos,
       "fixed_nonpermutable_triplet_combinations":fixed_combos,
       "eligible_strata":len(active),
       "repetitions":repetitions,
       "exceedances":exceed,
       "p_spatial_cluster":(exceed+1)/(repetitions+1),
       "null_median":simulations[len(simulations)//2],
       "null_p95":simulations[min(len(simulations)-1,int(repetitions*.95))],
       "warning":"Teste de agrupamento de pares JA observados, condicionado a municipio e volume; nao testa a probabilidade absoluta de gerar cada par e nao preserva exatamente composicao de cada zona."}

def report_rows(groups,kind):
    output=[]
    for group_name,pairs in groups.items():
        for key,sections in pairs.items():
            n=len(sections)
            sample=sections[0]
            output.append({"escopo":group_name,
                "tipo":("par" if group_name.endswith("_par") else "vetor"),
                "UF":sample["UF"] if "brasil" not in group_name else "BR",
                "municipio":sample["municipio"] if "brasil" not in group_name else "",
                "zona":sample["zona"] if "zona_" in group_name else "",
                "votos_lula":sample["lula_13"],"votos_flavio":sample["flavio_22"],
                "outros":sample["outros_validos"] if group_name.endswith("vetor") else "",
                "brancos":sample["brancos"] if group_name.endswith("vetor") else "",
                "nulos":sample["nulos"] if group_name.endswith("vetor") else "",
                "nr28":sample["votos_28"] if group_name.endswith("vetor") else "",
                "secoes":n,
                "combinacoes_de_tres":n*(n-1)*(n-2)//6,
                "chaves":"|".join(f"{r['UF']}/{r['municipio']}/{r['zona']}/{r['secao']}" for r in sorted(sections,key=lambda x:(x["UF"],int(x["municipio"]),int(x["zona"]),int(x["secao"]))))
                })
    return output

GROUP_FIELDS=("escopo","tipo","UF","municipio","zona","votos_lula",
              "votos_flavio","outros","brancos","nulos","nr28",
              "secoes","combinacoes_de_tres","chaves")
TIE_FIELDS=("UF","municipio","zona","secao","lula_13","flavio_22",
            "outros_validos","brancos","nulos","votos_28","validos",
            "n_dupla","recebido")

def run(root,repetitions=199,minvotes=MIN_CANDIDATES):
    folder=root/BASE
    ha,ma,h_sha,m_sha=verified_input(folder)
    rows,totals=read_all(folder,ha,ma)
    valid,ties,zero,groups=profile(rows,minvotes)
    tie_model=zone_tie_expectation(rows,minvotes)
    spatial=spatial_test(rows,repetitions,minvotes=minvotes)
    out_groups=report_rows(groups,None)
    out_groups.sort(key=lambda x:(-x["secoes"],x["escopo"],x["UF"],x["municipio"]))
    summaries={key:{"groups":len(v),
          "sections":sum(len(rs) for rs in v.values()),
          "triplets_combinations":sum(len(rs)*(len(rs)-1)*(len(rs)-2)//6
                     for rs in v.values())} for key,v in groups.items()}
    print(f"[1T 2026] secoes={totals['sections']:,} empates 13=22 "
          f"com n>={minvotes}: {len(ties):,}; "
          f"esperado binomial simplificado={tie_model['expected_ties']:.1f}",
          flush=True)
    for key,item in summaries.items():
        print(f"[{key}] grupos de 3+ = {item['groups']}, "
              f"secoes envolvidas={item['sections']}",flush=True)
    print(f"[NULO zona] p={spatial['p_spatial_cluster']:.5f}, "
          f"observado triplets={spatial['observed_triplet_combinations']} "
          f"mediana nula={spatial['null_median']}",flush=True)
    tie_file=folder/"phase5n_2026_ties_lula_flavio_by_section.csv"
    group_file=folder/"phase5n_2026_three_or_more_identical_results.csv"
    atomic_csv(tie_file,TIE_FIELDS,ties)
    atomic_csv(group_file,GROUP_FIELDS,out_groups)
    summary={
        "version":VERSION,"status":"PARES_IDENTICOS_1T_2026_AUDITADOS",
        "year":2026,"round":1,
        "candidates":{"13":"Lula","22":"Flavio Bolsonaro"},
        "source_BWEB_H_sha256":h_sha,"source_corrected_M_sha256":m_sha,
        "sections_verified":totals["sections"],
        "votes_reconciled":totals,
        "minimum_two_candidate_votes":minvotes,
        "zero_duo_sections_not_counted_as_ties":len(zero),
        "eligible_sections":len(valid),
        "actual_ties_13_equals_22":len(ties),
        "expected_ties_independent_binomial_reference":tie_model,
        "repeated_pair_and_full_vector":summaries,
        "spatial_permutation_by_municipality_and_vote_volume":spatial,
        "largest_repeated_groups":out_groups[:20],
        "tie_csv_path":str(tie_file),"tie_csv_sha256":sha256(tie_file),
        "groups_csv_path":str(group_file),"groups_csv_sha256":sha256(group_file),
        "limitations":[
          "Somente primeiro turno 2026; nenhum dado do segundo turno foi testado",
          "Empates Lula=Flavio dentro de urna e triplas de resultados iguais entre urnas sao hipoteses DISTINTAS",
          "Grupos globais repetidos crescem naturalmente com a quantidade de secoes; priorizar mesma zona e vetor completo",
          "Referencia binomial ignora heterogeneidade de eleitores; nao e prova de fraude nem valor p causal",
          "Permutacao preserva pares observados e municipio/faixa de tamanho; avalia apenas agrupamento entre zonas, nao geracao dos pares",
          "O vetor completo inclui nulos tecnicos 28 para evitar falsa equivalencia de votos validos",
          "Fontes BWEB e EA16 sao oficiais, nao BUs fisicos auditados independentemente",
          "Qualquer alegacao sobre 2o turno de 2026 exige leitura dos BU do segundo turno, nao deducao do primeiro"
        ]}
    path=folder/"phase5n_2026_identical_presidential_sections_summary.json"
    atomic_json(path,summary)
    print(json.dumps({"status":summary["status"],
                      "empates":len(ties),"triplas":summaries,
                      "nulo_espacial":spatial,
                      "summary":str(path)},ensure_ascii=False,indent=2),flush=True)
    return summary

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root")
    parser.add_argument("--permutacoes",type=int,default=199)
    parser.add_argument("--minimo-votos-dois-candidatos",type=int,default=80)
    args=parser.parse_args()
    run(root_path(args.root),args.permutacoes,args.minimo_votos_dois_candidatos)
