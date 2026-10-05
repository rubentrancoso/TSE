# Diário cronológico da investigação — Totalização 2026

Este arquivo é o **registro temporal imutável da investigação**. Ele documenta o que foi feito, com quais dados, o que foi observado, o que ainda não foi explicado e por que o passo seguinte foi escolhido.

## Regras do diário

- Entradas antigas **não devem ser reescritas para acomodar conclusões posteriores**.
- Se uma conclusão mudar, criar uma nova entrada corrigindo a anterior e explicar o motivo.
- Distinguir sempre: **observação**, **cálculo**, **hipótese**, **limitação** e **próxima ação**.
- Todo resultado quantitativo deve apontar para o script e/ou arquivo derivado que o produziu.
- Commits Git funcionam como âncoras temporais adicionais; o horário exato fica preservado no histórico do repositório.
- Dados brutos permanecem fora do Git quando forem grandes, mas seus hashes/manifests e todos os relatórios derivados relevantes devem ser preservados.

---

## 2026-10-05 — E0001 — Formalização da investigação

**Evento:** criação do protocolo metodológico da investigação.

**Motivação:** investigar de forma reproduzível a interrupção/defasagem observada na divulgação presidencial e separar atraso operacional, divergência de agregação e eventual discrepância material de votos.

**Documento criado:**  
`docs/INVESTIGACAO_TOTALIZACAO_2026.md`

**Commit:** `7be6ed3f66d9fc54816652bb7a7bb26206df5aed`

**Decisões metodológicas:**
- não presumir a causa da anomalia;
- tratar fato observado, anomalia, hipótese e evidência de fraude como categorias diferentes;
- priorizar reconciliação determinística e hierárquica;
- preservar cadeia de custódia;
- usar estatística exploratória apenas quando compatível com a estrutura dos dados;
- reservar conclusão forte sobre fraude para discrepância material reproduzível e/ou evidência adicional de mecanismo.

**Próxima ação definida:** preservar dados oficiais e construir testes de reconciliação.

---

## 2026-10-05 — E0002 — Coleta forense disponível localmente

**Evento:** execução do `collect_forensics.py` no computador local.

**Estado reportado pelo coletor antes da nova análise:**
- snapshots locais encontrados: **8**;
- snapshot mais recente: `20261005T104314Z`;
- JSONs de UF/município no snapshot: **5.785 / 5.785**;
- percentual nacional do snapshot final: **100,00%**;
- arquivos completos do portal oficial: **224**;
- volume local dos arquivos do portal: **372,13 MB**;
- arquivos temporários incompletos: **0**;
- nacional sem mudança, portanto o snapshot final foi reutilizado;
- JSONs adicionais a baixar: **0 / 5.785**;
- recursos do portal adicionais a baixar: **0 / 224**;
- erros no download do portal: **0**.

**Disponibilidade urna por urna verificada pelo coletor:**
- Boletins de Urna: **ainda não disponíveis no catálogo consultado**;
- arquivos `.bu/.imgbu/.rdv`: **ainda não disponíveis**;
- votação por seção: **ainda não disponível**.

**Observação:** isso permite análise BR↔UF↔município, mas ainda não permite reconciliação BU/seção por seção.

**Limitação:** os dados brutos ficam em `data/forensics/` e, naquele momento, estavam ignorados pelo Git.

**Próxima ação definida:** executar uma primeira reconciliação usando somente os JSONs já coletados.

---

## 2026-10-05 — E0003 — Implementação da Fase 1

**Evento:** criação do analisador `analyze_forensics.py`.

**Commit:** `b99a05c96ccefaec1210e7c1c2babe13c5eeefcc`

**Testes implementados:**
1. fechamento interno: soma dos candidatos = votos válidos;
2. Brasil = soma das UFs/ZZ;
3. UF = soma dos municípios no snapshot final;
4. medição da janela real de coleta do snapshot para identificar comparações não atômicas.

**Saídas planejadas:**
- `data/forensics/analysis/phase1_summary.json`
- `data/forensics/analysis/snapshots.csv`
- `data/forensics/analysis/municipality_reconciliation.csv`
- `data/forensics/analysis/accounting_errors.csv`

**Próxima ação definida:** executar o script sobre os 8 snapshots locais.

---

## 2026-10-05 — E0004 — Resultado da primeira reconciliação

**Evento:** execução local de `python analyze_forensics.py`.

**Resultado reportado pela execução:**
- snapshots analisados: **8**;
- snapshot final: `20261005T104314Z`, **100,00%**;
- diferença de votos válidos `BR - soma UFs`: **0**;
- maior diferença por candidato `BR - soma UFs`: **0**;
- UFs com divergência `UF - soma municípios`: **2**;
- falhas de fechamento contábil interno: **0**.

**Interpretação limitada desta etapa:**
- no snapshot final, a camada nacional fecha exatamente com a soma das 28 abrangências (27 UFs + exterior);
- nenhum JSON analisado apresentou falha no teste interno de votos válidos versus soma dos candidatos;
- duas divergências permaneceram no nível UF↔municípios e exigiram decomposição adicional.

**Importante:** neste ponto ainda não foi atribuída causa às duas divergências.

**Próxima ação definida:** versionar os relatórios e inspecionar BA e MG em detalhe.

---

## 2026-10-05 — E0005 — Versionamento dos resultados derivados

**Evento:** ajuste do `.gitignore` para manter dados brutos grandes fora do Git, mas permitir o versionamento de `data/forensics/analysis/`.

**Motivação:** os dados baixados não apareciam no `git status` porque `data/` estava integralmente ignorado.

**Resultado:** os relatórios derivados passaram a poder ser commitados sem obrigar o versionamento dos centenas de MB/GB de arquivos brutos.

**Commit dos relatórios realizado localmente pelo investigador:**  
`dd2ea97ae98cef5993cd48b80c295dac342936b8`

**Arquivos versionados:**
- `accounting_errors.csv`
- `municipality_reconciliation.csv`
- `phase1_summary.json`
- `snapshots.csv`

**Observação de higiene do repositório:** o mesmo commit também criou um arquivo chamado `python`; isso não faz parte dos resultados científicos e poderá ser removido separadamente.

---

## 2026-10-05 — E0006 — Leitura independente dos resultados da Fase 1

**Fonte:** arquivos versionados no commit `dd2ea97`.

### E0006-A — Reconciliação nacional final

No snapshot final:
- seções BR: **499.248**;
- soma das seções das 28 abrangências: **499.248**;
- diferença: **0**;
- votos válidos BR: **119.300.788**;
- soma dos votos válidos das 28 abrangências: **119.300.788**;
- diferença: **0**;
- maior diferença por candidato: **0**.

**Observação:** a fotografia final BR↔UF/ZZ está matematicamente reconciliada.

### E0006-B — Fechamento contábil

`accounting_errors.csv` contém apenas o cabeçalho.

**Observação:** o analisador não encontrou, nos arquivos verificados, caso em que:
- soma dos votos dos candidatos ≠ votos válidos; ou
- válidos + brancos + nulos ≠ comparecimento, quando os campos eram comparáveis.

### E0006-C — Divergências UF↔municípios

Foram encontradas exatamente duas:

**Bahia**
- municípios presentes: **417**;
- votos válidos no JSON da UF: **8.560.291**;
- soma dos municípios: **8.559.047**;
- diferença: **+1.244 votos** no agregado da UF;
- maior diferença individual entre candidatos: **967 votos**.

**Minas Gerais**
- municípios presentes: **853**;
- votos válidos no JSON da UF: **11.976.235**;
- soma dos municípios: **11.968.327**;
- diferença: **+7.908 votos** no agregado da UF;
- maior diferença individual entre candidatos: **4.898 votos**.

**Status:** **anomalias em investigação; causa ainda não determinada**.

### E0006-D — Snapshots intermediários BR↔UF

Foram observadas diferenças pequenas e com sinais diferentes entre o nacional e a soma das UFs antes da estabilização final.

Exemplos:
- `20261005T002055Z`: votos válidos BR − UFs = **−16.436**;
- `20261005T003141Z`: **+391**;
- `20261005T004102Z`: **+10.364**;
- `20261005T005057Z`: **−313**;
- `20261005T054655Z`: **0**;
- `20261005T104314Z`: **0**.

Os manifests mostram janelas de coleta de aproximadamente **162 a 239 segundos** em vários snapshots.

**Limitação crítica:** nacional e UFs não foram baixados atomicamente. Portanto, essas diferenças intermediárias não podem ser tratadas diretamente como discrepância eleitoral sem controlar o instante de captura de cada arquivo.

**Próxima ação definida:** decompor BA e MG por seções, comparecimento, brancos, nulos e candidato.

---

## 2026-10-05 — E0007 — Ampliação do analisador para BA e MG

**Evento:** atualização do `analyze_forensics.py`.

**Commit:** `e40c32ec16d0e750663f8f8d3f1f27779cb91cfd`

**Novas medições adicionadas para UF↔municípios:**
- diferença de seções;
- diferença de comparecimento;
- diferença de votos válidos;
- diferença de brancos;
- diferença de nulos;
- diferença por candidato.

**Novo artefato derivado:**
- `data/forensics/analysis/uf_candidate_reconciliation.csv`

**Status desta entrada:** código preparado, mas os novos resultados ainda precisam ser gerados localmente e versionados.

