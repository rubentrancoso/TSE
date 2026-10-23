"""Testes de diagnostico sem importacao nem downloads."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from diagnose_forensics import diagnostic


class DiagnoseTests(unittest.TestCase):
    def test_error_summary_and_missing_section_by_uf(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            analysis = root / "analysis"
            analysis.mkdir()
            (root / "download_manifest_latest.json").write_text(json.dumps({
                "selected": 113, "processed": 113, "reused": 112,
                "downloaded": 0, "errors": [{
                    "stage": "resource", "kind": "artefatos",
                    "uf": "SP", "name": "arquivo-sp",
                    "error": "HTTP 503", "url": "https://example.test/file.zip"
                }], "resources": []}), encoding="utf-8")
            (analysis / "reconciliacao_bu_secao.summary.json").write_text(
                json.dumps({"keys_compared": 6, "matches": 3, "different_or_missing": 3,
                            "missing_bu": 0, "missing_section": 3}), encoding="utf-8")
            path = analysis / "reconciliacao_bu_secao.csv"
            with path.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.writer(stream, delimiter=";")
                writer.writerow(["UF","municipio","zona","secao","turno","cargo",
                                 "votavel","votos_BU","votos_secao","diferenca","situacao"])
                writer.writerows([
                    ["BA","1","2","3","1","1","13","45","","","SEM_SECAO"],
                    ["BA","1","2","4","1","1","22","12","","","SEM_SECAO"],
                    ["SP","1","2","5","1","1","13","23","","","SEM_SECAO"]
                ])
            messages = []
            report = diagnostic(root, emit=messages.append)
            self.assertEqual(len(report["errors"]), 1)
            self.assertEqual(report["errors"][0]["error"], "HTTP 503")
            self.assertEqual(report["status_counts"]["SEM_SECAO"], 3)
            self.assertEqual(report["missing_section_by_state_turn"][0],
                             {"uf": "BA", "turn": "1", "keys": 2})
            self.assertTrue((analysis / "diagnostico_execucao.json").exists())
            self.assertIn("ERRO #1", "\n".join(messages))
            self.assertEqual(report["csv_rows_scanned"], 3)

    def test_quick_mode_no_csv(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "analysis").mkdir()
            report = diagnostic(root, detailed=False, emit=lambda x: None)
            self.assertEqual(report["csv_rows_scanned"], 0)
            self.assertEqual(report["errors"], [])


if __name__ == "__main__":
    unittest.main()
