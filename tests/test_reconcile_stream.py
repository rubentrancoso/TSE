"""Testes do motor sequencial, equivalente ao SQL antigo em base sintetica."""
import csv
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import reconcile_incremental as old
import reconcile_stream as stream
import urnas


def add(db, line, kind, uf, mu, zone, section, turn, office, candidate, votes):
    db.execute("INSERT INTO votes VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
               (kind+":synthetic", "synthetic.csv", line, kind,
                uf, mu, zone, section, turn, office, candidate,
                votes, "{}"))


def contents(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return sorted(tuple(row) for row in csv.reader(f, delimiter=";"))


class StreamReconcileTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.db = sqlite3.connect(self.folder / "urnas.sqlite3")
        self.addCleanup(self.db.close)
        urnas.schema(self.db)
        records = [
            ("bu", "AC", "1007", "9", "1", "1", "1", "13", 50),
            ("bu", "AC", "1007", "9", "1", "1", "1", "13", 17),
            ("secao_nacional", "AC", "1007", "9", "1", "1", "1", "13", 67),
            ("secao", "AC", "1007", "9", "1", "1", "1", "13", 67),
            ("bu", "AC", "1007", "9", "1", "1", "1", "22", 143),
            ("secao_nacional", "AC", "1007", "9", "1", "1", "1", "22", 143),
            ("bu", "AC", "1007", "9", "1", "1", "1", "95", 2),
            ("secao_nacional", "AC", "1007", "9", "1", "1", "1", "96", 7),
            ("bu", "AC", "1007", "9", "1", "1", "1", "55", 10),
            ("secao_nacional", "AC", "1007", "9", "1", "1", "1", "55", 9),
            ("bu", "PE", "24570", "10", "20", "1", "25", "101", 17),
            ("bu", "AL", "27000", "3", "4", "1", "1", "13", 100),
            ("secao", "AL", "27000", "3", "4", "1", "1", "13", 100),
        ]
        for line, entry in enumerate(records, 1):
            add(self.db, line, *entry)
        for i, kind in enumerate(("bu", "secao", "secao_nacional")):
            self.db.execute(
                "INSERT INTO imports(resource_key,sha256,imported_utc,rows,"
                "files,parser_version) VALUES(?,?,?,?,?,?)",
                (kind+":synthetic", kind+"-sha", "2026-10-23", 5, 1, 3))
        self.db.commit()

    def test_same_as_old_national_join(self):
        first = self.folder / "old" / "report.csv"
        first.parent.mkdir()
        legacy = old.reconcile_resumable(self.db, first, workers=1)
        output = self.folder / "stream" / "report.csv"
        output.parent.mkdir()
        newer = stream.reconcile_stream(self.db, output, buckets=8, chunk_rows=3)
        for key in ("keys_compared", "different_or_missing",
                    "missing_bu", "missing_section", "matches"):
            self.assertEqual(newer[key], legacy[key], key)
        self.assertEqual(newer["keys_compared"], 7)
        self.assertEqual(newer["different_or_missing"], 4)
        self.assertEqual(newer["missing_section"], 2)
        self.assertEqual(newer["missing_bu"], 1)
        self.assertEqual(contents(first), contents(output))
        repeated = stream.reconcile_stream(self.db, output,
                                           buckets=8, chunk_rows=2)
        self.assertEqual(repeated["rows_scanned"], len(
            self.db.execute("SELECT rowid FROM votes").fetchall()))
        self.assertEqual(repeated["keys_compared"], 7)

    def test_pilot_retains_original_report_and_resumes(self):
        output = self.folder / "original.csv"
        output.write_text("historico intocado", encoding="utf-8")
        pilot = stream.reconcile_stream(self.db, output, buckets=8,
                                        chunk_rows=4, pilot_rows=4)
        self.assertEqual(pilot["status"], "piloto_checkpoint_salvo")
        self.assertEqual(pilot["rows_scanned"], 4)
        self.assertFalse(pilot["scan_complete"])
        self.assertEqual(output.read_text(encoding="utf-8"),
                         "historico intocado")
        report = stream.reconcile_stream(self.db, output, buckets=8,
                                         chunk_rows=4)
        self.assertEqual(report["rows_scanned"], 13)
        self.assertEqual(report["different_or_missing"], 4)

    def test_resume_after_interrupted_scan(self):
        output = self.folder / "resume.csv"
        def interrupt(chunks, state):
            if chunks == 2:
                raise KeyboardInterrupt("interrupcao de teste")
        with self.assertRaises(KeyboardInterrupt):
            stream.reconcile_stream(self.db, output, buckets=8,
                                     chunk_rows=4, after_chunk=interrupt)
        self.assertFalse(output.exists())
        report = stream.reconcile_stream(self.db, output, buckets=8,
                                         chunk_rows=4)
        self.assertEqual(report["rows_scanned"], 13)
        self.assertEqual(report["keys_compared"], 7)
        self.assertEqual(report["different_or_missing"], 4)

    def test_resume_after_interrupted_partition(self):
        output = self.folder / "partition.csv"
        def interrupt(number, state):
            raise KeyboardInterrupt("interrupcao de particao")
        with self.assertRaises(KeyboardInterrupt):
            stream.reconcile_stream(self.db, output, buckets=8,
                                     chunk_rows=5, after_part=interrupt)
        report = stream.reconcile_stream(self.db, output, buckets=8,
                                         chunk_rows=5)
        self.assertEqual(report["partitions_completed"], 8)
        self.assertEqual(report["different_or_missing"], 4)

    def test_change_import_hash_isolates_new_workspace(self):
        output = self.folder / "report.csv"
        first = stream.reconcile_stream(self.db, output,
                                        buckets=8, chunk_rows=5)
        self.db.execute("UPDATE imports SET sha256='changed' "
                        "WHERE resource_key='bu:synthetic'")
        self.db.commit()
        second = stream.reconcile_stream(self.db, output,
                                         buckets=8, chunk_rows=5)
        self.assertNotEqual(first["fingerprint"], second["fingerprint"])
        self.assertEqual(second["keys_compared"], 7)

    def test_corrupt_partition_detected_by_digest(self):
        output = self.folder / "report.csv"
        report = stream.reconcile_stream(self.db, output,
                                         buckets=8, chunk_rows=4)
        bucket_dir = Path(report["checkpoint_folder"]) / "buckets"
        target = next(p for p in bucket_dir.glob("*.tsv")
                      if p.stat().st_size > 0)
        with open(target, "r+b") as file:
            file.seek(0)
            original = file.read(1)
            file.seek(0)
            file.write(b"Q" if original != b"Q" else b"X")
        with self.assertRaisesRegex(RuntimeError, "alterada ou corrompida"):
            stream.reconcile_stream(self.db, output,
                                    buckets=8, chunk_rows=4)


if __name__ == "__main__":
    unittest.main()
