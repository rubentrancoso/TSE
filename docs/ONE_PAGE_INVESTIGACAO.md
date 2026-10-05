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
- O total final das zonas ainda incompletas às 20:04 é 3,46× maior que o pool real restante. Logo horário de conclusão de zona caracteriza a geografia tardia, mas não reconstrói sozinho os votos que entraram depois do corte.

## Alegações já testadas

- “Candidatos menores ficaram congelados”: rejeitada pelos dados; eles também se moveram.
- “UFs pró-Lula sofreram mais travamentos técnicos”: não sustentada pela métrica de travamentos.
- “UFs pró-Lula estavam proporcionalmente menos apuradas”: sustentada.
- “58,3 milhões de votos do PL para Senado implicam 58,3 milhões de eleitores”: falso; o Senado tem duas escolhas por eleitor.
- “Lula nunca caiu e Flávio nunca subiu depois do travamento”: confirmada nos totais inteiros.
- “Essa sequência equivale a 152 eventos independentes de 50/50”: rejeitada.

## O que ainda falta

A principal lacuna é reconstruir geograficamente o conjunto exato de 18.809.656 votos incorporados depois de 20:04:39. Os snapshots locais conhecidos começam cerca de 21:20 BRT, portanto podem cobrir somente a cauda desse pool. A reconstrução completa exige histórico de versões por UF/município/zona no corte de 20:04, como o banco bruto do coletor externo ou fonte temporal equivalente.

Também permanece aberta a busca por uma série nacional de 2022 com resolução temporal comparável.

## Próxima fase

**Fase 4I — auditoria de cobertura e reconstrução da cauda local.**

Objetivos:
- medir exatamente quanto do pool pós-20:04 é coberto pelos snapshots locais;
- reconstruir por UF o trecho entre o primeiro snapshot local útil e o final;
- reconciliar essa soma com o delta nacional;
- registrar quantitativamente a lacuna 20:04→primeiro snapshot local;
- decidir se a próxima etapa exige obter o histórico bruto externo ou se os dados locais bastam.
