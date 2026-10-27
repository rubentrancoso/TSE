"""Testes da variacao de parametros em serie BWEB 2026 ja materializada."""
import csv
import json
from pathlib import Path
import tempfile
import unittest

import sensitivity_bweb_periodicity_2026 as mod
from reconcile_stream import sha256


class Sensitivity2026Test(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.base=self.root/"analysis"/"periodicidade_bweb_2026"
        self.base.mkdir(parents=True)
        self.series=self.base/"serie_2026_por_minuto.csv"
        fields=["brt","sections","minutes","d_sections","d_valid",
                "d_flavio","d_lula","batch_share_pct","cum_share_pct"]
        with self.series.open("w",encoding="utf-8",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=fields,delimiter=";")
            writer.writeheader()
            fcount=lcount=0
            for i in range(80):
                v=30000
                f=16000 if i%11 else 4000
                l=v-f
                fcount+=f;lcount+=l
                writer.writerow({"brt":f"2026-10-04 {17+i//60:02d}:{i%60:02d}",
                    "sections":i+1,"minutes":i,"d_sections":1,"d_valid":v,
                    "d_flavio":f,"d_lula":l,
                    "batch_share_pct":100*f/v,
                    "cum_share_pct":100*fcount/((i+1)*v)})
        self.report={
            "status":"APURACAO_POR_MINUTO_ANALISADA",
            "minute_bins":80,
            "timeline_sha256":sha256(self.series),
            "match_and_coverage":{
                "sections_timestamped":80,
                "total_in_timed_sections":{"valid":80*30000}
            }
        }
        (self.base/"phase5c_summary.json").write_text(
            json.dumps(self.report),encoding="utf-8")

    def test_recheck_checksum_and_counts(self):
        data,original=mod.read_verified_series(self.base)
        self.assertEqual(len(data),80)
        self.assertEqual(data[-1]["sections"],80)
        self.assertEqual(original["minute_bins"],80)
        with self.series.open("a",encoding="utf-8") as f:
            f.write("tampered\n")
        with self.assertRaises(RuntimeError):
            mod.read_verified_series(self.base)

    def test_run_deterministic_without_2026_zip_reopen(self):
        out=mod.run(self.root,permutations_count=100)
        self.assertEqual(out["status"],"EXPLORATORIO_CONCLUIDO")
        self.assertEqual(out["parameter_grid"],6)
        self.assertEqual(out["minute_bins"],80)
        self.assertTrue(all(entry["periodicity"]["r2"]>=0
                            for entry in out["results"]))
        second=mod.run(self.root,permutations_count=100)
        self.assertEqual(out,second)
        self.assertTrue((self.base/"phase5d_sensitivity_2026_summary.json").is_file())


    def test_corrected_mode_sha_and_national_totals(self):
        import shutil
        corrected=self.base/"phase5h_minute_corrected_2026.csv"
        shutil.copyfile(self.series,corrected)
        report={
            "status":"VALIDOS_PRESIDENCIAIS_CORRIGIDOS",
            "difference_valid_vs_official":0,
            "distinct_minutes":80,
            "initial_sections":80,
            "corrected_totals":{"valid":80*30000},
            "corrected_minutes_sha256":sha256(corrected)
        }
        (self.base/"phase5h_corrected_periodicity_2026_summary.json").write_text(
            json.dumps(report),encoding="utf-8")
        rows,_=mod.read_verified_series(self.base,corrected=True)
        self.assertEqual(len(rows),80)
        result=mod.run(self.root,permutations_count=100,corrected=True)
        self.assertEqual(result["source_mode"],"CORRIGIDO_NR28")
        self.assertEqual(result["parameter_grid"],6)
        self.assertTrue((self.base/"phase5d_sensitivity_corrected_2026_summary.json").is_file())
        with corrected.open("a",encoding="utf-8") as f:
            f.write("tampered\\n")
        with self.assertRaises(RuntimeError):
            mod.read_verified_series(self.base,corrected=True)

    def test_not_enough_iterations(self):
        with self.assertRaises(ValueError):
            mod.run(self.root,permutations_count=99)


if __name__=="__main__":
    unittest.main()
