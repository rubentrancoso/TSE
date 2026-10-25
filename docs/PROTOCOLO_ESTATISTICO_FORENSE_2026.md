# Protocolo de analise estatistica forense nacional — 2026

**Estado em 25/10/2026:** proposta de pesquisa, ANTES de executar novos modelos. **Prioridade operacional:** despriorizar o stress territorial de zonas (opcao E). Examinar a base nacional completa, sem preselecionar candidatos, municipios ou zonas suspeitos. Somente dados eleitorais de 2026; nao importar microdados de 2022.

## O que ja existe

O modulo statistical_forensics.py ja implementa Benford, digitos finais, mediana/MAD, relacao comparecimento-votacao, perfil 10x10, assimetria/curtose e consistencias. Sao estatisticas descritivas, sem simulacoes territoriais nulas calibradas, validacao de falsos positivos ou ajuste completo dos testes multiplos. Nao repetir downloads, reindexacao do SQLite de 221 GiB ou coleta de BU.

## Fase 0 — Base e denominadores

Gerar/reusar, verificando SHA-256, matriz de secoes com UF, municipio, zona, secao, turno, votos para Presidente por candidato (incluindo brancos/nulos e total de validos), cargos pareados onde existentes, e QT_APTOS/QT_COMPARECIMENTO somente se esses campos forem identificados na mesma secao em fonte verificavel. Registrar cobertura e ausencias. Participacao eleitoral exige comparecimento/aptos; nao substituir por votos_validos/aptos. Para Senado observar duas escolhas por eleitor. Separar votos em transito/exterior e secoes sem o cargo. Sem campos, declarar nao executado, nunca imputar valores.

## Testes estatisticos propostos

### T1 — Fingerprint comparecimento x apoio (Klimek et al., PNAS 2012)

Taxas: turnout = comparecimento / aptos e apoio = votos_candidato / validos_presidenciais. Comparar distribuicao conjunta observada com modelos nulos simulados, condicionados a tamanho de secao e heterogeneidade municipio/zona. Investigar excesso de massa em turnout/apoio simultaneamente altos e dependencia da escala geografica. So executar com aptos/comparecimento confirmados; respeitar causas legitimas de caudas e participacao elevada.

### T2 — Modelo hierarquico binomial / beta-binomial

Modelar votos por candidato dado o total valido e agrupamento territorial. Medir superdispersao, caudas e residuos preditivos fora da amostra em blocos geograficos. A nulidade nao exige mesma intencao de voto em todas as secoes. Teste prioritario quando os campos de turnout estiverem incompletos.

### T3 — Picos em percentuais especificos (Rozenas, 2017)

Verificar concentracoes em percentuais e fracoes exatas (50%, 60%, 2/3 etc.) por simulacao discreta/resampled kernel density condicionada aos denominadores reais. Numeros redondos aparecem naturalmente em contagens inteiras; avaliar apenas EXCESSO em relacao a nulo adequadamente calibrado.

### T4 — Digitos e arredondamentos

Testar heaping nos digitos finais e numeros multiplos de 5, 10 e 100 com simulacao condicionada a tamanho das secoes. Benford segundo digito como diagnostico auxiliar e primeiro digito sem status de teste principal; nao presumir que votos por secao obedecam universalmente a Benford ou que ultimos digitos sejam exatamente uniformes.

### T5 — Residuo multivariado por cargo

Analise conjunta de resultados para Presidente, Governador e Senado, apenas em secoes com pares de cargos validos e denominadores comparaveis. Condicionar a municipio/zona, tamanho e regime de votacao. Nao deduzir escolhas individuais ou rotulos ideologicos.

### T6 — Assinaturas algoritmicas inespecificas

Examinar residuos fora da amostra para periodicidade, arredondamento, repeticao excessiva e precisao anomalamente alta de formulas candidatas. Rejeitar apenas formas matematicas especificadas. Nao confundir ajuste a dados publicados com alteracao entre urna e publicacao: sem BU contemporaneo independente, D = Y - X nao e observavel.

## Regras obrigatorias de inferencia

1. Registrar ANTES os testes, estatisticas, filtros, seeds, unidades, grupos e criterio de decisao; nao selecionar so resultados favoraveis.
2. Simular distribuicoes nulas realistas que preservem denominadores e heterogeneidade territorial. Testar o ajuste preditivo; se nao aderir, registrar MODELO_NULO_INADEQUADO.
3. Usar treinos e validacoes por blocos territoriais; testar significancia com simulacao e relatar tamanho de efeito e incerteza.
4. Calibrar falsos positivos em dados sinteticos sem perturbacao e poder de deteccao em dados sinteticos com contaminacao conhecida. A injeccao e um teste de desempenho, nao uma hipotese assumida verdadeira na eleicao.
5. Corrigir multiplicidade (por exemplo BH-FDR q <= 0,01 onde adequado, mais estatisticas maximas simuladas quando necessarias para dependencia); manter relatorio COMPLETO, inclusive testes negativos.
6. Nunca converter p-valor, q-valor, parametro ajustado ou score anomalico em probabilidade de fraude. Sem rotulos independentes nao existe classificador validado de fraude real.
7. Anomalia de um modelo nao e prova de adulteracao eleitoral nem de um mecanismo especifico.

## Sequencia operacional proposta

**Primeiro:** inspecionar cobertura da matriz existente e construir/reutilizar compactacao de base nacional sem recaptura ou reindexacao. **Segundo:** T1 se houver aptos/comparecimento suficientes; caso contrario T2 + T3, que usam apenas BUs existentes. **Terceiro:** T4, T5 e T6. Gerar em pasta nova analysis/estatistica_forense_2026 arquivos de cobertura, protocolo, nulos simulados, todos os resultados e anomalias replicadas, com hashes, denominadores e metadados.

## Referencias

- Klimek et al. (2012), PNAS: https://doi.org/10.1073/pnas.1210722109
- Rozenas (2017), Political Analysis: https://doi.org/10.1017/pan.2016.9
- Montgomery et al. (2015), Political Analysis: https://doi.org/10.1093/pan/mpv023
- Deckert et al. (2011), Political Analysis: https://doi.org/10.1093/pan/mpr014

**Status:** apenas o protocolo foi publicado nesta fase; nenhuma nova analise empirica T1–T6 foi executada.
