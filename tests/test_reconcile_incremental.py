"""Testes de reconciliação com checkpoints, ETA e retomada em base sintética."""
import csv
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import reconcile_incremental as ri
import urnas


def row(db, line, kind, uf, mu, zone, sec, turn, candidate, votes):
    obj = json.dumps({"SG_UF": uf, "NR_SECAO": sec})
    db.execute("INSERT INTO votes VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
               (f"{kind}:resource", "records.csv", line, kind, uf, mu,
                zone, sec, turn, "1", candidate, votes, obj))


class ResumeReconcileTests(unittest.TestCase):
    def prepare(self):
        db = sqlite3.connect(":memory:")
        urnas.schema(db)
        db.commit()
        for i, (uf, mu, zone, sec) in enumerate([
                ("BA", "33693", "177", "111"),
                ("BA", "33693", "177", "112"),
                ("BA", "33693", "178", "113"),
                ("MG", "42434", "11", "2")], start=1):
            row(db, 20+i*10, "bu", uf, mu, zone, sec, "1", "13", 100)
            row(db, 21+i*10, "secao", uf, mu, zone, sec, "1", "13",
                101 if sec == "112" else 100)
            row(db, 22+i*10, "bu", uf, mu, zone, sec, "1", "22", 80)
            row(db, 23+i*10, "secao", uf, mu, zone, sec, "1", "22", 80)
        # Fonte nacional independente de seção, não somada outra vez.
        row(db, 999, "secao_nacional", "BA", "33693", "177",
            "111", "1", "13", 50000)
        db.execute("""INSERT INTO imports(resource_key,sha256,imported_utc,rows,files,parser_version)
                      VALUES('bu:original','sha1','2026-10-17',8,1,3)""")
        db.execute("""INSERT INTO imports(resource_key,sha256,imported_utc,rows,files,parser_version)
                      VALUES('secao:original','sha2','2026-10-17',8,1,3)""")
        db.commit()
        return db

    def test_president_national_source_fills_state_gap_without_double_count(self):
        db = sqlite3.connect(":memory:")
        urnas.schema(db)
        # Estado publica outros cargos; Presidente aparece no CSV nacional.
        row(db, 2, "bu", "AC", "1007", "9", "1", "1", "13", 67)
        row(db, 3, "bu", "AC", "1007", "9", "1", "1", "22", 143)
        row(db, 4, "secao_nacional", "AC", "1007", "9", "1", "1", "13", 67)
        row(db, 5, "secao_nacional", "AC", "1007", "9", "1", "1", "22", 143)
        row(db, 6, "bu", "AC", "1007", "9", "1", "1", "95", 2)
        row(db, 7, "secao_nacional", "AC", "1007", "9", "1", "1", "95", 2)
        row(db, 8, "bu", "AC", "1007", "9", "1", "1", "96", 7)
        row(db, 9, "secao_nacional", "AC", "1007", "9", "1", "1", "96", 7)
        db.commit()
        with tempfile.TemporaryDirectory() as folder:
            result = ri.reconcile_resumable(db, Path(folder) / "output.csv")
            self.assertEqual(result["keys_compared"], 4)
            self.assertEqual(result["different_or_missing"], 0)
            self.assertEqual(result["missing_section"], 0)
            self.assertTrue(result["fingerprint"])

        # Se houver tambem a mesma chave estadual, esta prevalece,
        # nao se somam 67 + 67 nem se compara duas vezes.
        row(db, 10, "secao", "AC", "1007", "9", "1", "1", "13", 67)
        db.commit()
        with tempfile.TemporaryDirectory() as folder:
            result = ri.reconcile_resumable(db, Path(folder) / "output.csv")
            self.assertEqual(result["keys_compared"], 4)
            self.assertEqual(result["different_or_missing"], 0)

    def test_president_national_missing_and_other_office_remain_visible(self):
        db = sqlite3.connect(":memory:")
        urnas.schema(db)
        row(db, 2, "bu", "PE", "24570", "23", "7", "1", "13", 61)
        row(db, 3, "bu", "PE", "24570", "23", "7", "1", "25", 14)
        # Registro de cargo diferente que nao esta no nacional.
        db.execute("UPDATE votes SET cargo='25' WHERE line=3")
        db.commit()
        with tempfile.TemporaryDirectory() as folder:
            report = ri.reconcile_resumable(db, Path(folder) / "output.csv")
            self.assertEqual(report["different_or_missing"], 2)
            self.assertEqual(report["missing_section"], 2)

    def test_national_resource_change_invalidates_checkpoints(self):
        db = self.prepare()
        db.execute("""INSERT INTO imports
            (resource_key,sha256,imported_utc,rows,files,parser_version)
            VALUES('secao_nacional:presidente','old','2026-10-23',40,1,3)""")
        db.commit()
        with tempfile.TemporaryDirectory() as folder:
            filename = Path(folder) / "output.csv"
            old = ri.reconcile_resumable(db, filename)
            db.execute("""UPDATE imports SET sha256='changed'
                WHERE resource_key='secao_nacional:presidente'""")
            db.commit()
            new = ri.reconcile_resumable(db, filename)
            self.assertNotEqual(old["fingerprint"], new["fingerprint"])
            self.assertEqual(new["reused_tasks"], 0)

    def test_resume_after_interrupt_and_no_recount(self):
        db = self.prepare()
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "reconciliacao_bu_secao.csv"
            def interrupt_after_first(i, task):
                if i == 1:
                    raise KeyboardInterrupt
            with self.assertRaises(KeyboardInterrupt):
                ri.reconcile_resumable(db, out, after_chunk=interrupt_after_first)
            state_file = Path(d) / "reconciliacao_checkpoints" / "estado.sqlite3"
            state = sqlite3.connect(state_file)
            self.assertEqual(state.execute("SELECT COUNT(*) FROM completed").fetchone()[0], 1)
            state.close()
            report = ri.reconcile_resumable(db, out)
            self.assertEqual(report["tasks_total"], 3)
            self.assertEqual(report["reused_tasks"], 1)
            self.assertEqual(report["keys_compared"], 8)
            self.assertEqual(report["different_or_missing"], 1)
            self.assertEqual(report["missing_bu"], 0)
            self.assertEqual(report["missing_section"], 0)
            text = out.read_text(encoding="utf-8-sig")
            self.assertIn("DIFERENTE", text)
            self.assertEqual(text.count("DIFERENTE"), 1)
            self.assertIn("100;101;-1", text)
            report_repeat = ri.reconcile_resumable(db, out)
            self.assertEqual(report_repeat["reused_tasks"], 3)
            self.assertEqual(out.read_text(encoding="utf-8-sig"), text)

    def test_corrupted_checkpoint_is_recomputed(self):
        db = self.prepare()
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "report.csv"
            first = ri.reconcile_resumable(db, out)
            folder = Path(first["checkpoint_folder"]) / "partes"
            path = sorted(folder.glob("*.csv"))[0]
            with path.open("a", encoding="utf-8") as stream:
                stream.write("adulterado\n")
            later = ri.reconcile_resumable(db, out)
            self.assertEqual(later["reused_tasks"], 2)
            self.assertEqual(later["different_or_missing"], 1)
            self.assertNotIn("adulterado", out.read_text(encoding="utf-8-sig"))

    def test_query_plan_uses_existing_locality_index(self):
        db = self.prepare()
        tasks, _ = ri.tasks_from_db(db, [], None)
        sql, params = ri.sql_group_for_task(tasks[0])
        plan = db.execute("EXPLAIN QUERY PLAN " + sql, params).fetchall()
        self.assertTrue(any("idx_votes_lookup" in str(row) for row in plan))

    def test_changed_source_hash_invalidates_old_checkpoints(self):
        db = self.prepare()
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "report.csv"
            first = ri.reconcile_resumable(db, out)
            db.execute("UPDATE imports SET sha256='new-source-digest' WHERE resource_key='bu:original'")
            db.commit()
            second = ri.reconcile_resumable(db, out)
            self.assertNotEqual(first["fingerprint"], second["fingerprint"])
            self.assertEqual(second["reused_tasks"], 0)
            self.assertEqual(second["keys_compared"], first["keys_compared"])

    def test_scope_by_state_and_turn(self):
        db = self.prepare()
        with tempfile.TemporaryDirectory() as d:
            report = ri.reconcile_resumable(db, Path(d) / "BA.csv", ["BA"], 1)
            self.assertEqual(report["keys_compared"], 6)
            self.assertEqual(report["tasks_total"], 2)

    def test_eta_is_qualified(self):
        self.assertIn("aprox.", ri.eta_text(180))
        self.assertEqual(ri.eta_text(-1), "indisponivel")


if __name__ == "__main__":
    unittest.main()
