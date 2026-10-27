"""Testes offline da origem DT_BU_RECEBIDO no BWEB de 2026."""
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import extract_bweb_received_2026 as bweb
from reconcile_stream import sha256


class BWEBReceiptTest(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        dest=self.root/"raw"/"bu"/"AC"
        dest.mkdir(parents=True)
        self.archive=dest/"123456789abc--bweb_1t_AC_051020261403.zip"
        buf=io.StringIO()
        writer=csv.writer(buf,delimiter=";")
        writer.writerow(("NR_TURNO","SG_UF","CD_MUNICIPIO",
                         "NR_ZONA","NR_SECAO","DS_CARGO_PERGUNTA",
                         "DT_BU_RECEBIDO","DS_TIPO_VOTAVEL",
                         "NR_VOTAVEL","QT_VOTOS"))
        for row in (
            ("1","AC","01104","0005","0001","Presidente",
             "04/10/2026 18:25:49","Nominal","13","100"),
            ("1","AC","01104","0005","0001","Presidente",
             "04/10/2026 18:25:49","Nominal","22","50"),
            ("1","AC","01104","0005","0002","Presidente",
             "04/10/2026 18:26:32","Nominal","13","120"),
            ("1","AC","01104","0005","0002","Presidente",
             "04/10/2026 18:26:32","Branco","95","3"),
            ("1","AC","01104","0005","0002","Presidente",
             "04/10/2026 18:26:32","Nulo","96","2"),
            ("1","AC","01104","0005","0002","Governador",
             "04/10/2026 18:26:32","Nominal","22","88"),
            ("2","AC","01104","0005","0009","Presidente",
             "25/10/2026 18:25:49","Nominal","22","60")):
            writer.writerow(row)
        with zipfile.ZipFile(self.archive,"w") as z:
            z.writestr("bweb_1t_AC.csv",buf.getvalue().encode("latin-1"))
        Path(str(self.archive)+".meta.json").write_text(json.dumps(
            {"sha256":sha256(self.archive)}),encoding="utf-8")

    def test_extract_minute_resolution_deduplicated(self):
        path,h=bweb.discover_archive(self.root,"AC")
        self.assertEqual(path,self.archive)
        data,stats=bweb.extract_archive(path,"AC",h)
        self.assertEqual(len(data),2)
        self.assertEqual(stats["repeated_rows"],3)
        self.assertEqual(stats["unique_sections"],2)
        self.assertEqual(data[("AC","1104","5","1","1")][6],
                         "2026-10-04 18:25")
        self.assertEqual(data[("AC","1104","5","2","1")][6],
                         "2026-10-04 18:26")
        self.assertEqual(data[("AC","1104","5","1","1")][8:12],
                         (150,150,100,50))
        self.assertEqual(data[("AC","1104","5","2","1")][12:14],
                         (3,2))

    def test_sha_failure_and_minute_format_validation(self):
        manifest=Path(str(self.archive)+".meta.json")
        manifest.write_text(json.dumps({"sha256":"0"*64}),encoding="utf-8")
        with self.assertRaises(RuntimeError):
            bweb.discover_archive(self.root,"AC")
        self.assertEqual(bweb.time_normalized("2026-10-04 18:25:49"),
                         "2026-10-04 18:25")
        with self.assertRaises(ValueError):
            bweb.time_normalized("2022-10-04 18:25:49")

    def test_end_to_end_shard_persisted_without_network(self):
        with patch.object(bweb,"UFs",("AC",)):
            out=bweb.run(self.root)
            cached=bweb.run(self.root)
        self.assertEqual(out["sections"],2)
        self.assertEqual(out["without_time"],0)
        self.assertEqual(cached["sections"],2)
        self.assertEqual(out["shard_count"],1)
        self.assertEqual(
            sha256(self.root/"analysis"/"periodicidade_bweb_2026"/"received-AC.csv"),
            out["ufs"]["AC"]["shard_sha256"])


if __name__=="__main__":
    unittest.main()