**Próxima ação:** executar novamente `python analyze_forensics.py`, versionar os relatórios resultantes e registrar uma nova entrada neste diário com o diagnóstico de BA e MG.

---

## Próxima entrada esperada

### E0008 — Diagnóstico detalhado das divergências BA/MG

A próxima entrada deverá registrar:
- diferenças de seções;
- comparecimento;
- brancos e nulos;
- diferenças candidato por candidato;
- se a divergência corresponde a categoria territorial/administrativa legítima, defasagem dos JSONs ou outra causa;
- evidências utilizadas para aceitar ou rejeitar cada explicação.


---

## 2026-10-05 — E0008 — Diagnóstico quantitativo das divergências BA/MG

**Evento:** leitura dos relatórios regenerados e versionados após a ampliação da Fase 1.

**Commit que preservou os resultados:** `10e0788d0d0d9759be58349f6af96c9b8725d72e`

**Arquivos usados:**
- `data/forensics/analysis/phase1_summary.json`
- `data/forensics/analysis/municipality_reconciliation.csv`
- `data/forensics/analysis/uf_candidate_reconciliation.csv`
- `data/forensics/analysis/accounting_errors.csv`

### Bahia

Diferença UF − soma dos 417 municípios:
- seções totalizadas: **+6**;
- comparecimento: **+1.322**;
- votos válidos: **+1.244**;
- brancos: **+29**;
- nulos: **+49**.

Identidade contábil da diferença:

`1.244 + 29 + 49 = 1.322`

Diferenças por candidato que somam os 1.244 votos válidos adicionais:
- 13: **+967**
- 14: **+9**
- 21: **+1**
- 22: **+236**
- 55: **+13**
- 70: **+17**
- 80: **+1**
- demais: **0**

### Minas Gerais

Diferença UF − soma dos 853 municípios:
- seções totalizadas: **+36**;
- comparecimento: **+8.413**;
- votos válidos: **+7.908**;
- brancos: **+138**;
- nulos: **+367**.

Identidade contábil da diferença:

`7.908 + 138 + 367 = 8.413`

Diferenças por candidato somam exatamente os 7.908 votos válidos adicionais. Maiores componentes:
- 13: **+4.898**
- 22: **+2.600**
- 14: **+97**
- 70: **+177**
- 55: **+91**
- demais diferenças menores completam exatamente o total.

### Observação técnica

As divergências não têm a forma de um erro aritmético interno: em BA e MG, o excedente estadual forma um conjunto contabilmente fechado de comparecimento, votos válidos, brancos, nulos e votos por candidato.

Além disso:
- BA apresenta exatamente **6 seções totalizadas a mais** no agregado estadual;
- MG apresenta exatamente **36 seções totalizadas a mais** no agregado estadual.

Isso restringe a investigação a duas classes principais de explicação, ainda sem escolher entre elas:

1. os JSONs municipais usados na soma não estavam realmente completos/atualizados; ou
2. existem seções contabilizadas na abrangência estadual que não entram da mesma forma na soma dos arquivos municipais de Presidente.

**Status:** anomalia localizada e contabilmente caracterizada; causa ainda não determinada.

---

## 2026-10-05 — E0009 — Teste preparado para distinguir defasagem municipal de diferença estrutural de abrangência

**Evento:** ampliação adicional do `analyze_forensics.py`.

**Commit:** `af514c7e1d7b4f32383d6543bdcad805480731b7`

**Novo teste:**
- comparar `ts` (total de seções existentes na abrangência), além de `st` (seções totalizadas);
- identificar qualquer município cujo JSON ainda tenha `st != ts` ou percentual abaixo de 100%;
- contar municípios incompletos;
- produzir `municipality_completion_anomalies.csv`.

**Por que este teste é decisivo nesta etapa:**

- Se a soma dos `ts` municipais for igual ao `ts` estadual, mas a soma dos `st` ficar abaixo, a hipótese mais direta será **snapshot municipal incompleto/defasado**.
- Se todos os municípios estiverem em 100% e o próprio `ts` estadual exceder a soma dos `ts` municipais exatamente em 6 (BA) e 36 (MG), teremos demonstrado uma **diferença estrutural de abrangência**, que deverá ser localizada usando EA16/EA18 e, depois, arquivos de zona/seção.

**Base documental:** a especificação EA20 define `ts` como quantidade de seções da abrangência e `st` como quantidade de seções totalizadas. A especificação EA16 mapeia UF → município → zona → seção e permite avançar para a identificação das seções.

**Próxima ação:** executar novamente `python analyze_forensics.py`, versionar os novos relatórios e então decidir, com base em `ts` versus `st`, se a etapa seguinte é:
- localizar arquivos municipais atrasados; ou
- baixar/analisar EA16 para localizar as 6 e 36 seções adicionais.


---

## 2026-10-05 — E0010 — Preparação da Fase 2: localização das seções divergentes

**Evento:** criação do `analyze_phase2_sections.py`.

**Commit:** `dec96cd17b725c0b85a42adf504e8df217c00713`

**Objetivo:** sair da divergência agregada de 6 seções na BA e 36 em MG e tentar localizar em quais municípios, zonas e seções ela está.

**Fontes técnicas utilizadas para construir o teste:**
- EA20: define `ts` como total de seções da abrangência e `st` como totalizadas;
- EA16: estrutura UF → município → zona → seção;
- EA18: para cada seção recebida, informa situação, hashes recebidos e nomes/tipos dos arquivos de urna.

**Procedimento implementado:**
1. baixar/preservar EA16 oficial de BA e MG para o pleito 3220;
2. comparar a configuração de seções com o `ts` dos EA20 municipais;
3. considerar explicitamente a possibilidade de seções agregadas, comparando dois modelos: todas as seções e apenas seções principais;
4. localizar municípios em que a contagem configurada não coincide com EA20;
5. baixar EA20 por zona somente nos municípios anômalos;
6. localizar zonas ainda divergentes;
7. consultar EA18 das seções candidatas que já tenham data/hora de arquivo auxiliar;
8. registrar se BU/RDV/log aparecem como tipos de arquivos disponíveis, sem baixar ainda os binários.

**Artefatos derivados previstos:**
- `phase2_sections_summary.json`
- `section_config_reconciliation.csv`
- `zone_reconciliation.csv`
- `section_candidates.csv`

**Próxima ação:** executar localmente a Fase 1 atualizada e a Fase 2, versionar somente os relatórios derivados e analisar os resultados antes de avançar para a reconstrução temporal da paralisação presidencial.


---

## 2026-10-05 — E0011 — Correção metodológica sobre disponibilidade de BU/EA18

**Evento:** revisão da mensagem de disponibilidade de dados urna por urna no `collect_forensics.py`.

**Problema identificado:** a verificação original consultava o **Portal de Dados Abertos/CKAN** e imprimia “AINDA NÃO DISPONÍVEL”. Essa frase podia ser interpretada de forma mais ampla do que o teste realmente demonstrava.

**Correção:** ausência de dataset urna por urna no catálogo de Dados Abertos **não implica** ausência dos arquivos no CDN utilizado pelo aplicativo Resultados.

**Ação tomada:**
- a mensagem do coletor passou a dizer explicitamente “NÃO ENCONTRADO NO CATÁLOGO DE DADOS ABERTOS”;
- a Fase 2 passa a consultar diretamente EA16/EA18 na estrutura oficial `arquivo-urna`.

**Commit da correção:** `4e4387563c744595a154e70f732e5574c4fba1a6`

**Impacto sobre entradas anteriores:** E0002 continua válido como registro do que o coletor reportou naquele momento, mas a interpretação correta é limitada ao catálogo consultado. Não se deve usar E0002 para afirmar indisponibilidade global de BU/RDV/log no ambiente Resultados.


---

## 2026-10-05 — E0012 — Correção de foco: a anomalia principal é temporal e entre cargos

**Evento:** esclarecimento do escopo central da investigação.

**Correção de foco:** as diferenças de **1.244 votos na BA** e **7.908 em MG** são uma investigação auxiliar de consistência hierárquica. Elas não representam a anomalia principal que motivou este trabalho.

**Anomalia principal a testar:** durante uma janela da totalização, a divulgação/totalização de **Presidente** ficou defasada enquanto resultados de **Governador e outros cargos estaduais** continuaram avançando. Como os votos desses cargos são produzidos pelas mesmas seções eleitorais e constam dos artefatos da mesma urna, a investigação deve comparar o **mesmo conjunto de seções** entre cargos, e não apenas agregados nacionais isolados.

**Escala relevante:** a janela envolve potencialmente **milhões de votos**, não milhares. Portanto a análise central passa a ser multivariada e seção a seção.

### Pergunta principal

Para uma mesma seção eleitoral (s) e um mesmo conjunto temporal (S(t)):

- os dados de Governador/Senado/Deputados dessa seção já estavam presentes?
- os votos de Presidente da mesma seção estavam presentes no BU/EA18?
- o agregado presidencial já os incorporava?

### Testes prioritários

1. **Presença cruzada por seção**
   - seção aparece no cargo estadual, mas não no agregado presidencial?
   - quantas seções?
   - quantos eleitores/votos representam?

2. **Reconstrução presidencial do conjunto já observado nos cargos estaduais**
   - somar Presidente diretamente dos BUs/arquivos de seção das urnas cujos cargos estaduais já haviam sido incorporados;
   - comparar com o agregado presidencial publicado naquele instante.

