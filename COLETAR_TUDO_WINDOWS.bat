@echo off
setlocal
cd /d "%~dp0"

echo Coleta forense completa dos dados oficiais do TSE
echo Os arquivos serao salvos em data\forensics
echo.

where py >nul 2>nul
if %errorlevel% equ 0 (
    py -3 collect_forensics.py
) else (
    python collect_forensics.py
)

echo.
if %errorlevel% equ 0 (
    echo Coleta concluida.
) else (
    echo A coleta terminou com avisos ou arquivos indisponiveis. Consulte os manifestos.
)
pause
