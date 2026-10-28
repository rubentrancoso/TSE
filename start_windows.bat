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
echo [C] ROBUSTEZ SENADO 2026 (bootstrap de zonas, sem SQLite)
echo [D] ZONAS QUE INFLUENCIAM OS 13 PARES (usa checkpoints C)
echo [E] STRESS: EXCLUIR VARIAS ZONAS (usa checkpoints C)
echo [F] PERIODICIDADE 2026: vales e permutacoes (sem baixar BU)
echo [G] BU INDIVIDUAL 2026: conferir horarios EA16 e construir matriz por secao
echo [H] BU RECEBIDOS 2026: extrair DT_BU_RECEBIDO e testar vales por minuto
echo [I] ROBUSTEZ DOS VALES 2026: filtros na serie CORRIGIDA (usa M)
echo [J] BU POR SEGUNDO 2026: padrao em blocos de 500-2000 urnas (cache H)
echo [K] CONCILIAR 5246 VOTOS: BWEB vs votos oficiais por UF (cache H)
echo [L] IDENTIFICAR 5246 VOTOS: conferir NR_VOTAVEL=28 no BWEB original
echo [M] CORRIGIR VALIDADE E REFAZER PERIODICIDADE 2026 (usa H/K/L)
echo [N] TESTE GLOBAL: periodicidade 2026 com 6 filtros e ajuste conjunto
echo [O] RECONCILIAR 42 SECOES: EA20/EA16 vs BWEB (sem baixar ou SQLite)
echo [P] CERTIDAO NACIONAL: EA16 vs BWEB por chave 2026 (27 UFs)
echo [Q] EXTERIOR ZZ: localizar +42 secoes por municipio EA20/BWEB
echo [R] EXTERIOR ZZ: conferir comparecimento e votos nas 42 secoes
echo [S] CURVA FORENSE 2026: tempo real, BU recebidos, geografia UF/municipio
echo [T] FORA DA AMOSTRA: pre-20:04 prevendo BU recebidos apos 20:04
echo [U] LABORATORIO JUPYTER: abre automaticamente a ultima fase executada
echo [V] ZONAS TARDIAS: comparar municipio vs zona pre-20:04 sem vazamento
echo [W] CORTES PLACEBO: comparar votos na mesma zona em horarios diferentes
echo [X] PUBLICACAO EA20: curva linear vs volumes fisicos e lotes reais
echo [Y] RECEBIMENTO x PUBLICACAO: comparar BWEB por segundo vs EA20
echo [0] Sair
echo.
choice /C 123456789ABCDEFGHIJKLMNOPQRSTUVWXY0 /N /M "Selecione: "
if errorlevel 35 exit /b 0
if errorlevel 34 goto receipt_publication_timing_2026
if errorlevel 33 goto ea20_publication_mechanics_2026
if errorlevel 32 goto temporal_placebos_2026
if errorlevel 31 goto within_zone_holdout_2026
if errorlevel 30 goto forensic_notebook_2026
if errorlevel 29 goto geographic_holdout_2026
if errorlevel 28 goto operational_curve_2026
if errorlevel 27 goto audit_zz_42_votes_2026
if errorlevel 26 goto audit_zz_42_2026
if errorlevel 25 goto certify_all_sections_2026
if errorlevel 24 goto reconcile_42_2026
if errorlevel 23 goto joint_sensitivity_2026
if errorlevel 22 goto correct_vote28_2026
if errorlevel 21 goto audit_candidate_28_2026
if errorlevel 20 goto audit_bweb_uf_2026
if errorlevel 19 goto per_second_2026
if errorlevel 18 goto sensitivity_bweb_2026
if errorlevel 17 goto bweb_received_periodicity_2026
if errorlevel 16 goto bu_unit_timing_2026
if errorlevel 15 goto periodicity_2026
if errorlevel 14 goto stress_2026
if errorlevel 13 goto drivers_2026
if errorlevel 12 goto robust_2026
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

