#!/usr/bin/env python3
"""Abre o laboratorio forense no Jupyter pelo menu U. Nenhum dado eleitoral e baixado."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parent
NOTEBOOK = REPO / "notebooks" / "TSE_2026_Laboratorio_Forense_Fases_S_T.ipynb"
VENV = REPO / ".venv_tse_notebook"
DATA_FILES = (
    "phase5o_operational_curve_2026_summary.json",
    "phase5o_ea20_time_axes_2026.csv",
    "phase5o_bweb_receipt_geo_2026.csv",
    "phase5p_holdout_geographic_curve_2026_summary.json",
    "phase5p_holdout_receipt_curve_2026.csv",
    "phase5p_holdout_by_uf_2026.csv",
    "phase5p_holdout_by_municipality_2026.csv",
)


def check_inputs(root: Path):
    folder = root / "analysis" / "periodicidade_bweb_2026"
    return [str(folder / name) for name in DATA_FILES if not (folder / name).is_file()]


def env_python(directory: Path) -> Path:
    return directory / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def launch(root: Path, check_only: bool = False) -> int:
    if not NOTEBOOK.is_file():
        print("[ERRO] Notebook nao encontrado no repositorio: " + str(NOTEBOOK))
        return 1
    missing = check_inputs(root)
    if missing:
        print("[ERRO] Faltam resultados locais das opcoes S e/ou T:")
        for name in missing:
            print("  - " + name)
        print("Execute primeiro S e T no start_windows.bat. Nenhum dado foi baixado.")
        return 1
    if check_only:
        print("[OK] Notebook e relatorios S/T presentes. Integridade SHA sera conferida no notebook.")
        return 0
    python = env_python(VENV)
    if not python.is_file():
        print("[AMBIENTE] Criando ambiente isolado do Jupyter: " + str(VENV), flush=True)
        try:
            subprocess.run([sys.executable, "-m", "venv", str(VENV)], cwd=str(REPO), check=True)
        except subprocess.CalledProcessError as exc:
            print("[ERRO] Nao foi possivel criar o ambiente Python: " + str(exc))
            return 1
    try:
        installed = subprocess.run(
            [str(python), "-c", "import jupyterlab, pandas, matplotlib, ipykernel"],
            cwd=str(REPO), capture_output=True, text=True,
        ).returncode == 0
        if not installed:
            print("[AMBIENTE] Instalando JupyterLab, pandas e matplotlib no ambiente isolado (uma vez).", flush=True)
            print("[AMBIENTE] Apenas dependencias Python; nao baixa BUs nem bases eleitorais.", flush=True)
            subprocess.run(
                [str(python), "-m", "pip", "install", "--disable-pip-version-check",
                 "jupyterlab>=4,<5", "pandas>=2,<4", "matplotlib>=3,<4", "ipykernel>=6,<8"],
                cwd=str(REPO), check=True,
            )
        print("[JUPYTER] Abrindo laboratorio no navegador. Ctrl+C encerra o servidor.", flush=True)
        return subprocess.run(
            [str(python), "-m", "jupyterlab",
             str(NOTEBOOK.relative_to(REPO)),
             "--notebook-dir=" + str(REPO)],
            cwd=str(REPO),
        ).returncode
    except (subprocess.CalledProcessError, OSError) as exc:
        print("[ERRO] Jupyter nao iniciou: " + str(exc))
        return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", help="Diretorio local de urnas, por padrao H:/TSE/forensics/urnas")
    parser.add_argument("--check", action="store_true", help="Verifica entradas sem instalar/abrir Jupyter")
    args = parser.parse_args()
    from urnas import root_path
    return launch(root_path(args.root), check_only=args.check)


if __name__ == "__main__":
    sys.exit(main())
