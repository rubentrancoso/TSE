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

## RETIFICACAO DE METODO E EXECUCAO ATIVA — 25/10/2026

**Os BUs ja existentes no H: serao reutilizados.**
A proxima tarefa e testar uma hipotese concreta
de formula nos dados somente de 2026, nao fazer
novos inventarios ou downloads.

Uma auditoria do codigo encontrou um erro
no ajuste geografico do Senado v1:
`cross_office_senate_correlations.py` agrupava
momentos por municipio+zona **somente dentro
de cada particao BU**, mas uma zona aparece
em varias das 256 particoes. Assim, **os 13
pares com inversao do Senado sao resultados
provisorios de v1**, nao casos confirmados
apos controle geografico correto. Correcoes
na v2, sem substituir os artefatos v1:

- `cross_office_senate_correlations.py`: v2
  centra as 497.897 secoes pelas **zonas
  completas** de todas as particoes;
- `tests/test_cross_office_senate_correlations.py`:
  fixture de mesma zona dividida por buckets;
- `compare_senate_geo_versions_2026.py` e
  `tests/test_compare_senate_geo_versions_2026.py`:
  comparacao com 616 pares e hashes;
- `test_fixed_vote_formula_2026.py` e testes:
  testa votos P13/P22 = `round(alpha*N_pres)`
  apenas na eleicao 2026, separando treino
  e validacao por hash de secao e comparando
  modelos nacionais, por UF e por zona.

O teste de fórmula nao infere transferencias
entre candidatos. Para comprovar alteracao,
continua necessaria a origem independente da
contagem do BU emitido pela urna. Os limites
de cruzamento do Senado calculados por secao
sao aritmeticamente distintos do erro de
ajuste de medias geograficas, embora a
selecao dos nove candidatos dependa da
triagem antiga.

**Atalho de execucao para Windows (25/10/2026):** depois de
`git pull`, abrir `start_windows.bat` e selecionar
**opcao B — VALIDAR SENADO V2 E FORMULA 2026**.
A opcao roda a bateria de testes sintéticos, a correlacao corrigida,
a comparacao v1/v2 e a formula fixa na ordem indicada abaixo.
Se alguma etapa falhar, as seguintes nao sao executadas.
A opcao B nao efetua novos downloads, nao reindexa e nao abre SQLite.
Os arquivos originais em H: sao preservados; os novos resultados
sao gravados somente em diretorios de analise.

**Validacao de codigo:** a execucao CI
`40225595039` concluiu com sucesso apos corrigir a colisao
de nomes entre o modulo de testes e o script de formula.
**Validacao empirica:** ainda depende de executar a opcao B
com os 256 CSVs no Windows. Nao afirmar os totais reais
de inversoes v2 antes dessa execucao.

**Execucao controlada, sem reler SQLite:**

```bat
git pull
python -m unittest discover -s tests -p test_cross_office_senate_correlations.py -v
python -m unittest discover -s tests -p test_compare_senate_geo_versions_2026.py -v
python -m unittest discover -s tests -p test_fixed_vote_formula_2026.py -v
python cross_office_senate_correlations.py
python compare_senate_geo_versions_2026.py
python test_fixed_vote_formula_2026.py
```

Os CSVs e JSONs novos sao gravados em
`analysis/entre_cargos/<fingerprint>/`,
em subpastas proprias, sem mudar a v1.
Os testes novos ainda dependem de validacao
pelo investigador no Windows, antes de
interpretar resultados reais.

## PRECEDENCIA OPERACIONAL — dados ja coletados no H: (25/10/2026)

A opcao 1 do `start_windows.bat` **ja executa coleta
integral**: `collect_forensics.py all --download-portal-files`
chama `collect_urnas_h()`, que invoca
`urnas.py fetch --all --kind bu --kind secao --kind artefatos`.
O acervo de urnas fica em
`H:/TSE/forensics/urnas/raw/{bu,secao,artefatos}/`
e os dados indexados em
`H:/TSE/forensics/urnas/analysis/urna_2026.sqlite3`.
Os arquivos de portal nao pertencentes a urnas podem
ficar tambem em `H:/TSE/forensics/portal/files/`.

