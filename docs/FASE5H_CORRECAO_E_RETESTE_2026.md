# Fase 5H — corrigir nulos tecnicos e testar novamente a periodicidade em 2026

**Estado em 27/10/2026:** as fases **L e M** foram executadas e CONCLUIDAS
nos BWEB reais de 2026; votos validos corrigidos reconciliados com
resultado nacional, e testes estatisticos refeitos.

## Resultado da opcao L: reconciliacao exata

O operador executou `L — IDENTIFICAR 5246 VOTOS` no Windows.
A rotina leu novamente os ZIPs BWEB originais, validou SHA-256
e verificou os votos do numero presidencial **28** contra a
diferenca de votos validos da opcao K.

Resultado nacional, **28/28 UFs e ZZ reconciliadas**:
- 5.246 votos do numero 28 nos BWEB;
- 5.246 votos a mais na definicao antiga de validos
  (total menos branco e nulo convencionais);
- residuo da conciliacao apos retirar o numero 28: **zero**;
- diferencas de votos dos candidatos 13 e 22: zero em cada UF.

Todos os arquivos originais foram mantidos.

**Nao confundir o prologo de testes:**
a linha inicial no diretorio Temp com
`[NR28 AC] BWEB=5 excedente_K=6` e apenas uma
fixture artificial destinada a testar que uma
divergencia sera detectada. Os dados reais
comecam em `[NR28 AC] BWEB=23 excedente_K=23`;
nao ha UF com residuo real diferente de zero.

Esse resultado encerra a discrepancia de **5.246 votos**
como erro de classificacao do nosso extrator. Os votos
do numero 28 estao nos BWEB, mas nao integram os
validos oficiais. Os totais 13 e 22 bateram exatamente.

## Correcao de denominadores: opcao M

O algoritmo da fase H usava
`validos_antigos = total_de_votos - branco - nulo_convencional`.
A correcao e:

`validos_corrigidos_secao =
   validos_antigos_secao - votos_numero_28_secao`.

Nao basta subtrair 5.246 do denominador nacional:
a classificacao e aplicada na MESMA chave
UF, municipio, zona, secao e por minuto/segundo de
recebimento, preservando a dinamica real dos lotes.

**Pipeline implementado:**

1. Confere o estado final `CONCILIACAO_COMPLETA_NR_28`
   do relatorio L e os SHA-256 do resultado K.
2. Para cada UF, extrai do ZIP BWEB SHA-validado
   o mapa compacto `secao -> votos28`; guarda
   checkpoint com SHA-256, para nunca mais reler
   essa UF se os arquivos nao mudarem.
3. Reune esse mapa aos `received-UF.csv` da fase H,
   cujo SHA continua inalterado. Bloqueia voto
   negativo, chave nao encontrada, contagem divergente
   ou variacao de hash.
4. Confere totais nacionais corrigidos:
   **119.300.788 validos, 53.879.538 de Lula,
   56.104.503 de Flavio e 5.246 anulados da
   contagem antiga**. Se qualquer valor divergir,
   interrompe antes da interpretacao estatistica.
5. Reconstrói as curvas por minuto de recepcao
   (354 instantes, expectativa) e por segundos
   (9.039 instantes, expectativa), SEM inventar
   ordem dentro do mesmo segundo.
6. Refaz as simulacoes por minuto (1.000) e por
   blocos-alvo de 500, 1.000 e 2.000 urnas
   (200 simulacoes por grupo), usando exatamente
   as configuracoes exploratorias da H/J para
   comparar antes vs depois da correcao.
7. Escreve somente novos arquivos `phase5h_*`
   e seus hashes, sem sobrescrever nenhum
   arquivo original das opcoes H, J, K ou L.

**Nao exige downloads, SQLite ou microdados de 2022.**
A primeira execucao necessita ler uma vez os ZIPs BWEB
locais para recuperar a distribuicao do numero 28 por
secao, pois a L arquivou apenas os somatorios por UF.
Reexecucoes passam a usar os checkpoints pequenos.

## Execucao

    cd C:\Users\PC\Documents\git\TSE
    git pull
    start_windows.bat

Selecionar **M — CORRIGIR VALIDADE E REFAZER PERIODICIDADE 2026**.

Ou:

    python correct_bweb_28_periodicity_2026.py

Relatorio resultante:

    H:\TSE\forensics\urnas\analysis\periodicidade_bweb_2026\phase5h_corrected_periodicity_2026_summary.json

## Verificacao de software

Testes sinteticos passaram em **Windows e Linux,
176 testes por sistema**, incluindo arquivo BWEB
ficticio, numero 28 por secao, retoma da UF sem
releitura ZIP, divergencias de integridade e
ausencia de amostra suficiente:

https://github.com/rubentrancoso/TSE/actions/runs/40522038862

Esses testes de software NAO significam que a
fase M tenha sido executada sobre os 499.206
BU reais. Resultado real somente apos
o operador enviar a saida da opcao M.

## Pendencia distinta: 42 secoes

A diferenca entre 499.206 seções da base BWEB e
499.248 seções do ultimo snapshot nacional
continua **NAO CONCILIADA**. Ela nao e explicada
pela reclassificacao dos 5.246 votos.
A referencia estatal versus municipal possui
alguns desvios na BA e MG, mas ainda faltam
chaves para demonstrar sua relacao com essas 42.

