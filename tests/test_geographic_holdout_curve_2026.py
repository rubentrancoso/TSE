"""Testes Fase 5P: perfis geograficos pre-corte, sem vazamento de resultados futuros."""
from pathlib import Path
from unittest.mock import patch
import csv
import json
import tempfile
import unittest

import test_geographic_holdout_curve_2026 as mod
import analyze_operational_curve_2026 as s
from correct_bweb_28_periodicity_2026 import VERSION as M_VERSION
from reconcile_stream import sha256


class GeographicHoldoutTests(unittest.TestCase):
    def example(self):
        split={
          ("BA","101"):[100,60,30,100,40,50],
          ("BA","202"):[0,0,0,100,70,20],
          ("MG","303"):[100,20,70,100,40,50],
        }
        first={("BA","101"):[20,8,10],("BA","202"):[40,28,8],
               ("MG","303"):[20,8,10]}
        second={("BA","101"):[80,32,40],("BA","202"):[60,42,12],
                ("MG","303"):[80,32,40]}
        minutes={"2026-10-04 20:04":first,"2026-10-04 20:05":second}
        final={("BA","101"):[200,100,80],
               ("BA","202"):[100,70,20],
               ("MG","303"):[200,60,120]}
        return split,minutes,final

    def test_holdout_baseline_and_in_sample_leakage(self):
        split,minutes,final=self.example()
        rows,ufs,muns,summary=mod.create_forecasts(split,minutes,final)
        self.assertEqual(summary["training_pre_cut_valid"],200)
        self.assertEqual(summary["holdout_post_cut_valid"],300)
        self.assertEqual(summary["holdout_post_cut_lula"],150)
        self.assertEqual(summary["municipalities_without_pre_cut_voting"],1)
        self.assertEqual(summary["post_votes_from_unseen_municipalities"],100)
        m=summary["forecast_models"]
        self.assertAlmostEqual(m["BR_pre"]["pred_lula_pct"],40)
        self.assertAlmostEqual(m["UF_pre"]["pred_lula_pct"],140/3)
        self.assertAlmostEqual(m["MUNICIPIO_pre"]["pred_lula_pct"],140/3)
        self.assertAlmostEqual(m["MUNICIPIO_final_IN_SAMPLE"]["pred_lula_pct"],50)
        self.assertAlmostEqual(m["MUNICIPIO_final_IN_SAMPLE"]["lula_final_error_pp"],0)
        self.assertEqual(rows[-1]["cum_post_valid"],300)
        self.assertEqual(rows[0]["brt_minute"],"2026-10-04 20:04")
        self.assertEqual(len(ufs),2)
        self.assertEqual(len(muns),3)

    def test_no_lookahead_when_post_results_change(self):
        split,minutes,final=self.example()
        original=mod.create_forecasts(split,minutes,final)[3]["forecast_models"]
        # Vazamento deliberado: alterar somente os dados futuros usados no oracle.
        future=final.copy()
        future[("BA","202")]=[100,85,5]
        updated=mod.create_forecasts(split,minutes,future)[3]["forecast_models"]
        for k in ("BR_pre","UF_pre","MUNICIPIO_pre"):
            self.assertEqual(original[k]["pred_lula_pct"],updated[k]["pred_lula_pct"])
        self.assertNotEqual(original["MUNICIPIO_final_IN_SAMPLE"]["pred_lula_pct"],
                            updated["MUNICIPIO_final_IN_SAMPLE"]["pred_lula_pct"])

    def test_seconds_cut_not_minute_cut_and_sha(self):
        with tempfile.TemporaryDirectory() as t:
            base=Path(t)
            shard=base/"received-AC.csv"
            with shard.open("w",encoding="utf-8",newline="") as f:
                w=csv.writer(f,delimiter=";")
                w.writerow(("UF","municipio","zona","secao","turno",
                            "recebimento_minuto","DT_BU_RECEBIDO",
                            "votos_pres_validos","votos_13","votos_22"))
                w.writerow(("AC","10","1","1","1","2026-10-04 20:04",
                            "04/10/2026 20:04:38","102","60","40"))
                w.writerow(("AC","10","1","2","1","2026-10-04 20:04",
                            "04/10/2026 20:04:39","100","25","75"))
            nr=base/"phase5h_nr28_sections_AC.csv"
            nr.write_text("UF;municipio;zona;secao;votos_28\nAC;10;1;1;2\n",
                          encoding="utf-8")
            meta={"version":M_VERSION,"csv_sha256":sha256(nr),
                  "archive_sha256":"abc","votes_28":2}
            (base/"phase5h_nr28_sections_AC.json").write_text(
                json.dumps(meta),encoding="utf-8")
            manifest={"ufs":{"AC":{"sections":2,"shard_sha256":sha256(shard),
                                   "source_sha256":"abc"}}}
            corrected={"checkpoint_sources":{"AC":meta}}
            with patch.object(s,"UFs",("AC",)):
                *common,split,post=s.read_receipt_data(base,manifest,corrected,include_holdout=True)
            self.assertEqual(split[("AC","10")],[100,60,40,100,25,75])
            self.assertEqual(post["2026-10-04 20:04"][("AC","10")],[100,25,75])
            self.assertEqual(common[3]["AC"],[100,60,40,100,25,75])
            # O minuto e o mesmo, mas os segundos separam corretamente pre/post.
            self.assertEqual(len(common[0]),1)
            shard.write_text("changed",encoding="utf-8")
            with patch.object(s,"UFs",("AC",)):
                with self.assertRaises(RuntimeError):
                    s.read_receipt_data(base,manifest,corrected,include_holdout=True)

    def test_rejects_no_training_or_invalid_prior(self):
        split,minutes,final=self.example()
        with self.assertRaises(ValueError):
            mod.create_forecasts(split,minutes,final,prior_votes=0)
        no_pre={k:[0,0,0,*v[3:]] for k,v in split.items()}
        with self.assertRaises(ValueError):
            mod.create_forecasts(no_pre,minutes,final)


if __name__=="__main__":
    unittest.main()
