"""Testes offline do gerenciador de boletins de urna (sem depender do TSE)."""
import io
import json
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path

import urnas


class UrnasTests(unittest.TestCase):
    def test_selection_and_ufs(self):
        sources = {
            "bu": {"resources": [
                {"id": "1", "name": "BA - Boletim de Urna - Primeiro turno",
                 "url": "https://cdn.tse.jus.br/bweb_1t_BA_05102026.zip"},
                {"id": "2", "name": "MG - Boletim de Urna - Primeiro turno",
                 "url": "https://cdn.tse.jus.br/bweb_1t_MG_05102026.zip"},
                {"id": "3", "name": "BA - Hash SHA2 - Primeiro turno",
                 "url": "https://cdn.tse.jus.br/hash_1t_BA.txt"}]},
            "secao": {"resources": [
                {"id": "4", "name": "BA - Votação por seção eleitoral - 2026",
                 "url": "https://cdn.tse.jus.br/votacao_secao_2026_BA.zip"},
                {"id": "5", "name": "Votação por município",
                 "url": "https://cdn.tse.jus.br/municipio.zip"}]},
            "artefatos": {"resources": []}}
        picked = urnas.select_resources(sources, ["bu", "secao"], ["BA"], 1)
        self.assertEqual(len(picked), 3)
        self.assertEqual({x[0] for x in picked}, {"bu", "secao"})
        self.assertEqual({x[1] for x in picked}, {"BA"})

    def test_sqlite_import_reconcile_export_idempotence(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            db = sqlite3.connect(":memory:")
            urnas.schema(db)
            db.commit()
            header = ("SG_UF;CD_MUNICIPIO;NR_ZONA;NR_SECAO;NR_TURNO;"
                      "DS_CARGO_PERGUNTA;NR_VOTAVEL;QT_VOTOS\n")
            bu_data = (header + "BA;33693;177;111;1;Presidente;13;100\n"
                       "BA;33693;177;111;1;Presidente;22;80\n")
            sec_data = (header + "BA;33693;177;111;1;Presidente;13;100\n"
                        "BA;33693;177;111;1;Presidente;22;81\n")
            for name, data, kind in (("bu.zip", bu_data, "bu"),
                                     ("secao.zip", sec_data, "secao")):
                file = base / name
                with zipfile.ZipFile(file, "w") as archive:
                    archive.writestr("resultados.csv", data.encode("latin-1"))
                checksum = urnas.sha256_file(file)
                self.assertEqual(urnas.import_file(db, file, kind, kind, checksum), 2)
                self.assertEqual(urnas.import_file(db, file, kind, kind, checksum), 0)

            self.assertEqual(db.execute("SELECT COUNT(*) FROM votes").fetchone()[0], 4)
            csvpath = base / "dif.csv"
            urnas.reconcile(db, csvpath, ["BA"], 1)
            text = csvpath.read_text(encoding="utf-8-sig")
            self.assertIn("DIFERENTE", text)
            self.assertIn("80;81;-1", text)
            report = json.loads(csvpath.with_suffix(".summary.json").read_text(encoding="utf-8"))
            self.assertEqual(report["keys_compared"], 2)
            self.assertEqual(report["different_or_missing"], 1)

            exp = base / "consulta.csv"
            urnas.export_rows(db, exp, ["BA"], "33693", "177", "111", 1, "bu", "13")
            self.assertIn("Presidente", exp.read_text(encoding="utf-8-sig"))

    def test_separate_national_section_source_and_preserve_details(self):
        sample = {
            "secao": {"resources": [
                {"id": "n", "name": "Presidente - Votação por seção eleitoral - 2026",
                 "url": "https://cdn.tse.jus.br/presidente.zip"},
                {"id": "a", "name": "AC - Votação por seção eleitoral - 2026",
                 "url": "https://cdn.tse.jus.br/votacao_secao_2026_AC.zip"},
                {"id": "d", "name": "Detalhe da apuração por seção eleitoral",
                 "url": "https://cdn.tse.jus.br/detalhe_secao.zip"}]},
            "bu": {"resources": []}, "artefatos": {"resources": []}}
        rows = urnas.select_resources(sample, ["secao"], [], None)
        self.assertEqual({r[0] for r in rows},
                         {"secao", "secao_nacional", "secao_detalhe"})

    def test_filename_parsing_and_sqlite_reports(self):
        self.assertEqual(
            urnas.section_from_name("p003220-ba-m33693-z0177-s0111.bu"),
            ("BA", "33693", "177", "111"))
        with tempfile.TemporaryDirectory() as tmp:
            db = sqlite3.connect(":memory:")
            urnas.schema(db)
            db.execute("""INSERT INTO archive_entries
                (resource_key,member,bytes,extensao,uf,municipio,zona,secao,sha256)
                VALUES('x','test.bu',100,'.bu','BA','33693','177','111','abc')""")
            urnas.write_analysis_reports(db, Path(tmp))
            self.assertIn("BA;.bu;1;100;1;1",
                          (Path(tmp) / "arquivos_por_uf.csv").read_text(encoding="utf-8-sig"))

    def test_binary_archives_are_catalogued_without_claiming_decoding(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "artefatos.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("p003220-ba-m33693-z0177-s0111.bu", b"binary")
                archive.writestr("p003220-ba-m33693-z0177-s0111.rdv", b"binary")
            db = sqlite3.connect(":memory:")
            urnas.schema(db)
            db.commit()
            urnas.import_file(db, path, "artefatos", "artefatos", urnas.sha256_file(path))
            self.assertEqual(db.execute("SELECT COUNT(*) FROM archive_entries").fetchone()[0], 2)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM votes").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