:robust_2026
echo.
echo ROBUSTEZ DESCRITIVA DAS INVERSOES SENADO 2026.
echo Le BU ja derivados em H:, confere SHA-256; nao reindexa nem baixa.
echo Checkpoints permitem retomada sem repetir particoes ja processadas.
%PY% -m unittest discover -s tests -p "test_robust_senate_inversions_2026.py" -q
if errorlevel 1 goto validate_failed
%PY% robust_senate_inversions_2026.py
if errorlevel 1 goto validate_failed
echo.
echo [CONCLUIDO] Consulte robustez_inversoes_2026/summary.json.
goto done

:drivers_2026
echo.
echo INFLUENCIA TERRITORIAL DAS 13 INVERSOES - SEM RELEITURA DE BU.
echo Verifica os SHA-256 dos checkpoints da opcao C.
%PY% -m unittest discover -s tests -p "test_analyze_senate_zone_drivers_2026.py" -q
if errorlevel 1 goto validate_failed
%PY% analyze_senate_zone_drivers_2026.py
if errorlevel 1 goto validate_failed
echo.
echo [CONCLUIDO] Consulte robustez_inversoes_2026/drivers_zonais/summary.json
goto done

:stress_2026
echo.
echo STRESS TERRITORIAL 2026 - EXCLUSAO CONJUNTA DE ZONAS.
echo Usa somente os checkpoints SHA-256 da opcao C; nao reler BU ou SQLite.
%PY% -m unittest discover -s tests -p "test_stress_senate_zones_2026.py" -q
if errorlevel 1 goto validate_failed
%PY% stress_senate_zones_2026.py
if errorlevel 1 goto validate_failed
echo.
echo [CONCLUIDO] Consulte robustez_inversoes_2026/stress_zonas/summary.json.
goto done

:periodicity_2026
echo.
echo SERIE NACIONAL DE 2026 - PESQUISA DE VALES E PERIODICIDADE.
echo 193 snapshots 2026, sem 2022, download ou SQLite.
%PY% -m unittest discover -s tests -p "test_analyze_periodicity_2026.py" -q
if errorlevel 1 goto validate_failed
%PY% analyze_periodicity_2026.py
if errorlevel 1 goto validate_failed
echo [CONCLUIDO] data\forensics\analysis\phase5a_periodicity_2026_summary.json
goto done

:bu_unit_timing_2026
echo.
echo FASE 5B: BU INDIVIDUAL 2026, INTEGRIDADE EA16 E ORDEM REAL.
echo Usa 256 particoes BU existentes; SHA e checkpoints, sem downloads ou SQLite.
echo Se EA16 nao comprovar recepcao individual, reportara limite sem simular uma ordem.
%PY% -m unittest discover -s tests -p "test_analyze_bu_individual_timing_2026.py" -q
if errorlevel 1 goto validate_failed
%PY% analyze_bu_individual_timing_2026.py
if errorlevel 1 goto validate_failed
echo [CONCLUIDO] analysis\entre_cargos\...\periodicidade_bu_individual_2026\summary.json
goto done

:bweb_received_periodicity_2026
echo.
echo FASE 5C: ORDEM DE RECEBIMENTO BWEB POR SECAO - SOMENTE 2026.
echo Confere SHA dos ZIPs originais e DT_BU_RECEBIDO; nunca baixa ou usa SQLite.
echo Analisa por MINUTO; nao inventa ordem das urnas empatadas.
%PY% -m unittest discover -s tests -p "test_extract_bweb_received_2026.py" -q
if errorlevel 1 goto validate_failed
%PY% -m unittest discover -s tests -p "test_analyze_bweb_receipt_periodicity_2026.py" -q
if errorlevel 1 goto validate_failed
%PY% extract_bweb_received_2026.py
if errorlevel 1 goto validate_failed
%PY% analyze_bweb_receipt_periodicity_2026.py
if errorlevel 1 goto validate_failed
echo [CONCLUIDO] H:\TSE\forensics\urnas\analysis\periodicidade_bweb_2026\phase5c_summary.json
goto done

:sensitivity_bweb_2026
echo.
echo FASE 5D: SENSIBILIDADE DA PERIODICIDADE 2026, REUSA CSV CORRIGIDO DA OPCAO M.
echo NAO rele arquivos BU nem ZIP; NAO reindexa SQLite nem faz download.
%PY% -m unittest discover -s tests -p "test_sensitivity_bweb_periodicity_2026.py" -q
if errorlevel 1 goto validate_failed
%PY% sensitivity_bweb_periodicity_2026.py --corrigido
if errorlevel 1 goto validate_failed
echo [CONCLUIDO] H:\TSE\forensics\urnas\analysis\periodicidade_bweb_2026\phase5d_sensitivity_corrected_2026_summary.json
goto done

