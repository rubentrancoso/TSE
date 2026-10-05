# Investigação da interrupção/defasagem na divulgação presidencial — Eleições 2026

**Status:** protocolo de investigação v0.1  
**Escopo:** 1º turno de 04/10/2026  
**Objetivo:** reconstruir, de forma reprodutível, o que ocorreu durante a janela em que a divulgação nacional para Presidente deixou de avançar enquanto resultados estaduais continuaram sendo atualizados, e testar hipóteses concorrentes sem presumir a conclusão.

---

## 1. Princípio metodológico

Esta investigação parte de uma distinção rigorosa entre:

1. **fato observado** — algo diretamente verificável em arquivo oficial, Boletim de Urna, log, timestamp, assinatura, snapshot preservado ou outra fonte primária;
2. **anomalia** — divergência, interrupção, atraso ou padrão quantitativo que exige explicação;
3. **hipótese** — explicação possível para a anomalia;
4. **evidência de fraude** — conclusão muito mais forte, que exige demonstrar discrepância material nos votos, mecanismo de alteração e/ou incompatibilidade com os artefatos oficiais da votação.

Uma curva incomum, um atraso de publicação ou uma mudança brusca de percentual podem justificar investigação, mas não serão tratados, isoladamente, como prova de fraude.

---

## 2. Premissas documentadas

### P1 — A urna apura os votos da própria seção e gera um único conjunto de artefatos ao final da votação

A Resolução TSE nº 23.751/2026 determina que, ao final da votação, os votos sejam apurados eletronicamente e sejam gerados e assinados digitalmente o Boletim de Urna (BU), o Registro Digital do Voto (RDV) e os demais arquivos.

Fonte oficial:  
https://www.tse.jus.br/legislacao/compilada/res/2026/resolucao-no-23-751-de-26-de-fevereiro-de-2026

### P2 — O BU contém a votação por candidato e por cargo da mesma seção

O TSE informa que o BU registra votação individual de candidatas e candidatos, votos em branco e nulos e totais agrupados por cargo. A mesma seção produz os dados usados para Presidente, Governador, Senado e demais cargos.

Fontes oficiais:  
https://www.tse.jus.br/eleicoes/processo-eleitoral-brasileiro/votacao/votacao-segura  
https://www.tse.jus.br/legislacao/compilada/res/2026/resolucao-no-23-751-de-26-de-fevereiro-de-2026

**Implicação investigativa:** se uma seção já teve seus dados recebidos/processados para cargos estaduais, existe um fundamento forte para verificar se os dados presidenciais da mesma seção também já estavam disponíveis no conjunto de arquivos daquela urna.

### P3 — Apuração e totalização são etapas distintas

Segundo o TSE, a urna faz a apuração local e gera o BU. Em seguida, os dados das urnas são reunidos e somados na totalização.

Fonte oficial:  
https://www.tse.jus.br/comunicacao/noticias/2026/Outubro/entenda-a-diferenca-entre-apuracao-e-totalizacao-de-votos

### P4 — A totalização presidencial segue um caminho institucional diferente dos demais cargos

A Justiça Eleitoral informa que os resultados para Governador, Senador e Deputados são processados nos TREs, enquanto o TSE faz a totalização e a divulgação da eleição para Presidente da República.

Fontes oficiais:  
https://www.tse.jus.br/eleicoes/historia/processo-eleitoral-brasileiro/divulgacao-de-resultados  
https://www.tse.jus.br/legislacao/compilada/res/2026/resolucao-no-23-751-de-26-de-fevereiro-de-2026

**Implicação investigativa:** uma paralisação exclusiva do agregado nacional presidencial pode ocorrer em uma camada posterior ao recebimento dos BUs; por isso precisamos separar, quantitativamente, **recebimento do BU**, **totalização estadual/federal** e **publicação na CDN/site**.

### P5 — Os dados oficiais de divulgação são públicos e estruturados

Para 2026, o ambiente oficial usa:
- eleição federal: **6257**;
- eleições estaduais: **6259**;
- arquivos de acompanhamento EA14/EA15;
- configuração de seções EA16;
- arquivo auxiliar da seção EA18;
- resultado unificado EA20;
- arquivos assinados JWS.

Fonte oficial:  
https://www.tse.jus.br/eleicoes/informacoes-tecnicas-sobre-a-divulgacao-de-resultados