3. **Análise estatística multivariada**
   - modelar a votação presidencial por seção condicionada a município, zona, comparecimento, brancos/nulos e padrões dos cargos estaduais;
   - comparar resíduos antes, durante e depois da janela;
   - procurar mudança estrutural que não seja explicada pela composição geográfica das seções que chegaram.

4. **Teste de lote/backlog**
   - identificar o conjunto de seções acumulado durante a paralisação;
   - calcular a composição presidencial real desse conjunto;
   - verificar se o salto posterior no agregado presidencial é exatamente a soma dessas seções.

5. **Teste de distribuição conjunta, não apenas marginal**
   - comparar relações entre Presidente, Governador, comparecimento e localização;
   - usar resíduos condicionais, mudança de regime e distância multivariada;
   - não usar apenas distribuição nacional agregada ou testes univariados simples.

### Limitação lógica importante

Uma distribuição artificial pode, em princípio, ser construída para preservar algumas estatísticas marginais. Portanto, nenhuma regra estatística isolada garante detectar toda manipulação possível. O poder da investigação vem de exigir simultaneamente consistência entre:
- seção;
- município;
- UF;
- Brasil;
- cargos diferentes;
- comparecimento;
- brancos/nulos;
- timestamps;
- hashes e BUs.

Quanto mais dimensões independentes precisam fechar ao mesmo tempo, mais restritiva se torna qualquer hipótese de alteração.

**Próxima fase prioritária:** após concluir a localização das 42 seções auxiliares de BA/MG, iniciar a Fase 3 — reconstrução temporal e cruzada entre cargos durante a janela da paralisação presidencial.


---

## 2026-10-05 — E0013 — Fechamento da investigação auxiliar BA/MG

**Evento:** análise dos resultados versionados da Fase 1 atualizada e da Fase 2.

**Commit dos resultados:** `3cf592b9730e588f3fdeb490adaab93952f51e48`

### Resultado BA

- `ts` estadual: **35.476**
- soma de `ts` municipais: **35.476**
- diferença estrutural de seções: **0**
- `st` estadual: **35.476**
- soma de `st` municipais: **35.470**
- diferença de seções totalizadas: **6**
- municípios ainda incompletos no snapshot: **3**
- faltantes nesses municípios: **4 + 1 + 1 = 6**

### Resultado MG

- `ts` estadual: **52.062**
- soma de `ts` municipais: **52.062**
- diferença estrutural de seções: **0**
- `st` estadual: **52.062**
- soma de `st` municipais: **52.026**
- diferença de seções totalizadas: **36**
- municípios ainda incompletos no snapshot: **8**
- faltantes nesses municípios: **4 + 3 + 9 + 7 + 1 + 6 + 1 + 5 = 36**

### EA16

A contagem de **seções principais** do EA16 fecha exatamente com o `ts` estadual:
- BA: **35.476**
- MG: **52.062**

Portanto, não há evidência aqui de seções estaduais “extras” fora da estrutura municipal. A diferença observada decorre de arquivos EA20 municipais que permaneciam atrás do agregado estadual.

### EA18 e artefatos de urna

A Fase 2 consultou as seções das zonas investigadas:
- BA: **285** seções consultadas;
- MG: **175** seções consultadas;
- total: **460** seções.

Resultado:
- **460/460** com EA18 disponível;
- **460/460** com status `Totalizada`;
- **460/460** listando `bu`;
- **460/460** listando `rdv`;
- **460/460** listando `log`;
- **460/460** listando `vota`;
- erros de consulta: **0**.

**Conclusão limitada:** a divergência BA/MG é explicada por defasagem dos EA20 municipais/zonais em relação ao agregado estadual; não é uma discrepância estrutural na quantidade total de seções. Essa conclusão é específica a esta anomalia auxiliar.

**Observação adicional importante:** em Joaíma/MG, o EA20 municipal preservado estava em **85% (34/40)**, enquanto o EA20 de zona consultado posteriormente já aparecia em **100% (40/40)**. Isso demonstra concretamente que diferentes abrangências/arquivos podem refletir versões temporais distintas.

**Decisão:** encerrar BA/MG como trilha auxiliar explicada e retomar imediatamente a anomalia principal — a defasagem de milhões de votos na divulgação presidencial em comparação com cargos estaduais.

---

## 2026-10-05 — E0014 — Plano de viabilidade temporal para a Fase 3

**Pergunta:** os arquivos oficiais atuais ainda preservam informação temporal suficiente para reconstruir quais seções já estavam disponíveis durante a janela da paralisação presidencial?

A documentação técnica do TSE informa que os campos `da` e `ha` do EA16 registram data/hora de geração do arquivo auxiliar da seção e podem ser usados para identificar a chegada dos arquivos da urna.

**Teste de viabilidade definido:**
1. baixar/preservar EA16 das 27 UFs;
2. usar apenas seções principais;
3. construir histograma nacional minuto a minuto de `da/ha`;
4. comparar essa cronologia com a série histórica presidencial já preservada;
5. verificar se a cronologia atual do EA16 é compatível com a evolução observada no dia da eleição.

**Decisão condicional:**
- se os tempos EA16 preservarem a sequência da noite eleitoral, eles passam a ser o eixo temporal da reconstrução seção a seção;
- se os tempos estiverem regenerados/agrupados posteriormente e não reproduzirem a evolução, a Fase 3 precisará depender de capturas históricas contemporâneas adicionais ou de outro artefato temporal oficial.



---

## 2026-10-05 — E0015 — Implementação do teste temporal nacional EA16

**Evento:** criação do `analyze_phase3_arrivals.py`.

**Commit:** `af9589d99e35ddfa90f7b0591cf1d26969b2a458`

**Objetivo:** testar, em escala nacional, se os campos `da/ha` atuais do EA16 ainda preservam uma sequência temporal utilizável para reconstruir a chegada dos arquivos de urna durante a noite da eleição.

**Procedimento:**
- baixar EA16 das 27 UFs;
- considerar apenas seções principais;
- contar cobertura de `da/ha`;
- gerar histograma minuto a minuto;
- registrar primeiro/último minuto e picos de geração;
- comparar depois essa distribuição com a série presidencial preservada.

**Artefatos derivados:**
- `phase3_arrivals_summary.json`
- `phase3_arrivals_by_minute.csv`
- `phase3_arrivals_by_uf.csv`

**Critério de decisão:** os timestamps somente serão usados como eixo temporal se apresentarem progressão compatível com a apuração. Uma concentração artificial posterior ou regeneração em massa impedirá seu uso como substituto de snapshots históricos.


---

## 2026-10-05 — E0016 — Resultado da Fase 3A: EA16 atual não preserva uma cronologia fina da chegada das urnas

**Evento:** análise dos artefatos produzidos por `analyze_phase3_arrivals.py`.

**Commit dos resultados:** `ef212f2`

**Cobertura:**
- 27 UFs brasileiras;
- **497.897** seções principais;
- **497.897/497.897 (100%)** com `da/ha`;
- exterior não incluído nesta execução; 497.897 + 1.351 seções do exterior = 499.248 seções nacionais finais.

**Distribuição temporal observada:**
- apenas **50 minutos distintos** para 497.897 seções;
- primeiro minuto: **04/10/2026 20:23**;
- último minuto: **05/10/2026 06:00**;
- maiores concentrações:
  - 00:52: **69.438** seções;
  - 22:59: **40.750**;
  - 23:01: **36.249**;
  - 22:23: **35.499**;
  - 22:44: **27.142**;
  - 23:00: **25.107**;
  - 23:11: **23.765**.

**Padrão por UF:** várias UFs têm praticamente todas as suas seções marcadas dentro de poucos segundos ou poucos minutos. Exemplos:
- AC: 2.270 seções entre 21:08:15 e 21:08:18;
- AP: 1.914 entre 21:04:25 e 21:04:27;
- BA: 35.476 entre 00:51:40 e 00:52:33;
- MG: 52.062 entre 00:51:54 e 00:52:52;
- SP: 103.656 entre 22:58:58 e 23:01:49;
- AM: 8.157 entre 06:00:31 e 06:00:37.

**Interpretação:** embora a documentação técnica do TSE diga que `da/ha` do EA16 informam a geração do arquivo auxiliar e podem ser usados para identificar a chegada dos arquivos de urna, **a versão atual recuperada após a eleição apresenta geração fortemente agrupada por UF**. Ela não será tratada como substituto de uma sequência histórica fina, seção por seção, da noite eleitoral.

**Decisão metodológica:** rejeitar, para esta investigação, o uso ingênuo do EA16 atual como relógio individual de chegada das urnas. EA16 continua útil para estrutura UF→município→zona→seção e localização dos artefatos EA18.

---

## 2026-10-05 — E0017 — Descoberta e confronto de duas capturas independentes da defasagem presidencial

**Evento:** busca por séries contemporâneas públicas capazes de preencher a lacuna temporal que o EA16 atual não preserva.

### Fonte independente A — ArvorCo/PNAD

O repositório público descreve um coletor que gravou em SQLite:
- corpo original dos arquivos;
- horário de geração no TSE;
- horário de totalização;
- horário da leitura;
- hash;
- toda requisição, inclusive respostas 304;
- tratamento de versões/regressões de CDN.

