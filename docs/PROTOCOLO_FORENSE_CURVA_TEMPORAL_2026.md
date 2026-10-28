# Protocolo forense da curva presidencial de 2026 — revisão de 28/10/2026

## 1. Problema correto

O foco não é procurar um valor-p favorável ou discutir
probabilidade abstrata de uma linha reta. O foco é averiguar
se a trajetória **observada** dos resultados nacionais do
primeiro turno é compatível com a cadeia operacional:

- votação em seções identificadas;
- disponibilização/recebimento de BWEB;
- totalização de votos e publicação de versões EA20;
- heterogeneidade geográfica dos lotes;
- representação em gráficos e janelas de captura.

Uma curva lisa ou monotônica é um sintoma a investigar,
não uma conclusão pronta sobre fraude ou sua inexistência.

## 2. Defeito de visualização encontrado e corrigido

Arquivo: `index.html`, gráfico `#chart`, opção
`xmode=time`. Antes de 28/10/2026, o código usava:

    const xs=viewH.map((x,i)=>xm==="pst"?+x.pst:i);

Ou seja, embora o seletor exibisse `Eixo: horário`,
o eixo X era **índice da atualização**, espaçando
igualmente intervalos de 21 segundos e de dezenas de
minutos. Isso afeta a aparência das inclinações:
**não era um eixo de tempo físico**.

A correção lê os campos `dt/ht` de cada snapshot,
calcula distâncias proporcionais aos segundos entre
versões (inclusive ao cruzar a meia-noite) e exibe
rótulos de data+hora. O antigo espaçamento por índice
permanece disponível sob a legenda explícita
`Eixo: atualização (espaçamento igual)`.
Se faltarem timestamps válidos, o painel informa
que recorre ao índice, em vez de identificá-lo
incorretamente como tempo transcorrido.

O painel é o **instrumento de visualização**;
corrigir o eixo não altera os votos ou os arquivos
oficiais preservados. O gráfico usa segmentos
retos entre snapshots observados: o trecho
interpolado é desenho, não medição entre as capturas.

Teste de regressão:
`tests/test_chart_time_axis.js`, executado
em CI Windows e Linux, inclui intervalo temporal
real e passagem de 04 para 05 de outubro.

## 3. Fatos já verificados, sem recomeçar a investigação

- `data/forensics/analysis/phase4f_summary.json`:
  após **04/10/2026 20:04:39 BRT**, a série nacional
  preservada apresentou 152 atualizações até
  05/10/2026 02:59:31, nas quais Lula não caiu
  e Flávio não subiu em percentuais acumulados.
  O padrão **não** é um passo idêntico de
  `+0,01/-0,01` ou uma cadência de 15 segundos.
- `data/forensics/analysis/phase4g_summary.json`:
  recalculando percentuais de votos inteiros, as
  152 mudanças foram estritamente monotônicas;
  18.809.656 votos válidos entraram após o corte,
  Lula 54,0881% e Flávio 39,3429% nesse conjunto.
  O conjunto de lotes é de tal composição que o
  sentido das curvas persistiria em **qualquer**
  permutação dos 152 lotes.
- `phase3j_summary.json`, `phase4h_summary.json`
  e Fases 3I/4J: há evidência de dependência
  territorial do horário de chegada/totalização.
  Isso propõe uma hipótese de mecanismo geográfico,
  não a comprovação automática de sua suficiência.
- Fases H/M: 499.206 BWEB presidenciais de primeiro
  turno têm horário de recebimento, com 5.246 votos
  do número 28 corretamente tratados como nulos
  técnicos e **119.300.788 válidos** reconciliados.
  O campo BWEB `DT_BU_RECEBIDO` não equivale
  necessariamente ao instante de publicação EA20.
- Fases N/P/Q/R tratam periodicidade, chaves e
  discrepâncias, mas **não substituem** uma
  reconstrução causal da curva pós-retomada.

## 4. Próxima investigação operacional — testes, não justificativas

### A. Separar três curvas

1. **EA20 público efetivamente capturado:** pontos com
   data/hora real, votos inteiros acumulados, lote
   incremental e intervalo desde a versão anterior.
2. **BWEB individual reconstruído:** agrupar por
   segundo de `DT_BU_RECEBIDO`, sem inventar
   ordem dentro de um mesmo segundo e com
   denominador válido corrigido na M.
3. **Predição territorial condicionada:** agregar os
   BWEB observados por UF/município/zona e medir,
   dentro de cada estrato, quais localidades
   chegaram antes e depois do corte. Preservar
   o perfil de cada localidade e os tamanhos
   dos lotes na comparação.

As séries 1 e 2 não devem ser fundidas artificialmente:
um BU recebido às 20:02 pode aparecer no agregado
nacional em uma versão gerada depois, e isso exige
medir atraso/buffering, não assumir igualdade.

### B. Procurar mecanismo falsificável

- Verificar se a sequência acumulada de incrementos
  fica **mais lisa** do que seria esperado após
  preservar tamanho, origem geográfica e tempo
  de recepção dos lotes.
