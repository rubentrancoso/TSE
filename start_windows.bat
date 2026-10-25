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
echo [6] Reconciliar fontes locais via varredura sequencial (retomavel)
echo [7] Verificar integridade dos downloads
echo [8] Executar novamente a bateria estatistica (sem baixar arquivos)
echo [9] Diagnosticar ultima coleta: erro e SEM_SECAO por UF/cargo
echo [A] Reparar APENAS arquivos em erro da ultima coleta
echo [B] VALIDAR SENADO V2 E FORMULA 2026 (sem download / sem SQLite)
echo [0] Sair
echo.
choice /C 123456789AB0 /N /M "Selecione: "
if errorlevel 12 exit /b 0
if errorlevel 11 goto validate_2026
if errorlevel 10 goto repair
if errorlevel 9 goto diagnose
if errorlevel 8 goto stats
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
echo Interromper: Ctrl+C ou tecla Q. O programa preservara o que estiver concluido.
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
echo Comparacao dos BUs e votos por secao JA BAIXADOS.
echo Sem download; varredura sequencial com particoes e checkpoints.
%PY% urnas.py reconcile
goto done

:verify
%PY% urnas.py verify
goto done

:stats
%PY% urnas.py stats
goto done

:diagnose
echo Diagnostico SEM download e SEM recalcular reconciliacao.
%PY% diagnose_forensics.py
goto done

:repair
echo Reparar SOMENTE recursos em erro no ultimo manifesto.
echo Nao refaz reconciliacao ou estatisticas; reaproveita os dados.
%PY% urnas.py repair
goto done

:validate_2026
echo.
echo FASE 2026 - testes, ajuste Senado v2, comparacao v1/v2 e formula fixa.
echo Usa somente particoes BU locais em H:. NAO faz download nem acessa o SQLite de 221 GiB do acervo.
echo Se uma etapa falhar, interrompe para proteger a interpretacao dos resultados.
%PY% -m unittest discover -s tests -p "test_*.py" -q
if errorlevel 1 goto validate_failed
%PY% cross_office_senate_correlations.py
if errorlevel 1 goto validate_failed
%PY% compare_senate_geo_versions_2026.py
if errorlevel 1 goto validate_failed
%PY% test_fixed_vote_formula_2026.py
if errorlevel 1 goto validate_failed
echo.
echo [CONCLUIDO] Confira as inversoes Senado v2 e a predicao fora da amostra.
goto done

:validate_failed
echo.
echo [ERRO] Validacao 2026 interrompida. Nao considerar os resultados completos.
echo Consulte a mensagem anterior; os dados originais nao foram modificados.
pause
goto menu

:done
echo.
if errorlevel 130 (
  echo [CANCELADO] Checkpoints preservados. Repita a mesma opcao para retomar.
  pause
  goto menu
)
if errorlevel 1 (
  echo [AVISO] A rotina encerrou com erro. Consulte a mensagem e retome a mesma opcao.
) else (
  echo Rotina concluida. Veja os relatórios e mensagens acima.
)
pause
goto menu
