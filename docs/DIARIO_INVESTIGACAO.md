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


---

## 2026-10-05 — E0039 — Resultado da Fase 3I: geografia explica parte, mas não toda, da recuperação de Lula

**Evento:** análise dos resultados versionados da Fase 3I.

**Commit dos resultados:** `65f3f9c`

### Fechamento final

Resultado oficial final:
- Flávio: **56.104.503**
- Lula: **53.879.538**
- margem Flávio−Lula: **+2.224.965**

A soma das margens das 28 abrangências fecha exatamente com o nacional:
- diferença: **0**

### Snapshot de 19:06

Margem nacional naquele instante:
- **+5.559.042** para Flávio.

Movimento líquido real até o resultado final:
- **−3.334.077** na margem Flávio−Lula, portanto movimento líquido a favor de Lula.

Se o restante de cada UF mantivesse exatamente a composição que aquela UF já apresentava às 19:06, a projeção era:
- **−1.333.000**

Isso corresponde a aproximadamente **40,0%** do movimento líquido realmente observado até o final.

Diferença entre movimento real e projeção de composição constante:
- **−2.001.077** adicionais a favor de Lula.

Decomposição por grupo:
- UFs Lula-led:
  - movimento real restante: **−5.251.603**
  - projetado: **−4.120.000**
- UFs Flávio-led:
  - movimento real restante: **+1.976.568**
  - projetado: **+2.787.000**

Portanto o desvio adicional em favor de Lula aparece nos dois lados:
- estados já favoráveis a Lula entregaram saldo ainda mais pró-Lula do que sua composição observada previa;
- estados favoráveis a Flávio entregaram saldo menos pró-Flávio do que sua composição observada previa.

Maiores contribuições líquidas restantes pró-Lula desde 19:06:
- BA: aproximadamente **−1.754.186**
- CE: **−1.025.413**
- PE: **−898.928**
- MA: **−608.261**
- PI: **−305.682**

Entre UFs que naquele momento eram Flávio-led:
- AM terminou contribuindo aproximadamente **−131.232** no restante, invertendo o sinal da projeção inicial.

### Snapshot de 19:32

Margem nacional:
- **+5.005.947**

Movimento real restante até o final:
- **−2.780.982**

Projeção mantendo a composição então observada em cada UF:
- **−1.510.000**

Parcela do movimento explicada por essa projeção:
- **54,3%**

Componente adicional:
- aproximadamente **−1.270.982** a favor de Lula além da projeção de composição constante.

### Snapshot de 20:47

Margem nacional:
- **+3.912.599**

Movimento real restante:
- **−1.687.634**

Projeção mantendo composição por UF:
- **−932.000**

Parcela explicada:
- **55,2%**

Componente adicional:
- aproximadamente **−755.634** a favor de Lula.

### Conclusão limitada

A composição geográfica entre UFs explica corretamente **o sentido** de uma parte importante da recuperação de Lula, mas não explica toda a magnitude.

A partir de 19:06, somente cerca de **40%** do movimento líquido até o final seria obtido se cada UF simplesmente mantivesse a mesma proporção Lula/Flávio que já exibia naquele momento.

O restante indica que o voto que entrou mais tarde **dentro das próprias UFs** foi, no agregado, mais favorável a Lula do que o voto que já havia sido contado.

Isso não identifica causa. A próxima pergunta é geográfica e intraestadual:
> zonas eleitorais que terminaram mais tarde eram estruturalmente mais favoráveis a Lula?

A comparação com 2022 é necessária para verificar se essa ordenação temporal já existia antes de 2026.

---

## 2026-10-05 — E0040 — Implementação da Fase 3J: horário de conclusão das zonas x inclinação política

**Evento:** criação do `analyze_phase3j_zone_completion_bias.py`.

**Commit:** `b778e3a05b24a0803df1cecb9fecff9238b1a98d`

### Fonte

`ArvorCo/PNAD`, `zonas.json`, commit fixado:
`beb3bec9ae5c25e2868ee2f2cefb9e6dccd91415`

O produto contém **6.106 pares município-zona**, com:
- votos presidenciais finais de 2026;
- hora em Brasília da primeira seção observada;
- hora em Brasília em que a zona atingiu todas as seções;
- resultado presidencial de 2022 quando disponível.

### Método

Dentro de cada UF, para reduzir o efeito de composição entre estados:

1. ordenar as zonas por horário de conclusão;
2. calcular Spearman entre horário de conclusão e margem Lula−Flávio de 2026;
3. repetir para margem Lula−Bolsonaro no 1º turno de 2022;
4. comparar o quartil que concluiu primeiro com o quartil que concluiu por último, somando votos;
5. verificar se o mesmo gradiente temporal aparece em 2022.

### Interpretação

Se zonas mais tardias forem mais Lula em 2026 **e também já fossem mais Lula em 2022**, isso sustenta uma explicação de ordenação geográfica estrutural.

Se o gradiente aparecer fortemente apenas em 2026, o padrão exigirá investigação adicional.

### Limitação

A hora de conclusão de uma zona é a hora em que entrou sua última seção. Ela não informa quando cada seção da zona entrou.

Portanto a Fase 3J testa **ordenação geográfica do término da apuração**, não a composição exata dos lotes nacionais de 19:14 e 20:04.

**Próxima ação:** executar a Fase 3J e versionar os três artefatos.


---

## 2026-10-05 — E0041 — Resultado da Fase 3J: zonas tardias eram mais Lula também em 2022

**Evento:** análise dos resultados versionados da Fase 3J.

