"""Tests for immutable, content-addressed report history (offline, synthetic)."""
import gzip
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import history_forensics as history
import urnas


class HistoryTests(unittest.TestCase):
    def test_snapshots_deduplicate_objects_and_restore_old(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            reports = base / "analysis" / "estatistica"
            reports.mkdir(parents=True)
            bu_report = base / "analysis" / "reconciliacao_bu_secao.csv"
            stat_report = reports / "benford.csv"
            bu_report.write_text("versao A\n", encoding="utf-8")
            stat_report.write_text("primeira analise\n", encoding="utf-8")
            first = history.snapshot(base, "antes", context={"phase": 1})
            self.assertIsNotNone(first)
            objects = sorted((base / "analysis" / "history" / "objects").glob("*.gz"))
            self.assertEqual(len(objects), 2)
            again = history.snapshot(base, "mesma-versao")
            self.assertNotEqual(again["run_id"], first["run_id"])
            self.assertEqual(len(list((base / "analysis" / "history" / "objects").glob("*.gz"))), 2)

            bu_report.write_text("versao B\n", encoding="utf-8")
            newer = history.snapshot(base, "depois", context={"phase": 2})
            self.assertEqual(len(list((base / "analysis" / "history" / "objects").glob("*.gz"))), 3)

            restored = base / "restaurados"
            self.assertEqual(history.restore(base, first["run_id"], restored), 2)
            self.assertEqual(
                (restored / "analysis" / "reconciliacao_bu_secao.csv").read_text(encoding="utf-8"),
                "versao A\n")
            self.assertEqual(bu_report.read_text(encoding="utf-8"), "versao B\n")
            self.assertEqual(len((base / "analysis" / "history" / "ledger.jsonl").read_text(
                encoding="utf-8").splitlines()), 3)
            self.assertTrue(newer["code"])
            first_record = first["reports"][0]
            archive_file = base / "analysis" / "history" / first_record["object_gzip"]
            with gzip.open(archive_file, "rb") as source:
                data = source.read()
            self.assertEqual(history.digest_file(archive_file) is not None, True)
            self.assertTrue(data)

    def test_source_hashes_and_no_sqlite_duplication(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            db_file = root / "analysis" / "urna_2026.sqlite3"
            db_file.parent.mkdir(parents=True)
            db = sqlite3.connect(db_file)
            urnas.schema(db)
            db.execute("""INSERT INTO imports
                (resource_key,sha256,imported_utc,rows,files,parser_version)
                VALUES('bu:resource-a','deadbeef','2026-10-16',15,1,2)""")
            db.commit()
            db.close()
            (root / "analysis" / "summary.json").write_text('{"test":true}')
            result = history.snapshot(root, "sources")
            self.assertEqual(result["sources_imported"][0]["sha256"], "deadbeef")
            self.assertFalse(any("sqlite" in entry["path"] for entry in result["reports"]))

    def test_empty_is_not_claimed_as_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertIsNone(history.snapshot(folder, "empty"))
            self.assertFalse((Path(folder) / "analysis" / "history").exists())

    def test_invalid_restore_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                history.restore(folder, "../unsafe", Path(folder) / "out")


if __name__ == "__main__":
    unittest.main()