**EVIDENCIA CONFIRMADA:** 67.858.746 chaves BU
ja analisadas, 499.206 secoes na matriz e
497.897 secoes pareadas entre cargos. A ausencia
de `.bu/.rdv` na tabela `archive_entries`
de um inventario parcial nao significa ausencia
de BU digital ou de arquivos baixados e NAO
justifica recomecar downloads ou reindexacoes.

**A partir deste ponto:** nunca usar
`inventory_material_evidence_2026.py` ou
`diagnose_artifact_coverage_2026.py` como
bloqueio obrigatorio para retomar a investigacao.
Eles sao ferramentas OPCIONAIS de metadados,
nao inventarios totais de evidencias e
nao substituem o historico de processamento.
Seguir as hipoteses analiticas sobre 2026,
usando os artefatos existentes. Ver diario E0103.
Nao importar microdados de 2022.

## DIRETRIZ ATIVA — referencia a 2022 e escopo analitico (24/10/2026)

**Correcao explicita do investigador:** nesta linha de trabalho
NAO utilizar bases de votos, resultados, microdados ou distribuicoes
eleitorais de 2022 como controle, treino ou comparacao. A referencia
a "2022" e **conceitual**: existe uma hipotese de uma
**formula ou mecanismo geral alegadamente comum aos pleitos de
2022 e 2026**. Sua existencia, formulacao, parametros e
aplicacao nao estao demonstrados.

**Evidencia empirica para testar essa hipotese agora:
somente dados eleitorais de 2026** (BU, cargo, secao,
publicacao, cadeia de transmissao e registros externos
independentes quando disponiveis). O estudo de 2022
permanece no acervo e no diario como trabalho historico
ja realizado, sem nova leitura, reprocessamento,
reutilizacao como controle ou extensao nesta fase.

**Como testar uma "formula" sem a presumir verdadeira:**
formular uma transformacao matematica concreta de votos,
seu dominio (secao/cargo/candidato/tempo), entradas,
parametros, saidas previstas e residuos falsificaveis.
Ajustar/validar em particoes distintas de **2026**,
controlar geografia, voto em transito, denominadores
do Senado e os demais candidatos; confrontar predicoes
com artefatos de urna e publicacao independentes.
Nao converter dissonancia politica agregada em
inferencia individual ou prova automatica de fraude.

**Precedencia:** este bloco substitui as recomendacoes
anteriores de incorporar dados de 2022
como comparadores na etapa corrente, inclusive nos
blocos historicos deste mesmo arquivo e em mensagens
anteriores. Preservar essas descricoes como registro
da evolucao do plano, nao como comandos ativos.

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


## Resultado real Presidente x Senado — 616 pares (24/10/2026)

Execucao nacional observada: `cross_office_senate_correlations.py`
terminou com sucesso, com 5 testes OK, 27 UFs,
308 candidaturas ao Senado, 497.897 secoes com
ambos cargos e 616 pares Presidente x Senador.
O arquivo `correlacao_presidente_senado/pares_por_uf.csv`
tem SHA-256
`0b05e18dd5eb9b980e203ef361bcbaf069fb28008f51f310cb44b49d8c618d68`.

Este numero de pares confirma apenas a **cobertura de
processamento**; nao classifica sinal ou forca dos
coeficientes, pois o terminal nao exibiu as linhas.

O novo `audit_senate_correlations.py` faz analise
leve **somente desse CSV**, sem reprocessar BU:
verifica SHA-256, existencia de todos os 616 pares,
disponibilidade dos coeficientes e distribuicao por UF.
Produz `correlacao_presidente_senado/diagnostico/`
com `todos_pares.csv`, `por_uf.csv` e `summary.json`.

