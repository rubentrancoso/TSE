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
| P1 | Perfil por seção de Presidente/Governador/Senado/Deputados | Extrator `cross_office_sections.py` publicado; execução real no H: pendente |
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


## Execucao da matriz de votos entre cargos (24/10/2026)

O modulo `cross_office_sections.py` consome **somente** as
256 particoes TSV assinadas localmente com SHA-256 pelo
`reconcile-stream-v1`. Seleciona exclusivamente
`source_kind=bu`, sem reabrir o SQLite e sem misturar
fontes BU e seção. Agrupa por UF/municipio/zona/secao/turno/
cargo/votavel e soma duplicatas com checkpoint por particao.

```bat
git pull
python -m unittest discover -s tests -p test_cross_office_sections.py -v
python cross_office_sections.py --pilot-buckets 2
python cross_office_sections.py
```

O piloto processa **duas particoes de hash**, nao uma amostra
probabilistica da populacao. Ele nao publica matriz nacional.
A execucao completa retoma as particoes ja confirmadas,
produz `analysis/entre_cargos/<fingerprint>-<versao>/` com:
- `candidatos/bucket-XXXX.csv`: votos BU por
  secao/cargo/votavel; os cargos 1/3/5/6/7/8 sao considerados;
- `secoes/bucket-XXXX.csv`: totais por secao
  para Presidente, Governador e Senado, com ausencias explicitas;
- `secoes_por_cargo.csv`: matriz consolidada de secoes;
- `state.json`, `summary.json`: progresso,
  SHA-256 e contagens verificaveis.

Os totais por cargo **nao equivalem a apoio ideologico**.
Diferença entre a soma de votos de Presidente e Governador
na mesma secao nao prova adulteracao, sobretudo em casos
de regras eleitorais e eleitores habilitados por cargo
distintos. O Senado tem duas oportunidades de voto; nunca
interpretar soma de senadores como numero de eleitores.

Antes dos testes de transferencias politicas, criar e revisar
uma tabela de classificacao de candidaturas e alianças, com
fontes explicitas e variantes de sensibilidade.

**Estado:** codigo e testes sinteticos publicados; piloto
nacional e testes locais no H: ainda aguardam execucao.


## Auditoria descritiva dos denominadores por secao (24/10/2026)

**Evidencia de execucao real:** a matriz entre cargos foi concluida
no computador do investigador com SHA-256
`9aefc6cf4591180a1f2edfdc2cdb7b9e44c19ae8caf2b5d23fa2d6c83f02dfad`.
Ela contem **499.206 secoes** e **67.858.746** chaves BU,
para cargos 1,3,5,6,7,8.
Presidente aparece em 499.206 secoes; Governador e Senado,
em 497.897 cada um; 497.897 secoes possuem ambos
Presidente e Governador. Nestas, **17.233** secoes
(aproximadamente 3,46%) tem totais distintos.
**Nao classificar estas diferencas como divergencias de
totalizacao BU x oficial nem como fraude.**
Os 228 registros do cargo 25 do pleito especial 6261
foram deliberadamente excluidos da matriz regular;
a verificacao agregada especifica ja foi concluida.

**Auditoria seguinte publicada:** `audit_cross_office_totals.py`.
Executar apos o `git pull` e testes:

```bat
git pull
python -m unittest discover -s tests -p test_audit_cross_office_totals.py -v
python audit_cross_office_totals.py
```

O script confere SHA-256 da matriz, repeticoes de secao,
coerencia dos flags de cargo e os contadores nacionais,
sem reler SQLite. Produz no subdiretorio
`auditoria_totais/`: `por_uf_turno.csv`,
`por_municipio_turno.csv`, `maiores_diferencas.csv`
e `summary.json` com SHA-256 das tres saidas.
Documenta a **distribuicao** e a magnitude dos 17.233
casos, sem fazer classificacao ideologica.

Depois: averiguar as maiores diferencas com artefatos BU,
regras de voto por cargo, votos brancos/nulos,
comparecimento e identificador de eleicao, antes da
analise de correlacao territorial de candidaturas.


## Resultado de denominadores e hipotese de voto em transito (24/10/2026)

