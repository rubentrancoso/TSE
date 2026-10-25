"""Diagnostico offline das lacunas de ZIP de transmissao, somente 2026."""
import json
from pathlib import Path
import sqlite3
from contextlib import closing
import tempfile
import unittest

import diagnose_artifact_coverage_2026 as diag
from urnas import resource_path


class CoverageTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        db = self.root / "analysis" / "urna_2026.sqlite3"
        db.parent.mkdir()
        with closing(sqlite3.connect(db)) as cx:
            cx.execute("CREATE TABLE imports (resource_key TEXT, sha256 TEXT)")
            cx.execute("""CREATE TABLE archive_entries (
                resource_key TEXT, member TEXT, extensao TEXT)""")
            cx.executemany("INSERT INTO imports VALUES (?,?)", [
                ("artefatos:aaa", "hash"), ("bu:bbb", "hash")])
            cx.executemany("INSERT INTO archive_entries VALUES (?,?,?)", [
                ("artefatos:aaa", "SP/z1/a.bu", ".bu"),
                ("artefatos:aaa", "SP/z1/b.rdv", ".rdv"),
                ("bu:bbb", "SP/z1/report.pdf", ".pdf")])
            cx.commit()
        self.resources = [
            {"id": "aaa", "name": "SP - Arquivos transmitidos",
             "url": "https://dadosabertos.tse.jus.br/dataset/a/sp-transmission.zip"},
            {"id": "ccc", "name": "AC - Arquivos transmitidos",
             "url": "https://dadosabertos.tse.jus.br/dataset/b/ac-transmission.zip"},
        ]
        (self.root / "catalogo_latest.json").write_text(json.dumps({
            "checked_at_utc": "2026-10-25T17:00:00Z",
            "datasets": {"artefatos": {"resources": self.resources}}
        }), encoding="utf-8")
        path = resource_path(self.root,"artefatos","SP",self.resources[0])
        path.parent.mkdir(parents=True)
        path.write_bytes(b"PK fixture is only metadata, not inspected")

    def test_catalogue_vs_zip_index_vs_disk(self):
        result = diag.run(self.root, write=False)
        self.assertEqual(result["escopo"], "2026_SOMENTE")
        self.assertEqual(result["catalogo_oficial_salvo"]["resources"], 2)
        self.assertEqual(result["catalogo_oficial_salvo"]["local"], 1)
        self.assertEqual(result["catalogo_oficial_salvo"]["missing"], 1)
        self.assertEqual(result["disco_zip_transmissao"]["zips"], 1)
        self.assertEqual(result["indice_sqlite"]["imports_por_tipo"]["artefatos"], 1)
        self.assertEqual(result["indice_sqlite"]["extensoes"][".bu"], 1)
        self.assertEqual(result["indice_sqlite"]["extensoes"][".pdf"], 1)

    def test_no_catalogue_is_unknown_not_zero_dataset(self):
        (self.root / "catalogo_latest.json").unlink()
        result = diag.run(self.root, write=False)
        self.assertEqual(result["catalogo_oficial_salvo"]["status"],
                         "CATALOGO_SALVO_AUSENTE")

    def test_missing_db_is_not_deletion_of_raw(self):
        (self.root / "analysis" / "urna_2026.sqlite3").unlink()
        result = diag.run(self.root, write=False)
        self.assertEqual(result["indice_sqlite"]["status"], "BANCO_AUSENTE")
        self.assertEqual(result["disco_zip_transmissao"]["zips"], 1)

    def test_report_written_without_mutation(self):
        db = self.root / "analysis" / "urna_2026.sqlite3"
        original = db.read_bytes()
        result = diag.run(self.root)
        self.assertEqual(db.read_bytes(), original)
        self.assertEqual(
            json.loads(Path(result["output"]).read_text("utf-8"))["version"],
            diag.VERSION)


if __name__ == "__main__":
    unittest.main()
