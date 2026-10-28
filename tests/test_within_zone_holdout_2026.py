"""Fase 5Q — controles sinteticos, segregacao temporal e integridade SHA."""
import csv
import json
from pathlib import Path
import tempfile
import unittest

import analyze_within_zone_holdout_2026 as v
import audit_geographic_holdout_curve_2026 as t
from correct_bweb_28_periodicity_2026 import VERSION as M_VERSION
from reconcile_stream import sha256


class ZoneHoldout2026Tests(unittest.TestCase):
    def fixture(self):
        zones = {
            ("AC","10","1"): [4000,2400,1000,3000,2200,600],
            ("AC","10","2"): [4000,1200,2300,2000,800,900],
            ("AC","20","1"): [0,0,0,3000,2700,150],
        }
        minutes = {
            "2026-10-04 20:04": {("AC","10","1"):[2000,1500,400]},
            "2026-10-04 20:05": {
                ("AC","10","1"):[1000,700,200],
                ("AC","10","2"):[2000,800,900],
                ("AC","20","1"):[3000,2700,150],
            }
        }
        return zones, minutes

    def test_models_and_group_reconciliation(self):
        z, mins = self.fixture()
        minutes, municipalities, zones, result = v.evaluate(z, mins)
        self.assertEqual(result["valid_pre"],8000)
        self.assertEqual(result["valid_post"],8000)
        self.assertEqual(result["lula_post"],5700)
        self.assertEqual(len(zones),3)
        self.assertEqual(len(municipalities),2)
        self.assertEqual(len(minutes),2)
        self.assertEqual(sum(g["post_valid"] for g in result["categories"].values()),8000)
        self.assertEqual(sum(g["post_lula"] for g in result["categories"].values()),5700)
        self.assertEqual(result["categories"]["MUNICIPIO_SEM_PRE"]["post_valid"],3000)
        self.assertEqual(result["paired_zones_with_1000_pre_and_post"],2)
        models = result["forecast_models"]
        self.assertNotEqual(models["ZONA_pre"]["pred_lula_pct"],
                            models["MUNICIPIO_pre"]["pred_lula_pct"])

    def test_pretime_models_match_phase_t(self):
        z, mins = self.fixture()
        split = {}
        final = {}
        for (uf, mu, zone), counts in z.items():
            k = (uf,mu)
            a = split.setdefault(k,[0]*6)
            for i in range(6):
                a[i] += counts[i]
        for k,a in split.items():
            final[k]=[a[0]+a[3],a[1]+a[4],a[2]+a[5]]
        tminutes={}
        for minute,by_zone in mins.items():
            d={}
            for (uf,mu,zone),values in by_zone.items():
                a=d.setdefault((uf,mu),[0,0,0])
                for i in range(3):
                    a[i]+=values[i]
            tminutes[minute]=d
        prior=t.create_forecasts(split,tminutes,final)[3]["forecast_models"]
        actual=v.evaluate(z,mins)[3]["forecast_models"]
        for name in ("BR_pre","UF_pre","MUNICIPIO_pre"):
            for metric in ("pred_lula_pct","lula_final_error_pp","weighted_minute_rmse_lula_pp"):
                self.assertAlmostEqual(actual[name][metric],prior[name][metric],places=7)

    def test_future_outcome_cannot_change_prezone_rate(self):
        z, mins = self.fixture()
        original=v.evaluate(z,mins)[3]["forecast_models"]
        a=[*z[("AC","10","1")]]
        # Same future vote volume, different future split.
        a[4]+=200
        a[5]-=200
        z[("AC","10","1")]=a
        changed={k:{key:vv.copy() for key,vv in value.items()} for k,value in mins.items()}
        changed["2026-10-04 20:04"][("AC","10","1")][1]+=100
        changed["2026-10-04 20:04"][("AC","10","1")][2]-=100
        changed["2026-10-04 20:05"][("AC","10","1")][1]+=100
        changed["2026-10-04 20:05"][("AC","10","1")][2]-=100
        later=v.evaluate(z,changed)[3]["forecast_models"]
        for model in ("BR_pre","UF_pre","MUNICIPIO_pre","ZONA_pre"):
            self.assertEqual(original[model]["pred_lula_pct"], later[model]["pred_lula_pct"])
        self.assertNotEqual(original["ZONA_final_IN_SAMPLE"]["pred_lula_pct"],
                            later["ZONA_final_IN_SAMPLE"]["pred_lula_pct"])

    def test_same_minute_second_cut_and_hash_detection(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            path=root/"received-AC.csv"
            with path.open("w",newline="",encoding="utf-8") as f:
                writer=csv.writer(f,delimiter=";")
                writer.writerow(("UF","municipio","zona","secao","turno","recebimento_minuto",
                                 "DT_BU_RECEBIDO","votos_pres_validos","votos_13","votos_22"))
                writer.writerow(("AC","10","1","1","1","2026-10-04 20:04",
                                 "04/10/2026 20:04:38","102","60","38"))
                writer.writerow(("AC","10","1","2","1","2026-10-04 20:04",
                                 "04/10/2026 20:04:39","100","70","25"))
            nr=root/"phase5h_nr28_sections_AC.csv"
            nr.write_text("municipio;zona;secao;votos_28\n10;1;1;2\n",encoding="utf-8")
            meta={"version":M_VERSION,"csv_sha256":sha256(nr),
                  "archive_sha256":"archive_hash","votes_28":2}
            (root/"phase5h_nr28_sections_AC.json").write_text(json.dumps(meta),encoding="utf-8")
            manifest={"ufs":{"AC":{"sections":2,"shard_sha256":sha256(path),
                                    "source_sha256":"archive_hash"}}}
            corrected={"checkpoint_sources":{"AC":meta}}
            zones, minutes, totals, hashes=v.read_zone_votes(root,manifest,corrected,ufs=("AC",))
            self.assertEqual(zones[("AC","10","1")],[100,60,38,100,70,25])
            self.assertEqual(totals,[2,200,130,63])
            self.assertEqual(minutes["2026-10-04 20:04"][("AC","10","1")],[100,70,25])
            path.write_text("tampered",encoding="utf-8")
            with self.assertRaises(RuntimeError):
                v.read_zone_votes(root,manifest,corrected,ufs=("AC",))

    def test_empty_and_bad_prior_rejected(self):
        z,m=self.fixture()
        with self.assertRaises(ValueError):
            v.evaluate(z,m,prior_zone=0)
        with self.assertRaises(ValueError):
            v.evaluate({k:[0,0,0,*a[3:]] for k,a in z.items()},m)


if __name__ == "__main__":
    unittest.main()