**Commit dos resultados:** \`6bcf701\`

### Cobertura

- zonas reportadas na fonte: **6.106**
- zonas incompletas: **12**
- zonas completas utilizáveis: **6.094**
- zonas sem comparação 2022: **24**

### Resultado nacional por quartis definidos dentro de cada UF

Em 2026:
- quartil mais cedo: margem Lula−direita **−0,85 pp**
- quartil mais tarde: **+0,19 pp**
- diferença late−early: **+1,04 pp**

Nas mesmas posições de conclusão, usando o resultado de 2022:
- quartil mais cedo: margem Lula−Bolsonaro **+5,87 pp**
- quartil mais tarde: **+7,41 pp**
- diferença late−early: **+1,54 pp**

Portanto o gradiente "zonas mais tardias são mais Lula" **já existia em 2022** e, no agregado ponderado por votos, era inclusive maior que em 2026.

### Spearman por UF

2026:
- UFs com correlação positiva entre horário de conclusão e margem Lula: **17/27**
- negativas: **10/27**
- mediana rho: **+0,073**

2022, usando as mesmas zonas ordenadas pelo horário de conclusão de 2026:
- positivas: **17/27**
- negativas: **10/27**
- mediana rho: **+0,024**

### Estados importantes para a Fase 3I

Gradiente late−early de margem Lula−direita, 2026 versus 2022:

- AM: **+50,32 pp** vs **+56,55 pp**
- BA: **+9,87 pp** vs **+11,51 pp**
- CE: **+17,08 pp** vs **+21,55 pp**
- PE: **+13,60 pp** vs **+19,35 pp**
- PA: **+23,66 pp** vs **+26,93 pp**
- MG: **+12,28 pp** vs **+12,94 pp**
- MA: **+4,08 pp** vs **+4,02 pp**
- SP: **+23,15 pp** vs **+20,52 pp**

Nos principais estados que explicaram o movimento posterior pró-Lula na Fase 3I, a maior parte mostra gradiente tardio semelhante ou **mais forte em 2022**.

### Conclusão limitada

A Fase 3J sustenta fortemente uma explicação de **ordenação geográfica estrutural** para uma parte relevante do fato de resultados tardios tenderem a favorecer Lula.

O padrão:
- não apareceu apenas em 2026;
- aparece nas mesmas zonas quando se substitui o voto de 2026 pelo voto presidencial de 2022;
- em agregado, o gradiente tardio era maior em 2022.

Isso reduz a plausibilidade da interpretação de que o simples fato de o voto tardio ser mais Lula seja, por si só, uma anomalia exclusiva de 2026.

Ainda resta uma pergunta:
> depois de controlar explicitamente a inclinação política da mesma zona em 2022, existe um componente temporal residual em 2026?

---

## 2026-10-05 — E0042 — Implementação da Fase 3K: efeito temporal residual controlado por 2022

**Evento:** criação do \`analyze_phase3k_residual_timing.py\`.

**Commit:** \`cc4f5d6f1b96e80d962d761de3bda562360b86ab\`

### Método

Para cada zona com dados comparáveis:

\[
\Delta margem = (Lula-Flávio)_{2026} - (Lula-Bolsonaro)_{2022}
\]

Dentro de cada UF serão calculados:
- Spearman entre horário de conclusão e \(\Delta margem\);
- diferença late−early em 2026;
- diferença late−early em 2022;
- **delta-do-gradiente**:
  \[
  (late-early)_{2026} - (late-early)_{2022}
  \]

Também será produzido um agregado nacional com quartis definidos separadamente dentro de cada UF.

### Leitura esperada

- delta-do-gradiente > 0:
  o viés pró-Lula das zonas tardias ficou mais forte em 2026;
- delta-do-gradiente < 0:
  o viés já existia e ficou mais fraco em 2026.

### Inspeção exploratória antes da automação

Usando os artefatos já versionados da Fase 3J, a conta preliminar do agregado produz aproximadamente:
- late−early 2026: **+1,10 pp**
- late−early 2022: **+1,46 pp**
- delta-do-gradiente: **−0,36 pp**

Nos estados-chave:
- AM: delta do gradiente **−6,23 pp**
- BA: **−1,64 pp**
- CE: **−4,47 pp**
- PE: **−5,75 pp**
- PA: aproximadamente **−3,18 pp**
- MG: **−0,66 pp**
- MA: aproximadamente **−0,11 pp**
- SP: aproximadamente **+2,81 pp**

Essa é apenas inspeção preliminar; a conclusão ficará condicionada à execução reproduzível da Fase 3K.

**Próxima ação:** executar a Fase 3K, versionar os três artefatos e então encerrar esta sublinha temporal/geográfica ou identificar UFs residuais específicas para aprofundamento.


---

## 2026-10-05 — E0043 — Resultado da Fase 3K: controle histórico reduz fortemente o caráter anômalo do voto tardio

**Evento:** análise dos resultados versionados da Fase 3K.

**Commit dos resultados:** \`bc78365\`

### Cobertura

- zonas comparáveis com 2022: **6.070**
- UFs: **27**

### Resultado agregado ponderado

Quartis definidos dentro de cada UF:

2026:
- gradiente late−early da margem Lula−direita: **+1,10 pp**

2022:
- gradiente late−early: **+1,46 pp**

Delta-do-gradiente:
- **−0,36 pp**

Isto significa que, no agregado ponderado por votos, o viés pró-Lula das zonas que terminam mais tarde **não ficou mais forte em 2026**; ficou ligeiramente mais fraco que no mesmo ordenamento geográfico observado em 2022.

### Resultado por UF

Spearman entre horário de conclusão e mudança de margem 2026−2022:
- mediana: **+0,109**
- positivo em **20 UFs**
- negativo em **7 UFs**

Delta-do-gradiente por UF:
- mediana: **+1,33 pp**
- positivo em **16 UFs**
- negativo em **11 UFs**

Portanto existe heterogeneidade: muitas UFs mostram mudança relativa mais favorável a Lula nas zonas tardias, porém isso não domina o agregado ponderado nacional.

### Estados centrais para a recuperação posterior de Lula

Delta-do-gradiente 2026−2022:
- AM: **−6,23 pp**
- BA: **−1,64 pp**
- CE: **−4,47 pp**
- PE: **−5,75 pp**
- PA: **−3,18 pp**
- MG: **−0,66 pp**
- MA: **−0,11 pp**
- SP: **+2,81 pp**

Nos principais estados que explicaram o saldo tardio pró-Lula na Fase 3I, quase todos apresentam gradiente tardio **igual ou menor que o histórico de 2022**. SP é a exceção de maior porte entre esses estados.

### UFs com maior aumento residual do gradiente tardio

Entre os maiores deltas positivos:
- RR: **+11,48 pp** (14 zonas comparáveis)
- AP: **+7,19 pp** (17 zonas)
- TO: **+4,76 pp**
- RS: **+4,59 pp**
- AL: **+4,27 pp**
- RN: **+3,59 pp**
- AC: **+3,43 pp**
- PB: **+3,13 pp**
- MT: **+3,13 pp**
- SP: **+2,81 pp**

RR e AP têm número pequeno de zonas e serão tratados com cautela.

### Conclusão limitada

A sublinha "Lula cresce porque resultados tardios são anormalmente pró-Lula em 2026" perde força quando se usa 2022 como controle geográfico.

O fato básico permanece:
- zonas tardias tendem, em vários estados, a ser mais Lula;
- isso já acontecia em 2022;
- no agregado ponderado, o gradiente era inclusive maior em 2022.

Não se conclui que toda a dinâmica temporal esteja explicada. Permanecem:
- a interrupção/defasagem de publicação nacional já documentada;
- os catch-ups com movimento top-2 extremo contra janelas comparáveis;
- UFs residuais específicas, sobretudo SP, que podem ser revisitadas.

A linha geográfica temporal ampla fica, por ora, **explicada em grande parte por ordenação estrutural pré-existente**.

---

## 2026-10-05 — E0044 — Implementação da Fase 4A: Governador direita/CD x Presidente

**Evento:** início da investigação de coerência entre cargos solicitada anteriormente.

**Commit:** \`96d8050228d14d339cc0d95f2b539fe41e8cb2d8\`

### Hipótese de trabalho

Quem vota em candidatura a Governador classificada como direita ou centro-direita tende a votar também à direita para Presidente.

### Classificação usada nesta primeira triagem

Cenário A:
- classificação externa do produto \`ArvorCo/PNAD governadores.json\`;
- campos incluídos: \`direita\` e \`centro-direita\`;
- a classificação fica registrada explicitamente no relatório e poderá ser substituída por cenários alternativos.

### Limites matemáticos por candidatura

Para:
- \`N\` = comparecimento presidencial na UF;
- \`G\` = votos da candidatura a Governador;
- \`L\` = votos em Lula;
- \`F\` = votos em Flávio Bolsonaro;

calcular:

1. sobreposição mínima Governador×Lula:
   \[
   \max(0, G + L - N)
   \]

2. sobreposição máxima Governador×Lula:
   \[
   \min(G, L)
   \]

3. mínimo de eleitores da candidatura a Governador que não podem estar no conjunto de votos de Flávio:
   \[
   \max(0, G - F)
   \]

O terceiro número é específico a Flávio e **não** equivale ainda a "não votou em nenhum presidenciável de direita".

### Cobertura desta fase

A fonte usada traz, em \`ufs[].candidatos\`, a candidatura eleita ou o par do 2º turno. Portanto a Fase 4A é uma **triagem das principais candidaturas**, não ainda o bloco completo de todas as candidaturas de direita em cada UF.

AL e AM podem estar marcados como provisórios no produto externo e serão explicitamente sinalizados.

### Próxima ação

Executar a Fase 4A e versionar:
- \`phase4a_governor_president_bounds.csv\`
- \`phase4a_summary.json\`

Depois:
- identificar UFs onde a sobreposição Governador-direita × Lula é matematicamente inevitável;
- aprofundar essas UFs em município/zona/seção;
- em seguida construir a versão específica para Senado, respeitando dois votos por eleitor.


---

## 2026-10-05 — E0045 — Resultado da Fase 4A: uma sobreposição Governador-direita × Lula é matematicamente inevitável

**Evento:** análise dos resultados versionados da Fase 4A.

**Commit dos resultados:** \`5d9017a\`

### Cobertura

- UFs com candidaturas principais de direita/centro-direita triadas: **19**
- candidaturas triadas: **20**
- linhas marcadas como fonte provisória no produto externo: **2**
- candidaturas com sobreposição mínima obrigatória Governador×Lula > 0: **1**
- candidaturas com mínimo obrigatório de eleitores fora do conjunto Flávio > 0: **7**

### Caso matematicamente mais forte: Paraíba

Lucas Ribeiro (PP, classificado como centro-direita):
- votos para Governador: **1.470.252**
- comparecimento presidencial: **2.683.988**
- votos em Lula: **1.541.127**
- votos em Flávio: **831.377**

Limite inferior Governador×Lula:

\[
\max(0, 1.470.252 + 1.541.127 - 2.683.988)
= 327.391
\]

Portanto, sob esses totais agregados, **pelo menos 327.391 eleitores** necessariamente pertencem ao conjunto de votantes de Lucas Ribeiro e ao conjunto de votantes de Lula.

Isso corresponde a **22,27%** dos votos de Lucas Ribeiro.

O limite máximo é 1.470.252; portanto o intervalo matematicamente possível para a sobreposição é:

\[
[327.391,\ 1.470.252]
\]

Esse resultado não identifica indivíduos, mas o limite inferior positivo é uma consequência combinatória inevitável dos totais.

### Candidaturas com mais votos que Flávio na mesma UF

Número mínimo de eleitores daquela candidatura a Governador que não podem estar contidos no conjunto de votos de Flávio:

- SP, Tarcísio: **1.569.851** (**10,83%** dos votos de Tarcísio)
- PB, Lucas Ribeiro: **638.875** (**43,45%**)
- MG, Cleitinho Azevedo: **544.042** (**8,61%**)
- PA, Dr. Daniel: **181.764** (**7,75%**)
- AL, JHC: **156.139** (**17,51%**) — fonte de Governador marcada como provisória no produto externo
- MS, Eduardo Riedel: **40.972** (**4,48%**)
- RN, Allyson: **13.316** (**1,81%**)

Esses limites são específicos ao conjunto de votos de Flávio. Eles **não** significam ainda que todos esses eleitores deixaram de votar em um presidenciável de direita, pois existem outras candidaturas presidenciais classificáveis como direita/centro-direita.

### Conclusão limitada

A Fase 4A já mostra que a hipótese de alinhamento perfeito Governador-direita → Flávio é incompatível com os totais em pelo menos sete candidaturas triadas.

No caso da Paraíba, há um resultado mais forte: mesmo sem escolher como distribuir todos os demais votos, a sobreposição Lucas Ribeiro × Lula precisa ser de pelo menos **327.391 eleitores**.

A Fase 4A, porém, não cobre:
- todas as candidaturas a Governador;
- todas as UFs;
- o bloco presidencial completo de direita.

Por isso o próximo teste deve substituir candidatura isolada por **blocos ideológicos completos**.

---

## 2026-10-05 — E0046 — Implementação da Fase 4B: blocos completos de direita em todas as UFs

**Evento:** criação do \`analyze_phase4b_full_right_blocks.py\`.

**Commit:** \`7584bc32031d1fc35ce6ef92dd15148ebc04a0d7\`

### Objetivo

Repetir o teste da Fase 4A nas 27 UFs usando:
- todos os candidatos válidos a Governador;
- todos os candidatos válidos a Presidente;
- a mesma classificação explícita de partidos;
- bloco ampliado \`direita + centro-direita\`.

### Fontes oficiais

Para cada UF:
- Governador:
  \`/oficial/ele2026/6259/dados/{uf}/{uf}-c0003-e006259-u.json\`
- Presidente:
  \`/oficial/ele2026/6257/dados/{uf}/{uf}-c0001-e006257-u.json\`

A estrutura do endpoint de Governador foi confirmada em captura contemporânea preservada do TSE.

### Classificação

Fonte:
\`ArvorCo/PNAD apuracao/public/campos.json\`

A tabela de classificação é versionada e explícita:
- direita
- centro-direita
- centro
- centro-esquerda
- esquerda
- indefinido

Exceções por \`sqcand\` têm precedência sobre a classificação partidária.

### Métricas por UF

Definições:
- \`G_R\`: todos os votos válidos para Governador em candidaturas direita/centro-direita;
- \`P_R\`: todos os votos válidos para Presidente em candidaturas direita/centro-direita;
- \`L\`: Lula;
- \`N\`: comparecimento.

Violação mínima da hipótese de alinhamento:

\[
\max(0, G_R - P_R)
\]

Sobreposição mínima Governador-direita × Lula:

\[
\max(0, G_R + L - N)
\]

Também serão calculados os intervalos completos de sobreposição entre:
- Governador-direita × Presidente-direita;
- Governador-direita × Lula.

### Auditoria de qualidade embutida

O script também verifica:
- comparecimento Governador vs Presidente por UF;
- soma dos votos válidos dos candidatos vs \`v.vv\` para Presidente;
- soma dos votos válidos dos candidatos vs \`v.vv\` para Governador;
- votos válidos de candidatos que permaneceram sem classificação.

### Saídas previstas

- \`phase4b_uf_blocks.csv\`
- \`phase4b_candidate_inventory.csv\`
- \`phase4b_summary.json\`

**Próxima ação:** executar a Fase 4B. Se a violação mínima continuar positiva depois de agregar **todo** o bloco presidencial de direita, então teremos um resultado substancialmente mais forte do que o teste Flávio-isolado da Fase 4A.


---

## 2026-10-05 — E0047 — Resultado da Fase 4B: bloco completo de direita/CD

**Evento:** análise dos resultados versionados da Fase 4B.

**Commit dos resultados:** \`b794a6c\`

### Cobertura

- UFs analisadas: **27**
- linhas de inventário de candidaturas: **508**
- UFs com \`G_R > P_R\` e, portanto, violação mínima obrigatória da hipótese de alinhamento perfeito: **13**
- UFs com sobreposição mínima obrigatória Governador-direita × Lula > 0: **7**
- reconciliação dos votos válidos dos candidatos com \`v.vv\`:
  - Presidente: **0 erros**
  - Governador: **0 erros**
- votos válidos sem classificação na taxonomia usada:
  - Presidente: **0**
  - Governador: **0**

### Maiores violações mínimas \`max(0, G_R - P_R)\`

Cenário usado: \`direita + centro-direita\` nos dois cargos.

- PB: **1.146.651** (**56,68%** de \`G_R\`)
- MG: **1.068.784** (**14,85%**)
- BA: **1.059.171** (**29,19%**)
- SP: **655.183** (**4,52%**)
- RN: **507.418** (**40,10%**)
- MT: **238.529** (**15,15%**)
- AL: **128.745** (**14,41%**)
- MS: **125.107** (**12,10%**)
- PA: **92.800** (**3,96%**)
- RR: **75.752** (**24,11%**)
- AC: **49.409** (**13,69%**)
- SE: **21.639** (**4,68%**)
- PI: **11.757** (**2,09%**)

### Sobreposição mínima obrigatória Governador-direita × Lula

- PB: **880.227** (**43,51%** de \`G_R\`)
- RN: **332.237** (**26,26%**)
- BA: **239.242** (**6,59%**)
- MT: **104.293** (**6,62%**)
- RR: **55.891** (**17,79%**)
- MS: **9.567** (**0,93%**)
- AC: **7.463** (**2,07%**)

Esses valores são limites inferiores combinatórios usando os totais agregados.

### Comparecimento Presidente × Governador

O script marcou diferença de comparecimento nas **27 UFs**, sempre com Presidente acima de Governador. Soma das diferenças:
- **165.584** comparecimentos a mais no cargo Presidente.

Esse padrão é compatível com a regra oficial de **voto em trânsito**:
- quem vota em trânsito dentro da mesma UF pode votar em todos os cargos;
- quem está em outra UF pode votar **apenas para Presidente**;
- eleitor inscrito no exterior em trânsito no Brasil também vota apenas para Presidente.

Portanto a diferença sistemática Presidente > Governador não é, por si só, erro de qualidade.

Além disso, usar o comparecimento presidencial como universo \`N\` nos limites Governador×Lula torna o limite **conservador**, porque \`N\` inclui pessoas que nem eram elegíveis ao cargo Governador naquela UF.

### Conclusão limitada

A Fase 4B produz um resultado substancialmente mais forte que a 4A: mesmo somando todos os presidenciáveis classificados como direita/centro-direita, há **13 UFs** nas quais o bloco de Governador-direita é maior que o bloco presidencial equivalente.

Em 7 UFs a interseção Governador-direita × Lula é matematicamente positiva mesmo usando o universo presidencial ampliado pelo voto em trânsito.

Entretanto, o resultado ainda depende da fronteira classificatória:
- PSD aparece como \`centro\`;
- AVANTE aparece como \`centro\`;
- PSDB aparece como \`centro-esquerda\` na classificação partidária, embora alguns candidatos específicos possam ser percebidos politicamente de outra forma.

Por isso nenhuma conclusão substantiva deve ser fechada antes de uma análise de sensibilidade da classificação.

---

## 2026-10-05 — E0048 — Evidência externa visual: alegação de pausa e swing Lula/Flávio

**Evento:** recebida captura de uma postagem pública com a alegação de que:
1. os updates da apuração teriam sido interrompidos por cerca de uma hora;
2. após a retomada, Lula teria crescido e Flávio caído.

A imagem contém um gráfico com pontos aproximados:
- 17:35
- 18:00
- 18:30
- 18:48
- 20:14
- 20:30

e marca uma faixa contínua entre ~18:48 e ~20:14 como período de interrupção.

### Comparação com a cronologia já reconstruída

A alegação tem um **núcleo factual parcial**:
- houve interrupção/defasagem relevante na publicação nacional de Presidente;
- após os grandes catch-ups, a participação relativa de Lula sobe e a de Flávio cai.

Porém o desenho de uma única pausa contínua 18:48→20:14 é simplificado demais.

A série de maior resolução já reconstruída mostrou:
- atualização nacional em **18:48:59**;
- nova atualização em **19:14:08**;
- principal congelamento nacional de **19:14:08 a 20:04:39** (~50,52 min);
- pausa geral de geração EA20 de **19:32:47 a 20:01:55** (~29,13 min).

Portanto o gráfico da postagem **omite o catch-up nacional de 19:14** e não deve ser usado sozinho para afirmar que não houve nenhum update entre 18:48 e 20:14.

### Relação com os demais testes

- Fase 3F: os catch-ups tiveram movimento top-2 extremo contra janelas de tamanho comparável;
- Fases 3J/3K: resultados geograficamente tardios já eram estruturalmente mais pró-Lula em 2022, e o gradiente agregado tardio foi ligeiramente menor em 2026.

Assim, a postagem registra uma percepção pública relevante e uma parte verdadeira da cronologia, mas **não estabelece causa** para o swing.

---

## 2026-10-05 — E0049 — Implementação da Fase 4C: sensibilidade da classificação ideológica

**Evento:** criação do \`analyze_phase4c_classification_sensitivity.py\`.

**Commit:** \`aa630d87fbce7be4069e4063bc9de9240dea6cc4\`

### Objetivo

Verificar se as 13 violações mínimas da Fase 4B sobrevivem a diferentes fronteiras de classificação.

### Cenários

1. \`strict_symmetric\`
   - Governador: direita
   - Presidente: direita

2. \`broad_symmetric\`
   - Governador: direita + centro-direita
   - Presidente: direita + centro-direita
   - reproduz a Fase 4B

3. \`nonleft_symmetric\`
   - Governador: direita + centro-direita + centro
   - Presidente: direita + centro-direita + centro

4. \`stress_min_violation\`
   - Governador: somente direita
   - Presidente: direita + centro-direita + centro

O quarto cenário é propositalmente assimétrico e conservador:
- minimiza \`G\`;
- maximiza \`P\` dentro da taxonomia usada.

Se \`G > P\` persistir mesmo nesse cenário, a conclusão é robusta à fronteira direita/CD/centro usada pela fonte.

### Saídas previstas

- \`phase4c_sensitivity_by_uf.csv\`
- \`phase4c_summary.json\`

**Próxima ação:** executar a Fase 4C e somente depois selecionar UFs para aprofundamento por município/zona/seção.


---

## 2026-10-05 — E0050 — Resultado da Fase 4C: três UFs permanecem positivas no stress test

**Evento:** análise dos resultados versionados da Fase 4C.

**Commit dos resultados:** \`d99d664\`

### Cenários

- \`strict_symmetric\`: direita em ambos os cargos
- \`broad_symmetric\`: direita + centro-direita em ambos
- \`nonleft_symmetric\`: direita + centro-direita + centro em ambos
- \`stress_min_violation\`: Governador somente direita; Presidente direita + centro-direita + centro

### Resultado

Número de UFs com violação mínima \`max(0, G-P) > 0\`:

- strict: **5**
- broad: **13**
- nonleft: **21**
- stress: **3**

UFs positivas nos três cenários simétricos:
- **MG**
- **MT**
- **RR**
- **SE**

UFs que permanecem positivas mesmo no stress test:
- **MG**
- **MT**
- **RR**

### Stress test — magnitudes

MG:
- Governador-direita: **7.197.091**
- Presidente direita+centro-direita+centro: **6.768.467**
- violação mínima: **428.624**
- **5,96%** do bloco estadual estrito

MT:
- Governador-direita: **1.568.841**
- Presidente não-esquerda do cenário: **1.409.314**
- violação mínima: **159.527**
- **10,17%**

RR:
- Governador-direita: **314.243**
- Presidente não-esquerda do cenário: **250.709**
- violação mínima: **63.534**
- **20,22%**

### Sobreposição mínima Governador-direita × Lula no stress test

MT:
- **98.389**
- **6,27%** do bloco Governador-direita

RR:
- **55.891**
- **17,79%**

MG:
- limite estadual agregado = **0**

Importante: limite estadual zero em MG não significa ausência de voto cruzado; apenas significa que os totais estaduais permitem, em princípio, uma alocação sem interseção obrigatória. Ao descer para municípios, déficits e superávits locais deixam de se compensar entre si e o limite pode se tornar positivo.

### Conclusão limitada

MG, MT e RR são os três estados mais robustos ao problema de classificação, porque o resultado \`G>P\` sobrevive a um cenário propositalmente favorável ao alinhamento:
- bloco estadual reduzido a somente "direita";
- bloco presidencial ampliado para direita + centro-direita + centro.

Esse resultado continua sendo um teste de conjuntos agregados, não prova de transferência individual para Lula.

**Próxima etapa:** decompor MG, MT e RR por município, com o mesmo stress test e controles de qualidade.

---

## 2026-10-05 — E0051 — Implementação da Fase 4D: decomposição municipal em MG, MT e RR

**Evento:** criação do \`analyze_phase4d_municipality_bounds.py\`.

**Commit:** \`1fb714eb2567b825981705eb7ff204b438e0dbf5\`

### Objetivo

Descer um nível geográfico nos três estados robustos da Fase 4C e medir:

\[
\max(0,G-P)
\]

e

\[
\max(0,G+L-N)
\]

por município.

### Propriedade importante

Municípios são universos de votação disjuntos.

Por isso:

\[
\sum_m \max(0,G_m-P_m)
\ge
\max(0,\sum_m G_m-\sum_m P_m)
\]

O mesmo raciocínio vale para o limite de sobreposição com Lula.

Assim, a decomposição municipal pode revelar um limite inferior total maior que o limite estadual, porque um excesso de voto presidencial alinhado em um município não pode "compensar" eleitores de outro município.

### Cobertura

- MG
- MT
- RR

O script:
- baixa de forma idempotente os EA20 municipais finais de Presidente e Governador;
- executa os quatro cenários da Fase 4C;
- reconcilia votos válidos por arquivo;
- compara as somas municipais com os totais estaduais;
- produz ranking dos municípios com maiores mínimos no stress test.

### Saídas previstas

- \`phase4d_municipality_bounds.csv\`
- \`phase4d_state_summary.csv\`
- \`phase4d_summary.json\`

**Próxima ação:** executar a Fase 4D e, com base no ranking municipal, selecionar os municípios que justificam descida para zona/seção.


---

## 2026-10-05 — E0052 — Resultado da Fase 4D: decomposição municipal de MG, MT e RR

**Evento:** análise dos resultados versionados da Fase 4D.

**Commit dos resultados:** \`2f37c6f\`

### Cobertura

- municípios processados: **1.010**
- MG: **853**
- MT: **142**
- RR: **15**
- erros de download/processamento: **0**
- reconciliação interna candidato→votos válidos em cada arquivo:
  - Presidente: **0 erros**
  - Governador: **0 erros**

### Stress test municipal

Cenário:
- Governador = somente \`direita\`
- Presidente = \`direita + centro-direita + centro\`

#### MG

A partir das somas municipais disponíveis:
- mínimo estadual agregado: **431.625**
- soma dos mínimos municipais: **642.836**
- ganho de localização: **+211.211**

Sobreposição mínima Governador-direita × Lula:
- no agregado municipal do estado: **0**
- soma dos mínimos municipais: **330.138**

Municípios:
- com violação mínima positiva: **766/853**
- com overlap mínimo Gov-direita × Lula positivo: **582/853**

#### MT

- mínimo estadual agregado: **159.527**
- soma dos mínimos municipais: **159.527**
- overlap mínimo Gov-direita × Lula por soma municipal: **99.030**

Municípios:
- violação positiva: **142/142**
- overlap mínimo com Lula: **141/142**

#### RR

- mínimo estadual agregado: **63.534**
- soma dos mínimos municipais: **63.534**
- overlap mínimo Gov-direita × Lula: **55.891**

Municípios:
- violação positiva: **15/15**
- overlap mínimo com Lula: **15/15**

### Maiores municípios no stress test

Entre os maiores mínimos aparecem:
- Boa Vista/RR: violação >= **30.487**, overlap Gov-direita×Lula >= **25.786**
- Cuiabá/MT: violação >= **17.323**, overlap >= **4.855**
- Divinópolis/MG: violação >= **16.077**, overlap >= **8.589**
- Várzea Grande/MT: violação >= **10.697**, overlap >= **5.409**
- Patos de Minas/MG: violação >= **9.861**, overlap >= **5.889**
- Rondonópolis/MT: violação >= **7.379**, overlap >= **2.888**
- Minas Novas/MG: violação >= **5.959**, overlap >= **4.860**
- Cáceres/MT: violação >= **5.948**, overlap >= **4.445**

### Interpretação limitada

A descida municipal aumenta materialmente o limite inferior em MG, como esperado quando se impede compensação entre municípios.

Em MT e RR, a violação é praticamente estrutural em toda a malha municipal do cenário adotado.

---

## 2026-10-05 — E0053 — Correção de qualidade: MG municipal continua com EA20 presidencial defasado em 8 municípios

**Evento:** comparação dos totais municipais da Fase 4D com os totais estaduais da Fase 4C e com a anomalia auxiliar já identificada na Fase 2.

### Diferenças MG — stress test

Fase 4C, arquivo estadual oficial:
- Governador-direita: **7.197.091**
- Presidente não-esquerda do cenário: **6.768.467**
- Lula: **5.188.936**
- comparecimento Presidente: **12.637.274**
- violação mínima estadual: **428.624**

Soma dos arquivos municipais usada na Fase 4D:
- Governador-direita: **7.197.091**
- Presidente não-esquerda: **6.765.466**
- Lula: **5.184.038**
- comparecimento: **12.628.861**
- violação mínima calculada das somas municipais: **431.625**

Diferenças municipal−estadual:
- Governador-direita: **0**
- Presidente não-esquerda: **−3.001**
- Lula: **−4.898**
- comparecimento: **−8.413**

Essas diferenças coincidem com a anomalia auxiliar já documentada na Fase 2: **36 seções** ausentes em 8 EA20 municipais de MG.

Municípios já identificados:
- 40622
- 41556
- 41696
- 42005
- 46078
- 47198
- 51977
- 53171

### Impacto

- MT e RR reconciliam exatamente entre soma municipal e estado.
- MG **não pode ainda ter seus limites municipais finais tratados como fechados**.
- O valor estadual robusto de MG continua sendo o da Fase 4C: **428.624**.
- Os rankings municipais de MG são úteis como triagem, mas a soma de mínimos (**642.836**) e o overlap mínimo com Lula (**330.138**) ficam provisórios até substituir os 8 arquivos municipais defasados por dados de zona/seção completos.

---

## 2026-10-05 — E0054 — Evidência externa: alegação "58,1 milhões no PL Senado > 56 milhões de Flávio"

**Evento:** recebida captura de postagem pública que afirma:

> se candidatos do PL ao Senado somaram 58.123.987 votos e Flávio teve cerca de 56 milhões, então pelo menos ~2 milhões de votos teriam sido "roubados".

### Problema lógico da comparação

Nas Eleições 2026 cada eleitor faz **duas escolhas para Senador**, em candidatos diferentes.

Portanto:
- total de votos dos candidatos do PL ao Senado = **votos-candidato**;
- votos de Flávio para Presidente = **um voto presidencial por eleitor**.

Essas grandezas não são diretamente comparáveis como número de pessoas únicas.

Se, apenas como ilustração extrema, todos os 58.123.987 votos-candidato do PL fossem distribuídos em pares entre dois candidatos PL pelos mesmos eleitores, o total corresponderia a apenas cerca de **29,1 milhões de eleitores únicos**.

O limite correto, porém, deve ser calculado **UF por UF**:
- para uma UF com dois candidatos PL ao Senado, o menor número possível de eleitores únicos do PL é o maior dos dois totais individuais, não metade arredondada do total nacional;
- com um único candidato PL, votos-candidato = eleitores únicos daquele candidato.

### Outro detalhe

A postagem usa **56.076.888** para Flávio. O resultado final oficial preservado nesta investigação é **56.104.503**. Portanto o número da imagem parece ser snapshot anterior ou valor não final.

### Status

A conclusão "pelo menos 2 milhões foram roubados" **não decorre dessa aritmética**.

Ainda assim, a pergunta substantiva será investigada:
- quantos eleitores únicos no mínimo votaram em pelo menos um candidato PL ao Senado?
- quantos desses, por simples limite de conjuntos por UF, necessariamente não cabem no conjunto de votos de Flávio?
- existe overlap mínimo matemático PL-Senado × Lula?

---

## 2026-10-05 — E0055 — Implementação da Fase 4E: PL Senado × Flávio

**Evento:** criação do \`analyze_phase4e_pl_senate_claim.py\`.

**Commit:** \`9ae3419493e4c69b0a54039ea214faaf4675b1bb\`

### Método

Para cada UF:
- baixar resultado oficial final de Senado (cargo 5);
- identificar todos os candidatos válidos do PL;
- calcular:
  - soma de votos-candidato PL;
  - limite inferior de eleitores únicos PL = maior votação individual entre candidatos PL;
  - limite superior = min(comparecimento ao Senado, soma dos votos PL);
- comparar os limites com Flávio e Lula no resultado presidencial oficial.

### Limites calculados

\[
U_{PL,min}=\max(votos\ dos\ candidatos\ PL\ na\ UF)
\]

\[
min(PL\text{-}Senado\ fora\ de\ Flávio)=\max(0,U_{PL,min}-F)
\]

\[
min(PL\text{-}Senado\cap Lula)=\max(0,U_{PL,min}+L-N_{Pres})
\]

### Controle adicional

O script verifica se, em cada UF:

\[
v.tv = 2 \times comparecimento
\]

no arquivo do Senado, evidenciando diretamente que o total de oportunidades de voto ao Senado é duas vezes o número de votantes.

### Saídas previstas

- \`phase4e_pl_senate_by_uf.csv\`
- \`phase4e_pl_senate_candidates.csv\`
- \`phase4e_summary.json\`

**Próxima ação:** executar a Fase 4E e, em paralelo, preparar reparo dos 8 municípios defasados de MG antes de descer para zona/seção.


---

## 2026-10-05 — E0056 — Resultado da Fase 4E: alegação PL Senado x Flávio

**Evento:** análise dos resultados versionados da Fase 4E.

**Commit dos resultados:** \`5e1116f\`

### Totais observados

- votos-candidato de todos os candidatos válidos do PL ao Senado nas 27 UFs:
  **58.307.861**
- Flávio no resultado final nacional, incluindo exterior:
  **56.104.503**
- diferença bruta:
  **+2.203.358**

Essa diferença bruta continua **não sendo uma diferença de eleitores**, porque o Senado oferece duas escolhas por votante.

### Intervalo de eleitores únicos PL-Senado

Somando os limites por UF:

- limite inferior: **49.340.389**
- limite superior: **57.923.160**

Portanto os 58,3 milhões de votos-candidato do PL podem corresponder a qualquer quantidade de eleitores únicos dentro desse intervalo; não se pode deduzir diretamente "58,3 milhões de pessoas votaram PL para Senado".

### Limite PL-Senado fora do conjunto Flávio

Somando os limites inferiores UF por UF:

- mínimo obrigatório de eleitores PL-Senado que não cabem no conjunto de votos de Flávio:
  **515.873**

Concentração:
- BA: **436.858**
- MS: **30.203**
- DF: **28.880**
- CE: **19.932**

Isso significa apenas "não podem todos ser eleitores de Flávio". Esses eleitores podem ter votado em outro candidato presidencial, branco/nulo ou Lula; o conjunto agregado não identifica qual opção.

### Sobreposição obrigatória PL-Senado × Lula

- mínimo agregado por UF:
  **0**

Logo, os totais não obrigam matematicamente nenhuma interseção PL-Senado × Lula.

### Evidência estrutural do voto duplo para Senado

Em **27/27 UFs**:

\[
v.tv = 2 \times comparecimento
\]

confirmando no próprio arquivo oficial que o cargo Senado contabiliza duas oportunidades de voto por eleitor.

### Conclusão limitada

A inferência pública "58,3 milhões no PL Senado menos 56,1 milhões em Flávio = pelo menos 2,2 milhões roubados" é aritmeticamente inválida.

Existe, porém, um resultado legítimo diferente:
- pelo menos **515.873** eleitores do limite inferior PL-Senado não podem estar todos dentro do conjunto Flávio, quando o cálculo é feito UF por UF.

Isso é voto cruzado/abstenção/branco-nulo/terceira candidatura em aberto; não é evidência automática de fraude.

---

## 2026-10-05 — E0057 — Correção territorial da Fase 4E: exterior não participa do Senado

**Evento:** revisão do controle de qualidade da Fase 4E.

O relatório gerado mostrou:
- soma Flávio nas 27 UFs: **55.960.603**
- Flávio BR: **56.104.503**
- diferença: **143.900**

Essa diferença é o **exterior (ZZ)**, não erro de reconciliação.

Como não há eleição de Senador no exterior, existem duas comparações brutas possíveis:

1. PL-Senado 27 UFs vs Flávio BR:
   - 58.307.861 − 56.104.503 = **+2.203.358**

2. PL-Senado 27 UFs vs Flávio 27 UFs:
   - 58.307.861 − 55.960.603 = **+2.347.258**

Ambas continuam misturando votos-candidato de Senado com voto presidencial individual e, portanto, nenhuma delas fornece número de eleitores "faltantes".

O script \`analyze_phase4e_pl_senate_claim.py\` foi corrigido para rotular explicitamente:
- Flávio BR;
- Flávio 27 UFs;
- exterior implícito;
- e retirar a expressão "erro de reconciliação".

**Commit da correção:** \`8c8b09e8e628486561d5d4ec515d8193b099a3f3\`

A correção de rotulagem **não altera** o limite principal de **515.873**, porque ele já era calculado UF por UF.

---

## 2026-10-05 — E0058 — Evidência externa: "após o travamento Lula nunca desce, Flávio nunca sobe"

**Evento:** recebida nova captura pública com a alegação:

> depois que o site saiu do travamento, Lula subiria continuamente e Flávio cairia continuamente; a postagem também afirma passos de 0,01% a cada 15 segundos e associa o padrão a 2022.

### Inspeção direta da série preservada

Na série nacional de versões genuínas já preservada, a parte **direcional** da alegação é verdadeira.

Janela aproximada da imagem, de 20:04:39 a 20:30:35:
- versões: **26**
- transições: **25**
- Lula subiu em **25/25**
- Lula caiu em **0/25**
- Flávio caiu em **25/25**
- Flávio subiu em **0/25**

Da retomada de 20:04:39 até a última versão, 02:59:31:
- transições: **152**
- Lula: **150 altas, 2 estáveis, 0 quedas**
- Flávio: **150 quedas, 2 estáveis, 0 altas**

Movimento acumulado pós-retomada:
- Lula: **+1,6706 pp**
- Flávio: **−1,4384 pp**

Portanto a sequência monotônica não termina às 20:30; ela persiste até 100% na série nacional observada.

### Partes da postagem que não conferem literalmente

Na janela 20:04→20:30:
- passos Lula exatamente +0,01 pp em duas casas: **9/25**
- passos Flávio exatamente −0,01 pp: **14/25**
- mediana entre novas versões nacionais: **41 s**
- mínimo: **21 s**
- máximo: **377 s**
- nenhuma transição exatamente em **15 s**

Assim:
- "Lula nunca desce / Flávio nunca sobe": sustentado pela série;
- "sempre exatamente ±0,01": não sustentado;
- "nova versão exatamente a cada 15 s": não sustentado pelas horas de geração do arquivo nacional.

A interface pode consultar o servidor em outra cadência, mas isso não é o mesmo que o TSE gerar nova versão a cada 15 s.

### Relação com a geografia já medida

A monotonicidade significa matematicamente que quase todos os lotes posteriores tinham:
- share de Lula acima de sua participação acumulada anterior;
- share de Flávio abaixo de sua participação acumulada anterior.

As Fases 3J/3K mostraram que zonas tardias já eram estruturalmente mais pró-Lula também em 2022, o que oferece um controle histórico relevante.

A afirmação específica "como em 2022" da nova captura **ainda não foi testada com uma série temporal nacional de 2022 equivalente**.

---

## 2026-10-05 — E0059 — Implementação da Fase 4F: monotonicidade pós-retomada

**Evento:** criação do \`analyze_phase4f_post_resume_monotonicity.py\`.

**Commit:** \`2c7753021316acf9f2f9a8a6ab8b19660f56076d\`

### Objetivo

Separar e testar formalmente:
1. direção monotônica;
2. tamanho dos passos exibidos em duas casas;
3. cadência real entre versões;
4. duração/comprimento da sequência;
5. composição marginal dos lotes.

### Saídas previstas

- \`phase4f_post_resume_transitions.csv\`
- \`phase4f_summary.json\`

### Próxima ação

Executar a Fase 4F e versionar os artefatos. Depois:
- procurar uma série temporal equivalente de 2022 para testar a frase "como em 2022";
- retomar o reparo dos 8 municípios defasados de MG antes de descer para zona/seção na linha Governador×Presidente.


---

## 2026-10-05 — E0060 — Resultado confirmado da Fase 4F e correção de arredondamento

**Evento:** análise dos resultados versionados da Fase 4F.

**Commit dos resultados:** \`09db62b\`

### Resultado observado

Janela 20:04:39 → 20:30:35:
- transições: **25**
- Lula: 25 altas, 0 quedas
- Flávio: 25 quedas, 0 altas

Da retomada 20:04:39 até 100%:
- transições: **152**
- no campo percentual arredondado a 4 casas:
  - Lula: 150 altas, 2 empates, 0 quedas
  - Flávio: 150 quedas, 2 empates, 0 altas

Movimento acumulado:
- Lula: **+1,6706 pp**
- Flávio: **−1,4384 pp**

### Correção importante

Recalculando as participações diretamente dos totais inteiros \`lula/vv\` e
\`flavio/vv\`, os dois aparentes empates desaparecem.

Resultado exato:
- Lula aumenta em **152/152** transições;
- Flávio diminui em **152/152** transições.

Logo a sequência pós-retomada é estritamente monotônica nos totais inteiros;
os dois empates da Fase 4F eram apenas efeito de arredondamento do campo
percentual publicado.

### Partes da alegação pública

Confirmada:
- direção: Lula nunca cai e Flávio nunca sobe após 20:04:39.

Não confirmadas:
- exatamente ±0,01 pp em cada atualização;
- geração de nova versão a cada 15 segundos.

---

## 2026-10-05 — E0061 — Implementação da Fase 4G: monotonicidade depende da ordem ou do conteúdo dos lotes?

**Evento:** criação do \`analyze_phase4g_order_invariance.py\`.

**Commit:** \`402da79ca41f82208f4c3e7fa8f39e683fa10245\`

### Pergunta

Uma sequência de 152 movimentos consecutivos no mesmo sentido parece, à
primeira vista, estatisticamente extrema.

Mas o teste correto precisa distinguir:
- acaso na **ordem** dos lotes;
- composição sistematicamente diferente dos **lotes que restavam**.

### Achado exploratório antes da execução formal

Derivando os 152 lotes diretamente das diferenças entre totais cumulativos
consecutivos:

- participação inicial às 20:04:39:
  - Lula: **43,49215%**
  - Flávio: **48,46621%**

- participação final:
  - Lula: **45,16277%**
  - Flávio: **47,02777%**

- conjunto inteiro de votos restantes após 20:04:39:
  - válidos: **18.809.656**
  - Lula: **54,08809%**
  - Flávio: **39,34286%**

Entre os 152 lotes:
- menor share de Lula: **47,67532%**
- maior share de Flávio: **46,21849%**
- Lula supera Flávio em **152/152** lotes
- menor margem Lula−Flávio em qualquer lote: **+2,83073 pp**

### Teste determinístico de ordem

Para Lula:
- ordenar os lotes por share Lula **decrescente** é o caso mais adverso para
  os lotes de share menor, pois maximiza o acumulado antes de eles entrarem.

Para Flávio:
- ordenar por share Flávio **crescente** é o caso mais adverso para lotes de
  share maior, pois minimiza o acumulado antes de eles entrarem.

Se mesmo nessas ordens adversariais:
- Lula nunca cair;
- Flávio nunca subir;

então a monotonicidade é **invariante à permutação** dos 152 lotes.

Nesse caso, uma conta como \((1/2)^{152}\) seria conceitualmente inadequada:
a sequência não seria resultado de 152 eventos independentes equiprováveis;
seria consequência do conteúdo do conjunto remanescente.

### Próxima ação

Executar a Fase 4G e versionar:
- \`phase4g_post_resume_batches.csv\`
- \`phase4g_summary.json\`

Depois:
1. interpretar se a sequência é ordem-invariante;
2. investigar a composição geográfica do conjunto remanescente;
3. continuar busca por série temporal nacional preservada de 2022.


---

## 2026-10-05 — E0062 — Resultado da Fase 4G: monotonicidade é invariante à ordem dos 152 lotes

**Evento:** análise dos resultados versionados da Fase 4G.

**Commit dos resultados:** \`1b9c3f7\`

### Resultado exato

Janela:
- início: **20:04:39**
- fim: **02:59:31**
- lotes: **152**
- votos válidos restantes: **18.809.656**

Nos totais inteiros:
- Lula sobe em **152/152** transições;
- Flávio desce em **152/152**.

Composição do pool inteiro restante:
- Lula: **54,0881%**
- Flávio: **39,3429%**
- margem Lula−Flávio: **+14,7452 pp**

Distribuição dos 152 lotes:
- menor share Lula: **47,6753%**
- maior share Flávio: **46,2185%**
- Lula > Flávio em **152/152**
- menor margem Lula−Flávio de qualquer lote: **+2,8307 pp**

### Certificado adversarial de ordem

Para Lula:
- lotes reordenados por share Lula decrescente;
- falhas: **0**
- headroom mínimo ainda positivo: **+2,513611 pp**

Para Flávio:
- lotes reordenados por share Flávio crescente;
- falhas: **0**
- headroom mínimo ainda positivo: **+0,809287 pp**

Resultado:

\[
\boxed{\text{qualquer permutação dos mesmos 152 lotes continua monotônica}}
\]

### Consequência metodológica

A sequência 152/152 não deve ser tratada como 152 lançamentos independentes de moeda.

Condicionado ao conjunto de lotes que restava depois de 20:04:39:
- a ordem observada não é necessária para produzir a monotonicidade;
- o fenômeno está na **composição do conjunto remanescente**.

Portanto a pergunta passa de:
> "por que a ordem das atualizações sempre favoreceu Lula?"

para:
> "por que todos os lotes remanescentes tinham composição mais Lula que Flávio?"

Isso não resolve a causa. Localiza a causa a investigar:
- composição geográfica;
- perfil das zonas/seções que concluem tarde;
- comparação histórica com as mesmas regiões.

---

## 2026-10-05 — E0063 — Inspeção preliminar: zonas que concluem tarde são fortemente mais Lula, também em 2022

**Evento:** cruzamento exploratório entre o horário de conclusão das zonas e a composição final das mesmas zonas.

Fonte:
- \`ArvorCo/PNAD zonas.json\`
- 6.094 zonas completas.

### Corte 20:04:39

Zonas que só concluíram depois:
- **2.732 zonas**
- votos válidos finais dessas zonas: **65.132.802**
- Lula 2026: **50,98%**
- Flávio 2026: **41,87%**
- margem Lula−Flávio: **+9,11 pp**

As mesmas zonas em 2022:
- Lula: **54,10%**
- Bolsonaro: **38,06%**
- margem: **+16,04 pp**

Zonas já concluídas até 20:04:
- Lula 2026: **38,06%**
- Flávio: **53,34%**
- margem Lula−Flávio: **−15,28 pp**

### Cortes progressivamente mais tardios

Zonas que concluíram depois de 20:30:
- Lula 2026: **52,90%**
- Flávio: **40,23%**
- margem: **+12,67 pp**
- mesmas zonas em 2022: **+19,63 pp** Lula−Bolsonaro

Depois de 21:00:
- Lula: **56,63%**
- Flávio: **37,05%**
- margem: **+19,58 pp**
- mesmas zonas em 2022: **+26,65 pp**

Depois de 22:00:
- Lula: **65,00%**
- Flávio: **30,29%**
- margem: **+34,71 pp**
- mesmas zonas em 2022: **+42,89 pp**

Depois de 00:00:
- Lula: **71,92%**
- Flávio: **24,46%**
- margem: **+47,46 pp**
- mesmas zonas em 2022: **+57,34 pp**

### Limitação crítica

Os **65,1 milhões** de votos finais das zonas que terminaram após 20:04 não são os **18,8 milhões** de votos que entraram depois de 20:04.

Uma zona pode:
- já ter publicado grande parte de suas seções;
- continuar marcada como "não concluída";
- completar apenas quando chega sua última seção.

Logo o horário de conclusão serve para caracterizar a **geografia do conjunto tardio**, não para atribuir todos os votos daquela zona ao período pós-corte.

Mesmo com essa limitação, o padrão histórico é forte:
- quanto mais tarde o corte, mais pró-Lula é o conjunto de zonas que ainda falta concluir;
- as mesmas zonas eram ainda mais pró-Lula em 2022.

---

## 2026-10-05 — E0064 — Implementação da Fase 4H: composição das zonas de conclusão tardia

**Evento:** criação do \`analyze_phase4h_late_zone_composition.py\`.

**Commit:** \`8e7486e125ad8f5453b2ed69977d0c00dbcb5227\`

### Objetivo

Formalizar a inspeção do E0063 e comparar os seguintes cortes:
- 20:04:39
- 20:30:35
- 21:00
- 22:00
- 00:00

Para cada corte:
- grupo EARLY = zonas já concluídas;
- grupo LATE = zonas ainda não concluídas;
- composição ponderada por votos em 2026;
- composição das mesmas zonas em 2022;
- gradiente LATE−EARLY;
- delta do gradiente 2026−2022.

### Relação com a Fase 4G

O relatório também importa o pool real da 4G para deixar explícito que:
- pool real pós-20:04 = **18,8 milhões**;
- votos finais das zonas LATE às 20:04 são muito maiores;
- portanto 4H é análise composicional, não reconstrução histórica exata.

### Busca por série fina de 2022

A busca no GitHub encontrou vários projetos de 2022 que consultavam o endpoint do TSE em tempo real, mas até este ponto **não foi localizada uma série nacional preservada de snapshots com resolução comparável à série 2026**.

Também foi localizado material de 2022 com microdados/horários de recebimento de BU, útil para reconstrução estrutural, mas isso não equivale ao histórico do painel nacional.

A busca permanece aberta; nenhuma afirmação "igual a 2022" será feita sem uma fonte temporal equivalente.

### Próxima ação

Executar a Fase 4H e versionar:
- \`phase4h_late_zone_thresholds.csv\`
- \`phase4h_summary.json\`
---

## 2026-10-05 — E0065 — Resultado da Fase 4H: gradiente tardio quase replica 2022

**Evento:** análise dos resultados versionados da Fase 4H.

**Commit dos resultados:** `009c96db7374b12d21c1e4bea2516e65cdbb4d6a`

### Resultado

Zonas completas analisadas: **6.094**.

No corte de 20:04:39:
- zonas ainda incompletas: **2.732**;
- Lula 2026: **50,98%**;
- Flávio 2026: **41,87%**;
- margem Lula−Flávio: **+9,11 pp**;
- mesmas zonas em 2022: margem Lula−Bolsonaro **+16,04 pp**.

O contraste mais informativo é LATE−EARLY:
- 2026: **+24,39 pp**;
- 2022: **+23,64 pp**;
- delta do gradiente 2026−2022: **+0,75 pp**.

Cortes seguintes:
- 20:30: delta do gradiente **+0,56 pp**;
- 21:00: **+0,21 pp**;
- 22:00: **−1,03 pp**;
- 00:00: **−2,75 pp**.

### Interpretação

O fato de as zonas que concluem mais tarde serem muito mais pró-Lula não é exclusivo de 2026. O mesmo ordenamento geográfico já carregava gradiente semelhante, e em vários cortes ainda maior, em 2022.

Isso fornece uma explicação composicional forte para o pool tardio pró-Lula observado na Fase 4G.

### Limitação decisiva

Os votos finais das zonas ainda incompletas às 20:04 somam **65,13 milhões**, enquanto o pool real restante depois de 20:04:39 é **18,81 milhões**.

Razão: **3,46×**.

Logo a Fase 4H caracteriza a geografia tardia, mas não reconstrói os votos exatos incorporados depois do corte.

### Próxima ação

Auditar a cobertura temporal dos snapshots locais e reconstruir apenas o trecho realmente preservado, sem extrapolação.

---

## 2026-10-05 — E0066 — Implementação da Fase 4I: cobertura local e reconstrução da cauda

**Evento:** criação de `analyze_phase4i_local_tail_coverage.py`.

**Commit:** `79b01690073f67483d61c023403685079633a40b`

Também foi criado o resumo executivo de uma página:
- `docs/ONE_PAGE_INVESTIGACAO.md`
- commit: `89ff1b5dc37b4c7463d2ae6c75272b7769436597`

### Objetivo

Antes de tentar atribuir geograficamente os **18.809.656** votos restantes após 20:04:39, medir exatamente o que os snapshots locais preservam.

A Fase 4I:
1. identifica o snapshot local mais próximo do corte;
2. mede a lacuna temporal entre 20:04:39 e esse snapshot;
3. calcula que fração do pool da Fase 4G está efetivamente coberta;
4. reconstrói por UF a cauda entre o primeiro snapshot útil e o final;
5. reconcilia a soma das UFs contra o delta nacional;
6. marca explicitamente se uma reconstrução geográfica completa do pool 20:04→final é possível com os dados locais.

### Regra metodológica

Se não houver snapshot no corte, o script **não extrapola** os votos faltantes para UFs, municípios ou zonas.

A diferença nacional não coberta é registrada apenas como lacuna aritmética. Para atribuição geográfica determinística será necessário histórico de versões cobrindo o corte, como o banco bruto de um coletor contemporâneo ou fonte temporal equivalente.

### Próxima ação

Executar:

```
python analyze_phase4i_local_tail_coverage.py
```

Depois versionar:
- `data/forensics/analysis/phase4i_local_tail_by_uf.csv`
- `data/forensics/analysis/phase4i_summary.json`

e registrar o resultado antes de decidir a Fase 4J.

---

## 2026-10-05 — E0067 — Resultado da Fase 4I: snapshots locais cobrem apenas 5,31% do pool pós-20:04

**Evento:** execução local de `analyze_phase4i_local_tail_coverage.py`.

### Resultado

- snapshots locais utilizáveis: **8**;
- primeiro snapshot local útil: **21:19:37 BRT**;
- corte alvo: **20:04:39 BRT**;
- lacuna temporal: **74,97 min**;
- cauda coberta localmente: **999.110 votos válidos**;
- cobertura do pool pós-20:04: **5,31%**;
- composição da cauda local:
  - Lula: **67,19%**;
  - Flávio: **28,37%**.

Reconciliação da cauda por UF contra o nacional:
- válidos: **+16.436** BR−somaUF;
- Lula: **+12.382**;
- Flávio: **+3.399**.

Essa diferença é compatível com a limitação já documentada de snapshots não atômicos: BR e UFs foram capturados ao longo de uma janela de minutos.

### Conclusão

Os snapshots locais são insuficientes para reconstruir geograficamente o pool de **18.809.656** votos iniciado às 20:04:39.

A maior parte do intervalo crítico não foi preservada localmente e não deve ser inferida a partir dos 5,31% finais.

---

## 2026-10-05 — E0068 — Descoberta de corte independente às 20:05:57 e implementação da Fase 4J

**Evento:** revisão das fontes contemporâneas já preservadas pela Fase 3B.

Foi identificado que `vitoropereira/eleicoes2026`, no commit fixado
`3f4d7442dd601eb1b11afb8e9510d1373c495e7c`, preserva em
`marcos/75pct/comparacao_fontes.json` os **28 agregados exatos por UF/ZZ**
capturados às **20:05:57 BRT**.

A captura contém por abrangência:
- seções totalizadas;
- votos válidos;
- votos de Flávio;
- votos de Lula.

Soma declarada das UFs no corte:
- **100.819.887 votos válidos**;
- **425.421 seções**.

Comparando com o resultado final de **119.300.788 válidos**, o trecho
20:05:57→final contém **18.480.901 votos válidos**, o que representa
**98,25%** do pool pós-20:04 da Fase 4G.

A parcela não coberta cai para apenas:
- **328.755 votos válidos**;
- **1,75%** do pool;
- janela de **78 segundos**, 20:04:39→20:05:57.

### Implementação

Criado:
- `analyze_phase4j_post_resume_geography.py`

**Commit:** `d56686119a357353e1c728336503e5aad9facb8b`

### Objetivo

Reconstruir deterministicamente por UF a cauda 20:05:57→final, reconciliar o
corte independente, reconciliar o final UF↔BR e medir a composição política e
as maiores contribuições geográficas do trecho que representa 98,25% do pool
pós-retomada.

### Próxima ação

Executar a Fase 4J e versionar seus dois artefatos antes de definir a Fase 4K.

---

## 2026-10-05 — E0069 — Arquitetura formal de proveniência e replay primário

**Evento:** transformação da reprodutibilidade em requisito explícito da investigação.

Foram adicionados:

- provenance/SOURCES.json
- provenance/PHASES.json
- replay_investigation.py
- docs/REPRODUCIBILITY.md

### Regra

Reprodutibilidade matemática e replay com fonte primária passam a ser estados distintos.

Uma fase pode ser perfeitamente reproduzível a partir de uma captura externa fixada por commit/hash e ainda permanecer marcada como PRIMARY-GAP.

### Política de substituição

Quando uma fonte primária histórica equivalente for obtida:

1. preservar o bruto e seu SHA-256;
2. manter a captura externa original;
3. normalizar ambas para o mesmo contrato de dados;
4. rerodar a fase afetada e todas as dependentes;
5. produzir diff quantitativo antigo × primário;
6. revisar conclusões somente depois desse confronto.

### Arquitetura-alvo

RAW imutável → CANONICAL → ANALYSIS → REPORT.

O trabalho futuro de recuperação das fontes primárias deve alimentar a camada RAW/CANONICAL, sem alterar a matemática dos testes.

### Prioridade primária

A maior lacuna atual é o histórico oficial de versões EA20 durante a noite da apuração, especialmente nacional/UF e depois município/zona no entorno de 20:04.

As capturas ArvorCo e Vitor permanecem como controles independentes, mesmo depois de eventual substituição por fonte primária.


---

## 2026-10-16 — E0070 — Retomada da coleta primária por seção e correção do diagnóstico de disponibilidade

**Evento:** migração da investigação para análise de Boletins de Urna, votação por
seção e arquivos de urna transmitidos (BU/RDV/log/vota).

**Contexto:** a primeira coleta, iniciada em 05/10, pesquisava sobretudo o
catálogo de Dados Abertos (CKAN). A ausência de recursos identificados por esse
mecanismo não estabelecia indisponibilidade geral dos documentos no sistema
Resultados. O próprio diário já registrara essa correção em E0011.

**Alteração da metodologia:** os arquivos do portal e os produtos de votação
por seção passam a ser procurados por recursos de catálogo específicos e pela
estrutura `arquivo-urna` descoberta na Fase 2.

**Código:** `urnas.py`, integrado a `collect_forensics.py` e ao
`start_windows.bat`; arquivos volumosos no drive H:, uso de cache,
downloads retomáveis e SHA-256.

**Cuidado histórico:** nesta entrada não são atribuídas datas novas de
disponibilidade a todos os tipos de arquivos, nem se presume que a coleta
integral tenha terminado. A disponibilidade de recursos deve ser comprovada
pelos metadados efetivamente preservados e pelo manifesto de download local.

**Próxima ação:** conciliar BUs e votação por seção; documentar cobertura e
quais tipos de arquivo foram de fato baixados e interpretados.

---

## 2026-10-16 — E0071 — Bateria estatística incorporada à coleta completa

**Evento:** criação de `statistical_forensics.py` e da documentação
`docs/METODOS_ESTATISTICOS_2026.md`.

**Testes exploratórios implementados:**
- Benford (primeiro e segundo dígitos), quando as contagens passam por
  condições mínimas de tamanho e dispersão;
- dígitos finais e frequências de 0/5;
- assimetria e curtose por município;
- desvios robustos por mediana e MAD;
- correlação entre participação e fração de votos;
- histograma bivariado participação × voto;
- testes contábeis preliminares por seção.

**Regra:** são indicadores de triagem. Desvios estatísticos não constituem
automaticamente prova de fraude. As métricas devem ser confrontadas com
seções semelhantes, fontes independentes e hipótese nula plausível.

**Limitação:** a implementação atual trabalha principalmente com CSVs de
BU para Presidente; RDV e log binários ainda carecem de interpretação de
seu conteúdo. Testes temporais e inferências com modelos simulados seguem
como etapas futuras.

**Saída prevista:** `H:/TSE/forensics/urnas/analysis/estatistica/`.

**Status neste evento:** implementação e testes no repositório; nenhum
resultado estatístico da coleta integral real foi validado nesta entrada.

---

## 2026-10-16 — E0072 — Histórico permanente de resultados e preparação do segundo artigo

**Motivação:** a execução anterior gerava arquivos de saída nomeados como
`latest`, que poderiam ser substituídos por execuções posteriores. O
histórico do código no Git não é suficiente para preservar os resultados
analíticos calculados a partir de cada versão do banco.

**Mudança:** criado `history_forensics.py`. A coleta de urnas e os
comandos de análise agora executam preservação **antes e depois**
dos cálculos. Cada etapa cria um manifesto separado em
`H:/TSE/forensics/urnas/analysis/history/runs/` com:
- ID exclusivo e hora UTC da captura;
- nomes, tamanhos e SHA-256 de cada relatório preservado;
- versão Git e SHA-256 dos scripts principais;
- SHA-256 das fontes já registradas na tabela de importações;
- etapa e parâmetros resumidos da execução.

**Armazenamento:** o conteúdo dos relatórios é guardado em objetos
compactados identificados por SHA-256 sob `history/objects/`.
Relatórios idênticos entre execuções reutilizam o mesmo objeto e
recebem apenas novos manifestos. O `history/ledger.jsonl` é append-only.
Não são duplicados os ZIPs brutos e nem o banco SQLite vivo.

**Limite:** conservar hashes da tabela de importações não constitui uma
fotografia transacional de todo o banco SQLite. Para replay integral,
permanecem indispensáveis os dados brutos preservados e a versão do parser.
O mecanismo começa a operar nas execuções feitas **depois** da atualização
do código; não recupera automaticamente relatórios substituídos antes dela.

**Artigo:** preservado sem alterações o primeiro
`docs/ARTIGO_PUBLICO.md`; criado
`docs/ARTIGO_02_PLANO.md` como roteiro ainda não publicável,
com questões, evidências pendentes e limites explícitos.

**Regra:** alterações e análises continuam diretamente na `main`;
resultados locais verificáveis serão registrados aqui em eventos
posteriores. Não serão inventadas conclusões sobre os BUs sem ler o
resultado da coleta concluída.

**Próxima entrada esperada:** confirmação da conclusão do download com
quantidade de seções, arquivos, erros, hashes e primeiro resultado de
reconciliação BU ↔ seção, vinculados ao ID do snapshot histórico.


---

## 2026-10-17 — E0073 — Execucao incompleta em arquivo nacional e interrupcao de terminal

**Fonte da observacao:** copia do texto do terminal, entregue pelo
investigador em 17/10/2026. O arquivo de log recebido termina antes de
`[1/113]` (na lista de recursos disponiveis), logo nao comprova o
ponto exato de bloqueio da tentativa atual.

**Constatado no registro:**
- oito snapshots locais, 5.785/5.785 JSONs, 100% do resultado final;
- portal: 312 arquivos reutilizados, nenhum download novo, zero erros;
- catalogo de urna: 113 recursos selecionados;
- entre esses recursos, 56 documentos BU/hash, 2 arquivos nacionais de
  votacao/detalhe por secao, 27 arquivos estaduais de votacao por secao,
  28 arquivos transmitidos por UF/ZZ;
- na listagem, os 56 BU/hash e os dois arquivos nacionais aparecem
  `LOCAL`, os 27 estaduais e 28 transmitidos aparecem `REMOTO`.
  `LOCAL` significa que o destino existe, **nao confirma importacao**
  em SQLite nem sua validacao nesta tentativa.

**Relato independente do investigador:** numa execucao anterior, a
progressao chegou ao recurso 58 de aproximadamente 113. O usuario
precisou fechar a janela porque `Ctrl+C` nao produziu interrupcao
visivel. O recurso 58 e, na ordem observada, o CSV nacional de
votacao por secao de Presidente. Processar esse arquivo pode
exigir muitos inserts SQLite. **Hipotese tecnica a testar:** a ausencia
de progresso visivel e uma transacao unica de importacao ou
(re)construcao de indices resultaram em longa espera. O log fornecido
nao possui tempos/profiler para confirmar a causa.

**Correcao do coletor, publicada diretamente na `main`:**
- criado `run_control.py`, com etapa atual, relatorio periodico
  durante tarefas longas (15 s) e tratamento de `Ctrl+C` e
  `Ctrl+Break` no Windows;
- `collect_forensics.py` e `urnas.py` propagam a interrupcao com
  codigo de saida 130; dados integrais e parciais `.part` permanecem;
- inicio e fim do preparo dos indices SQLite passam a ser anunciados,
  para separar atraso de download e atraso de importacao;
- cache de SHA/ZIP validado anteriormente pode ser reutilizado sem
  recalcular todo o CRC se arquivo/tamanho/data de modificacao e
  metadados permanecerem identicos; opcao `verify` recalcula SHA;
- `import_file` passa a registrar checkpoints SQLite de 20.000
  linhas por arquivo CSV, confirmando cada bloco; uma interrupcao
  preserva as transacoes ja confirmadas;
- na retomada, um checkpoint do mesmo recurso/SHA reaproveita linhas
  ja importadas sem duplicacao; importacoes v2 completas tambem sao
  reutilizadas, evitando reindexacao em massa;
- `history_forensics.py` passa a indicar qual relatorio esta
  arquivando antes de uma nova tentativa.

**Testes previstos/implementados:** dados sinteticos de 25 mil linhas
com checkpoint de 20 mil, retomada das 5 mil restantes e confirmacao
de ausencia de duplicacao; reutilizacao de importacoes anteriores.
A integracao com o volume real dos dados ainda exige a nova execucao
no ambiente Windows/H:.

**Limite:** nao existe aqui acesso ao drive H: do investigador,
portanto nao afirmamos que os 113 recursos foram baixados ou que a
causa exata de bloqueio foi comprovada.

**Proxima verificacao:** observar qual etapa permanece visivel,
quantidade indexada e manifestos em
`H:/TSE/forensics/urnas/analysis/history/` e
`H:/TSE/forensics/urnas/download_manifest_latest.json`
durante a proxima execucao. Nenhum dado previo deve ser apagado.


---

## 2026-10-22 — E0074 — Reconciliação nacional sem progresso: 9.335 segundos

**Evidência fornecida pelo investigador:** a opção de coleta completa
permaneceu pelo menos **9.335 segundos (2h35min35s)** na mensagem
`reconciliacao automatica BU x votacao por secao`, com atualização de
tempo decorrido a cada 15 segundos, sem previsão de conclusão.

**Diagnóstico do código anterior:** `urnas.py:reconcile()` construía
uma consulta SQLite única, com agregação nacional, junções e varredura
dos registros entre BU e votação por seção. O resultado era gerado
ao percorrer esse cursor e não havia checkpoints por UF/zona.
**O tempo decorrido não permite afirmar quanto faltava.** Também não
comprova, isoladamente, travamento do computador ou erro nos votos.

**Limite decisivo da retomada:** interromper aquela versão preserva
ZIPs, dados importados e relatórios anteriores, mas não possibilita
retomar no meio da consulta única; não há como recuperar os passos
intermediários não registrados. É indispensável uma versão
nova para conservar trabalho de reconciliação a partir de agora.

**Mudança implementada na `main`:**
- criado `reconcile_incremental.py`, acionado tanto na coleta
  completa quanto no comando `urnas.py reconcile`;
- grupos de trabalho separados por UF/município/zona/turno;
- cada grupo concluído é persistido em CSV com SHA-256 e
  checkpoint SQLite, sem apagar os grupos de execuções anteriores;
- a identidade das fontes é estabelecida por hash dos recursos
  importados, versão da lógica, escopo e contagens elegíveis;
- o programa informa fração dos grupos e das linhas, divergências,
  partes reutilizadas e uma estimativa aproximada de tempo restante
  baseada na velocidade dos grupos novos, após amostra inicial;
- o CSV final só substitui a versão anterior quando **todas**
  as zonas forem concluídas e consolidadas;
- o menu opção 6 realiza apenas a reconciliação local, sem iniciar
  downloads novamente, e serve para retomar checkpoints;
- importações incompletas são declaradas nos metadados da análise;
- testes com entradas sintéticas reproduzem cancelamento após uma
  zona, retomada das demais e invalidação do cache se o SHA das
  fontes for alterado.

**Estado de verificação:** não há neste registro resultados calculados
na base real do investigador após a atualização. A velocidade futura
é desconhecida antes de processar os primeiros grupos reais. A
estimativa é operacional, não previsão estatística de tempo garantida.

**Evidência do próximo ensaio:** guardar do console as mensagens
`PLANO PRONTO`, `PROGRESSO RECONCILIACAO` e
`reconciliacao_bu_secao.summary.json`, assim como o hash das entradas.


---

## 2026-10-23 — E0075 — Resultado de conciliacao e estatistica, com uma fonte em erro

**Evidencia recebida:** final do log de execucao fornecido pelo investigador,
incluindo o resumo de reconciliacao, a bateria estatistica e o manifesto do
historico. O arquivo de log encaminhado **nao inclui a mensagem especifica do
recurso que falhou**; a causa nao deve ser adivinhada.

**Resultado calculado pelo programa no ambiente do investigador:**
- 113 recursos oficiais selecionados, 112 reutilizados, 0 novos;
- 1 recurso com erro, a identificar em
  `H:/TSE/forensics/urnas/download_manifest_latest.json`;
- 67.858.974 chaves de comparacao BU versus votacao por secao;
- 64.058.235 chaves coincidentes;
- 3.800.739 chaves em `SEM_SECAO`;
- 0 chaves em `SEM_BU`;
- 0 chaves em `DIFERENTE` por diferenca numerica entre duas
  chaves correspondentes, conforme os totais do resumo;
- bateria estatistica: 499.206 secoes, 1.387 valores extremos
  locais e 0 secoes com candidato duplicado na verificacao;
- 14 relatorios preservados no snapshot
  `20261023T021123576322Z-066fc88b7f`, incluindo CSV de
  reconciliacao de 145.665.711 bytes.

**Interpretacao limitada:** `SEM_SECAO` e uma chave de
comparacao ausente na fonte `secao` indexada. Nao equivale a
secoes fisicas inexistentes, votos eliminados ou fraude. Os pares
de chaves efetivamente comparados fecharam na medida reportada.
Ainda e necessario medir a distribuicao dos casos por
UF/cargo/turno e identificar o recurso com falha. A analise nao
confirma cobertura nacional completa apenas por contar
499.206 secoes.

**Observacao do fluxo:** o log recebido mostra o formato de
reconciliacao antigo, com `keys_compared` e `limitations` e
sem campos `engine`, `fingerprint` ou `tasks_completed`.
A execucao **nao demonstra uso do novo reconciliador
incremental**; pode ter sido iniciada antes do update.

**Ajuste de investigacao:** criado `diagnose_forensics.py`,
ligado ao menu opcao 9, que le o manifesto e os relatorios
existentes sem download nem recalculo. Produz
`analysis/diagnostico_execucao.json`, descreve a mensagem do erro
e agrega `SEM_SECAO` por UF, turno e cargo. A classificacao
dos dados de origem deve preceder qualquer conclusao a publicar
no segundo artigo.

**Verificacao pendente:** diagnostico dos arquivos locais reais
e conferência do recurso em erro no manifesto. A ausencia de
acesso remoto ao drive H: impede concluir esses itens neste evento.


---

## 2026-10-23 — E0076 — Identificacao da fonte nacional de Presidente excluida da reconciliacao

**Evidencia nova do investigador:** `diagnostico_execucao.json`, extraido
do banco e relatorios locais, com 113 recursos selecionados e processados,
112 reutilizados, 1 falha no ZIP de artefatos transmitidos SP.

**Reconstrucao do resultado anterior:**
- 67.858.974 chaves de cargo/candidato/secao comparadas;
- 64.058.235 com igualdade numérica;
- 3.800.739 `SEM_SECAO`, zero `SEM_BU`;
- todas as chaves ausentes no primeiro turno;
- 3.800.511 chaves de `cargo=1` (Presidente), espalhadas por
  todas as UFs e exterior;
- 228 chaves de `cargo=25`, exclusivamente Pernambuco.

**Causa identificada no código, nao ainda comprovada na base real:**
a versao anterior de `reconcile()` selecionava somente
`source_kind='bu'` e `source_kind='secao'`. O proprio coletor
classifica o conjunto nacional de **Presidente por secao eleitoral**
em uma terceira categoria, `source_kind='secao_nacional'`, para
evitar duplicidade de votos. Esse arquivo nacional era portanto
**excluido da comparacao**, produzindo ausencia de contrapartida
principalmente em `cargo=1`.

**Correcao de lógica:** `reconcile_incremental.py` v2 inclui o
`secao_nacional` somente no cargo 1; usa a fonte estadual
`secao` com prioridade por chave (UF, municipio, zona, secao,
turno, cargo, votavel) e o arquivo nacional somente como
complemento de chaves inexistentes. **Nunca soma as duas fontes**.
A versao v2 invalida automaticamente checkpoints antigos por
incorporar o numero da versao na impressao digital das fontes.

**Limite da inferencia:** a classificacao de 3.800.511 chaves
presidenciais como lacuna de comparacao e um diagnostico da
logica de software, nao significa que todas serao conciliadas.
Ainda e necessario confirmar que o arquivo nacional esta
efetivamente importado no SQLite, verificar seu layout, repetir
a reconciliacao e medir os casos residuais.

**Cargo 25 - contexto externo:** a Eleicao Municipal de
Fernando de Noronha (PE) de 04/10/2026 incluiu votacao para
Conselho Distrital, documentada pelo TSE e TRE-PE em 05/10/2026.
O cargo 25 e pertencente a esse pleito local, nao Presidente.
Os 228 registros sem contraparte precisam ser confrontados com
o conjunto adequado desse pleito, sem contaminar o indice de
discrepancias do cargo 1.

Fontes primarias:
- https://www.tse.jus.br/comunicacao/noticias/2026/Outubro/eleitores-de-fernando-de-noronha-elegem-7-conselheiros-distritais
- https://www.tre-pe.jus.br/comunicacao/noticias/2026/Outubro/eleitores-de-fernando-de-noronha-elegem-7-conselheiros-distritais

**Proximo teste:** confirmar importacao `secao_nacional` com
`diagnose_forensics.py`; executar reconciliacao revisada e comparar
resultado anterior e novo por UF/cargo. O CSV antigo e seus hashes
permanecem no snapshot de historico
`20261023T021123576322Z-066fc88b7f`.

---

## 2026-10-23 — E0077 — Recuperacao segura do ZIP de artefatos de Sao Paulo

**Erro original literal:** `Arquivo incompleto, corrompido ou ZIP com
CRC invalido`, no arquivo parcial
`bu_imgbu_logjez_rdv_vscmr_2026_1t_SP.zip.part`.

**Observacao:** esse arquivo pertence ao conjunto
`artefatos` transmitidos de SP (BU binarios, RDV, log etc.).
A falha de CRC nao e uma divergencia de votos nem explica o
padrao nacional de `SEM_SECAO` do reconciliador, que consulta
os conjuntos CSV separadamente.

**Alteracoes no codigo:**
- download com CRC/SHA falho passa a mover o arquivo suspeito para
  `H:/TSE/forensics/urnas/quarantine/artefatos/SP/` com hash e
  motivo, sem o destruir;
- tenta novamente uma transferencia integral desde o zero,
  no maximo uma segunda tentativa automatica;
- preserva a segunda copia caso tambem seja invalida, sem laço infinito;
- comando `python urnas.py repair` e **opcao A do menu** executam
  somente os recursos em erro no manifesto anterior;
- o reparo importa apenas os arquivos recuperados (nao refaz
  conciliacao de dezenas de milhoes de chaves nem estatistica);
- manifesta o reparo e grava snapshot historico apos conclusao.

**Proxima verificacao:** resultado da tentativa no ambiente Windows
do investigador. Sem acesso ao drive H: nao e possivel afirmar que
o ZIP de SP esteja integro, recuperado ou indexado.


---

## 2026-10-23 — E0078 — Confirmacao da fonte nacional no SQLite

**Evidencia:** saida literal de `python diagnose_forensics.py --quick`
apos `git pull` (fast-forward de `8e1966b` para `17faaae` na
`main`), compartilhada pelo investigador. O comando foi executado
duas vezes com os mesmos contadores.

**Inventario confirmado pela tabela `imports` do banco local:**

| Fonte | Recursos | Linhas |
| --- | ---: | ---: |
| `bu` | 56 | 67.858.974 |
| `secao` | 27 | 64.058.235 |
| `secao_nacional` | 1 | 3.800.511 |

As linhas de `secao` e `secao_nacional` totalizam **67.858.746**,
exatamente **228** a menos que as linhas de `bu` registradas.
O diagnostico anterior mostrou **3.800.511** chaves `SEM_SECAO`
de cargo 1 (Presidente) e **228** de cargo 25, somente em PE.

**Conclusao tecnica sustentada:** o arquivo nacional presidencial
**esta importado** e a exclusao de `source_kind='secao_nacional'`
pela versao anterior do reconciliador explica o padrao quantitativo
dos `SEM_SECAO`. Ha correspondencia **numerica dos contadores**
com a soma das fontes; falta verificar **chave por chave e voto por
voto agregado em cada chave** com o reconciliador v2. Nao publicar
a igualdade de contadores como conciliacao eleitoral concluida.

**Estado do erro independente:** o arquivo de artefatos transmitidos
de SP continua em `erro` por CRC invalido segundo o manifesto
anterior. O reparo `urnas.py repair` ainda nao foi executado ou
comprovado nesta entrada.

**Proximas etapas:** `python urnas.py reconcile` para reprocessar
as chaves usando a fonte nacional com prioridade da estadual,
checkpoint por zona e ETA aproximada; comparar com o resumo antigo,
sem apagar seus 14 relatorios historicos; `python urnas.py repair`
isoladamente para recuperar o ZIP de SP. Registrar o resultado real
e eventuais chaves remanescentes numa nova entrada.


---

## 2026-10-23 — E0079 — Gargalo de reconciliação: previsão de 180 horas; novo motor indexado

**Registro da execução:** amostra do terminal encaminhada pelo investigador.
A operação `python urnas.py reconcile` mostra progresso de
80/6.251 a 152/6.251 zonas; a estimativa variou de 189h15min a
164h56min, voltou a ultrapassar 180h. O contador da etapa chegou
a mais de 14 mil segundos. Muitas zonas de AM demoravam
consideravelmente mais que as de AL. A operação reportou zero
divergências nas primeiras zonas; isso é um resultado parcial,
não confirmação nacional.

**Diagnóstico de desempenho pelo código-fonte:** o algoritmo
incremental v2 utilizava para cada uma das 6.251 zonas
`WITH grouped`, agregação, anti-join e junções à esquerda
entre três fontes. O padrão pode repetir operações caras de
ordenação e criação de estruturas temporárias no SQLite.
Aumentar processos sem eliminar o trabalho repetido é arriscado,
sobretudo com disco H: possivelmente limitado por I/O.

**Melhoria publicada diretamente na `main`:**
- criado `reconcile_fast.py`: uma leitura por zona usando o índice
  `idx_votes_lookup`, agregação por chave em memória e comparação
  direta BU/estadual/nacional, sem criar e juntar tabelas SQL por zona;
- `reconcile_incremental.py` preserva o fingerprint lógico v2, assim
  os checkpoints concluídos antes da atualização continuam válidos
  após verificação SHA-256;
- habilitados 1 a 8 processos independentes, padrão 4, fila limitada.
  O ajuste serve para aproveitar CPU multicore, mas o rendimento
  efetivo dependerá do disco. `--workers 2` é alternativa se o
  acesso H: ficar saturado;
- cache versionado e comprimido do planejamento de zonas, associado
  à revisão SHA-256 das entradas e aos parâmetros da consulta. Evita
  repetir o `GROUP BY` nacional ao retomar execução equivalente;
- ETA de processamento paralelo baseado no tempo real de parede,
  não na soma do tempo simultâneo dos trabalhadores;
- relatório final só é consolidado quando todas as zonas terminam,
  mantendo versão anterior intacta durante cálculos parciais.

**Testes adicionados:** equivalência sintética entre cálculo SQL
anterior e novo método em cada zona; prioridade estadual em presença
de cópia nacional; cache de planejamento; subprocessos paralelos
lendo base SQLite; reuso de checkpoints. Execução completa no drive H:
não foi observada diretamente e precisa de confirmação na máquina.

**Orientação operacional:** parar com Q/Ctrl+C, encerrar processo
antes de atualizar o código, executar `git pull` e
`python urnas.py reconcile --workers 4`. Nenhum download
nem reimportação de dados são necessários para a nova reconciliação.
Não excluir SQLite, ZIP ou checkpoints; monitorar 20 a 50 zonas novas,
reavaliar ETA e utilização do disco antes de escolher quantidade
de trabalhadores.

**Cautela:** a meta é eliminar um gargalo técnico do algoritmo,
não fabricar um resultado eleitoral. Comparações e fontes permanecem
as mesmas, e a medida de desempenho na base real ainda está pendente.


---

## 2026-10-23 — E0080 — Ausencia de comprovacao de progresso na execucao multiprocessada

**Evidencia compartilhada:** execucao literal de
`python urnas.py reconcile --workers 5`. Iniciou com
`HISTORICO antes-reconcile` (15 relatorios) e concluiu
a consulta nacional de planejamento em **3.639,6 s**,
enumerando 6.251 grupos e 135.717.720 linhas elegiveis.
Gravou o plano compactado em
`analysis/reconciliacao_checkpoints/plans/8633061accf908c836f25b61720cf06d0af2776f07d39a5d3faa1da63b9e29cd.json.gz`.

Depois anunciou cinco processos paralelos e reutilizou
pelo menos **160 checkpoints existentes**, com zero divergencias
nos grupos reutilizados. O log continuou ate **6.933 s**
de tempo na etapa, sem mensagem de nova zona concluida,
sem identificacao de PID dos workers e sem progresso novo
mensuravel. Isto **nao comprova a aceleracao anunciada**.
A mera existencia da mensagem `PROCESSAMENTO: 5 processos`
nao demonstra que os workers executaram e terminaram consultas.

**Analise tecnica:** a revisao do agendador identificou duas
fontes de opacidade: leitura/verificacao dos 6.251 checkpoints
um a um com consultas individuais ao banco H: e ausencia de
telemetria do inicio de cada tarefa ou da linha lida ate que
um processo devolvesse a zona concluida. O log nao permite
determinar se o bloqueio ocorreu na varredura de checkpoints,
inicializacao de subprocessos ou consulta SQLite. O drive H:
e uma hipotese de gargalo, nao causa comprovada.

**Correcao publicada na `main`:**
- carregar o cadastro SQLite dos checkpoints de uma vez e
  conferir hashes com contador `[CHECKPOINTS] n/6251`,
  reduzindo milhares de pequenas consultas ao drive H:;
- imprimir `[FASE]` ao preparar tarefas,
  `[ZONA SUBMETIDA]` ao enviar ao executor e
  `[ZONA CONCLUIDA]` apenas depois de receber resultado real;
- o worker imprime PID, abertura do SQLite,
  `[WORKER BUSCA]` e `[WORKER LENDO]` a cada 20 segundos
  quando houver linhas sendo recebidas; mensagem
  `[WORKER SQLITE ATIVO]` quando a maquina virtual ainda
  executa o SQL;
- a cada 30 segundos sem zona concluida, o processo pai
  informa `[SEM RESULTADO]`, a quantidade de tarefas ativas
  e a idade das mais antigas.

**Orientacao segura:** encerrar a execucao antiga antes do
`git pull`; nao apagar bancos, ZIPs, planos e checkpoints.
Reiniciar **com 1 processo para diagnostico**:
`python urnas.py reconcile --workers 1`, verificando
a primeira zona nova e cronometro. Se houver conclusoes
rapidas e estabilidade de I/O, tentar 2 e depois 4 processos,
sem rodar instancias simultaneas do reconciliador.

**Limite:** o comportamento real da proxima execucao precisa
ser observado antes de afirmar ganho. O saldo de 3.800.511
chaves presidenciais segue em verificacao; nao foi calculado
nenhum novo resultado nacional nessa execucao multiprocessada.


---

## 2026-10-23 — E0081 — Teste de execucao real por duas zonas e telemetria dos workers

**Evidencia:** o log do investigador para `--workers 5` registrou
plano criado apos 3.639,6 segundos, 6.251 zonas, 135.717.720
linhas e pelo menos 160 checkpoints anteriores reconhecidos;
depois disso, nenhum grupo novo foi confirmado ate 6.933
segundos na etapa, cerca de 55 minutos apos o plano. A existencia
de cinco processos anunciados nao e prova de trabalho completo.

**Correcao de desempenho e observabilidade:** a versao agora
consulta a tabela de checkpoints em uma unica consulta,
conservando verificacao individual dos hashes; anuncia andamento
a cada 500 zonas; imprime envio, PID, abertura SQLite,
atividade de VM, linhas recebidas e conclusao por zona;
detecta intervalos de 30 segundos sem resultado dos processos.
No cancelamento da versao nova, encerra os trabalhadores
paralelos de leitura para evitar processos antigos no H:.

**Instrumento de confirmacao:** `reconcile_probe.py` usa o
plano comprimido salvo no primeiro ensaio e escolhe duas
zonas representativas de tamanhos diferentes. Executa
`EXPLAIN QUERY PLAN` e a mesma rotina de comparação
indexada, em SQLite read-only, com medicao de tempo,
chaves comparadas e divergencias. CSVs do teste sao
temporarios e nao alteram os relatorios nem os checkpoints.
Limite padrao de 120 segundos de execucao da VM SQLite
por zona (sujeito a bloqueio de I/O fora do controle da VM).

**Teste ainda pendente:** rodar o probe no H: sem outra
instancia ativa. Uma conclusao da zona com numeros e
tempo demonstra que o algoritmo calcula uma zona real;
somente medicao de varias zonas representativas permite
estimar throughput nacional. Nao existe ainda evidencia
de ganho de desempenho da consulta otimizada no H:.


---

## 2026-10-23 — E0082 — Probe comprova primeira zona

**Evidência recebida:** saída parcial de `python reconcile_probe.py --budget 120`
executado sobre o SQLite real do investigador no volume H:.

- Plano de comparação já existente: 6.251 zonas, arquivo de plano SHA
  `8633061accf908c836f25b61720cf06d0af2776f07d39a5d3faa1da63b9e29cd.json.gz`;
- Primeira zona `SC/80446/83/1`: 1.958 linhas na consulta;
  `EXPLAIN QUERY PLAN` indica `SEARCH votes USING INDEX idx_votes_lookup
  (uf=? AND municipio=? AND zona=?)`, **não** `COVERING INDEX`;
  979 chaves comparadas, zero divergências, 16,8 s de parede,
  com confirmação `[WORKER OK]` e `ZONA REAL CONCLUIDA`;
- Segunda zona `PR/79693/135/1`: 6.912 linhas estimadas no plano;
  índice `idx_votes_lookup` confirmado; após 20 s,
  1.198 linhas lidas; aos 29 s houve atividade do motor SQLite.
  **O trecho recebido termina antes do resultado final da segunda zona.**

**Conclusão delimitada:** o motor otimizado comprovadamente executa e
termina uma consulta real, com validação das chaves da primeira zona.
Ainda não foi demonstrada aceleração nacional, nem ganho da execução
com cinco processos. A latência de cerca de 16,8 s para 1.958 linhas
é alta. A ausência da palavra `COVERING` no plano é compatível com
buscas adicionais na tabela principal; este é um gargalo **possível,
não comprovado**. É necessário comparar planos de acesso e tempo de
I/O de alternativas antes de construir novos índices gigantescos.

**Próxima ação técnica:** não relançar a comparação completa
imediatamente; observar o fim (ou limite) da segunda zona do probe,
medir uma solução de acesso sequencial/materialização reduzida
ou índice cobridor para subconjunto antes de adotar uma migração
nacional. Nenhum dado foi alterado pelo probe.


---

## 2026-10-23 — E0083 — Duas zonas reais concluidas; medida do gargalo de leitura

**Evidencia recebida:** conclusao integral de
`python reconcile_probe.py --budget 120` sobre o
SQLite no volume H: do investigador.

Resultados do motor de comparacao atual em amostras reais:

| Zona | Linhas lidas | Chaves comparadas | Divergencias | Tempo |
| --- | ---: | ---: | ---: | ---: |
| SC/80446/83/1 | 1.958 | 979 | 0 | 16,8 s |
| PR/79693/135/1 | 6.912 | 3.456 | 0 | 102,1 s |

Em ambas `EXPLAIN QUERY PLAN` indicou
`SEARCH votes USING INDEX idx_votes_lookup
(uf=? AND municipio=? AND zona=?)`. Nao indicou
`COVERING INDEX`; portanto os valores solicitados,
como `votos` e `source_kind`, podem necessitar
leituras adicionais na tabela. A hipotese de I/O
aleatorio dispendioso em drive H: e plausivel,
**mas ainda depende de contraste com leitura sequencial
para ser confirmada**.

As duas amostras somam 4.435 chaves, todas coincidentes.
Amostras locais com divergencia zero nao permitem
extrapolacao para o pleito inteiro. O teste comprovou
a completude do calculo dessas zonas, nao que a
execucao multiprocessada seja mais rapida.

**Medicao seguinte adicionada a main:**
`reconcile_io_probe.py`, teste somente leitura.
Mede tres janelas representativas de `rowid`
(inicio/meio/fim da tabela), utilizando
`SELECT ... FROM votes NOT INDEXED
WHERE rowid>=? LIMIT ?`, com o MESMO conjunto
de colunas da consulta por zona. Exibe
tamanho do arquivo SQLite, espaco livre em H:,
`EXPLAIN QUERY PLAN`, velocidade de linhas/s
e interrupcao por limite de tempo de instrucao
SQL. Usa duas pesquisas de rowid com LIMIT 1,
evitando um `MIN+MAX` que poderia varrer
135 milhoes de linhas. Nao cria indices,
nao regrava o banco e nao modifica checkpoints.

**Criterio para escolher a proxima arquitetura:**
se a leitura por `rowid` for substancialmente
mais rapida nas tres partes do banco e houver
espaco livre adequado para arquivos intermediarios,
priorizar um pipeline de varredura unica com
particionamento seguro e reconciliacao offline
dos grupos; caso contrario investigar mais o
hardware, a base SQLite, page cache e indices.
Nao construir automaticamente indice cobridor
nacional de dezenas de milhoes de registros,
sem prever custo, espaco e verificação.


---

## 2026-10-23 — E0084 — Benchmark sequencial confirma vantagem local; motor externo retomavel

**Dados efetivamente medidos no H: do investigador:**

- SQLite original: **221,24 GiB**;
- espaco livre no volume H: **1.711,45 GiB**;
- consulta de amostras por `rowid` em `votes NOT INDEXED`;
- `inicio`: 50.000 linhas em 1,09 s, **45.745,7 linhas/s**;
- `meio`: 50.000 linhas em 0,78 s, **63.938,6 linhas/s**;
- `fim`: 50.000 linhas em 0,09 s, **537.634,4 linhas/s**
  (provavelmente favorecida por cache; nao extrapolar);
- SQLite confirmou `SEARCH votes USING INTEGER PRIMARY KEY (rowid>?)`
  nos tres pontos.

Em comparacao, os probes indexados por zona retornaram
68–117 linhas/s. A discrepancia de ordens de grandeza
justifica abandonar esse padrao de acesso para o trabalho
nacional. **A medicao de 50 mil linhas nao garante a
velocidade sustentada sobre todos os 140 milhoes de registros.**

**Implementacao iniciada e publicada na `main`:**

- novo `reconcile_stream.py` (engine `reconcile-stream-v1`);
- varredura unica de SQLite por `rowid`, selecionando os
  nove campos estritamente necessarios, sem `dados_json`;
- normalizacao de UF, municipio, zona, secao, turno,
  cargo e votavel conforme regras de reconciliacao;
- distribuicao deterministica em 256 particoes TSV por hash
  de (UF, municipio, zona, turno);
- checkpoints com offsets, rowid, total de linhas examinadas,
  fsync antes de salvar o estado, retomada que descarta
  escritos nao confirmados; arquivos fisicos preservados;
- selagem SHA-256 das particoes antes da comparacao;
- comparacao de chaves por particao, com `secao`
  estadual prevalecendo sobre `secao_nacional` de Presidente
  sem somar a mesma chave duas vezes;
- resultado de cada particao com digest/checkpoint independente;
  consolidacao atomica do CSV ao concluir todas;
- bloqueio entre processos para nao executar a mesma
  sessao stream duas vezes em paralelo;
- mecanismo de piloto `--pilot-rows` que nao substitui
  o relatorio nem cria historico redundante;
- `urnas.py reconcile` e opcao 6 do menu usam
  stream por padrao; metodo `--engine zones` permanece
  disponivel e todos seus checkpoints permanecem intactos;
- testes sinteticos incluidos para equivalencia com
  reconciliador antigo, duplicatas, fontes presidenciais,
  divergencias, interrupcao no scan/particoes, SHA e
  mudanca dos recursos importados.

**Estado da confianca:** a implementacao foi publicada no
codigo, mas **ainda nao foi executada sobre H: neste registro**,
e nao ha confirmacao de GitHub Actions concluidos. Nao
afirmar que a reconciliacao nacional foi acelerada nem
que a integridade do resultado final foi confirmada.
A proxima evidencia exigida e a saida do teste offline
mais o piloto de 1.000.000 linhas em 4 checkpoints de
250.000 linhas, que mostrara a velocidade efetiva de
leitura + escrita das particoes.

**Instrucoes para o piloto seguro:**
`git pull`;
`python -m unittest discover -s tests -p test_reconcile_stream.py -v`;
`python urnas.py reconcile --engine stream --pilot-rows 1000000 --chunk-rows 250000`.
Apenas depois de analisar esses resultados, executar
`python urnas.py reconcile --engine stream`.


---

## 2026-10-23 — E0085 — Piloto sequencial de um milhao de linhas concluido no H:

**Saida literal do investigador:** comando
`python urnas.py reconcile --engine stream --pilot-rows 1000000 --chunk-rows 250000`
concluiu normalmente, usando 256 particoes, com fingerprint
`8ab3ce83c8992b9a4be03587c0f2fc49e93d5d3247b76a182d4a2dac0a9ce6b2`.

**Evidencias quantitativas, incluindo leitura e gravacao de checkpoints:**
- checkpoint 1: rowid=250.000; 250.000 examinadas/elegiveis;
  36.116 linhas/s;
- checkpoint 2: rowid=500.000; 500.000 examinadas/elegiveis;
  27.304 linhas/s;
- checkpoint 3: rowid=750.000; 750.000 examinadas/elegiveis;
  25.330 linhas/s;
- checkpoint 4: rowid=1.000.000; 1.000.000 examinadas/elegiveis;
  24.224 linhas/s na media acumulada;
- limite superior informado no banco: rowid=140.699.402;
- `PILOTO CONCLUIDO` e confirmacao explicita de que
  `nenhum relatorio nacional alterado`.

**Conclusao tecnicamente sustentada:** a fase de varredura,
normalizacao e particionamento executa e grava checkpoints
persistentes na base real. A velocidade sustentada do primeiro
milhao foi ~24.224 linhas/s (aprox. 41 s), muito superior
aos 68–117 linhas/s das consultas indexadas por zona.
Nao existe ainda evidencia de que as 256 particoes possam
ser reconciliadas e consolidadas nessa mesma velocidade,
nem teste nacional de equivalencia concluido.

**Projecao condicional:** restam aproximadamente
139,7 milhoes de rowids; a 24.224 linhas/s seriam
aproximadamente 1h36min adicionais somente para a
varredura. A velocidade pode variar com cache, volume
de particoes, CPU, disco e sistema de arquivos; nao e
um compromisso de duracao total.

**Proximo passo:** exigir `OK` nos testes
`python -m unittest discover -s tests -p test_reconcile_stream.py -v`
caso ainda nao demonstrado, e depois retomar usando
`python urnas.py reconcile --engine stream`,
sem excluir checkpoints. Conferir no inicio
`retomando depois de rowid=1,000,000`, observar
`VARREDURA CONCLUIDA`, `INTEGRIDADE`,
`PARTICAO` e o resumo final antes de qualquer
declaracao de conciliacao nacional confirmada.


---

## 2026-10-24 — E0086 — Reconciliacao stream nacional concluida

**Execucao observada em log fornecido pelo investigador:**

- Engine `reconcile-stream-v1`, fingerprint `8ab3ce83c8992b9a4be03587c0f2fc49e93d5d3247b76a182d4a2dac0a9ce6b2`.
- Total `rows_scanned=140699402`; elegiveis `135717720`.
- 256 particoes seladas e verificadas por SHA-256.
- `keys_compared=67858974`; `matches=67858746`.
- `different_or_missing=228`, todas classificadas `SEM_SECAO`; `missing_bu=0`.
- `imports_incomplete=[]`, `status=concluido`.
- O resumo mantem `cobertura_nacional_confirmada=false`. Este indicador e conservador e fixo no codigo, **nao e calculado** a partir das 228 ocorrencias.
- O CSV final foi gravado com 8.816 bytes, contra 145.665.711 bytes do relatorio preservado no snapshot anterior. Metodologia e conteudo das duas versoes requerem comparacao independente antes de interpretar a diferenca.
- A saida confirma selagem completa e resultado consolidado, nao certificacao fisica da eleicao nem auditoria independente de todos os recursos esperados.
- Duracao total deste ultimo trecho na etapa foi aproximadamente 2.309 s, incluindo varredura retomada de 76 milhoes, selagem, comparacao e consolidacao.

**Observacao numerica:** `140699402-135717720=4981682` linhas nao elegiveis. No checkpoint de 76 milhoes, a mesma diferenca ja aparecia entre linhas lidas e elegiveis. Convergencia com o planejamento anterior de `135717720` linhas.

**Seguimento:** novo `audit_reconciliation.py`, somente leitura sobre o CSV final de 8.816 bytes e seu summary, identifica distribuicao dos 228 casos por UF, turno, cargo, zona, secao, votavel e votos_BU, verifica contadores e checksum. Executar depois de `git pull` com `python audit_reconciliation.py`. Conferir a distribuicao e examinar fontes de cada caso antes de determinar sua causa; o script novo ainda nao foi executado no H: pelo assistente.


---

## 2026-10-24 — E0087 — Explicacao geografia/cargo das 228 ocorrencias

`python audit_reconciliation.py` terminou no H: com
`Conferencia CSV x resumo: OK` e SHA-256 do CSV
`31db2a2915492fc07786ff79dc40c74a0d20f42d75d113a54e1c9be01c41ce5b`.

Todas as 228 ocorrencias `SEM_SECAO` sao de
`PE/30015/zona 4/turno 1/cargo 25`, distribuidas
por 10 secoes, com soma de 2.445 votos BU e zero
chaves duplicadas.

O README ja identificava esse cargo como Conselheiro
Distrital de Fernando de Noronha. Pesquisa de fontes
primarias confirmou que o TSE anunciou 2.445 votantes
em dez secoes para esta eleicao especial, realizada
junto com as eleicoes gerais; o sitio tecnico do TSE
identifica a eleicao distrital separadamente pelo
codigo `6261` (vs `6257` federal e `6259` estadual).

**Interpretacao:** 228 ausencias sao fortemente compativeis
com diferenca de escopo da fonte `secao` para pleito
especial. Nao sao diferencas numericas de votos em chaves
pareadas e nao provam perda de votos da totalizacao.
A causa especifica de ausencia do recurso por secao do
pleito `6261` ainda precisa de comprovacao com fonte
independente correspondente. Nao apagar nem reclassificar
as linhas originais.

Referencias oficiais:
https://www.tse.jus.br/comunicacao/noticias/2026/Outubro/eleitores-de-fernando-de-noronha-elegem-7-conselheiros-distritais
https://www.tse.jus.br/eleicoes/informacoes-tecnicas-sobre-a-divulgacao-de-resultados

Relatorio tecnico completo e limites:
`docs/RECONCILIACAO_NACIONAL_2026.md`.


---

## 2026-10-24 — E0088 — Objetivo permanente e cruzamento entre cargos

O investigador reiterou que a reconciliacao contabil e
**etapa, nao conclusao do projeto**. O objetivo permanente
e testar com metodos estatisticos e provas independentes a
possibilidade de alteracao de dados entre urna, transmissao,
totalizacao e publicacao, alem de padroes eleitorais atipicos.
Solicitou explicitamente comparacao entre apoio a Presidencia
e candidaturas locais/estaduais/federais e controles historicos,
inclusive alegacoes sobre 2022, sem assumir que a hipotese ja
tenha ocorrido em 2026.

**Protocolo versionado:** foi criado
`docs/PROTOCOLO_INVESTIGACAO_MULTICAMADAS_2026.md`
e vinculado ao README e aos metodos estatisticos. O
programa agora especifica:
- comparacao de BU impresso/QR e artefatos assinados contra
  os votos publicados; hashes obtidos apenas apos download
  nao provam a origem independente;
- cotejos de series EA14, EA15, EA16, EA18, EA20 por
  secao/candidato e separacao de recebimento, totalizacao,
  publicacao e CDN;
- base por secao para Presidente, Governador, Senado
  (duas vagas em 2026) e deputados;
- classificacoes ideologicas versionadas, com ambiguidade,
  fonte, aliancas e teste de sensibilidade;
- limites de inferencia ecologica, simulacoes/permutações
  condicionadas por geografia e calibracao historica;
- prefeito em 2024: controle historico, nao mesmo pleito;
- quaisquer alegacoes de fraude em 2022 precisam de
  evidencias especificas, sem transformacao em fato:
  auditoria do TCU dos BUs em 2022 nao encontrou divergencias
  no conjunto examinado;
- uma anomalia estatistica nao autoriza atribuir causalidade
  ou declarar adulteracao sem comparacao material independente.

**Status:** protocolo implementado como documentacao;
modulos especificos de cruzamento entre cargos,
limites ecologicos, verificacao criptografica e modelos
condicionais estao **planejados, nao executados**.
Preservar os resultados negativos e verificacoes que
contrariem as hipoteses; nao otimizar so em busca de
um resultado preconcebido.


---

## 2026-10-24 — E0089 — Confirmacao agregada do pleito 6261 e matriz entre cargos

**Verificacao real no computador do investigador:**

- `git pull` atualizou o script `verify_noronha_6261.py`.
- Seis testes sinteticos de `test_verify_noronha_6261.py`
  concluidos: `Ran 6 tests ... OK`.
- `python verify_noronha_6261.py` obteve o JSON do
  endereco oficial
  `https://resultados.tse.jus.br/oficial/ele2026/6261/dados/pe/pe30015-z0004-c0025-e006261-u.json`.
