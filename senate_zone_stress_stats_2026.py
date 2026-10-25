"""Teste adversarial descritivo de exclusao conjunta de zonas (2026).

Amostra de pares pre-selecionados (13 entre 616): nao inferir
significancia ou probabilidade de fraude. Trabalha com momentos zonais.
"""
from __future__ import annotations
import hashlib
import random
from senate_robustness_stats_2026 import centered, pearson, sum_cov, quantile


def stress(key, records, reference, repetitions=400):
    if repetitions < 100:
        raise ValueError("Sao exigidas pelo menos 100 replicacoes")
    total_sections=sum(m[0] for _,m in records)
    active=sorted(((ident,m,centered(m)) for ident,m in records if m[0]>=2),
                  key=lambda item:item[0])
    if total_sections!=reference["n"] or len(active)!=reference["z"]:
        raise RuntimeError("Quantidade de secoes ou zonas difere da v2")
    base=sum_cov(x[2] for x in active)
    original=pearson(base)
    if original is None or abs(original-reference["adjusted"])>2e-5:
        raise RuntimeError("Coeficiente original nao foi reproduzido")
    if len(active)<7:
        raise RuntimeError("Menos de 7 zonas com variacao: exclusao de 5 inaplicavel")

    def without(indices):
        excluded=set(indices)
        left=[record[2] for j,record in enumerate(active) if j not in excluded]
        value=pearson(sum_cov(left))
        if value is None:
            raise RuntimeError("Exclusao resultou em variancia nula")
        removed=sum(active[j][1][0] for j in excluded)
        return value, removed

    by_cov=sorted(range(len(active)),
                  key=lambda i:(-abs(active[i][2][0]),active[i][0]))
    sensitivities=[]
    for i,(_,_,v) in enumerate(active):
        trial,_=without((i,))
        sensitivities.append((abs(trial-original), i))
    by_influence=[i for _,i in sorted(
        sensitivities,key=lambda x:(-x[0],active[x[1]][0]))]

    result={"UF":key[0],"presidente":key[1],"senador":key[2],
            "secoes":total_sections,"zonas_n2":len(active),
            "r_original":round(original,6)}
    for k in (1,3,5):
        observed, dropped=without(by_cov[:k])
        result[f"r_sem_top{k}_cov_abs"]=round(observed,6)
        result[f"pct_secoes_retiradas_top{k}_cov_abs"]=round(
            100*dropped/total_sections,3)
        result[f"mudou_sinal_top{k}_cov_abs"]=int(observed*original<0)

    observed,dropped=without(by_influence[:5])
    result["r_sem_top5_impacto_individual"]=round(observed,6)
    result["pct_secoes_retiradas_top5_impacto_individual"]=round(
        100*dropped/total_sections,3)
    result["mudou_sinal_top5_impacto_individual"]=int(observed*original<0)

    seed=int.from_bytes(hashlib.sha256(
        ("stress-zone-2026-v1|"+"|".join(key)).encode("utf-8")
    ).digest()[:8],"big")
    rng=random.Random(seed)
    draws=[without(rng.sample(range(len(active)),5))[0]
           for _ in range(repetitions)]
    draws.sort()
    result["rand5_replicacoes"]=len(draws)
    result["rand5_pct_mesmo_sinal"]=round(
        100*sum(r*original>0 for r in draws)/len(draws),3)
    result["rand5_min_r"]=round(draws[0],6)
    result["rand5_p025_r"]=round(quantile(draws,.025),6)
    result["rand5_mediana_r"]=round(quantile(draws,.5),6)
    result["rand5_p975_r"]=round(quantile(draws,.975),6)
    result["rand5_max_r"]=round(draws[-1],6)
    critical=[]
    for category,ranking in (("cov_abs",by_cov),("impacto_individual",by_influence)):
        for position,index in enumerate(ranking[:5],1):
            ident,n,cov=active[index]
            trial,_=without((index,))
            critical.append({
                "UF":ident[0],"municipio":ident[1],"zona":ident[2],
                "turno":ident[3],"presidente":ident[4],"senador":ident[5],
                "criterio":category,"posicao":position,
                "secoes":n[0],"cov_xy_intrazona":round(cov[0],9),
                "r_sem_zona":round(trial,6)})
    return result,critical
