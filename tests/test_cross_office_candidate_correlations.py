"""Testes offline: correlacao entre candidatos, controle geografico e SHA."""
import csv
import json
from pathlib import Path
import tempfile
import unittest

import cross_office_candidate_correlations as c
from reconcile_stream import sha256


def make_fixture(root):
    fp = "a" * 64
    folder = root / "analysis" / "entre_cargos" / "sample"
    candidates = folder / "candidatos"
    candidates.mkdir(parents=True)
    # Dois grupos territoriais: correlacao agregada negativa apesar de
    # correlacao positiva DENTRO de cada zona.
    records = []
    for municipality, zone, section, p13, g10 in [
        ("101", "1", "1", 10, 70), ("101", "1", "2", 20, 80),
        ("102", "2", "3", 70, 10), ("102", "2", "4", 80, 20),
    ]:
        for office, values in (("1", [("13", p13), ("22", 100-p13)]),
                               ("3", [("10", g10), ("55", 100-g10)])):
            for candidate, votes in values:
                records.append(["AC", municipality, zone, section, "1",
                                office, candidate, votes])
    first = candidates / "bucket-0000.csv"
    second = candidates / "bucket-0001.csv"
    first_records = sorted(records[:8], key=lambda x: tuple(x[:7]))
    second_records = sorted(records[8:], key=lambda x: tuple(x[:7]))
    for path, rows in ((first, first_records), (second, second_records)):
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["UF", "municipio", "zona", "secao", "turno",
                        "cargo", "votavel", "votos_BU"])
            w.writerows(rows)
    (folder / "summary.json").write_text(json.dumps({
        "status": "concluido", "source_fingerprint": fp,
        "partitions": 2, "candidate_keys": 16,
    }), encoding="utf-8")
    (folder / "state.json").write_text(json.dumps({
        "completed": {"0": {"candidate_sha256": sha256(first)},
                      "1": {"candidate_sha256": sha256(second)}}
    }), encoding="utf-8")
    (root / "analysis" / "reconciliacao_bu_secao.summary.json").write_text(
        json.dumps({"fingerprint": fp}), encoding="utf-8")
    return first, second


class CandidateCorrelationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.first, self.second = make_fixture(self.root)

    def test_simpson_and_candidate_pair(self):
        result = c.run(self.root, top_governors=2)
        self.assertEqual(result["pairs_compared"], 4)
        self.assertEqual(result["candidate_keys_checked"], 16)
        self.assertEqual(sum(result["paired_sections_by_uf"].values()), 4)
        self.assertEqual(sum(result["valid_share_sections_by_uf"].values()), 4)
        with Path(result["correlation_csv"]).open(
                "r", newline="", encoding="utf-8") as f:
            data = list(csv.DictReader(f, delimiter=";"))
        pair = next(r for r in data if r["presidente"] == "13"
                    and r["governador"] == "10")
        self.assertEqual(pair["secoes_pareadas_validas"], "4")
        self.assertLess(float(pair["correlacao_bruta_pearson"]), 0)
        self.assertAlmostEqual(float(pair["correlacao_dentro_municipio_zona"]),
                               1.0, places=5)

    def test_reject_modified_candidate_file(self):
        with self.first.open("a", encoding="utf-8") as f:
            f.write("changed\n")
        with self.assertRaises(RuntimeError):
            c.run(self.root)

    def test_not_make_individual_transfer_claim(self):
        result = c.run(self.root, top_governors=2)
        with Path(result["correlation_csv"]).open("r", encoding="utf-8") as f:
            row = next(csv.DictReader(f, delimiter=";"))
        self.assertIn("nao representa votos individuais", row["nota"])
        self.assertIn("Nao e transferencia individual", result["note"])

    def test_pearson_degenerate(self):
        m = c.Moments()
        m.add(1, 3)
        m.add(1, 5)
        self.assertIsNone(c.pearson(m.centered()))


if __name__ == "__main__":
    unittest.main()