Filtros **descritivos** predefinidos para evitar
reversoes triviais por ruido de pequena amostra:
- minimo 1.000 secoes;
- minimo 10 zonas com variacao interna;
- minimo 1.000 votos da candidatura senatorial;
- sinais opostos de `r_bruto` e `r_ajustado`
  somente com `|r| >= 0,1` em ambos;
- mudanca de magnitude relevante como
  `|r_bruto-r_ajustado| >= 0,2`.

Nao sao limiares de significancia estatistica nem
probabilidade de fraude. Registrar todas as 616
linhas, incluindo as nao calculaveis ou abaixo
dos limiares, antes de investigar qualquer caso.

```bat
git pull
python -m unittest discover -s tests -p test_audit_senate_correlations.py -v
python audit_senate_correlations.py
```

Para concluir comparacao entre Governador e Senado,
ainda e preciso executar
`cross_office_candidate_correlations.py`
e separar efeitos de denominadores diferentes.
A etapa de comparacao de apoio a blocos partidarios
fica pendente de classificacao historica e geografica
documentada; nao derivar rotulos politicos dos
coeficientes.


## Primeiro fechamento de pares por candidato: 778 (24/10/2026)

`cross_office_candidate_correlations.py` foi executado com
sucesso no H: (4/4 testes sintéticos OK), confirmando **162 pares**
nas 27 UFs, cada UF com 3 candidaturas a Governador e 2 a Presidente.
Foram 497.897 seções pareadas, 67.858.746 chaves BU de origem
verificadas, e SHA-256
`2e76281067a9d8bdb2c59dd3a702baab4fa573e6706a35f2399e1d425b41d627`
para `correlacao_presidente_governador/pares_por_uf.csv`.

Com o modulo do Senado, ha **778 pares de candidatos calculados**.
O novo `audit_cross_office_correlations.py` confere os hashes
dos CSVs de 162 e 616 pares, seu universo, turno e
fingerprint, aplicando criterios descritivos:
- n≥1000 seções por par, ≥10 grupos territoriais com
  variacao, ambos coeficientes calculaveis;
- no Senado, ≥1000 votos no candidato (campo ausente na
  versao existente do arquivo de Governador; esta
  diferenca de controle fica documentada);
- sinal oposto com magnitudes ≥0,1 em ambas medidas;
- mudança absoluta de correlação ≥0,2.

**Importante:** Gov usa votos validos do cargo como denominador
e Senado usa votos totais por eleitor habilitado (dois votos por
eleitor no Senado). Por isso, nao equiparar numericamente
as duas taxas nem usar coeficientes para imputar voto individual.
Outros controles territoriais, multiplos testes,
comportamento historico e artefatos independentes continuam
necessarios para avaliar qualquer suspeita.

Comandos recomendados:
```bat
git pull
python -m unittest discover -s tests -p test_audit_cross_office_correlations.py -v
python audit_cross_office_correlations.py
```

O script gera `diagnostico_conjunto/todos_os_pares.csv`,
`por_uf_cargo.csv` e `summary.json` com hashes.
**Status:** implementado na main; aguarda execucao real
para saber quantos pares mudam de sinal ou amplitude.


## Diagnostico conjunto real dos 778 pares — 24/10/2026

O investigador apresentou o resultado final de
`audit_cross_office_correlations.py`, com 7 testes OK:
162 pares Presidente/Governador e 616 Presidente/Senado.
Ambos os arquivos de origem foram confrontados por SHA-256;
todos os 778 coeficientes bruto e intrazona foram calculados.
O resumo produzido fica em
`analysis/entre_cargos/8ab3ce83c8992b9a-94fc637b4737c20d/diagnostico_conjunto/summary.json`.

**Governador:** 162 pares aptos, zero inversao de sinal
com magnitudes >=0,10 em ambos os coeficientes,
29 mudancas absolutas >=0,20. Direcoes apos ajuste:
71 positivas, 75 negativas, 16 proximas de zero.