Auditoria local `python audit_cross_office_totals.py` terminou com
quatro testes unitarios OK e o mesmo SHA da matriz seccional
`9aefc6cf4591180a1f2edfdc2cdb7b9e44c19ae8caf2b5d23fa2d6c83f02dfad`.

**Resumo nacional observado:**
- 499.206 secoes; 497.897 pares Presidente/Governador;
- 480.664 com totais iguais; 17.233 diferentes;
- em TODOS os 17.233, Presidente > Governador;
  zero com Governador > Presidente;
- soma dos votos P em pares = 124.934.069;
  G em pares = 124.768.485; excedente P-G = **165.584**;
- maior excedente em uma secao: 289;
- 174 secoes com excedente superior a 100.

**Explicacao concorrente forte, ainda por comprovar por secao:**
as regras oficiais de 2026 permitem voto em transito
fora da UF apenas para Presidente, e tambem aos inscritos
no exterior em transito no Brasil. Portanto, P>G
sem ocorrencias de G>P e compativel com habilitacao
distinta por cargo; nao e, isoladamente, evidencia
de alteracao pos-transmissao.

Fonte primaria do TSE:
https://www.tse.jus.br/eleicoes/eleicoes-2026-content/voto-em-transito-perguntas-e-respostas

**Teste de controle novo, independente da comparacao BU×secao:**
`audit_cross_office_eligibility.py`. Ele valida o SHA da
mesma matriz, mede quantitativos de Presidente sem
Governador por UF/turno, e confere:
- P >= G em cada secao com ambos presentes;
- Senado = 2×Governador na mesma secao, pois em 2026
  havia duas escolhas ao Senado por eleitor elegivel;
- se Governador e Senado compartilham exatamente
  as mesmas secoes presentes;
- identifica as secoes que contrariem invariantes.

Fonte oficial da regra de duas vagas:
https://www.tse.jus.br/comunicacao/noticias/2026/Setembro/manual-do-eleitor-veja-como-se-preparar-para-a-votacao

Comandos de validacao no H::
```bat
git pull
python -m unittest discover -s tests -p test_audit_cross_office_eligibility.py -v
python audit_cross_office_eligibility.py
```

**Aviso:** Senado=2×Governador e P>=G sao testes contabeis
de plausibilidade, nao prova de quem votou ou da elegibilidade
de cada pessoa. A atribuicao causal de um excedente ao voto em
transito depende de listas oficiais de secoes/habilitacoes ou
de outros dados verificaveis de eleitores por cargo.
Os novos scripts/testes estao publicados na main, mas nao
foram executados no H: neste registro.


## Auditoria de elegibilidade concluída no H: (24/10/2026)

O investigador executou `python audit_cross_office_eligibility.py`,
com **4/4 testes OK**, a partir da matriz original com SHA-256
`9aefc6cf4591180a1f2edfdc2cdb7b9e44c19ae8caf2b5d23fa2d6c83f02dfad`.

**Resultados reais:**
- 499.206 seções com votos presidenciais;
- 497.897 seções também com Governador e Senado;
- 1.309 seções somente com Presidente, somando **341.766 votos**;
- 480.664 seções com P=G;
- 17.233 com P>G, excedente **165.584 votos** nas pareadas;
- **0** com G>P;
- nas 497.897 seções pareadas G/S,
  **497.897 obedecem S=2×G**, 0 exceções e
  soma `S-2G=0`;
- zero quebras de invariantes na amostra.

**Interpretação:** as identidades são compatíveis com a
elegibilidade distinta de voto presidencial e duas vagas
no Senado. O grupo das 1.309 seções sem Governador precisa
de identificação de UF/município, especialmente eleitorado
inscrito no exterior `ZZ`. A coincidência matemática,
dentro de fontes BU, não comprova autenticidade física
nem atribui as diferenças exclusivamente a voto em trânsito.

## Próximo módulo: correlações ecológicas de candidaturas

Foi publicado `cross_office_candidate_correlations.py`.
Em vez de iniciar com rótulos ideológicos presumidos,
o programa seleciona os dois candidatos presidenciais
com mais votos válidos nacionais no turno 1, e
os três candidatos a Governador mais votados em cada UF.
Faz somente leitura das **256 partições BU por candidato**,
com SHA-256 conferido contra o checkpoint da matriz.

