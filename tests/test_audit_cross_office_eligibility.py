"""Testes offline da auditoria de elegibilidade entre cargos."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import tempfile
import unittest

import audit_cross_office_eligibility as e
from audit_cross_office_totals import digest


class EligibilityTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.analysis = self.root / "analysis"
        self.base = self.analysis / "entre_cargos" / "test"
        self.base.mkdir(parents=True)
        self.matrix = self.base / "secoes_por_cargo.csv"
        self.fields = ["UF", "municipio", "zona", "secao", "turno",
                       "tem_presidente", "tem_governador", "tem_senado",
                       "votos_presidente", "votos_governador", "votos_senado"]
        self.rows = [
            ["AC", "1", "1", "1", "1", "1", "1", "1", "7", "7", "14"],
            ["AC", "1", "1", "2", "1", "1", "1", "1", "9", "7", "14"],
            ["RJ", "2", "1", "3", "1", "1", "1", "1", "7", "7", "13"],
            ["ZZ", "3", "1", "4", "1", "1", "0", "0", "4", "", ""],
        ]
        self.write()
        self.fingerprint = "f" * 64
        (self.analysis / "reconciliacao_bu_secao.summary.json").write_text(
            json.dumps({"fingerprint": self.fingerprint}), encoding="utf-8")
        self.summary_path = self.base / "summary.json"
        self.write_summary()

    def write(self):
        with self.matrix.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(self.fields)
            writer.writerows(self.rows)

    def write_summary(self):
        self.summary_path.write_text(json.dumps({
            "status": "concluido", "source_fingerprint": self.fingerprint,
            "matrix": str(self.matrix), "matrix_sha256": digest(self.matrix),
            "distinct_sections": 4, "paired_president_governor_sections": 3,
            "president_governor_totals_unequal": 1,
        }), encoding="utf-8")

    def test_invariants_and_location_breakdown(self):
        result = e.run(self.root)
        st = result["totals"]
        self.assertEqual(st["secoes"], 4)
        self.assertEqual(st["presidente_maior_governador"], 1)
        self.assertEqual(st["governador_maior_presidente"], 0)
        self.assertEqual(st["votos_presidente_excedentes_nos_pares"], 2)
        self.assertEqual(st["presidente_sem_governador"], 1)
        self.assertEqual(st["votos_presidente_sem_governador"], 4)
        self.assertEqual(st["governador_senado_pareados"], 3)
        self.assertEqual(st["senado_igual_dobro_governador"], 2)
        self.assertEqual(st["senado_diferente_dobro_governador"], 1)
        self.assertEqual(st["soma_desvio_senado_menos_dobro_governador"], -1)
        self.assertEqual(len(result["amostra_quebras"]), 1)
        self.assertTrue((self.base / "auditoria_elegibilidade" /
                         "por_uf_turno.csv").exists())

    def test_reject_bad_hash(self):
        self.matrix.write_text("invalid\n", encoding="utf-8")
        with self.assertRaises(RuntimeError):
            e.run(self.root)

    def test_reject_missing_presence_flag(self):
        self.rows[0][7] = "0"
        self.write()
        self.write_summary()
        with self.assertRaises(RuntimeError):
            e.run(self.root)

    def test_reject_inconsistent_counts(self):
        self.summary_path.write_text(json.dumps({
            "status": "concluido", "source_fingerprint": self.fingerprint,
            "matrix": str(self.matrix), "matrix_sha256": digest(self.matrix),
            "distinct_sections": 5, "paired_president_governor_sections": 3,
            "president_governor_totals_unequal": 1,
        }), encoding="utf-8")
        with self.assertRaises(RuntimeError):
            e.run(self.root)


if __name__ == "__main__":
    unittest.main()
