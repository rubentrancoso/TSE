"""Testes estaticos do laboratorio Jupyter; sem deps externas nem disco H."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "notebooks" / "TSE_2026_Laboratorio_Forense_Fases_S_T.ipynb"


class ForensicNotebook2026Tests(unittest.TestCase):
    def test_notebook_json_and_cells(self):
        doc = json.loads(NB.read_text(encoding="utf-8"))
        self.assertEqual(doc["nbformat"], 4)
        self.assertGreaterEqual(len(doc["cells"]), 12)
        self.assertEqual(doc["cells"][0]["cell_type"], "markdown")
        self.assertTrue(all(c["cell_type"] in ("code", "markdown") for c in doc["cells"]))
        for cell in doc["cells"]:
            if cell["cell_type"] == "code":
                src = "".join(cell["source"])
                compile(src, "<notebook>", "exec")
                self.assertEqual(cell["execution_count"], None)
                self.assertEqual(cell["outputs"], [])

    def test_no_network_or_raw_download(self):
        doc = json.loads(NB.read_text(encoding="utf-8"))
        source = "\n".join("".join(c["source"]) for c in doc["cells"] if c["cell_type"] == "code")
        for forbidden in ("requests.get(", "urlopen(", "subprocess.run(", "pd.read_sql("):
            self.assertNotIn(forbidden, source)

    def test_launcher_and_batch_menu(self):
        batch = (ROOT / "start_windows.bat").read_text(encoding="utf-8")
        self.assertIn("[U] LABORATORIO FORENSE JUPYTER", batch)
        self.assertIn("launch_forensic_notebook.py", batch)
        self.assertIn("ABCDEFGHIJKLMNOPQRSTU0", batch)
        launcher = (ROOT / "launch_forensic_notebook.py").read_text(encoding="utf-8")
        compile(launcher, "launch_forensic_notebook.py", "exec")


if __name__ == "__main__":
    unittest.main()