### P6 — O próprio TSE documenta que arquivos podem aparecer em momentos diferentes na CDN

A documentação técnica informa que EA14/EA15 e EA20 são gerados em paralelo e depois sincronizados/distribuídos pela CDN, de forma que podem ocorrer diferenças no instante em que cada arquivo reflete a atualização.

Fonte oficial:  
https://www.tse.jus.br/eleicoes/informacoes-tecnicas-sobre-a-divulgacao-de-resultados

Essa possibilidade deverá ser **medida**, não presumida como explicação suficiente.

### P7 — EA16/EA18 permitem reconstruir a chegada dos arquivos das seções

O TSE informa que o EA16 possui atributos de data/hora associados à geração do arquivo auxiliar da seção e que esses campos podem indicar a chegada dos arquivos de urna. O EA18 permite chegar aos artefatos específicos de cada seção.

Fonte oficial:  
https://www.tse.jus.br/eleicoes/informacoes-tecnicas-sobre-a-divulgacao-de-resultados

---

## 3. Evento que motiva a investigação

Há registro jornalístico de que a divulgação presidencial permaneceu sem atualização por aproximadamente uma hora enquanto informações estaduais continuaram sendo atualizadas. A reportagem registrou 64,81% às 19h06 e retorno da plataforma às 20h08 com 84,96%. A mesma reportagem afirmou que, segundo sua apuração, a totalização não teria parado e o problema teria sido um atraso no “espelho” do site; essa afirmação precisa ser testada contra os dados técnicos.

Fonte secundária:  
https://www.metropoles.com/brasil/sistema-do-tse-fica-travado-por-mais-de-1-hora-devido-a-volume-de-dados

**Importante:** o relato jornalístico serve para definir a janela temporal da investigação. Não será usado como prova técnica da causa.

---

## 4. Evidência preliminar já preservada

Nossa captura histórica secundária contém uma descontinuidade relevante:

| Horário informado no dado | Seções | % seções | Votos válidos |
|---|---:|---:|---:|
| 18:44:02 | 235.931 | 47,2573% | 54.746.502 |
| 19:13:55 | 349.344 | 69,9740% | 82.085.920 |

Diferença entre os pontos:
- **+113.413 seções**
- **+22,7167 pontos percentuais de seções**
- **+27.339.418 votos válidos**

No segundo ponto, o coletor secundário registrou a marca `somado_dos_estados=true`, ou seja, passou a reconstruir o nacional pela soma das UFs porque essa soma estava adiante do arquivo nacional consultado.

Esta é uma **pista operacional**, não uma prova final. O arquivo vem de uma captura independente e deverá ser confrontado com fontes primárias do TSE.

Fonte da captura secundária:  
https://github.com/pedreirorr/painel-eleicao-2026/tree/dados

---

## 5. Hipóteses concorrentes

### H0 — Atraso apenas na camada de publicação nacional

Os BUs e/ou totais das UFs continuaram avançando, mas o EA20 nacional presidencial/site/CDN ficou atrasado.

**Predições testáveis:**
- arquivos estaduais/municipais/seções continuam recebendo timestamps novos;
- a soma independente das UFs avança enquanto o nacional fica constante;
- quando o nacional retorna, converge exatamente para a soma dos dados inferiores;
- BUs individuais não apresentam discrepância.

### H1 — Paralisação específica da totalização presidencial

Os BUs chegaram, cargos estaduais continuaram sendo processados, mas a totalização presidencial deixou temporariamente de incorporar novas seções.

**Predições testáveis:**
- seções aparecem no fluxo estadual antes de aparecerem no agregado presidencial;
- timestamps de recebimento dos arquivos existem durante a janela;
- a soma presidencial construída diretamente dos BUs avança, mas os EA20 presidenciais oficiais ficam estáticos.

### H2 — Defasagem de CDN/cache sem paralisação lógica do sistema

Os arquivos foram gerados internamente, mas diferentes objetos/abrangências chegaram à CDN em tempos diferentes.

**Predições testáveis:**
- `idg`, horários de geração/totalização e cabeçalhos HTTP mostram geração anterior à disponibilização observada;
- divergência desaparece sem diferença de conteúdo final;
- o fenômeno varia entre endpoints/abrangências.

### H3 — Discrepância material nos votos presidenciais

O agregado presidencial posterior não é reconciliável com a soma dos BUs/UFs correspondentes.

