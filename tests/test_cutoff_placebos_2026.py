"""Fase 5R: placebos temporais de seções dentro de zonas; testes sinteticos."""
import csv
import json
from pathlib import Path
import tempfile
import unittest

import analyze_cutoff_placebos_2026 as w
from correct_bweb_28_periodicity_2026 import VERSION as M_VERSION
from reconcile_stream import sha256


class TimeCutoffPlaceboTests(unittest.TestCase):
    def test_zone_shift_and_eligible_coverage(self):
        cuts=("2026-10-04 18:00:00", w.CUT,"2026-10-04 21:00:00")
        # First zone has 4k valid before/after primary with 50% -> 70% Lula.
        # Second zone only arrives after primary and is never paired then.
        records={
            ("AC","10","1"):[8000,4800,2800,
                             0,0,0, 4000,2000,1800, 8000,4800,2800],
            ("AC","20","1"):[3000,1500,1000,
                             0,0,0, 0,0,0, 3000,1500,1000],
        }
        rows,ufs,zones,robust=w.measure_cutoffs(records,cuts,min_side=100)
        primary=rows[1]
        self.assertEqual(primary["all_post_valid"],7000)
        self.assertEqual(primary["all_pre_valid"],4000)
        self.assertEqual(primary["paired_zones"],1)
        self.assertEqual(primary["paired_post_valid"],4000)
        self.assertAlmostEqual(primary["weighted_shift_lula_pp"],20.0)
        self.assertEqual(primary["positive_zone_count"],1)
        self.assertEqual(ufs[0]["UF"],"AC")
        self.assertEqual(len(zones),1)
        self.assertEqual(rows[0]["paired_zones"],0)
        self.assertEqual(rows[2]["paired_zones"],0)

    def test_pre_cutoff_accumulator_includes_all_later_cutoffs(self):
        cuts=("2026-10-04 19:00:00",w.CUT,"2026-10-04 21:00:00")
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            shard=folder/"received-AC.csv"
            with shard.open("w",newline="",encoding="utf-8") as f:
                wr=csv.writer(f,delimiter=";")
                wr.writerow(("UF","municipio","zona","secao","turno","recebimento_minuto",
                    "DT_BU_RECEBIDO","votos_pres_validos","votos_13","votos_22"))
                wr.writerow(("AC","10","1","1","1","2026-10-04 20:00",
                    "04/10/2026 20:00:00","102","60","35"))
                wr.writerow(("AC","10","1","2","1","2026-10-04 20:04",
                    "04/10/2026 20:04:39","100","70","25"))
            nr=folder/"phase5h_nr28_sections_AC.csv"
            nr.write_text("municipio;zona;secao;votos_28\n10;1;1;2\n",encoding="utf-8")
            state={"version":M_VERSION,"csv_sha256":sha256(nr),
                   "archive_sha256":"abc","votes_28":2}
            (folder/"phase5h_nr28_sections_AC.json").write_text(json.dumps(state),encoding="utf-8")
            manifest={"ufs":{"AC":{"sections":2,"shard_sha256":sha256(shard),
                  "source_sha256":"abc"}}}
            corrected={"checkpoint_sources":{"AC":state}}
            records,totals,_=w.read_multicut(folder,manifest,corrected,cutoffs=cuts,ufs=("AC",))
            self.assertEqual(totals,[2,200,130,60])
            self.assertEqual(records[("AC","10","1")],
                [200,130,60, 0,0,0, 100,60,35, 200,130,60])
            # Same minute but the second exactly at CUT must be post.
            self.assertEqual(records[("AC","10","1")][6:9],[100,60,35])
            shard.write_text("alterado",encoding="utf-8")
            with self.assertRaises(RuntimeError):
                w.read_multicut(folder,manifest,corrected,cutoffs=cuts,ufs=("AC",))

    def test_invalid_cutoffs_and_minimum(self):
        with self.assertRaises(ValueError):
            w.read_multicut(Path("."),{}, {},cutoffs=(w.CUT,"2026-10-04 18:00:00"),ufs=())
        with self.assertRaises(ValueError):
            w.measure_cutoffs({},min_side=0)


class TimePlaceboNotebookTests(unittest.TestCase):
    def test_code_cells_compile_without_results(self):
        path=Path(__file__).resolve().parents[1]/"notebooks"/"TSE_2026_Laboratorio_Forense_Fase_W.ipynb"
        doc=json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(doc["nbformat"],4)
        self.assertGreaterEqual(len(doc["cells"]),10)
        body=""
        for cell in doc["cells"]:
            if cell["cell_type"]!="code":
                continue
            src="".join(cell["source"])
            compile(src,"<notebook W>","exec")
            self.assertTrue(cell.get("execution_count") is None or (type(cell["execution_count"]) is int and cell["execution_count"] >= 0))
            self.assertEqual(cell["outputs"],[])
            body+=src
        self.assertIn("phase5r_cutoff_placebos_2026_summary.json",body)
        self.assertIn("sha256(",body)
        self.assertNotIn("requests.get(",body)
        self.assertNotIn("subprocess.run(",body)


if __name__=="__main__":
    unittest.main()