- SHA-256 do JSON oficial:
  `96463db912ac20355cddcd0cfbfd6bee5b8ed63feb04aad33e9d28264cae5ddf`.
- 228 chaves de BU em PE/30015/zona4/turno1/cargo25,
  10 secoes, 2.445 votos totais.
- Comparados 24 votaveis: 24 iguais, 0 diferentes,
  0 sem correspondencia; 95=44 (brancos),
  96=62 (nulos), ambos iguais ao EA20 oficial.
- Relatorio derivado:
  `H:/TSE/forensics/urnas/analysis/validacao_6261/comparacao_96463db912ac2035.json`.
- Saida literal: `RESULTADO: EQUIVALENCIA_AGREGADA_CONFIRMADA`.
- Conclusao: igualdade de totais por votavel **na zona**,
  nao auditoria independente de cada uma das 10 secoes.

**Proxima fase publicada na main, mas ainda NAO executada no H::**

- `cross_office_sections.py`, com
  `tests/test_cross_office_sections.py`;
- somente leitura das particoes BU/stream ja verificadas por SHA-256;
- prepara matriz por secao dos seis cargos 1,3,5,6,7,8,
  sem classificar candidato como direita/esquerda
  antes de fonte verificavel; soma dos votos
  especiais preservada para auditoria;
