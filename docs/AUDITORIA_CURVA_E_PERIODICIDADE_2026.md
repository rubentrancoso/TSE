# Primeiro turno de 2026 — auditoria quantitativa da curva nacional e alegacao de quedas periodicas

**Estado:** analise descritiva de dados de cronologia observada (27/10/2026). Nao e teste confirmatorio de fraude nem avaliacao de video nao fornecido.

## Fonte e filtros

- Serie externa preservada: ArvorCo/PNAD, commit imutavel `beb3bec9ae5c25e2868ee2f2cefb9e6dccd91415`, `analysis/apuracao_2026/dados/linha_do_tempo.json`.
- Hash registrado no acervo: `3e29b16d2827f88e407096d6fa494a3d1b862f8156633f1a7f905e799f70af73`.
- Dados usados: somente **2026**, cargo Presidente, primeiro turno. 331 linhas brutas de versoes da divulgacao nacional. Foram mantidas 193 versoes com `marcada_regressiva=false`, `d_vv>0`, `vv>0`, ordenadas pela data UTC de geracao; calculamos 192 transicoes a partir dos totais INTEIROS, nao do campo percentual arredondado.
- Nao assumir que instantes de geracao das versoes TSE sejam identicos ao polling de uma interface ou ao momento fisico de apuracao do BU.

## Queda e liderança nao sao a mesma variavel

- Primeira versao com votos: 17:21:47 BRT: Flavio **48,85128%**, Lula **42,50489%**.
- Pico de percentual de Flavio na serie: 18:13:47: Flavio **51,22455%**, Lula **40,65969%**. A vantagem (Flavio menos Lula) foi **10,56486 pp**.
- Antes e incluindo a versao 20:04:39, foram 40 transicoes com votos novos: Flavio **subiu 29** vezes e **caiu 11** vezes. Logo, nao e verdade que seu percentual sempre caiu desde o inicio.
- Apos 20:04:39 foram 152 transicoes com votos novos: Flavio **caiu 152/152**, Lula **subiu 152/152** nos percentuais exatos.
- Final: 02:59:31 de 05/10: Flavio **47,02777%**, Lula **45,16277%**; Flavio manteve a lideranca por **1,86500 pp**. Nenhum dos 193 snapshots nacionais selecionados apresenta Lula na frente.

## Distincao essencial: composicao do lote e ordem de publicacao

Percentual acumulado de Flavio antes do lote = `p=F/V`.
Novo lote contem `f` votos de Flavio entre `n` validos.
Identidade algebrica exata:

`p_novo-p = [n/(V+n)]*[f/n-p]`.

Logo, uma queda de percentual ocorre se e somente
se a fracao de Flavio no lote e inferior ao percentual
anterior; a magnitude depende tanto do tamanho do
lote quanto da diferenca de composicao.

A fase 4G ja havia feito teste de ORDEM adversarial
sobre todos os 152 lotes preservados. Resultado:
mesmo rearranjando os lotes na ordem mais desfavoravel
para a monotonicidade, a participacao Flavio cai,
e a de Lula sobe. Isto implica que **qualquer permutacao
dos mesmos 152 lotes** preservaria a monotonicidade,
dadas as contagens e o estado inicial de 20:04:39.
Essa prova nao demonstra que a composicao dos lotes
seja normal nem anormal; mostra que nao foi necessario
programar uma ordem particular desses lotes para
obter uma curva monotona.

O pool de 18.809.656 votos validos incorporados
apos 20:04:39 tinha Lula com **54,0881%** e
Flavio com **39,3429%**; o agregado nacional
nesse instante tinha Lula **43,4922%** e
Flavio **48,4662%**.

## As maiores quedas e a hipotese de periodicidade

Entre as 152 atualizacoes apos a retomada, com
limiar de **queda maior que 0,03 ponto percentual**,
encontramos os seguintes sete eventos:

| Horario BRT | Queda Flavio (pp) | Votos validos incluidos |
|---|---:|---:|
| 20:10:56 | -0,25475 | 4.156.336 |
| 20:13:34 | -0,04124 | 528.839 |
| 20:50:25 | -0,08302 | 1.160.029 |
| 20:51:35 | -0,04585 | 624.826 |
| 20:55:27 | -0,03970 | 504.873 |
| 20:59:36 | -0,07845 | 906.516 |
| 21:01:17 | -0,03483 | 347.979 |

Intervalos entre esses eventos:
**2,63; 36,85; 1,17; 3,87; 4,15; 1,68 minutos**.
Nao sao eventos igualmente espacados nesse corte.
O limiar de 0,03 pp e um diagnostico exploratorio
escolhido para descrever eventos maiores, nao
um teste inferencial pre-registrado.

A cadencia de atualizacoes COM VOTOS NOVOS no
pos-retomada varia entre **21 segundos** e **5.224
segundos** (mediana **60 segundos**); nao houve
periodicidade fixa de 15 segundos. O grafico de
uma interface pode atualizar por polling sem que
isso corresponda a novo lote de votos.

As duas grandes atualizacoes de acumulacao
anteriormente investigadas foram:
- 19:14:08: 21.016.324 votos validos incluidos;
  percentual Flavio diminuiu ~**0,6180 pp**.
- 20:04:39: 24.728.306 votos validos incluidos;
  percentual Flavio diminuiu ~**1,1187 pp**.
Esses dois instantes separados por ~50,5 minutos
nao formam uma serie suficiente para afirmar um
ciclo periodico.

