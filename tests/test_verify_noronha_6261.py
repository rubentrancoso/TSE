"""Testes offline da comparacao do pleito especial 6261."""
import csv
import tempfile
import unittest
from pathlib import Path

import verify_noronha_6261 as v


class Noronha6261Test(unittest.TestCase):
    def test_tallies_json_ea20(self):
        doc = {
            "ele": "6261", "tpabr": "zona", "cdabr": "0004",
            "carg": [{
                "cd": "25", "agr": [{
                    "par": [{"cand": [{"n": "170", "vap": "10"},
                                       {"n": "172", "vap": "5"}]}]
                }]
            }],
            "v": {"tv": "18", "vb": "1", "tvn": "2"},
            "s": {"st": "10"}
        }
        got, totals, sections = v.official_tallies(doc)
        self.assertEqual(got, {"170": 10, "172": 5, "95": 1, "96": 2})
        self.assertEqual(totals["tv"], "18")
        self.assertEqual(sections["st"], "10")
        rows, missing = v.compare({"170": 10, "172": 5, "95": 1, "96": 2}, got)
        self.assertEqual(len(rows), 4)
        self.assertEqual(missing, [])
        self.assertTrue(all(r["situacao"] == "OK" for r in rows))

    def test_detect_difference_and_missing(self):
        rows, missing = v.compare({"170": 9, "999": 3},
                                  {"170": 10, "95": 0})
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0]["votavel"], "999")
        self.assertEqual(
            next(row["situacao"] for row in rows if row["votavel"] == "170"),
            "DIFERENTE")

    def test_reject_wrong_election(self):
        with self.assertRaises(RuntimeError):
            v.official_tallies({"ele": "6259", "tpabr": "zona",
                                "cdabr": "0004", "carg": []})

    def test_reject_wrong_zone(self):
        with self.assertRaises(RuntimeError):
            v.official_tallies({"ele": "6261", "tpabr": "zona",
                                "cdabr": "0003", "carg": []})

    def test_read_csv_reject_unexpected_scope(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "reconciliacao.csv"
            with path.open("w", encoding="utf-8", newline="") as file:
                writer = csv.writer(file, delimiter=";")
                writer.writerow(["UF", "municipio", "zona", "secao",
                                 "turno", "cargo", "votavel",
                                 "votos_BU", "situacao"])
                writer.writerow(["SP", "71072", "1", "1", "1",
                                 "25", "170", "1", "SEM_SECAO"])
            with self.assertRaises(RuntimeError):
                v.read_bu(path)

    def test_immutable_report(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "result.json"
            v.save_json_once(path, {"sha": "abc"})
            v.save_json_once(path, {"sha": "abc"})
            with self.assertRaises(RuntimeError):
                v.save_json_once(path, {"sha": "other"})


if __name__ == "__main__":
    unittest.main()