- checkpoints derivados por particao e produto separado;
  nao substitui reconciliacao nacional;
- piloto proposto: `python cross_office_sections.py --pilot-buckets 2`;
  depois, com testes OK e piloto verificado:
  `python cross_office_sections.py`.

Objetivo investigativo: quantificar correlacoes e limites
de voto cruzado entre cargos e selecionar casos para pericia
de artefatos de urna/transmissao. Nenhuma diferenca de
padrão agregada basta para concluir fraude.


---

## 2026-10-24 — E0090 — Matriz nacional entre cargos finalizada

O investigador executou no H: `python cross_office_sections.py`,
retomando o piloto de 2/256 particoes. O programa confirmou
`MATRIZ ENTRE CARGOS CONCLUIDA`, sem mensagens de erro.

**Dados da saida real:**

- fingerprint preservado:
  `8ab3ce83c8992b9a4be03587c0f2fc49e93d5d3247b76a182d4a2dac0a9ce6b2`;
- `input_rows_eligible=135717720`;
- `source_bu_rows_selected=67858746` (cargos 1,3,5,6,7,8;
  cargo 25 especial fica fora desta matriz);
- `candidate_keys=67858746`, `distinct_sections=499206`;
- `sections_by_office`: Presidente 499206, Governador 497897,
  Senado 497897, Dep. Federal 497897, Dep. Estadual 490928,
  Dep. Distrital 6969;
