# Fase 5S / opcao X — mecanismo dos volumes publicados EA20 (primeiro turno 2026)

**Implementada em 28/10/2026.** A serie nacional
`data/forensics/analysis/phase5a_presidential_national_2026.csv`
ja foi examinada diretamente via GitHub; a rotina do menu X
e os respectivos CSV/JSON no disco H ainda precisam ser
executados no Windows do investigador.

## Pergunta fisica concreta

O grafico cumulativo do EA20 tem R² = 0,99044479
contra secoes totalizadas apos 20:04:39. A lisura e uma
consequencia natural dos volumes das atualizacoes, mesmo
se cada lote adicionar votos com a mesma participacao?
Os lotes reais exibem composicao estavel?

**O EA20 mede PUBLICACAO e nao recebimento BWEB.**
As fases T/V/W mediram recebimento DT_BU_RECEBIDO e
nao podem ser artificialmente alinhadas por minuto a EA20.

## Dados nacionais observados (ja medidos na fonte versionada)

- 193 snapshots EA20 preservados; 153 apos 20:04:39
  inclusive, com 152 incrementos.
- O ultimo snapshot do corte tinha 100.491.132 validos
  e 424.153 secoes nacionalmente.
- Ao final sao 119.300.788 validos e 499.248 secoes,
  portanto **18.809.656 novos validos** em **75.095**
  novas secoes EA20 apos o corte.
- A cauda inteira publicada teve **54,08809178% Lula**.
- R² observado dos percentuais cumulativos Lula:
  por **secoes 0,9904447872**, por **validos 0,9897050825**;
  a linearidade nao e particular ao simples contador de secoes.

### Controle retrospectivo de composicao constante

Preservamos o numero **real** de votos validos e secoes
de cada uma das 152 atualizacoes, mas fixamos o percentual
de Lula dos novos votos em **54,08809178%**, isto e, a
taxa de todo o conjunto publicado apos o corte.
O modelo cumulativo e

    L_model_i = L_corte + round(p_tail * (VV_i - VV_corte))
    share_model_i = 100 * L_model_i / VV_i

Cada candidato (Lula e Flavio) recebe votos INTEIROS por arredondamento cumulativo. Verificamos que todos os incrementos sao possiveis entre zero e os validos de cada lote, que ambos somados cabem nos votos validos e que o final inteiro fecha exatamente. Este controle deu R² **0,9988478072** por secoes e
**0,9989823110** por validos, mais linear que o real.
O erro RMSE da curva real perante o controle foi
**0,1332003580 ponto percentual**, com desvio maximo
**0,2384951882 pp**.

**AVISO:** p_tail foi estimada com os votos FINAIS da
propria cauda; o controle e **IN_SAMPLE e circular**.
Demonstra que volumes acumulados com participacao constante
sao capazes de produzir uma reta muito lisa, nao que
a composicao real foi constante, nem que tal processo
explica causalmente a sequencia EA20.

### A composicao real variou

Grupos consecutivos aproximadamente iguais em votos,
sem repartir um lote no meio (ordem EA20):

| Bloco | ValidOS acrescentados | Lula entre novos validos |
|---|---:|---:|
| 1 | 4.891.708 | 50,81473% |
| 2 | 4.746.818 | 52,53856% |
| 3 | 4.778.781 | 53,39887% |
| 4 | 4.392.349 | 60,15804% |

Logo, a participacao entre os lotes realmente publicados
se altera consideravelmente, embora a curva cumulativa
permaneca muito lisa. Nos 20 ultimos incrementos,
Lula teve 81,69853%, mas esse conjunto representa
apenas **40.270 votos validos** (0,214% da cauda):
o valor extremo tardio nao deve dominar a interpretacao.

### Controle sem conhecimento dos futuros votos

Estimar a taxa somente nos **10 primeiros incrementos EA20
apos o corte**, totalizando **6.546.962 validos**, cerca de
**34,8064%** da cauda publicada, resultou em
**51,22462907% Lula** nesse treino.

Congelando essa taxa e usando os **volumes de votos validos
observados** em cada update futuro (mas nao seus votos
por candidato), a previsao final de Lula acumulada seria
**44,71129773%** contra **45,16276791%** observados.
RMSE cumulativo fora do periodo de treino **0,326313 pp**.
E um teste da estabilidade da taxa dado o volume futuro,
nao previsao do volume ou ritmo de publicacao.

## Fase X implementada

`audit_ea20_publication_mechanics_2026.py`

- usa o CSV EA20 nacional versionado, com verificacoes
  de totais nacionais, cronologia e incrementos de votos
  inteiros, sem ZIP/SQLite/BWEB ou downloads;
- mede R² de curva real e do controle constante para eixos
  seções, validos e horario real;
- mede RMSE da curva real contra o oraculo;
- mede o modelo com treino inicial e avaliacao posterior;
- classifica quatro blocos cronologicos por volumes de
  votos validos aproximados, sem fracionar lotes;
- resolve a proporcao que cada lote teria de acrescentar
  para uma reta **exata pelos extremos**; se exceder [0,100%],
  registra a violacao de limite fisico;
- exporta todos os lotes por snapshot, sumario e quatro
  blocos com SHA-256.

Saidas em H:/TSE/forensics/urnas/analysis/periodicidade_bweb_2026:

- `phase5s_ea20_publication_mechanics_2026_summary.json`
- `phase5s_ea20_batch_mechanics_2026.csv`
- `phase5s_ea20_equal_volume_blocks_2026.csv`

Notebook: `notebooks/TSE_2026_Laboratorio_Forense_Fase_X.ipynb`.
O menu **U** abre o notebook X automaticamente depois da X.

**Conclusao ainda pendente:** os lotes publicados sao capturas
de incrementos do agregado nacional; nao sabemos, de cada
incremento, a lista individual de BUs nem seu momento de entrada
no mecanismo interno. A etapa posterior deve investigar se a
publicacao nacional pode ser decomposta por snapshots estaduais
sincronizados e se ha buffering mensuravel, sem presumir fraude
nem equiparar BWEB a EA20.
