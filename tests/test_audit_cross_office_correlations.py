"""Testes sinteticos do diagnostico conjunto Governador/Senado."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import tempfile
import unittest

import audit_cross_office_correlations as a
from reconcile_stream import sha256


class CombinedAuditTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.base = self.root / "analysis"
        self.folder = self.base / "entre_cargos" / "fixture"
        self.folder.mkdir(parents=True)
        self.fp = "b" * 64
        (self.base / "reconciliacao_bu_secao.summary.json").write_text(
            json.dumps({"fingerprint": self.fp}), encoding="utf-8")

        self.gov_path = self.folder / "correlacao_presidente_governador"
        self.sen_path = self.folder / "correlacao_presidente_senado"
        self.gov_path.mkdir()
        self.sen_path.mkdir()
        self.gov_csv = self.gov_path / "pares_por_uf.csv"
        self.sen_csv = self.sen_path / "pares_por_uf.csv"

        self.gov_header = [
            "UF", "turno", "presidente", "governador",
            "secoes_pareadas_validas", "correlacao_bruta_pearson",
            "correlacao_dentro_municipio_zona",
            "grupos_com_variacao_interna", "grupo_geo", "nota"]
        self.sen_header = [
            "UF", "turno", "presidente", "senador",
            "secoes_com_dois_cargos", "correlacao_bruta_pearson",
            "correlacao_dentro_municipio_zona",
            "zonas_com_variacao", "votos_senador", "interpretacao"]
        self.gov_rows = [
            ["AC", "1", "22", "10", "2000", "0.60", "-0.35", "25", "municipio+zona", ""],
            ["AC", "1", "13", "10", "2000", "-0.60", "0.35", "25", "municipio+zona", ""],
            ["AC", "1", "22", "55", "2000", "0.80", "0.70", "25", "municipio+zona", ""],
            ["AC", "1", "13", "55", "2000", "0.05", "-0.02", "25", "municipio+zona", ""],
        ]
        self.sen_rows = [
            ["AC", "1", "22", "170", "2000", "0.60", "-0.35", "25", "10000", ""],
            ["AC", "1", "13", "170", "2000", "-0.60", "0.35", "25", "10000", ""],
            ["AC", "1", "22", "171", "2000", "0.80", "0.70", "25", "50", ""],
            ["AC", "1", "13", "171", "2000", "0.05", "-0.02", "25", "50", ""],
        ]
        self._write(self.gov_csv, self.gov_header, self.gov_rows)
        self._write(self.sen_csv, self.sen_header, self.sen_rows)
        self.gov_meta = {
            "fingerprint": self.fp, "status": "DESCRITIVO_CONCLUIDO",
            "turno": "1", "presidente_top2": ["22", "13"],
            "governador_top_por_uf": {"AC": ["10", "55"]},
            "pairs_compared": 4, "correlation_csv": str(self.gov_csv),
            "correlation_csv_sha256": sha256(self.gov_csv),
        }
        self.sen_meta = {
            "fingerprint": self.fp, "status": "DESCRITIVO_CONCLUIDO",
            "turno": "1", "presidente_top2": ["22", "13"],
            "senadores_por_uf": {"AC": ["170", "171"]},
            "pairs_compared": 4, "csv": str(self.sen_csv),
            "csv_sha256": sha256(self.sen_csv),
        }
        self._save_summaries()

    def _save_summaries(self):
        (self.gov_path / "summary.json").write_text(
            json.dumps(self.gov_meta), encoding="utf-8")
        (self.sen_path / "summary.json").write_text(
            json.dumps(self.sen_meta), encoding="utf-8")

    @staticmethod
    def _write(path, header, rows):
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(header)
            writer.writerows(rows)

    def test_total_8_pairs_and_separate_thresholds(self):
        result = a.run(self.root)
        self.assertEqual(result["pairs"], 8)
        gov = result["totals_by_office"]["governador"]
        sen = result["totals_by_office"]["senador"]
        self.assertEqual(gov["pares"], 4)
        self.assertEqual(gov["aptos_filtro_votos"], 4)
        self.assertEqual(gov["sinais_opostos"], 2)
        self.assertEqual(gov["mudancas_020"], 2)
        self.assertEqual(sen["pares"], 4)
        self.assertEqual(sen["aptos_comuns"], 4)
        self.assertEqual(sen["aptos_filtro_votos"], 2)
        self.assertEqual(sen["sinais_opostos"], 2)
        self.assertEqual(result["outputs"]["todos_os_pares.csv"],
                         sha256(self.folder / "diagnostico_conjunto" / "todos_os_pares.csv"))

    def test_governor_hash_change_is_rejected(self):
        self.gov_csv.write_text("invalid\n", encoding="utf-8")
        with self.assertRaises(RuntimeError):
            a.run(self.root)

    def test_senator_hash_change_is_rejected(self):
        self.sen_csv.write_text("invalid\n", encoding="utf-8")
        with self.assertRaises(RuntimeError):
            a.run(self.root)

    def test_missing_senator_pair_rejected(self):
        self.sen_rows.pop()
        self._write(self.sen_csv, self.sen_header, self.sen_rows)
        self.sen_meta["csv_sha256"] = sha256(self.sen_csv)
        self._save_summaries()
        with self.assertRaises(RuntimeError):
            a.run(self.root)

    def test_mismatched_fingerprint_rejected(self):
        self.sen_meta["fingerprint"] = "a" * 64
        self._save_summaries()
        with self.assertRaises(RuntimeError):
            a.run(self.root)

    def test_invalid_pearson_rejected(self):
        self.gov_rows[0][5] = "nan"
        self._write(self.gov_csv, self.gov_header, self.gov_rows)
        self.gov_meta["correlation_csv_sha256"] = sha256(self.gov_csv)
        self._save_summaries()
        with self.assertRaises(RuntimeError):
            a.run(self.root)

    def test_governor_denominator_not_identified_as_senate(self):
        result = a.run(self.root)
        self.assertIn("denominador", result["interpretation"])
        self.assertIn("Senado", result["interpretation"])
        self.assertIn("exploratorio", result["interpretation"])


if __name__ == "__main__":
    unittest.main()
