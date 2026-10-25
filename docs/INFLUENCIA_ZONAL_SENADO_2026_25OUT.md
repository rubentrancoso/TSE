# Resultado empirico — influencia por zona nas 13 inversoes (2026)

**Data:** 25/10/2026. **Fonte:** execucao local da opcao D no disco H:,
transcrita pelo investigador. Etapa real identificada por
\`[ZONAS 1/256]\` a \`[ZONAS 256/256]\`. O primeiro par
AC/13/170 em diretorio Temp e uma FIXTURE sintetica e nao faz
parte dos 13 resultados reais.

## Integridade e escala

- 4 testes de unidade locais: OK;
- checkpoints verificados: 256/256, sem ler os 67,8 milhoes
  de registros BU novamente, sem abrir SQLite;
- 13 pares selecionados apos 616 comparacoes anteriores;
- 2.156 observacoes *par x municipio/zona*, **nao 2.156 zonas
  distintas**: os mesmos municipios/zonas se repetem entre
  pares presidenciais e senatoriais;
- 13 linhas de resumo, 2.156 linhas por zona/par,
  65 linhas de top 5 por par.

| Artefato | SHA-256 |
|---|---|
| \`drivers_zonais/resumo_pares.csv\` | \`55bc291a596a5c45f88e042e6d659a1d137fcb1a76e052070f057bb5c13b3183\` |
| \`drivers_zonais/zonas_por_par.csv\` | \`6ccbec12342a13b320360f8de967bd4a6c0d158db43c7da4074d801ffadd9007\` |
| \`drivers_zonais/top5_zonas_influentes.csv\` | \`0017ff8cc47d093042e9cdcef8eafcd00f45c465d2723b5fb95b382cf1b08826\` |

Diretorio de origem:
\`H:/TSE/forensics/urnas/analysis/entre_cargos/8ab3ce83c8992b9a-94fc637b4737c20d/correlacao_presidente_senado_v2/robustez_inversoes_2026/drivers_zonais/\`

## Resultados por par

\`alinhadas\` representa zonas cuja covariancia intrazona
tem o mesmo sinal do coeficiente agregado. \`top5_abs\`
e a fracao das somas dos valores ABSOLUTOS das covariancias
de zona contida nas cinco maiores contribuicoes, **nao
percentual de votos nem de eleitores**.

| UF | Presid. | Senador | Zonas alinhadas/total | Top 5 abs | Maior delta r ao excluir uma zona |
|---|---|---|---|---:|---:|
| AC | 13 | 277 | 20/23 | 79,484% | 0,045933 |
| AC | 22 | 277 | 19/23 | 77,376% | 0,039341 |
| AL | 22 | 111 | 78/107 | 33,715% | 0,021383 |
| AM | 22 | 455 | 49/74 | 36,202% | 0,033408 |
| PI | 13 | 111 | 160/230 | 30,542% | 0,041465 |
| RN | 13 | 444 | 90/172 | 54,334% | 0,047606 |
| RN | 22 | 444 | 96/172 | 52,389% | 0,038311 |
| RR | 13 | 155 | 10/16 | 72,190% | 0,052112 |
| SP | 13 | 232 | 490/779 | 13,441% | 0,003821 |
| TO | 13 | 153 | 87/140 | 41,886% | 0,056593 |
| TO | 13 | 222 | 98/140 | 42,428% | 0,027075 |
| TO | 22 | 153 | 91/140 | 41,002% | 0,051558 |
| TO | 22 | 222 | 100/140 | 40,726% | 0,021594 |

Em SP, 267 zonas apresentam covariancia oposta e
22 tem covariancia zero segundo a tolerancia do script.
Por isso, 490+267+22=779. Os outros pares nao tinham
zona classificada como zero.

### Municipio e zona de maior influencia por exclusao

Sao **8 zonas unicas**, uma por UF: varios pares
na mesma UF compartilham a mesma zona mais influente.
Os identificadores sao codigos eleitorais, nao nomes
de municipios. **Nao inferir irregularidade local**
pela repeticao de uma zona entre pares relacionados.

| UF | Codigo municipio | Zona | Pares cuja maior influencia ocorreu nessa zona |
|---|---|---|---|
| AC | 1104 | 5 | 13/277 e 22/277 |
| AL | 28533 | 15 | 22/111 |
| AM | 2836 | 19 | 22/455 |
| PI | 12190 | 98 | 13/111 |
| RN | 18376 | 51 | 13/444 e 22/444 |
| RR | 3107 | 7 | 13/155 |
| SP | 71072 | 408 | 13/232 |
| TO | 96210 | 9 | 13/153, 13/222, 22/153 e 22/222 |

## Interpretacao

1. Exclusao de uma zona em separado preservou o sinal
   em todos os pares (etapa C); isso nao significa
   invariancia ao retirar simultaneamente varias zonas.
2. Em SP, a covariancia absoluta e relativamente
   distribuida entre zonas; em AC e RR ha concentracao
   substancial em poucas zonas, sem troca de sinal
   na exclusao unica. O RN combina concentracao
   territorial com numeros proximos de zonas a favor
   e contra a direcao agregada.
3. A fracao de covariancia absoluta e diferente
   do efeito real de remover essas zonas na
   correlacao padronizada (Pearson muda as tres somas).
4. Nao ha teste confirmatorio dos 616 pares,
   ajuste de comparacoes multiplas nem evidencia
   de uma diferenca urna->publicacao \`D=Y-X\`.

## Proxima verificacao predefinida

Realizar um teste adversarial de **exclusao conjunta**
das 1, 3 e 5 zonas de maior contribuicao absoluta
e das 5 zonas de maior influencia individual,
comparando com exclusao aleatoria reprodutivel de
5 zonas. Usar SOMENTE os checkpoints SHA-256 da etapa C,
sem releitura dos BU ou mistura com dados de 2022.
Informar fracoes de secoes removidas, r original,
r apos exclusao, e eventual troca de sinal.
Esse teste e deliberadamente POS-SELECAO e
descritivo, jamais uma probabilidade de fraude.

**Status da proxima verificacao:** codigo da opcao E publicado,
CI com 136 testes aprovados em Linux e Windows
(https://github.com/rubentrancoso/TSE/actions/runs/40238571980).
Execucao real da E no disco H: ainda pendente.