**Predições testáveis:**
- `Presidente publicado != soma exata dos BUs presidenciais` para o mesmo conjunto de seções;
- votos de um ou mais candidatos não fecham contabilmente;
- há seções incluídas/excluídas de modo não explicado pela documentação;
- discrepância persiste após controlar versões, seções anuladas, substituídas, voto em trânsito e reprocessamentos.

Esta é a hipótese que, se confirmada com dados primários, elevaria substancialmente a gravidade da investigação.

---

## 6. Testes matemáticos principais

### T1 — Reconciliação nacional × UFs

Para cada instante (t):

[
R_c(t)=V^{BR}_c(t)-sum_{u in UF+ZZ}V_{c,u}(t)
]

onde:
- (V^{BR}_c(t)) = votos nacionais publicados para o candidato (c);
- (V_{c,u}(t)) = votos publicados/reconstruídos para o candidato (c) na UF (u).

Registrar:
- erro absoluto;
- erro relativo;
- número de seções em cada lado;
- duração da divergência.

**Resultado esperado em regime normal:** diferença zero ou transitória por sincronização, convergindo rapidamente.

### T2 — Reconstrução diretamente dos BUs

Definir (S(t)) como o conjunto de seções cujos arquivos estavam disponíveis/recebidos até (t).

Para cada candidato presidencial:

[
P_c(t)=sum_{sin S(t)}BU_{s,c}
]

A curva (P_c(t)) será comparada com:
- EA20 nacional;
- EA20 por UF;
- snapshots preservados.

Esta reconstrução independe do gráfico oficial nacional.

### T3 — Mesmo conjunto de seções, cargos diferentes

Para cada UF e instante (t), comparar a lista de seções já incorporadas no cargo estadual com a lista presidencial.

Pergunta central:

> Existem seções que já contribuíam para Governador/Senado/Deputados enquanto seus votos presidenciais permanececiam ausentes da totalização presidencial?

O teste será feito por **identificador de seção**, não apenas por percentuais agregados.

### T4 — Velocidade e backlog

Para intervalos consecutivos:

[
Delta S = S_{t_2}-S_{t_1}
]

[
Delta V = V_{t_2}-V_{t_1}
]

[
q_c=rac{Delta V_c}{Delta V_{válidos}}
]

Isso permite determinar:
- tamanho do backlog acumulado;
- velocidade antes/durante/depois da interrupção;
- composição eleitoral do lote incorporado após a retomada.

Não será pressuposto que lotes sucessivos devam ter a mesma composição política, pois a ordem geográfica das seções não é aleatória.

### T5 — Conservação contábil

Para cada snapshot e abrangência:

[
sum_c V_c = V_{válidos}
]

e, quando os campos forem comparáveis:

[
Comparecimento = V_{válidos} + Brancos + Nulos
]

Também serão procurados:
- totais acumulados que diminuem;
- número de seções que diminui;
- reprocessamentos;
- duplicações;
- lacunas inexplicadas.

### T6 — Integridade final por seção

No final da eleição:

[
V^{final}_{c}= sum_{todas as seções válidas} BU_{s,c}
]

A soma será comparada ao resultado oficial final por candidato, UF e Brasil.

### T7 — Assinaturas, hashes e geração

Sempre que possível:
- baixar versão JWS;
- verificar assinatura conforme manual do TSE;
- calcular SHA-256 local;
- preservar `idg`, `dg/hg`, `dt/ht`, ETag e Last-Modified;
- nunca sobrescrever o arquivo bruto original.

---

## 7. Testes que NÃO serão usados como prova isolada

Não serão tratados como evidência suficiente de fraude:

- Lei de Benford aplicada ingenuamente a totais eleitorais;
- “curva lisa demais” ou “curva estranha” sem controlar geografia;
- mudança rápida de percentual;
- correlação visual;
- distribuição de último dígito sem modelo apropriado;
- comparação com pesquisas eleitorais;
- ausência de atualização de uma página web sem verificar os arquivos subjacentes.

Esses métodos podem gerar perguntas exploratórias, mas não sustentam sozinhos uma conclusão causal.

---

## 8. Cadeia de custódia digital

Todos os dados usados na análise deverão obedecer a este procedimento:

1. salvar o arquivo bruto exatamente como recebido;
2. registrar URL completa;
3. registrar horário de coleta em UTC e Brasília;
4. registrar cabeçalhos HTTP relevantes;
5. calcular SHA-256;
6. verificar JWS quando disponível;
7. armazenar o bruto em diretório somente-leitura;
8. gerar arquivos derivados em diretório separado;
9. versionar scripts e documentação no Git;
10. registrar qualquer transformação de dados.

