#!/usr/bin/env python3
"""Fase 5Q (menu V): secoes tardias dentro de municipio/zona no 1T 2026.

Le apenas CSV BWEB H + NR28 M com SHA; treina em BUs recebidos antes
de 20:04:39 BRT; testa os recebidos depois. Nao baixa, abre ZIP ou SQLite.
Cronologia BWEB nao equivale a publicacao EA20.
"""
from __future__ import annotations
from collections import defaultdict
import argparse
import csv
import json
import math
from pathlib import Path

from analyze_operational_curve_2026 import BASE, CUT, atomic_csv, atomic_json, load_sources
from analyze_bweb_seconds_2026 import parse_original_second
from extract_bweb_received_2026 import UFs, norm
from correct_bweb_28_periodicity_2026 import VERSION as M_VERSION
from reconcile_stream import sha256
from urnas import root_path

VERSION = "phase5q-within-zone-holdout-2026-v1"
PRIOR_MUN = 1000
PRIOR_ZONE = 1000
MIN_POST_MINUTE = 5000
MIN_PAIRED_SIDE = 1000
MODELS = ("BR_pre", "UF_pre", "MUNICIPIO_pre", "ZONA_pre", "ZONA_final_IN_SAMPLE")
ZONE_COLS = ("UF", "municipio", "zona", "pre_valid", "pre_lula", "post_valid",
             "post_lula", "post_flavio", "pre_lula_pct", "post_lula_pct",
             "delta_post_minus_pre_pp", "municipio_pre_pred_lula_pct",
             "zone_pre_pred_lula_pct", "municipio_residual_lula_votes",
             "zone_residual_lula_votes", "classification")
MUN_COLS = ("UF", "municipio", "pre_valid", "post_valid", "post_lula",
            "observed_post_lula_pct", "mun_pre_pred_lula_pct",
            "zone_pre_pred_lula_pct", "mun_residual_lula_votes",
            "zone_residual_lula_votes", "unseen_zone_valid")
MIN_COLS = ("brt_minute", "post_valid", "post_lula", "post_flavio",
            "real_post_lula_pct", "br_pre_lula_pct", "uf_pre_lula_pct",
            "mun_pre_lula_pct", "zone_pre_lula_pct", "zone_final_lula_pct",
            "mun_residual_lula_pp", "zone_residual_lula_pp",
            "cum_post_valid", "cum_actual_lula_pct", "cum_mun_pre_lula_pct",
            "cum_zone_pre_lula_pct")


def pct(v, total):
    return 100 * v / total if total else None


