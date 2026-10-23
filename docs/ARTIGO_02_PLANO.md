# Artigo 2 — Do agregado nacional ao Boletim de Urna
## Plano editorial e rastreabilidade — NÃO É VERSÃO PARA PUBLICAÇÃO

**Continuação direta de:** [O gráfico travou. O que os dados realmente mostram até agora](ARTIGO_PUBLICO.md).

**Estado em 16/10/2026:** programa ampliado; coleta de microdados iniciada no
computador do investigador, ainda sem relatório de conclusão da coleta e dos
testes auditado nesta etapa. Nenhuma conclusão nova sobre discrepâncias
urna a urna está validada para publicação.

### Ponto em que o artigo 1 terminou

- Resultado nacional, UFs e municípios foram comparados em fotografias oficiais.
- A cronologia do painel foi reconstruída a partir de capturas públicas.
- Com o corte independente 20:05:57, a reconstrução geográfica da cauda
  pós-retomada pode cobrir 18.480.901 votos válidos (98,25% do pool
  iniciado às 20:04:39). Atribuição exata dos 328.755 votos anteriores
  ao corte independente permanece pendente.
- As verificações por BU/seção não estavam disponíveis na coleta original.
- A causa técnica do atraso de publicação e a separação entre recepção,
  totalização e publicação ainda não estavam esclarecidas.

A narrativa posterior **não deve alterar retrospectivamente o artigo 1**.
Se surgir correção, explicá-la no artigo 2 e no diário, mantendo a versão
anterior.

### Pergunta do artigo 2

> Depois de obter os boletins de urna e os dados de votação por seção,
> conseguimos reproduzir os agregados oficiais, identificar os arquivos
> e horários de cada seção, e explicar ou reduzir as lacunas da primeira
> investigação?

### Sequência editorial (preencher somente com saídas verificadas)

1. **A publicação posterior dos dados:** datas do catálogo consultado,
   URL, identificadores dos recursos e o que o coletor antigo efetivamente
   procurava. Diferenciar ausência no CKAN de ausência no serviço de
   arquivos por seção.
2. **Cadeia de custódia:** número de recursos e UFs cobertos, downloads
   reutilizados, erros, tamanho, hashes SHA-256, versões de código e ID
   de execução em `analysis/history/runs/`.
3. **Reconciliação de votos:** BU ↔ votação por seção ↔ município ↔ UF
   ↔ país, com o mesmo turno/cargo, seções agregadas e tratamento
   dos campos de votos brancos/nulos/legenda.
4. **O que houve após a meia-noite:** distinguir momento de registro de
   voto, encerramento da votação, geração do BU, envio, recepção e
   publicação; não inferir a hora de um voto a partir do horário de
   atualização do painel.
5. **Análises estatísticas:** Benford, dígitos finais, forma das
   distribuições, anomalias locais, participação e simulações
   quando sustentadas por modelo de referência. Mostrar também
   resultados negativos e testes inaplicáveis.
6. **Comparação 2022 versus 2026:** confrontar geografia e composição
   das mesmas zonas apenas após harmonizar códigos e coberturas.
7. **O que ficou sem resposta:** lacunas de dados, impossibilidade de
   decodificar completamente binários RDV/log na fase atual,
   limites de independência de fontes originadas no mesmo sistema.
8. **Conclusão proporcional:** demonstrar quais somas coincidem e
   quais divergem, sem inferir mecanismo de fraude a partir de
   padrões agregados.

### Novo diagnóstico — 23/10/2026 (não publicar como discrepância de votos)

O relatório local fornecido pelo investigador contém **3.800.739
chaves SEM_SECAO** no primeiro turno, distribuídas entre:
**3.800.511 chaves de Presidente (cargo 1)** e
**228 chaves de Conselheiro Distrital (cargo 25), somente PE**.

