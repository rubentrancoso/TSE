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