- `paired_president_governor_sections=497897`;
- `president_governor_totals_unequal=17233` (3,461% das pareadas);
- `partitions=256`;
- matriz `analysis/entre_cargos/8ab3ce83c8992b9a-94fc637b4737c20d/secoes_por_cargo.csv`;
- SHA-256 da matriz:
  `9aefc6cf4591180a1f2edfdc2cdb7b9e44c19ae8caf2b5d23fa2d6c83f02dfad`.

**Interpretacao:** as 17.233 ocorrencias sao **diferencas
entre a soma de votos BU de dois cargos**, nao
divergencias BU-vs-secao no mesmo cargo e nao
prova de alteracao na totalizacao. 1.309 secoes
contem Presidente mas nao Governador; origem
geografica ainda nao classificada.

**Proximo modulo:** `audit_cross_office_totals.py` e
`tests/test_audit_cross_office_totals.py` publicados na
main com workflow de testes atualizado. Le somente o CSV
de matriz verificado por SHA-256, calcula
distribuicao das magnitudes e direcoes dos deltas
por UF, municipio, turno e seleciona ate 50
secoes para verificacao posterior. **Ainda nao
executado no H:** resultados precisam ser fornecidos
pelo investigador. Nenhuma inferencia de voto
cruzado foi feita.


