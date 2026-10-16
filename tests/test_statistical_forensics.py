"""Testes offline da bateria de analise estatistica (dados sinteticos)."""
import csv
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import urnas
import statistical_forensics as sf


def data_row(db, line, uf, city, zone, sec, turn, cand, votes, turnout, aptos, kind="bu"):
    obj = {
        "SG_UF": uf, "CD_MUNICIPIO": city, "NR_ZONA": zone,
        "NR_SECAO": sec, "NR_TURNO": turn,
        "CD_CARGO_PERGUNTA": "1", "NR_VOTAVEL": cand, "QT_VOTOS": str(votes),
        "QT_COMPARECIMENTO": str(turnout), "QT_APTOS": str(aptos),
        "DS_TIPO_VOTAVEL": "Válido",
    }
    db.execute("INSERT INTO votes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
               ("synthetic", "BU.csv", line, kind, uf, city, zone, sec,
                turn, "1", cand, votes, json.dumps(obj, ensure_ascii=False)))


class BasicStatistics(unittest.TestCase):
    def test_benford_probabilities_sum_to_one(self):
        for mode in ("first", "second"):
            probabilities = sf.benford_expected(mode)
            self.assertAlmostEqual(sum(probabilities.values()), 1., places=12)
        self.assertEqual(sf.first_digit(987), 9)
        self.assertEqual(sf.second_digit(987), 8)
        self.assertEqual(sf.second_digit(10), 0)

    def test_digit_applicability_requires_size_and_range(self):
        result = sf.digit_diagnostic([12] * 150, "first", "test", "BA", "1", "13")
        self.assertEqual(result["aplicabilidade"], "insuficiente")
        self.assertEqual(result["qui_quadrado_descritivo"], "")
        data = [10 + (i * 37) % 993 for i in range(400)]
        result = sf.digit_diagnostic(data, "second", "test", "BA", "1", "13")
        self.assertEqual(result["aplicabilidade"], "exploratorio")
        self.assertTrue(float(result["qui_quadrado_descritivo"]) >= 0)

    def test_correlation_not_a_causal_test(self):
        self.assertAlmostEqual(sf.correlation([(x, x / 100) for x in range(40)]), 1)
        self.assertIsNone(sf.correlation([(1, 1)] * 80))
        self.assertIsNone(sf.correlation([(x, x) for x in range(3)]))

    def test_pipeline_creates_reports_and_does_not_claim_fraud(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = sqlite3.connect(":memory:")
            urnas.schema(db)
            db.commit()
            line = 2
            for sec in range(1, 66):
                vote13 = 65 + ((sec * 19) % 35)
                vote22 = 165 - vote13
                if sec == 50:
                    vote13, vote22 = 5, 160
                turnout = 180 + sec % 8
                aptos = 240 + sec % 11
                if sec == 49:
                    aptos = 100  # Inconsistencia: mais comparecimento do que aptos
                for cand, count in (("13", vote13), ("22", vote22)):
                    data_row(db, line, "BA", "33693", "177", str(sec), "1",
                             cand, count, turnout, aptos)
                    line += 1
            # Outra fonte com voto duplicado nao pode contaminar os testes de BU.
            data_row(db, line, "BA", "33693", "177", "1", "1",
                     "13", 9000, 9500, 10000, kind="secao_nacional")
            result = sf.analyze(db, Path(tmp) / "out")
            self.assertEqual(result["secoes"], 65)
            self.assertEqual(result["linhas_processadas"], 130)
            self.assertEqual(result["municipios_grupos"], 1)
            self.assertEqual(result["status"], "analise_concluida")
            self.assertFalse(result["cobertura_completa_confirmada"])
            self.assertEqual(result["cobertura_por_uf_e_turno"][0]["secoes"], 65)
            self.assertGreaterEqual(result["desvios_locais_sinalizados"], 1)
            self.assertIn("nao", " ".join(result["limites"]).lower())
            folder = Path(tmp) / "out"
            for name in ("benford.csv", "digitos_finais.csv", "desvios_municipais.csv",
                         "participacao_correlacao.csv", "consistencia_por_secao.csv",
                         "perfil_participacao_voto.csv", "forma_distribuicao_municipal.csv",
                         "estatistica_resumo.json"):
                self.assertTrue((folder / name).exists(), name)
            with (folder / "consistencia_por_secao.csv").open(encoding="utf-8-sig") as stream:
                data = stream.read()
                self.assertIn("COMPARECIMENTO_INVALIDO", data)
            previous = (folder / "desvios_municipais.csv").read_bytes()
            result2 = sf.analyze(db, folder)
            self.assertEqual(result2["secoes"], 65)
            self.assertEqual(previous, (folder / "desvios_municipais.csv").read_bytes())

    def test_empty_database_reports_insufficient_not_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = sqlite3.connect(":memory:")
            urnas.schema(db)
            result = sf.analyze(db, tmp)
            self.assertEqual(result["status"], "SEM_DADOS_BU_PRESIDENTE")
            self.assertEqual(result["secoes"], 0)


if __name__ == "__main__":
    unittest.main()
