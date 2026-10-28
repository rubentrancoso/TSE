"""Fase 5O - verificacoes do mecanismo de cronologia e decomposicao geografica."""
import csv
from datetime import datetime
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import analyze_operational_curve_2026 as mod
from extract_bweb_received_2026 import VERSION as H_VERSION
from correct_bweb_28_periodicity_2026 import VERSION as M_VERSION
from reconcile_stream import sha256

REPO=Path(__file__).resolve().parents[1]

class OperationalCurveTests(unittest.TestCase):
    def test_versioned_national_timeline_real_data_contract(self):
        rows=mod.ea20_rows(REPO/mod.NATIONAL)
        after=[r for r in rows if r["brt"]>=mod.CUT]
        self.assertEqual(len(after),153)
        self.assertEqual(len(rows),193)
        self.assertEqual(after[0]["valid"],100491132)
        self.assertEqual(rows[-1]["valid"],119300788)
        with_time=mod.describe_line(after,"share_lula_pct","clock")
        with_index=mod.describe_line(after,"share_lula_pct","updates")
        self.assertEqual(with_time["points"],153)
        self.assertEqual(with_index["points"],153)
        self.assertGreater(abs(with_time["rmse_pp"]-with_index["rmse_pp"]),1e-5)
        self.assertTrue(math.isfinite(with_time["r2"]))

    def test_uneven_intervals_are_not_equally_spaced(self):
        times=[mod.stamp(x).timestamp() for x in
          ("2026-10-04 20:04:39","2026-10-04 20:10:56",
           "2026-10-04 20:11:55")]
        self.assertEqual(times[1]-times[0],377)
        self.assertEqual(times[2]-times[1],59)
        y=[43.0,43.4,43.5]
        a=mod.line_fit(times,y)
        b=mod.line_fit([0,1,2],y)
        self.assertNotAlmostEqual(a["rmse_pp"],b["rmse_pp"],places=4)
        self.assertEqual(mod.stamp("2026-10-05 00:00:00")-
                         mod.stamp("2026-10-04 23:59:00"),
                         __import__("datetime").timedelta(seconds=60))

    def test_geo_model_is_a_counterfactual_not_duplicate(self):
        batches={
           "2026-10-04 18:00":{
              ("BA","1"):[1,100,80,20],
              ("BA","2"):[1,100,20,80],
              ("MG","3"):[1,100,40,60]},
           "2026-10-04 19:00":{
              ("BA","1"):[1,100,70,30],
              ("MG","3"):[1,100,10,90]},
        }
        # BA final 400 valid, 170+20=190? BA1=150, BA2=20 => 170,
        # MG final 200 valid, 50 Lula.
        uf={"BA":[300,170,130],"MG":[200,50,150]}
        mun={("BA","1"):[200,150,50],("BA","2"):[100,20,80],
             ("MG","3"):[200,50,150]}
        rows,tot,geo=mod.make_reception_curve(batches,uf,mun)
        self.assertEqual(tot,[5,500,220,280])
        self.assertAlmostEqual(geo[0],220)
        self.assertAlmostEqual(geo[1],220)
        self.assertAlmostEqual(geo[2],280)
        self.assertAlmostEqual(geo[3],280)
        self.assertAlmostEqual(rows[-1]["delta_lula_mun_pp"],0)
        self.assertNotAlmostEqual(rows[0]["share_lula_pct"],
                                  rows[0]["model_mun_lula_pct"])

    def test_sha_and_number28_per_section(self):
        with tempfile.TemporaryDirectory() as t:
            folder=Path(t)
            shard=folder/"received-AC.csv"
            with shard.open("w",encoding="utf-8",newline="") as f:
                w=csv.writer(f,delimiter=";")
                w.writerow(("UF","municipio","zona","secao","turno",
                            "recebimento_minuto","votos_pres_validos",
                            "votos_13","votos_22"))
                w.writerow(("AC","101","1","1","1","2026-10-04 18:00",
                            "102","50","50"))
                w.writerow(("AC","101","1","2","1","2026-10-04 18:01",
                            "100","60","40"))
            nr=folder/"phase5h_nr28_sections_AC.csv"
            nr.write_text("UF;municipio;zona;secao;votos_28\nAC;101;1;1;2\n",
                          encoding="utf-8")
            state={"version":M_VERSION,"csv_sha256":sha256(nr),
                   "archive_sha256":"abc","votes_28":2}
            (folder/"phase5h_nr28_sections_AC.json").write_text(json.dumps(state))
            m={"checkpoint_sources":{"AC":state}}
            h={"ufs":{"AC":{"sections":2,"shard_sha256":sha256(shard),
                            "source_sha256":"abc"}}}
            with patch.object(mod,"UFs",("AC",)):
                b,u,mu,times,seals=mod.read_receipt_data(folder,h,m)
            self.assertEqual(u["AC"],[200,110,90])
            self.assertEqual(b["2026-10-04 18:00"][("AC","101")],
                             [1,100,50,50])
            self.assertEqual(times["AC"][:3],[200,110,90])
            shard.write_text("tampered",encoding="utf-8")
            with patch.object(mod,"UFs",("AC",)):
                with self.assertRaises(RuntimeError):
                    mod.read_receipt_data(folder,h,m)

if __name__=="__main__":
    unittest.main()
