"""Testes offline do resumo descritivo de correlacoes Presidente x Senado."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import tempfile
import unittest

import audit_senate_correlations as a
from reconcile_stream import sha256

COLS = [
    "UF", "turno", "presidente", "senador",
    "secoes_com_dois_cargos", "correlacao_bruta_pearson",
    "correlacao_dentro_municipio_zona", "zonas_com_variacao",
    "votos_senador", "interpretacao"]


class AuditSenateTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.folder = (self.root / "analysis" / "entre_cargos" / "sample" /
                       "correlacao_presidente_senado")
        self.folder.mkdir(parents=True)
        self.file = self.folder / "pares_por_uf.csv"
        self.data = [
            ["AC", "1", "22", "170", "2000", "0.60", "-0.35", "25", "10000", ""],
            ["AC", "1", "13", "170", "2000", "-0.60", "0.35", "25", "10000", ""],
            ["AC", "1", "22", "171", "2000", "0.80", "0.70", "25", "10000", ""],
            ["AC", "1", "13", "171", "2000", "0.05", "-0.02", "25", "10000", ""],
        ]
        self._write()
        self.meta = {
            "fingerprint": "e" * 64, "status": "DESCRITIVO_CONCLUIDO",
            "presidente_top2": ["22", "13"],
            "senadores_por_uf": {"AC": ["170", "171"]},
            "pairs_compared": 4, "csv": str(self.file),
            "csv_sha256": sha256(self.file)}
        (self.folder / "summary.json").write_text(
            json.dumps(self.meta), encoding="utf-8")
        (self.root / "analysis" /
         "reconciliacao_bu_secao.summary.json").write_text(
            json.dumps({"fingerprint": "e" * 64}), encoding="utf-8")

    def _write(self):
        with self.file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(COLS)
            writer.writerows(self.data)

    def _metadata(self):
        self.meta["csv_sha256"] = sha256(self.file)
        return self.meta

    def test_reversal_and_geographic_correction(self):
        result = a.run(self.root)
        self.assertEqual(result["pares_avaliados"], 4)
        self.assertEqual(result["ufs"], 1)
        self.assertEqual(result["contagens"]["sinais_opostos_robustos"], 2)
        self.assertEqual(result["contagens"]["alteracao_absoluta_020"], 2)
        self.assertEqual(result["contagens"]["amostra_suficiente"], 4)
        self.assertEqual(result["contagens"]["ajustado_proximo_zero"], 1)
        self.assertEqual(len(result["ufs_com_sinal_oposto"]), 1)
        self.assertEqual(result["files"]["todos_pares.csv"]["sha256"],
                         sha256(Path(result["files"]["todos_pares.csv"]["path"])))

    def test_insufficient_votes_not_flagged(self):
        self.data[0][8] = "4"
        self._write()
        _, _, summary = a.audit(self.file, self._metadata())
        self.assertEqual(summary["amostra_insuficiente"], 1)
        self.assertEqual(summary["sinais_opostos_robustos"], 1)

    def test_hash_mismatch_rejected(self):
        self.file.write_text("corrompido", encoding="utf-8")
        with self.assertRaises(RuntimeError):
            a.audit(self.file, self.meta)

    def test_unknown_pair_rejected(self):
        self.data[0][3] = "999"
        self._write()
        with self.assertRaises(RuntimeError):
            a.audit(self.file, self._metadata())

    def test_unbounded_or_nonfinite_coefficients_rejected(self):
        self.data[0][5] = "nan"
        self._write()
        with self.assertRaises(RuntimeError):
            a.audit(self.file, self._metadata())

    def test_duplicate_pair_rejected(self):
        self.data[1] = self.data[0][:]
        self._write()
        with self.assertRaises(RuntimeError):
            a.audit(self.file, self._metadata())

    def test_missing_correlations_marked_without_claims(self):
        self.data[0][5] = ""
        self.data[0][6] = ""
        self._write()
        records, _, summary = a.audit(self.file, self._metadata())
        self.assertEqual(summary["sem_coeficiente_bruto"], 1)
        self.assertEqual(summary["sem_coeficiente_ajustado"], 1)
        self.assertEqual(summary["sinais_opostos_robustos"], 1)
        self.assertEqual(records[0]["amostra_suficiente_descritiva"], 0)


if __name__ == "__main__":
    unittest.main()
