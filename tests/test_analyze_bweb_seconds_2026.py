"""Testes offline: 2026 BU por segundo com empates preservados."""
import csv
import json
from pathlib import Path
import tempfile
import unittest

import analyze_bweb_seconds_2026 as mod
from extract_bweb_received_2026 import HEAD,VERSION as EXTRACT_VERSION
from reconcile_stream import sha256


class BwebSecondTest(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.folder=self.root/"analysis"/"periodicidade_bweb_2026"
        self.folder.mkdir(parents=True)
        self.cache=self.folder/"received-AC.csv"
        self.members=[]
        for i in range(60):
            second=f"2026-10-04 18:{i//60:02d}:{i%60:02d}"
            minute=second[:16]
            for j in range(2):
                valid=300
                f=130 if i%7 else 50
                self.members.append(("AC","1104","5",str(i*2+j+1),"1",
                     second,minute,"a"*64,valid,valid,valid-f,f,0,0))
        with self.cache.open("w",encoding="utf-8",newline="") as f:
            w=csv.writer(f,delimiter=";")
            w.writerow(HEAD);w.writerows(self.members)
        meta={"version":EXTRACT_VERSION,"sections":len(self.members),
             "ufs":{"AC":{"sections":len(self.members),
                           "shard_sha256":sha256(self.cache)}}}
        (self.folder/"summary.json").write_text(json.dumps(meta),encoding="utf-8")

    def test_parse_exact_seconds(self):
        self.assertEqual(mod.parse_original_second("04/10/2026 17:15:06"),
                         ("2026-10-04 17:15:06",True))
        self.assertEqual(mod.parse_original_second("2026-10-04 17:15"),
                         ("2026-10-04 17:15:00",False))
        with self.assertRaises(RuntimeError):
            mod.parse_original_second("INVALID")

    def test_same_second_is_never_split(self):
        groups,info=mod.read_seconds(self.folder)
        self.assertEqual(info["sections"],120)
        self.assertEqual(info["seconds_coverage"],1)
        self.assertEqual(info["n_distinct_seconds"],60)
        self.assertEqual(info["max_sections_in_same_second"],2)
        grouped=mod.group_to_series(groups,5)
        self.assertEqual(grouped[0]["d_sections"],6)
        self.assertEqual(grouped[-1]["sections"],120)
        self.assertEqual(sum(x["d_sections"] for x in grouped),120)
        self.assertEqual(len(mod.group_to_series(groups)),60)

    def test_sha_validation_rejects_changed_cache(self):
        with self.cache.open("a",encoding="utf-8") as f:
            f.write("tampered\n")
        with self.assertRaises(RuntimeError):
            mod.read_seconds(self.folder)

    def test_periodogram_with_injected_regular_dip(self):
        from datetime import datetime, timedelta
        base=datetime(2026,10,4,18,0,0)
        groups={}
        for i in range(150):
            t=(base+timedelta(seconds=i)).strftime("%Y-%m-%d %H:%M:%S")
            f=600 if i%11 else 100
            groups[t]=[5,1000,f,1000-f]
        series=mod.group_to_series(groups,target_sections=10)
        assert len(series)>=30
        first=mod.test_periodicity(series,1000,15,100,20261027)
        second=mod.test_periodicity(series,1000,15,100,20261027)
        self.assertEqual(first,second)
        self.assertEqual(first["points_analyzed"],75)

    def test_run_with_insufficient_section_count_returns_explicit_reason(self):
        report=mod.run(self.root,simulations=100)
        self.assertEqual(report["status"],"TESTE_EXPLORATORIO_DE_SEGUNDOS_E_BLOCOS")
        self.assertEqual(len(report["tests"]),3)
        self.assertTrue(all("not_executed_reason" in t for t in report["tests"]))
        self.assertTrue((self.folder/"phase5e_por_segundo_2026.csv").is_file())


if __name__=="__main__":
    unittest.main()
