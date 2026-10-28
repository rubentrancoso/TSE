"""Tests for Fase 5S EA20 publication batch mechanics (first round only)."""
import csv
import json
from pathlib import Path
import tempfile
import unittest

import audit_ea20_publication_mechanics_2026 as mod
from analyze_operational_curve_2026 import CUT, NATIONAL, ea20_rows


class PublicationMechanicsTests(unittest.TestCase):
    def test_versioned_national_real_counts_and_fit(self):
        repo=Path(__file__).resolve().parents[1]
        rows=ea20_rows(repo/NATIONAL)
        batches,blocks,stat=mod.describe(rows,expected_post=153)
        self.assertEqual(len(batches),152)
        self.assertEqual(sum(r["d_valid"] for r in batches),18809656)
        self.assertEqual(sum(x["valid"] for x in blocks),18809656)
        self.assertEqual(sum(x["lula"] for x in blocks),stat["published_tail"]["lula"])
        self.assertAlmostEqual(stat["fits"]["sections"]["actual"]["r2"],
                               0.9904447872243246,places=10)
        self.assertGreater(stat["fits"]["sections"]["constant_tail_oracle"]["r2"],
                           stat["fits"]["sections"]["actual"]["r2"])
        self.assertAlmostEqual(stat["fits"]["valid"]["actual"]["r2"],
                               0.9897050824675357,places=10)
        self.assertLess(stat["constant_tail_oracle"]["rmse_actual_minus_oracle_cumulative_pp"],0.14)
        self.assertAlmostEqual(stat["early_ten_update_training"]["training_lula_pct"],
                               51.22462907223229,places=8)
        self.assertAlmostEqual(stat["early_ten_update_training"]["forecast_final_lula_pct"],
                               44.71129772903334,places=8)
        self.assertAlmostEqual(stat["last_20_updates"]["lula_pct"],
                               81.6985348894959,places=8)
        self.assertEqual(stat["endpoint_line_diagnostic"]["unphysical_required_batch_shares"],0)

    def test_future_change_does_not_change_training_rate(self):
        repo=Path(__file__).resolve().parents[1]
        original=ea20_rows(repo/NATIONAL)
        _,_,baseline=mod.describe(original,expected_post=153)
        modified=[]
        # Change only the final stage (after 10 training updates).
        # The oracle must change but the training rate must remain invariant.
        for r in original:
            r=r.copy()
            if r["brt"]=="2026-10-05 02:59:31":
                r["lula"]+=2
                r["d_lula"]+=2
            modified.append(r)
        _,_,changed=mod.describe(modified,expected_post=153)
        training="early_ten_update_training"
        self.assertEqual(baseline[training]["training_lula_pct"],
                         changed[training]["training_lula_pct"])
        self.assertNotEqual(baseline["published_tail"]["lula_pct"],
                            changed["published_tail"]["lula_pct"])
        self.assertNotEqual(baseline[training]["forecast_final_error_pp"],
                            changed[training]["forecast_final_error_pp"])

    def test_reject_bad_increment_and_small_training(self):
        repo=Path(__file__).resolve().parents[1]
        data=ea20_rows(repo/NATIONAL)
        with self.assertRaises(ValueError):
            mod.describe(data,training_updates=0)
        broken=[x.copy() for x in data]
        index=next(i for i,r in enumerate(broken) if r["brt"]>CUT)
        broken[index]["d_valid"]+=1
        with self.assertRaises(RuntimeError):
            mod.describe(broken)

    def test_no_download_and_notebook_has_unexecuted_codes(self):
        repo=Path(__file__).resolve().parents[1]
        script=(repo/"audit_ea20_publication_mechanics_2026.py").read_text(encoding="utf-8")
        for forbidden in ("urllib.request","urlopen(", "requests.get(", ".extractall(", "sqlite3"):
            self.assertNotIn(forbidden,script)
        notebook=repo/"notebooks"/"TSE_2026_Laboratorio_Forense_Fase_X.ipynb"
        nb=json.loads(notebook.read_text(encoding="utf-8"))
        self.assertEqual(nb["nbformat"],4)
        self.assertGreaterEqual(len(nb["cells"]),12)
        src=""
        for cell in nb["cells"]:
            if cell["cell_type"]=="code":
                code="".join(cell["source"])
                compile(code,"<notebook phase X>","exec")
                self.assertTrue(cell.get("execution_count") is None or (type(cell["execution_count"]) is int and cell["execution_count"] >= 0))
                self.assertEqual(cell["outputs"],[])
                src+=code
        self.assertIn("phase5s_ea20_publication_mechanics_2026_summary.json",src)


if __name__=="__main__":
    unittest.main()