def read_zone_votes(folder, manifest, corrected, ufs=UFs):
    """Uma unica varredura SHA-validada sobre os shards H e M."""
    zone = defaultdict(lambda: [0] * 6)
    minutes = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    totals = [0, 0, 0, 0]
    hashes = {}
    for uf in ufs:
        shard = folder / f"received-{uf}.csv"
        nrfile = folder / f"phase5h_nr28_sections_{uf}.csv"
        nrmeta = folder / f"phase5h_nr28_sections_{uf}.json"
        info = manifest["ufs"][uf]
        trusted = corrected["checkpoint_sources"][uf]
        if not shard.is_file() or sha256(shard) != info["shard_sha256"]:
            raise RuntimeError("BWEB sem SHA valido: " + uf)
        if not nrfile.is_file() or not nrmeta.is_file():
            raise RuntimeError("NR28 indisponivel: " + uf)
        meta = json.loads(nrmeta.read_text(encoding="utf-8"))
        digest = sha256(nrfile)
        if (meta.get("version") != M_VERSION or digest != meta["csv_sha256"]
            or digest != trusted["csv_sha256"]
            or meta["archive_sha256"] != info["source_sha256"]):
            raise RuntimeError("Manifesto/correcao NR28 divergente: " + uf)
        nr28 = {}
        with nrfile.open(newline="", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f, delimiter=";"):
                key = tuple(norm(r[k]) for k in ("municipio", "zona", "secao"))
                if key in nr28:
                    raise RuntimeError("NR28 duplicado: " + uf + " " + str(key))
                nr28[key] = int(r["votos_28"])
        if sum(nr28.values()) != meta["votes_28"]:
            raise RuntimeError("NR28 nao reconcilia na UF " + uf)
        count = 0
        seen = set()
        with shard.open(newline="", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f, delimiter=";"):
                if r["UF"] != uf or norm(r["turno"]) != "1":
                    raise RuntimeError("UF/turno incorretos: " + uf)
                m, z, sec = [norm(r[k]) for k in ("municipio", "zona", "secao")]
                skey = (m, z, sec)
                if skey in seen:
                    raise RuntimeError("Secao repetida: " + str((uf, *skey)))
                seen.add(skey)
                n28 = nr28.pop(skey, 0)
                v = int(r["votos_pres_validos"]) - n28
                lula = int(r["votos_13"])
                flavio = int(r["votos_22"])
                if min(v, lula, flavio) < 0 or lula + flavio > v:
                    raise RuntimeError("Contagens incoerentes na secao " + str((uf, *skey)))
                second, precise = parse_original_second(r["DT_BU_RECEBIDO"])
                if not precise or second[:16] != r["recebimento_minuto"]:
                    raise RuntimeError("Segundo nao certificado: " + str((uf, *skey)))
                start = 0 if second < CUT else 3
                key = (uf, m, z)
                target = zone[key]
                for j, x in enumerate((v, lula, flavio)):
                    target[start+j] += x
                if start == 3 and v:
                    current = minutes[r["recebimento_minuto"]][key]
                    for j, x in enumerate((v, lula, flavio)):
                        current[j] += x
                for i, x in enumerate((1, v, lula, flavio)):
                    totals[i] += x
                count += 1
        if nr28:
            raise RuntimeError("NR28 sem secao correspondente: " + uf)
        if count != info["sections"]:
            raise RuntimeError("Contagem de secoes difere do manifesto: " + uf)
        hashes[uf] = {"BWEB_SHA256": info["shard_sha256"], "NR28_SHA256": digest}
        print(f"[UF {uf}] {count:,} secoes, hashes validados", flush=True)
    return zone, minutes, totals, hashes


