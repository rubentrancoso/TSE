#!/usr/bin/env python3
"""Correlacoes ECOLOGICAS Presidente x Governador no 1o turno por UF.

Le somente arquivos de candidatos BU extraidos em 'entre_cargos'.
Nao abre SQLite nem infere voto individual. Agrupamento por secao;
coeficientes brutos e ajustados dentro de municipio+zona.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import argparse
import csv
import json
import math
import os
from pathlib import Path

from reconcile_stream import sha256
from urnas import root_path

VERSION = "cross-office-candidate-pairs-v1"
INVALID = {"95", "96"}
F_NAMES = ["UF", "turno", "presidente", "governador", "secoes_pareadas_validas",
           "correlacao_bruta_pearson", "correlacao_dentro_municipio_zona",
           "grupos_com_variacao_interna", "grupo_geo", "nota"]


class Moments:
    __slots__ = ("n", "sx", "sy", "sxx", "syy", "sxy")

    def __init__(self):
        self.n = 0
        self.sx = self.sy = self.sxx = self.syy = self.sxy = 0.0

    def add(self, x, y):
        self.n += 1
        self.sx += x
        self.sy += y
        self.sxx += x * x
        self.syy += y * y
        self.sxy += x * y

    def centered(self):
        if self.n < 2:
            return 0.0, 0.0, 0.0
        return (self.sxy - self.sx * self.sy / self.n,
                self.sxx - self.sx * self.sx / self.n,
                self.syy - self.sy * self.sy / self.n)

    def values(self):
        return [self.n, self.sx, self.sy, self.sxx, self.syy, self.sxy]

    @classmethod
    def restore(cls, values):
        obj = cls()
        obj.n, obj.sx, obj.sy, obj.sxx, obj.syy, obj.sxy = values
        return obj


def pearson(tup):
    covariance, xx, yy = tup
    if xx <= 1e-12 or yy <= 1e-12:
        return None
    return max(-1.0, min(1.0, covariance / math.sqrt(xx * yy)))


def rows(path):
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter=";")
        needed = {"UF", "municipio", "zona", "secao", "turno",
                  "cargo", "votavel", "votos_BU"}
        if not needed.issubset(reader.fieldnames or []):
            raise RuntimeError("Cabecalho inesperado: " + str(path))
        for r in reader:
            yield r


def source(root):
    base = root / "analysis"
    national = json.loads((base / "reconciliacao_bu_secao.summary.json").read_text("utf-8"))
    found = []
    for summary in (base / "entre_cargos").glob("*/summary.json"):
        obj = json.loads(summary.read_text("utf-8"))
        if obj.get("status") == "concluido" and obj.get("source_fingerprint") == national["fingerprint"]:
            found.append((summary.parent, obj))
    if len(found) != 1:
        raise RuntimeError(f"Esperada exatamente uma matriz nacional: {len(found)}")
    folder, obj = found[0]
    state = json.loads((folder / "state.json").read_text("utf-8"))
    count = int(obj["partitions"])
    if len(state.get("completed", {})) != count:
        raise RuntimeError("Particoes de candidatos incompletas")
    paths = []
    for i in range(count):
        path = folder / "candidatos" / f"bucket-{i:04d}.csv"
        expected = state["completed"][str(i)]["candidate_sha256"]
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError("SHA-256 de candidatos diferente: " + str(path))
        paths.append(path)
    return folder, obj, paths


def choose_candidates(paths, turn="1", limit_governor=3):
    by_office = Counter()
    count = 0
    for path in paths:
        for r in rows(path):
            count += 1
            if r["turno"] != turn or r["cargo"] not in ("1", "3"):
                continue
            v = r["votavel"]
            if v in INVALID:
                continue
            n = int(r["votos_BU"])
            if n < 0:
                raise RuntimeError("Votos negativos em " + str(path))
            by_office[(r["UF"], r["cargo"], v)] += n
    nationals = Counter()
    for (uf, office, candidate), votes in by_office.items():
        if office == "1":
            nationals[candidate] += votes
    pres = [name for name, _ in nationals.most_common(2)]
    if len(pres) != 2:
        raise RuntimeError("Dois candidatos presidenciais nao encontrados")
    governors = defaultdict(Counter)
    for (uf, office, candidate), votes in by_office.items():
        if office == "3":
            governors[uf][candidate] += votes
    selected = {
        uf: [candidate for candidate, _ in counter.most_common(limit_governor)]
        for uf, counter in governors.items()
    }
    return pres, selected, count


def compute(paths, pres, governors, turn="1", progress=None):
    """Acumula momentos sem reunir todo o pais em memoria."""
    raw = defaultdict(Moments)
    within = defaultdict(lambda: defaultdict(Moments))
    paired = Counter()
    valid = Counter()
    for ix, path in enumerate(paths):
        current = None
        p_votes, g_votes = {}, {}
        p_den = g_den = 0

        def flush():
            if current is None:
                return
            uf, mu, zone, sec, t = current
            if t != turn or not p_votes or not g_votes:
                return
            paired[uf] += 1
            if p_den == 0 or g_den == 0 or uf not in governors:
                return
            valid[uf] += 1
            geo = (mu, zone)
            for p in pres:
                x = p_votes.get(p, 0) / p_den
                for g in governors[uf]:
                    y = g_votes.get(g, 0) / g_den
                    key = (uf, t, p, g)
                    raw[key].add(x, y)
                    within[key][geo].add(x, y)

        for r in rows(path):
            key = (r["UF"], r["municipio"], r["zona"],
                   r["secao"], r["turno"])
            if current != key:
                flush()
                current = key
                p_votes, g_votes = {}, {}
                p_den = g_den = 0
            if r["turno"] != turn or r["cargo"] not in ("1", "3"):
                continue
            office, candidate, n = r["cargo"], r["votavel"], int(r["votos_BU"])
            if n < 0:
                raise RuntimeError("Voto BU negativo em " + str(path))
            if office == "1":
                p_votes[candidate] = p_votes.get(candidate, 0) + n
                if candidate not in INVALID:
                    p_den += n
            elif office == "3":
                g_votes[candidate] = g_votes.get(candidate, 0) + n
                if candidate not in INVALID:
                    g_den += n
        flush()
        if progress:
            progress(ix + 1, len(paths))
    return raw, within, paired, valid


def output_rows(raw, within):
    results = []
    for key in sorted(raw):
        uf, turn, p, g = key
        m = raw[key]
        cxy = cyy = cxx = 0.0
        count = 0
        for local in within[key].values():
            if local.n < 2:
                continue
            a, b, c = local.centered()
            cxy += a
            cxx += b
            cyy += c
            count += 1
        base = pearson(m.centered())
        adjusted = pearson((cxy, cxx, cyy))
        results.append({
            "UF": uf, "turno": turn, "presidente": p, "governador": g,
            "secoes_pareadas_validas": m.n,
            "correlacao_bruta_pearson": round(base, 6) if base is not None else "",
            "correlacao_dentro_municipio_zona": round(adjusted, 6) if adjusted is not None else "",
            "grupos_com_variacao_interna": count,
            "grupo_geo": "municipio+zona",
            "nota": "Correlacao de secoes; nao representa votos individuais nem prova de fraude",
        })
    return results


def run(root, turn="1", top_governors=3):
    if top_governors < 1 or top_governors > 15:
        raise ValueError("--top-governors deve estar entre 1 e 15")
    folder, original, paths = source(root)
    print("CANDIDATOS ENTRE CARGOS: arquivos BU com SHA-256 validado")
    print("Particoes:", len(paths), "| fingerprint:", original["source_fingerprint"])
    pres, governors, count = choose_candidates(paths, turn, top_governors)
    if count != original["candidate_keys"]:
        raise RuntimeError(f"Chaves da origem diferentes: {count} != {original['candidate_keys']}")
    print("Top 2 presidenciais por votos validos:", pres)
    print("UFs com candidatos a Governador:", len(governors))
    raw, within, paired, valid = compute(paths, pres, governors, turn,
                                         progress=lambda i, n: print(
                                             f"[PARES {i}/{n}]", flush=True)
                                         if i in (1, 2, n) or i % 20 == 0 else None)
    table = output_rows(raw, within)
    directory = folder / "correlacao_presidente_governador"
    directory.mkdir(exist_ok=True)
    target = directory / "pares_por_uf.csv"
    temp = Path(str(target) + ".part")
    try:
        with temp.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, delimiter=";", fieldnames=F_NAMES,
                                    lineterminator="\n")
            writer.writeheader()
            writer.writerows(table)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, target)
    finally:
        if temp.exists():
            temp.unlink()
    report = {
        "version": VERSION, "status": "DESCRITIVO_CONCLUIDO",
        "fingerprint": original["source_fingerprint"], "turno": turn,
        "presidente_top2": pres,
        "governador_top_por_uf": governors,
        "candidate_keys_checked": count,
        "paired_sections_by_uf": dict(sorted(paired.items())),
        "valid_share_sections_by_uf": dict(sorted(valid.items())),
        "pairs_compared": len(table),
        "correlation_csv": str(target), "correlation_csv_sha256": sha256(target),
        "note": ("Pearson descritivo dos percentuais de votos validos por secao; "
                 "segundo coeficiente remove medias municipio+zona. "
                 "Nao e transferencia individual de votos nem classificacao "
                 "de direita/esquerda; nao demonstra fraude. "
                 "Interpretar com controles territoriais e informacao de candidatos.")
    }
    meta = directory / "summary.json"
    temporary = meta.with_suffix(".json.part")
    temporary.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")
    os.replace(temporary, meta)
    print("CORRELACAO ENTRE CARGOS CONCLUIDA")
    print(json.dumps({"pairs": len(table), "presidente_top2": pres,
                      "paired_sections": sum(paired.values()),
                      "valid_sections": sum(valid.values()),
                      "csv": str(target),
                      "sha256": report["correlation_csv_sha256"]},
                     ensure_ascii=False, indent=2), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", help="Diretorio de dados (padrao Windows H:)")
    parser.add_argument("--turn", default="1", choices=("1",),
                        help="Turno de governador disponivel: 1")
    parser.add_argument("--top-governors", type=int, default=3,
                        help="Quantos candidatos a governo por UF (1-15)")
    args = parser.parse_args()
    run(root_path(args.root), args.turn, args.top_governors)


if __name__ == "__main__":
    main()