Estrutura proposta:

```
investigacao/
  raw/
    tse/
      ea14/
      ea15/
      ea16/
      ea18/
      ea20/
      bu/
  derived/
  hashes/
  scripts/
  reports/
```

---

## 9. Hierarquia de evidências

### Nível A — Fonte primária
- BU oficial;
- EA16/EA18/EA20;
- JWS assinado;
- logs oficiais da urna;
- RDV quando aplicável;
- documentação técnica do TSE.

### Nível B — Captura independente contemporânea
- snapshots de terceiros que preservaram respostas do endpoint oficial;
- nossa própria base SQLite/JSON coletada em tempo real.

### Nível C — Registro jornalístico/tela
- reportagens;
- screenshots;
- transmissões;
- relatos públicos.

Conclusões quantitativas serão baseadas prioritariamente em A. B será usado para reconstrução temporal quando A não preservar versões históricas. C será usado principalmente para cronologia e formulação de hipóteses.

---

## 10. Critérios de conclusão

A investigação não usará apenas “suspeito/não suspeito”. Cada achado será classificado:

### C0 — Explicado
A divergência é completamente reconciliável com geração paralela, cache/CDN, ordem de processamento ou outra regra documentada.

### C1 — Anomalia operacional reproduzível
Existe interrupção/defasagem demonstrável, mas todos os votos fecham com os BUs.

### C2 — Inconsistência técnica não explicada
Há discrepância persistente entre camadas oficiais que não é explicada pela documentação disponível.

### C3 — Discrepância de votos
O resultado de uma abrangência não reconcilia com a soma dos BUs/seções correspondentes.

### C4 — Evidência adicional de mecanismo
Além da discrepância C3, existem artefatos que indicam modificação, substituição indevida, falha de integridade ou outra causa específica.

Qualquer afirmação sobre fraude exigirá evidências compatíveis com C3/C4; matemática pode demonstrar discrepância, mas atribuição de intenção ou autoria exige evidência adicional.

---

## 11. Primeiras tarefas executáveis

1. **Preservar os 354 snapshots** já recuperados da captura histórica.
2. **Extrair a janela 18:30–20:15** e identificar exatamente os pontos em que:
   - nacional presidencial parou;
   - soma das UFs continuou;
   - nacional voltou a alcançar as UFs.
3. Baixar EA14/EA15/EA16/EA18 atuais e mapear a estrutura de todas as seções.
4. Baixar BUs/arquivos auxiliares das seções necessárias para reconstruir a janela.
5. Criar tabela:
   `timestamp | seção | UF | presidente disponível? | governador disponível? | recebido em | totalizado em`.
6. Reconstruir Presidente independentemente a partir dos BUs.
7. Comparar reconstrução com:
   - nacional oficial;
   - soma por UF;
   - captura histórica.
8. Publicar primeiro relatório técnico com todos os scripts reproduzíveis.

---

## 12. Perguntas que a investigação precisa responder

1. Qual foi o instante exato em que o agregado presidencial deixou de avançar?
2. Por quanto tempo ficou defasado?
3. Quantas seções e quantos votos chegaram nesse intervalo?
4. Essas mesmas seções já apareciam nos resultados estaduais?
5. Os votos presidenciais dessas seções já estavam presentes nos BUs?
6. A soma das UFs continuou avançando?
7. O arquivo nacional estava congelado, atrasado ou apenas não divulgado?
8. Quando retornou, o nacional passou a coincidir exatamente com a soma inferior?
9. O lote acumulado após a retomada é integralmente explicável pelas seções que entraram?
10. O resultado final fecha exatamente com a soma dos BUs?
11. Existem diferenças de assinatura, hash, timestamp ou versão que indiquem reprocessamento?
12. Alguma divergência permanece depois de controlar seções anuladas, substituições e voto em trânsito?

---

## 13. Regra de transparência

Todo resultado relevante deverá vir acompanhado de:

- fonte;
- código utilizado;
- fórmula;
- população de seções analisada;
- período;
- arquivos/hash;
- limitações;
- teste de hipótese alternativa.

O objetivo é produzir uma análise que qualquer pessoa tecnicamente habilitada consiga reproduzir de forma independente.
