"""Testes sem rede e sem SQLite da matriz inter-cargos."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import tempfile
import unittest

import cross_office_sections as co
from reconcile_stream import sha256, save_state


def load_csv(path):
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def make_fixture(root):
    fp = "f" * 64
    analysis = root / "analysis"
    analysis.mkdir(parents=True)
    summary = {"status": "concluido", "fingerprint": fp,
               "partitions_total": 2}
    (analysis / "reconciliacao_bu_secao.summary.json").write_text(
        json.dumps(summary), encoding="utf-8")
    workspace = (analysis / "reconciliacao_checkpoints" / "stream" /
                 fp / "buckets")
    workspace.mkdir(parents=True)
    rows = [
        [
            ("AC", "1007", "1", "12", "1", "1", "13", "bu", "3"),
            ("AC", "1007", "1", "12", "1", "1", "13", "bu", "4"),
            ("AC", "1007", "1", "12", "1", "1", "95", "bu", "1"),
            ("AC", "1007", "1", "12", "1", "3", "55", "bu", "7"),
            ("AC", "1007", "1", "12", "1", "3", "96", "bu", "1"),
            ("AC", "1007", "1", "12", "1", "5", "170", "bu", "10"),
            ("AC", "1007", "1", "12", "1", "6", "1100", "bu", "8"),
            ("AC", "1007", "1", "12", "1", "1", "13", "secao", "7"),
        ], [
            ("AC", "1010", "2", "13", "1", "1", "22", "bu", "5"),
            ("AC", "1010", "2", "13", "1", "3", "22", "bu", "3"),
        ]
    ]
    offsets = []
    hashes = []
    for i, items in enumerate(rows):
        path = workspace / f"bucket-{i:04d}.tsv"
        with path.open("w", encoding="utf-8", newline="") as f:
            csv.writer(f, delimiter="\t", lineterminator="\n").writerows(items)
        offsets.append(path.stat().st_size)
        hashes.append(sha256(path))
    save_state(workspace.parent / "state.json",
               {"fingerprint": fp, "scan_complete": True,
                "bucket_hashes": hashes, "offsets": offsets,
                "rows_eligible": 10})
    return workspace


class CrossOfficeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.workspace = make_fixture(self.root)

    def test_pilot_resume_and_normalize(self):
        pilot = co.run(self.root, pilot_buckets=1)
        self.assertEqual(pilot["status"], "piloto")
        result = co.run(self.root)
        self.assertEqual(result["candidate_keys"], 9)
        self.assertEqual(result["source_bu_rows_selected"], 9)
        self.assertEqual(result["distinct_sections"], 2)
        self.assertEqual(result["paired_president_governor_sections"], 2)
        self.assertEqual(result["president_governor_totals_unequal"], 1)
        self.assertEqual(result["sections_by_office"]["1"], 2)
        self.assertEqual(result["sections_by_office"]["3"], 2)
        self.assertEqual(result["sections_by_office"]["5"], 1)
        rows = load_csv(Path(result["matrix"]))
        self.assertEqual(len(rows), 2)
        first = next(x for x in rows if x["secao"] == "12")
        self.assertEqual(first["votos_presidente"], "8")
        self.assertEqual(first["votos_governador"], "8")
        self.assertEqual(first["votos_senado"], "10")
        candidates_dir = Path(result["candidates_dir"])
        candidates = load_csv(candidates_dir / "bucket-0000.csv")
        self.assertEqual(
            next(x["votos_BU"] for x in candidates
                 if x["cargo"] == "1" and x["votavel"] == "13"), "7")
        repeat = co.run(self.root)
        self.assertEqual(repeat["matrix_sha256"], result["matrix_sha256"])

    def test_corrupt_original_rejected(self):
        source = self.workspace / "bucket-0000.tsv"
        with source.open("a", encoding="utf-8") as f:
            f.write("changed\n")
        with self.assertRaises(RuntimeError):
            co.run(self.root)

    def test_wrong_fingerprint_rejected(self):
        state = self.workspace.parent / "state.json"
        obj = json.loads(state.read_text(encoding="utf-8"))
        obj["fingerprint"] = "X" * 64
        save_state(state, obj)
        with self.assertRaises(RuntimeError):
            co.run(self.root)

    def test_atomic_csv(self):
        path = self.root / "test.csv"
        co.atomic_csv(path, ["col"], [["first"], ["second"]])
        self.assertEqual(load_csv(path), [{"col": "first"}, {"col": "second"}])


if __name__ == "__main__":
    unittest.main()