:per_second_2026
echo.
echo FASE 5E: PADROES POR SEGUNDOS REAIS E BLOCOS 500-2000 BU.
echo REUSA SOMENTE received-XX.csv do H:, sem abrir ZIP/BU ou SQLite.
%PY% -m unittest discover -s tests -p "test_analyze_bweb_seconds_2026.py" -q
if errorlevel 1 goto validate_failed
%PY% analyze_bweb_seconds_2026.py
if errorlevel 1 goto validate_failed
echo [CONCLUIDO] H:\TSE\forensics\urnas\analysis\periodicidade_bweb_2026\phase5e_high_resolution_2026_summary.json
goto done

:audit_bweb_uf_2026
echo.
echo FASE 5F: RECONCILIACAO POR UF DOS VOTOS VALIDOS BWEB 2026.
echo Usa apenas received-XX.csv no H: e a tabela UF por candidato do repositorio.
echo Sem ZIP, download, SQLite ou dados 2022.
%PY% -m unittest discover -s tests -p "test_audit_bweb_uf_totals_2026.py" -q
if errorlevel 1 goto validate_failed
%PY% audit_bweb_uf_totals_2026.py
if errorlevel 1 goto validate_failed
echo [CONCLUIDO] analysis\periodicidade_bweb_2026\phase5f_reconciliation_2026_summary.json
goto done

:audit_candidate_28_2026
echo.
echo FASE 5G: ORIGEM DOS 5246 VOTOS RESIDUAIS NO BWEB 2026.
echo Reusa os ZIPs BWEB ja existentes; confere SHA; NAO baixa nem abre SQLite.
%PY% -m unittest discover -s tests -p "test_audit_bweb_candidate_28_2026.py" -q
if errorlevel 1 goto validate_failed
%PY% audit_bweb_candidate_28_2026.py
if errorlevel 1 goto validate_failed
echo [CONCLUIDO] analysis\periodicidade_bweb_2026\phase5g_nr28_reconciliation_2026_summary.json
goto done

:correct_vote28_2026
echo.
echo FASE 5H: CLASSIFICAR NUMERO 28 COMO ANULADO, CONFERIR TOTAIS E REFAZER VALES.
echo Reusa BU da H, conciliacao K/L e ZIP BWEB local uma vez por UF com checkpoints.
echo Sem download, sem SQLite, sem dados 2022; preserva as saidas anteriores.
%PY% -m unittest discover -s tests -p "test_correct_bweb_28_periodicity_2026.py" -q
if errorlevel 1 goto validate_failed
%PY% correct_bweb_28_periodicity_2026.py
if errorlevel 1 goto validate_failed
echo [CONCLUIDO] analysis\periodicidade_bweb_2026\phase5h_corrected_periodicity_2026_summary.json
goto done

:joint_sensitivity_2026
echo.
echo FASE 5I: TESTE GLOBAL DA GRADE DE PERIODICIDADE NO 2026 CORRIGIDO.
echo Usa so phase5h_minute_corrected_2026.csv; sem ZIP, download, SQLite ou 2022.
echo Calibra estatistica maxima por 6 configuracoes e 144 frequencias cada.
%PY% -m unittest discover -s tests -p "test_joint_sensitivity_periodicity_2026.py" -q
if errorlevel 1 goto validate_failed
%PY% joint_sensitivity_periodicity_2026.py
if errorlevel 1 goto validate_failed
echo [CONCLUIDO] analysis\periodicidade_bweb_2026\phase5i_joint_periodicity_2026_summary.json
goto done

:reconcile_42_2026
echo.
echo FASE 5J: COMPARAR 42 SECOES NOS CONTADORES EA20 E BU INDIVIDUAIS 2026.
echo Usa BA/MG dos CSVs BWEB da H e relatórios EA16/EA20 ja preservados.
echo Nao baixa nada, nao consulta SQLite nem reprocessa ZIP.
%PY% -m unittest discover -s tests -p "test_reconcile_42_section_counters_2026.py" -q
if errorlevel 1 goto validate_failed
%PY% reconcile_42_section_counters_2026.py
if errorlevel 1 goto validate_failed
echo [CONCLUIDO] H:\TSE\forensics\urnas\analysis\periodicidade_bweb_2026\phase5j_42_section_counter_reconciliation_2026_summary.json
goto done

