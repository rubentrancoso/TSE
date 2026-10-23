# Protocolo permanente de investigação eleitoral multievidência — 2026

**Estado:** diretriz de pesquisa e execução, atualizada em 24/10/2026.
**Autoridade interna:** este documento orienta novas análises; não revoga
o diário, o inventário, os scripts de apuração ou os dados brutos.
**Questão central:** há evidência reproduzível de inconsistência,
alteração não autorizada, problema de totalização ou comportamento
estatístico incompatível com modelos adequados aos dados?

Este protocolo existe para evitar que a equipe se limite à reconciliação
de duas fontes oficiais ou esqueça a linha de investigação original.
**Investigar seriamente qualquer hipótese é obrigatório; pressupor
a resposta antes dos testes é proibido.** Todas as hipóteses aceitam
resultados que as refutem.

## Estado comprovado e pendências

- O motor stream reconciliou 140.699.402 registros examinados,
  135.717.720 elegíveis e 67.858.974 chaves.
- 67.858.746 chaves tiveram valores coincidentes.
- 228 chaves classificadas SEM_SECAO, todas PE, município 30015,
  zona 4, turno 1, cargo 25, dez seções, 2.445 votos BU;
  correspondem ao escopo da eleição especial 6261 do Conselho
  Distrital de Fernando de Noronha. Falta comparar a fonte própria
  de resultados do pleito.
- A equivalência entre CSV BU e CSV seção **não prova**, isoladamente,
  que os dados originais da urna não tenham sido adulterados depois
  do encerramento da votação; ambas as cópias dependem de uma cadeia
  de publicação/informação oficial.
- Os snapshots nacionais e estaduais, a descontinuidade de publicação,
  a reconstrução pós-retomada e controles de 2022 permanecem
  objeto de investigação própria no documento
  `INVESTIGACAO_TOTALIZACAO_2026.md`.

## Eixo A — Testar alteração entre urna, transmissão e publicação

**Hipótese A0:** números publicados e totalizados correspondem aos
dados gerados na urna; atrasos entre versões refletem publicação,
cache, reprocessamento ou diferença de etapas.

**Hipótese A1:** houve alteração material de valores, inclusão,
exclusão ou substituição injustificada de registros entre a geração
na urna e a totalização/divulgação.

**Hierarquia operacional de comparações, por seção e cargo:**

1. BU físico/QR capturado contemporaneamente por terceiros,
   preferencialmente com proveniência verificável,
   versus BU de seção disponibilizado no TSE;
2. artefato transmitido original assinado e verificado
   criptograficamente (não apenas SHA-256 calculado depois
   do download) versus registro publicado;
3. registro de voto digital e logs, quando decodificáveis,
   confrontados com totais BU, limitações e exclusões;
4. soma dos BU por seção versus EA20/resultado por zona,
   município, UF, BR e voto por candidato;
5. snapshots temporais de EA14/EA15/EA16/EA18/EA20:
   separar horário da urna, geração, recepção, processamento,
   totalização, publicação na CDN e horário de captura;
6. comparar as mesmas seções já incorporadas para cargos
   estaduais e Presidente, controlando caminhos distintos
   de totalização e latências de publicação.

**Predição falsificável de A1:** discrepância de votos ou de
integridade por seção/candidato após alinhar identificadores de
eleição, turno, cargo, reprocessamentos, anulações, versões
e fontes independentes. Se tudo fecha, registrar resultado
negativo explicitamente. Arquivos com SHA-256 iguais
baixados posteriormente não constituem duas fontes independentes.

Os BUs impressos/QR podem ser coletados por fiscais e eleitores
na seção ao fim da votação. O TSE documenta verificação de
assinaturas e autenticidade na totalização. O objetivo é
medir resultados contra artefatos verificáveis, não presumir
que a alteração seja impossível nem que tenha ocorrido.

## Eixo B — Compatibilidade entre cargos e voto cruzado