Para cada par Presidente/Governador dentro de uma UF,
calcula:
- correlação descritiva bruta de percentuais por seção;
- correlação após retirar médias específicas de
  `municipio+zona` (evita parte do confundimento geográfico);
- número de seções com ambos os cargos presentes e
  denominadores de votos válidos positivos.

O coeficiente **não infere como uma pessoa votou**.
Sem mapa de posicionamento, aliança e partido
versionado, não interpreta direita/esquerda.
Uma correlação forte não comprova manipulação.

```bat
git pull
python -m unittest discover -s tests -p test_cross_office_candidate_correlations.py -v
python cross_office_candidate_correlations.py
```

Relatórios novos em
`analysis/entre_cargos/<fingerprint-versao>/correlacao_presidente_governador/`:
`pares_por_uf.csv` e `summary.json`.
O código ainda aguarda testes reais no H:.


## Modulo Presidente x Senado — 24/10/2026

**Solicitacao explicita do investigador:** o cruzamento
entre cargos deve analisar o Senado com a mesma importancia
de Governador, candidato por candidato. Uma eventual
coerencia ideologica nao deve ser inferida apenas da soma
de votos de candidatos do mesmo bloco.

**Novo codigo** `cross_office_senate_correlations.py`,
com testes sinteticos
`tests/test_cross_office_senate_correlations.py`.

O motor faz somente leitura dos mesmos CSVs de BU ja
extraidos por secao, valida SHA-256 dos 256 arquivos
contra `analysis/entre_cargos/.../state.json` e seleciona
as **duas candidaturas presidenciais mais votadas** no
primeiro turno e, por padrao, **todos os candidatos ao
Senado** presentes em cada UF.

Para cada secao, define:
- `P_s = votos_do_presidenciavel / total_de_votos_para_presidente`
  (inclui brancos e nulos no denominador);
- `S_s = votos_do_senador / (total_de_votos_para_senado / 2)`
  (inclui brancos e nulos no denominador).

Como 2026 teve duas vagas de Senado, `S_s` mede
a proporcao do eleitorado que votou naquele candidato
nas duas oportunidades, **nao** a participacao do
candidato na soma dos votos senatoriais.
Se um candidato tem 40 votos e 100 eleitores,
sua taxa sera 40%, ainda que o total da disputa
ao Senado seja 200 votos. A soma das taxas de
todos os candidatos nao tem obrigacao de 100%.

Para cada par Presidente/Senador, calcular:
- Pearson descritivo bruto por secao dentro de UF;
- Pearson de desvios intrazona (subtrair media
  por municipio+zona, evitando confundimento geografico);
- seções com dados validos para os dois cargos;
- votos totais ao senador, para contextualizar peso amostral.

A implementacao agrega momentos de cada zona ao
final do seu grupo: memoria nao cresce com todos
os grupos territoriais de todo o pais.
Nao deduz o voto presidencial do eleitor a partir
da escolha senatorial; essa inferencia ecologica
nao e identificavel individualmente.

**Comandos, apos `git pull`:**

```bat
python -m unittest discover -s tests -p test_cross_office_senate_correlations.py -v
python cross_office_senate_correlations.py
```

Para um ensaio limitado, pode-se utilizar
`--top-senators 6` (seis senadores por UF),
mas o padrao `0` inclui todos.

Saidas esperadas em
`analysis/entre_cargos/<fingerprint-versao>/correlacao_presidente_senado/`:
`pares_por_uf.csv`, `summary.json`, com SHA-256.
Nao substituem `correlacao_presidente_governador`.
A versao atual ainda nao foi validada no H:;
exigir saida dos testes e processamento real antes
de emitir interpretacao empirica.

**Fontes oficiais para a regra de duas vagas:**
https://www.tse.jus.br/comunicacao/noticias/2026/Setembro/manual-do-eleitor-veja-como-se-preparar-para-a-votacao
https://www.tse.jus.br/eleicoes/informacoes-tecnicas-sobre-a-divulgacao-de-resultados