- Medir **curvatura, erro de previsão, direção
  e mudança de regime** na série de votos inteiros,
  e não apenas no percentual exibido com duas casas.
- Testar o efeito de retirar UF, município ou
  zonas de uma vez, evitando que um padrão
  agregado seja tratado como um sinal
  uniforme em todas as regiões.
- Investigar a concentração de lotes com
  perfil político semelhante após 20:04
  comparando com perfis ANTERIORES da própria
  eleição e com a geografia histórica, sem
  presumir que eleições distintas sejam
  experimentos idênticos.
- Se a série EA20 for muito mais regular que
  a reconstrução por tempos BWEB, localizar
  **quando e onde** a diferença surge:
  coleta, armazenamento, ordenação,
  emissão de versão ou apresentação.

### C. Controles positivos e negativos

- **Controle negativo:** visualização com
  índice equidistante contra escala temporal
  real; sem alterar os votos. O objetivo é
  mostrar quanto da aparência é do gráfico.
- **Controle geográfico:** UF isolada, município
  isolado, zona isolada e amostras de BWEB
  com mesmos intervalos e volumes.
- **Controle de processamento:** incluir/excluir
  blocos com timestamps empatados, preservar
  brancos, nulos e o número 28 como categoria
  própria, sempre com total de votos conciliado.
- **Controle de publicação:** tratar atualizações
  nacionais tardias como possíveis lotes
  administrativos com buffering, sem assumir
  que a ordem de votos foi gerada nesse instante.

## 5. Comparação com eleições dos EUA

A observação visual é válida como alerta investigativo.
Mas uma comparação forense precisa usar **o mesmo tipo
de curva**: proporção acumulada ou saldo de votos,
mesmo eixo X (horário real, evolução por atualização
ou porcentagem de seções), resolução temporal e
mesma unidade territorial. Em especial, uma curva
agregada de milhares de municípios não é diretamente
comparável a um gráfico isolado de condado/estado ou
a boletins de atualização com cadência diferente.
Uma fonte americana independente e com timestamps
preservados só será incluída depois de fixarmos
essas condições de comparação; não se presumirá
que "nunca ocorre" ou que "pode ocorrer" sem dados.

## 6. Critérios de decisão e limites

- **Representação corrigida:** a linearidade desaparece
  quando se usa o horário real? Se sim, documentar
  artefato de visualização, não descartar o fenômeno
  residual.
- **Composição suficiente:** as contribuições por
  UF/município/zona e volumes de lotes explicam
  numericamente a trajetória e sua suavidade?
  Exigir reconciliação de votos e identidade.
- **Mecanismo ainda inexplicado:** se os dados
  individualizados e a logística de recebimento
  não sustentarem o agregado, registrar a
  divergência com chaves, timestamps, hashes,
  magnitudes e hipóteses alternativas.
- **Indício auditável de alteração:** valores
  oficiais incompatíveis com fontes autenticadas
  independentes ou alteração demonstrável de
  artefato. Uma curva estética incomum por
  si só não identifica essa causa.

Nenhum resultado de teste da futura etapa A/B/C
foi executado aqui. Os resultados disponíveis
são das fases previamente concluídas.


## 7. 28/10/2026 — Fase 5O, análise operacional implementada (opção S)

**Resultado já calculado sobre a fonte EA20 versionada (193 snapshots):**
o corte de 20:04:39 BRT produz 153 pontos (152 intervalos).
Ajustando a reta diretamente aos percentuais de votos inteiros
acumulados para Lula, o ajuste descritivo varia fortemente
segundo o eixo horizontal:

| Eixo X | R² da reta | RMSE em ponto percentual | Desvio máximo em pp |
|---|---:|---:|---:|
| Horário real transcrito dos campos gerado_brt | 0,61017 | 0,29103 | 1,25438 |
| Índice da atualização | 0,84211 | 0,18522 | 0,51801 |
| Número de seções EA20 st | **0,99044** | **0,04556** | 0,17478 |

O intervalo observado entre versões vai de 21 a 5.224
segundos, duração total de 414,87 minutos no trecho.
Isso comprova alta linearidade descritiva no eixo
`st`; não equivale a uma sequência proporcional
a minutos de relógio. O diagnóstico usa
`data/forensics/analysis/phase5a_presidential_national_2026.csv`,
não capturas hipotéticas de outros países.
R² não é uma probabilidade de fraude.

**Código implementado:** `analyze_operational_curve_2026.py`,
disponível na opção **S** do painel Windows:
- valida o SHA de cada BWEB/UF já derivado pela H
  e dos caches por seção da correção NR28 da M;
- reconcilia exatamente 499.206 seções, 119.300.788
  votos válidos, 53.879.538 Lula e 56.104.503 Flávio;
- reproduz por minuto a série corrigida da M com
  checagem de SHA e dos incrementos inteiros;
- calcula separadamente a curva de versões EA20
  (horário real, índice de atualizações e seções);
