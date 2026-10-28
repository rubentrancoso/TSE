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
