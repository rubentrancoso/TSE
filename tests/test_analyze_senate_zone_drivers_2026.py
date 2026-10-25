"""Testes sinteticos do diagnostico de influencia zonal (somente 2026)."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import analyze_senate_zone_drivers_2026 as drv
from senate_robustness_stats_2026 import pearson, centered, sum_cov
from reconcile_stream import sha256


def moments(x, y):
    n=len(x)
    return [n,sum(x),sum(y),sum(a*a for a in x),
            sum(b*b for b in y),sum(a*b for a,b in zip(x,y))]


class Drivers2026Test(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.folder=Path(tmp.name)/"analysis"/"entre_cargos"/"fixture"
        self.folder.mkdir(parents=True)
        self.first=("AC","101","1","1","13","170")
        self.second=("AC","102","2","1","13","170")
        self.a=moments([.1,.2],[.7,.8])
        self.b=moments([.7,.8],[.16,.2])
        self.adjusted=pearson(sum_cov([centered(self.a),centered(self.b)]))
        self.case=("AC","13","170")
        self.ref={"n":4,"z":2,"adjusted":self.adjusted}

    def test_zone_contributions_and_influence(self):
        stats,details,top=drv.analyze_pair(
            self.case,[(self.first,self.a),(self.second,self.b)],self.ref)
        self.assertEqual(stats["secoes"],4)
        self.assertEqual(stats["zonas_n2"],2)
        self.assertEqual(stats["zonas_cov_pos"],2)
        self.assertEqual(stats["zonas_cov_neg"],0)
        self.assertEqual(stats["pct_zonas_sinal_alinhado"],100)
        self.assertEqual(len(details),2)
        self.assertEqual(len(top),2)
        self.assertAlmostEqual(stats["r_ajustado"],self.adjusted,places=5)
        self.assertTrue(all(row["r_sem_zona"]==1.0 for row in details))
        self.assertAlmostEqual(stats["top5_fracao_cov_abs_pct"],100)

    def test_validates_cache_hashes_and_source_provenance(self):
        directory=self.folder/"correlacao_presidente_senado_v2"/"robustez_inversoes_2026"/"checkpoints"
        directory.mkdir(parents=True)
        original_hash="a"*64
        v2="b"*64
        comp="c"*64
        data={"source":original_hash,
              "groups":[list(self.first)+self.a,list(self.second)+self.b]}
        shard=directory/"bucket-0000.json"
        shard.write_text(json.dumps(data),encoding="utf-8")
        (directory/"state.json").write_text(json.dumps({
            "identity":{"version":"senate-robustness-2026-v1",
                        "fingerprint":"f"*64,"v2_sha256":v2,
                        "comparison_sha256":comp},
            "completed":{"0":{"source":original_hash,"sha256":sha256(shard)}}}),
            encoding="utf-8")
        (self.folder/"state.json").write_text(json.dumps({
            "completed":{"0":{"candidate_sha256":original_hash}}}),
            encoding="utf-8")
        result,buckets=drv.read_cache(self.folder,"f"*64,
                                     {self.case:self.ref},v2,comp)
        self.assertEqual(buckets,1)
        self.assertEqual(sum(x[0] for x in result.values()),4)
        shard.write_text("{}",encoding="utf-8")
        with self.assertRaises(RuntimeError):
            drv.read_cache(self.folder,"f"*64,{self.case:self.ref},v2,comp)

    def test_complete_report_without_original_bu_scan(self):
        grouped={self.first:self.a,self.second:self.b}
        with (patch.object(drv,"find_folder",return_value=(self.folder,"f"*64)),
              patch.object(drv,"load_cases",return_value=(
                  {self.case:self.ref},"b"*64,"c"*64)),
              patch.object(drv,"read_cache",return_value=(grouped,2))):
            report=drv.run(Path("."))
        self.assertEqual(report["pares"],1)
        self.assertEqual(report["checkpoints_sha_verificados"],2)
        self.assertEqual(report["files"]["zonas"]["rows"],2)
        self.assertEqual(report["files"]["top5"]["rows"],2)
        for filedata in report["files"].values():
            self.assertEqual(sha256(Path(filedata["path"])),filedata["sha256"])

    def test_wrong_reference_rejected(self):
        bad=dict(self.ref,adjusted=-self.adjusted)
        with self.assertRaises(RuntimeError):
            drv.analyze_pair(self.case,[(self.first,self.a),
                                        (self.second,self.b)],bad)


if __name__=="__main__":
    unittest.main()