- monta a curva dos BU por hora real de
  `DT_BU_RECEBIDO`, sem presumir que BU recebido
  foi imediatamente publicado pelo EA20;
- constrói dois **contrafactuais geográficos**
  que mantêm as quantidades reais recebidas por
  minuto, mas atribuem a cada lote sua taxa final
  observada na própria UF ou município;
- compara desvios dos modelos geográficos com a
  série de recebimento real, sem confundir
  ajuste in-sample com previsão causal independente.

A opção S não baixa dados, não abre ZIP e não
consulta SQLite. Saídas no H:
`phase5o_operational_curve_2026_summary.json`,
`phase5o_ea20_time_axes_2026.csv`,
`phase5o_bweb_receipt_geo_2026.csv`,
`phase5o_uf_receipt_breakdown_2026.csv`.

**Pendente:** a execução S sobre H com BWEB
individual e avaliação do resultado contrafactual.
Até lá não foi verificado se a geografia
por município responde pela linearidade
EA20 de R²=0,9904.


## 8. Resultado real da S e avanço para T — 28/10/2026

**A Fase 5O (opção S) foi executada com sucesso no Windows**
sobre o acervo local SHA-validado de 2026, com 499.206
BWEB e correção técnica de `NR_VOTAVEL=28` herdada da M.

A reconstrução confirma os resultados do EA20 de
153 pontos após 20:04:39 BRT:
- reta por **tempo real**: R² = **0,61016581**;
  RMSE = 0,29103431 pp;
- reta por **número de atualizações**: R² = **0,84210892**;
  RMSE = 0,18521793 pp;
- reta por **número de seções**: R² = **0,99044479**;
  RMSE = 0,04556427 pp (medido diretamente da série
  EA20 versionada, não do mesmo modelo geográfico).

Na série cumulativa reconstruída a partir do
`DT_BU_RECEBIDO` por minuto, para o trecho posterior
ao corte, a diferença entre a composição municipal
FINAL e o perfil de votação realmente recebido foi
de **RMSE 0,06164460 pp** para Lula
(Flávio: 0,05065081 pp).
O modelo com proporções FINAIS por UF teve erro
maior: Lula **0,17470034 pp**
(Flávio 0,14542577 pp).
Isso confirma que a mistura de municípios explica
uma parte grande das variações acumuladas
quando empregamos as proporções eleitorais
**finais da mesma eleição**.

**A ressalva fundamental é vazamento de informação:**
as taxas finais por município são extraídas dos
mesmos votos cujo comportamento pretendemos
explicar. Um RMSE baixo nesse contrafactual
*in-sample* não é prova de previsibilidade
anterior à apuração nem demonstra por si
que a cadeia de publicação EA20 é explicada.
Além disso, a agregação cumulativa suaviza
flutuações locais, e erro pequeno da curva
cumulativa pode esconder erros grandes por lote.

**Divergência temporal a não confundir com votos perdidos:**
a Fase 4G registra 18.809.656 válidos publicados
após o último snapshot nacional 20:04:39,
enquanto a S registra 13.627.882 válidos
nos BU com `DT_BU_RECEBIDO` posterior ao corte.
A diferença aritmética de **5.181.774** não prova
falta de votos: recebimento e publicação são
eventos distintos, e um BU recebido antes
pode integrar uma versão publicada depois.
O corte por minuto na S pode incluir o minuto
20:04 inteiro; a próxima opção T separa
rigorosamente antes/depois **por segundo**.

### Fase 5P / opção T: teste sem conhecimento do resultado final

Nova rotina: `test_geographic_holdout_curve_2026.py`.
Usando os mesmos BWEB de H e a correção NR28 de M,
divide cada seção segundo a data/hora de recebimento
exata em segundos, no corte **20:04:39 BRT**.

Treina somente com dados de antes do corte:
- proporção anterior do Brasil;
- proporção anterior de cada UF;
- proporção anterior de cada município, suavizada
  pelo perfil UF anterior com peso fixo de 1.000
  votos para evitar estimativas extremas de
  municípios com pouca cobertura;
- municípios sem amostra prévia usam apenas a
  proporção anterior de sua UF (ou do BR se
  também faltar cobertura estadual).

Avalia os BU de depois do corte, separando erro
de lote por minuto, ponderado pelo número de
votos válidos, e erro na proporção final da cauda.
O modelo municipal com proporções finais da
mesma eleição reaparece exclusivamente como
**referência circular rotulada de vazamento**,
para mostrar quanto o ajuste in-sample pode
superestimar poder explicativo.

Gera:
- `phase5p_holdout_geographic_curve_2026_summary.json`;
- `phase5p_holdout_receipt_curve_2026.csv`;
- `phase5p_holdout_by_uf_2026.csv`;
- `phase5p_holdout_by_municipality_2026.csv`.

A opção T não baixa arquivos, não abre ZIP, não
consulta SQLite e não analisa segundo turno.
O T ainda não foi executado com os dados reais
do disco H: do operador.