O arquivo derivado `analysis/apuracao_2026/dados/linha_do_tempo.json` registra:

**Travamento 1 relevante**
- 18:48:59 → 19:14:08;
- nacional: 235.931 → 323.539 seções;
- salto ao voltar: **87.608 seções**;
- **21.016.324 votos válidos** no lote.

**Travamento principal**
- 19:14:08 → 20:04:39;
- nacional: 323.539 → 424.153;
- duração: **50,52 min**;
- 101 leituras do arquivo nacional no intervalo;
- 100 respostas 304 e 1 nova versão;
- lote de destravamento: **100.614 seções** e **24.728.306 válidos**;
- composição do lote:
  - candidato 22: **45,0389%**;
  - candidato 13: **47,3057%**.

**Maior defasagem visível nacional × soma das UFs**
- 19:14;
- nacional visível: **235.931** seções;
- soma das UFs: **345.942**;
- diferença: **110.011 seções**, ou **22,04%** do total nacional.

A série minuto a minuto mostra que o nacional ficou atrás enquanto a soma das UFs continuava avançando. Após a atualização nacional de 19:14, a diferença volta a crescer e alcança cerca de 100 mil seções novamente.

### Fonte independente B — vitoropereira/eleicoes2026

O repositório preservou snapshots durante a noite e um arquivo específico `marcos/75pct/comparacao_fontes.json`.

Ele registra:
- nacional travado com conteúdo de 19:06:33: **323.539 seções**, 64,81%, **75.762.826 válidos**;
- soma das UFs no patamar 84,93%: **423.988 seções**, **100.448.357 válidos**;
- nacional destravado: **424.153 seções**, 84,96%, **100.491.132 válidos**.

Os landmarks nacionais de 323.539/75.762.826 e 424.153/100.491.132 coincidem exatamente com a captura ArvorCo.

### Achado que altera a formulação inicial

A captura ArvorCo registra também uma **lacuna geral de geração de arquivos de resultado EA20 (-u)**:

- início: **19:32:47**;
- fim: **20:01:55**;
- duração: **29,13 min**;
- nenhum EA20 novo de Presidente, Governador, Senado ou deputados, em nível nacional/UF/município/zona, possui horário de geração dentro dessa lacuna;
- o coletor realizou **82.573 requisições** nesse intervalo;
- 57.337 foram 304;
- respostas com corpo novo correspondiam a versões geradas antes da lacuna;
- arquivos de acompanhamento EA14/EA15 (`-ab`) tiveram uma rodada nova por volta de 19:45.

**Implicação:** a hipótese “Governador continuou normalmente durante toda a pausa presidencial” não deve ser usada como premissa indivisível. A janela precisa ser segmentada:

1. **18:48:59–19:14:08:** nacional de Presidente parado/defasado enquanto camadas inferiores avançam;
2. **19:14:08–19:32:47:** nacional de Presidente continua parado e a soma das UFs/monitoramento continua avançando;
3. **19:32:47–20:01:55:** pausa mais ampla na geração dos EA20 de todos os cargos/níveis, embora o acompanhamento `-ab` ainda seja atualizado;
4. **20:01:55–20:04:39:** geração dos resultados volta; logo depois o nacional presidencial publica o grande lote acumulado.

**Status:** a defasagem nacional presidencial é reproduzida por duas capturas independentes. A causa não é inferida por esse fato. A comparação Presidente × Governador deve agora ser feita separadamente por fase.

---

## 2026-10-05 — E0018 — Implementação da Fase 3B: timeline externa reproduzível

**Evento:** criação do `analyze_phase3b_external_timeline.py`.

**Commit:** `739dbd970fe0e9228aff0303aa20a2cbdf94c60d`

**Objetivo:** tornar os achados da E0017 reprodutíveis no nosso próprio pipeline.

**Procedimento:**
- baixar versões fixadas por commit das duas capturas independentes;
- preservar os arquivos brutos localmente com SHA-256;
- extrair a defasagem nacional × soma das UFs minuto a minuto;
- segmentar a janela nas quatro fases acima;
- medir o grande lote nacional de destravamento;
- fazer cross-check numérico entre os dois coletores.

**Saídas:**
- `phase3b_summary.json`
- `phase3b_lag_by_minute.csv`
- `phase3b_phases.csv`
- `phase3b_crosscheck.csv`

**Próxima ação:** executar a Fase 3B, versionar os quatro derivados e, em seguida, iniciar a comparação histórica específica Presidente × Governador na parte da janela anterior à pausa geral.


---

## 2026-10-05 — E0019 — Terceira captura contemporânea e preparação da Fase 3C

**Evento:** localização de uma terceira fonte pública independente com respostas brutas reais do TSE preservadas em ciclos durante a noite de 04/10/2026.

**Fonte:** repositório `madebysandro/apuracao-2026`, commit fixado `8917e32edb3aafd72664dc47a5ba53f576575197`.

O próprio repositório descreve `fixtures/tse-provisorio/` como uma sequência real de respostas brutas do TSE extraída de uma gravação contemporânea. Cada pasta representa um ciclo de captura e preserva, no mesmo instante aproximado, arquivos de:
- Presidente nacional;
- Presidente por UF;
- Governador;
- Senador;
- Deputado Federal;
- Deputado Estadual.

A gravação disponível usa o Pará para os cargos estaduais, o que permite um teste cruzado especialmente útil: comparar, no mesmo ciclo, a quantidade de seções presente em Presidente/PA e nos quatro cargos da eleição estadual 6259.

### Inspeção preliminar antes da automação

**Ciclo 21:36:05Z (~18:36 BRT):**
- Presidente BR: 159.242 seções;
- Presidente PA: 9.210;
- Governador PA: 9.247;
- Senador PA: 9.247;
- Deputado Federal PA: 9.247;
- Deputado Estadual PA: 9.247.

**Ciclo 21:39:46Z (~18:39 BRT):**
- Presidente BR: 182.745;
- Presidente PA: 9.764;
- Governador PA: 9.819;
- Senador PA: 9.819;
- Deputado Federal PA: 9.819;
- Deputado Estadual PA: 9.819.

**Ciclo 21:44:49Z (~18:44 BRT):**
- Presidente BR: 207.533;
- Presidente PA: 10.636;
- Governador PA: 10.570;
- Senador PA: 10.570;
- Deputado Federal PA: 10.570;
- Deputado Estadual PA: 10.570.

**Ciclo 23:17:25Z (~20:17 BRT):**
- Presidente BR: 449.547;
- Presidente PA: 18.258;
- Governador PA: 18.272;
- Deputado Federal PA: 18.272.

**Ciclo 00:01:02Z (~21:01 BRT):**
- Presidente BR: 490.242;
- Presidente PA: 20.149;
- Governador PA: 20.188;
- Senador PA: 20.188;
- Deputado Federal PA: 20.188;
- Deputado Estadual PA: 20.188.

### Observação preliminar

Nos ciclos preservados, os cargos estaduais 6259 do Pará aparecem com números de seções idênticos ou quase idênticos entre si. O Presidente/PA acompanha o mesmo conjunto com diferença de poucas dezenas de seções, compatível com a geração assíncrona dos arquivos dentro de um mesmo ciclo de captura.

Isso fornece evidência independente de que os cargos de uma mesma UF avançavam sobre praticamente o mesmo conjunto de seções, como esperado pelo fato de serem originados dos mesmos boletins.

### Limitação importante

A gravação tem ciclos em ~18:36–18:44 e volta apenas em ~20:16. Portanto ela **não cobre diretamente o trecho 18:49–19:32**, que é justamente a parte mais importante da defasagem presidencial antes da pausa geral.

Ela não resolve sozinha a pergunta central, mas:
1. valida o comportamento cruzado entre cargos na mesma UF;
2. fornece uma terceira captura independente;
3. reduz a plausibilidade de tratar cada cargo como se recebesse um conjunto de seções totalmente distinto;
4. orienta a próxima busca para snapshots preservados especificamente dentro de 18:49–19:32.

### Implementação

Criado `analyze_phase3c_cross_cargo.py`.

**Commit:** `9c133162acec5f73ef22438b298d4a016d51c378`

O script:
- baixa e preserva os arquivos brutos fixados pelo commit da fonte;
- calcula SHA-256;
- extrai `ts`, `st`, `hg`, `ht`, votos válidos e totais;
- compara Presidente/PA com Governador/Senador/Deputados no mesmo ciclo;
- mede a dispersão de seções entre os cargos estaduais;
- gera uma tabela de alinhamento temporal.

**Saídas previstas:**
- `phase3c_summary.json`
- `phase3c_cross_cargo_cycles.csv`
- `phase3c_pa_alignment.csv`

**Próxima ação:** executar a Fase 3C, versionar os derivados e depois ampliar a busca por capturas contemporâneas dentro de 18:49–19:32, priorizando snapshots de Governador/Presidente da mesma UF.


---

## 2026-10-05 — E0020 — Resultado da Fase 3C: alinhamento entre cargos estaduais e Presidente/PA

**Evento:** análise dos resultados versionados da Fase 3C.

**Commit dos resultados:** `1321549ea56c54e0e016f2245e3db3a800e2a9bc`

**Cobertura:** 6 ciclos contemporâneos preservados; 33 arquivos brutos carregados.

### Resultado

