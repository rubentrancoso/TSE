# Etapa de robustez territorial: Senado x Presidencia — 2026

## Objetivo

Verificar se as 13 inversoes de sinal encontradas entre 616 pares
Presidente x Senado sao estaveis sob mudancas controladas da
composicao de zonas eleitorais. Isto e uma analise de sensibilidade
POS-SELECAO, nao evidencia causal nem teste da existencia de fraude.

## Metodos fixados antes da execucao nos BU reais

- Usar apenas dados eleitorais de 2026, turno 1, em
  `analysis/entre_cargos/<fingerprint>/candidatos/bucket-*.csv`.
- `source()` confere SHA-256 dos 256 arquivos antes de ler votos.
- Comparacao e Senado v2 devem estar com SHA-256 valido; os
  coeficientes bruto e intrazona sao reconstruidos a partir
  dos BU e comparados aos numeros publicados na v2
  (tolerancia aritmetica 0,00002).
- Denominador presidencial: total de votos para Presidente
  incluindo branco e nulo. Denominador senatorial:
  metade de todas as escolhas de Senado na secao.
- Unidade de reamostragem: zona completa `UF,municipio,zona,turno`.
- Calcular coeficiente intrazona apos retirar cada zona
  individualmente (leave-one-zone-out).
- Filtrar zonas com menos de 5 secoes e com menos de 10
  secoes, sem alterar os dados de referencia.
- Bootstrap nao parametrico de zonas, 400 replicacoes por par,
  com semente SHA-256 deterministica de `UF,presidente,senador`;
  informar percentuais de mesmo sinal, mesmo sinal com
  magnitude >= 0,1 e quantis 2,5% e 97,5%.
- O bootstrap reamostra estatisticas intrazona
  precentradas e nao revela votos individuais.
- Checkpoints por particao permitem retomar; os dados
  originais sao somente leitura. JSON e CSV novos sao
  gravados em `correlacao_presidente_senado_v2/robustez_inversoes_2026/`.

## Execucao

```bat
cd C:\Users\PC\Documents\git\TSE
git pull
start_windows.bat
```

Escolher **C — ROBUSTEZ SENADO 2026**, ou:

```bat
python -m unittest discover -s tests -p "test_robust_senate_inversions_2026.py" -q
python robust_senate_inversions_2026.py
```

Nenhum comando desta etapa baixa arquivos ou reindexa o
SQLite. O processamento completo exige uma passagem pelos
CSVs de BU locais, mas nao refaz as correlacoes de 616 pares.

## Interpretacao e limites

Percentual alto de estabilidade significa somente que o
coeficiente exploratorio nao depende de uma unica zona ou
de uma reamostragem zonal especifica. Nao significa
probabilidade de fraude e nao comprova voto cruzado individual.
Os pares foram selecionados apos examinar 616 comparacoes
e compartilham candidatos e secoes: as observacoes
nao sao independentes nem os intervalos sao corrigidos
para multiplas comparacoes. Zonas proximas podem ter
dependencia espacial, reduzindo a confiabilidade do
bootstrap simples. Os intervalos nao devem receber
interpretação confirmatoria de significancia.

A atribuicao de adulteracao requer confronto de BU fisico
ou QR independente, capturado no encerramento da votacao,
com a publicacao do mesmo boletim e chave eleitoral.
Sem `X` independente, o vetor `D=Y-X` e desconhecido.

**Estado de inicio:** codigo publicado e em validacao de CI,
aguardando execucao empirica no disco H:.
