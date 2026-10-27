"""Testes offline da periodicidade nacional do primeiro turno de 2026."""
import math
import unittest

from analyze_periodicity_2026 import (
    SOURCE, read_csv, batches, prepare, find_valleys,
    templates, maximum_periodic_r2, analyze, Mulberry32,
    permutations,
)


class Periodicity2026Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.observed=read_csv(SOURCE)
        cls.batches=batches(cls.observed)
        cls.selected=prepare(cls.batches)

    def test_data_2026_trace_reconstructed(self):
        self.assertEqual(len(self.observed),193)
        self.assertEqual(len(self.batches),192)
        self.assertEqual(len(self.selected),140)
        self.assertEqual(self.observed[-1]["sections"],499248)
        self.assertEqual(self.observed[-1]["valid"],119300788)

    def test_valley_count_and_period_peak(self):
        valleys=find_valleys(self.selected)
        self.assertEqual(len(valleys),4)
        y=[r["residual_pp"] for r in self.selected]
        peak=maximum_periodic_r2(y,templates(self.selected))
        self.assertEqual(peak["axis"],"minutes")
        self.assertAlmostEqual(peak["period"],2.518880306,places=5)
        self.assertAlmostEqual(peak["r2"],0.07781158,places=5)

    def test_deterministic_nulll_and_no_fraud_claim(self):
        first,_=analyze(self.observed,replications=100)
        again,_=analyze(self.observed,replications=100)
        self.assertEqual(first,again)
        for value in first["max_frequency_scan_corrected_mc_p"].values():
            self.assertGreater(value,0)
            self.assertLessEqual(value,1)
        self.assertIn("nao e veredito de fraude",
                      " ".join(first["limitations"]))

    def test_detects_injected_sinusoidal_pattern(self):
        artificial=[{"sections":10000+i*1000,"minutes":i*3.0}
                    for i in range(150)]
        response=[math.sin(2*math.pi*r["sections"]/10000)
                  for r in artificial]
        peak=maximum_periodic_r2(response,templates(artificial))
        self.assertGreater(peak["r2"],0.9)

    def test_rng_and_shuffle_deterministic(self):
        y=list(range(20))
        parts=[list(range(0,10)),list(range(10,20))]
        a=permutations(y,parts,Mulberry32(32),"individual")
        b=permutations(y,parts,Mulberry32(32),"individual")
        self.assertEqual(a,b)
        self.assertCountEqual(a[:10],y[:10])
        self.assertCountEqual(a[10:],y[10:])
        self.assertNotEqual(a,y)
        c=permutations(y,parts,Mulberry32(32),"blocks")
        self.assertCountEqual(c,y)

    def test_invalid_parameters(self):
        with self.assertRaises(ValueError):
            prepare(self.batches,width=8)
        with self.assertRaises(ValueError):
            analyze(self.observed,replications=99)


if __name__=="__main__":
    unittest.main()
