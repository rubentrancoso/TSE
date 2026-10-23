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

    def test_import_interrupted_after_checkpoint_resumes_without_duplicates(self):
        import hashlib
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            path = base / "massivo.zip"
            header = ("SG_UF;CD_MUNICIPIO;NR_ZONA;NR_SECAO;NR_TURNO;"
                      "CD_CARGO_PERGUNTA;NR_VOTAVEL;QT_VOTOS\n")
            rows = [f"BA;33693;177;{i};1;1;13;{i % 97}\n"
                    for i in range(1, 25001)]
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("votos.csv", (header + "".join(rows)).encode("latin-1"))
            db = sqlite3.connect(":memory:")
            urnas.schema(db)
            db.commit()
            key = "bu:test-large"
            sha = urnas.sha256_file(path)
            self.assertEqual(urnas.import_file(db, path, "bu", key, sha), 25000)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM votes").fetchone()[0], 25000)

            # Simula uma interrupcao apos confirmar o bloco de 20 mil
            # linhas, mas antes de registrar importacao concluida.
            db.execute("DELETE FROM imports WHERE resource_key=?", (key,))
            db.execute("DELETE FROM votes WHERE line > 20001 AND resource_key=?", (key,))
            db.execute("INSERT INTO import_progress VALUES(?,?,?,?)",
                       (key, sha, "2026-10-17", "2026-10-17"))
            db.execute("INSERT INTO import_checkpoints VALUES(?,?,?,?,?)",
                       (key, "votos.csv", 20001, 20000, "2026-10-17"))
            db.commit()

            self.assertEqual(urnas.import_file(db, path, "bu", key, sha), 5000)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM votes").fetchone()[0], 25000)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM import_progress").fetchone()[0], 0)
            self.assertEqual(urnas.import_file(db, path, "bu", key, sha), 0)

    def test_legacy_import_v2_is_reused(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            db = sqlite3.connect(":memory:")
            urnas.schema(db)
            db.execute("""INSERT INTO imports
                (resource_key,sha256,imported_utc,rows,files,parser_version)
                VALUES('bu:old','abc','2026-10-16',22,1,2)""")
            db.commit()
            # O arquivo nem precisa ser aberto quando importado e validado.
            self.assertEqual(urnas.import_file(db, base / "old.zip", "bu",
                                               "bu:old", "abc"), 0)

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

    def test_corrupt_sp_zip_is_quarantined_and_downloaded_cleanly_once(self):
        from unittest.mock import patch

        class Response(io.BytesIO):
            status = 200
            headers = {}

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
                archive.writestr("dados.csv", b"secoes-teste-original")
            clean = buffer.getvalue()
            corrupt = clean.replace(b"secoes-teste-original", b"secoes-teste-corrupto")
            self.assertNotEqual(clean, corrupt)
            self.assertTrue(zipfile.is_zipfile(io.BytesIO(corrupt)))
            resource = {"id": "sp-zip", "name": "SP - Arquivos transmitidos",
                        "url": "https://cdn.tse.jus.br/test-sp.zip"}
            with patch("urllib.request.urlopen",
                       side_effect=[Response(corrupt), Response(clean)]) as getter:
                dest, checksum = urnas.download(root, "artefatos", "SP", resource, 0)
                self.assertEqual(getter.call_count, 2)
                self.assertEqual(checksum, urnas.sha256_file(dest))
                self.assertEqual(dest.read_bytes(), clean)
            quarantined = list((root / "quarantine" / "artefatos" / "SP").glob("*.bad"))
            self.assertEqual(len(quarantined), 1)
            self.assertEqual(quarantined[0].read_bytes(), corrupt)
            self.assertTrue(Path(str(quarantined[0]) + ".json").exists())

    def test_download_cache_prevents_second_network_request(self):
        from unittest.mock import patch

        class Response(io.BytesIO):
            status = 200
            headers = {}

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stream = io.BytesIO()
            with zipfile.ZipFile(stream, "w") as archive:
                archive.writestr("data.csv", b"A;B\\n1;2\\n")
            data = stream.getvalue()
            resource = {"id": "urn01", "name": "Teste BO",
                        "url": "https://cdn.tse.jus.br/test-download.zip",
                        "size": len(data), "last_modified": "2026-10-06"}
            with patch("urllib.request.urlopen", return_value=Response(data)) as fetch:
                path, digest = urnas.download(root, "bu", "BA", resource, 0)
                self.assertEqual(fetch.call_count, 1)
                self.assertEqual(urnas.sha256_file(path), digest)
            with patch("urllib.request.urlopen", side_effect=AssertionError("re-download")):
                reused, digest_again = urnas.download(root, "bu", "BA", resource, 0)
                self.assertEqual(reused, path)
                self.assertEqual(digest_again, digest)

    def test_all_turns_are_selected_by_default(self):
        datasets = {"bu": {"resources": [
            {"id": "one", "name": "AC - Boletim de Urna - Primeiro turno",
             "url": "https://cdn.tse.jus.br/bweb_1t_AC.zip"},
            {"id": "two", "name": "AC - Boletim de Urna - Segundo turno",
             "url": "https://cdn.tse.jus.br/bweb_2t_AC.zip"}]}}
        self.assertEqual(len(urnas.select_resources(datasets, ["bu"], [], None)), 2)
        self.assertEqual(len(urnas.select_resources(datasets, ["bu"], [], 1)), 1)

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
