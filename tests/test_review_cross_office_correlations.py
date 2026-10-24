"""Testes offline da revisao dos pares com inversao territorial."""
import csv
import json
from pathlib import Path
import tempfile
import unittest

import review_cross_office_correlations as review
from reconcile_stream import sha256


def row(office, president, candidate, r0, r1,
        flip=0, shift=0, senate_votes=None):
    return {
        "cargo": office, "UF": "AC", "turno": "1",
        "presidente": president, "candidato": candidate,
        "secoes": "1500",
        "grupos_geograficos_com_variacao": "20",
        "votos_candidato_disponiveis": (
            str(senate_votes) if senate_votes is not None else ""),
        "r_bruto": str(r0), "r_ajustado": str(r1),
        "abs_mudanca": str(round(abs(r0-r1), 6)),
        "apto_criterios_comuns": "1",
        "apto_com_filtro_de_votos": (
            "0" if senate_votes is not None and senate_votes < 1000 else "1"),
        "sinal_oposto": str(flip),
        "mudanca_pelo_menos_020": str(shift),
        "sem_coeficiente": "0",
    }


class ReviewInversionsTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.fp = "a" * 64
        analysis = self.root / "analysis"
        analysis.mkdir()
        (analysis / "reconciliacao_bu_secao.summary.json").write_text(
            json.dumps({"fingerprint": self.fp}), encoding="utf-8")
        self.folder = (analysis / "entre_cargos" / "fixture" /
                       "diagnostico_conjunto")
        self.folder.mkdir(parents=True)
        self.all_path = self.folder / "todos_os_pares.csv"
        self.reg_path = self.folder / "por_uf_cargo.csv"
        self.reg_path.write_text("cargo;UF\nsenador;AC\n",
                                 encoding="utf-8")
        self.rows = [
            row("governador", "22", "10", .6, .3, shift=1),
            row("governador", "13", "10", -.6, -.55),
            row("governador", "22", "55", -.2, -.15),
            row("governador", "13", "55", .2, .15),
            row("senador", "22", "170", .6, -.35,
                flip=1, shift=1, senate_votes=10000),
            row("senador", "13", "170", -.6, .35,
                flip=1, shift=1, senate_votes=10000),
            row("senador", "22", "171", .8, .7, senate_votes=50),
            row("senador", "13", "171", .05, -.02, senate_votes=50),
        ]
        self._save()

    def _save(self):
        with self.all_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=review.FIELDS,
                                    delimiter=";")
            writer.writeheader()
            writer.writerows(self.rows)
        self.summary = {
            "status": "DESCRITIVO_CONCLUIDO",
            "fingerprint": self.fp, "pairs": 8,
            "outputs": {
                "todos_os_pares.csv": sha256(self.all_path),
                "por_uf_cargo.csv": sha256(self.reg_path)},
            "thresholds_exploratorios": {
                "min_sections": 1000, "min_zones": 10,
                "min_senate_votes": 1000},
            "totals_by_office": {
                "governador": {
                    "pares": 4, "aptos_comuns": 4,
                    "aptos_filtro_votos": 4,
                    "sinais_opostos": 0, "mudancas_020": 1},
                "senador": {
                    "pares": 4, "aptos_comuns": 4,
                    "aptos_filtro_votos": 2,
                    "sinais_opostos": 2, "mudancas_020": 2},
            },
        }
        (self.folder / "summary.json").write_text(
            json.dumps(self.summary), encoding="utf-8")

    def test_distinct_senator_and_derived_files(self):
        out = review.run(self.root)
        self.assertEqual(out["pares_totais"], 8)
        self.assertEqual(out["pares_senado_com_inversao"], 2)
        self.assertEqual(out["senadores_distintos_em_inversoes"], 1)
        self.assertEqual(out["ufs_com_inversao_senado"], 1)
        self.assertEqual(out["pares_governador_com_inversao"], 0)
        self.assertEqual(out["mudancas_020_totais"], 3)
        self.assertEqual(out["senado_inversoes_por_uf"][0]["UF"], "AC")
        self.assertEqual(out["senado_pares_invertidos"][0]["senador"], "170")
        for entry in out["arquivos"].values():
            self.assertEqual(entry["sha256"], sha256(Path(entry["path"])))

    def test_original_sha_mismatch_rejected(self):
        self.all_path.write_text("trocado", encoding="utf-8")
        with self.assertRaises(RuntimeError):
            review.run(self.root)

    def test_flag_inconsistent_rejected(self):
        self.rows[4]["sinal_oposto"] = "0"
        self._save()
        with self.assertRaises(RuntimeError):
            review.run(self.root)

    def test_different_summary_rejected(self):
        self.summary["totals_by_office"]["senador"]["sinais_opostos"] = 3
        (self.folder / "summary.json").write_text(
            json.dumps(self.summary), encoding="utf-8")
        with self.assertRaises(RuntimeError):
            review.run(self.root)

    def test_missing_uf_aggregate_rejected(self):
        self.reg_path.write_text("changed", encoding="utf-8")
        with self.assertRaises(RuntimeError):
            review.run(self.root)


if __name__ == "__main__":
    unittest.main()
