"""Teste de curva presidencial por BU individual com ordenacao so por minuto BWEB."""
import csv
from pathlib import Path
import tempfile
import json
import unittest
from unittest.mock import patch

import analyze_bweb_receipt_periodicity_2026 as mod
from extract_bweb_received_2026 import HEAD, VERSION as INPUT_VERSION
from reconcile_stream import sha256


class BWEBPeriodicity2026Test(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        self.base=self.root/"analysis"/"periodicidade_bweb_2026"
        self.base.mkdir(parents=True)
        rows=[]
        for i in range(60):
            minute=f"2026-10-04 {17+i//60:02d}:{i%60:02d}"
            valid=200
            f=90 if i%7 else 40
            l=valid-f
            rows.append(("AC","1104","5",str(i+1),"1",
                         minute+":05",minute,"a"*64,
                         valid,valid,l,f,0,0))
        self.path=self.base/"received-AC.csv"
        with self.path.open("w",encoding="utf-8",newline="") as f:
            w=csv.writer(f,delimiter=";")
            w.writerow(HEAD)
            w.writerows(rows)
        self.rows=rows
        report={"version":INPUT_VERSION,"shard_count":1,
                "sections":len(rows),
                "ufs":{"AC":{"shard_sha256":sha256(self.path),
                             "sections":len(rows)}}}
        (self.base/"summary.json").write_text(
            json.dumps(report),encoding="utf-8")

    def test_bu_join_and_minute_bins(self):
        buckets,coverage=mod.read_sections(self.base)
        self.assertEqual(coverage["sections_total"],60)
        self.assertEqual(coverage["sections_timestamped"],60)
        self.assertEqual(coverage["fraction_sections_in_UF_span_under_5min"],0)
        self.assertEqual(len(buckets),60)
        timeline=mod.minute_series(buckets)
        self.assertEqual(timeline[-1]["sections"],60)
        self.assertEqual(timeline[-1]["d_valid"],200)
        self.assertEqual(timeline[-1]["cum_share_pct"],
                         100*sum(r[11] for r in self.rows)/(60*200))

    def test_periodicity_reproducible(self):
        series=mod.minute_series(mod.read_sections(self.base)[0])
        report,selected=mod.score(series,minimum_votes=100,simulations=100)
        second,_=mod.score(series,minimum_votes=100,simulations=100)
        self.assertEqual(report,second)
        self.assertEqual(report["batches_selected"],60)
        self.assertTrue(0<=report["best_period"]["r2"]<=1)
        self.assertEqual(len(selected),60)

    def test_run_no_network_or_sqlite(self):
        result=mod.run(self.root,simulations=100,min_vote=100)
        self.assertEqual(result["status"],"APURACAO_POR_MINUTO_ANALISADA")
        self.assertEqual(result["minute_bins"],60)
        self.assertTrue((self.base/"phase5c_summary.json").is_file())
        self.assertIn("periodicity",result)

    def test_noncredible_uf_burst_blocks_claim(self):
        dataset=list(csv.reader(self.path.open(encoding="utf-8"),delimiter=";"))
        for i,row in enumerate(dataset[1:],1):
            row[6]="2026-10-04 17:01" if i<=30 else "2026-10-04 17:02"
        with self.path.open("w",encoding="utf-8",newline="") as f:
            w=csv.writer(f,delimiter=";")
            w.writerows(dataset)
        manifest=json.loads((self.base/"summary.json").read_text("utf-8"))
        manifest["ufs"]["AC"]["shard_sha256"]=sha256(self.path)
        (self.base/"summary.json").write_text(json.dumps(manifest),encoding="utf-8")
        report=mod.run(self.root,simulations=100,min_vote=100)
        self.assertEqual(report["status"],"HORARIOS_BWEB_AGRUPADOS_NAO_APLICAR_ORDEM")
        self.assertNotIn("periodicity",report)

    def test_source_integrity_mandatory(self):
        with self.path.open("a",encoding="utf-8") as f:
            f.write("corrupt\n")
        with self.assertRaises(RuntimeError):
            mod.read_sections(self.base)


if __name__=="__main__":
    unittest.main()
