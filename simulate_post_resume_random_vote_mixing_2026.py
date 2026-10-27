#!/usr/bin/env python3
"""Teste de mistura aleatoria dos votos restantes nos 152 lotes de 2026.

MODELO CONDICIONAL ILUSTRATIVO, nao detector de fraude.
Mantem totais de votos por candidato e numero de votos por lote,
mas redistribui votos INDIVIDUAIS aleatoriamente sem reposicao
entre lotes. Nao preserva agrupamento dos BUs por secao/territorio.
Nao baixa dados, nao consulta SQLite e nao cria relatorios em H:.
Requer NumPy apenas para amostragem hipergeometrica multivariada.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path

START_N = 100_491_132
START_FLAVIO = 48_704_246
START_LULA = 43_705_754
EXPECTED_FINAL_N = 119_300_788
EXPECTED_FINAL_F = 56_104_503
EXPECTED_FINAL_L = 53_879_538
DEFAULT_CSV = Path("data/forensics/analysis/phase4g_post_resume_batches.csv")


def load_batches(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        records=list(csv.DictReader(stream))
    if len(records)!=152:
        raise ValueError("Esperados exatamente 152 lotes pos-20:04:39")
    sizes=[]
    total_f=total_l=0
    for row in records:
        size=int(row["d_vv"])
        f=int(row["d_flavio"])
        l=int(row["d_lula"])
        if size<=0 or f<0 or l<0 or f+l>size:
            raise ValueError("Contagens impossiveis no lote")
        sizes.append(size)
        total_f+=f
        total_l+=l
    if (START_N+sum(sizes), START_FLAVIO+total_f, START_LULA+total_l) != (
        EXPECTED_FINAL_N,EXPECTED_FINAL_F,EXPECTED_FINAL_L):
        raise ValueError("Soma dos 152 lotes diverge do total final documentado")
    return sizes,(total_f,total_l,sum(sizes)-total_f-total_l)


def run(nsim=10000,seed=20261027,path=DEFAULT_CSV):
    try:
        import numpy as np
    except ImportError as exc:
        raise SystemExit("NumPy necessario: python -m pip install numpy") from exc
    sizes,pool=load_batches(path)
    rng=np.random.default_rng(seed)
    counts={"flavio_152_quedas":0,"lula_152_subidas":0,
            "ambas_152":0}
    dist={150:0,151:0,152:0}
    for _ in range(nsim):
        rest=np.array(pool,dtype=np.int64)
        n0=START_N
        f0=START_FLAVIO
        l0=START_LULA
        falls=rises=0
        for n in sizes:
            f,l,o=(int(v) for v in rng.multivariate_hypergeometric(rest,n))
            rest-=np.array([f,l,o],dtype=np.int64)
            # Contagens inteiras evitam arredondamentos dos percentuais.
            falls+=int(f*n0 < f0*n)
            rises+=int(l*n0 > l0*n)
            n0+=n
            f0+=f
            l0+=l
        counts["flavio_152_quedas"]+=int(falls==152)
        counts["lula_152_subidas"]+=int(rises==152)
        counts["ambas_152"]+=int(falls==rises==152)
        dist[falls]=dist.get(falls,0)+1
    report={"version":"mix-votos-condicional-2026-v1",
            "status":"SIMULACAO_SOB_MODELO_CONDICIONAL",
            "source":str(path),"seed":seed,
            "simulacoes":nsim,"tamanhos_lote":len(sizes),
            "votos_restantes":sum(sizes),
            "flavio_restantes":pool[0],
            "lula_restantes":pool[1],
            "outros_restantes":pool[2],
            "probabilidades_empiricas_pct":{
                k:round(100*v/nsim,5) for k,v in counts.items()},
            "contagens":counts,"distribuicao_n_quedas_flavio":dist,
            "limites":[
                "Esta simulacao EMBARALHA VOTOS, NAO urnas, e condiciona ao resultado e pool tardio observados",
                "Nao testa se a selecao do pool tardio nem os horarios ocorreram naturalmente",
                "Nao testa periodos, saltos temporais nem fraude de totalizacao",
                "Frequencia Monte Carlo sob nulo artificial nao e probabilidade de fraude ou inocencia"]}
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulacoes",type=int,default=10000)
    parser.add_argument("--semente",type=int,default=20261027)
    parser.add_argument("--csv",type=Path,default=DEFAULT_CSV)
    args=parser.parse_args()
    if args.simulacoes<1:
        parser.error("--simulacoes deve ser positivo")
    print(json.dumps(run(args.simulacoes,args.semente,args.csv),
                     ensure_ascii=False,indent=2))