A pesquisa de periodicidade continua exploratoria:
p-valores sobre permutacoes de residuos nao
representam probabilidade de fraude e nao
corrigem toda a heterogeneidade territorial.


## Execucao real da opcao M — 27/10/2026

**Situacao: concluida no disco H: com dados reais de 2026.**
A saida do terminal foi fornecida pelo investigador.
As primeiras 5 verificacoes, em pastas temporarias Windows e
com apenas 2 secoes, sao fixtures de teste. A execucao nacional
real comeca em `[NR28 AC] secoes com 28=20, votos=23`.

Os 28 ZIPs BWEB foram lidos novamente apenas para derivar o mapa
numero 28 por secao, e as somas foram comparadas ao cache H, ao
resultado L e ao total nacional. Resultado:
- secoes processadas: **499.206**;
- votos reclassificados de validos para anulados tecnicos: **5.246**;
- votos validos corrigidos: **119.300.788**;
- diferenca entre validos corrigidos e total oficial: **0**;
- Lula (13): **53.879.538**, sem divergencia;
- Flavio (22): **56.104.503**, sem divergencia;
- instantes de recepcao: **354 minutos e 9.039 segundos**
  ja observados na fase J;
- por minuto, 254 lotes com >=10.000 validos;
- por bloco-alvo de 500, 1000 e 2000 secoes,
  respectivamente 893, 470 e 243 lotes.

### Periodicidade antes e depois da correcao

| Medida | Antes H/J | Depois M |
| --- | ---: | ---: |
| Periodo mais forte por minuto | 14,208199 min | 14,208199 min |
| R2 senoidal por minuto | 0,03954052 | 0,03958410 |
| p de permutacao individual (minutos) | 0,3086913 | 0,3066933 |
| p de permutacao em blocos (minutos) | 0,4945055 | 0,4935065 |
| Vales por minuto, limite de 8pp | 1 | 1 |
| Residuo do vale de 21:31 (pp) | -4,43335 | -4,43163 |
| Proeminencia desse vale (pp) | 9,24395 | 9,24548 |
| Votos validos no lote de 21:31 | 15.312 | 15.311 |

| Alvo | Melhor periodo em secoes (antes/depois) | R2 antes | R2 corrigido | p em blocos corrigido |
| --- | ---: | ---: | ---: | ---: |
| 500 | 4.829,436671 | 0,01776219 | 0,01777551 | 0,2089552 |
| 1000 | 4.829,436671 | 0,01976418 | 0,01976781 | 0,8706468 |
| 2000 | 35.103,147196 | 0,04767183 | 0,04768052 | 0,6069652 |

Em todas as tres escalas BU agrupados, **zero vales** ultrapassaram
proeminencia de 8pp. Nulos tecnicos foram retirados corretamente
dos denominadores, sem alterar a frequencia mais forte
nas escalas de 500/1000 urnas.

**Conclusao condicionada:** a regularidade candidata em ~4.829
secoes **nao se tornou estatisticamente robusta** apos a
reclassificacao. O melhor pico em 500 urnas continuou com
p individual 0,039801 mas p com blocos = 0,2089552;
as tres escalas e muitas frequencias nao constituem testes
independentes. Os controles nao preservam toda dependencia
territorial. Nada disso prova fraude ou ausencia dela.

**Estado cientifico:** a conciliacao dos 5.246 votos foi
encerrada com hashes e por secao; a discrepancia de
**42 secoes da contagem** segue separada e ainda nao foi
resolvida por identidade. O estudo de variacao de limiares
e janelas de suavizacao ainda nao foi repetido sobre a
serie corrigida, e testes nulos com dependencia espacial
tambem nao foram executados.

Arquivo de saida local:
`H:/TSE/forensics/urnas/analysis/periodicidade_bweb_2026/phase5h_corrected_periodicity_2026_summary.json`.


## Sensibilidade da serie corrigida — opcao I atualizada

Em 27/10/2026, o painel foi atualizado para que a opcao
**I** execute a analise da grade de parametros **sobre os
denominadores corrigidos da opcao M**, por meio do argumento
`--corrigido` de `sensitivity_bweb_periodicity_2026.py`.

A entrada usada agora e o arquivo derivado
`phase5h_minute_corrected_2026.csv`, com o SHA-256
registrado em `phase5h_corrected_periodicity_2026_summary.json`.
Nao reabre qualquer ZIP, nao faz downloads e nao consulta SQLite.
A grade varia limiares de volume (1000, 5000, 10000, 20000)
e janela central de mediana (9, 15 e 21) em seis
configuracoes predeterminadas, comparando proeminencias de
4, 8 e 12 pontos percentuais.

O novo relatorio sera
`phase5d_sensitivity_corrected_2026_summary.json`
no mesmo diretorio H: das outras fases. A funcao antiga
sem `--corrigido` continua acessivel para reproducibilidade
dos calculos anteriores, mas o menu I passa
**explicitamente pela serie corrigida**.

**A opcao I corrigida ainda nao foi executada com os dados reais.**
Resultados dela nao devem ser afirmados antecipadamente.
Cuidado adicional: os diversos parametros e periodos da
grade sao multiplas comparacoes no MESMO conjunto eleitoral;
selecionar o menor valor-p nao e teste confirmatorio.