**Senado:** 610 pares aptos de 616 (seis nao alcancaram
o filtro de pelo menos 1.000 votos do senador),
13 inversoes relevantes de sinal e 92 mudancas
absolutas >=0,20. Direcoes: 172 positivas, 185
negativas e 253 proximas de zero.
As inversoes ocorrem em oito UFs:
TO=4, AC=2, RN=2, AL=1, AM=1,
PI=1, RR=1, SP=1. Os 13 pares
**nao sao necessariamente 13 senadores diferentes**.

Comparar magnitudes de correlacao entre cargos requer
normalizacao comparavel; Governador usa votos validos,
Senado usa total por eleitor com duas escolhas.
Ambos os conjuntos compartilham as mesmas secoes e
presidenciaveis, logo os pares nao sao independentes.
Sem significancia calibrada e confirmacao documental,
nao atribuir essas inversoes a fraude.

**Proximo passo antes de novas leituras volumosas:**
`review_cross_office_correlations.py`, que verifica
SHA-256 e contabiliza exatamente quais IDs de Senador
e Presidente integram os 13 pares, seus `r_bruto`,
`r_ajustado`, secões, zonas e votos, e quais senadores
sao repetidos nos pares. Retorna tambem lista de todas
as 121 mudancas >=0,20 dos dois cargos. Os relatórios
ficam em `diagnostico_conjunto/revisao_inversoes/`.
Testes sintéticos sao obrigatorios antes da execucao
no conjunto real:

```bat
git pull
python -m unittest discover -s tests -p test_review_cross_office_correlations.py -v
python review_cross_office_correlations.py
```

Essa etapa **nao relê SQLite nem BU**.
Apos examinar os IDs de candidato, enriquecer
com dados oficiais de candidatura/partido/coligacao,
sem classificacao ideologica automatica;
depois calibrar significancia e robustez com
metodos espaciais e controles temporais.


## Limites necessarios de escolha cruzada nos nove candidatos (24/10/2026)

A revisao nacional real identificou nove candidaturas
ao Senado em oito UFs (13 pares com inversao
de sinal, 5 testes OK). Os nomes, partidos e links
publicos ficam em `docs/CANDIDATOS_SENADO_INVERSOES_2026.csv`;
a tabela com as 13 correlações e o contexto metodologico
esta em `docs/REVISAO_INVERSOES_SENADO_2026.md`.
Filiacao partidaria **nao substitui** evidencia de
aliança concreta nem comprova a ideologia do eleitor.

Para responder de modo verificavel a hipotese de
compatibilidade de eleitores entre cargos, o novo
`senate_ecological_bounds.py` mede por secao:
- N = total de votos presidenciais, incluindo brancos,
  nulos e possiveis votos em transito;
- P = votos na secao para um presidencial (13 ou 22);
- S = votos na secao para um senador entre os nove IDs;
- intersecao necessaria minima = `max(0, P+S-N)`;
- intersecao possivel maxima = `min(P,S)`;
- senadores que necessariamente nao cabem nos votos
  do candidato P = `max(0, S-P)`.

Cada candidato senatorial so pode ser escolhido
uma vez por eleitor, apesar das duas vagas ao Senado.
As intersecoes sao **limites**, nao valores observados.
A soma das intersecoes minimas de diferentes categorias
pode ser analisada, mas as maximas individuais nao
devem ser somadas e chamadas de resultado observado.

O script valida o hash de todas as 256 particoes
de candidatos e exige mapeamento exatamente coincidente
com o relatorio anterior. Faz uma varredura BU por secao,
sem abrir SQLite e sem alterar a evidencia.

```bat
git pull
python -m unittest discover -s tests -p test_senate_ecological_bounds.py -v
python senate_ecological_bounds.py
```