---

## 2026-10-24 — E0091 — Assimetria Presidente/Governador e teste de voto em transito

**Execucao e testes apresentados pelo investigador:** 4 testes
do `audit_cross_office_totals.py` concluiram OK.
A execucao nacional verificou SHA-256 da matriz
`9aefc6cf4591180a1f2edfdc2cdb7b9e44c19ae8caf2b5d23fa2d6c83f02dfad`
e terminou `DIAGNOSTICO ENTRE CARGOS CONCLUIDO`.

- 499.206 secoes na matriz; 497.897 pareadas P/G;
- 480.664 pares iguais; 17.233 pares diferentes;
- 17.233 com Presidente > Governador, nenhum com G>P;
- soma P=124.934.069 e G=124.768.485 nos pares;
  excedente de 165.584 votos; maximo local=289;
- distribuicao de diferencas por magnitude:
  1:5269, 2:2281, 3–5:3699, 6–10:2435,
  11–50:2957, 51–100:418, >100:174;
- maiores ocorrencias em numero por UF: SP 4603,
  RJ 2725, MG 1520, PR 1347.

**Fonte oficial TSE verificada:** em 2026, voto em transito
entre UFs permite somente voto presidencial; dentro da
UF, todos os cargos. Este mecanismo pode produzir
P>G na mesma secao sem alteracao fraudulenta de
dados. **Nao inferir automaticamente que os 165.584
votos sao todos de transito** sem conferencia de
eleitorado especial por secao.
https://www.tse.jus.br/eleicoes/eleicoes-2026-content/voto-em-transito-perguntas-e-respostas

**Proximo teste publicado no GitHub, ainda sem resultado
real:** `audit_cross_office_eligibility.py` e testes.
Verifica P≥G, Senado=2×G em cada secao com ambos presentes,
casos P sem G, UF e 100 possiveis excecoes.
Entradas sao apenas a matriz e o resumo anteriores
com SHA-256, sem reabrir banco nem checkpoints originais.
Depois, buscar dados oficiais de voto em transito para
validar a causa por secao e seguir para modelos de
compatibilidade politica entre cargos.


---

## 2026-10-24 — E0092 — Controle Senado=2xGovernador e correlação entre candidatos

**Resultado observado diretamente no log do investigador:**
`python -m unittest discover -s tests -p test_audit_cross_office_eligibility.py -v`
terminou `Ran 4 tests ... OK`. A execução real de
`python audit_cross_office_eligibility.py` terminou normalmente
usando SHA-256 da matriz
`9aefc6cf4591180a1f2edfdc2cdb7b9e44c19ae8caf2b5d23fa2d6c83f02dfad`.

No país, 499.206 seções contêm Presidente. Há 1.309 seções
com Presidente e sem Governador, somando 341.766 votos
presidenciais. Nas 497.897 seções com Governador e Presidente,
480.664 totalizam P=G, 17.233 P>G (soma excedente 165.584),
zero G>P. **Nas 497.897 seções com Senado/Governador
S=2×G exatamente**, em nenhuma foi encontrado S diferente
de 2×G. `amostra_quebras=[]`.

**Interpretação:** estas relações apoiam uma explicação
contábil de elegibilidade por cargo, compatível com
voto em trânsito fora da UF (apenas Presidente),
voto presidencial no exterior e duas vagas para Senado;
ainda não há comprovação da origem exata das
17.233 diferenças por identificação de eleitores
habilitados/seções oficiais. Não atribuir automaticamente
165.584 votos a trânsito. As identidades são internas
a BU e não substituem evidência física independente.

**Avanço implementado na main:** novo
`cross_office_candidate_correlations.py`,
com testes `tests/test_cross_office_candidate_correlations.py`.
Analisa os dois presidenciáveis mais votados e três
governadores mais votados em cada UF, nos BU da matriz,
calculando correlação bruta e correlação após subtrair
médias `municipio+zona`, sem supor ideologia nem
voto individual. No momento este script ainda **não foi
executado na base real H:**; executar testes e coleta
de saídas antes de interpretar qualquer coeficiente.


---

## 2026-10-24 — E0093 — Extensao comparacao eleitoral para Senado

**Solicitacao do investigador:** nao limitar cruzamentos
entre cargos a Presidente/Governador; investigar tambem
Presidente/Senado, candidato por candidato, e mais tarde
as possibilidades de alinhamentos/coligacoes politicas
com controle de territorio e historico.

**Publicacao na main:** novo
`cross_office_senate_correlations.py`,
`tests/test_cross_office_senate_correlations.py`
e inclusao da bateria no workflow dos testes.

O modulo seleciona os 2 presidenciaveis com mais
votos e por padrao **todos** os senadores por UF
(`--top-senators N` e opcional para ensaio reduzido).
Compara por secao as respectivas taxas de apoio.
Denominadores: Presidente total de votos do cargo;
Senado total de votos do cargo **dividido por 2**,
pois no primeiro turno de 2026 cada eleitor fez
duas escolhas ao Senado. Brancos e nulos integram
os denominadores, nao os numeradores dos candidatos.

Gera correlacoes Pearson brutas e apos remover
efeitos fixos de municipio+zona, com matriz
somente de BU previamente verificada por SHA-256.
Nao deduz voto individual nem compatibilidade
ideologica automaticamente. Preserva os artefatos
do modulo de Governador; as saidas senatoriais
ficam em diretorio especifico.

**Estado:** ainda sem execucao real no H: e sem
comprovacao local dos testes. Proximos comandos:
`git pull`;
`python -m unittest discover -s tests -p test_cross_office_senate_correlations.py -v`;
`python cross_office_senate_correlations.py`.


---

## 2026-10-24 — E0094 — Correlacao nacional Presidente x Senado executada

**Execucao real observada diretamente no terminal do investigador:**
`git pull` sincronizou `cross_office_senate_correlations.py`.
A bateria `python -m unittest discover -s tests -p test_cross_office_senate_correlations.py -v`
executou **5 testes com OK**, incluindo validacao de duas
escolhas, assinatura SHA-256 da derivacao e ajuste por zona.

O comando real `python cross_office_senate_correlations.py`
terminou `CORRELACAO PRESIDENCIA X SENADO CONCLUIDA`.
Resultados medidos:

- 67.858.746 chaves BU verificadas na origem por SHA-256;
- presidenciaveis selecionados: votaveis `22` e `13`;
- **27 UFs**, **308 candidaturas ao Senado**;
- **497.897 secoes pareadas**, todas com percentuais
  computaveis de Presidente e Senado;
- **616 pares** = 308 candidatos senatoriais x 2 presidenciais;
- CSV publicado apenas no disco do investigador:
  `H:/TSE/forensics/urnas/analysis/entre_cargos/8ab3ce83c8992b9a-94fc637b4737c20d/correlacao_presidente_senado/pares_por_uf.csv`;
- SHA-256 do CSV:
  `0b05e18dd5eb9b980e203ef361bcbaf069fb28008f51f310cb44b49d8c618d68`.

**Interpretação:** o log confirma que as correlacoes brutas
e intrazona foram calculadas, **nao apresenta os 616
coeficientes**. Portanto nao afirmar quantos sao positivos,
negativos, fortes ou mudam sinal antes de obter o diagnostico.
O metodo usa a taxa de cada senador com denominador
`total de votos ao Senado / 2`, para duas escolhas, e
percentual presidencial por secao. E uma comparacao
ecologica, nao reconstituicao de cédulas individuais.

**Publicacao adicional ainda nao executada no H::**
`audit_senate_correlations.py` e testes
`tests/test_audit_senate_correlations.py`.
Le apenas o CSV de 616 linhas e seu resumo, valida
SHA-256 e cardinalidade, contabiliza por UF coeficientes
existentes, reversoes robustas de sinal e reducao
geografica. Predefine minimos descritivos
1.000 secoes, 10 zonas com variacao e 1.000 votos
senatoriais. Sinal oposto requer magnitudes de ambos
os coeficientes >= 0,1; mudanca >= 0,2 e marcada
separadamente. Regras descritivas, nao p-valores.

**Proximos comandos:**

```bat
git pull
python -m unittest discover -s tests -p test_audit_senate_correlations.py -v
python audit_senate_correlations.py
```

Ainda esta pendente a execucao nacional do modulo
`cross_office_candidate_correlations.py` para Governador,
necessaria para comparacao entre os dois cargos.
Controlar que as duas implementacoes usam denominadores
diferentes (para Governo, votos validos; para Senado,
eleitores que votaram nas duas escolhas) antes de comparar
magnitudes de Pearson. Nunca inferir fraude so de correlacao.


---

## 2026-10-24 — E0095 — Correlacao Presidente e Governador nacional concluida

**Evidencia observada diretamente no terminal do investigador:**

- `python -m unittest discover -s tests -p test_cross_office_candidate_correlations.py -v` concluiu **4 testes OK**;
- `python cross_office_candidate_correlations.py` percorreu e verificou as 256 particoes de candidatos derivadas de BU, **67.858.746 chaves**;
- duas candidaturas presidenciais selecionadas pelos votos totais: `22` e `13`;
- Governador: tres candidaturas selecionadas por cada uma de **27 UFs**;
- **497.897 secoes pareadas**, todas com frações validas para o calculo;
- **162 pares** Presidente x Governador, com correlações brutas e ajustadas por municipio+zona;
- CSV `H:/TSE/forensics/urnas/analysis/entre_cargos/8ab3ce83c8992b9a-94fc637b4737c20d/correlacao_presidente_governador/pares_por_uf.csv`;
- SHA-256: `2e76281067a9d8bdb2c59dd3a702baab4fa573e6706a35f2399e1d425b41d627`.

**Consolidado de cobertura:** 162 pares P/G + 616 pares P/S = **778 pares calculados**. Esse numero nao informa os sinais ou amplitudes, que ainda devem ser extraidos dos CSVs; nao confundir processamento com conclusao investigativa. Os dois modulos tem denominadores diferentes: Governador usa votos validos presidenciais e governatoriais; Senado usa votos totais (incluindo branco/nulo), e no Senado divide as duas oportunidades de voto por 2.

**Avanco publicado na main, ainda nao executado no H::**
`audit_cross_office_correlations.py` e
`tests/test_audit_cross_office_correlations.py`.
O script verifica SHA-256, turnos, candidaturas e todos os pares
dos dois CSVs existentes, registra sinais, casos sem coeficiente,
mudancas apos retirar medias municipais/zonais e filtros descritivos.
Saidas em `analysis/entre_cargos/8ab3ce83c8992b9a-94fc637b4737c20d/diagnostico_conjunto/`.
**Nao reler BU nem SQLite**.

Comandos de proxima execucao:

```bat
git pull
python -m unittest discover -s tests -p test_audit_cross_office_correlations.py -v
python audit_cross_office_correlations.py
```

Avisos cientificos: os 778 pares nao sao amostras independentes
(os mesmos eleitores/secoes entram em varias comparacoes).
Sinal trocado e correlacao forte nao demonstram voto cruzado de
pessoas identificadas nem fraude. Filtros são heuristicas descritivas,
nao valores-p calibrados. Qualquer inferencia eleitoral depende de
robustez, simulacoes adequadas e verificacao externa.


---

## 2026-10-24 — E0096 — Diagnostico nacional dos 778 pares

O investigador executou `git pull`, os testes
`test_audit_cross_office_correlations.py` (7/7 OK),
e `python audit_cross_office_correlations.py` com
`DIAGNOSTICO CONJUNTO PRESIDENTE X GOVERNADOR E SENADO CONCLUIDO`.

**Resultado nacional calculado a partir dos CSVs de
correlacao (sem reler os BU):**

- **778 pares totais**, 162 Presidente/Governador e
  616 Presidente/Senado;
- Governador: **162 aptos**, 0 sem coeficiente,
  **0 inversoes de sinal robustas**, 29 mudancas absolutas
  de Pearson >=0,20; correlacao ajustada: 71 r>=0,10,
  75 r<=-0,10, 16 entre -0,10 e +0,10;
- Senado: **610 de 616 aptos** (6 fora do filtro de
  minimo de votos), 0 sem coeficiente, **13 inversoes de sinal
  robustas**, 92 mudancas absolutas >=0,20; correlacao
  ajustada entre os 610 aptos: 172 r>=0,10,
  185 r<=-0,10, 253 entre -0,10 e +0,10;
- inversoes senatoriais por UF:
  **TO 4, AC 2, RN 2, AL 1, AM 1, PI 1, RR 1, SP 1**;
  8 UFs, 13 pares, possivelmente menos de 13 candidaturas
  senatoriais distintas (dois presidenciaveis por senador);
- mudancas >=0,20 representam ~17,9% dos pares aptos
  do Governador (29/162) e ~15,1% do Senado (92/610),
  **nao** frequencia de adulteracao eleitoral;
- saida:
  `H:/TSE/forensics/urnas/analysis/entre_cargos/8ab3ce83c8992b9a-94fc637b4737c20d/diagnostico_conjunto/summary.json`.

**Interpretacao metodologica:** a revisao descritiva
identifica sensibilidade geográfica dos coeficientes e
possibilidade de paradoxo de Simpson; nao ha resultado
de testes de significancia calibrada, evidencia independente
de alteracao material nem inferencia de voto individual.
As 778 correlacoes nao sao observacoes independentes,
e Senado e Governador usam denominadores diferentes.
Nao inferir padrao politico a partir de IDs `22`, `13`,
ou outros sem identificar candidaturas e alianças
com fontes e controle por UF.

**Proxima verificacao publicada na main, ainda nao
executada no H::**

`review_cross_office_correlations.py` e
`tests/test_review_cross_office_correlations.py`.
Le apenas os 778 pares de `diagnostico_conjunto/todos_os_pares.csv`,
verifica SHA-256, limiares e resumo, e produz:
- `revisao_inversoes/senado_pares_invertidos.csv` com
  os 13 pares individuais, r bruto, r ajustado,
  UF, identificadores e tamanho do conjunto;
- `revisao_inversoes/senado_por_uf.csv` com
  **quantidade de senadores distintos por UF**;
