# Malha cartográfica das 27 UFs brasileiras — uso no painel público

Este diretório contém `brasil_ufs_ibge_simplificado.geojson` (GeoJSON
`FeatureCollection` com exatamente 27 unidades federativas, incluindo DF).
Cada polígono traz `properties.sigla`, `nome` e `cd_geocuf`.

## Proveniência e uso permitido

- Fonte cartográfica: [IBGE — Malhas Territoriais / API de malhas de UF](https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais/15774-malhas.html).
- Distribuição simplificada utilizada:
  [henriquemalvar/br-geojson — dist/estados.geojson](https://github.com/henriquemalvar/br-geojson/blob/main/dist/estados.geojson).
- Licença declarada pelo distribuidor: **CC0 1.0 Universal**.
- Blob Git SHA de origem: `d06e54a3a03519ae3fa48fe3d85da6c3558cd47d`.
- O arquivo foi incorporado **inalterado** ao repositório TSE. O script valida
  o conjunto fechado das 27 siglas das UFs antes de desenhar o mapa.

Os contornos foram simplificados para visualização e **não** devem ser
usados para aferir áreas, distâncias, fronteiras ou localização precisa
de seções eleitorais.

Nenhum resultado de votos vem do arquivo GeoJSON. As cores dos mapas
são calculadas somente dos arquivos BWEB derivados SHA-verificados:

1. **Recebimento tardio por UF:** proporção dos votos válidos da UF
   recebidos a partir de 20:04:39 no BWEB, a partir da Fase T;
2. **Contraste temporal por UF:** média do contraste Lula (pós − pré)
   nas zonas daquela UF com pelo menos 1.000 votos válidos de cada
   lado do corte, ponderada por votos tardios, a partir da Fase W;
3. **Macrorregiões:** agregação das UFs pela composição clássica das
   cinco grandes regiões IBGE (Norte, Nordeste, Centro-Oeste, Sudeste,
   Sul), com denominadores explícitos.

**ZZ é exterior, não UF brasileira.** Nunca projetar seus votos no
território da federação. As cores não são métricas de fraude e não
demonstram adulteração ou ilícito.
