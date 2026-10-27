"""Testes de reconciliacao dos 5246 votos 2026 usando cache individual BWEB."""
import csv
import json
import tempfile
from collections import Counter
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import audit_bweb_uf_totals_2026 as audit
from extract_bweb_received_2026 import HEAD, VERSION as INPUT_VERSION
from reconcile_stream import sha256


class TestBUUFReconciliation(TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.folder=self.root/"analysis"/"periodicidade_bweb_2026"
        self.folder.mkdir(parents=True)
        path=self.folder/"received-AC.csv"
        self.path=path
        self.table=[
            ("AC","1104","5","1","1","2026-10-04 18:00:03",
             "2026-10-04 18:00","a"*64,200,205,80,100,3,2),
            ("AC","1104","5","2","1","2026-10-04 18:00:04",
             "2026-10-04 18:00","a"*64,150,157,60,75,4,3)]
        with path.open("w",encoding="utf-8",newline="") as f:
            w=csv.writer(f,delimiter=";");w.writerow(HEAD);w.writerows(self.table)
        (self.folder/"summary.json").write_text(json.dumps({
            "version":INPUT_VERSION,"sections":2,
            "ufs":{"AC":{"sections":2,"shard_sha256":sha256(path)}}}),
            encoding="utf-8")

    def test_counts_and_candidate_grouping(self):
        records,sha=audit.sum_bweb(self.folder)
        self.assertEqual(records["AC"]["sections"],2)
        self.assertEqual(records["AC"]["valid"],350)
        self.assertEqual(records["AC"]["13"],140)
        self.assertEqual(records["AC"]["22"],175)
        self.assertEqual(records["AC"]["other"],35)
        self.assertEqual(records["AC"]["blank"],7)
        self.assertEqual(records["AC"]["null"],5)
        off={"AC":Counter({"13":140,"22":175,"14":30})}
        compared=audit.compare(records,off)
        self.assertEqual(compared[0]["diferenca_validos"],5)
        self.assertEqual(compared[0]["diferenca_demais"],5)
        self.assertEqual(compared[0]["diferenca_13"],0)
        self.assertEqual(compared[0]["diferenca_22"],0)

    def test_invalid_hash_is_detected(self):
        with self.path.open("a",encoding="utf-8") as f:
            f.write("untrusted;row\n")
        with self.assertRaises(RuntimeError):
            audit.sum_bweb(self.folder)

    def test_end_to_end_only_cache_read(self):
        fake={"AC":Counter({"13":140,"22":175,"14":30})}
        with patch.object(audit,"official",return_value=(fake,"b"*64)):
            result=audit.run(self.root)
        self.assertEqual(result["national"]["diferenca_validos"],5)
        self.assertEqual(result["national"]["diferenca_demais"],5)
        self.assertEqual(result["national"]["diff_sections_vs_snapshot_499248"],-499246)
        self.assertTrue((self.folder/"phase5f_reconciliation_2026_summary.json").exists())
        self.assertEqual(result["largest_uf_differences"][0]["UF"],"AC")

    def test_real_official_reference_sum(self):
        table=Path("data/forensics/analysis/uf_candidate_reconciliation.csv")
        if not table.is_file():
            self.skipTest("Referencial de candidatos nacional nao incluido nesta copia")
        candidates,digest=audit.official(table)
        self.assertEqual(len(candidates),28)
        self.assertEqual(sum(sum(x.values()) for x in candidates.values()),119300788)
        self.assertEqual(len(digest),64)


if __name__=="__main__":
    import unittest
    unittest.main()