**Pergunta:** existe, em seção, zona, município ou UF, uma
combinação de apoio a candidaturas de outros cargos e à
Presidência que seja excepcional, após controle de
heterogeneidade geográfica e política?

**Unidade inicial:** mesma seção, mesmo turno, mesma eleição.
Comparações por zona/município/UF servem para síntese, mas
não substituem a análise de seção.

**Fontes e classificação:**

- Presidente, Governador, Senadores, Deputado Federal e Estadual
  em 2026; 2024 (prefeito) e 2022 em tabelas históricas
  separadas, com documentação de mudanças geográficas,
  cadastro, alianças e comparecimento.
- Construir `classificacao_politica_2026.csv` versionado,
  com `eleicao,uf,municipio,turno,cargo,votavel,bloco,
  fonte_publica,justificativa,grau_de_ambiguidade`.
  Sem classificação automática direita/esquerda por número,
  partido ou cargo. Permitir bloco "indeterminado" e análise
  de sensibilidade a filiação/alianças locais.
- Não inferir voto individual a partir das margens por candidato,
  partido ou seção: dados eleitorais agregados preservam sigilo.
- Há **duas opções de voto para o Senado em 2026** por eleitor,
  em candidatos distintos. A soma de votos a um grupo de
  senadores não é número de pessoas daquele grupo;
  não comparar com Presidência sem normalizar oportunidade
  de votos e limites.
- Prefeitos foram eleitos em 2024, não na votação geral
  de 2026. Usar como indicador histórico territorial,
  não como voto simultâneo do mesmo eleitor.

**Limite lógico obrigatório (sem revelar eleitores):**
para dois conjuntos de escolhas `A` e `B`, no mesmo
eleitorado de tamanho `N`, o número de eleitores
que fizeram ambas as escolhas satisfaz

`max(0, A+B-N) <= |A∩B| <= min(A,B)`.

Exemplo: `N=10`, cinco votos no candidato de direita
para Governador e oito no candidato de esquerda para Presidente.
Pelo menos `max(0,5+8-10)=3` pessoas votaram nos dois
candidatos, se ambos os valores representam pessoas distintas
do mesmo eleitorado. Isso é possível e constitui uma
estimativa **mínima**, não um achado de fraude.

Aplicar o limite apenas a escolhas **unitárias por eleitor**
ou usar bounds específicos para duas vagas ao Senado;
tratar brancos/nulos e comparecimento separadamente;
não construir pseudo-indivíduos a partir da contagem agregada.

**Etapas analíticas:**

B1. Verificar identidade dos denominadores por seção:
aptos, comparecimento, votos válidos, brancos, nulos,
vagas/cargo, seções anuladas e seções com dado ausente.

B2. Criar tabela por seção dos resultados por
Presidente/Governador/Senador/Deputados para cada candidato,
mantendo as linhas originais e o código do pleito.
Agregações devem ser reproduzíveis, sem aplicar blocos
políticos nesta etapa.

B3. Construir várias matrizes: voto presidencial versus
governador; versus os DOIS votos para Senado;
versus partidos/federações para deputados; e mudanças
territoriais 2022/2024/2026. Testar por zona,
município, UF e seções (com tamanho como peso quando adequado).

B4. Medir limites ecológicos mínimos de voto cruzado,
correlações de seção, resíduos relativos à zona/município,
dissimilaridade entre cargos e outliers robustos.
Um `incompatível` não pode significar somente
`politicamente contraintuitivo`; definir a regra e
avaliá-la em controles históricos.

B5. Modelos nulos/alternativos multivariados:
Monte Carlo/permutação condicional por município/zona,
turnout/tamanho e estrutura de apoio local, modelo
beta-binomial/hierárquico e controles de duas vagas
para Senado. Preservar geografia, não supor
independência entre seções ou entre candidatos.

