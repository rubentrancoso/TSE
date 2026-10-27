# Fase 5J — 42 seções de diferença entre contadores de 2026

**Data:** 27 de outubro de 2026. Somente primeiro turno presidencial de 2026.

**Estado:** diagnóstico sobre arquivos já versionados executado; opção O implementada na branch main e validada em testes sintéticos. A conciliação de chaves dos BWEB reais do disco H: depende da execução local de O. Não foi feito novo download, nem aberto o SQLite de 221 GB.

## Comparações distintas: não somar nem equiparar indevidamente

1. **Último snapshot nacional:** `st = 499.248`, válidos = **119.300.788** (Fase 5A, `phase5a_presidential_national_2026.csv`).
2. **BWEB presidencial real:** **499.206** chaves completas, confirmadas nas Fases H/M, com votos válidos corrigidos de **119.300.788**, diferença de votos = **zero**.
3. **EA16 principal, 27 UFs:** **497.897**; BWEB exterior `ZZ`: **1.309**; soma **499.206**. O EA16 não foi coletado para `ZZ` na Fase 3A, e não se deve afirmar que a configuração EA16 cobre o exterior.
4. **EA20 estadual vs soma dos municípios:** na BA, 35.476 estaduais menos 35.470 municipais `st` = **6**; em MG, 52.062 estaduais menos 52.026 municipais `st` = **36**; soma **42**.
5. Assim, `snapshot_BR.st - BWEB = +42` e `EA20_estadual.st - soma_municipal.st = +42`. **Estes são dois contrastes diferentes, entre conjuntos e níveis diferentes.** A igualdade dos números não identifica 42 seções repetidas ou desaparecidas.

Os dois estados têm `ts` estadual e soma `ts` municipal exatamente iguais aos EA16 principais (35.476 BA; 52.062 MG). Todos os contadores EA20 estaduais de BA e MG indicam `st=ts` neste snapshot.

## Localização dos onze municípios de discrepância EA20

| UF | Código | Município | EA20 ts municipal | EA20 st municipal | Diferença |
| --- | --- | --- | ---: | ---: | ---: |
| BA | 33693 | Belo Campo | 58 | 54 | 4 |
| BA | 34673 | Conceição do Coité | 187 | 186 | 1 |
| BA | 36013 | Itaeté | 40 | 39 | 1 |
| MG | 40622 | Rosário da Limeira | 16 | 12 | 4 |
| MG | 41556 | Bom Jesus do Galho | 41 | 38 | 3 |
| MG | 41696 | Botumirim | 19 | 10 | 9 |
| MG | 42005 | Curral de Dentro | 19 | 12 | 7 |
| MG | 46078 | Ijaci | 16 | 15 | 1 |
| MG | 47198 | Joaíma | 40 | 34 | 6 |
| MG | 51977 | Santo Antônio do Amparo | 47 | 46 | 1 |
| MG | 53171 | Senador Modestino Gonçalves | 17 | 12 | 5 |
| | | **Total** | | | **42** |

**Achado adicional importante: os níveis EA20 não são plenamente aditivos.**

A soma dos déficits `ts-st` dos 11 contadores **zonais** arquivados é de **36**, não 42:
- três zonas da BA: 4+1+1 = **6**;
- oito zonas de MG: 4+3+9+7+1+0+1+5 = **30**.

Os seis restantes estão inteiramente em **Joaíma/MG**: a zona eleitoral **0149** informa `st=40` e `ts=40`, assim como a configuração principal EA16; mas o registro **municipal** EA20 informa `st=34` e `ts=40`. Não é possível inferir *quais seis seções* teriam sido excluídas do município, apenas pelos campos `st/ts`.

## Disponibilidade de evidência por seção

A Fase 2 já arquivou `section_candidates.csv` com **460 identificadores de seção** em 10 das 11 zonas anomalas. **Todos os 460 registros têm status EA18 `Totalizada`** no momento da coleta preservada. Os 40 registros da zona 0149 de Joaíma não estão nessa tabela, pois a fase original só fez download dos EA18 quando o contador **zonal** divergia; em Joaíma, não divergia.

Logo, o conjunto já materializado mostra status `Totalizada` inclusive em zonas cujos contadores `st` são inferiores a `ts`. Isso merece auditoria da cronologia/semântica dos snapshots, mas não é uma prova de que 42 BUs físicos estejam ausentes ou adulterados.

## Solução implementada: opção O

`reconcile_42_section_counters_2026.py` lê, sem downloads:
- snapshot nacional Fase 5A;
- inventário EA16 Fase 3A com SHA-256;
- sumário BA/MG e as três tabelas da Fase 2 (`section_config_reconciliation.csv`, `zone_reconciliation.csv`, `section_candidates.csv`);
- somete os **CSV BWEB BA e MG** derivados pela opção H, com os SHA-256 do manifesto `summary.json` no H:.

Se os EA16 brutos originais BA/MG estiverem disponíveis localmente com SHA da Fase 3A, lê suas chaves principais e marca eventuais diferenças **por UF, município, zona e seção** contra os BWEB. Se não estiverem disponíveis, não fabrica uma confirmação; mantém a conciliação dos contadores e usa as chaves EA18 já preservadas, sinalizando a cobertura reduzida.

O programa bloqueia inconsistências de fonte e confere estas identidades:
- `EA16(27 UFs)+ZZ = BWEB = 499.206`;
- `BR.st-BWEB = 42`;
- `(BA+MG).EA20_mun.ts-st = 42`;
- `soma_gaps_zonais=36` e `diferença zona↔município=6`;
- todos os arquivos locais BWEB consultados conservam os hashes derivados na H.

Relatórios gerados no H:
- `phase5j_42_section_counter_reconciliation_2026_summary.json`;
- `phase5j_municipal_42_2026.csv`;
- `phase5j_zonal_42_2026.csv`;
- `phase5j_candidate_key_differences_2026.csv`.

**O arquivo de diferenças por chave só identifica divergências observáveis entre fontes com identificadores completos; não imputa arbitrariamente os contadores `st` a seções específicas.**

## Como executar sem refazer trabalhos anteriores

No Windows:

    cd C:\Users\PC\Documents\git\TSE
    git pull
    start_windows.bat

Selecionar **O — RECONCILIAR 42 SECOES**.

Nao precisa rodar H, M ou N novamente. Nao baixa os arquivos de urna, nao reabre ZIP BWEB, nao indexa SQLite.

Validação de software: **185 testes aprovados em Windows e Linux**:
https://github.com/rubentrancoso/TSE/actions/runs/40531866677

## Interpretação limitada

O projeto identificou a divergência numérica e sua localização por município/nível de agregação. A causa final do contador nacional `st` 42 acima dos BWEB ainda não foi comprovada por referência de seção individual. Sem definições verificadas dos contadores e comparação de seus snapshots temporais, **não se deve dizer que encontramos 42 urnas faltando**. As somas dos votos presidenciais de 2026 corrigidos continuam iguais ao total oficial.
