"""Teste de leitura sequencial com amostras e limite de tempo."""
from contextlib import closing
import json
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
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
            with closing(sqlite3.connect(dbfile)) as check:
                self.assertEqual(
                    check.execute("SELECT COUNT(*) FROM votes").fetchone()[0], 150)
            # No Windows falha com WinError 32 se a conexao de run
            # ou de verificacao continua aberta apos o context manager.
            renamed = folder / "renamed.sqlite3"
            dbfile.rename(renamed)
            renamed.rename(dbfile)

    def test_clock_same_tick_still_reports_positive_throughput(self):
        with closing(sqlite3.connect(":memory:")) as conn:
            conn.execute("""CREATE TABLE votes(
                source_kind,uf,municipio,zona,secao,turno,
                cargo,votavel,votos)""")
            conn.executemany("INSERT INTO votes VALUES(?,?,?,?,?,?,?,?,?)",
                             [("bu","SC","80000","1","1","1","1","13",1)]*4)
            # Simula relogio com a mesma marcacao antes e apos leitura.
            with patch("reconcile_io_probe.time.perf_counter_ns",
                       return_value=123456789):
                report = sample_window(conn, 1, 4, 3)
            self.assertEqual(report["rows"], 4)
            self.assertGreater(report["seconds"], 0)
            self.assertGreater(report["rows_per_sec"], 0)

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
