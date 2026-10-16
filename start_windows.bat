@echo off
setlocal EnableExtensions
cd /d "%~dp0"
where python >nul 2>nul
if not errorlevel 1 (
  set "PY=python"
) else (
  where py >nul 2>nul
  if errorlevel 1 (
    echo [ERRO] Python 3 nao encontrado.
    pause
    exit /b 1
  )
  set "PY=py -3"
)
:menu
cls
echo ==========================================================
echo TSE 2026 - PAINEL E INVESTIGACAO FORENSE
echo ==========================================================
echo.
echo [1] COLETA COMPLETA: localizar, baixar tudo, validar,
echo     reaproveitar arquivos locais, indexar e reconciliar
echo [2] Abrir painel de apuracao
echo [3] Consultar disponibilidade e arquivos ja baixados
echo [4] Coleta opcional por UF (BU, votacao e arquivos de urna)
echo [5] Exportar registros de uma secao
echo [6] Reconciliar fontes locais novamente
echo [7] Verificar integridade dos downloads
echo [0] Sair
echo.
choice /C 12345670 /N /M "Selecione: "
if errorlevel 8 exit /b 0
if errorlevel 7 goto verify
if errorlevel 6 goto reconcile
if errorlevel 5 goto export
if errorlevel 4 goto state
if errorlevel 3 goto status
if errorlevel 2 goto panel
if errorlevel 1 goto full

:full
echo.
echo COLETA INTEGRAL DE 2026 - sem repetir arquivos ja validos.
echo Dados volumosos em H:\TSE\forensics\.
%PY% collect_forensics.py all --download-portal-files
goto done

:panel
%PY% server.py
goto done

:status
%PY% urnas.py status --all --kind bu --kind secao --kind artefatos
goto done

:state
set "UF="
set /p "UF=UF (exemplo: BA): "
if not defined UF goto menu
%PY% urnas.py fetch --uf "%UF%" --kind bu --kind secao --kind artefatos
goto done

:export
set "UF="
set "MU="
set "ZO="
set "SE="
set /p "UF=UF: "
set /p "MU=Codigo do municipio: "
set /p "ZO=Zona: "
set /p "SE=Secao: "
%PY% urnas.py export --uf "%UF%" --municipio "%MU%" --zona "%ZO%" --secao "%SE%"
goto done

:reconcile
%PY% urnas.py reconcile --turn 1
goto done

:verify
%PY% urnas.py verify
goto done

:done
echo.
if errorlevel 1 (
  echo [AVISO] A rotina encerrou com erro; escolha 1 para continuar de onde parou.
) else (
  echo Rotina concluida. Veja os relatórios e mensagens acima.
)
pause
goto menu
