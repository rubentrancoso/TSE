# Fase 5A — Reproducao do teste de vales e cadencias na apuracao 2026

**Eleicao estudada:** primeiro turno presidencial de 4 de outubro de 2026.
**Escopo:** somente 2026; os graficos do video sobre 2022
foram usados EXCLUSIVAMENTE para formular a hipotese de
repeticao de vales. NENHUM microdado de 2022 foi lido.

## Hipotese falsificavel

Um suposto algoritmo de penalizacao periodica faria aparecer
vales repetidos, de forma ou espacamento previsivel, na
sequencia de atualizacoes, mesmo quando se separa:
- tendencia acumulada do candidato;
- quantidade variavel de votos novos em cada lote;
- cadencia irregular de atualizacao do totalizador.

A quantidade de vales e sua periodicidade devem ser calculadas
nos dados publicados, nao escolhidas por inspecao do video.

## Dados e integridade

Fonte ja preservada no projeto: ArvorCo/PNAD,
commit fixo beb3bec9ae5c25e2868ee2f2cefb9e6dccd91415,
arquivo analysis/apuracao_2026/dados/linha_do_tempo.json,
SHA-256 3e29b16d2827f88e407096d6fa494a3d1b862f8156633f1a7f905e799f70af73.

Arquivo derivado, PUBLICADO NA MAIN:
data/forensics/analysis/phase5a_presidential_national_2026.csv

Filtros de origem: linha nao regressiva,
delta de validos positivo e total valido positivo;
ordem por instante de GERACAO UTC. Total de
**193 snapshots**, 192 transicoes entre eles;
de 17:21:47 BRT em 04/10 ate 02:59:31 BRT em 05/10.
Identificadores de secao acumulada: 6.157 a 499.248.

**Nao e a ordem individual de 499 mil BUs!** Cada ponto
da serie e uma atualizacao nacional agregada. Os eixos
sao horario real de GERACAO e secoes ACUMULADAS; nao
se inventam timestamps individuais de urna.

## Transformacao e criterios

1. Diferenciar as contagens inteiras de Flavio e os
   votos validos entre snapshots consecutivos para
   obter a participacao NOVA POR LOTE:
   100 * DeltaFlavio / DeltaValidos.
2. Usar somente os **140 lotes com >=10.000 votos
   validos** para evitar que lotes finais diminutos
   dominem o sinal.
3. Subtrair uma mediana movel centrada de
   15 atualizacoes, obtendo residuo local em
   pontos percentuais. Esses parametros sao
   exploratorios e devem ter sensibilidade testada.
4. Sinalizar minimos locais cujo relevo medido
   contra maximos da vizinhanca de cinco lotes
   de cada lado seja >=8 pontos percentuais.
5. Ajustar par de senos/cossenos com intercepto
   para 72 periodos logaritmicamente espacados
   de 2.000 a 100.000 SECOES e 72 periodos de
   2 a 120 MINUTOS; registrar maior R² entre
   todos os 144 candidatos, corrigindo a escolha
   da frequencia na estatistica maxima.
6. Executar 1.000 simulacoes de dois nulos com
   semente 20261027, permutando residuos
   dentro de QUARTIS de progresso da apuracao:
   (a) permutacao individual; (b) permutacao de
   blocos consecutivos com ate cinco atualizacoes.
7. p empirico com correcao para contagem finita:
   (1 + numero de simulacoes com maior R²
    >= R² observado)/(1 + numero de simulacoes).
   E um **teste exploratorio condicionado ao
   nulo simplificado**, nao prova causal nem
   significancia confirmatoria.

## Resultado preliminar reproduzido em calculo direto

- 140 lotes selecionados, 4 vales residuais
  com proeminencia >=8 pp;
- maior R² = **0,07781158** (7,78% da
  variacao residual), a um periodo de cerca
  de **2,51888 minutos**;
- 1.000 permutacoes individuais deram
  p empirico ~**0,1968**;
- 1.000 permutacoes em blocos deram
  p empirico ~**0,2527**.

As quatro janelas sinalizadas incluem:
- 21:17:06 BRT, apos 494.766 secoes;
- 21:28:45 BRT, apos 496.011 secoes;
- 21:47:34 BRT, apos 497.326 secoes;
- 22:19:45 BRT, apos 498.623 secoes.

**Resultado:** no recorte/nulo definido, NAO
foi observada periodicidade estatisticamente
extraordinaria. Isso nao elimina outros
periodos, nao verifica a ordem dos BUs
individuais e nao certifica ausencia de fraude.
Os efeitos dos 10.000 votos minimos,
filtro de mediana e nulo espacial permanecem
limites de sensibilidade.

## Como repetir sem baixar os BU

Atualizar a main:
git pull

Executar:
python analyze_periodicity_2026.py

Ou executar start_windows.bat e escolher **F**.

Saidas na pasta do repositorio:
- data/forensics/analysis/phase5a_periodicity_2026_summary.json
- data/forensics/analysis/phase5a_periodicity_residuals_2026.csv

Sem download, sem reindexar SQLite e sem
utilizar o disco H: para obter os CSVs do estudo.

## Proxima verificacao em maior resolucao

O que falta para transpor com fidelidade a
analise do video e criar uma serie por BU
individual em 2026, ordenada por horario
de recepcao verificavel (se disponivel),
e nao por codigo da secao. O acervo local
ja contem votos por secao, mas a existencia
e cobertura de timestamps autenticos na
mesma chave precisam ser verificadas.
Apos essa validacao, fazer detecao de
vales, distancia e autocorrelacao pela
mesma rotina usando cada BU como unidade.

Nao usar uma ordem geografica arbitraria
para fingir ordem de transmissao.