:certify_all_sections_2026
echo.
echo FASE 5K: CERTIDAO NACIONAL DE CHAVES EA16 x BWEB, SEM BAIXAR NEM ZIP/SQLite.
echo Confere EA16 original de cada UF com SHA da fase 3 e BU do cache H.
echo Se snapshots EA20 estaduais ja arquivados existirem, identifica em qual nivel divergem contadores.
%PY% -m unittest discover -s tests -p "test_certify_2026_all_section_keys.py" -q
if errorlevel 1 goto validate_failed
%PY% certify_2026_all_section_keys.py
if errorlevel 1 goto validate_failed
echo [CONCLUIDO] H:\TSE\forensics\urnas\analysis\periodicidade_bweb_2026\phase5k_national_section_key_certificate_2026_summary.json
goto done

:audit_zz_42_2026
echo.
echo FASE 5L: INVESTIGAR +42 SECOES DE ZZ ENTRE EA20 E BWEB.
echo Confere SHA dos JSON EA20 arquivados e BWEB ZZ ja extraido na H.
echo Sem downloads, reabertura ZIP, SQLite ou dados 2022.
%PY% -m unittest discover -s tests -p "test_audit_zz_42_sections_2026.py" -q
if errorlevel 1 goto validate_failed
%PY% audit_zz_42_sections_2026.py
if errorlevel 1 goto validate_failed
echo [CONCLUIDO] H:\TSE\forensics\urnas\analysis\periodicidade_bweb_2026\phase5l_zz_42_sections_2026_summary.json
goto done

:audit_zz_42_votes_2026
echo.
echo FASE 5M: VERIFICAR COMPARECIMENTO E VOTOS EA20 DOS 42 CONTADORES ZZ.
echo Usa apenas JSONs EA20 arquivados e manifesto SHA da opcao Q.
echo Nao baixa arquivos, nem consulta ZIP, SQLite ou dados 2022.
%PY% -m unittest discover -s tests -p "test_audit_zz_42_voting_status_2026.py" -q
if errorlevel 1 goto validate_failed
%PY% audit_zz_42_voting_status_2026.py
if errorlevel 1 goto validate_failed
echo [CONCLUIDO] H:\TSE\forensics\urnas\analysis\periodicidade_bweb_2026\phase5m_zz_42_voting_status_2026_summary.json
goto done

:operational_curve_2026
echo.
echo FASE 5O: RECONSTRUCAO DA CURVA PRESIDENCIAL EM TEMPO REAL.
echo Compara EA20 em horario real com BWEB por recebimento, sem confundir os eventos.
echo Decompoe UF/municipio por composicao geografia; so caches H e M.
echo Sem download, ZIP, SQLite ou dados do 2o turno.
%PY% -m unittest discover -s tests -p "test_analyze_operational_curve_2026.py" -q
if errorlevel 1 goto validate_failed
%PY% analyze_operational_curve_2026.py
if errorlevel 1 goto validate_failed
echo [CONCLUIDO] H:\TSE\forensics\urnas\analysis\periodicidade_bweb_2026\phase5o_operational_curve_2026_summary.json
goto done

:geographic_holdout_2026
echo.
echo FASE 5P: PREVISAO SEM CONHECER RESULTADOS FUTUROS DOS MUNICIPIOS.
echo Treina antes de 20:04:39 e mede erro sobre BWEB recebidos depois.
echo Separa modelo BR, UF, municipio pre-corte e ORACLE final circular.
echo Sem download, ZIP, SQLite, nem segundo turno.
%PY% -m unittest discover -s tests -p "test_geographic_holdout_curve_2026.py" -q
if errorlevel 1 goto validate_failed
%PY% audit_geographic_holdout_curve_2026.py
if errorlevel 1 goto validate_failed
echo [CONCLUIDO] H:\TSE\forensics\urnas\analysis\periodicidade_bweb_2026\phase5p_holdout_geographic_curve_2026_summary.json
goto done

