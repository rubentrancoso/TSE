"""Testes offline da auditoria de totais Presidente x Governador."""
import csv
import json
from pathlib import Path
import tempfile
import unittest

import audit_cross_office_totals as a


class AuditTotalsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.data_dir = self.root / "analysis" / "entre_cargos" / "f00"
        self.data_dir.mkdir(parents=True)
        self.matrix = self.data_dir / "secoes_por_cargo.csv"
        self.cols = [
            "UF", "municipio", "zona", "secao", "turno",
            "tem_presidente", "tem_governador", "tem_senado",
            "votos_presidente", "votos_governador", "votos_senado",
            "delta_presidente_menos_governador"]
        self.rows = [
            ["AC", "100", "1", "12", "1", "1", "1", "1", "15", "15", "30", "0"],
            ["AC", "100", "1", "13", "1", "1", "1", "1", "10", "8", "19", "2"],
            ["AC", "101", "2", "14", "1", "1", "1", "0", "20", "25", "", "-5"],
            ["ZZ", "999", "1", "15", "1", "1", "0", "0", "4", "", "", ""],
        ]
        self._write()
        summary = {
            "status": "concluido", "source_fingerprint": "f" * 64,
            "matrix": str(self.matrix), "matrix_sha256": a.digest(self.matrix),
            "distinct_sections": 4,
            "paired_president_governor_sections": 3,
            "president_governor_totals_unequal": 2,
        }
        (self.data_dir / "summary.json").write_text(json.dumps(summary))
        (self.root / "analysis" / "reconciliacao_bu_secao.summary.json"
         ).write_text(json.dumps({"fingerprint": "f" * 64}))

    def _write(self):
        with self.matrix.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(self.cols)
            writer.writerows(self.rows)

    def test_totals_and_histogram(self):
        result = a.run(self.root)
        self.assertEqual(result["total"]["secoes"], 4)
        self.assertEqual(result["total"]["presidente_governador_pareados"], 3)
        self.assertEqual(result["total"]["totais_diferentes"], 2)
        self.assertEqual(result["total"]["soma_delta"], -3)
        self.assertEqual(result["total"]["soma_abs_delta"], 7)
        self.assertEqual(result["magnitude_distribution"], {"2": 1, "3-5": 1})
        self.assertEqual(result["total"]["com_senado"], 2)
        self.assertEqual(len(result["top_cases"]), 2)

    def test_hash_rejected(self):
        self.matrix.write_text("corrompido")
        with self.assertRaises(RuntimeError):
            a.run(self.root)

    def test_expected_counters_rejected(self):
        path = self.data_dir / "summary.json"
        obj = json.loads(path.read_text())
        obj["distinct_sections"] = 5
        path.write_text(json.dumps(obj))
        with self.assertRaises(RuntimeError):
            a.run(self.root)

    def test_presence_flag_rejected(self):
        self.rows[0][5] = "0"
        self._write()
        path = self.data_dir / "summary.json"
        obj = json.loads(path.read_text())
        obj["matrix_sha256"] = a.digest(self.matrix)
        path.write_text(json.dumps(obj))
        with self.assertRaises(RuntimeError):
            a.run(self.root)


if __name__ == "__main__":
    unittest.main()