- `revisao_inversoes/mudancas_020.csv` com todos
  os 121 pares de mudanca >=0,20;
- `revisao_inversoes/summary.json` com hashes.

Executar `git pull`, testar modulo e rodar a revisao.
Nao reprocessar dados brutos antes de examinar os pares.


---

## 2026-10-24 — E0097 — Candidatos das 13 inversoes identificados e limites ecologicos

**Entrada observada:** 5/5 testes OK em
`tests/test_review_cross_office_correlations.py`,
seguido de `REVISAO DAS INVERSOES CONCLUIDA`,
com 778 pares, 13 inversoes no Senado,
0 no Governador, 9 senadores distintos em 8 UFs.

**IDs, filiacoes e identificacao verificada nas paginas
de candidatos do Senado Federal publicadas em 24/08/2026:**

- AC 277: Dr. Junior Feitosa (DC), 19.283 votos;
- AL 111: Arthur Lira (PP), 948.703 votos;
- AM 455: Plinio Valerio (PSDB), 948.793 votos;
- PI 111: Ciro Nogueira (PP), 904.961 votos;
- RN 444: Tercio Tinoco (Uniao), 102.834 votos;
- RR 155: Teresa Surita (MDB), 117.270 votos;
- SP 232: Soninha Francine (Cidadania), 165.707 votos;
- TO 153: Alexandre Guimaraes (MDB), 316.786 votos;
- TO 222: Eduardo Gomes (PL), 450.191 votos.

Total: 9 candidaturas distintas, 7 siglas e 13
pares Presidente/Senador; duas candidaturas
presidenciais compartilhadas geram dependencias
entre coeficientes. Fontes URL individuais:
`docs/CANDIDATOS_SENADO_INVERSOES_2026.csv`.
Coeficientes por par e regras de interpretacao em
`docs/REVISAO_INVERSOES_SENADO_2026.md`.
Lista de candidatura de agosto nao equivale a
situacao juridica final; conferir EA20 e DivulgaCand.

**Proxima fase publicada na main, ainda sem execucao
real no H::** `senate_ecological_bounds.py` e
`tests/test_senate_ecological_bounds.py`.
Verifica todos os SHA-256 dos arquivos BU seccionais
derivados, usa mapa dos nove candidatos e cruza com
os mesmos IDs de `revisao_inversoes/summary.json`.
Calcula limites exatos de interseccao por secao,
`max(0,P+S-N) <= intersecao <= min(P,S)`, soma
os limites por UF/candidatura e registra os limites
percentuais de eleitores que necessariamente podem
ou nao podem ter feito a escolha presidencial.
O Senado tem duas vagas, mas cada pessoa escolhe
um candidato especifico no maximo uma vez.
Este modulo NAO imputa combinacoes individuais,
nao estima fraude nem reabre SQLite.
Saidas em `limites_presidencia_senado_inversoes/`,
com CSV, JSON e hashes.

**Comandos no computador do investigador:**

```bat
git pull
python -m unittest discover -s tests -p test_senate_ecological_bounds.py -v
python senate_ecological_bounds.py
```

O ultimo comando reexamina os arquivos BU por candidato
porque essa nova pergunta exige dados por secao;
nao requer reexecutar a reconciliacao nacional.


---

## 2026-10-24 — E0098 — Limites por secao de voto cruzado com nove senadores

**Execucao observada no computador do investigador:**
`python -m unittest discover -s tests -p test_senate_ecological_bounds.py -v`
terminou `Ran 6 tests ... OK`.
`python senate_ecological_bounds.py` percorreu as
**256/256** particoes BU por candidato e conferiu
**67.858.746** chaves, sem SQLite; terminou
`LIMITES PRESIDENTE X SENADO CONCLUIDOS`.

Entradas preservadas:
- mapa oficial local de nove candidaturas
  `docs/CANDIDATOS_SENADO_INVERSOES_2026.csv`
  SHA-256 `ecf426fdfaeef33fe36dc6d2451657a77b84abec6933115255b187c5fe9cdd9f`;
- relatorio das 13 inversoes
  SHA-256 `b71eabb5c98764b351c90a5ccb18abe81caac924fe0186f426243767a3e5e03b`;
- CSV dos 18 limites
  `analysis/entre_cargos/8ab3ce83c8992b9a-94fc637b4737c20d/limites_presidencia_senado_inversoes/limites_por_senador_presidente.csv`
  SHA-256 `bdf25f56d647d9265b7e20fcc9e75095f712031659b32bffcc7e7380ff20157f`.

**Conceitos:** cada senador S representa eleitores distintos,
porque cada candidato pode ser escolhido uma vez, apesar
das duas vagas. Nas mesmas secoes, P=13 ou P=22 e
N=comparecimento presidencial; intersecao desconhecida:
`max(0,P+S-N) <= sobreposicao <= min(P,S)`.
A somatoria e feita **por secao**, estreitando os limites
em relacao a usar apenas a UF. Os limites N incluem
eleitores em transito eventualmente elegiveis so
para Presidente, o que conserva a inferencia.

**Valores minimos necessarios, como fracao dos votos de S:**

| UF | Senador | Votos S | Minimo tambem P13 | Minimo fora de P22 |
| --- | --- | ---: | ---: | ---: |
| AC | Dr. Junior Feitosa | 19.283 | 85 (0,44%) | 128 (0,66%) |
| AL | Arthur Lira | 948.703 | 193.108 (20,35%) | 306.199 (32,28%) |
| AM | Plinio Valerio | 948.793 | 125.588 (13,24%) | 165.094 (17,40%) |
| PI | Ciro Nogueira | 904.961 | 289.310 (31,97%) | 413.039 (45,64%) |
| RN | Tercio Tinoco | 102.834 | 653 (0,64%) | 1.840 (1,79%) |
| RR | Teresa Surita | 117.270 | 1.671 (1,42%) | 2.041 (1,74%) |
| SP | Soninha Francine | 165.707 | 0 (0%) | 1 (aprox. 0%) |
| TO | Alexandre Guimaraes | 316.786 | 15.531 (4,90%) | 27.935 (8,82%) |
| TO | Eduardo Gomes | 450.191 | 35.429 (7,87%) | 65.317 (14,51%) |

**Inferencia rigorosa:** por exemplo, nos BU de PI, ao
menos 289.310 dos eleitores registrados para Ciro Nogueira
tambem escolheram P13, e ao menos 413.039 nao escolheram
P22. Isso nao afirma que foram os mesmos 289.310 ou que
o restante foi necessariamente para P13: os conjuntos
foram delimitados separadamente e ha demais candidaturas,
brancos/nulos. **Nao converter em imputacao de
voto individual, desvio ou adulteracao.**
Nao somar dois senadores de uma mesma UF como eleitores unicos;
nao extrapolar os nove selecionados por inversao
de sinal para todos os 308 candidatos ao Senado.

**Avanco leve publicado na main (ainda sem execucao real):**
`audit_senate_ecological_bounds.py` com os testes
`tests/test_audit_senate_ecological_bounds.py`.
Reabre APENAS o CSV de 18 linhas e JSON; confere hashes
do CSV e do mapa, consistencia com a revisao anterior,
bounds e percentuais, e produz o resumo
`analise_limites/resumo_cruzamento.csv`
e `analise_limites/summary.json`.
Nao reler novamente os 67,8 milhoes de BU.

Comandos a executar:
```bat
git pull
python -m unittest discover -s tests -p test_audit_senate_ecological_bounds.py -v
python audit_senate_ecological_bounds.py
```

O proximo passo substantivo deve separar fatos aritmeticos
de explicacoes eleitorais: identificar coligacoes e
candidaturas nos dados oficiais finais, e construir
grupos concorrentes de classificacao; usar controles
2022/2024 harmonizados ou modelos nulos condicionais
para perguntar se a magnitude dos limites e atipica.
A hipotese de integridade urna/transmissao permanece
independente.


---

## 2026-10-24 — E0099 — Limites auditados e escopo conceitual da formula 2022

**Execucao apresentada pelo investigador:** `git pull` concluiu;
`python -m unittest discover -s tests -p test_audit_senate_ecological_bounds.py -v`
concluiu **6/6 testes OK**; a execucao real
`python audit_senate_ecological_bounds.py` terminou
`AUDITORIA RESUMIDA DE LIMITES CONCLUIDA`.
Resultado: 9 senadores, 18 pares Presidente-Senado,
checagem de SHA/percentuais/margens e CSV novo em
`H:/TSE/forensics/urnas/analysis/entre_cargos/8ab3ce83c8992b9a-94fc637b4737c20d/limites_presidencia_senado_inversoes/analise_limites/resumo_cruzamento.csv`
com SHA-256
`87fa7f7a3fd954e5fb794eff0eb16b42872ae7b611aecb443efccce7be0933a0`.

Cinco maiores limites minimos necessarios P13:
Ciro Nogueira (PI) 289.310 / 31,9693%;
Arthur Lira (AL) 193.108 / 20,3549%;
Plinio Valerio (AM) 125.588 / 13,2366%;
Eduardo Gomes (TO) 35.429 / 7,8698%;
Alexandre Guimaraes (TO) 15.531 / 4,9027%.

Cinco maiores minimos de votos senatoriais fora de P22:
Ciro Nogueira (PI) 413.039 / 45,6416%;
Arthur Lira (AL) 306.199 / 32,2755%;
Plinio Valerio (AM) 165.094 / 17,4004%;
Eduardo Gomes (TO) 65.317 / 14,5087%;
Alexandre Guimaraes (TO) 27.935 / 8,8183%.
Sao limites aritmeticos, **nao contagens exatas do
voto individual, parametros de manipulacao ou prova
de adulteracao**.

### Correcao explicita do objetivo pelo investigador

O investigador esclareceu que **NAO deseja usar dados
eleitorais de 2022** nas proximas analises. Sua
referencia a 2022 dizia respeito a uma **hipotese de
formula ou mecanismo geral** que teria sido usado em
2022 e 2026, e NAO a comparar microdados ou resultados
de 2022 contra 2026.

Portanto, a partir desta entrada, os proximos testes
desta linha utilizam **somente dados de 2026**,
com eventuais evidencias documentais independentes
da urna, transmissao e totalizacao da mesma eleicao.
Nao carregar, treinar, recalibrar ou reproduzir
modelos com arquivos eleitorais de 2022. O trabalho
anterior de 2022 permanece preservado como
historico do projeto, sem novas execucoes.
Nao afirmar como fato a existencia de uma formula
aplicada nos dois pleitos: sua expressao matematica,
parametros, entradas, saidas e predicoes falsificaveis
ainda precisam ser definidos e testados.

**Prioridade seguinte:** modelar hipoteses concorrentes
de mecanismo sistematico nos dados de 2026 e testar
residuos, sinais esperados, concentracao espacial
e estabilidade em subconjuntos disjuntos do
mesmo pleito, seguidos por confrontacao material
com BUs fisicos/QR, arquivos assinados e cadeia
de transmissao. Testes ecologicos de voto cruzado
apenas fundamentam limites de composicao eleitoral:
nao identificam a causalidade de alteracoes.


---

## 2026-10-24 — E0100 — Confirmacao sem dados novos; iniciar teste material de 2026

O investigador apresentou novamente a mesma execucao de
`audit_senate_ecological_bounds.py` ja documentada na
entrada E0099, com 6/6 testes OK, nove senadores,
18 pares e mesmo CSV SHA-256
`87fa7f7a3fd954e5fb794eff0eb16b42872ae7b611aecb443efccce7be0933a0`.
**Nao e nova observacao e nao muda os resultados.**

A diretriz sobre 2022 foi confirmada: NAO utilizar
dados eleitorais de 2022. A hipotese de uma
formula comum a 2022 e 2026 e referencia
conceitual, nao comparacao historica nem fato
ja demonstrado. O conjunto empirico atual e
exclusivamente a eleicao 2026.

**Nova prioridade:** parar auditorias repetidas de
limites e verificar evidencia fisica e origem de
votos. Publicados na main:
- `inventory_material_evidence_2026.py`: consulta
  somente a tabela `archive_entries` no SQLite
  em modo de leitura, agrupando por UF/extensao
  os artefatos .bu/.rdv/.imgbu/.log/.vota
  oficialmente catalogados; nao reprocessa
  dados de voto. Compara, separadamente,
  eventual manifesto de capturas de terceiros
  em `evidencia_independente_2026/manifest.csv`
  e verifica hashes dos originais declarados,
  sem promover SHA-256 a assinatura ou
  independencia da fonte.
- `tests/test_inventory_material_evidence_2026.py`
  com sete testes sinteticos.
- `docs/TESTE_FORMULA_GERAL_SOMENTE_2026.md`:
  define X (BU independente), Y (publicado),
  D=Y-X (so quando X verificavel) e hipoteses
  falsificaveis H0, H1, H2 e H3 para transferencia,
  proporcionalidade ou selecao temporal.

**Importante:** X independente ainda NAO foi
demonstrado nesta fase. Sem X nao se pode
estimar diferencas materiais D a partir de
correlacoes, nem atribuir manipulacao.
Os novos scripts/testes foram publicados, mas
nao ha execucao no H: confirmada neste registro.

Proximos comandos:
```bat
git pull
python -m unittest discover -s tests -p test_inventory_material_evidence_2026.py -v
python inventory_material_evidence_2026.py
```


---

## 2026-10-24 — E0101 — Falha Windows em fixture SQLite do inventario

**Relato real recebido:** `git pull` levou o projeto ao
commit `75d69fd`; comando
`python -m unittest discover -s tests -p test_inventory_material_evidence_2026.py -v`
terminou `Ran 7 tests ... FAILED (errors=7)`.
Os rastros mostram **PermissionError [WinError 32]**
ao executar `Path.unlink` e `tempfile.cleanup` nos
arquivos `C:/Users/PC/AppData/Local/Temp/tmp.../analysis/urna_2026.sqlite3`.
Nao houve mensagem de erro SQL, hash ou divergencia
nos votos. Alguns metadados sinteticos chegaram a
ser corretamente relatados antes da falha.

**Diagnostico do codigo:** a fixture em
`tests/test_inventory_material_evidence_2026.py`
criava SQLite com `with sqlite3.connect(...) as db`,
que confirma a transacao mas nao fecha
automaticamente a conexao. No Windows, uma
conexao ainda aberta bloqueia exclusao do
arquivo temporario. O codigo produtivo do
inventario ja chamava `conn.close()`
no bloco `finally`.

**Correcao direta na main:** substituir
o contexto da fixture por
`with contextlib.closing(sqlite3.connect(...))`,
executar `db.commit()` antes do fechamento
(commit `ba91186`). No modulo produtivo,
a consulta de amostra de UF foi mudada de
`WHERE UPPER(uf)=?` para `WHERE uf=?`
e `extensao IN(...)`, permitindo uso do
indice ja existente `idx_archives_secao`,
sem alteracao do banco (commit `2a9e536`).

O log do investigador termina imediatamente
apos digitar `python inventory_material_evidence_2026.py`;
**NAO ha saida conclusiva de execucao real**.
Nao inventar contagens reais de BUs, RDVs
ou capturas fisicas. A solucao foi publicada,
mas **aguarda novo teste no Windows do investigador**.

Comandos apos eventual termino/cancelamento
do processo anterior, se ainda ativo:

```bat
git pull
python -m unittest discover -s tests -p test_inventory_material_evidence_2026.py -v
python inventory_material_evidence_2026.py
```

Protocolo ativo continua exclusivamente em 2026.
Ninguem deve alterar o SQLite original ou
tratar arquivos oficiais TSE com SHA-256 como
captura independente de um BU impresso.


---

## 2026-10-25 — E0102 — Inventario material real: apenas PDFs no indice

**Saida observada no terminal do investigador:**
`git pull` atualizou a main ate `07abb0a`.
`python -m unittest discover -s tests -p test_inventory_material_evidence_2026.py -v`
terminou **7 testes OK**, validando a correcao de WinError 32.
`python inventory_material_evidence_2026.py` terminou normalmente,
gravando `H:/TSE/forensics/urnas/analysis/evidencia_material_2026/inventario.json`.

**Resultado real do inventario SQLite archive_entries:**
- `catalogo_tse_status=CATALOGO_CONSULTADO`;
- **84 membros PDF**, nenhum hash de membro PDF calculado
  na coluna `sha256`;
- **29 identificadores de UF** distintos no grupo
  do catalogo, que podem incluir `ZZ` e
  `NAO_IDENTIFICADA`, sem interpretacao
  preliminar de cobertura eleitoral;
- **0** membros .bu/.rdv/.imgbu/.log/.vota
  nessa tabela;
- **0 capturas externas registradas** em
  `evidencia_independente_2026/manifest.csv`.

A contagem `0` significa **ausencia no indice consultado,
NAO ausencia comprovada no disco, no portal TSE ou
entre capturas fisicas de terceiros**.

**Fonte oficial primaria verificada na web:**
https://dadosabertos.tse.jus.br/dataset/resultados-2026-arquivos-transmitidos-para-totalizacao
O conjunto "Resultados 2026 - Arquivos transmitidos para
totalizacao" lista ZIPs por UF e exterior ZZ, declarando
arquivos `bu log rdv vota` na situacao "Totalizado".
Logo os arquivos existem publicamente como conjunto de
recursos; nao foi verificado que todos estejam locais,
integros ou decodificaveis. Nao baixar imediatamente
ZIPs potencialmente grandes nem afirmar independência
das copias oficiais.

**Causa potencial no proprio codigo:**
`urnas.py` usa `kinds=['bu','secao']` por padrao
para `fetch`; `artefatos` exige selecao
explicita. O motor `import_file` somente
popula `archive_entries` para recursos ja
importados, e somente calcula hashes internos
de .bu/.rdv/.log/.vota/.imgbu se
`kind='artefatos'`. Os PDFs nao comprovam
que ZIPs de transmissao foram ingeridos.
Ainda nao se sabe se a causa real foi
falta de download, importacao desabilitada,
erro de importacao, ou ficheiros locais
com caminho divergente.

**Implementacao publicada e pendente de execucao
real no H::**
`diagnose_artifact_coverage_2026.py`
e `tests/test_diagnose_artifact_coverage_2026.py`.
Consulta SEM download, em modo leitura,
`catalogo_latest.json` (recursos declarados),
arquivos de `raw/artefatos/<UF>/` e SQLite
(`imports`, `archive_entries`), separando
recurso disponibilizado, ZIP local,
parcial, indice e extensoes.
Gera `analysis/evidencia_material_2026/diagnostico_cobertura.json`.
NAO abre ZIP, nao le registros de votos,
nao usa dados de 2022.

```bat
git pull
python -m unittest discover -s tests -p test_diagnose_artifact_coverage_2026.py -v
python diagnose_artifact_coverage_2026.py
```

Somente depois desse diagnostico decidir se
cabe reindexar ZIPs que ja estao no H: ou
baixar seletivamente arquivos de uma UF.
Lembrar que artefatos transmitidos pelo TSE
ainda nao sao capturas independentes
do BU impresso na hora da votacao.


---

## 2026-10-25 — E0103 — Correcao de escopo do inventario e do BAT completo

**Correcao necessaria do assistente.** O investigador contestou
corretamente a suposicao de que a falta de .bu/.rdv na tabela
`archive_entries` significaria ausencia de dados de urna ou
necessidade de baixar novamente o acervo.

**Codigo da rotina completa verificado diretamente na main:**

1. `start_windows.bat`, opcao 1 `COLETA COMPLETA`,
   executa `python collect_forensics.py all --download-portal-files`.
2. `collect_forensics.py::main` chama
   `collect_portal(...)` e, em seguida,
   `collect_urnas_h()` quando o download foi solicitado.
3. `collect_urnas_h()` executa a CLI de `urnas.py`
   com `fetch --all --kind bu --kind secao --kind artefatos`.
4. `urnas.py::resource_path` grava recursos selecionados
   em `H:/TSE/forensics/urnas/raw/<kind>/<UF>/`, conforme
   o `root_path()` no Windows.
5. `urnas.py::import_file` indexa os ZIPs baixados em
   `H:/TSE/forensics/urnas/analysis/urna_2026.sqlite3`,
   incluindo as tabelas `votes` e `archive_entries`
   quando os recursos sao efetivamente importados.
6. O coletor separado preserva arquivos do portal que
   NAO sao de urna em `H:/TSE/forensics/portal/files/`;
   snapshots ficam sob `data/forensics` no projeto.

**Observacoes de execucoes anteriores realmente confirmadas:**

- BU digital x CSV por secao: **67.858.746** chaves
  coincidentes na matriz de candidatos;
- matriz cross-office com **499.206 secoes**;
- **497.897** secoes pareadas entre Presidente,
  Governador e Senado;
- correlações: **162** pares Presidente/Governador
  + **616** pares Presidente/Senado;
- limites ecologicos para nove senadores e dois
  presidenciaveis: **18** pares auditados;
- as origens e os derivados continuam no drive H:.

**Alcance real do inventario de E0102:** ele consultou
SOMENTE `archive_entries` e listou 84 membros PDF,
sem entradas .bu/.rdv/.imgbu/.log. Isso NAO mede
todo o banco (`votes`), nao percorre os diretórios de
download, nao examina os ZIPs brutos e nao altera
o que ja foi comprovado pelas execucoes das analises.
A coluna hash vazia para PDF e esperada, porque
`import_file` calcula hash de membro apenas para
extensoes especificas e recurso `kind=artefatos`.
Os resultados do inventario sao verdadeiros no
seu escopo, mas a interpretacao anterior do assistente
e as propostas reiteradas de "localizar os dados"
ou recomeçar a coleta estavam incorretas.

