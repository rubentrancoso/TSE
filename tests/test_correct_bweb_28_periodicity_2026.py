"""Fase 5H: correcoes por secao do candidato 28 e curvas nacionais 2026."""
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import audit_bweb_candidate_28_2026 as auditL
import correct_bweb_28_periodicity_2026 as mod
from extract_bweb_received_2026 import HEAD, VERSION
from reconcile_stream import sha256


class Correct28Test(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.base=self.root/"analysis"/"periodicidade_bweb_2026"
        self.base.mkdir(parents=True)
        directory=self.root/"raw"/"bu"/"AC"
        directory.mkdir(parents=True)
        archive=directory/"test--bweb_1t_AC_20261004.zip"
        buffer=io.StringIO()
        writer=csv.writer(buffer,delimiter=";")
        writer.writerow(["NR_TURNO","SG_UF","DS_CARGO_PERGUNTA",
                         "NR_VOTAVEL","QT_VOTOS","CD_MUNICIPIO",
                         "NR_ZONA","NR_SECAO"])
        writer.writerows([
            ("1","AC","Presidente","28",3,"1104","5","1"),
            ("1","AC","Presidente","28",2,"1104","5","2"),
            ("1","AC","Presidente","13",100,"1104","5","1"),
            ("1","AC","Presidente","22",50,"1104","5","1"),
            ("2","AC","Presidente","28",1000,"1104","5","1"),
            ("1","AC","Senador","28",1000,"1104","5","1")
        ])
        with zipfile.ZipFile(archive,"w") as f:
            f.writestr("bweb_1t_AC.csv",buffer.getvalue().encode("latin-1"))
        digest=sha256(archive)
        Path(str(archive)+".meta.json").write_text(
            json.dumps({"sha256":digest}),encoding="utf-8")
        self.archive=archive

        rows=[
            ("AC","1104","5","1","1","04/10/2026 18:25:49",
             "2026-10-04 18:25","a"*64,155,155,100,50,0,0),
            ("AC","1104","5","2","1","04/10/2026 18:26:32",
             "2026-10-04 18:26","a"*64,155,155,60,90,0,0)
        ]
        shard=self.base/"received-AC.csv"
        with shard.open("w",encoding="utf-8",newline="") as f:
            w=csv.writer(f,delimiter=";")
            w.writerow(HEAD)
            w.writerows(rows)
        (self.base/"summary.json").write_text(json.dumps({
            "version":VERSION,"sections":2,
            "ufs":{"AC":{"sections":2,"shard_sha256":sha256(shard)}}}),
            encoding="utf-8")

        columns=["UF","diferenca_validos","diferenca_demais",
                 "diferenca_13","diferenca_22"]
        reference=self.base/"phase5f_reconciliation_by_uf_2026.csv"
        with reference.open("w",encoding="utf-8",newline="") as f:
            w=csv.DictWriter(f,fieldnames=columns,delimiter=";")
            w.writeheader()
            w.writerow({"UF":"AC","diferenca_validos":5,
                       "diferenca_demais":5,"diferenca_13":0,
                       "diferenca_22":0})
        (self.base/"phase5f_reconciliation_2026_summary.json").write_text(
            json.dumps({"by_uf_sha256":sha256(reference)}),encoding="utf-8")
        self.lpath=self.base/"phase5g_nr28_reconciliation_2026_summary.json"
        self.lpath.write_text(json.dumps({
            "status":"CONCILIACAO_COMPLETA_NR_28",
            "ufs_reconciled":1,"difference_after_excluding_nr_28":0,
            "sources_by_uf":{"AC":{"votos_28":5,"sha256":digest}}
        }),encoding="utf-8")
        self.patch_ufs=patch.object(mod,"UFs",("AC",))
        self.patch_lufs=patch.object(auditL,"UFs",("AC",))
        self.patch_expected=patch.object(mod,"EXPECTED",
                               {"valid":305,"13":160,"22":140,"number28":5})
        self.patch_ufs.start()
        self.patch_lufs.start()
        self.patch_expected.start()
        self.addCleanup(self.patch_ufs.stop)
        self.addCleanup(self.patch_lufs.stop)
        self.addCleanup(self.patch_expected.stop)

    def test_scan_individual_sections(self):
        observed=mod.extract_nr28(self.archive,"AC")
        self.assertEqual(observed,{("AC","1104","5","1"):3,
                                  ("AC","1104","5","2"):2})

    def test_full_reconciliation_and_curves(self):
        report=mod.run(self.root,minute_simulations=100,second_simulations=100)
        self.assertEqual(report["status"],"VALIDOS_PRESIDENCIAIS_CORRIGIDOS")
        self.assertEqual(report["corrected_totals"]["valid"],305)
        self.assertEqual(report["corrected_totals"]["nr28"],5)
        self.assertEqual(report["corrected_totals"]["sections"],2)
        self.assertEqual(report["difference_valid_vs_official"],0)
        self.assertEqual(report["corrected_minute_periodicity"]["status"],
                         "AMOSTRA_INSUFICIENTE")
        self.assertTrue((self.base/"phase5h_minute_corrected_2026.csv").exists())
        self.assertEqual(len(report["corrected_block_periodicities"]),3)
        self.assertTrue(all(row["periodicity"]["status"]=="AMOSTRA_INSUFICIENTE"
               for row in report["corrected_block_periodicities"].values()))

    def test_restarts_without_reopening_zip(self):
        first=mod.run(self.root,100,100)
        with patch.object(mod,"discover_archive",side_effect=RuntimeError("re-open ZIP!")):
            second=mod.run(self.root,100,100)
        self.assertEqual(first["corrected_totals"],second["corrected_totals"])
        self.assertEqual(first["corrected_minutes_sha256"],
                         second["corrected_minutes_sha256"])

    def test_missing_number_28_section_is_not_ignored(self):
        filepath=self.base/"received-AC.csv"
        content=filepath.read_text(encoding="utf-8")
        filepath.write_text(content.replace(";2;1;", ";3;1;"),
                            encoding="utf-8")
        # Nao aceitar cache BU diferente do SHA selado.
        with self.assertRaises(RuntimeError):
            mod.run(self.root,100,100)

    def test_rejects_invalid_source_l(self):
        original=json.loads(self.lpath.read_text("utf-8"))
        original["status"]="RESTAM_DIVERGENCIAS"
        self.lpath.write_text(json.dumps(original),encoding="utf-8")
        with self.assertRaises(RuntimeError):
            mod.run(self.root,100,100)


if __name__=="__main__":
    unittest.main()