Nas 152 atualizacoes posteriores, correlacao de
Pearson descritiva entre **magnitude absoluta**
da alteracao do percentual Flavio e o numero de
votos do lote: aproximadamente **r=0,9913**.
Esta correlacao e fortemente afetada pela propria
IDENTIDADE MATEMATICA do percentual cumulativo;
nao e teste causal e nao elimina possiveis efeitos
de composicao dos lotes. Ela mostra por que grandes
lotes naturalmente geram saltos mais visiveis.

## Geografia e identificabilidade

A fase 4H, baseada em finalizacao de zonas no
mesmo pleito 2026, documentou diferenca territorial:
no corte 20:04, zonas concluidas ate esse instante
tinham aproximadamente 38,06% Lula e 53,34% Flavio,
enquanto zonas que concluiam depois tinham cerca de
50,98% Lula e 41,87% Flavio (votos finais dessas
zonas). Importante: isso **nao equivale** a contar
votos efetivamente recebidos depois das 20:04:
as zonas finalizadas tarde podem ter enviado
secoes antes, e somam muito mais votos finais
que os 18,8 milhoes de votos do pool tardio.

## Limite inferencial e teste ainda necessario

- Uma curva cumulativa NAO deve seguir uma curva
  normal e percentuais de candidatos nao precisam
  se cruzar, mesmo em resultado nacional apertado.
- A monotonicidade exata 152/152 e FATO EMPIRICO.
- A irregularidade temporal dos eventos acima
  **nao valida um teste formal de ausencia de
  periodicidade**. Para isso: executar periodograma
  Lomb-Scargle ou teste de varredura de periodos
  sobre residuos da composicao por lote, com
  intervalos de geracao genuinos e simulacoes nulas
  que preservem volumes, estrutura espacial e
  filas de publicacao, corrigindo a selecao
  de periodos, limiares e janelas.
- Na ausencia de rastro independente de BU,
  periodicidade, ainda que verificada, nao
  provaria adulteracao de votos; poderia
  refletir processamento/transmissao/publicacao
  em lotes, entre outras causas.
- O video alegado nao foi disponibilizado,
  portanto seus graficos e pontos especificos
  nao foram conferidos visualmente.

**Resultado presente:** ha mudanca de regime clara
apos 20:04, mas nao foi identificado um ciclo
de quedas de espacamento fixo nos eventos
examinados, nem evidencia causal de programacao
de votos na curva. Preservar a hipotese de
periodicidade residual como **NAO TESTADA
FORMALMENTE**.

## Relatorios anteriores do mesmo projeto

- `data/forensics/analysis/phase4f_summary.json`
- `data/forensics/analysis/phase4g_summary.json`
- `data/forensics/analysis/phase4h_summary.json`
- `data/forensics/analysis/phase3e_summary.json`
- `docs/INVESTIGACAO_TOTALIZACAO_2026.md`


## Atualizacao de 27/10/2026 — mistura aleatoria condicional dos votos

Nova pergunta: seria impossivel obter 152 quedas consecutivas do percentual de Flavio por mero agrupamento dos votos restantes?

Foi executado experimento Monte Carlo com gerador NumPy, distribuicao hipergeometrica multivariada exata, 10.000 replicacoes, semente inteira 20261027.

Estado de partida 20:04:39: 100.491.132 votos validos; Flavio 48.704.246; Lula 43.705.754. Pool posterior: 18.809.656 votos validos; Flavio 7.400.257; Lula 10.173.784; outros 1.235.615. Os tamanhos dos 152 lotes efetivos foram preservados. Em cada rodada foram redistribuidos ALEATORIAMENTE os VOTOS INDIVIDUAIS restantes entre os 152 lotes, SEM reposicao, com todos os totais finais preservados. Os percentuais acumulados foram recalculados de contagens inteiras.

**Resultados sob ESSE modelo:**
- 9.777 de 10.000 (97,77%) produziram 152 quedas estritas do percentual de Flavio;
- 9.936 de 10.000 (99,36%) produziram 152 subidas estritas do percentual de Lula;
- 9.760 de 10.000 (97,60%) produziram ambas simultaneamente.

Esse nulo demonstra que a sequencia de 152 movimentos na mesma direcao NAO e estatisticamente impossivel nem rara QUANDO SE CONDICIONA AO POOL TARDIO OBSERVADO: Flavio tinha 48,466% no acumulado as 20:04, enquanto entre os votos restantes sua participacao era de apenas 39,343%.

ATENCAO: essa simulacao embaralha votos individuais, NAO urnas BU inteiras, e condiciona ao numero de votos e sua composicao remanescente efetivamente observados. Nao testa se a chegada desse pool foi natural, nao preserva localizacao, nem modela horarios, nem verifica picos periodicos. Os percentuais acima NAO sao probabilidades de fraude ou inocencia. Um modelo por urnas com geografia/ordem de divulgacao ainda precisa ser testado para a hipotese mais ampla.

O script reproduzivel esta em simulate_post_resume_random_vote_mixing_2026.py. Entrada: data/forensics/analysis/phase4g_post_resume_batches.csv, que contem os 152 lotes com seus volumes; nao le SQLite, nem baixa dados. Executar com Python e NumPy instalado.

A hipotese de periodicidade dos saltos de maior magnitude permanece NAO TESTADA formalmente com modelo nulo condicionado em volume e geografia.
