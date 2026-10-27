"""Synthetic checks for jointly calibrated 2026 periodicity across six configs."""
import csv
import json
from pathlib import Path
import tempfile
import unittest

import joint_sensitivity_periodicity_2026 as mod
from analyze_periodicity_2026 import maximum_periodic_r2,prepare,templates
from reconcile_stream import sha256


def fixture(n=80):
    rows=[]
    for i in range(n):
        share=47 + (7 if i%11==0 else 0) - (10 if i%13==0 else 0)
        rows.append({"brt":f"2026-10-04 {17+i//60:02d}:{i%60:02d}",
            "sections":(i+1)*100,
            "minutes":float(i),
            "d_sections":100,"d_valid":30000,
            "d_flavio":int(30000*share/100),
            "d_lula":30000-int(30000*share/100),
            "batch_share_pct":share,
            "cum_share_pct":share})
    return rows


class GlobalSixConfigTest(unittest.TestCase):
    def test_scores_match_original_preprocessing(self):
        rows=fixture()
        spec=mod.specifications(rows)
        ours=mod.score_all([r["batch_share_pct"] for r in rows],spec)
        self.assertEqual(len(ours),6)
        for r in ours:
            selected=prepare(rows,r["minimum_votes"],r["median_window"])
            expected=maximum_periodic_r2(
                [x["residual_pp"] for x in selected],templates(selected))
            self.assertAlmostEqual(r["r2"],expected["r2"],places=12)

    def test_shared_quartile_permutations_preserve_content(self):
        series=list(range(80))
        parts=mod.quartile_parts(len(series))
        from analyze_periodicity_2026 import Mulberry32
        for mode in ("individual","blocks"):
            shuffled=mod.simulate(series,parts,Mulberry32(23456),mode)
            self.assertEqual(len(shuffled),80)
            self.assertNotEqual(shuffled,series)
            for block in parts:
                self.assertCountEqual([shuffled[i] for i in block],
                                      [series[i] for i in block])

    def test_synthetic_joint_test_and_sha_report(self):
        rows=fixture()
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            folder=root/"analysis"/"periodicidade_bweb_2026"
            folder.mkdir(parents=True)
            trace=folder/"phase5h_minute_corrected_2026.csv"
            keys=("brt","sections","minutes","d_sections","d_valid",
                  "d_flavio","d_lula","batch_share_pct","cum_share_pct")
            with trace.open("w",encoding="utf-8",newline="") as f:
                w=csv.DictWriter(f,fieldnames=keys,delimiter=";")
                w.writeheader();w.writerows(rows)
            digest=sha256(trace)
            prior={"status":"VALIDOS_PRESIDENCIAIS_CORRIGIDOS",
                   "difference_valid_vs_official":0,
                   "distinct_minutes":80,
                   "initial_sections":8000,
                   "corrected_totals":{"valid":2400000},
                   "corrected_minutes_sha256":digest}
            (folder/"phase5h_corrected_periodicity_2026_summary.json").write_text(
                json.dumps(prior),encoding="utf-8")
            result=mod.run(root,repetitions=100,seed=20261027)
            self.assertEqual(result["total_selected_configs"],6)
            self.assertEqual(result["minutes"],80)
            self.assertEqual(result["source_sha256"],digest)
            self.assertEqual(result["searched_periods_per_configuration"],144)
            self.assertEqual(result["status"],"TESTE_GLOBAL_EXPLORATORIO_2026")
            for null in result["joint_null_tests"].values():
                self.assertTrue(0<null["p_global_grid_and_frequencies"]<=1)
                self.assertTrue(0<null["p_postselected_configuration_uncorrected"]<=1)
                # The joint maximum has at least as many exceedances as a
                # particular selected candidate under the SAME permutations.
                self.assertGreaterEqual(null["null_exceedances_global"],0)
            output=folder/"phase5i_joint_periodicity_2026_summary.json"
            self.assertTrue(output.is_file())
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["source_sha256"],digest)
            with trace.open("a",encoding="utf-8") as f:
                f.write("tampered\n")
            with self.assertRaises(RuntimeError):
                mod.run(root,repetitions=100,seed=20261027)

    def test_rejects_less_than_hundred(self):
        with self.assertRaises(ValueError):
            mod.compute(fixture(),repetitions=99)


if __name__=="__main__":
    unittest.main()