Nos ciclos com Governador/Senador/Deputados do Pará:
- a maior dispersão entre os cargos estaduais 6259 no mesmo ciclo foi de apenas **4 seções**;
- em vários ciclos, os quatro cargos estaduais tinham exatamente o mesmo `st`;
- a maior diferença absoluta entre Presidente/PA e a mediana dos cargos estaduais foi de **66 seções**.

Exemplos:
- ~18:36 BRT: Presidente/PA 9.210; quatro cargos estaduais 9.247;
- ~18:39 BRT: Presidente/PA 9.764; quatro cargos estaduais 9.819;
- ~18:44 BRT: Presidente/PA 10.636; quatro cargos estaduais 10.570;
- ~20:17 BRT: Presidente/PA 18.258; Governador e Dep. Federal 18.272;
- ~21:01 BRT: Presidente/PA 20.149; quatro cargos estaduais 20.188.

**Interpretação limitada:** a captura confirma empiricamente que os cargos estaduais de uma mesma UF avançam sobre praticamente o mesmo conjunto de seções, e que Presidente/UF acompanha esse conjunto com defasagens pequenas de publicação. Isso é compatível com a origem comum nos mesmos boletins/urnas.

**Limitação:** a fonte não cobre diretamente 18:49–19:32, portanto ainda não prova o comportamento de Governador durante toda a janela crítica.

---

## 2026-10-05 — E0021 — Hipótese: apenas os dois primeiros candidatos se moveriam nos grandes lotes

**Evento:** foi levantada a observação visual de que, quando a atualização nacional de Presidente retorna, os dois primeiros colocados mudariam enquanto os demais candidatos permaneceriam praticamente parados.

**Status inicial:** hipótese testável; não será aceita nem rejeitada por inspeção visual do gráfico.

### Razão metodológica

Em um gráfico com eixo vertical de dezenas de milhões de votos:
- um candidato que ganha 10–12 milhões de votos produz deslocamento visual muito grande;
- um candidato com 2–3% dos votos pode ganhar 500–700 mil votos no mesmo lote e parecer quase horizontal na mesma escala.

Portanto, o teste correto precisa comparar:
1. delta absoluto de votos;
2. participação do candidato no lote;
3. participação acumulada antes do lote;
4. mudança em pontos percentuais;
5. posteriormente, composição geográfica do lote.

### Inspeção preliminar dos dados nacionais preservados

No grande destravamento de **20:04:39**, o lote contém **24.728.306 votos válidos**.

Deltas observados:
- Flávio Bolsonaro: **+11.137.351**
- Lula: **+11.697.901**
- Augusto Cury: **+710.669**
- Renan Santos: **+553.291**
- Ronaldo Caiado: **+508.289**
- demais candidatos agrupados: **+120.805**

Logo, os candidatos fora do top 2 somaram **+1.893.054 votos** no lote, equivalentes a **7,655%** dos votos válidos adicionados. Nenhum desses grupos teve delta zero.

Comparação de participação acumulada antes do lote versus participação dentro do lote:
- Flávio: 49,585% → 45,039% no lote;
- Lula: 42,247% → 47,306%;
- Cury: 2,967% → 2,874%;
- Renan: 2,340% → 2,237%;
- Caiado: 2,343% → 2,055%;
- outros agrupados: 0,518% → 0,489%.

**Observação preliminar:** no grande lote nacional, os candidatos menores não ficaram parados em votos absolutos. O que ficou relativamente estável foi sua **participação percentual**, porque a participação deles no lote ficou próxima da participação acumulada anterior. A maior redistribuição relativa ocorreu entre os dois primeiros.

Isso pode explicar a percepção visual de que apenas os dois primeiros “mexeram”.

**Importante:** essa constatação não encerra a análise estatística. A composição geográfica dos lotes não é aleatória; portanto o próximo teste deve comparar as participações por UF/município/seção antes de concluir se a estabilidade percentual dos menores é comum ou incomum.

---

## 2026-10-05 — E0022 — Implementação da Fase 3D: movimento dos candidatos

**Evento:** criação do `analyze_phase3d_candidate_motion.py`.

**Commit:** `a596d55c79f4e2392af1366d6ac561066c089bf6`

**Objetivo:** testar formalmente a hipótese da E0021 nos dois grandes lotes presidenciais.

**Métricas produzidas por candidato/grupo:**
- votos antes e depois;
- delta absoluto;
- crescimento relativo;
- participação acumulada antes do lote;
- participação dentro do lote;
- diferença em pontos percentuais;
- valor descritivo esperado caso mantivesse a participação anterior;
- razão observado/esperado.

**Regra:** a comparação com a participação anterior é apenas descritiva. Não será transformada em p-valor multinomial, pois a ordem de chegada das seções não é aleatória.

**Saídas previstas:**
- `phase3d_candidate_batches.csv`
- `phase3d_candidate_motion_summary.json`

**Próxima ação:** executar a Fase 3D, versionar os resultados e então partir para a análise condicionada por geografia, que é o teste estatístico relevante.


---

## 2026-10-05 — E0023 — Resultado da Fase 3D: candidatos menores não ficaram parados

**Evento:** análise dos resultados versionados da Fase 3D.

**Commit dos resultados:** `1c70672`

### Catch-up 1 — 19:14:08

Lote:
- **87.608 seções**
- **21.016.324 votos válidos**

Votos adicionados:
- Flávio Bolsonaro: **+10.082.597**
- Lula: **+9.216.075**
- Augusto Cury: **+629.674**
- Renan Santos: **+503.159**
- Ronaldo Caiado: **+472.374**
- demais agrupados: **+112.445**

Candidatos fora do top 2:
- total: **+1.717.652 votos**
- participação no lote: **8,173%**
- grupos com delta zero: **0**

Mudança de participação no lote versus acumulado anterior:
- Cury: **+0,040 pp**
- Renan: **+0,075 pp**
- Caiado: **−0,132 pp**
- outros: **+0,023 pp**
- Flávio: **−2,228 pp**
- Lula: **+2,221 pp**

### Catch-up 2 — 20:04:39

Lote:
- **100.614 seções**
- **24.728.306 votos válidos**

Votos adicionados:
- Flávio Bolsonaro: **+11.137.351**
- Lula: **+11.697.901**
- Augusto Cury: **+710.669**
- Renan Santos: **+553.291**
- Ronaldo Caiado: **+508.289**
- demais agrupados: **+120.805**

Candidatos fora do top 2:
- total: **+1.893.054 votos**
- participação no lote: **7,655%**
- grupos com delta zero: **0**

Mudança de participação no lote versus acumulado anterior:
- Cury: **−0,093 pp**
- Renan: **−0,102 pp**
- Caiado: **−0,287 pp**
- outros: **−0,030 pp**
- Flávio: **−4,546 pp**
- Lula: **+5,058 pp**

### Conclusão limitada

A formulação “os outros candidatos ficaram parados” é rejeitada em termos de **votos absolutos**: todos os grupos cresceram materialmente e os candidatos fora do top 2 somaram mais de 1,7 milhão e 1,89 milhão de votos nos dois catch-ups.

A observação visual corresponde melhor a outra propriedade:
- a **participação percentual** dos candidatos menores mudou pouco;
- a maior redistribuição percentual ocorreu entre os dois primeiros.

Isso ainda pode ser estatisticamente interessante, mas exige comparação com o comportamento normal dos demais lotes e, idealmente, controle geográfico.

---

## 2026-10-05 — E0024 — Implementação da Fase 3E: benchmark empírico dos lotes

**Evento:** criação do `analyze_phase3e_batch_benchmark.py`.

**Commit:** `3c92531a6172da38d8fa6096b0c15fd3ae1f2fd5`

**Pergunta:** a estabilidade percentual relativa dos candidatos menores nos dois grandes catch-ups é realmente incomum em comparação com os demais lotes da mesma noite?

**Método:**
- usar todas as versões nacionais genuínas e não regressivas preservadas na mesma série histórica;
- para cada lote, calcular:
  - RMS da mudança em pontos percentuais dos candidatos fora do top 2;
  - maior mudança absoluta entre esses candidatos;
  - RMS da mudança dos dois primeiros;
  - razão entre movimento top 2 e movimento dos demais;
- comparar os dois catch-ups contra:
  - todos os lotes;
  - apenas lotes grandes, definidos como >= 1 milhão de votos válidos adicionados.

**Vantagem metodológica:** o controle é empírico, baseado na própria noite eleitoral. Não supõe que as seções tenham chegado em ordem aleatória.

**Limitação:** mesmo esse benchmark ainda é nacional. O passo posterior continua sendo condicionamento por UF/município/seção quando houver snapshots históricos suficientes.

**Saídas previstas:**
- `phase3e_batch_benchmark.csv`
- `phase3e_target_percentiles.csv`
- `phase3e_summary.json`

**Próxima ação:** executar a Fase 3E e versionar os resultados.


---

## 2026-10-05 — E0025 — Falha de execução da Fase 3E e correção

**Evento:** primeira execução de `analyze_phase3e_batch_benchmark.py` falhou antes de gerar artefatos derivados.

**Erro observado:**

`TypeError: int() argument must be a string, a bytes-like object or a real number, not 'NoneType'`

A exceção ocorreu ao tentar converter `d_vv` para inteiro.

### Causa

A série histórica contém linhas que não representam um lote comparável e, por isso, não possuem delta calculado em campos como `d_vv`, `d_st` e deltas por candidato. A primeira versão histórica é um exemplo esperado dessa situação.

