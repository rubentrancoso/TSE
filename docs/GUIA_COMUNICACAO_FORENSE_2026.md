# Guia de comunicação pública da investigação forense TSE 2026

## Princípio e pergunta

**Pergunta pública:** há evidência verificável de votos presidenciais do primeiro turno de 2026 adulterados, acrescentados, omitidos ou contabilizados em desacordo com os boletins individuais?

Esta investigação deve procurar esses mecanismos **ativamente**. Isso exige hipóteses falsificáveis, documentação reproduzível e disposição para reconhecer explicações não fraudulentas quando os controles as sustentam. Investigar fraude não é rotular qualquer curva visualmente incomum como fraude.

O público não precisa aprender a métrica R² para avaliar se os votos foram contabilizados corretamente. R² é uma medida técnica de ajuste da forma, não critério de integridade eleitoral.

## Cadeia da prova

| Grau | O que se observa | Como divulgar | O que ainda não comprova |
|---|---|---|---|
| A — divergência individual auditável | BU de uma seção/candidato autenticado difere de resultado que afirma representar o mesmo BU | Publicar chaves, documentos verificáveis, hashes, método de reconciliação e tentativas de replicação | Motivo, autoria ou extensão de eventual irregularidade |
| B — incompatibilidade operacional documentada | Registros sincronizados da cadeia de recebimento/publicação não podem representar a sequência declarada | Mostrar relógios, semântica dos campos e cronologia exata | Alteração do número de votos sem rastrear a origem |
| C — diferença estatística persistente | Padrão robusto a controles geográficos e temporais | Mostrar distribuições, denominadores e hipóteses alternativas | Fraude, por si só |
| D — aparência incomum | Curva aparentemente reta, salto, agrupamento ou correlação | Apresentar como pergunta exploratória, sem insinuar prova | Qualquer mecanismo ilícito |

Não confundir "acima da previsão" com "votos acrescentados" e não chamar divergência entre relógios de voto inexistente.

## Evidências reproduzíveis já discutidas

- **Fase V — recebimento BWEB:** modelo municipal pré-20:04:39 subestimou a proporção de Lula nos BUs tardios em 2,06049 pontos percentuais, e o modelo por zona em 2,02346. São *erros de previsão*, não contagem de votos adulterados. 2.127 zonas com BUs dos dois lados concentram aproximadamente 257.869 votos Lula *acima do modelo municipal*, não votos inexistentes.
- **Fase W — placebos por horário BWEB:** contraste Lula pós menos pré dentro das zonas já estava positivo antes das 20h04. No corte original, 965 das 1.380 zonas elegíveis tinham aumento, mas conjuntos elegíveis mudam conforme o corte.
- **Fase X — publicação EA20:** 18.809.656 votos válidos publicados depois do corte, em 152 incrementos, agrupados em quatro blocos cronológicos com participação Lula de aproximadamente 50,8%, 52,5%, 53,4% e 60,2%. O R² da participação acumulada por seções era 0,99044; um contrafactual *circular* com proporção final constante e volumes reais alcançou aproximadamente 0,99885. Isso mostra que uma linha ainda mais lisa pode ocorrer sem exigir lotes uniformes.
- **Fase Y — condição recebimento/pub.:** teste de horários para votos válidos, Lula e Flávio. **Não publicar resultado numérico da Y sem sua execução local e validação de horários.**

**Limite essencial:** BWEB DT_BU_RECEBIDO e publicação EA20 são eventos distintos. Nunca atribuir a um lote EA20 os BUs recebidos no mesmo minuto sem identificadores que provem tal vínculo. Os arquivos locais usados podem vir das mesmas fontes oficiais; hash não significa origem independente.

## Um gráfico = uma pergunta + uma resposta + uma ressalva

Para cada visualização, use o seguinte roteiro:

1. **Pergunta popular:** "Os votos foram alterados?", "Por que essa linha parece reta?", "Os votos recebidos tarde vieram de lugares diferentes?".
2. **O que medimos:** fonte, horário, unidade (voto, BU, seção, zona), universo, denominador.
3. **Imagem reveladora:** preferir lotes incrementais, distribuição territorial, comparação antes/depois e desvios por seção, em vez de apenas R² da média acumulada.
4. **Resultado interpretável:** usar unidades cotidianas — votos, milhões, pontos percentuais — e identificar o período em cada gráfico.
5. **Explicação alternativa concreta:** geografia, fila de publicação, relógio, viés de composição ou distribuição dos tamanhos de seção.
6. **Prova que falta:** registro individual ou evento operacional que decida entre hipóteses.
7. **Conclusão graduada:** observado / explicado em parte / hipótese não sustentada / ainda inconclusivo.

**Evitar** cortar eixo vertical em gráfico de barras de proporções, exibir diferenças de previsão como votos irregulares, suprimir faixas de cobertura ou afirmar que o modelo retrospectivo previu um resultado futuro.

## Testes que realmente enfrentam a hipótese de fraude

### H1 — alteração do total por seção
**Previsão se ocorrer:** para uma seção definida por UF, município, zona, seção, turno e cargo, o documento BU autenticado contém votos de candidato diferentes do resultado público que deveria representar exatamente aquele BU.

