"""Testes offline: Presidente x Senado, duas vagas e controle geografico."""
import csv
import json
from pathlib import Path
import tempfile
import unittest

import cross_office_senate_correlations as sen
from reconcile_stream import sha256


def fixture(root):
    fp = "e" * 64
    base = root / "analysis"
    folder = base / "entre_cargos" / "teste_senado"
    candidates = folder / "candidatos"
    candidates.mkdir(parents=True)
    # Duas zonas, 2 secoes por zona: Paradoxo de Simpson para
    # Presidente 13 e Senador 170. Senado tem 2 votos por eleitor:
    # votos 170+171+172 = 200 para 100 eleitores em cada secao.
    sections = [
        ("101", "1", "1", 10, 70),
        ("101", "1", "2", 20, 80),
        ("102", "2", "3", 70, 10),
        ("102", "2", "4", 80, 20),
    ]
    complete = []
    for mu, zo, se, p13, s170 in sections:
        for office, votes in (
            ("1", [("13", p13), ("22", 100-p13)]),
            ("5", [("170", s170), ("171", 100-s170), ("172", 100)]),
        ):
            for cand, n in votes:
                complete.append(["AC", mu, zo, se, "1", office, cand, n])
    # Cada particao contem uma zona, como bucket_for do motor original.
    paths = []
    for i, mu in enumerate(("101", "102")):
        path = candidates / f"bucket-{i:04d}.csv"
        records = sorted((r for r in complete if r[1] == mu),
                         key=lambda r: tuple(r[:7]))
        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file, delimiter=";")
            writer.writerow(["UF", "municipio", "zona", "secao", "turno",
                             "cargo", "votavel", "votos_BU"])
            writer.writerows(records)
        paths.append(path)
    (folder / "state.json").write_text(json.dumps({
        "completed": {str(i): {"candidate_sha256": sha256(path)}
                      for i, path in enumerate(paths)}
    }), encoding="utf-8")
    (folder / "summary.json").write_text(json.dumps({
        "status": "concluido", "source_fingerprint": fp,
        "partitions": 2, "candidate_keys": len(complete)
    }), encoding="utf-8")
    (base / "reconciliacao_bu_secao.summary.json").write_text(
        json.dumps({"fingerprint": fp}), encoding="utf-8")
    return paths


class SenateCorrelationsTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.paths = fixture(self.root)

    def test_senate_per_voter_and_simpson(self):
        result = sen.run(self.root)
        self.assertEqual(result["candidate_keys_checked"], 20)
        self.assertEqual(result["senadores_total"], 3)
        self.assertEqual(result["pairs_compared"], 6)
        self.assertEqual(sum(result["valid_sections_by_uf"].values()), 4)
        self.assertEqual(result["denominators"]["senador"],
                         "(total de votos senatoriais incluindo branco e nulo)/2")
        with Path(result["csv"]).open("r", encoding="utf-8") as file:
            data = list(csv.DictReader(file, delimiter=";"))
        pair = next(x for x in data if x["presidente"] == "13"
                    and x["senador"] == "170")
        self.assertEqual(int(pair["secoes_com_dois_cargos"]), 4)
        self.assertLess(float(pair["correlacao_bruta_pearson"]), 0)
        self.assertAlmostEqual(
            float(pair["correlacao_dentro_municipio_zona"]),
            1.0, places=5)
        self.assertEqual(int(pair["votos_senador"]), 180)

    def test_selected_subset(self):
        result = sen.run(self.root, max_senators=2)
        self.assertEqual(result["senadores_total"], 2)
        self.assertEqual(result["pairs_compared"], 4)

    def test_modified_input_refused(self):
        with self.paths[0].open("a", encoding="utf-8") as file:
            file.write("changed\n")
        with self.assertRaises(RuntimeError):
            sen.run(self.root)

    def test_candidate_vote_cannot_exceed_voter_count(self):
        # Testa diretamente o controle da dupla escolha.
        path = self.paths[0]
        with path.open("r", encoding="utf-8", newline="") as file:
            records = list(csv.reader(file, delimiter=";"))
        # troca 170 por 171 na secao 1, deslocando 130 votos
        # para 170, mas sem alterar a soma total de Senado (200).
        for rec in records[1:]:
            if rec[3] == "1" and rec[5] == "5":
                if rec[6] == "170":
                    rec[7] = "130"
                elif rec[6] == "171":
                    rec[7] = "-30"
        with path.open("w", encoding="utf-8", newline="") as file:
            csv.writer(file, delimiter=";").writerows(records)
        _, original, paths = sen.source(self.root) if False else (None, None, None)
        # Aplicar a modificacao autorizada apenas na fixture: o teste
        # nao deve ser confundido com SHA divergente.
        state_path = path.parent.parent / "state.json"
        state = json.loads(state_path.read_text("utf-8"))
        state["completed"]["0"]["candidate_sha256"] = sha256(path)
        state_path.write_text(json.dumps(state), encoding="utf-8")
        with self.assertRaises(RuntimeError):
            sen.run(self.root)

    def test_empty_choice_semantics(self):
        m = sen.Moments()
        m.add(0.2, 0.5)
        m.add(0.3, 0.6)
        self.assertAlmostEqual(sen.pearson(m.centered()), 1.0)


if __name__ == "__main__":
    unittest.main()
