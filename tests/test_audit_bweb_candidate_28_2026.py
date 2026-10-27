"""Testes sinteticos 2026 para identificar NR_VOTAVEL=28 por UF no BWEB."""
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import audit_bweb_candidate_28_2026 as target
from reconcile_stream import sha256


class Audit28Test(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        archive_folder=self.root/"raw"/"bu"/"AC"
        archive_folder.mkdir(parents=True)
        self.archive=archive_folder/"test--bweb_1t_AC_20261004.zip"
        csv_buf=io.StringIO()
        w=csv.writer(csv_buf,delimiter=";")
        w.writerow(("NR_TURNO","SG_UF","DS_CARGO_PERGUNTA","NR_VOTAVEL",
                    "QT_VOTOS","DS_TIPO_VOTAVEL","CD_MUNICIPIO",
                    "NR_ZONA","NR_SECAO"))
        w.writerows([
            (1,"AC","Presidente","13",100,"Nominal","1104","5","1"),
            (1,"AC","Presidente","28",3,"Nominal","1104","5","1"),
            (1,"AC","Presidente","28",2,"Nominal","1104","5","2"),
            (1,"AC","Presidente","28",0,"Nominal","1104","5","3"),
            (1,"AC","Presidente","22",150,"Nominal","1104","5","2"),
            (1,"AC","Senador","28",900,"Nominal","1104","5","1"),
            (2,"AC","Presidente","28",1000,"Nominal","1104","5","1"),
        ])
        with zipfile.ZipFile(self.archive,"w") as z:
            z.writestr("bweb_1t_AC.csv",csv_buf.getvalue().encode("latin-1"))
        Path(str(self.archive)+".meta.json").write_text(
            json.dumps({"sha256":sha256(self.archive)}),encoding="utf-8")
        self.folder=self.root/"analysis"/"periodicidade_bweb_2026"
        self.folder.mkdir(parents=True)
        self.kpath=self.folder/"phase5f_reconciliation_by_uf_2026.csv"
        with self.kpath.open("w",encoding="utf-8",newline="") as f:
            w=csv.DictWriter(f,fieldnames=["UF","diferenca_validos",
                 "diferenca_demais","diferenca_13","diferenca_22"],delimiter=";")
            w.writeheader()
            w.writerow({"UF":"AC","diferenca_validos":5,
                  "diferenca_demais":5,"diferenca_13":0,"diferenca_22":0})
        (self.folder/"phase5f_reconciliation_2026_summary.json").write_text(
            json.dumps({"by_uf_sha256":sha256(self.kpath)}),encoding="utf-8")

    def test_filter_first_turn_president_and_count_28(self):
        data=target.scan_28(self.archive,"AC")
        self.assertEqual(data["votos_28"],5)
        self.assertEqual(data["secoes_com_28"],2)
        self.assertEqual(data["registros_28"],3)
        self.assertEqual(data["DS_TIPO_VOTAVEL_28"],{"Nominal":5})

    def test_reconciles_per_uf_and_reports_provenance(self):
        with patch.object(target,"UFs",("AC",)):
            report=target.run(self.root)
        self.assertEqual(report["status"],"CONCILIACAO_COMPLETA_NR_28")
        self.assertEqual(report["votes_28_total_BWEB"],5)
        self.assertEqual(report["difference_after_excluding_nr_28"],0)
        self.assertEqual(report["ufs_reconciled"],1)
        self.assertTrue((self.folder/"phase5g_nr28_by_uf_2026.csv").exists())

    def test_detects_unexplained_difference_without_hiding(self):
        fields=["UF","diferenca_validos","diferenca_demais",
                "diferenca_13","diferenca_22"]
        with self.kpath.open("w",encoding="utf-8",newline="") as f:
            w=csv.DictWriter(f,fieldnames=fields,delimiter=";")
            w.writeheader()
            w.writerow({"UF":"AC","diferenca_validos":6,
                       "diferenca_demais":6,"diferenca_13":0,
                       "diferenca_22":0})
        (self.folder/"phase5f_reconciliation_2026_summary.json").write_text(
            json.dumps({"by_uf_sha256":sha256(self.kpath)}),encoding="utf-8")
        with patch.object(target,"UFs",("AC",)):
            out=target.run(self.root)
        self.assertEqual(out["status"],"RESTAM_DIVERGENCIAS")
        self.assertEqual(out["difference_after_excluding_nr_28"],1)

    def test_k_sha_validation_and_bweb_hash_detection(self):
        self.kpath.write_text("invalid change\n",encoding="utf-8")
        with patch.object(target,"UFs",("AC",)):
            with self.assertRaises(RuntimeError):
                target.read_k_report(self.folder)
        Path(str(self.archive)+".meta.json").write_text(
            json.dumps({"sha256":"0"*64}),encoding="utf-8")
        with self.assertRaises(RuntimeError):
            target.discover_archive(self.root,"AC")


if __name__=="__main__":
    unittest.main()
