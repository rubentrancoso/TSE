"""Momentos estatisticos para analise intrazona, sem leitura de arquivos."""
import math
import random


def pearson(cov):
    xy, xx, yy = cov
    if xx <= 1e-12 or yy <= 1e-12:
        return None
    return max(-1.0, min(1.0, xy / math.sqrt(xx * yy)))


def centered(m):
    n, sx, sy, xx, yy, xy = m
    return (xy-sx*sy/n, max(0.0, xx-sx*sx/n),
            max(0.0, yy-sy*sy/n))


def sum_cov(moments):
    return tuple(math.fsum(m[i] for m in moments) for i in range(3))


def quantile(ordered, p):
    loc = p * (len(ordered)-1)
    i = int(loc)
    alpha = loc-i
    return ordered[i]*(1-alpha)+ordered[min(i+1,len(ordered)-1)]*alpha


def analyze(moments, n_expected, zones_expected, raw_expected,
            adjusted_expected, seed, draws=400):
    if draws < 100:
        raise ValueError("Bootstrap exige pelo menos 100 replicacoes")
    n = sum(m[0] for m in moments)
    active = [m for m in moments if m[0] >= 2]
    if n != n_expected or len(active) != zones_expected:
        raise RuntimeError("Total de secoes/zonas nao coincide")
    sx, sy, xx, yy, xy = [
        math.fsum(m[i] for m in moments) for i in range(1,6)]
    raw = pearson((xy-sx*sy/n, xx-sx*sx/n, yy-sy*sy/n))
    cov = [centered(m) for m in active]
    base = sum_cov(cov)
    adjusted = pearson(base)
    if (raw is None or adjusted is None or
        abs(raw-raw_expected) > 2e-5 or
        abs(adjusted-adjusted_expected) > 2e-5):
        raise RuntimeError("Coeficientes nao coincidem com Senado v2")
    side = 1 if adjusted > 0 else -1
    loo = [pearson(tuple(base[i]-v[i] for i in range(3))) for v in cov]
    loo = [x for x in loo if x is not None]
    if not loo:
        raise RuntimeError("Sem leave-one-zone-out definido")
    rng = random.Random(seed)
    bootstrap = []
    for _ in range(draws):
        picks = (cov[rng.randrange(len(cov))] for _ in range(len(cov)))
        value = pearson(sum_cov(picks))
        if value is not None:
            bootstrap.append(value)
    if not bootstrap:
        raise RuntimeError("Bootstrap sem correlacoes definidas")
    bootstrap.sort()
    def filter_size(size):
        sample = [centered(m) for m in moments if m[0] >= size]
        coef = pearson(sum_cov(sample)) if sample else None
        return "" if coef is None else round(coef, 6)
    return {
        "r_bruto": round(raw, 6),
        "r_ajustado": round(adjusted, 6),
        "r_zonas_n5": filter_size(5),
        "r_zonas_n10": filter_size(10),
        "pct_loo_mesmo_sinal": round(100*sum(side*x>0 for x in loo)/len(loo),3),
        "pct_boot_mesmo_sinal": round(100*sum(side*x>0 for x in bootstrap)/len(bootstrap),3),
        "pct_boot_mesmo_sinal_e_modulo_010": round(
            100*sum(side*x>=0.1 for x in bootstrap)/len(bootstrap),3),
        "bootstrap_p025": round(quantile(bootstrap,0.025),6),
        "bootstrap_p975": round(quantile(bootstrap,0.975),6),
        "bootstrap_validos": len(bootstrap),
        "secoes": n, "zonas_n2": len(active)
    }
