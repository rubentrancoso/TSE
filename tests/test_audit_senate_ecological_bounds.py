"""Testes da auditoria leve dos limites Presidente x Senado, sem SQLite."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import tempfile
import unittest

import audit_senate_ecological_bounds as a
from reconcile_stream import sha256


class SenateEcologicalAuditTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.analysis = self.root / "analysis"
        self.base = self.analysis / "entre_cargos" / "fixture"
        self.directory = self.base / "limites_presidencia_senado_inversoes"
        self.directory.mkdir(parents=True)
        self.mapping = self.root / "map.csv"
        self.mapping.write_text("UF;numero\nAC;170\n", encoding="utf-8")
        self.review = (self.base / "diagnostico_conjunto" /
                       "revisao_inversoes" / "summary.json")
        self.review.parent.mkdir(parents=True)
        self.review.write_text('{"senadores_distintos_em_inversoes":1}\n', encoding="utf-8")
        self.fp = "a" * 64
        self.analysis.mkdir(exist_ok=True)
        (self.analysis / "reconciliacao_bu_secao.summary.json").write_text(
            json.dumps({"fingerprint": self.fp}), encoding="utf-8")
        self.csv = self.directory / "limites_por_senador_presidente.csv"
        self.rows = [
            {
                "UF": "AC", "senador": "170",
                "nome_urna": "Nome documentado", "partido": "PARTIDO",
                "presidente": "13", "secoes_validas": 1,
                "secoes_com_senador": 1, "votos_senador": 5,
                "votos_presidenciais_do_candidato": 8,
                "comparecimento_presidencial": 10,
                "eleitorado_senado_naquelas_secoes": 10,
                "sobreposicao_minima": 3, "sobreposicao_maxima": 5,
                "senador_fora_do_presidente_minimo": 0,
                "secoes_com_sobreposicao_obrigatoria": 1,
                "pct_minima_dos_votos_senador": 60.0,
                "pct_maxima_dos_votos_senador": 100.0,
            }, {
                "UF": "AC", "senador": "170",
                "nome_urna": "Nome documentado", "partido": "PARTIDO",
                "presidente": "22", "secoes_validas": 1,
                "secoes_com_senador": 1, "votos_senador": 5,
                "votos_presidenciais_do_candidato": 2,
                "comparecimento_presidencial": 10,
                "eleitorado_senado_naquelas_secoes": 10,
                "sobreposicao_minima": 0, "sobreposicao_maxima": 2,
                "senador_fora_do_presidente_minimo": 3,
                "secoes_com_sobreposicao_obrigatoria": 0,
                "pct_minima_dos_votos_senador": 0.0,
                "pct_maxima_dos_votos_senador": 40.0,
            },
        ]
        self.save()

    def save(self):
        with self.csv.open("w", encoding="utf-8", newline="") as f:
            fields = list(self.rows[0].keys())
            w = csv.DictWriter(f, fieldnames=fields, delimiter=";")
            w.writeheader()
            w.writerows(self.rows)
        meta = {
            "source_fingerprint": self.fp, "status": "LIMITES_CALCULADOS",
            "csv": str(self.csv), "csv_sha256": sha256(self.csv),
            "candidate_mapping_sha256": sha256(self.mapping),
            "review_summary_sha256": sha256(self.review),
            "pares_presidencia_senado": len(self.rows),
            "candidatos_distintos": 1, "por_candidato": self.rows,
        }
        (self.directory / "summary.json").write_text(
            json.dumps(meta), encoding="utf-8")
        return meta

    def test_correct_bounds_and_complements(self):
        report = a.run(self.root, docs_path=self.mapping)
        self.assertEqual(report["numero_senadores"], 1)
        self.assertEqual(report["numero_pares"], 2)
        vals = report["ranking_minimo_com_13"][0]
        self.assertEqual(vals["min"], 3)
        self.assertEqual(vals["pct"], 60.0)
        self.assertEqual(report["ranking_minimo_fora_22"][0]["min"], 3)
        self.assertEqual(report["ranking_minimo_fora_22"][0]["pct"], 60.0)
        self.assertEqual(sha256(Path(report["output"])),
                         report["output_sha256"])

    def test_csv_integrity_rejected(self):
        metadata = self.save()
        with self.csv.open("a", encoding="utf-8") as f:
            f.write("modified\n")
        with self.assertRaises(RuntimeError):
            a.audit_rows(self.csv, metadata)

    def test_impossible_bounds_rejected_even_with_matching_hash(self):
        self.rows[0]["sobreposicao_minima"] = 6
        metadata = self.save()
        with self.assertRaises(RuntimeError):
            a.audit_rows(self.csv, metadata)

    def test_unexpected_presidential_choice_rejected(self):
        self.rows[1]["presidente"] = "99"
        metadata = self.save()
        with self.assertRaises(RuntimeError):
            a.audit_rows(self.csv, metadata)

    def test_modified_mapping_rejected(self):
        self.mapping.write_text("tampered", encoding="utf-8")
        with self.assertRaises(RuntimeError):
            a.run(self.root, docs_path=self.mapping)

    def test_missing_comparison_rejected(self):
        self.rows.pop()
        metadata = self.save()
        with self.assertRaises(RuntimeError):
            a.audit_rows(self.csv, metadata)


if __name__ == "__main__":
    unittest.main()
