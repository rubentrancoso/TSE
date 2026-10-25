"""Testes sinteticos de comparacao de ajuste zonal v1/v2."""
from __future__ import annotations
import csv
import json
from pathlib import Path
import tempfile
import unittest

import compare_senate_geo_versions_2026 as comparison
from reconcile_stream import sha256


class CompareSenateGeoTest(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.fp="c"*64
        base=self.root/"analysis"
        base.mkdir()
        (base/"reconciliacao_bu_secao.summary.json").write_text(
            json.dumps({"fingerprint":self.fp}),encoding="utf-8")
        self.folder=base/"entre_cargos"/"fixture"
        self.old=self.folder/"correlacao_presidente_senado"
        self.new=self.folder/"correlacao_presidente_senado_v2"
        self.old.mkdir(parents=True)
        self.new.mkdir(parents=True)
        self.rows=[
            ["AC","1","13","170","1500","0.3","-0.3","30","10000",""],
            ["AC","1","22","170","1500","-0.3","0.3","30","10000",""],
        ]
        self.write(self.old,"cross-office-senate-v1",self.rows)
        second=[list(x) for x in self.rows]
        second[0][6]="0.2"  # inversao desaparece
        second[1][6]="-0.3" # aparece outra inversao
        self.write(self.new,"cross-office-senate-v2",second)

    def write(self, path,version,records):
        csvpath=path/"pares_por_uf.csv"
        with csvpath.open("w",newline="",encoding="utf-8") as f:
            w=csv.writer(f,delimiter=";")
            w.writerow(["UF","turno","presidente","senador",
                        "secoes_com_dois_cargos","correlacao_bruta_pearson",
                        "correlacao_dentro_municipio_zona",
                        "zonas_com_variacao","votos_senador","interpretacao"])
            w.writerows(records)
        (path/"summary.json").write_text(json.dumps({
            "status":"DESCRITIVO_CONCLUIDO", "version":version,
            "fingerprint":self.fp,"presidente_top2":["13","22"],
            "senadores_por_uf":{"AC":["170"]},
            "candidate_keys_checked":20,"pairs_compared":2,
            "csv":str(csvpath),"csv_sha256":sha256(csvpath)
        }),encoding="utf-8")

    def test_changed_signs_reported_with_raw_preserved(self):
        report=comparison.run(self.root)
        self.assertEqual(report["pairs_compared"],2)
        self.assertEqual(report["totals"]["v1_inversoes"],2)
        self.assertEqual(report["totals"]["v2_inversoes"],2)
        self.assertEqual(report["totals"]["persistentes"],0)
        self.assertEqual(report["totals"]["apenas_v1"],2)
        self.assertEqual(report["totals"]["novas_v2"],2)
        self.assertEqual(len(report["v2_pares_com_inversao"]),2)
        self.assertEqual(sha256(Path(report["output"])),
                         report["output_sha256"])

    def test_modified_raw_coefficient_rejected(self):
        records=[list(r) for r in self.rows]
        records[0][5]="0.1"
        self.write(self.new,"cross-office-senate-v2",records)
        with self.assertRaises(RuntimeError):
            comparison.run(self.root)

    def test_hash_mismatch_rejected(self):
        with (self.new/"pares_por_uf.csv").open("a",encoding="utf-8") as f:
            f.write("tampered\n")
        with self.assertRaises(RuntimeError):
            comparison.run(self.root)

    def test_incomplete_pair_rejected(self):
        self.write(self.new,"cross-office-senate-v2",self.rows[:1])
        with self.assertRaises(RuntimeError):
            comparison.run(self.root)


if __name__=="__main__":
    unittest.main()