O código da primeira versão da Fase 3E assumia incorretamente que toda linha não regressiva teria deltas completos.

### Impacto

- nenhum relatório da Fase 3E foi produzido;
- nenhum resultado estatístico foi calculado;
- portanto não há conclusão analítica a revisar;
- o repositório local permaneceu sem arquivos derivados novos, razão pela qual o Git corretamente informou `nothing to commit`.

### Correção

O script passou a:
- aceitar campos ausentes/nulos;
- ignorar linhas sem delta completo em vez de falhar;
- ignorar separadamente versões marcadas como regressivas;
- registrar no resumo quantas linhas históricas foram descartadas por cada motivo.

**Commit da correção:** `8ce589d0b5d1894d85a8e502c3295feb3a997579`

**Próxima ação:** atualizar o branch local, executar novamente a Fase 3E, versionar os três artefatos derivados e só então interpretar os percentis empíricos.


---

## 2026-10-05 — E0026 — Segunda falha da Fase 3E: CSV parcial e correção atômica

**Evento:** segunda execução da Fase 3E avançou além do primeiro erro, mas falhou ao escrever o arquivo de percentis.

**Erro observado:**

`ValueError: dict contains fields not in fieldnames: 'minutes_since_previous'`

### Causa

Cada linha de `targets` é construída a partir da linha completa do lote e, portanto, contém o campo `minutes_since_previous`. A lista de colunas usada por `csv.DictWriter` para `phase3e_target_percentiles.csv` não incluía esse campo.

### Impacto

Antes da exceção:
- `phase3e_batch_benchmark.csv` foi gerado;
- `phase3e_target_percentiles.csv` foi criado parcialmente;
- `phase3e_summary.json` **não foi gerado**.

Esses dois CSVs parciais/completos foram posteriormente versionados no commit local:

`76e53d60c2b57de897f72b5749a6a0f381f8867e`

Portanto, esse commit deve ser tratado como **execução incompleta da Fase 3E**, e não como resultado final.

### Correção

O script foi alterado para:
- incluir `minutes_since_previous` nas colunas do CSV de alvos;
- escrever todos os CSVs de forma **atômica** usando arquivo `.part` + `os.replace`;
- remover o arquivo temporário em caso de falha.

Isso evita que futuras exceções deixem relatórios parcialmente escritos que possam ser confundidos com resultados completos.

**Commit da correção:** `13fe6fb58df1acf110dd8fb990445b3f47e644dd`

### Observação preliminar a partir do CSV de benchmark que foi escrito integralmente

Embora a execução tenha sido incompleta, o `phase3e_batch_benchmark.csv` contém a população de referência e permite uma leitura preliminar:

- catch-up 1:
  - RMS dos candidatos menores: **0,0792 pp**;
  - razão movimento top2 / menores: **28,07**;
- catch-up 2:
  - RMS dos candidatos menores: **0,1601 pp**;
  - razão movimento top2 / menores: **30,04**.

Esses números ainda não serão promovidos a conclusão final até a execução completa gerar o resumo e os percentis de forma reproduzível.

**Próxima ação:** atualizar o branch local, executar novamente a Fase 3E, verificar que os três artefatos são gerados e versioná-los.


---

## 2026-10-05 — E0027 — Resultado completo da Fase 3E

**Evento:** execução bem-sucedida de `analyze_phase3e_batch_benchmark.py`.

**Commit dos resultados:** `03546c1`

**População de referência:**
- linhas históricas: **331**
- linhas regressivas ignoradas: **133**
- linhas sem delta completo: **6**
- lotes genuínos comparáveis: **192**
- lotes grandes (>= 1.000.000 válidos adicionados): **16**

### Catch-up 1 — 19:14:08

- RMS da mudança percentual dos candidatos fora do top 2: **0,0792 pp**
- percentil entre todos os lotes: **6,25**
- percentil entre lotes grandes: **62,5**
- RMS dos dois primeiros: **2,2241 pp**
- razão movimento top2 / movimento menores: **28,07**
- percentil dessa razão entre lotes grandes: **62,5**

**Leitura:** entre lotes grandes, os candidatos menores não foram excepcionalmente estáveis. O catch-up 1 fica perto do meio-superior da distribuição de movimento dos menores.

### Catch-up 2 — 20:04:39

- RMS da mudança percentual dos candidatos fora do top 2: **0,1601 pp**
- percentil entre todos os lotes: **18,23**
- percentil entre lotes grandes: **93,75**
- RMS dos dois primeiros: **4,8090 pp**
- razão movimento top2 / movimento menores: **30,04**
- percentil dessa razão entre lotes grandes: **87,5**

**Leitura:** entre os 16 lotes grandes, o segundo catch-up está no extremo alto do **movimento dos candidatos menores**, não no extremo baixo. Portanto a hipótese de que os menores estariam estatisticamente “congelados” não é sustentada por este benchmark.

O que aparece como incomum é outra característica: a redistribuição entre os dois primeiros é muito maior que a dos demais. A razão top2/menores do catch-up 2 está no percentil **87,5** entre lotes grandes — alta, mas não única.

### Conclusão limitada

A observação visual “somente os dois primeiros mudaram” deve ser reformulada:

- em votos absolutos, todos os candidatos/grupos se moveram;
- em participação percentual, os menores se moveram pouco em termos visuais;
- porém, quando comparados apenas a lotes grandes, o catch-up 2 mostra **mais** movimento percentual dos menores que 15 dos 16 lotes, não menos;
- a característica mais marcante é a grande troca relativa entre os dois primeiros.

Este resultado não prova normalidade nem fraude. Ele rejeita uma formulação específica da anomalia e desloca o foco para a magnitude e a origem geográfica da redistribuição top 2.

---

## 2026-10-05 — E0028 — Próximo controle: janelas agregadas de tamanho comparável

**Problema metodológico identificado:** comparar um catch-up de 21–25 milhões de votos com lotes individuais menores pode ser enviesado, porque agregações grandes tendem a suavizar oscilações percentuais.

**Teste definido:** construir janelas móveis de lotes normais consecutivos, sem incluir os dois catch-ups, até atingir entre **80% e 120%** do tamanho em votos válidos de cada catch-up.

Para cada janela de tamanho comparável serão calculados:
- RMS dos candidatos menores;
- RMS do top 2;
- razão top2/menores;
- percentil descritivo dos catch-ups dentro dessas janelas.

**Importante:** as janelas se sobrepõem, portanto os percentis serão tratados como benchmark empírico descritivo, não como p-valores ou amostras independentes.


---

## 2026-10-05 — E0029 — Implementação da Fase 3F: janelas agregadas comparáveis

**Evento:** criação do `analyze_phase3f_matched_windows.py`.

**Commit:** `e3518b48f47d97a99c0612781a496acb87416693`

**Objetivo:** controlar o efeito do tamanho excepcional dos dois catch-ups.

**Método:**
- construir janelas de lotes normais consecutivos;
- excluir os dois catch-ups das janelas de referência;
- acumular entre 80% e 120% dos votos válidos do catch-up alvo;
- encerrar uma janela se houver lacuna interna superior a 15 minutos;
- comparar RMS dos menores, RMS do top 2 e razão top2/menores.

**Importante:** as janelas podem se sobrepor. Portanto os percentis resultantes serão usados apenas como benchmark empírico descritivo, não como p-valores.

**Próxima ação:** executar a Fase 3F, versionar os três artefatos derivados e então decidir se o comportamento top 2 continua incomum mesmo após controlar aproximadamente o tamanho da janela.


---

## 2026-10-05 — E0030 — Resultado da Fase 3F: janelas de tamanho comparável

**Evento:** análise dos resultados versionados da Fase 3F.

**Commit dos resultados:** `5b09203`

### Catch-up 1 — 19:14:08

Comparado com **36 janelas agregadas** contendo entre 80% e 120% do mesmo volume de votos válidos:

- movimento RMS dos candidatos fora do top 2: percentil **30,6**;
- movimento RMS dos dois primeiros: percentil **100,0**;
- razão movimento top2 / menores: percentil **91,7**.

### Catch-up 2 — 20:04:39

Comparado com **35 janelas agregadas** de tamanho semelhante:

- movimento RMS dos candidatos fora do top 2: percentil **100,0**;
- movimento RMS dos dois primeiros: percentil **100,0**;
- razão movimento top2 / menores: percentil **91,4**.

### Conclusão limitada

A hipótese “os candidatos menores ficaram congelados” continua rejeitada.

Por outro lado, nos dois catch-ups o movimento percentual conjunto dos dois primeiros foi maior do que em **todas as janelas de referência de tamanho comparável** construídas por este método.

Isso é uma característica empírica relevante dos dois lotes e deve ser preservada como alvo de investigação, mas **não é um p-valor nem prova de manipulação**, porque:
- as janelas se sobrepõem;
- a composição geográfica dos lotes não foi controlada;
- seções não chegam como uma amostra aleatória nacional.

**Próxima ação analítica:** condicionar a redistribuição top 2 à geografia efetiva das UFs/municípios/seções que compõem os lotes.

---

## 2026-10-05 — E0031 — Hipótese futura: coerência eleitoral entre Presidente, Governador e Senado

**Evento:** foi proposta a investigação, em todas as UFs, da aparente combinação entre votos em candidaturas estaduais identificadas como de direita e voto presidencial em Lula.

