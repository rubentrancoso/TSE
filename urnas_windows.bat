@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>&1
if errorlevel 1 (
  echo Python nao encontrado no PATH.
  pause
  exit /b 1
)
:menu
cls
echo ====================================================
echo TSE 2026 - GERENCIADOR DE BOLETINS / VOTOS POR SECAO
echo ====================================================
echo 1 - Consultar catalogo oficial sem baixar
echo 2 - Baixar e indexar BU + votacao de uma UF
echo 3 - Baixar documentos binarios BU/RDV/LOG de uma UF
echo 4 - BAIXAR TUDO do 1o turno (volume elevado)
echo 5 - Exportar votos de uma secao do banco SQLite
echo 6 - Reconciliar BU versus votacao por secao
echo 7 - Conferir integridade dos arquivos locais
echo 0 - Sair
echo.
choice /c 12345670 /n /m "Opcao: "
if errorlevel 8 exit /b 0
if errorlevel 7 goto verify
if errorlevel 6 goto reconcile
if errorlevel 5 goto export
if errorlevel 4 goto full
if errorlevel 3 goto binary
if errorlevel 2 goto state
if errorlevel 1 goto status
:status
python urnas.py status
goto done
:state
set /p UF="UF (exemplo: BA): "
python urnas.py fetch --uf %UF% --kind bu --kind secao
goto done
:binary
set /p UF="UF (exemplo: BA): "
python urnas.py fetch --uf %UF% --kind artefatos
goto done
:full
echo AVISO: grandes arquivos serao baixados para H:\TSE\forensics\urnas.
echo Os CSVs serao importados para SQLite, consumindo espaco adicional.
choice /c SN /n /m "Confirma descarga completa? S/N: "
if errorlevel 2 goto menu
python urnas.py fetch --all --kind bu --kind secao --kind artefatos
goto done
:export
set /p UF="UF (ex.: BA): "
set /p MU="Codigo do municipio TSE: "
set /p ZO="Zona: "
set /p SE="Secao: "
python urnas.py export --uf %UF% --municipio %MU% --zona %ZO% --secao %SE%
goto done
:reconcile
set /p UF="UF (ex.: BA): "
python urnas.py reconcile --uf %UF%
goto done
:verify
python urnas.py verify
:done
echo.
pause
goto menu