**Controle:** lista completa de chaves; votáveis válidos e anulados; justificativa de ausências, retotalizações, seções no exterior e recontagens; assinatura/hash do BU; cópia verificável externa ao TSE, se possível.

**Critério de avanço:** divergência documentada em seção identificável, reproduzida por análise independente e não explicada por versão/escopo.

### H2 — inclusão ou omissão de seções
**Previsão se ocorrer:** conjunto publicado contém chave com votos sem BU correspondente, ou BU autenticado aparece ausente após a totalização definitiva.

**Controle:** distinguir seções totalizadas, aptas, agregadas, especiais, zero votante, locais ZZ e versões do resultado.

**Critério de avanço:** discrepância persistente após reconciliação completa por chave e voto.

### H3 — manipulação da divulgação
**Previsão se ocorrer:** logs de publicação e registros de recebimento assinados e sincronizados mostram retenção, reordenação ou envio impossível segundo a regra declarada.

**Controle:** semântica dos timestamps, fusos, capturas públicas não contínuas, versões EA20, cadeia intermediária.

**Critério de avanço:** incompatibilidade de cronologia auditável em fontes independentes; mesmo assim verificar se afetou voto ou apenas apresentação.

### H4 — padrões estatísticos incompatíveis com processamento legítimo
**Previsão se ocorrer:** anomalias persistentes depois de preservar geografia, tamanhos de seção, volume de lote, ordem e diferenças normais de recebimento.

**Controle:** simulações e placebos pré-especificados, comparação de poder preditivo fora da amostra, correção por múltiplos testes.

**Critério de avanço:** anomalia localizada e reproduzível que motive auditoria H1/H2/H3, **não prova isolada de fraude**.

## A narrativa deve mostrar o Brasil, do nacional ao território

O **mapa do Brasil é parte essencial da história visual** sempre
que a hipótese envolver diferenças geográficas. Mas cada mapa
deve responder a UMA pergunta específica, não servir como
ilustração ou imagem insinuando fraude.

O painel Jupyter público contém agora:

1. **Recepção tardia por UF (mapa 1):** porcentagem dos votos
   válidos da própria UF cujos BUs foram recebidos pelo BWEB
   desde 20:04:39. Denominador é o total da UF (não área e não
   número de UFs). O exterior (ZZ) é excluído.
2. **Mudança dentro das zonas por UF (mapa 2):** diferença média
   em pontos percentuais da participação de Lula entre BUs
   recebidos depois e antes do corte, apenas em zonas com
   >=1.000 votos válidos de ambos os lados. Ponderar cada
   zona pelos votos tardios e distinguir cobertura limitada.
3. **Cinco grandes regiões (gráfico 3):** Norte, Nordeste,
   Centro-Oeste, Sudeste e Sul, com contraste ponderado pela
   quantidade de votos tardios das zonas elegíveis. Exibir
   também número de votos e zonas por região na tabela.
4. **Progresso do Brasil para a seção:** agregar em nível
   nacional e regional para entender o panorama; aprofundar
   UFs/zonas com evidências concretas; por fim confrontar
   registros **individualizados** de BU e publicação antes
   de fazer afirmações sobre adulteração.

A malha vetorial é GeoJSON das 27 UFs, derivada de dados IBGE,
licença CC0; está incorporada offline em
`data/geografia/brasil_ufs_ibge_simplificado.geojson` com
proveniência em `data/geografia/README.md`. Não requer rede.

**Regras gráficas:** usar escala contínua, cor neutra e
legenda com unidade; barra comparativa começando em zero
quando mostrar composição de votos; deixar estados sem amostra
em cinza; indicar amostra mínima e ausência de ZZ. Não usar
cores como se fossem selo de crime ou como previsão eleitoral.

## Visualizações e relatório para o público

Abra a opção **U** do `start_windows.bat`: notebook central
`notebooks/TSE_2026_Painel_Publico_Forense.ipynb`.

A opção U usa os resultados locais SHA-verificados e produz:

- até 8 figuras PNG com legendas autoexplicativas, incluindo 2 mapas por UF e 1 gráfico regional (o confronto com EA20 tem dados reais apenas se Y foi executada);
- tabela de hipóteses e conclusões provisórias;
- página `relatorio_publico_forense_2026.html` com imagens incorporadas, para abrir e ler sem Jupyter.

As saídas ficam em `H:\TSE\forensics\urnas\analysis\periodicidade_bweb_2026\divulgacao_publica_2026`.

**Opção Z** mantém o laboratório Jupyter técnico de última fase. Não transformar os notebooks da pesquisa em peças de acusação; faça a revisão editorial do HTML antes de qualquer publicação.

## Rodapé obrigatório nos materiais públicos

> Investigação independente da apuração presidencial de 2026, primeiro turno, com dados de BWEB e capturas nacionais EA20. Alguns testes usam o mesmo universo de fontes oficiais e não representam auditoria independente de cada voto. Um desvio estatístico ou temporal não comprova, por si, fraude. Metodologia, código e arquivos derivados disponíveis no repositório do projeto.

Nenhuma figura deve ser distribuída sem referência à fase, unidade, período, origem e principal ressalva.