Depois de obtidos os limites, interpretar separadamente
a necessidade matematica de votos cruzados, a plausibilidade
sociopolitica e a hipotese de alteracao de totalizacao.
Uma necessidade matematica de voto cruzado **nao e prova
de fraudacao**, apenas um fato dedutivel das contagens
dos BU oficiais existentes.


## Resultado real dos limites senatoriais por secao — 24/10/2026

A execucao de `senate_ecological_bounds.py` no H:
foi concluida; **6 testes sintéticos OK**, 256 particoes
BU verificadas, 67.858.746 chaves conferidas,
nove candidatos ao Senado e 18 pares com P13/P22.
CSV original dos limites com SHA-256
`bdf25f56d647d9265b7e20fcc9e75095f712031659b32bffcc7e7380ff20157f`.

Dentre os resultados, a sobreposicao **minima
matematicamente obrigatoria** com P13 e a quantidade
minima que **nao pode** ter votado em P22:
- Ciro Nogueira/PI: >=289.310 (31,97%) em P13;
  >=413.039 (45,64%) fora de P22;
- Arthur Lira/AL: >=193.108 (20,35%) em P13;
  >=306.199 (32,28%) fora de P22;
- Plinio Valerio/AM: >=125.588 (13,24%) em P13;
  >=165.094 (17,40%) fora de P22;
- Eduardo Gomes/TO: >=35.429 (7,87%) em P13;
  >=65.317 (14,51%) fora de P22.

Todos os nove casos e as ressalvas sao preservados
na entrada E0098 do Diario. Os nove senadores foram
escolhidos **por terem inversoes de sinal de
correlacao**; logo a amostra nao pode representar
os 308 candidatos ao Senado. Valores sao limites
deduzidos dos BU, nao contagem exata de eleitores
cruzados. A investigacao de autenticidade de
artefatos e transmissao continua distinta.

Novo `audit_senate_ecological_bounds.py` faz
conferencia adicional leve: verifica integridade
do CSV de 18 pares, dois presidenciaveis por
senador, percentuais, bounds e identidade
`minimo_fora_de_P = votos_senador - maximo_com_P`,
sem reler BU. Gera uma linha por candidato
com P13 e P22 lado a lado:

```bat
git pull
python -m unittest discover -s tests -p test_audit_senate_ecological_bounds.py -v
python audit_senate_ecological_bounds.py
```

**Depois disso, nao repetir a mesma aritmetica:**
priorizar a calibracao historica e contextual de
compatibilidade, por UF/municipio/zona e por
coligacoes documentadas; testar cenarios
alternativos de classificacao politica e
obter referencias de 2022/2024 ou
simulacoes condicionais.


## Proxima entrega ativa: inventario material exclusivo 2026

A auditoria dos 18 limites senatoriais foi repetida
sem resultados novos. A linha do mecanismo geral
segue sem dados historicos de 2022.

Para deixar de repetir correlacoes e margens
de BU, a proxima etapa utiliza
`inventory_material_evidence_2026.py` e o
protocolo falsificavel
`docs/TESTE_FORMULA_GERAL_SOMENTE_2026.md`.

O inventario consulta a tabela `archive_entries`
do SQLite **somente em leitura** e nao le votos.
Separa artefatos TSE de capturas fisicas/QR
de terceiros declaradas e verificadas por SHA-256.
A existencia de hash em arquivo TSE NAO implica
autenticidade criptografica, independencia de
origem nem identidade com o BU emitido pela urna.
Uma captura declarada tambem nao se torna
independente apenas por constar num manifesto.

```bat
git pull
python -m unittest discover -s tests -p test_inventory_material_evidence_2026.py -v
python inventory_material_evidence_2026.py
```

Nao usar dados eleitorais de 2022 na etapa.
A ausencia de artefatos capturados de forma
independente limita a verificacao de qualquer
transformacao sistematica: marcar
`DADO_INSUFICIENTE` e buscar tais artefatos,
sem tratar ausencia de evidencia como ausencia
de problema ou como prova de problema.
