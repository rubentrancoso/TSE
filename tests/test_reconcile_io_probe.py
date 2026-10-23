"""Teste de leitura sequencial com amostras e limite de tempo."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from reconcile_io_probe import run, sample_window


class SequentialIOProbeTest(unittest.TestCase):
    def test_sample_windows_no_write_to_votes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / "analysis"
            folder.mkdir()
            dbfile = folder / "urna_2026.sqlite3"
            conn = sqlite3.connect(dbfile)
            conn.execute("""CREATE TABLE votes (
                source_kind TEXT, uf TEXT, municipio TEXT,
                zona TEXT, secao TEXT, turno TEXT,
                cargo TEXT, votavel TEXT, votos INTEGER)""")
            conn.executemany("INSERT INTO votes VALUES(?,?,?,?,?,?,?,?,?)", [
                ("bu","SC","80446","83",str(i),"1","1","13",20)
                for i in range(150)
            ])
            conn.commit()
            conn.close()
            result = run(root, rows=100, timeout=10)
            self.assertEqual(len(result), 3)
            self.assertEqual(result[0][1]["rows"], 100)
            self.assertEqual(result[1][1]["rows"], 76)
            self.assertTrue(result[0][1]["rows_per_sec"] > 0)
            with sqlite3.connect(dbfile) as check:
                self.assertEqual(
                    check.execute("SELECT COUNT(*) FROM votes").fetchone()[0], 150)

    def test_sqlite_query_keeps_sequential_rowid_order(self):
        conn=sqlite3.connect(":memory:")
        conn.execute("""CREATE TABLE votes(
            source_kind,uf,municipio,zona,secao,turno,
            cargo,votavel,votos)""")
        conn.executemany("INSERT INTO votes VALUES(?,?,?,?,?,?,?,?,?)",
                         [("bu","SC","80000","1","1","1","1","13",1)]*3)
        report = sample_window(conn, 2, 2, 3)
        self.assertEqual(report["rows"], 2)
        self.assertIn("INTEGER PRIMARY KEY", report["plan"])
        conn.close()


if __name__ == "__main__":
    unittest.main()
