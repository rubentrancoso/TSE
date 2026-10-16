#!/usr/bin/env python3
"""Analise exploratoria de anomalias eleitorais por secao (dados oficiais BU CSV).

Nao produz veredictos de fraude nem substitui auditoria de cedulas originais.
Testes com pre-condicoes, numero de observacoes, fontes e limites documentados.
Somente biblioteca padrao Python; utiliza a tabela 'votes' do urnas.py.
"""
from __future__ import annotations
import collections
import csv
import json
import math
import os
import statistics
from datetime import datetime, timezone
from pathlib import Path

VERSION = "tse-electoral-forensics-v1"
INVALID_CODES = {"95", "96"}
MIN_DIGIT_N = 100
MIN_LOCAL_N = 30
MIN_SECTION_VOTES = 40


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def csv_writer(path, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(path.suffix + ".part")
    fd = part.open("w", encoding="utf-8-sig", newline="")
    writer = csv.DictWriter(fd, fieldnames=fields, delimiter=";", extrasaction="ignore")
    writer.writeheader()
    return fd, writer, part


def finish_csv(fd, part, final):
    fd.close()
    os.replace(part, final)


def first_digit(n):
    while n >= 10:
        n //= 10
    return n


def second_digit(n):
    while n >= 100:
        n //= 10
    return n % 10


def benford_expected(mode):
    if mode == "first":
        return {digit: math.log10(1 + 1 / digit) for digit in range(1, 10)}
    return {digit: sum(math.log10(1 + 1 / (10 * first + digit))
                       for first in range(1, 10)) for digit in range(10)}


def digit_diagnostic(values, mode, label, uf, turn, candidate):
    values = [int(x) for x in values if x is not None and
              (int(x) >= (1 if mode == "first" else 10))]
    n = len(values)
    expected = benford_expected(mode)
    counts = collections.Counter(
        first_digit(x) if mode == "first" else second_digit(x) for x in values)
    distinct = len(set(values))
    span = max(values) / min(values) if values else 0
    applicable = n >= MIN_DIGIT_N and span >= 10 and distinct >= 30
    statistic = sum((counts.get(d, 0) - n * p) ** 2 / (n * p)
                    for d, p in expected.items()) if n else None
    mad = sum(abs(counts.get(d, 0) / n - p)
              for d, p in expected.items()) / len(expected) if n else None
    return {
        "uf": uf, "turno": turn, "candidato": candidate,
        "teste": mode, "observacoes": n, "valores_distintos": distinct,
        "alcance_max_min": round(span, 5), "aplicabilidade": (
            "exploratorio" if applicable else "insuficiente"),
        "qui_quadrado_descritivo": round(statistic, 5) if applicable else "",
        "mad": round(mad, 7) if applicable else "",
        "contagens_0_a_9": json.dumps([counts.get(d, 0) for d in range(10)]),
        "esperado_0_a_9": json.dumps([round(expected.get(d, 0), 6)
                                      for d in range(10)]),
        "limite": "Benford nao possui garantia de adequacao a votos por secao; nenhum desvio prova fraude."
    }


def last_digit_diagnostic(values, uf, turn, candidate):
    pool = [int(x) for x in values if x is not None and int(x) >= 30]
    n = len(pool)
    counts = collections.Counter(x % 10 for x in pool)
    counts_list = [counts.get(x, 0) for x in range(10)]
    chi2 = sum((x - n / 10) ** 2 / (n / 10)
               for x in counts_list) if n else None
    return {"uf": uf, "turno": turn, "candidato": candidate, "observacoes": n,
            "aplicabilidade": "exploratorio" if n >= MIN_DIGIT_N else "insuficiente",
            "contagens_0_a_9": json.dumps(counts_list),
            "qui_quadrado_uniforme_descritivo": round(chi2, 5) if n >= MIN_DIGIT_N else "",
            "terminados_em_0_ou_5_pct": round(100 *
                (counts[0] + counts[5]) / n, 4) if n else "",
            "limite": "Uniformidade nao e distribuicao garantida em dados reais; efeito do tamanho das secoes."}


def correlation(points):
    # Formula numericamente estavel centrada nas medias; nao fornece causalidade.
    if len(points) < MIN_LOCAL_N:
        return None
    ax = [p[0] for p in points]
    ay = [p[1] for p in points]
    mx, my = statistics.fmean(ax), statistics.fmean(ay)
    sxy = sum((x - mx) * (y - my) for x, y in points)
    sxx = sum((x - mx) ** 2 for x in ax)
    syy = sum((y - my) ** 2 for y in ay)
    if sxx <= 0 or syy <= 0:
        return None
    return max(-1., min(1., sxy / math.sqrt(sxx * syy)))


def numeric(value):
    try:
        if value is None or str(value).strip() == "":
            return None
        return int(str(value))
    except (ValueError, TypeError):
        return None


def is_valid_candidate(votavel, payload):
    votavel = str(votavel or "").strip()
    if not votavel or votavel in INVALID_CODES:
        return False
    category = str(payload.get("DS_TIPO_VOTAVEL", "")).casefold()
    if "branco" in category or "nulo" in category:
        return False
    return True


def normal_section(value, key):
    if key not in value:
        return ""
    raw = str(value[key] or "").strip()
    try:
        return str(int(raw))
    except ValueError:
        return raw


def build_section(key, rows):
    uf, municipality, zone, section, turn = key
    candidates = collections.Counter()
    eligible = turnout = None
    received = None
    records = 0
    duplicate_candidates = collections.Counter()
    for candidate, votes, raw in rows:
        try:
            payload = json.loads(raw)
        except (ValueError, TypeError):
            payload = {}
        if eligible is None:
            eligible = numeric(payload.get("QT_APTOS"))
        if turnout is None:
            turnout = numeric(payload.get("QT_COMPARECIMENTO"))
        if received is None:
            received = payload.get("DT_BU_RECEBIDO") or None
        votes = numeric(votes)
        if votes is None:
            continue
        records += 1
        if is_valid_candidate(candidate, payload):
            candidates[str(candidate)] += votes
            duplicate_candidates[str(candidate)] += 1
    total = sum(candidates.values())
    return {
        "uf": uf, "municipio": normal_section({"m": municipality}, "m"),
        "zona": normal_section({"z": zone}, "z"),
        "secao": normal_section({"s": section}, "s"), "turno": turn,
        "candidatos": dict(candidates), "validos": total,
        "aptos": eligible, "comparecimento": turnout,
        "recebimento_bu": received,
        "linhas": records,
        "duplicacoes_candidato": {k: x for k, x in duplicate_candidates.items() if x > 1}
    }


def distribution_shape(values):
    """Assimetria e curtose EXPLORATORIAS; nenhuma suposicao de normalidade."""
    if len(values) < MIN_LOCAL_N:
        return None
    avg = statistics.fmean(values)
    moments2 = statistics.fmean([(v - avg) ** 2 for v in values])
    if moments2 < 1e-12:
        return None
    moments3 = statistics.fmean([(v - avg) ** 3 for v in values])
    moments4 = statistics.fmean([(v - avg) ** 4 for v in values])
    return moments3 / moments2 ** 1.5, moments4 / moments2 ** 2 - 3


def calculate_city(rows, writer_outliers, writer_correlations, writer_shape):
    if not rows:
        return 0
    totals = collections.Counter()
    for row in rows:
        totals.update(row["candidatos"])
    top = [x for x, _ in totals.most_common(2)]
    if not top:
        return 0
    base = rows[0]
    uf, turn, municipality = base["uf"], base["turno"], base["municipio"]
    out_count = 0
    for candidate in top:
        shares = []
        pairs = []
        for s in rows:
            if s["validos"] < MIN_SECTION_VOTES:
                continue
            share = s["candidatos"].get(candidate, 0) / s["validos"]
            shares.append((s, share))
            if s["aptos"] and s["comparecimento"] is not None and (
                    0 <= s["comparecimento"] <= s["aptos"]):
                pairs.append((s["comparecimento"] / s["aptos"], share))
        r = correlation(pairs)
        writer_correlations.writerow({
            "uf": uf, "municipio": municipality, "turno": turn,
            "candidato": candidate, "n_secoes_com_participacao": len(pairs),
            "correlacao_pearson": round(r, 6) if r is not None else "",
            "interpretacao": "descritivo, nao causal; demografia e geografia confundem relacoes"
        })
        shape = distribution_shape([p for _, p in shares])
        writer_shape.writerow({
            "uf": uf, "municipio": municipality, "turno": turn,
            "candidato": candidate, "secoes": len(shares),
            "assimetria": round(shape[0], 6) if shape else "",
            "curtose_excesso": round(shape[1], 6) if shape else "",
            "nota": "Distribuicoes eleitorais nao precisam seguir curva normal; resultado descritivo."
        })
        if len(shares) < MIN_LOCAL_N:
            continue
        median = statistics.median([p for _, p in shares])
        mad = statistics.median([abs(p - median) for _, p in shares])
        if mad < 0.015:
            continue  # MAD proximo de zero nao produz z robusto confiavel.
        scale = 1.4826 * mad
        local = []
        for section, share in shares:
            z = (share - median) / scale
            if abs(z) >= 5:
                local.append((abs(z), section, share, z))
        for _, section, share, z in sorted(local, reverse=True, key=lambda p: p[0])[:5]:
            writer_outliers.writerow({
                "uf": uf, "municipio": municipality, "zona": section["zona"],
                "secao": section["secao"], "turno": turn, "candidato": candidate,
                "votos_candidato": section["candidatos"].get(candidate, 0),
                "votos_validos": section["validos"],
                "participacao_candidato": round(share, 6),
                "mediana_municipal": round(median, 6), "mad_municipal": round(mad, 6),
                "desvio_robusto": round(z, 4), "n_secoes_referencia": len(shares),
                "nota": "anomalia exploratoria; contextos locais e secoes agregadas podem explicar"
            })
            out_count += 1
    return out_count


def analyze(db, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    paths = {
        "benford": output / "benford.csv",
        "digitos_finais": output / "digitos_finais.csv",
        "desvios_municipais": output / "desvios_municipais.csv",
        "participacao_correlacao": output / "participacao_correlacao.csv",
        "consistencia": output / "consistencia_por_secao.csv",
        "perfil_2d": output / "perfil_participacao_voto.csv",
        "forma_distribuicao": output / "forma_distribuicao_municipal.csv",
    }
    specs = {
        "benford": ["uf","turno","candidato","teste","observacoes","valores_distintos",
                    "alcance_max_min","aplicabilidade","qui_quadrado_descritivo","mad",
                    "contagens_0_a_9","esperado_0_a_9","limite"],
        "digitos_finais": ["uf","turno","candidato","observacoes","aplicabilidade",
                           "contagens_0_a_9","qui_quadrado_uniforme_descritivo",
                           "terminados_em_0_ou_5_pct","limite"],
        "desvios_municipais": ["uf","municipio","zona","secao","turno","candidato",
                              "votos_candidato","votos_validos","participacao_candidato",
                              "mediana_municipal","mad_municipal","desvio_robusto",
                              "n_secoes_referencia","nota"],
        "participacao_correlacao": ["uf","municipio","turno","candidato",
                                    "n_secoes_com_participacao","correlacao_pearson",
                                    "interpretacao"],
        "consistencia": ["uf","municipio","zona","secao","turno","aptos","comparecimento",
                         "validos","observacao"],
        "perfil_2d": ["uf","turno","candidato","bin_participacao",
                     "bin_votos","secoes"],
        "forma_distribuicao": ["uf","municipio","turno","candidato","secoes",
                               "assimetria","curtose_excesso","nota"],
    }
    handles, writers, parts = {}, {}, {}
    for name, columns in specs.items():
        handles[name], writers[name], parts[name] = csv_writer(paths[name], columns)
    total_sections = 0
    total_rows = 0
    flagged = 0
    detected_dup = 0
    cities = 0
    city_rows = []
    current_city = None
    state_rows = []
    current_state = None
    section_key = None
    section_records = []
    catalog_fingerprint = collections.Counter()
    unsupported = 0

    def finish_state(rows):
        if not rows:
            return
        state = rows[0]
        uf, turn = state["uf"], state["turno"]
        totals = collections.Counter()
        for row in rows:
            totals.update(row["candidatos"])
        for candidate, _ in totals.most_common(2):
            nums = [r["candidatos"].get(candidate, 0) for r in rows]
            for mode in ("first", "second"):
                writers["benford"].writerow(digit_diagnostic(
                    nums, mode, "n-secoes", uf, turn, candidate))
            writers["digitos_finais"].writerow(last_digit_diagnostic(nums, uf, turn, candidate))
            for (state_uf, state_turn, cand, x, y), count in catalog_fingerprint.items():
                if (state_uf, state_turn, cand) == (uf, turn, candidate):
                    writers["perfil_2d"].writerow({
                        "uf": uf, "turno": turn, "candidato": candidate,
                        "bin_participacao": x, "bin_votos": y, "secoes": count})
        # Correlacao municipal computada separadamente para evitar confusao estadual.

    def add_section(key, records):
        nonlocal total_sections, flagged, detected_dup, city_rows, current_city
        nonlocal state_rows, current_state, cities
        if not records:
            return
        section = build_section(key, records)
        total_sections += 1
        state_key = (section["uf"], section["turno"])
        city_key = (section["uf"], section["turno"], section["municipio"])
        if current_city is not None and current_city != city_key:
            flagged += calculate_city(city_rows, writers["desvios_municipais"],
                                      writers["participacao_correlacao"], writers["forma_distribuicao"])
            city_rows = []
            cities += 1
        if current_state is not None and current_state != state_key:
            finish_state(state_rows)
            state_rows = []
            catalog_fingerprint.clear()
        current_city, current_state = city_key, state_key
        city_rows.append(section)
        state_rows.append(section)
        values = section["candidatos"]
        if section["duplicacoes_candidato"]:
            detected_dup += 1
            writers["consistencia"].writerow({**section,
                                              "observacao": "MESMO_CANDIDATO_DUPLICADO"})
        if section["aptos"] is not None and section["comparecimento"] is not None and (
                section["comparecimento"] > section["aptos"] or section["comparecimento"] < 0):
            writers["consistencia"].writerow({**section, "observacao": "COMPARECIMENTO_INVALIDO"})
        if section["comparecimento"] is not None and section["validos"] > section["comparecimento"]:
            writers["consistencia"].writerow({**section, "observacao": "VALIDOS_ACIMA_COMPARECIMENTO"})
        if section["aptos"] and section["comparecimento"] is not None and (
                0 <= section["comparecimento"] <= section["aptos"]) and section["validos"] > 0:
            x = min(9, int(10 * section["comparecimento"] / section["aptos"]))
            for cand, votes in values.items():
                y = min(9, int(10 * votes / section["validos"]))
                catalog_fingerprint[(section["uf"], section["turno"], cand, x, y)] += 1

    try:
        cursor = db.execute("""
            SELECT uf,municipio,zona,secao,turno,votavel,votos,dados_json
            FROM votes
            WHERE source_kind = 'bu' AND (cargo = '1' OR LOWER(cargo) = 'presidente')
            ORDER BY uf,turno,municipio,zona,secao,votavel
        """)
        for uf, mu, zo, se, turn, candidate, vote, raw in cursor:
            total_rows += 1
            key = (uf, mu, zo, se, turn)
            if None in key or not str(se).strip():
                unsupported += 1
                continue
            if section_key is None:
                section_key = key
            if key != section_key:
                add_section(section_key, section_records)
                section_records = []
                section_key = key
            section_records.append((candidate, vote, raw))
        if section_records and section_key:
            add_section(section_key, section_records)
        if city_rows:
            flagged += calculate_city(city_rows, writers["desvios_municipais"],
                                      writers["participacao_correlacao"], writers["forma_distribuicao"])
            cities += 1
        if state_rows:
            finish_state(state_rows)
    finally:
        for name in paths:
            finish_csv(handles[name], parts[name], paths[name])
    result = {
        "version": VERSION, "produzido_em_utc": timestamp(),
        "fonte": "CSV oficial do Boletim de Urna importado na tabela votes, source_kind=bu, cargo Presidente",
        "linhas_processadas": total_rows, "secoes": total_sections, "municipios_grupos": cities,
        "desvios_locais_sinalizados": flagged, "secoes_com_candidato_duplicado": detected_dup,
        "registros_sem_identificador_secao": unsupported,
        "status": "analise_concluida" if total_sections else "SEM_DADOS_BU_PRESIDENTE",
        "arquivos": {k: str(v) for k, v in paths.items()},
        "metodos": ["Benford primeiro/segundo digitos (diagnostico)",
                    "Qui quadrado descritivo dos digitos finais",
                    "Mediana/MAD local (escore robusto, limiar 5)",
                    "Correlacao Pearson participacao x apoio por municipio",
                    "Mapa 10x10 participacao x apoio",
                    "Assimetria e curtose por municipio (forma da distribuicao)",
                    "Consistencia de totais e registros duplicados"],
        "limites": [
            "Nao e um detector de fraude nem um teste causal; ocorrencias exigem investigacao documental.",
            "Benford e digitos finais podem ser inadequados para contagens pequenas ou com faixa restrita.",
            "Resultados por municipio sao afetados por heterogeneidade demografica e contexto geografico.",
            "Sem comparacao com cedulas verificaveis independentemente, nao e auditoria de limite de risco.",
            "Nao usa RDV/log binarios; dependera de um decodificador e dados temporais confiaveis.",
            "Usa somente cargos Presidente; extensao aos demais cargos depende de tratamento de votos de legenda.",
            "Se houver multiplos arquivos com mesmo BU, checar as duplicacoes antes de confiar nas frequencias.",
            "Nenhum p-valor ou taxa de falso positivo foi calibrado; niveis de anomalia sao exploratorios."
        ]
    }
    tmp = output / "estatistica_resumo.json.tmp"
    tmp.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, output / "estatistica_resumo.json")
    print("ESTATISTICA FORENSE: secoes={:,}, desvios_locais={}, duplicadas={}.".format(
        total_sections, flagged, detected_dup), flush=True)
    return result
