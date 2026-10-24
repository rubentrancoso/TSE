#!/usr/bin/env python3
"""Revisao dos 18 limites Presidente x Senado, sem reler os BU.

Confere fingerprints, SHA-256, correspondencia CSV/JSON, as duas escolhas
presidenciais por senador e identidades dos limites; gera a tabela
comparativa com percentuais. Nao infere voto individual ou fraude.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path

from reconcile_stream import sha256
from urnas import root_path

VERSION = "audit-senate-ecological-bounds-v1"
PRESIDENTS = {"13", "22"}
FIELDS = (
    "UF", "senador", "nome_urna", "partido", "votos_senador",
    "minimo_com_13", "pct_minimo_com_13",
    "minimo_com_22", "pct_minimo_com_22",
    "minimo_fora_13", "pct_minimo_fora_13",
    "minimo_fora_22", "pct_minimo_fora_22",
    "maximo_com_13", "maximo_com_22",
    "secoes_13", "secoes_22",
    "tipo_analise",
)


def nonnegative(value, label):
    text = str(value).strip()
    if not text.isdecimal():
        raise RuntimeError(f"Contagem invalida em {label}: {value!r}")
    return int(text)


def pct(n, total):
    return round(100.0 * n / total, 4) if total else None


def audit_rows(path, metadata):
    if sha256(path) != metadata.get("csv_sha256"):
        raise RuntimeError("SHA-256 do CSV dos 18 limites nao confere")
    expected = {}
    for item in metadata.get("por_candidato", []):
        k = (item["UF"], str(item["senador"]), str(item["presidente"]))
        if k in expected:
            raise RuntimeError("Par duplicado no JSON: " + repr(k))
        expected[k] = item
    if len(expected) != metadata.get("pares_presidencia_senado"):
        raise RuntimeError("Resumo dos limites tem cardinalidade inconsistente")
    fields_needed = {
        "UF", "senador", "nome_urna", "partido", "presidente",
        "secoes_validas", "votos_senador",
        "votos_presidenciais_do_candidato", "comparecimento_presidencial",
        "eleitorado_senado_naquelas_secoes", "sobreposicao_minima",
        "sobreposicao_maxima", "senador_fora_do_presidente_minimo",
        "pct_minima_dos_votos_senador", "pct_maxima_dos_votos_senador",
    }
    by_candidate = {}
    seen = set()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        if not fields_needed.issubset(reader.fieldnames or []):
            raise RuntimeError("Colunas do CSV incompletas")
        for item in reader:
            key = (item["UF"], item["senador"], item["presidente"])
            if key not in expected or key in seen:
                raise RuntimeError("Par inesperado ou repetido: " + repr(key))
            seen.add(key)
            for col in fields_needed:
                json_value = str(expected[key][col])
                if item[col] != json_value:
                    raise RuntimeError(f"CSV/JSON diferem: {key}, {col}")
            if item["presidente"] not in PRESIDENTS:
                raise RuntimeError("Presidenciavel fora da selecao")
            n = nonnegative(item["votos_senador"], "votos_senador")
            p = nonnegative(item["votos_presidenciais_do_candidato"], "votos_presidenciais_do_candidato")
            universe = nonnegative(item["comparecimento_presidencial"], "comparecimento_presidencial")
            s_eligible = nonnegative(item["eleitorado_senado_naquelas_secoes"], "eleitorado_senado_naquelas_secoes")
            low = nonnegative(item["sobreposicao_minima"], "sobreposicao_minima")
            high = nonnegative(item["sobreposicao_maxima"], "sobreposicao_maxima")
            not_p = nonnegative(item["senador_fora_do_presidente_minimo"],
                                "senador_fora_do_presidente_minimo")
            section_count = nonnegative(item["secoes_validas"], "secoes_validas")
            if (not 0 <= low <= high <= n <= s_eligible <= universe or
                    high > p or not_p != n-high or section_count == 0):
                raise RuntimeError("Limites inconsistentes: " + repr(key))
            # Limites agregados por secao sao mais fortes que bounds globais:
            # low >= max(0, P+S-N) e high <= min(P,S).
            if low < max(0, p+n-universe) or high > min(p,n):
                raise RuntimeError("Bounds agregados contradizem margens: " + repr(key))
            try:
                recorded_lo = float(item["pct_minima_dos_votos_senador"])
                recorded_hi = float(item["pct_maxima_dos_votos_senador"])
            except ValueError as exc:
                raise RuntimeError("Percentuais originais invalidos") from exc
            if (abs(recorded_lo - pct(low,n)) > 0.00011 or
                    abs(recorded_hi - pct(high,n)) > 0.00011):
                raise RuntimeError("Percentuais originais inconsistentes")
            ckey = key[:2]
            col = by_candidate.setdefault(ckey, {})
            if "info" not in col:
                col["info"] = {
                    "UF": item["UF"], "senador": item["senador"],
                    "nome_urna": item["nome_urna"], "partido": item["partido"],
                    "votos_senador": n,
                    "eleitorado_senado_naquelas_secoes": s_eligible,
                }
            if (n != col["info"]["votos_senador"] or
                    s_eligible != col["info"]["eleitorado_senado_naquelas_secoes"] or
                    col["info"]["nome_urna"] != item["nome_urna"] or
                    col["info"]["partido"] != item["partido"] or
                    item["presidente"] in col):
                raise RuntimeError("Inconsistencia por candidato: " + repr(ckey))
            col[item["presidente"]] = {
                "min": low, "max": high, "not": not_p,
                "secoes": section_count,
            }
    if seen != set(expected):
        raise RuntimeError("Faltam pares no CSV de limites")
    if len(by_candidate) != metadata.get("candidatos_distintos"):
        raise RuntimeError("Quantidade de senadores nao fecha")
    out = []
    for key, bundle in sorted(by_candidate.items()):
        if set(bundle) != {"info", "13", "22"}:
            raise RuntimeError("Faltou comparacao presidencial: " + repr(key))
        obj = bundle["info"]
        n = obj["votos_senador"]
        row = {
            "UF": obj["UF"], "senador": obj["senador"],
            "nome_urna": obj["nome_urna"], "partido": obj["partido"],
            "votos_senador": n,
            "minimo_com_13": bundle["13"]["min"],
            "pct_minimo_com_13": pct(bundle["13"]["min"], n),
            "minimo_com_22": bundle["22"]["min"],
            "pct_minimo_com_22": pct(bundle["22"]["min"], n),
            "minimo_fora_13": bundle["13"]["not"],
            "pct_minimo_fora_13": pct(bundle["13"]["not"], n),
            "minimo_fora_22": bundle["22"]["not"],
            "pct_minimo_fora_22": pct(bundle["22"]["not"], n),
            "maximo_com_13": bundle["13"]["max"],
            "maximo_com_22": bundle["22"]["max"],
            "secoes_13": bundle["13"]["secoes"],
            "secoes_22": bundle["22"]["secoes"],
            "tipo_analise": "Limite matematico por secao; nao transferencia observada",
        }
        out.append(row)
    return out


def write_csv(path, rows):
    tmp = Path(str(path) + ".part")
    try:
        with tmp.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS, delimiter=";",
                               lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def run(root, docs_path=None):
    analysis = root / "analysis"
    national = json.loads(
        (analysis / "reconciliacao_bu_secao.summary.json").read_text("utf-8"))
    fp = national["fingerprint"]
    matches = []
    for path in (analysis / "entre_cargos").glob(
            "*/limites_presidencia_senado_inversoes/summary.json"):
        data = json.loads(path.read_text("utf-8"))
        if (data.get("source_fingerprint") == fp and
                data.get("status") == "LIMITES_CALCULADOS"):
            matches.append((path, data))
    if len(matches) != 1:
        raise RuntimeError(f"Esperado um unico resumo de limites: {len(matches)}")
    summary_path, metadata = matches[0]
    folder = summary_path.parent
    source_path = Path(metadata["csv"])
    map_file = (Path(docs_path) if docs_path else
                Path(__file__).resolve().parent /
                "docs/CANDIDATOS_SENADO_INVERSOES_2026.csv")
    if (sha256(map_file) != metadata["candidate_mapping_sha256"] or
            sha256(folder.parent / "diagnostico_conjunto" /
                   "revisao_inversoes" / "summary.json")
            != metadata["review_summary_sha256"]):
        raise RuntimeError("Fonte de mapeamento ou revisao original foi alterada")
    records = audit_rows(source_path, metadata)
    target = folder / "analise_limites"
    target.mkdir(exist_ok=True)
    csv_output = target / "resumo_cruzamento.csv"
    write_csv(csv_output, records)
    result = {
        "version": VERSION,
        "status": "RESUMO_DE_LIMITES_CONCLUIDO",
        "source_fingerprint": fp,
        "source_sha256": metadata["csv_sha256"],
        "mapping_sha256": metadata["candidate_mapping_sha256"],
        "numero_senadores": len(records),
        "numero_pares": len(records)*2,
        "ranking_minimo_com_13": [
            {"UF": r["UF"], "nome": r["nome_urna"],
             "min": r["minimo_com_13"],
             "pct": r["pct_minimo_com_13"]}
            for r in sorted(records, key=lambda r: r["minimo_com_13"],
                            reverse=True)],
        "ranking_minimo_fora_22": [
            {"UF": r["UF"], "nome": r["nome_urna"],
             "min": r["minimo_fora_22"],
             "pct": r["pct_minimo_fora_22"]}
            for r in sorted(records, key=lambda r: r["minimo_fora_22"],
                            reverse=True)],
        "output": str(csv_output), "output_sha256": sha256(csv_output),
        "limitations": [
            "Apenas 9 candidaturas selecionadas por inversao de correlacao: amostra nao representativa",
            "Somas de limites de senadores diferentes nao representam eleitores unicos",
            "Comparacao 13/22 nao equivale a comparar automaticamente blocos ideologicos",
            "Limites inferiores demonstram sobreposicao necessaria, nao taxa real de voto cruzado",
            "Para Senado houve duas escolhas, mas uma mesma candidatura representa no maximo uma pessoa",
            "Estatistica descritiva nao demonstra fraude nem adulteracao da transmissao",
        ],
    }
    target_json = target / "summary.json"
    tmp = Path(str(target_json) + ".part")
    try:
        tmp.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n",
                       encoding="utf-8")
        os.replace(tmp, target_json)
    finally:
        if tmp.exists():
            tmp.unlink()
    print("AUDITORIA RESUMIDA DE LIMITES CONCLUIDA")
    print(json.dumps({
        "senadores": len(records), "pares": len(records)*2,
        "minimo_com_13_maiores_5": result["ranking_minimo_com_13"][:5],
        "minimo_fora_22_maiores_5": result["ranking_minimo_fora_22"][:5],
        "csv": str(csv_output), "sha256": result["output_sha256"]
    }, ensure_ascii=False, indent=2), flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", help="Diretorio do acervo de dados")
    parser.add_argument("--mapping", help="CSV de nomes oficiais alternativo")
    args = parser.parse_args()
    run(root_path(args.root), args.mapping)
