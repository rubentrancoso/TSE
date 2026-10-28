# Fase 5Q / opcao V — seções tardias dentro de municípios e zonas

**Estado:** implementada em 28/10/2026. Aguardando execução empírica no disco H do investigador.

## Motivação: resultado real da Fase T

A Fase 5P (opção T) foi executada sobre **499.206** BWEB presidenciais do
primeiro turno de 2026, com SHA de H/M e 119.300.788 válidos conciliados.
Para o corte por segundo **04/10/2026 20:04:39 BRT**:

- antes: **105.672.906 válidos**; Lula representava **43,86698%**;
- depois: **13.627.882 válidos**, dos quais **7.524.029 Lula** e
  **5.236.944 Flávio**; Lula **55,21055%** e Flávio **38,42816%**;
- predição BR pré-corte: Lula 43,86698%, erro final **-11,34358 pp**;
- predição UF pré-corte: Lula 51,49914%, erro **-3,71142 pp**;
- predição município pré-corte: Lula 53,15006%, erro **-2,06049 pp**;
  isso corresponde a **280.801,5 votos Lula acima da previsão**, não a
  uma contagem de votos irregulares;
- município final **IN_SAMPLE**: Lula 54,10933%, erro **-1,10122 pp**:
  mesmo conhecendo a proporção municipal final, a cauda ainda difere
  do conjunto completo dentro dos municípios;
- **266 municípios** sem nenhuma seção com votos recebidos antes do corte,
  perfazendo **1.340.387 válidos** na cauda (**9,84%**);
- RMSE por minuto para Lula (137 minutos com >=5.000 válidos):
  BR **11,97833**, UF **4,46831**, município pré **2,82262**,
  município final IN_SAMPLE **1,46216** pp.

Estes são resultados da análise de recebimento BWEB, não uma
reconstrução direta da cadeia de publicação EA20. A diferença temporal
entre **18.809.656 votos publicados EA20 depois do corte** e
**13.627.882 BWEB recebidos depois do corte** não implica perda de votos.

## Questão nova, falsificável

O desvio remanescente do modelo municipal está localizado
1. em municípios sem observações pré-corte,
2. em **zonas sem observações pré-corte** de municípios já observados, ou
3. **dentro das mesmas zonas** com observações tanto antes como depois?

A V decompõe exatamente a soma dos resíduos em votos Lula nas três categorias.
Não presume que seção/votante seja uma amostra aleatória.

## Implementação

Script: `analyze_within_zone_holdout_2026.py`.

- Lê somente `received-UF.csv` (H) e `phase5h_nr28_sections_UF.csv`
  (M), com comparação SHA dos manifests originais.
- Reusa os **segundos exatos** de `DT_BU_RECEBIDO`, sem inventar
  ordem entre seções empatadas; mantém chaves UF/município/zona/seção.
- Reconcilia seção, votos válidos e candidatos com o total oficial e com
  as mesmas taxas BR/UF/município calculadas independentemente na T.
  Se diferenças aparecerem, interrompe.
- Treina somente com votos **anteriores ao corte**:
  BR, UF, município (prior fixo de 1.000 votos do perfil UF),
  zona (prior fixo de 1.000 votos do perfil município).
- Compara um quinto modelo **ZONA_final_IN_SAMPLE** como controle circular,
  nunca como previsão genuína.
- Mede erro Lula/Flávio no total da cauda e MAE/RMSE ponderado por
  minuto de BWEB com >=5.000 válidos.
- Calcula por zona a diferença Lula pós - pré entre as zonas com
  >=1.000 válidos de cada lado, sem atribuir causalidade.
- Gera ranking de municípios, zonas e a decomposição da contribuição
  para o desvio municipal em unidades de votos.

**Arquivos de saída no H**:
`phase5q_zone_holdout_2026_summary.json`,
`phase5q_zone_holdout_minutes_2026.csv`,
`phase5q_zone_holdout_municipalities_2026.csv`,
`phase5q_zone_holdout_zones_2026.csv`.
Todos os três CSVs são certificados por SHA-256 no sumário.

O laboratório visual da V fica em
`notebooks/TSE_2026_Laboratorio_Forense_Fase_V.ipynb`. A opção
**U** abre esse notebook automaticamente depois que V for concluída;
antes da V, mantém o notebook S/T.

## Como executar

No Windows: `git pull origin main` → `start_windows.bat` →
**V** (analisa; sem downloads/ZIP/SQLite) → **U** (visualiza a V).
A primeira abertura U já instalou Jupyter; não precisa reinstalar.

Os testes sintéticos em `tests/test_within_zone_holdout_2026.py` cobrem
concordância dos modelos BR/UF/município com a T, corte por segundo
dentro do mesmo minuto, falha após alteração SHA, mudanças futuras
incapazes de alterar modelos pré-corte, e reconciliação por grupos.
Esses testes **não substituem execução empírica em H**.

## Critério de interpretação

Se ZONA_pre melhorar sensivelmente a previsão, testar a composição de
zonas como mecanismo explicativo. Se não melhorar, investigar variação
entre seções dentro da mesma zona. Em qualquer caso, não chamar diferença
de previsão de prova de fraude. O exame da **linearidade EA20 R²=0,99044
por seções** continua aberto e exige modelar separadamente
recebimento, buffering e publicação.
