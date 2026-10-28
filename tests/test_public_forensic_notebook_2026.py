"""Painel público: testes de integridade editorial e navegação, sem dados H."""
from __future__ import annotations

import json
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]
PANEL=ROOT/"notebooks"/"TSE_2026_Painel_Publico_Forense.ipynb"


class ForensicPublicNotebookTests(unittest.TestCase):
    def test_notebook_compiles_and_contains_reproducible_sources(self):
        nb=json.loads(PANEL.read_text(encoding="utf-8"))
        self.assertEqual(nb["nbformat"],4)
        self.assertGreaterEqual(len(nb["cells"]),17)
        body="\n".join("".join(c["source"]) for c in nb["cells"])
        self.assertIn("primeiro turno",body.lower())
        self.assertIn("alteração",body.lower())
        self.assertIn("não",body.lower())
        for phase in ("phase5q_zone_holdout_2026_summary.json",
                      "phase5r_cutoff_placebos_2026_summary.json",
                      "phase5s_ea20_publication_mechanics_2026_summary.json",
                      "phase5t_receipt_vs_publication_2026_summary.json"):
            self.assertIn(phase,body)
        self.assertIn("SHA-256",body)
        self.assertIn("checked_csv",body)
        self.assertIn("digest(actual_ea20)",body)
        self.assertIn("relatorio_publico_forense_2026.html",body)
        self.assertIn("base64.b64encode",body)
        for c in nb["cells"]:
            if c["cell_type"]=="code":
                compile("".join(c["source"]),"<public-forensic-notebook>","exec")
                self.assertTrue(c.get("execution_count") is None
                                or (type(c["execution_count"]) is int
                                    and c["execution_count"]>=0))
                self.assertIsInstance(c.get("outputs",[]),list)
        for forbidden in ("requests.get(","urlopen(","subprocess.run("):
            self.assertNotIn(forbidden,body)

    def test_public_dashboard_is_default_and_technical_remains_accessible(self):
        launcher=(ROOT/"launch_forensic_notebook.py").read_text(encoding="utf-8")
        compile(launcher,"<forensic-launcher>","exec")
        self.assertIn("NOTEBOOK_PUBLIC",launcher)
        self.assertIn("if not tecnico:",launcher)
        self.assertIn("notebook = NOTEBOOK_PUBLIC",launcher)
        self.assertIn('"--tecnico"',launcher)
        bat=(ROOT/"start_windows.bat").read_text(encoding="utf-8")
        choices=re.search(r"(?m)^choice /C ([A-Z0-9]+) /N /M",bat)
        self.assertIsNotNone(choices)
        order=choices.group(1)
        self.assertEqual(order.index("U")+1,30)
        self.assertEqual(order.index("Z")+1,35)
        self.assertEqual(order[-1],"0")
        self.assertIn("if errorlevel 30 goto forensic_notebook_2026",bat)
        self.assertIn("if errorlevel 35 goto forensic_notebook_technical_2026",bat)
        public=bat.split("\n:forensic_notebook_2026\n",1)[1].split("\n:validate_failed",1)[0]
        technical=bat.split("\n:forensic_notebook_technical_2026\n",1)[1].split("\n:forensic_notebook_2026",1)[0]
        self.assertIn("%PY% launch_forensic_notebook.py\n",public)
        self.assertNotIn("unittest",public)
        self.assertIn("%PY% launch_forensic_notebook.py --tecnico",technical)


if __name__=="__main__":
    unittest.main()