B6. Testes adversariais e robustez: modificar
classificações ambíguas, excluir zonas pequenas,
mudar granularidade, ajustar múltiplas comparações,
treinar/validar em períodos ou UFs separados, e
registrar resultados negativos. Uma correlação
forte, sozinha, não identifica manipulação.

B7. Selecionar anomalias persistentes e examinar
BU físico, QR, hashes, logs, artefatos assinados
e trajetórias temporais das **mesmas seções**.
Sem evidência independente, relatório conclui
`atípico, não explicado`, não `fraude`.

## Eixo C — Padrões estatísticos e séries temporais

Reaproveitar `statistical_forensics.py` e o roteiro
`METODOS_ESTATISTICOS_2026.md`:
Benford com verificação de aplicabilidade,
distribuições de dígitos, dispersão, outliers robustos,
participação versus voto, identidades contábeis,
regimes temporais, CUSUM e change-points,
heterogeneidade geográfica e simulações por seção.
Nenhum indicador isolado é prova.

Investigar o momento de congelamento/retomada de
Presidente em 2026 e o peso geográfico dos lotes:
distinguir ordem de publicação de ordem de votação
e comparar sempre mesmas seções ou mesmos conjuntos
de UFs, quando as fontes permitirem.

## Eixo D — História e alegações sobre 2022

Uma alegação de fraude em 2022 é hipótese/alegação,
não fato estabelecido apenas por ter sido apresentada.
O TCU analisou amostras de BU e publicou que não
encontrou divergência entre os boletins examinados
e os resultados totalizados. Essas auditorias possuem
limites de amostragem e não impedem verificar alegações
pontuais com fontes independentes.

Referência primária:
https://pesquisa.apps.tcu.gov.br/redireciona/acordao-completo/ACORDAO-COMPLETO-2613374

Para qualquer alegação concreta de 2022, exigir
identificador, artefato reproduzível, mecanismo hipotético,
predição falsificável e controles. Comparar 2022/2026
somente após harmonização e com ajustes para candidaturas,
participação, distribuição e composição territorial.

## Matriz de prioridade prática

| Nível | Entrega | Estado |
| --- | --- | --- |
| P0 | Inventário de origem independente de BU/QR/artefatos e validação de assinaturas | Parcial/pendente |
| P0 | Cotejar geração BU vs recepção/publicação por seção e candidato | Parcial/pendente |
| P1 | Fechar pleito especial 6261 sem apagar 228 ocorrências | **Concluído em agregado por zona**: 24 votáveis, 2.445 votos, 10 seções, zero diferenças; verificação individual por seção ainda pendente |
| P1 | Perfil por seção de Presidente/Governador/Senado/Deputados | A construir |
| P1 | Limites ecológicos de voto cruzado por seção e sensibilidade da classificação | A construir |
| P2 | Modelos nulos, permutação condicionada, correção de testes múltiplos | A construir |
| P2 | Comparação histórica 2022 e prefeitura 2024 com compatibilização | A construir |

## Regra de evidência, relatório e publicação

Todo teste informa: hipótese e alternativa, motivação, origem,
URL e SHA-256, unidade geográfica/temporal, universo e exclusões,
código/fingerprint, método, parâmetros escolhidos antes dos
resultados, testes de robustez, alternativas explicativas e grau
de conclusão.

Rótulos aceitos: `CONFIRMADO`, `REJEITADO`,
`INDETERMINADO`, `ANOMALIA_NAO_EXPLICADA`,
`INAPLICAVEL`, `DADO_INSUFICIENTE`.
A expressão `FRAUDE_DEMONSTRADA` requer cadeia
causal/material de evidências independentes,
não pode ser produzida automaticamente por modelo
estatístico exploratório.

Preservar snapshots, fontes, logs, checkpoint e
relatórios antigos; publicar novos derivados sem
sobrescrever evidencia. GitHub: somente branch main,
sem pull requests. Documentar cada execução no
`DIARIO_INVESTIGACAO.md`.
