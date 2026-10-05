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
