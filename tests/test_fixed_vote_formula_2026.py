"""Testes sinteticos para falsificar formula fixa, somente dados 2026."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import tempfile
import unittest

import test_fixed_vote_formula_2026 as formula
from reconcile_stream import sha256


def fixture(root, fractions=(0.5, 0.5)):
    fp = "a"*64
    base = root / "analysis"
    folder = base / "entre_cargos" / "fixture"
    dest = folder / "candidatos"
    dest.mkdir(parents=True)
    paths = []
    count = 0
    for i, mu in enumerate(("101", "102")):
        path = dest / f"bucket-{i:04d}.csv"
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["UF", "municipio", "zona", "secao", "turno",
                        "cargo", "votavel", "votos_BU"])
            for s in range(1, 71):
                sec = str(s)
                n = 100
                p13 = round(fractions[i]*n)
                for office, candidate, votes in [
                    ("1", "13", p13), ("1", "22", n-p13),
                    ("3", "10", 100),
                ]:
                    w.writerow(["AC", mu, str(i+1), sec, "1", office,
                                candidate, votes])
                    count += 1
        paths.append(path)
    (folder / "state.json").write_text(json.dumps({
        "completed": {str(i): {"candidate_sha256": sha256(p)}
                      for i, p in enumerate(paths)}
    }), encoding="utf-8")
    (folder / "summary.json").write_text(json.dumps({
        "status": "concluido", "source_fingerprint": fp,
        "partitions": 2, "candidate_keys": count,
    }), encoding="utf-8")
    (base / "reconciliacao_bu_secao.summary.json").write_text(
        json.dumps({"fingerprint": fp}), encoding="utf-8")
    return paths, count


class FormulaHypothesisTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_exact_fixed_share_not_refuted_by_descriptive_rule(self):
        paths, count = fixture(self.root)
        result = formula.run(self.root)
        self.assertEqual(result["source_candidate_keys"], count)
        self.assertEqual(result["counts"]["qualificadas"], 140)
        self.assertEqual(result["counts"]["secoes_presidenciais"], 140)
        self.assertEqual(result["counts"]["treino"]+
                         result["counts"]["validacao"], 140)
        self.assertGreater(result["validation_sections"], 0)
        self.assertTrue(result[
            "criterio_exploratorio_forma_simples_nao_refutada"]["13"])
        self.assertAlmostEqual(
            result["training"]["presidente_13_rate"], 0.5)
        one = next(x for x in result["national_results"]
                   if x["presidente"] == "13" and x["modelo"] == "nacional")
        self.assertEqual(one["pct_exatas"], 100)
        self.assertEqual(one["erro_absoluto_medio"], 0)
        self.assertEqual(sha256(Path(result["csv"])),
                         result["csv_sha256"])

    def test_different_zones_refute_single_national_share(self):
        fixture(self.root, (0.3, 0.7))
        result = formula.run(self.root)
        self.assertFalse(result[
            "criterio_exploratorio_forma_simples_nao_refutada"]["13"])
        nat = next(x for x in result["national_results"]
                   if x["presidente"] == "13" and x["modelo"] == "nacional")
        geo = next(x for x in result["national_results"]
                   if x["presidente"] == "13" and x["modelo"] == "municipio_zona")
        self.assertGreater(nat["erro_absoluto_medio"], geo["erro_absoluto_medio"])
        self.assertEqual(geo["erro_absoluto_medio"], 0)

    def test_modified_source_rejected(self):
        paths, count = fixture(self.root)
        with paths[0].open("a", encoding="utf-8") as file:
            file.write("modified\n")
        with self.assertRaises(RuntimeError):
            formula.run(self.root)

    def test_negative_vote_rejected_even_with_authorized_fixture_hash(self):
        paths, count = fixture(self.root)
        with paths[0].open("r", newline="", encoding="utf-8") as f:
            data = list(csv.reader(f, delimiter=";"))
        data[1][7] = "-1"
        with paths[0].open("w", newline="", encoding="utf-8") as f:
            csv.writer(f, delimiter=";").writerows(data)
        state_path = paths[0].parent.parent / "state.json"
        state = json.loads(state_path.read_text("utf-8"))
        state["completed"]["0"]["candidate_sha256"] = sha256(paths[0])
        state_path.write_text(json.dumps(state), encoding="utf-8")
        with self.assertRaises(RuntimeError):
            formula.run(self.root)

    def test_hash_split_stable_and_folds_have_no_overlap(self):
        a = ("AC", "101", "1", "30", "1")
        self.assertEqual(formula.holdout(a), formula.holdout(a))
        self.assertIsInstance(formula.holdout(a), bool)
        self.assertEqual(formula.predict(100, 0.504), 50)
        self.assertEqual(formula.predict(100, 0.505), 51)
        with self.assertRaises(RuntimeError):
            formula.predict(100, 1.01)


if __name__ == "__main__":
    unittest.main()