def evaluate(zone, minutes, prior_mun=PRIOR_MUN, prior_zone=PRIOR_ZONE):
    """Projecoes sem vazamento, exceto modelo rotulado IN_SAMPLE."""
    if min(prior_mun, prior_zone) <= 0:
        raise ValueError("Priors devem ser positivos")
    mun = defaultdict(lambda: [0] * 6)
    uf = defaultdict(lambda: [0] * 6)
    br = [0] * 6
    for (u, m, z), a in zone.items():
        for dest in (mun[(u, m)], uf[u], br):
            for i in range(6):
                dest[i] += a[i]
    if br[0] <= 0 or br[3] <= 0:
        raise ValueError("Sem votos antes/depois do corte")
    base_rate = (br[1]/br[0], br[2]/br[0])
    uf_rate = {u: ((v[1]/v[0], v[2]/v[0]) if v[0] else base_rate)
               for u, v in uf.items()}
    mu_rate = {}
    for key, a in mun.items():
        p = uf_rate[key[0]]
        mu_rate[key] = tuple((a[i]+prior_mun*p[i-1]) / (a[0]+prior_mun)
                             for i in (1, 2))
    rates = {}
    for key, a in zone.items():
        parent = mu_rate[key[:2]]
        zone_pre = tuple((a[i]+prior_zone*parent[i-1]) / (a[0]+prior_zone)
                         for i in (1, 2))
        all_v = a[0]+a[3]
        oracle = ((a[1]+a[4])/all_v, (a[2]+a[5])/all_v) if all_v else parent
        rates[key] = {"BR_pre": base_rate, "UF_pre": uf_rate[key[0]],
                      "MUNICIPIO_pre": parent, "ZONA_pre": zone_pre,
                      "ZONA_final_IN_SAMPLE": oracle}

    pred_counts = {model: [0., 0.] for model in MODELS}
    minute_scores = {name: [0., 0., 0, 0] for name in MODELS}
    minute_rows = []
    actual_cum = [0, 0, 0]
    pred_cum = {"MUNICIPIO_pre": 0., "ZONA_pre": 0.}
    for when in sorted(minutes):
        batch = [0, 0, 0]
        expected = {name: [0., 0.] for name in MODELS}
        for key, values in minutes[when].items():
            for i, x in enumerate(values):
                batch[i] += x
            for model in MODELS:
                for i in range(2):
                    expected[model][i] += values[0] * rates[key][model][i]
        if not batch[0]:
            continue
        for i, x in enumerate(batch):
            actual_cum[i] += x
        for model in MODELS:
            for i in range(2):
                pred_counts[model][i] += expected[model][i]
            if batch[0] >= MIN_POST_MINUTE:
                err = 100 * (expected[model][0]-batch[1]) / batch[0]
                w = minute_scores[model]
                w[0] += batch[0]*abs(err)
                w[1] += batch[0]*err*err
                w[2] += batch[0]
                w[3] += 1
        for model in pred_cum:
            pred_cum[model] += expected[model][0]
        minute_rows.append(dict(
            brt_minute=when, post_valid=batch[0], post_lula=batch[1], post_flavio=batch[2],
            real_post_lula_pct=pct(batch[1], batch[0]),
            br_pre_lula_pct=pct(expected["BR_pre"][0], batch[0]),
            uf_pre_lula_pct=pct(expected["UF_pre"][0], batch[0]),
            mun_pre_lula_pct=pct(expected["MUNICIPIO_pre"][0], batch[0]),
            zone_pre_lula_pct=pct(expected["ZONA_pre"][0], batch[0]),
            zone_final_lula_pct=pct(expected["ZONA_final_IN_SAMPLE"][0], batch[0]),
            mun_residual_lula_pp=100*(batch[1]-expected["MUNICIPIO_pre"][0])/batch[0],
            zone_residual_lula_pp=100*(batch[1]-expected["ZONA_pre"][0])/batch[0],
            cum_post_valid=actual_cum[0],
            cum_actual_lula_pct=pct(actual_cum[1], actual_cum[0]),
            cum_mun_pre_lula_pct=pct(pred_cum["MUNICIPIO_pre"], actual_cum[0]),
            cum_zone_pre_lula_pct=pct(pred_cum["ZONA_pre"], actual_cum[0]),
        ))
    if actual_cum != br[3:]:
        raise RuntimeError("Soma por minuto nao confere com post por zona")

    summaries = {}
    for model in MODELS:
        p_l, p_f = pred_counts[model]
        mae, sq, weight, points = minute_scores[model]
        summaries[model] = dict(
            pred_lula_pct=pct(p_l, br[3]),
            pred_flavio_pct=pct(p_f, br[3]),
            actual_lula_pct=pct(br[4], br[3]),
            actual_flavio_pct=pct(br[5], br[3]),
            lula_final_error_pp=pct(p_l-br[4], br[3]),
            flavio_final_error_pp=pct(p_f-br[5], br[3]),
            weighted_minute_mae_lula_pp=mae/weight if weight else None,
            weighted_minute_rmse_lula_pp=math.sqrt(sq/weight) if weight else None,
            minute_bins_ge_5000_valids=points,
            minute_valids_evaluated=int(weight),
        )

    categories = defaultdict(lambda: {"zones":0, "post_valid":0, "post_lula":0,
                                      "municipio_pred_lula":0., "zone_pred_lula":0.})
    zone_rows = []
    mun_detail = defaultdict(lambda: [0, 0, 0., 0., 0])
    for key, a in sorted(zone.items()):
        u, m, z = key
        if a[3] <= 0:
            continue
        category = ("MUNICIPIO_SEM_PRE" if mun[(u,m)][0] == 0 else
                    "ZONA_SEM_PRE" if a[0] == 0 else "MESMA_ZONA_COM_PRE")
        pmun = a[3]*rates[key]["MUNICIPIO_pre"][0]
        pzone = a[3]*rates[key]["ZONA_pre"][0]
        group = categories[category]
        group["zones"] += 1
        group["post_valid"] += a[3]
        group["post_lula"] += a[4]
        group["municipio_pred_lula"] += pmun
        group["zone_pred_lula"] += pzone
        md = mun_detail[(u,m)]
        md[0] += a[3]
        md[1] += a[4]
        md[2] += pmun
        md[3] += pzone
        if a[0] == 0:
            md[4] += a[3]
        zone_rows.append(dict(
            UF=u, municipio=m, zona=z, pre_valid=a[0], pre_lula=a[1],
            post_valid=a[3], post_lula=a[4], post_flavio=a[5],
            pre_lula_pct=pct(a[1],a[0]), post_lula_pct=pct(a[4],a[3]),
            delta_post_minus_pre_pp=(pct(a[4],a[3])-pct(a[1],a[0]) if a[0] else None),
            municipio_pre_pred_lula_pct=100*rates[key]["MUNICIPIO_pre"][0],
            zone_pre_pred_lula_pct=100*rates[key]["ZONA_pre"][0],
            municipio_residual_lula_votes=a[4]-pmun,
            zone_residual_lula_votes=a[4]-pzone,
            classification=category,
        ))
    municipal_rows = []
    for (u,m), counts in sorted(mun_detail.items()):
        valid, observed, pm, pz, unseen = counts
        municipal_rows.append(dict(UF=u, municipio=m, pre_valid=mun[(u,m)][0],
            post_valid=valid, post_lula=observed,
            observed_post_lula_pct=pct(observed, valid),
            mun_pre_pred_lula_pct=pct(pm,valid), zone_pre_pred_lula_pct=pct(pz,valid),
            mun_residual_lula_votes=observed-pm,
            zone_residual_lula_votes=observed-pz, unseen_zone_valid=unseen))
    summary_categories = {}
    for name, v in sorted(categories.items()):
        n = v["post_valid"]
        summary_categories[name] = dict(**v,
            post_lula_pct=pct(v["post_lula"],n),
            municipal_gap_votes=v["post_lula"]-v["municipio_pred_lula"],
            zone_gap_votes=v["post_lula"]-v["zone_pred_lula"],
            vote_fraction_of_tail=n/br[3])
    eligible = [r for r in zone_rows
                if r["pre_valid"] >= MIN_PAIRED_SIDE and r["post_valid"] >= MIN_PAIRED_SIDE]
    paired_v = sum(r["post_valid"] for r in eligible)
    paired_delta = (sum(r["post_valid"]*r["delta_post_minus_pre_pp"] for r in eligible)/paired_v
                    if paired_v else None)
    ranking = sorted(municipal_rows, key=lambda r: -abs(r["mun_residual_lula_votes"]))[:30]
    summary = dict(
        version=VERSION, cutoff="2026-10-04 20:04:39 BRT", year=2026, round=1,
        status="ZONA_PRE_CORTE_TESTADA_NA_CAUDA_BWEB_2026",
        valid_pre=br[0], lula_pre=br[1], flavio_pre=br[2],
        valid_post=br[3], lula_post=br[4], flavio_post=br[5],
        prior_municipality_votes=prior_mun, prior_zone_votes=prior_zone,
        min_paired_side_valid=MIN_PAIRED_SIDE,
        forecast_models=summaries, categories=summary_categories,
        paired_zones_with_1000_pre_and_post=len(eligible),
        paired_zones_post_valid=paired_v,
        paired_zones_weighted_delta_post_minus_pre_lula_pp=paired_delta,
        top_municipality_residuals=ranking,
        limits=[
            "Recebimento BWEB nao equivale a publicacao EA20",
            "Zona final IN SAMPLE usa votos futuros e e oraculo circular",
            "Sem ordem de urnas com timestamps coincidentes; corte por segundos exatos",
            "Pre e post na mesma zona nao sao amostras aleatorias de eleitores",
            "Desvios preditivos nao comprovam alteracao de votos",
            "Sem segundo turno, 2022, downloads, ZIP ou SQLite",
        ])
    return minute_rows, municipal_rows, zone_rows, summary