### Correção metodológica necessária

Não é possível inferir diretamente do resultado agregado que **a mesma pessoa** votou em determinado Governador, determinado Senador e em Lula.

O voto é secreto e o RDV embaralha os votos **cargo a cargo**, justamente para impedir associação entre as escolhas de uma mesma eleitora ou eleitor. Assim:
- BU/RDV permitem recontar cada cargo por seção;
- não permitem reconstruir o “ticket” individual de uma pessoa através dos cargos.

Portanto, qualquer afirmação do tipo “X pessoas votaram em Governador A + Senador B + Presidente C” seria inválida sem uma fonte individual independente.

### O que é possível testar rigorosamente

A investigação será feita em camadas:

1. **Presidente × Governador por seção**
   - comparar participação de Lula e dos candidatos/blocos a Governador;
   - medir correlação, resíduos e padrões espaciais;
   - comparar municípios e zonas semelhantes.

2. **Limites matemáticos de voto cruzado**
   - para uma seção com comparecimento `N`, votos `G` em um bloco/candidato a Governador e `L` em Lula:
     - mínimo possível de eleitores que votaram em ambos: `max(0, G + L - N)`;
     - máximo possível: `min(G, L)`.
   - esses limites não identificam pessoas, mas podem demonstrar quando algum nível mínimo de cruzamento é matematicamente inevitável.

3. **Benchmark histórico**
   - comparar padrões equivalentes com eleições anteriores quando dados compatíveis estiverem disponíveis;
   - isso permite distinguir split-ticket rotineiro de um padrão realmente incomum.

4. **Senado tratado separadamente**
   - em 2026 cada eleitor pode votar em **dois candidatos ao Senado**;
   - portanto a aritmética Presidente × Senado não pode reutilizar diretamente o modelo 1-voto-por-cargo do Governador.

5. **Classificação política auditável**
   - “direita”, “esquerda” ou “alinhado a candidato presidencial” não será inferido automaticamente pelo script;
   - será necessário um mapeamento explícito por UF/candidato, com fonte e justificativa, porque alianças estaduais podem atravessar blocos nacionais.

### Status

Hipótese registrada para uma fase posterior, em todas as UFs.

**Prioridade:** começar por Presidente × Governador, onde há um voto por cargo e os limites matemáticos são mais limpos. Depois incorporar Senado com modelo específico para duas escolhas por eleitor.


---

## 2026-10-05 — E0032 — Correção de enquadramento: hipótese de alinhamento ideológico será testada, não descartada

**Evento:** correção do enquadramento metodológico da E0031.

A investigação adotará explicitamente como **hipótese de trabalho testável**:

> **H0-alinhamento:** quem vota em uma candidatura classificada como de direita para Governador/Senado tende a votar também em uma candidatura presidencial classificada como de direita.

Essa hipótese não será tratada previamente como verdadeira nem falsa. O objetivo é **medir o desvio observado**, quantificá-lo por seção/município/UF e avaliar se o padrão é coerente, raro ou extremo em comparação com referências internas e históricas.

### Governador × Presidente — métricas principais

Para cada seção:
- `N`: comparecimento;
- `G_R`: votos válidos em candidato(s) a Governador classificados como direita;
- `P_R`: votos válidos em candidato(s) presidenciais classificados como direita;
- `L`: votos em Lula.

Serão calculados:

1. **Déficit mínimo de alinhamento direita→direita**
   - `max(0, G_R - P_R)`
   - interpretação: quantidade mínima de eleitores de Governador-direita que, necessariamente, não podem estar contidos no conjunto Presidente-direita.

2. **Taxa mínima de violação da hipótese de alinhamento**
   - `max(0, G_R - P_R) / G_R`, quando `G_R > 0`.

3. **Sobreposição mínima Governador-direita × Lula**
   - `max(0, G_R + L - N)`
   - esse é um limite matemático inferior: se positivo, existe necessariamente pelo menos essa quantidade de votos cruzados, independentemente de qualquer reconstrução individual.

4. **Sobreposição máxima possível**
   - `min(G_R, L)`.

5. **Intervalo possível de voto cruzado**
   - `[max(0, G_R + L - N), min(G_R, L)]`.

6. **Resíduo de alinhamento por seção**
   - comparar participação de Presidente-direita contra participação de Governador-direita, controlando comparecimento, brancos/nulos, município e zona.

### Senado × Presidente

Como cada eleitor pode registrar dois votos para Senado, a análise será específica.

Se `S_R` for o total de votos dados a candidatos classificados como direita ao Senado em uma seção com `N` eleitores votantes:

- número mínimo de eleitores que deram **ao menos um** voto de Senado à direita:
  `ceil(S_R / 2)`;
- número máximo:
  `min(N, S_R)`.

Assim, um limite inferior conservador para eleitores que necessariamente combinaram ao menos um voto de Senado-direita com Lula é:

`max(0, ceil(S_R/2) + L - N)`.

Também serão feitos testes candidato-a-candidato para Senado, onde cada candidatura individual pode receber no máximo um voto de cada eleitor.

### Classificação ideológica

A classificação "direita / esquerda / centro / não classificado" será uma **entrada explícita e versionada do modelo**, não inferida silenciosamente pelo código.

Para cada candidatura serão preservados:
- UF;
- cargo;
- candidato;
- partido/federação/coligação;
- classe adotada;
- fonte/justificativa;
- eventual ambiguidade.

Também será possível rodar cenários alternativos de classificação para medir sensibilidade.

### Objetivo

Produzir, para as 27 UFs:
- distribuição do desvio por seção;
- municípios e zonas com maior/menor alinhamento;
- limites mínimos de voto cruzado;
- comparação entre estados;
- comparação com eleições anteriores quando possível;
- identificação de padrões extremos que mereçam inspeção de BU/seção.

**Importante:** esta etapa não presume que o desvio seja normal, anormal, legítimo ou ilegítimo. Ela mede o fenômeno a partir da hipótese de alinhamento definida acima.


---

## 2026-10-05 — E0033 — Hipótese externa: vantagem de Lula/PT x atraso por UF e swing após retomada

**Evento:** incorporação de uma observação externa como questionamento formal da investigação.

**Hipótese levantada:**

> Os estados em que Lula/PT tinha vantagem teriam sido justamente os que apresentaram maior atraso/pausa de atualização; quando esses dados voltaram, Lula teria ganho participação relativa enquanto Flávio/oposição teria caído.

**Status:** hipótese exploratória, a ser medida. Não é tratada como fato nem descartada previamente.

### Operacionalização

Para evitar julgamento visual ou seleção manual de estados, a hipótese será dividida em duas perguntas independentes:

1. **Vantagem prévia × atraso**
   - classificar cada UF pelo líder presidencial no snapshot contemporâneo de ~19:06;
   - medir minutos de sobreposição entre eventos de travamento da UF e as janelas críticas:
     - W1: 18:48:59–19:14:08;
     - W2: 19:14:08–19:32:47;
   - comparar distribuição de atrasos entre UFs Lula-led e Flávio-led;
   - calcular correlação de Spearman entre margem Lula−Flávio e atraso.

2. **Atraso × swing após/ao longo da retomada**
   - calcular, por UF:
     `swing = Δ[(Lula %) − (Flávio %)]`
   - medir esse swing em:
     - 18:32→19:06;
     - 19:06→19:32;
     - 19:32→20:47;
   - testar se UFs mais atrasadas apresentam swing sistematicamente mais favorável a Lula.

### Fontes

- `ArvorCo/PNAD`: eventos de travamento por UF detectados na série histórica;
- `vitoropereira/eleicoes2026`: snapshots contemporâneos por UF em ~18:32, 19:06, 19:32 e 20:47.

### Inspeção exploratória antes da automação

Uma leitura preliminar das duas fontes mostrou:

- na W1, quase nenhuma UF possui evento de travamento detectado pela fonte; apenas SP tem pequena sobreposição (~0,32 min);
- na W2, as medianas preliminares de atraso detectado foram aproximadamente:
  - UFs com Lula na frente: **9,85 min**;
  - UFs com Flávio na frente: **10,32 min**;
- entre as maiores sobreposições W2 aparecem AM, AC, SP, PR e RS, todos com Flávio à frente no snapshot-base;
- o swing mediano 19:06→19:32 foi aproximadamente igual nos dois grupos (~+0,3 pp para Lula relativo a Flávio);
- no trecho 19:32→20:47, a mediana preliminar foi mais favorável a Lula nas UFs em que ele já liderava.

**Interpretação:** essa inspeção preliminar não confirma a forma forte da hipótese "estados pró-Lula atrasaram mais". Porém isso ainda precisa ser reproduzido pelo script e documentado em artefatos derivados antes de qualquer conclusão.

### Implementação

Criado `analyze_phase3g_uf_delay_bias.py`.

**Commit:** `e2b97f294bd6e28591fd9ef6e5cc791c78e36282`

**Saídas previstas:**
- `phase3g_uf_delay_bias.csv`
- `phase3g_summary.json`

**Próxima ação:** executar a Fase 3G, versionar os resultados e só então aceitar, rejeitar ou reformular essa hipótese.


---

## 2026-10-05 — E0034 — Falha da Fase 3G por commit-fonte incompleto e correção

