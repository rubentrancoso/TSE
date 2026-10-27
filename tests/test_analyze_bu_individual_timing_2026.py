"""Testes sinteticos da analise por BU individual, apenas 2026."""
import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import analyze_bu_individual_timing_2026 as phase
from reconcile_stream import sha256


class BU2026TimingTest(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base=Path(tmp.name)
        self.input=self.base/"bucket.csv"
        self.output=self.base/"section.csv"
        with self.input.open("w",encoding="utf-8",newline="") as f:
            w=csv.writer(f,delimiter=";")
            w.writerow(["UF","municipio","zona","secao","turno",
                        "cargo","votavel","votos_BU"])
            for row in [
                ("AC","1104","5","1","1","1","13","100"),
                ("AC","1104","5","1","1","1","22","50"),
                ("AC","1104","5","1","1","1","95","5"),
                ("AC","1104","5","1","1","1","96","3"),
                ("AC","1104","5","1","1","3","50","160"),
                ("AC","1104","5","2","1","1","13","120"),
                ("AC","1104","5","2","1","1","22","20"),
                ("AC","1104","5","2","1","1","95","4"),
                ("AC","1104","5","2","1","1","96","1"),
            ]:
                w.writerow(row)

    def test_bucket_presidential_reconstruction(self):
        report=phase.extract_president_bucket(self.input,self.output)
        self.assertEqual(report["sections"],2)
        self.assertEqual(report["totals"]["pres_valid"],290)
        self.assertEqual(report["totals"]["pres_total"],303)
        with self.output.open(encoding="utf-8") as f:
            data=list(csv.DictReader(f,delimiter=";"))
        self.assertEqual(data[0]["votos_validos_pres"],"150")
        self.assertEqual(data[0]["votos_totais_pres"],"158")
        self.assertEqual(data[1]["votos_13"],"120")
        self.assertEqual(data[1]["nulos"],"1")

    def test_ea16_burst_blocked(self):
        doc={"abr":[{"cd":"ac","mu":[{"cd":"1104","zon":[
          {"cd":"5","sec":[
            {"ns":"1","da":"04/10/2026","ha":"21:08:15"},
            {"ns":"2","da":"04/10/2026","ha":"21:08:17"},
            {"ns":"3","nsp":"1","da":"04/10/2026","ha":"21:08:18"}
          ]}
        ]}]}]}]}
        file=self.base/"ac-p003220-cs.json"
        file.write_text(json.dumps(doc),encoding="utf-8")
        expected={"sources":[{"uf":"AC","sha256":sha256(file)}]}
        with patch.object(phase,"UFs",("AC",)):
            times,quality=phase.load_ea16(self.base,expected)
        self.assertEqual(len(times),2)
        self.assertEqual(quality["sections"],2)
        self.assertEqual(quality["sections_in_uf_bursts_under_5_min"],2)
        self.assertEqual(quality["status"],
                         "EA16_CONCENTRACAO_EM_MASSA_INCOMPATIVEL_COM_ORDEM_INDIVIDUAL")

    def test_join_rejects_duplicate_bu_and_reports_missing_ea16(self):
        phase.extract_president_bucket(self.input,self.output)
        k=phase.key("AC","1104","5","1","1")
        timing={k:{"da":"04/10/2026","ha":"21:08:15",
                   "time":"2026-10-04T21:08:15"}}
        res=phase.merge_sections([self.output],timing,
                                 self.base/"merged.csv")
        self.assertEqual(res["bu_pres_sections"],2)
        self.assertEqual(res["matched_ea16"],1)
        self.assertEqual(res["without_ea16"],1)
        with self.assertRaises(RuntimeError):
            phase.merge_sections([self.output,self.output],timing,
                                 self.base/"duplicate.csv")

    def test_script_end_to_end_with_verified_fixture(self):
        root=self.base/"urnas"
        repo=self.base/"repo"
        local=repo/"data"/"forensics"/"analysis"
        local.mkdir(parents=True)
        (local/"phase3_arrivals_summary.json").write_text(
            json.dumps({"principal_sections":2,"timestamp_coverage_pct":100,
                        "ufs":{},"sources":[]}),encoding="utf-8")
        srcinfo={"source_fingerprint":"test-fingerprint"}
        with (patch.object(phase,"source",return_value=(
            root/"analysis"/"entre_cargos"/"fixture",srcinfo,[self.input])),
              patch.object(phase,"timestamp_sources",return_value=None)):
            result=phase.run(root,repo)
            second=phase.run(root,repo)
        self.assertEqual(result["status"],
                         "CRONOLOGIA_INVALIDA_NAO_REALIZAR_PERIODOGRAMA")
        self.assertEqual(result["matching"]["bu_pres_sections"],2)
        self.assertEqual(result["matching"]["matched_ea16"],0)
        self.assertEqual(result["bu_buckets_sha_verified"],1)
        self.assertEqual(result["matching"]["csv_sha256"],
                         second["matching"]["csv_sha256"])

    def test_section_key_normalization(self):
        self.assertEqual(phase.key("ac","01104","0005","0001","01"),
                         ("AC","1104","5","1","1"))
        with self.assertRaises(ValueError):
            phase.key("AC","","5","1")


if __name__=="__main__":
    unittest.main()
