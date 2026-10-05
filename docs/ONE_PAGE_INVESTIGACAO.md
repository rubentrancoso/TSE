# Estado da investigação — one page

Atualizado em 2026-10-05.

## Pergunta central

Investigar de forma reproduzível a defasagem observada na divulgação da eleição presidencial de 2026, separar atraso/publicação/composição geográfica de discrepância material de votos e testar alegações específicas sem presumir fraude nem normalidade.

## Cadeia de evidência

1. Dados oficiais e externos preservados em `data/forensics/`, com hashes/manifests quando aplicável.
2. Scripts de análise versionados na raiz do repositório.
3. Resultados derivados em `data/forensics/analysis/`.
4. Registro cronológico em `docs/DIARIO_INVESTIGACAO.md`.
5. Git como âncora temporal e de reprodutibilidade.

## O que está estabelecido

- O resultado final nacional fecha exatamente com a soma das UFs; não foram encontrados erros aritméticos internos nos JSONs analisados.
- As divergências auxiliares BA/MG eram arquivos EA20 municipais defasados em relação ao agregado estadual, não seções estruturais extras.
- Capturas contemporâneas independentes confirmam forte defasagem do arquivo nacional de Presidente. No principal destravamento, 19:14:08→20:04:39, entraram 100.614 seções e 24.728.306 votos válidos no arquivo nacional.
- Após 20:04:39, Lula sobe e Flávio desce em 152/152 transições quando os percentuais são recalculados dos totais inteiros.
- O pool efetivamente restante após 20:04:39 contém 18.809.656 votos válidos: Lula 54,0881%, Flávio 39,3429%.
- A monotonicidade é invariante à ordem dos mesmos 152 lotes; portanto `(1/2)^152` não é um modelo probabilístico válido para o fenômeno.
- Zonas que concluem mais tarde são estruturalmente mais pró-Lula. Esse gradiente também aparece nas mesmas zonas em 2022.
- Na Fase 4H, no corte 20:04, a diferença LATE−EARLY da margem foi +24,39 pp em 2026 e +23,64 pp em 2022; delta histórico de apenas +0,75 pp.
- O total final das zonas ainda incompletas às 20:04 é 3,46× maior que o pool real restante. Logo horário de conclusão de zona caracteriza a geografia tardia, mas não reconstrói sozinho os votos que entraram depois do corte.\n- A Fase 4I mostrou que os snapshots locais cobrem apenas 999.110 válidos, ou 5,31% do pool pós-20:04.\n- Uma captura independente já preservada às 20:05:57 contém os 28 agregados exatos por UF/ZZ. Ela permite reconstruir 18.480.901 válidos, **98,25%** do pool pós-20:04; ficam sem geografia exata apenas 328.755 válidos (1,75%), correspondentes aos 78 segundos iniciais.

## Alegações já testadas

- “Candidatos menores ficaram congelados”: rejeitada pelos dados; eles também se moveram.
- “UFs pró-Lula sofreram mais travamentos técnicos”: não sustentada pela métrica de travamentos.
- “UFs pró-Lula estavam proporcionalmente menos apuradas”: sustentada.
- “58,3 milhões de votos do PL para Senado implicam 58,3 milhões de eleitores”: falso; o Senado tem duas escolhas por eleitor.
- “Lula nunca caiu e Flávio nunca subiu depois do travamento”: confirmada nos totais inteiros.
- “Essa sequência equivale a 152 eventos independentes de 50/50”: rejeitada.

## O que ainda falta

A lacuna geográfica foi reduzida drasticamente: a captura independente das 20:05:57 permite cobrir 98,25% do pool pós-retomada. Restam sem atribuição geográfica exata apenas 328.755 votos válidos entre 20:04:39 e 20:05:57.

Também permanece aberta a busca por uma série nacional de 2022 com resolução temporal comparável.

## Próxima fase

**Fase 4J — reconstrução geográfica quase completa do pool pós-retomada.**

Objetivos:
- reconstruir por UF o trecho 20:05:57→final;
- fechar o corte independente e o final;
- medir a composição Lula/Flávio dos 18,48 milhões reconstruídos;
- identificar quais UFs explicam o pool tardio;
- comparar essa geografia com os controles históricos já obtidos.