:within_zone_holdout_2026
echo.
echo FASE 5Q: DESVIOS DE BUs TARDIOS DENTRO DOS MUNICIPIOS E ZONAS.
echo Usa CSV H/M no H: com SHA, corte por SEGUNDO e 4 modelos sem vazamento.
echo Confronta taxas por municipio e zona, controles, desvios e contagem.
echo Nenhum download, ZIP, SQLite, 2022 ou segundo turno.
%PY% -m unittest discover -s tests -p "test_within_zone_holdout_2026.py" -q
if errorlevel 1 goto validate_failed
%PY% analyze_within_zone_holdout_2026.py
if errorlevel 1 goto validate_failed
echo [CONCLUIDO] H:\TSE\forensics\urnas\analysis\periodicidade_bweb_2026\phase5q_zone_holdout_2026_summary.json
goto done

:temporal_placebos_2026
echo.
echo FASE 5R: CORTES PLACEBO NOS BU RECEBIDOS DENTRO DA MESMA ZONA.
echo Compara antes/depois em dez cortes fixos e verifica concordancia com a V.
echo Mede deslocamento Lula/Flavio, cobertura e robustez ao retirar cada UF.
echo Reusa H/M com SHA em uma passagem, sem download, ZIP ou SQLite.
%PY% -m unittest discover -s tests -p "test_cutoff_placebos_2026.py" -q
if errorlevel 1 goto validate_failed
%PY% analyze_cutoff_placebos_2026.py
if errorlevel 1 goto validate_failed
echo [CONCLUIDO] H:\TSE\forensics\urnas\analysis\periodicidade_bweb_2026\phase5r_cutoff_placebos_2026_summary.json
goto done

:ea20_publication_mechanics_2026
echo.
echo FASE 5S: TESTE FISICO DA CURVA NACIONAL PUBLICADA EA20.
echo Compara curva real com modelo de proporcao CONSTANTE nos volumes observados.
echo Separa ORACULO final circular de previsao calibrada nos 10 primeiros lotes.
echo Decompoe 152 incrementos publicados e 4 blocos por votos validos.
echo Usa APENAS EA20 nacional versionado, sem ZIP, BWEB, SQLite ou downloads.
%PY% -m unittest discover -s tests -p "test_ea20_publication_mechanics_2026.py" -q
if errorlevel 1 goto validate_failed
%PY% audit_ea20_publication_mechanics_2026.py
if errorlevel 1 goto validate_failed
echo [CONCLUIDO] H:\TSE\forensics\urnas\analysis\periodicidade_bweb_2026\phase5s_ea20_publication_mechanics_2026_summary.json
goto done

:receipt_publication_timing_2026
echo.
echo FASE 5T: RECEBIMENTO BWEB VERSUS PUBLICACAO EA20 NO TEMPO.
echo Condicao NECESSARIA se relogios e universo de votos coincidirem:
echo votos publicados no EA20 nao excedem os ja recebidos BWEB ate t.
echo Testa validos, Lula e Flavio, por segundos e offsets FIXADOS no codigo.
echo Sem casar urna a lote; sem ZIP, download, SQLite ou segundo turno.
%PY% -m unittest discover -s tests -p "test_receipt_publication_timing_2026.py" -q
if errorlevel 1 goto validate_failed
%PY% audit_receipt_publication_timing_2026.py
if errorlevel 1 goto validate_failed
echo [CONCLUIDO] H:\TSE\forensics\urnas\analysis\periodicidade_bweb_2026\phase5t_receipt_vs_publication_2026_summary.json
goto done

:forensic_notebook_2026
echo.
echo LABORATORIO JUPYTER 2026 - ABRE FASE Y APOS EXECUCAO (OU ANTERIOR).
echo Valida presenca dos CSV/JSON em H:; confere SHA no notebook.
echo Primeiro uso instala somente dependencias Python em ambiente isolado.
echo Nao baixa BWEB, nao abre ZIP, SQLite ou dados de outro turno.
%PY% -m unittest discover -s tests -p "test_forensic_notebook_2026.py" -q
if errorlevel 1 goto validate_failed
%PY% launch_forensic_notebook.py
if errorlevel 1 goto validate_failed
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