**Evento:** primeira execução de `analyze_phase3g_uf_delay_bias.py` falhou antes de gerar relatórios.

**Erro observado:** `HTTP Error 404: Not Found`.

### Causa

A Fase 3G havia fixado a fonte `vitoropereira/eleicoes2026` no commit:

`3f4d7442dd601eb1b11afb8e9510d1373c495e7c`

Esse commit contém os snapshots de:
- 18:32;
- 19:06;
- 19:32;

mas **ainda não contém** o snapshot de 20:47 usado pelo script.

A ausência do arquivo no commit fixado provocou o 404. Não houve falha estatística nem problema nos dados locais.

### Verificação da correção

Foi localizado e verificado o commit:

`10c03a7d52058a2650836953b612939ba02a3235`

Ele contém os quatro snapshots necessários:
- `snapshots/2026-10-04_1832_36.6pct/dados.json`
- `snapshots/2026-10-04_1906_64.8pct/dados.json`
- `snapshots/2026-10-04_1932_84.9pct/dados.json`
- `snapshots/2026-10-04_2047_93.2pct/dados.json`

### Impacto

- nenhum relatório da Fase 3G foi produzido;
- `git status` permaneceu limpo;
- não há resultado analítico a revisar.

### Correção

`analyze_phase3g_uf_delay_bias.py` passou a fixar a fonte no commit `10c03a7d...`.

**Commit da correção:** `71654ebd7e237e23e2f77158420a93cc5717d2b6`

**Próxima ação:** atualizar o branch local e executar novamente a Fase 3G.


---

## 2026-10-05 — E0035 — Resultado da Fase 3G: travamentos por UF não se concentram nas UFs pró-Lula

**Evento:** análise dos resultados versionados da Fase 3G.

**Commit dos resultados:** `1bc302c0b3507ce103e886c29355f0133ba7a727`

**Cobertura:** 27 UFs.

### Resultado principal

Classificação no snapshot de ~19:06:
- UFs com Lula na frente: **11**
- UFs com Flávio na frente: **16**

Na janela W2 (19:14:08–19:32:47), mediana de minutos de travamento detectado por UF:
- Lula-led: **9,85 min**
- Flávio-led: **10,32 min**

Correlação de Spearman entre margem Lula−Flávio e atraso W2:
- **−0,478**

Ou seja: quanto maior a margem de Lula, menor tendeu a ser o atraso detectado por esta métrica.

Correlação entre atraso W2 e swing Lula−Flávio entre 19:06→19:32:
- **−0,041**

Isso é praticamente ausência de associação monotônica.

Correlação entre atraso W2 e swing 19:32→20:47:
- **−0,278**

Também não aponta para maior atraso associado a swing posterior favorável a Lula.

### UFs com maiores atrasos W2 detectados

Entre os maiores valores aparecem:
- AM: **16,20 min** — Flávio liderava
- AC: **13,40 min** — Flávio liderava
- SP: **12,25 min** — Flávio liderava
- PR: **11,05 min** — Flávio liderava
- RS: **10,97 min** — Flávio liderava

### Conclusão limitada

A forma forte da hipótese:

> “os estados onde Lula/PT tinha vantagem foram justamente os que atrasaram mais tecnicamente”

**não é sustentada** por esta definição de atraso baseada nos eventos `travamentos.ufs`.

Isso não encerra a hipótese mais ampla de **apuração tardia por composição geográfica**, porque um estado pode estar muito menos avançado na contagem sem apresentar mais eventos de congelamento técnico.

**Próxima pergunta:** UFs Lula-led estavam proporcionalmente menos apuradas nos snapshots contemporâneos?

---

## 2026-10-05 — E0036 — Implementação da Fase 3H: apuração tardia por composição geográfica

**Evento:** criação do `analyze_phase3h_late_counting.py`.

**Commit:** `37b401af695efb7d8776b0908ca7c0a3ae1cd046`

**Objetivo:** testar uma formulação diferente da hipótese externa:

> mesmo sem maior número/duração de freezes técnicos, UFs onde Lula liderava estavam menos avançadas na apuração e, portanto, tinham proporcionalmente mais resultado para entrar depois?

**Métricas:**
- percentual apurado por UF em 18:32, 19:06, 19:32 e 20:47;
- percentual ainda não apurado;
- comparação Lula-led × Flávio-led;
- correlação de Spearman entre margem Lula−Flávio e percentual apurado;
- progresso entre snapshots;
- swing Lula−Flávio posterior;
- proxy de escala: eleitorado total × fração ainda não apurada.

**Cuidado:** esse proxy não representa votos faltantes; ele serve apenas para comparar escala potencial entre grupos.

**Inspeção exploratória antes da automação:**
- mediana de apuração às 19:06:
  - Lula-led: **65,95%**
  - Flávio-led: **91,50%**
- mediana às 19:32:
  - Lula-led: **83,20%**
  - Flávio-led: **97,74%**
- Spearman margem Lula × percentual apurado às 19:06: aproximadamente **−0,629**
- Spearman margem Lula × percentual apurado às 19:32: aproximadamente **−0,626**

Isso sugere que a hipótese de “apuração mais tardia” pode aparecer na **proporção ainda não contada**, embora não apareça como maior frequência de travamentos técnicos.

**Próxima ação:** executar a Fase 3H, versionar os artefatos e então separar claramente:
1. atraso técnico;
2. apuração estruturalmente mais tardia;
3. swing político do resultado.


---

## 2026-10-05 — E0037 — Resultado da Fase 3H: UFs pró-Lula estavam menos avançadas proporcionalmente

**Evento:** análise dos resultados versionados da Fase 3H.

**Commit dos resultados:** `61499e5`

### Resultado principal

No snapshot de ~19:06:
- UFs com Lula na frente: mediana de **65,95%** apurado;
- UFs com Flávio na frente: mediana de **91,50%** apurado.

No snapshot de ~19:32:
- Lula-led: mediana de **83,20%**;
- Flávio-led: mediana de **97,74%**.

Correlação de Spearman entre margem Lula−Flávio e percentual apurado:
- 19:06: **−0,629**
- 19:32: **−0,626**

Isso indica associação clara entre maior vantagem de Lula e menor avanço proporcional da apuração naquele momento.

### Escala absoluta

Apesar dessa diferença proporcional, o grupo Flávio-led possui eleitorado total muito maior.

Proxy de eleitorado ainda associado à fração não apurada em 19:06:
- Lula-led: **~19,83 milhões**
- Flávio-led: **~25,70 milhões**

Em 19:32:
- Lula-led: **~12,25 milhões**
- Flávio-led: **~11,62 milhões**

Portanto:
- em termos proporcionais, as UFs pró-Lula estavam muito mais atrasadas;
- em termos absolutos de escala potencial, às 19:06 ainda havia mais eleitorado associado à parte não apurada nas UFs pró-Flávio;
- por volta de 19:32 os dois blocos ficam em escala absoluta semelhante, com pequena vantagem do grupo Lula-led.

### Relação com swing posterior

Spearman entre percentual não apurado em 19:06 e swing Lula−Flávio até 19:32:
- **+0,168**

Spearman entre percentual não apurado em 19:32 e swing até 20:47:
- **+0,358**

A associação posterior é positiva, mas moderada.

### Conclusão limitada

A hipótese de “apuração tardia” é sustentada **na dimensão proporcional por UF**: estados pró-Lula estavam significativamente menos avançados.

Isso não equivale a afirmar que esses estados tiveram mais travamentos técnicos; a Fase 3G mostrou o contrário para essa métrica específica.

Também não basta, por si só, para explicar toda a redistribuição nacional entre os dois primeiros. É necessário decompor o saldo posterior por UF e comparar:
- o que já era esperado pela composição geográfica observada;
- o que veio além dessa expectativa dentro das próprias UFs.

---

## 2026-10-05 — E0038 — Implementação da Fase 3I: decomposição geográfica do movimento até o final

**Evento:** criação do `analyze_phase3i_geographic_decomposition.py`.

**Commit:** `21750fbe3ccbcfe510cf7b9e134c999aa8e86025`

**Objetivo:** medir, por UF, de onde veio a redução posterior da margem Flávio−Lula.

### Método

Para cada snapshot de 19:06, 19:32 e 20:47:

1. usar a margem histórica aproximada por UF armazenada na fonte;
2. usar o resultado final oficial do TSE por UF;
3. calcular o movimento líquido real restante:
   - `margem_final_UF - margem_snapshot_UF`;
4. comparar com a projeção `rem_net` da própria fonte, que assume que o restante da UF manteria a composição observada naquele instante;
5. separar contribuições de UFs Lula-led e Flávio-led;
6. reconciliar a soma das margens finais das 28 abrangências com o nacional oficial.

### Limitação da margem histórica por UF

A fonte guarda `marg` arredondada em milhares de votos:
`round((Flávio - Lula)/1000)`.

Portanto a decomposição histórica por UF tem erro de arredondamento de aproximadamente ±500 votos por UF. A margem nacional histórica é exata.

### Pergunta central

Quanto do movimento posterior a favor de Lula já era previsível apenas pela geografia que faltava contar, mantendo os percentuais então observados dentro de cada UF?

E quanto do movimento veio de mudança adicional da composição do voto tardio **dentro das próprias UFs**?

**Próxima ação:** executar a Fase 3I, versionar os três artefatos derivados e analisar a decomposição.
