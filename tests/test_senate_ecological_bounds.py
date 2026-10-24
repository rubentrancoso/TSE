"""Testes offline dos limites ecologicos de secao com dois votos senatoriais."""
import csv
import json
from pathlib import Path
import tempfile
import unittest

import senate_ecological_bounds as b
from reconcile_stream import sha256


class SenateBoundsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        base = self.root / "analysis"
        base.mkdir()
        self.fp = "f" * 64
        (base / "reconciliacao_bu_secao.summary.json").write_text(
            json.dumps({"fingerprint": self.fp}), encoding="utf-8")
        self.folder = base / "entre_cargos" / "fixture"
        candidates = self.folder / "candidatos"
        candidates.mkdir(parents=True)
        self.files = []
        records = []
        for zone, sec, p13, p22, senate_170, senate_171 in [
            ("1", "1", 8, 2, 5, 5),
            ("2", "2", 3, 7, 4, 6),
        ]:
            recs = []
            for office, vals in (
                ("1", [("13", p13), ("22", p22)]),
                ("5", [("95", 10), ("170", senate_170),
                       ("171", senate_171)]),
            ):
                for candidate, votes in vals:
                    recs.append(["AC", "100", zone, sec, "1",
                                 office, candidate, votes])
            recs.sort(key=lambda x: tuple(x[:7]))
            path = candidates / f"bucket-{len(self.files):04d}.csv"
            self._write(path, recs)
            records.extend(recs)
            self.files.append(path)
        (self.folder / "state.json").write_text(json.dumps({
            "completed": {str(i): {"candidate_sha256": sha256(p)}
                          for i, p in enumerate(self.files)}
        }), encoding="utf-8")
        (self.folder / "summary.json").write_text(json.dumps({
            "status": "concluido", "source_fingerprint": self.fp,
            "partitions": 2, "candidate_keys": len(records),
        }), encoding="utf-8")
        self.review_dir = (self.folder / "diagnostico_conjunto" /
                           "revisao_inversoes")
        self.review_dir.mkdir(parents=True)
        self.review = self.review_dir / "summary.json"
        self._review([
            {"UF": "AC", "senador": "170", "presidente": "13"},
            {"UF": "AC", "senador": "170", "presidente": "22"}])
        self.mapping_path = self.root / "mapping.csv"
        self.mapping_path.write_text(
            "UF;turno;cargo;numero;nome_urna;partido;fonte;fonte_publicada_em\n"
            "AC;1;5;170;Nome documentado;PARTIDO;https://example.org;2026-08-24\n",
            encoding="utf-8")

    @staticmethod
    def _write(path, rows):
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["UF", "municipio", "zona", "secao", "turno",
                        "cargo", "votavel", "votos_BU"])
            w.writerows(rows)

    def _review(self, inversion_rows):
        data = {
            "input_fingerprint": self.fp,
            "senado_pares_invertidos": inversion_rows,
            "senadores_distintos_em_inversoes": len(
                set((x["UF"], x["senador"]) for x in inversion_rows)),
        }
        self.review.write_text(json.dumps(data), encoding="utf-8")

    def test_bounds_math(self):
        self.assertEqual(b.bounds(8, 5, 10), (3, 5, 0))
        self.assertEqual(b.bounds(2, 5, 10), (0, 2, 3))
        with self.assertRaises(RuntimeError):
            b.bounds(11, 5, 10)

    def test_two_senate_slots_with_distinct_electors(self):
        report = b.run(self.root, self.mapping_path)
        self.assertEqual(report["candidatos_distintos"], 1)
        self.assertEqual(report["pares_presidencia_senado"], 2)
        self.assertEqual(report["source_bu_candidate_keys"], 10)
        a = next(row for row in report["por_candidato"]
                 if row["presidente"] == "13")
        c = next(row for row in report["por_candidato"]
                 if row["presidente"] == "22")
        self.assertEqual(a["secoes_validas"], 2)
        self.assertEqual(a["votos_senador"], 9)
        self.assertEqual(a["sobreposicao_minima"], 3)
        self.assertEqual(a["sobreposicao_maxima"], 8)
        self.assertEqual(a["senador_fora_do_presidente_minimo"], 1)
        self.assertEqual(c["sobreposicao_minima"], 1)
        self.assertEqual(c["sobreposicao_maxima"], 6)
        self.assertEqual(c["senador_fora_do_presidente_minimo"], 3)
        self.assertEqual(a["comparecimento_presidencial"], 20)
        self.assertEqual(a["eleitorado_senado_naquelas_secoes"], 20)
        self.assertEqual(
            sha256(Path(report["csv"])), report["csv_sha256"])

    def test_missing_candidate_mapping_rejected(self):
        self.mapping_path.write_text(
            "UF;turno;cargo;numero;nome_urna;partido;fonte\n"
            "AC;1;5;171;Outro;X;https://example.org\n",
            encoding="utf-8")
        with self.assertRaises(RuntimeError):
            b.run(self.root, self.mapping_path)

    def test_corrupted_bucket_rejected(self):
        with self.files[0].open("a", encoding="utf-8") as file:
            file.write("x\n")
        with self.assertRaises(RuntimeError):
            b.run(self.root, self.mapping_path)

    def test_more_senator_votes_than_voters_rejected(self):
        # Recupera a origem com novo SHA na fixture, mas a estrutura
        # e contabilmente invalida: total Senate=22, N_pres=10.
        path = self.files[0]
        with path.open("r", newline="", encoding="utf-8") as f:
            data = list(csv.reader(f, delimiter=";"))
        for line in data[1:]:
            if line[5] == "5" and line[6] == "95":
                line[7] = "12"
        with path.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f, delimiter=";").writerows(data)
        state = self.folder / "state.json"
        obj = json.loads(state.read_text("utf-8"))
        obj["completed"]["0"]["candidate_sha256"] = sha256(path)
        state.write_text(json.dumps(obj), encoding="utf-8")
        with self.assertRaises(RuntimeError):
            b.run(self.root, self.mapping_path)

    def test_wrong_review_fingerprint_rejected(self):
        data = json.loads(self.review.read_text("utf-8"))
        data["input_fingerprint"] = "x" * 64
        self.review.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(RuntimeError):
            b.run(self.root, self.mapping_path)


if __name__ == "__main__":
    unittest.main()
