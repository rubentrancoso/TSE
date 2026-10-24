"""Testes offline do inventario 2026: catalogo oficial x captura declarada."""
import csv
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

import inventory_material_evidence_2026 as inv


class MaterialEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.analysis = self.root / "analysis"
        self.analysis.mkdir()
        self.db = self.analysis / "urna_2026.sqlite3"
        # sqlite3.Connection.__exit__ confirma transacao, mas NAO fecha
        # o handle. No Windows isso bloqueia tempfile.cleanup e unlink.
        with closing(sqlite3.connect(self.db)) as db:
            db.execute("""CREATE TABLE archive_entries (
                resource_key TEXT, member TEXT, bytes INTEGER,
                extensao TEXT, uf TEXT, municipio TEXT, zona TEXT,
                secao TEXT, sha256 TEXT)""")
            db.executemany(
                "INSERT INTO archive_entries VALUES (?,?,?,?,?,?,?,?,?)",
                [
                    ("tse_zip_1", "SP/0001/0010/a.bu", 35, ".bu",
                     "SP", "71072", "1", "10", "a"*64),
                    ("tse_zip_1", "SP/0001/0010/a.rdv", 43, ".rdv",
                     "SP", "71072", "1", "10", "b"*64),
                    ("tse_zip_1", "SP/0001/0010/a.log", 88, ".log",
                     "SP", "71072", "1", "10", None),
                ],
            )
            db.commit()
        self.base = self.root / "evidencia_independente_2026"
        self.base.mkdir()
        self.original = self.base / "captura-ac-01.txt"
        self.original.write_bytes(b"imagem ou dado original, fixture")
        self.sha = hashlib.sha256(self.original.read_bytes()).hexdigest()
        self.manifest = self.base / "manifest.csv"
        self.fields = ["id", "uf", "municipio", "zona", "secao",
                       "turno", "tipo", "arquivo", "origem",
                       "captura_utc", "sha256"]
        self.row = [
            "obs1", "SP", "71072", "1", "10", "1", "foto_bu",
            self.original.name, "foto de fiscal (apenas declarado)",
            "2026-10-04T20:00:00Z", self.sha,
        ]
        self.write_manifest()

    def write_manifest(self):
        with self.manifest.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(self.fields)
            w.writerow(self.row)

    def test_official_not_independent(self):
        result = inv.run(self.root, write=False)
        counts = result["official_artifacts"]["totais_extensoes"]
        self.assertEqual(counts[".bu"], 1)
        self.assertEqual(counts[".rdv"], 1)
        self.assertEqual(counts[".log"], 1)
        self.assertEqual(result["independent_captures"]["arquivos_hash_ok"], 1)
        self.assertFalse(result["independent_captures"]["declaracoes"][0][
            "autenticidade_criptografica_verificada"])
        self.assertFalse(result["independent_captures"]["declaracoes"][0][
            "proveniencia_verificada"])
        self.assertEqual(result["escopo"], "2026_EXCLUSIVO")

    def test_missing_database_is_unknown(self):
        self.db.unlink()
        result = inv.run(self.root, write=False)
        self.assertEqual(result["official_artifacts"]["status"], "BANCO_AUSENTE")

    def test_no_manifest_is_unknown(self):
        self.manifest.unlink()
        result = inv.run(self.root, write=False)
        self.assertEqual(result["independent_captures"]["status"],
                         "MANIFESTO_AUSENTE")
        self.assertEqual(result["independent_captures"]["registros"], 0)

    def test_modified_independent_file_is_flagged(self):
        self.original.write_bytes(b"trocado")
        result = inv.run(self.root, write=False)
        self.assertEqual(result["independent_captures"]["arquivos_hash_ok"], 0)
        self.assertEqual(result["independent_captures"]["arquivos_hash_erro"], 1)

    def test_path_escape_is_rejected(self):
        self.row[7] = "../fora.txt"
        self.write_manifest()
        with self.assertRaises(RuntimeError):
            inv.run(self.root, write=False)

    def test_bad_hash_rejected(self):
        self.row[-1] = "12345"
        self.write_manifest()
        with self.assertRaises(RuntimeError):
            inv.run(self.root, write=False)

    def test_output_and_immutability(self):
        original_bytes = self.db.read_bytes()
        result = inv.run(self.root)
        self.assertEqual(self.db.read_bytes(), original_bytes)
        file = Path(result["output"])
        self.assertTrue(file.is_file())
        json_result = json.loads(file.read_text("utf-8"))
        self.assertEqual(json_result["escopo"], "2026_EXCLUSIVO")


if __name__ == "__main__":
    unittest.main()
