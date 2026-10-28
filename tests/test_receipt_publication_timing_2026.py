"""Fase 5T: testa limites de recebimento versus publicação, com fontes sintéticas."""
import csv
import json
from pathlib import Path
import tempfile
import unittest

import audit_receipt_publication_timing_2026 as mod
from analyze_operational_curve_2026 import CUT, NATIONAL, ea20_rows
from correct_bweb_28_periodicity_2026 import VERSION as M_VERSION
from reconcile_stream import sha256


class ReceiptPublicationTests(unittest.TestCase):
    def mock(self):
        events={
            "2026-10-04 20:04:38":[1,100,60,30],
            "2026-10-04 20:04:39":[1,100,40,50],
            "2026-10-04 20:04:50":[1,100,80,15],
        }
        ea=[
            dict(brt=CUT,st=1,valid=50,lula=30,flavio=10),
            dict(brt="2026-10-04 20:04:45",st=2,valid=200,lula=100,flavio=80),
            dict(brt="2026-10-04 20:05:00",st=3,valid=300,lula=180,flavio=95),
        ]
        return events,ea

    def test_zero_offset_feasibility_and_boundaries(self):
        events,ea=self.mock()
        rows,offsets,status=mod.evaluate(ea,events)
        self.assertEqual(len(rows),3)
        self.assertEqual(rows[0]["valid_received_by_then"],200)
        self.assertEqual(rows[0]["valid_received_minus_published"],150)
        self.assertEqual(rows[0]["lula_received_minus_published"],70)
        self.assertEqual(rows[0]["latest_necessary_receipt_time"],"2026-10-04 20:04:38")
        self.assertEqual(rows[0]["aggregate_rank_slack_seconds"],1)
        self.assertTrue(all(row["all_three_constraints_ok"] for row in rows))
        self.assertTrue(status["baseline_offsets"]["all_constraints_held"])
        self.assertEqual(status["source_events"]["sections"],3)
        self.assertEqual(offsets[0]["offset_seconds_applied_to_bweb"],0)
        self.assertEqual(offsets[0]["snapshots_any_excess"],0)
        self.assertEqual(rows[-1]["valid_received_minus_published"],0)

    def test_candidate_excess_despite_sufficient_valid(self):
        events,ea=self.mock()
        ea[1]=dict(brt="2026-10-04 20:04:45",st=2,
                   valid=200,lula=150,flavio=40)
        rows,offsets,status=mod.evaluate(ea,events)
        self.assertTrue(rows[1]["constraint_valid_ok"])
        self.assertFalse(rows[1]["constraint_lula_ok"])
        self.assertFalse(rows[1]["all_three_constraints_ok"])
        self.assertEqual(status["baseline_offsets"]["snapshot_violations"],1)
        self.assertEqual(status["baseline_offsets"]["worst_lula_shortfall"],50)

    def test_shifting_clock_changes_necessary_constraint(self):
        events,ea=self.mock()
        rows,shifts,status=mod.evaluate(ea,events,offsets=(0,300,-300))
        by={r["offset_seconds_applied_to_bweb"]:r for r in shifts}
        self.assertGreater(by[300]["snapshots_any_excess"],0)
        self.assertEqual(by[-300]["snapshots_any_excess"],0)
        self.assertFalse(by[300]["final_valid_received"]==300)
        self.assertEqual(by[-300]["final_valid_received"],300)

    def test_one_pass_real_shard_and_sha_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            shard=folder/"received-AC.csv"
            with shard.open("w",encoding="utf-8",newline="") as f:
                w=csv.writer(f,delimiter=";")
                w.writerow(("UF","municipio","zona","secao","turno",
                            "DT_BU_RECEBIDO","recebimento_minuto",
                            "votos_pres_validos","votos_13","votos_22"))
                w.writerow(("AC","10","1","1","1","04/10/2026 20:04:38",
                            "2026-10-04 20:04","102","60","30"))
                w.writerow(("AC","10","1","2","1","04/10/2026 20:04:39",
                            "2026-10-04 20:04","100","40","50"))
            nr=folder/"phase5h_nr28_sections_AC.csv"
            nr.write_text("municipio;zona;secao;votos_28\n10;1;1;2\n",encoding="utf-8")
            state=dict(version=M_VERSION,csv_sha256=sha256(nr),
                       votes_28=2,archive_sha256="abc")
            (folder/"phase5h_nr28_sections_AC.json").write_text(
                json.dumps(state),encoding="utf-8")
            h={"ufs":{"AC":{"sections":2,"shard_sha256":sha256(shard),
                            "source_sha256":"abc"}}}
            m={"checkpoint_sources":{"AC":state}}
            events,totals,_=mod.read_second_events(folder,h,m,ufs=("AC",))
            self.assertEqual(totals,[2,200,100,80])
            self.assertEqual(events["2026-10-04 20:04:38"],[1,100,60,30])
            self.assertEqual(events["2026-10-04 20:04:39"],[1,100,40,50])
            shard.write_text("tampered",encoding="utf-8")
            with self.assertRaises(RuntimeError):
                mod.read_second_events(folder,h,m,ufs=("AC",))

    def test_real_ea20_snapshots_reconciled(self):
        repo=Path(__file__).resolve().parents[1]
        ea=ea20_rows(repo/NATIONAL)
        self.assertEqual(len(ea),193)
        self.assertEqual(ea[-1]["valid"],119300788)
        self.assertIn(CUT,[r["brt"] for r in ea])

    def test_notebook_syntax_and_source(self):
        path=(Path(__file__).resolve().parents[1]/"notebooks"/
              "TSE_2026_Laboratorio_Forense_Fase_Y.ipynb")
        doc=json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(doc["nbformat"],4)
        self.assertGreaterEqual(len(doc["cells"]),12)
        code=""
        for cell in doc["cells"]:
            if cell["cell_type"]=="code":
                body="".join(cell["source"])
                compile(body,"<notebook Y>","exec")
                self.assertIsInstance(cell.get("outputs", []), list)
                self.assertTrue(cell.get("execution_count") is None or (type(cell["execution_count"]) is int and cell["execution_count"] >= 0))
                code+=body
        self.assertIn("phase5t_receipt_vs_publication_2026_summary.json",code)
        self.assertIn("sha256(",code)


if __name__=="__main__":
    unittest.main()
