"""Fase 5K: integridade SHA e comparacao de chaves nacionais 2026."""
import csv
import json
from pathlib import Path
import tempfile
import unittest

import certify_2026_all_section_keys as mod
from reconcile_stream import sha256


class NationalKeys2026Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def test_ea16_principal_and_aggregated_independent_sets(self):
        file=self.root/"ba.json"
        file.write_text(json.dumps({"abr":[{"cd":"ba","mu":[
            {"cd":"033693","zon":[{"cd":"0177","sec":[
                {"ns":"0109"},{"ns":"0110","nsp":"0109"},{"ns":"0111"}
            ]}]}
        ]}]}),encoding="utf-8")
        principal,aggregated=mod.parse_ea16(file,"BA")
        self.assertEqual(len(principal),2)
        self.assertEqual(len(aggregated),1)
        self.assertIn(("BA",33693,177,109),principal)
        self.assertNotIn(("BA",33693,177,110),principal)

    def test_bweb_keys_are_normalized_and_duplicates_blocked(self):
        file=self.root/"received-BA.csv"
        def rows(data):
            with file.open("w",encoding="utf-8",newline="") as f:
                w=csv.writer(f,delimiter=";")
                w.writerow(("UF","municipio","zona","secao","turno"))
                w.writerows(data)
        rows([("BA","33693","0177","0109","1"),("BA","33693","177","111","1")])
        data=mod.parse_bweb_shard(file,"BA")
        self.assertEqual(len(data),2)
        rows([("BA","33693","0177","0109","1"),
              ("BA","33693","177","109","1")])
        with self.assertRaises(RuntimeError):
            mod.parse_bweb_shard(file,"BA")
        rows([("MG","33693","177","109","1")])
        with self.assertRaises(RuntimeError):
            mod.parse_bweb_shard(file,"BA")

    def test_sha_tamper_and_snapshot_counter(self):
        file=self.root/"ea20.json"
        file.write_text(json.dumps({"s":{"st":40,"ts":40},"dt":"05/10/2026","ht":"00:52:50"}),encoding="utf-8")
        good=sha256(file)
        self.assertTrue(mod.sha_safe(file,good))
        snap=mod.count_snapshot(file)
        self.assertEqual(snap["st"],40)
        self.assertEqual(snap["ts"],40)
        file.write_text(json.dumps({"s":{"st":"35.476","ts":"35.476"}}),encoding="utf-8")
        dotted=mod.count_snapshot(file)
        self.assertEqual(dotted["st"],35476)
        file.write_text("alterado",encoding="utf-8")
        with self.assertRaises(RuntimeError):
            mod.sha_safe(file,good)

    def test_missing_does_not_mean_zero(self):
        self.assertFalse(mod.sha_safe(self.root/"absent.zip","a"*64))

if __name__=="__main__":
    unittest.main()
