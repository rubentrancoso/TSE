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
NOTEBOOK_ZONE = REPO / "notebooks" / "TSE_2026_Laboratorio_Forense_Fase_V.ipynb"
NOTEBOOK_PLACEBOS = REPO / "notebooks" / "TSE_2026_Laboratorio_Forense_Fase_W.ipynb"
NOTEBOOK_EA20 = REPO / "notebooks" / "TSE_2026_Laboratorio_Forense_Fase_X.ipynb"
NOTEBOOK_TIMING = REPO / "notebooks" / "TSE_2026_Laboratorio_Forense_Fase_Y.ipynb"
NOTEBOOK_PUBLIC = REPO / "notebooks" / "TSE_2026_Painel_Publico_Forense.ipynb"
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
ZONE_FILES = (
    "phase5q_zone_holdout_2026_summary.json",
    "phase5q_zone_holdout_minutes_2026.csv",
    "phase5q_zone_holdout_municipalities_2026.csv",
    "phase5q_zone_holdout_zones_2026.csv",
)
PLACEBO_FILES = (
    "phase5r_cutoff_placebos_2026_summary.json",
    "phase5r_cutoff_placebos_2026.csv",
    "phase5r_uf_paired_zones_2026.csv",
    "phase5r_paired_zones_2026.csv",
)
EA20_FILES = (
    "phase5s_ea20_publication_mechanics_2026_summary.json",
    "phase5s_ea20_batch_mechanics_2026.csv",
    "phase5s_ea20_equal_volume_blocks_2026.csv",
)
TIMING_FILES = (
    "phase5t_receipt_vs_publication_2026_summary.json",
    "phase5t_receipt_vs_publication_timeline_2026.csv",
    "phase5t_receipt_vs_publication_offsets_2026.csv",
)


def check_inputs(root: Path):
    folder = root / "analysis" / "periodicidade_bweb_2026"
    return [str(folder / name) for name in DATA_FILES if not (folder / name).is_file()]


def env_python(directory: Path) -> Path:
    return directory / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def launch(root: Path, check_only: bool = False, tecnico: bool = False) -> int:
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
    folder = root / "analysis" / "periodicidade_bweb_2026"
    phase_v_present = (folder / ZONE_FILES[0]).is_file()
    notebook = NOTEBOOK_ZONE if phase_v_present else NOTEBOOK
    if phase_v_present:
        pending = [str(folder / name) for name in ZONE_FILES if not (folder / name).is_file()]
        if pending:
            print("[ERRO] A Fase V esta incompleta. Reexecute V no menu antes de U:")
            for item in pending:
                print("  - " + item)
            return 1
        if not notebook.is_file():
            print("[ERRO] Notebook V nao encontrado: " + str(notebook))
            return 1
    phase_w_present = (folder / PLACEBO_FILES[0]).is_file()
    if phase_w_present:
        missing_w = [str(folder / name) for name in PLACEBO_FILES
                     if not (folder / name).is_file()]
        if missing_w:
            print("[ERRO] A Fase W esta incompleta; reexecute W.")
            for item in missing_w:
                print("  - " + item)
            return 1
        if not NOTEBOOK_PLACEBOS.is_file():
            print("[ERRO] Notebook W nao encontrado: " + str(NOTEBOOK_PLACEBOS))
            return 1
        notebook = NOTEBOOK_PLACEBOS
    phase_x_present = (folder / EA20_FILES[0]).is_file()
    if phase_x_present:
        missing_x = [str(folder / name) for name in EA20_FILES
                     if not (folder / name).is_file()]
        if missing_x:
            print("[ERRO] A Fase X esta incompleta; reexecute X.")
            for item in missing_x:
                print("  - " + item)
            return 1
        if not NOTEBOOK_EA20.is_file():
            print("[ERRO] Notebook X nao encontrado: " + str(NOTEBOOK_EA20))
            return 1
        notebook = NOTEBOOK_EA20
    phase_y_present = (folder / TIMING_FILES[0]).is_file()
    if phase_y_present:
        missing_y = [str(folder / name) for name in TIMING_FILES
                     if not (folder / name).is_file()]
        if missing_y:
            print("[ERRO] Fase Y incompleta; reexecute Y.")
            for item in missing_y:
                print("  - " + item)
            return 1
        if not NOTEBOOK_TIMING.is_file():
            print("[ERRO] Notebook Y nao encontrado: " + str(NOTEBOOK_TIMING))
            return 1
        notebook = NOTEBOOK_TIMING
    if not tecnico:
        if not NOTEBOOK_PUBLIC.is_file():
            print("[ERRO] Notebook publico nao encontrado: " + str(NOTEBOOK_PUBLIC))
            return 1
        notebook = NOTEBOOK_PUBLIC
    if check_only:
        print("[OK] Notebook selecionado: " + str(notebook))
        print("[OK] CSVs/JSONs encontrados. Integridade SHA sera conferida no notebook.")
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
             str(notebook.relative_to(REPO)),
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
    parser.add_argument("--tecnico", action="store_true", help="Abre a fase tecnica mais recente em vez do painel publico consolidado")
    args = parser.parse_args()
    from urnas import root_path
    return launch(root_path(args.root), check_only=args.check, tecnico=args.tecnico)


if __name__ == "__main__":
    sys.exit(main())