**Diretriz operacional corrigida:**

- NAO reiniciar coleta, NAO exigir outra busca de
  arquivos ou inventarios como precondicao;
- NAO reprocessar 67,8 M chaves sem pergunta
  substantiva que de fato exija acesso por secao;
- aproveitar os BUs oficiais e os demais artefatos
  ja catalogados e suas hashes/fingerprints;
- prosseguir com teste falsificavel e comparacoes
  dos DADOS DE 2026 para a hipotese de mecanismo
  geral comum a pleitos diferentes (sem importar
  microdados de 2022);
- quando a hipotese exigir material INDEPENDENTE
  contemporaneo ao encerramento da urna, separar
  essa fonte de copia oficial, sem confundir
  ausencia no manifesto com ausencia global.

**Status:** corrigida a interpretacao; nenhuma
alteracao de dados ou novo download realizado.
O script `diagnose_artifact_coverage_2026.py`
e apenas diagnostico OPCIONAL, nao a proxima fase
obrigatoria da investigacao.


---

## 2026-10-25 — E0104 — Metodo Senado v2 e primeiro teste de formula fora da amostra

**Objetivo ativo do investigador:** seguir a analise
substantiva de uma hipotese de mecanismo geral,
utilizando exclusivamente votos de 2026 que ja
estao no drive H:, sem refazer coleta e sem
introduzir arquivos eleitorais de 2022.

### Retificacao de achado anterior

Foi detectado, na inspecao do codigo,
que a v1 de `cross_office_senate_correlations.py`
fechava os momentos da mesma zona eleitoral
independentemente em cada um dos 256 buckets.
Como os buckets dividem secoes, nao zonas,
isso muda o ajuste intrazona e pode gerar
inversoes de sinal espurias. As correlacoes
**brutas** ficam inalteradas, mas as intrazona
**v1** e a lista de 13 inversoes da E0096/E0097
devem ser consideradas **provisorias/retificadas**.
Os nove candidatos da etapa de limites foram
selecionados por esse filtro anterior; os
limites aritmeticos continuam limites por secao
para aqueles candidatos, mas nao sao um
ranking de atuais inversoes v2.

Foi publicada na main a v2 do mesmo modulo,
com zona `(UF,municipio,zona,turno)` completa
sobre TODOS os buckets e formula de centralizacao:
`Sxy_intra = sum(x*y) - sum_z(sum(x_z)*sum(y_z)/n_z)`.
As variancias x e y seguem a mesma identidade.
Os testes agora contêm caso de mesma zona em
buckets diferentes. Resultados v2 sao gravados
em `correlacao_presidente_senado_v2/`,
preservando v1 para rastreabilidade.

`compare_senate_geo_versions_2026.py` confronta
os 616 pares, hashes, metadados, coeficientes
brutos identicos e revisa quantas inversoes
v1 persistem, desaparecem ou surgem na v2.
Grava comparacao no diretorio de v2.
**Sem resultados reais nesta entrada**.

### Primeira forma concreta de formula a refutar

Publicado `test_fixed_vote_formula_2026.py`:
testa a forma `votos_P=round(alpha_P * N_pres)`
para os presidenciaveis 13 e 22 em 2026.
Usa 80% de secoes para treino e cerca de
20% para validacao, definidos por hash do
identificador da secao (independente do bucket).
O ajuste usa somente treino: alfa nacional,
alfa estadual e alfa por municipio+zona,
com fallback documentado. Preve as contagens
da validacao e compara MAE, RMSE, exatidao
e erro de ate um voto. A regra de avaliacao
da formula fixa nacional foi definida antes
de executar dados reais (>=95% de acerto exato
e MAE nacional <= MAE do modelo territorial).
E criterio descritivo exigente, NAO p-valor.
NENHUM acerto permite inferir fraude,
e fracasso desta forma simples nao descarta
outros mecanismos possiveis.

Os modulos e testes foram publicados
diretamente em `main`; os testes novos
ainda nao foram executados no Windows
do investigador. A analise le apenas
os arquivos BU por candidato derivados
ja presentes, valida SHA-256 e nao
acessa o SQLite nem baixa nada.

**Proximos comandos:**

```bat
git pull
python -m unittest discover -s tests -p test_cross_office_senate_correlations.py -v
python -m unittest discover -s tests -p test_compare_senate_geo_versions_2026.py -v
python -m unittest discover -s tests -p test_fixed_vote_formula_2026.py -v
python cross_office_senate_correlations.py
python compare_senate_geo_versions_2026.py
python test_fixed_vote_formula_2026.py
```

Nao concluir que existe transferencia eleitoral
sem fonte material independente para `D=Y-X`.


---

## 2026-10-25 — E0105 — Execucao real da robustez e diagnostico de zonas

**Fonte da evidencia:** saida completa da opcao C executada pelo
investigador em Windows, em H:/TSE/forensics/urnas (2026, turno 1).
Os primeiros trechos de 2 particoes e um par AC/170
sao testes SINTETICOS; os dados reais comecam em
`[ROBUSTEZ 1/256]` e terminam em `[ROBUSTEZ 256/256]`.

- 4 testes sinteticos locais concluídos;
- 256/256 particoes BU lidas uma vez, SHA conferidos;
- 13 pares reais das 616 comparacoes v2, reconstituidos
  sem desvio dos coeficientes originais;
- 400 replicacoes bootstrap por zona/par;
- 13/13 com sinal intrazona preservado ao retirar
  uma zona de cada vez;
- 6/13 mantiveram sinal em todas as replicacoes;
- 9/13 apresentaram quantis bootstrap de 2,5% e
  97,5% inteiramente do mesmo lado de zero;
- 4/13 tiveram intervalo atravessando zero:
  AM 22/455; RN 13/444; TO 13/153; TO 22/153;
- 4/13 mantiveram sinal e modulo >= 0,10
  em >=95% das replicacoes:
  AC 13/277; PI 13/111; TO 13/222; TO 22/222.

CSV no H::
`analysis/entre_cargos/8ab3ce83c8992b9a-94fc637b4737c20d/correlacao_presidente_senado_v2/robustez_inversoes_2026/pares_robustez.csv`.
SHA-256:
`f8dfe10cd1aa2f7c5d02c20f3aec54db75920273361380d811d2242c6613933e`.

**Interpretação:** estabilidade descritiva de algumas
correlacoes, não evidencia de urna adulterada.
Os pares foram selecionados entre 616, e as zonas
podem ser espacialmente dependentes. Nao atribuir
significancia confirmatoria a esses quantis bootstrap.

**Proxima fase implementada:** novo
`analyze_senate_zone_drivers_2026.py`, opcao D de
`start_windows.bat`, verifica SHA-256 dos checkpoints
produzidos pela opcao C e identifica as zonas mais
influentes na correlacao, sem reler BU ou SQLite.
Testes CI aprovados em Windows e Linux:
132 testes por SO,
https://github.com/rubentrancoso/TSE/actions/runs/40237539069

Documentacao detalhada:
`docs/ROBUSTEZ_SENADO_2026.md`.
Execucao empirica da opcao D: pendente.
Nenhum microdado de 2022 foi utilizado.


---

## 2026-10-25 — E0106 — Influencia por zona e stress de retirada conjunta

**Fonte:** saida da opcao D executada pelo investigador em
Windows sobre checkpoints da opcao C, apenas BU 2026.
O primeiro par AC/13/170 nos caminhos Temp era teste
SINTETICO e foi excluido das inferencias empiricas.

**Resultado de 2026**: 256/256 checkpoints com SHA-256
conferido; 13 pares e 2.156 linhas par x zona (as zonas
podem reaparecer para outros pares); 65 entradas top5
por par; 13 resumos. Recalculou todos os r ajustados.

Hashes dos tres CSVs:
- resumo: 55bc291a596a5c45f88e042e6d659a1d137fcb1a76e052070f057bb5c13b3183
- zonas: 6ccbec12342a13b320360f8de967bd4a6c0d158db43c7da4074d801ffadd9007
- top5: 0017ff8cc47d093042e9cdcef8eafcd00f45c465d2723b5fb95b382cf1b08826

**Observacoes geograficas:**
- SP 13/232: 490/779 zonas com covariancia alinhada,
  267 opostas e 22 zero; top 5 apenas 13,441%
  da soma de covariancia absoluta; maior delta
  de r ao omitir uma zona = 0,003821.
- AC 13/277: 20/23 zonas alinhadas; top5 = 79,484%
  de covariancia absoluta; maior delta = 0,045933.
- RN 13/444: 90/172 alinhadas e 82 opostas;
  top5 = 54,334%; maior delta = 0,047606.
- Os 13 pares apontam para apenas 8 diferentes
  zonas de maior influencia, uma em cada UF presente;
  isso se deve em parte a pares compartilhando secoes
  e candidaturas, e nao implica fonte comum de alteracao.

Lista e tabelas integrais:
\`docs/INFLUENCIA_ZONAL_SENADO_2026_25OUT.md\`.

**Nova opcao E:** stress adversarial removendo ao mesmo
tempo 1,3,5 zonas com maiores magnitudes da covariancia,
5 zonas de maior influencia individual, e 400 retiradas
aleatorias de cinco zonas. Usa apenas os checkpoints
da opcao C e valida SHA-256; dados originais preservados.
Avaliacao POS-SELECAO: nao e p-valor, nao corrige testes
multiplos, nao e prova de adulteracao eleitoral.

**Validacao:** 136/136 testes sinteticos aprovados
em Windows e Linux
https://github.com/rubentrancoso/TSE/actions/runs/40238571980

**Execucao empirica da opcao E:** pendente em H:.
Nenhuma importacao de dados eleitorais de 2022.


---

## 2026-10-27 — E0107 — Periodicidade por BU individual de 2026

Prioridade do investigador: aplicar a tecnica de deteccao
de vales/pulsos ao primeiro turno presidencial de 2026;
NAO estudar microdados da eleicao do video.

**Descoberta empirica da auditoria existente EA16:**
497.897 secoes principais, 100% com da/ha, mas
475.873 secoes (95,58%) agrupadas em 25 UFs cujos
horarios de todas as secoes cabem em menos de 5 min.
Esses campos NAO oferecem uma ordenacao individual
autentica para o grafico.

**Implementado sem refazer download ou SQLite:**
- Opcao G: tabela BU presidencial por secao extraida
  das 256 particoes BU SHA-validas + diagnostico de
  confiabilidade temporal EA16. O periodograma de
  ordem falsa permanece bloqueado.
- Opcao H: extrair DT_BU_RECEBIDO dos arquivos BWEB
  originais do primeiro turno de 2026 existentes em H:,
  validando cada ZIP com SHA do manifesto original,
  gerar uma linha de votos/recepcao por secao e
  checkpoint retomavel por UF. Reconstroi curva
  do total nacional por MINUTO de recebimento, mede
  vales, procura periodicidade em tempo e numero
  acumulado de secoes, e faz 1000 permutacoes
  comparativas sobre residuos do voto por minuto.
  Nao inventa ordem entre BUs com mesmo minuto.

**Arquivos publicados na main:**
analyze_bu_individual_timing_2026.py;
extract_bweb_received_2026.py;
analyze_bweb_receipt_periodicity_2026.py;
tests/test_analyze_bu_individual_timing_2026.py;
tests/test_extract_bweb_received_2026.py;
tests/test_analyze_bweb_receipt_periodicity_2026.py;
docs/FASE5C_BU_INDIVIDUAL_PERIODICIDADE_2026.md.

**Validação software:** 155/155 testes aprovados em
Ubuntu e Windows, GitHub Actions:
https://github.com/rubentrancoso/TSE/actions/runs/40508062650

**Execucao empirica H: opcao H ainda NAO executada
neste ambiente.** O relatorio esperado e:
H:/TSE/forensics/urnas/analysis/periodicidade_bweb_2026/phase5c_summary.json.
Sem ele, NAO se conhece o valor-p de periodicidade
nos BUs individuais de 2026.


---

## 2026-10-27 — E0108 — Fase 5C concluida empiricamente; segundos e robustez

**Fonte:** saida do terminal fornecida pelo investigador na opcao H
(Windows, H:/TSE/forensics/urnas, primeiro turno presidencial 2026).
As linhas dos testes em diretorio Temp sao inteiramente sinteticas
e nao se misturam aos dados das 28 UFs oficiais.

- 499.206 secoes extraidas dos BWEB locais SHA-validados (27 UFs + ZZ).
- 499.206 com DT_BU_RECEBIDO, nenhuma sem horario; 354 minutos.
- 254 minutos com >= 10.000 votos validos no teste por lote.
- Um vale de proeminencia >=8pp: 04/10 21:31,
  496.190 secoes acumuladas, 15.312 validos no minuto,
  residuo -4,43335pp, proeminencia 9,24395pp.
- Periodo senoidal maximo 14,208199 min,
  R² 0,03954052.
- p empirico sobre 1.000 permutacoes: 0,3086913 individual;
  0,4945055 em blocos de cinco.
- Nao excepcional frente aos dois nulos exploratorios.

**Cobertura a conferir:** 499.248 secoes na ultima
versao nacional da Fase 5A contra 499.206 nos ZIPs BWEB:
42 chaves de diferenca; sem pressupor adulteracao,
perda de votos ou identidade do escopo sem conciliacao.
Usar tambem total_compare_with_official do phase5c_summary.json.

**Ajustes publicados:** teste adicional na opcao I,
sensibilidade do minimo de votos e mediana (somente
CSV por minuto da H); teste adicional na opcao J,
pelo SEGUNDO original DT_BU_RECEBIDO ja salvo em
received-UF.csv, sem reler o ZIP, com agrupamentos
atomicos de segundo e blocos 500/1000/2000 BU.
Manter a ressalva de que multiplos BUs de mesmo
segundo NAO possuem ordem observada internamente.

**Estado empirico:** H concluido; I/J ainda nao executados.
Metodo e numeros:
docs/FASE5C_BU_INDIVIDUAL_PERIODICIDADE_2026.md.


---

## 2026-10-27 — E0109 — J (segundos) executado e teste de reconciliação K

**Fonte:** saída real do terminal Windows, primeiro turno de 2026.
A fixture anterior no Temp (120 BUs, 60 segundos) é sintética
e não integra a estatística nacional.

**Execução real:** 499.206 seções presidenciais, 9.039 segundos
distintos de DT_BU_RECEBIDO; precisão explícita de segundos
em 100% dos BUs. As 3 escalas de reagrupamento deram:

| Alvo de seções | Blocos | Melhor período (seções) | R² | p individual | p blocos de 5 |
|---|---:|---:|---:|---:|---:|
| 500 | 893 | 4.829,436671 | 0,01776219 | 0,039801 | 0,2089552 |
| 1000 | 470 | 4.829,436671 | 0,01976418 | 0,6368159 | 0,8706468 |
| 2000 | 243 | 35.103,147196 | 0,04767183 | 0,159204 | 0,6069652 |

Não foram detectados vales de proeminência ≥8 pp no
resíduo das três escalas; os p-valores vêm de apenas
200 simulações por nulo. Há aparente pico comum em
~4.829 seções, mas a escala 500 não confirma
sob blocos e a escala 2.000 aponta outro período.
Também há busca sobre 144 períodos e múltiplas escalas.
Trata-se de observação DESCRITIVA, não evidência de fraude.

**Reconciliação agregada:**
BU presidente 13 = 53.879.538, igual ao último snapshot;
BU presidente 22 = 56.104.503, igual ao último snapshot.
BU válidos = 119.306.034; snapshot = 119.300.788:
excesso BWEB +5.246, inteiramente na diferença
matemática da categoria residual demais candidatos.
BWEB 499.206 seções vs último snapshot 499.248:
-42 seções de escopo ainda não esclarecido.
Duas diferenças numericamente distintas. Não inferir
transferência de votos nem fraude apenas desse registro.

**Referência UF ↔ município já versionada:**
data/forensics/analysis/uf_candidate_reconciliation.csv
tem 18 linhas com diferenças entre UF e soma municipal,
nas UFs BA (1.244 votos) e MG (7.908 votos).
A fase 2 documenta BA 6 e MG 36 seções de diferença
estado vs soma municipal. Ainda não há chave que
prove serem as mesmas 42 da discrepância com a
contagem nacional.

**Implementação adicional:** audit_bweb_uf_totals_2026.py,
opção K, cruza o cache received-UF.csv da H com as
336 linhas por candidato/UF da fonte nacional,
sem ZIP, SQLite, rede ou material de 2022.
Separa diferença de votos 13, 22 e outros por UF;
não presume que diferença UF↔município seja erro de
votos BWEB. Resultado empírico K pendente.

Relatório principal:
docs/FASE5C_BU_INDIVIDUAL_PERIODICIDADE_2026.md.


---

## 2026-10-27 — E0110 — Identificada a origem da diferenca de 5.246 votos na Fase K

**Dados reais de 2026 — opcao K, executada localmente.**
BWEB 499.206 secoes (27 UFs + ZZ); nenhum arquivo de 2022.
Validos BWEB classificados por total menos branco e nulo
119.306.034, contra 119.300.788 no total oficial.
Diferenca +5.246 distribuidos por TODAS as 28 UFs.
Lula (13) 53.879.538 e Flavio (22) 56.104.503:
somatorios BWEB iguais ao oficial, por UF e nacional.

**Identificacao por fontes independentes:**
o numero presidencial **28, Leonardo Avalanche (PRTB)**,
obteve exatamente **5.246 votos nos boletins BWEB** que
nao figuram entre os votos validos oficiais. A candidatura
foi objeto de renuncia e seus votos nao sao validos.
Nulos convencionais BWEB 3.669.003 mais 5.246 nulos tecnicos
resultam nos 3.674.249 nulos oficiais.
Referencias:
https://multiversodigital.com.br/eleicoes2026/index.php
https://politica.one/eleicoes/2026/br/presidente
https://urna360.com.br/eleicoes/2026/1-turno/presidente
https://www1.folha.uol.com.br/poder/2026/10/leonardo-avalanche-desiste-de-candidatura-a-presidencia.shtml

**Erro no extrator H:** tratava todos os votos diferentes
de Branco ou Nulo como validos, ignorando numero 28
cujos votos nominais entraram como nulos tecnicos.
Assim, a explicacao aritmetica de +5.246 e concreta,
mas ainda precisa de conferencia de proveniencia nos
arquivos locais, UF por UF.

**Fase L publicada:** audit_bweb_candidate_28_2026.py,
e opcao L no start_windows.bat; valida SHA dos ZIPs originais
de 2026, soma somente NR_VOTAVEL 28 do turno 1/cargo
Presidente, cruza cada UF com as diferencas K e relata
todo residuo. Nao baixa, nao usa SQLite nem dados 2022.
171 testes de codigo passaram em Linux e Windows:
https://github.com/rubentrancoso/TSE/actions/runs/40519088095.
**Execucao com H: da opcao L ainda pendente**.

**Ponto separado:** diferenca de -42 entre contagem BU
e secoes totalizadas nacional ainda requer conciliar
definicoes/escopos; nao e explicada automaticamente
pelo caso do candidato 28.

Relatorio: docs/FASE5G_IDENTIFICACAO_5246_VOTOS_2026.md.


---

## 2026-10-27 — E0111 — Conciliacao L definitiva e teste M implementado

**Execucao real Windows, primeira votacao presidencial 2026:**
opcao L concluiu com status CONCILIACAO_COMPLETA_NR_28,
5.246 votos do numero presidencial 28, 5.246 votos
a mais no antigo calculo de validos, 28/28 UFs
reconciliadas com residuo ZERO em cada UF.
Os votos 13 e 22 haviam fechado por UF na etapa K.
A suposta divergencia inicial em AC (+1) no
inicio do terminal veio exclusivamente de teste
sintetico no diretorio Temp.

**Correcao na pesquisa temporal:** fase M acrescentada
ao menu e implementada em
correct_bweb_28_periodicity_2026.py.
Pelo mapa n28 por secao com checkpoints SHA-256,
subtrai os votos 28 da contagem de validos do mesmo
BU, e refaz as series por minuto, por segundo e blocos
500/1000/2000 sem alterar arquivos H/J/K/L.
Exige 119.300.788 validos, Lula 53.879.538,
Flavio 56.104.503 e 5.246 nulos tecnicos corrigidos.
Reusa ZIPs BWEB originais de 2026 sem download;
na primeira execucao necessita nova leitura apenas
das colunas para identificar qual secao votou 28,
porque L armazenou somente somas por UF.
Sem SQLite nem microdados de 2022.

**Estado:** M validada somente com fixture; ainda
nao executada sobre os BWEB reais locais.
176 testes de codigo passaram em Windows/Linux:
https://github.com/rubentrancoso/TSE/actions/runs/40522038862

Continuam separados: (1) periodicidade corrigida,
(2) divergencia de 42 secoes entre as duas contagens,
sem identidades por secao demonstradas.

Detalhes: docs/FASE5H_CORRECAO_E_RETESTE_2026.md.
