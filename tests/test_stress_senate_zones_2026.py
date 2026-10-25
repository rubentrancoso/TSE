"""Testes sinteticos do stress conjunto de zonas de 2026."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import stress_senate_zones_2026 as stage
from senate_zone_stress_stats_2026 import stress
from senate_robustness_stats_2026 import centered, pearson, sum_cov
from reconcile_stream import sha256


def moments(x,y):
    return [len(x),sum(x),sum(y),sum(v*v for v in x),
            sum(v*v for v in y),sum(a*b for a,b in zip(x,y))]


def fixture():
    x=[0.1,0.2,0.3,0.4]
    out=[]
    for zone in range(1,9):
        y=x if zone<=5 else list(reversed(x))
        key=("AC","101",str(zone),"1","13","170")
        out.append((key,moments(x,y)))
    r=pearson(sum_cov(centered(v) for _,v in out))
    return out,{"n":32,"z":8,"adjusted":r}


class StressZones2026Test(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.folder=self.root/"analysis"/"entre_cargos"/"fixture"
        self.folder.mkdir(parents=True)
        self.key=("AC","13","170")
        self.groups,self.ref=fixture()

    def test_multiple_zone_removal_can_flip_sign(self):
        result,chosen=stress(self.key,self.groups,self.ref,150)
        self.assertEqual(result["zonas_n2"],8)
        self.assertGreater(result["r_original"],0)
        self.assertEqual(result["mudou_sinal_top5_cov_abs"],1)
        self.assertLess(result["r_sem_top5_cov_abs"],0)
        self.assertEqual(len(chosen),10)
        self.assertEqual(result["rand5_replicacoes"],150)
        self.assertGreaterEqual(result["rand5_pct_mesmo_sinal"],0)
        self.assertLessEqual(result["rand5_pct_mesmo_sinal"],100)
        self.assertEqual(result["pct_secoes_retiradas_top5_cov_abs"],62.5)

    def test_permutation_order_does_not_change_result(self):
        first,chosen=stress(self.key,self.groups,self.ref,100)
        second,again=stress(self.key,list(reversed(self.groups)),self.ref,100)
        self.assertEqual(first,second)
        self.assertEqual(chosen,again)

    def test_reference_and_sample_size_checked(self):
        with self.assertRaises(RuntimeError):
            stress(self.key,self.groups,{**self.ref,"n":31},100)
        with self.assertRaises(RuntimeError):
            stress(self.key,self.groups,{**self.ref,"adjusted":-.25},100)
        with self.assertRaises(ValueError):
            stress(self.key,self.groups,self.ref,20)
        with self.assertRaises(RuntimeError):
            stress(self.key,self.groups[:6],
                   {"n":24,"z":6,"adjusted":.1},100)

    def test_generate_report_from_verified_checkpoint_reader(self):
        one={k:m for k,m in self.groups}
        with (patch.object(stage,"find_folder",
                           return_value=(self.folder,"f"*64)),
              patch.object(stage,"load_cases",
                           return_value=({self.key:self.ref},"b"*64,"c"*64)),
              patch.object(stage,"read_cache",
                           return_value=(one,2))):
            report=stage.run(self.root,replicacoes=100)
        self.assertEqual(report["pares"],1)
        self.assertEqual(report["checkpoints_verificados"],2)
        self.assertEqual(report["files"]["top5"]["rows"],10)
        for metadata in report["files"].values():
            self.assertEqual(sha256(Path(metadata["path"])),
                             metadata["sha256"])


if __name__=="__main__":
    unittest.main()