A investigação do código identificou que o reconciliador antigo
não usava o CSV **nacional de votação por seção de Presidente**
(`secao_nacional`), embora fosse uma fonte armazenada à parte.
Esta é uma **falha de seleção de fonte pelo software**, não uma
evidência de votação inexistente. O motor v2 inclui uma comparação
deduplicada usando a fonte nacional como complemento dos dados
estaduais, mas a eficácia quantitativa ainda **depende da execução
real e da confirmação de importação da fonte**.

Os 228 casos de cargo 25 são compatíveis com o escopo diferente
da **eleição de Conselheiro Distrital em Fernando de Noronha**, que
ocorreu com as eleições gerais e possui 10 seções segundo o TSE.
Falta examinar os registros concretos por seção e localizar o
conjunto adequado de votação do pleito local.

O único recurso em erro foi o ZIP de arquivos **transmitidos** de SP,
que falhou em CRC. O novo recuperador preserva o arquivo suspeito
e tenta uma transferência limpa. Esse problema de integridade
do ZIP é independente dos campos de votos CSV do conjunto
estadual/nacional usados na reconciliação.

**Condição para escrever a seção de resultados:** versão v2 executada
e guardada, origem da informação nacional confirmada no SQLite,
número de chaves faltantes antes/depois confrontado, arquivo SP
validado e status dos casos especiais de Noronha declarado.

Fonte oficial sobre Noronha:
https://www.tse.jus.br/comunicacao/noticias/2026/Outubro/eleitores-de-fernando-de-noronha-elegem-7-conselheiros-distritais

### Evidências necessárias antes da publicação

| Prova | Arquivo/controle | Estado |
| --- | --- | --- |
| Inventário e download integral | `download_manifest_latest.json` + SHA256 de fontes | **Aguardando resultado validado da coleta** |
| BU ↔ seção | `reconciliacao_bu_secao.csv` e resumo | **Aguardando análise dos dados reais** |
| Candidatos/cargos | `votos_por_cargo_candidato.csv` | **Aguardando análise dos dados reais** |
| Estatística por seção | `analysis/estatistica/*.csv` | **Aguardando análise dos dados reais** |
| Cobertura e exclusões | `estatistica_resumo.json` | **Aguardando análise dos dados reais** |
| Versão exata dos relatórios | `analysis/history/runs/<run-id>.json` | **Novo mecanismo de preservação implementado** |
| Reconstrução 4J completa | `phase4j_summary.json` e tabela por UF | **Exigir versionamento/validação do resultado, não inferir do script** |
| RDV/log interpretáveis | parser validado + evento/tempo + controle de integridade | **Pendente** |
| Narrativas alternativas | confronto entre atraso de publicação e atraso de recepção/totalização | **Pendente** |

### Regras para o texto final

- Cada número publicado deve trazer pelo menos uma referência a um
  arquivo de resultados, uma versão do código e um SHA-256 de entradas.
- Uma comparação de dois CSVs publicados pelo TSE confirma a
  consistência entre esses arquivos, não a autenticidade física
  independente de cada voto.
- O horário de totalização não deve ser chamado de horário do voto.
- O texto deve apresentar hipóteses concorrentes, limites e resultados
  que contrariem qualquer hipótese inicial.
- Não publicar resultados derivados de amostra incompleta como se
  representassem todas as seções.
- O diário cronológico é append-only: correções serão novas entradas.
- Arquivos grandes ficam no drive H: e **não** serão publicados no Git
  apenas para demonstrar existência. O relatório precisará de hashes,
  URLs oficiais e instruções reproduzíveis.

### Fontes de trabalho

- [Diário cronológico](DIARIO_INVESTIGACAO.md)
- [Protocolo formal](INVESTIGACAO_TOTALIZACAO_2026.md)
- [Reprodutibilidade e proveniência](REPRODUCIBILITY.md)
- [Métodos estatísticos](METODOS_ESTATISTICOS_2026.md)
- [Código de coleta](../urnas.py)
- [Histórico de análises](../history_forensics.py)