def run(root):
    base = root / BASE
    h, m, sha_h, sha_m = load_sources(base)
    zone, minutes, totals, hashes = read_zone_votes(base, h, m)
    if totals != [499206,119300788,53879538,56104503]:
        raise RuntimeError("Totais corrigidos discordam do nacional certificado")
    tfile = base / "phase5p_holdout_geographic_curve_2026_summary.json"
    if not tfile.is_file():
        raise RuntimeError("Execute T antes de V")
    t = json.loads(tfile.read_text(encoding="utf-8"))
    if t.get("status") != "PREVISAO_BWEB_FORA_DA_AMOSTRA_1T_2026":
        raise RuntimeError("Fase T com status incompatível")
    minutes_out, municipalities, zones, result = evaluate(zone, minutes)
    data = t["data"]
    if (result["valid_pre"] != data["training_pre_cut_valid"]
        or result["valid_post"] != data["holdout_post_cut_valid"]
        or result["lula_post"] != data["holdout_post_cut_lula"]
        or result["flavio_post"] != data["holdout_post_cut_flavio"]):
        raise RuntimeError("V: contagens de corte divergem da fase T")
    for model in ("BR_pre", "UF_pre", "MUNICIPIO_pre"):
        v = result["forecast_models"][model]
        old = data["forecast_models"][model]
        for field in ("pred_lula_pct", "pred_flavio_pct",
                      "weighted_minute_rmse_lula_pp", "lula_final_error_pp"):
            if not math.isclose(v[field], old[field], abs_tol=0.000001):
                raise RuntimeError("V difere de T: " + model + "/" + field)
    files = {
        "minutes": ("phase5q_zone_holdout_minutes_2026.csv",MIN_COLS,minutes_out),
        "municipalities": ("phase5q_zone_holdout_municipalities_2026.csv",MUN_COLS,municipalities),
        "zones": ("phase5q_zone_holdout_zones_2026.csv",ZONE_COLS,zones),
    }
    result["output_files"] = {}
    for label, (name, cols, rows) in files.items():
        path = base / name
        atomic_csv(path, cols, rows)
        result["output_files"][label] = {"path": str(path), "sha256":sha256(path), "rows":len(rows)}
    result["source_sha256"] = {"H_summary":sha_h,"M_summary":sha_m,"H_M_per_UF":hashes}
    output = base / "phase5q_zone_holdout_2026_summary.json"
    atomic_json(output, result)
    print(json.dumps({
        "status":result["status"],
        "model_errors":{name:{"lula_final_error_pp":v["lula_final_error_pp"],
                              "weighted_minute_rmse_lula_pp":v["weighted_minute_rmse_lula_pp"]}
                        for name,v in result["forecast_models"].items()},
        "categories":result["categories"],
        "paired_zones":result["paired_zones_with_1000_pre_and_post"],
        "paired_weighted_lula_shift_pp":result["paired_zones_weighted_delta_post_minus_pre_lula_pp"],
        "largest_municipal_residuals":result["top_municipality_residuals"][:6],
        "report":str(output),
    }, ensure_ascii=False, indent=2), flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root")
    args = parser.parse_args()
    run(root_path(args.root))
