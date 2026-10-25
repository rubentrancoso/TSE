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

## Execucao real em H: — 25/10/2026

A opcao C passou por **4 testes sinteticos locais** e processou
**256/256 particoes BU de 2026**, sem reuso de checkpoints
na primeira execucao. Reconstruiu os 13 pares com os
coeficientes originais e concluiu 400 replicacoes por par.

**Resultados agregados:**
- 13/13 pares preservaram o sinal apos retirar qualquer
  zona eleitoral isoladamente (leave-one-zone-out, 100%);
- o sinal tambem permaneceu nos filtros de zonas com
  menos de 5 ou 10 secoes;
- 6/13 preservaram o sinal em todas as 400 replicacoes;
- 9/13 tiveram os quantis de 2,5% e 97,5% do bootstrap
  inteiramente de um lado do zero;
- 4/13 cruzaram zero nos quantis exploratorios;
- apenas 4/13 tiveram sinal e modulo >=0,10 em pelo
  menos 95% das reamostragens. Esses quatro foram
  AC 13 x 277, PI 13 x 111, TO 13 x 222 e TO 22 x 222.

| UF | Presid. | Senador | r intrazona | Boot mesmo sinal | Quantis 2,5% a 97,5% |
|---|---|---|---:|---:|---|
| AC | 13 | 277 | -0,215486 | 100% | [-0,324748; -0,087176] |
| AC | 22 | 277 | +0,191363 | 100% | [+0,068365; +0,311476] |
| AL | 22 | 111 | +0,109550 | 99,75% | [+0,025425; +0,206951] |
| AM | 22 | 455 | +0,105302 | 93,75% | [-0,023042; +0,228187] |
| PI | 13 | 111 | -0,211450 | 100% | [-0,311706; -0,122902] |
| RN | 13 | 444 | +0,118039 | 96,25% | [-0,004577; +0,225701] |
| RN | 22 | 444 | -0,127813 | 97,75% | [-0,226602; -0,000778] |
| RR | 13 | 155 | +0,223131 | 99,75% | [+0,060567; +0,379599] |
| SP | 13 | 232 | -0,117541 | 100% | [-0,135553; -0,095634] |
| TO | 13 | 153 | -0,102593 | 94,00% | [-0,200707; +0,014871] |
| TO | 13 | 222 | -0,328465 | 100% | [-0,420937; -0,224021] |
| TO | 22 | 153 | +0,111438 | 96,25% | [-0,012968; +0,210037] |
| TO | 22 | 222 | +0,341408 | 100% | [+0,251164; +0,424964] |

**Arquivo empirico:**
`H:/TSE/forensics/urnas/analysis/entre_cargos/8ab3ce83c8992b9a-94fc637b4737c20d/correlacao_presidente_senado_v2/robustez_inversoes_2026/pares_robustez.csv`

SHA-256:
`f8dfe10cd1aa2f7c5d02c20f3aec54db75920273361380d811d2242c6613933e`.

O resultado fornece **estabilidade descritiva**, nao
significancia confirmatoria: os pares foram escolhidos
depois de examinar 616 correlacoes, e os bootstrap
nao ajustam multiplas comparacoes nem dependencia espacial.
Nao ha evidencia independente de diferenca `D=Y-X`.

### Seguimento: diagnostico de influencia por zona

`analyze_senate_zone_drivers_2026.py` reutiliza apenas
os **checkpoints zonais da opcao C** com seus SHA-256,
sem ler novamente os 67,8 milhoes de registros BU.
Reconstroi os 13 coeficientes, lista as zonas de maior
influencia por exclusao e quantifica zonas com covariancia
a favor e contra o sinal agregado.

No Windows, apos `git pull`, escolher **opcao D**
em `start_windows.bat`. Resultados esperados em
`robustez_inversoes_2026/drivers_zonais/`
(`resumo_pares.csv`, `zonas_por_par.csv`,
`top5_zonas_influentes.csv`, `summary.json`).
A execucao real da opcao D ainda nao ocorreu.

**Validacao de codigo da opcao C:** 128 testes aprovados
em Windows e Linux:
https://github.com/rubentrancoso/TSE/actions/runs/40236148686

