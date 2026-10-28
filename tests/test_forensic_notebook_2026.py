"""Testes do laboratorio Jupyter sem deps externas nem disco H.

As celulas podem ter sido executadas/salvas pelo investigador.
Isso e estado NORMAL do notebook, nao erro nem motivo para bloquear U.
"""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "notebooks" / "TSE_2026_Laboratorio_Forense_Fases_S_T.ipynb"


def validate_notebook(doc):
    if doc["nbformat"] != 4:
        raise AssertionError("Formato do notebook deve ser v4")
    if len(doc["cells"]) < 12:
        raise AssertionError("Notebook tem poucas celulas")
    if doc["cells"][0]["cell_type"] != "markdown":
        raise AssertionError("Primeira celula nao e markdown")
    for cell in doc["cells"]:
        if cell["cell_type"] not in ("code", "markdown"):
            raise AssertionError("Tipo de celula inesperado")
        if cell["cell_type"] != "code":
            continue
        code = "".join(cell["source"])
        compile(code, "<notebook>", "exec")
        count = cell.get("execution_count")
        if count is not None and (type(count) is not int or count < 0):
            raise AssertionError("Numero de execucao Jupyter invalido")
        if not isinstance(cell.get("outputs", []), list):
            raise AssertionError("Outputs Jupyter devem ser lista")
        # Nunca exigir count None nem outputs []:
        # o Jupyter grava contagens e graficos apos Run All Cells.


class ForensicNotebook2026Tests(unittest.TestCase):
    def test_notebook_json_and_cells(self):
        doc = json.loads(NB.read_text(encoding="utf-8"))
        validate_notebook(doc)

    def test_accepts_executed_notebook_saved_by_user(self):
        doc = json.loads(NB.read_text(encoding="utf-8"))
        code_cell = next(c for c in doc["cells"] if c["cell_type"] == "code")
        code_cell["execution_count"] = 1
        code_cell["outputs"] = [{
            "output_type": "stream",
            "name": "stdout",
            "text": ["Resultado de teste ja executado\n"]
        }]
        validate_notebook(doc)

    def test_no_network_or_raw_download(self):
        doc = json.loads(NB.read_text(encoding="utf-8"))
        source = "\n".join(
            "".join(c["source"]) for c in doc["cells"]
            if c["cell_type"] == "code"
        )
        for forbidden in ("requests.get(", "urlopen(", "subprocess.run(", "pd.read_sql("):
            self.assertNotIn(forbidden, source)

    def test_launcher_and_batch_menu(self):
        batch = (ROOT / "start_windows.bat").read_text(encoding="utf-8")
        self.assertRegex(batch, r"(?m)^echo \[U\] LABORATORIO\b")
        self.assertIn("launch_forensic_notebook.py", batch)
        u_command = batch.split(":forensic_notebook_2026\\n", 1)[1].split("\\n:validate_failed", 1)[0]
        self.assertIn("%PY% launch_forensic_notebook.py", u_command)
        self.assertNotIn("unittest", u_command)
        self.assertIn("if errorlevel 30 goto forensic_notebook_2026", batch)
        options = re.search(r"(?m)^choice /C ([A-Z0-9]+) /N /M", batch)
        self.assertIsNotNone(options)
        choices = options.group(1)
        self.assertEqual(len(choices), len(set(choices)))
        self.assertEqual(choices.index("U") + 1, 30)
        self.assertEqual(choices[-1], "0")
        launcher = (ROOT / "launch_forensic_notebook.py").read_text(encoding="utf-8")
        compile(launcher, "launch_forensic_notebook.py", "exec")
        self.assertIn("NOTEBOOK_TIMING", launcher)


if __name__ == "__main__":
    unittest.main()
