# Reconciliacao BU x secao — encerramento tecnico em 24/10/2026

## Resultado reproduzivel

Comando executado no Windows pelo investigador:

`python urnas.py reconcile --engine stream`

Motor: `reconcile-stream-v1`; fingerprint das fontes:

`8ab3ce83c8992b9a4be03587c0f2fc49e93d5d3247b76a182d4a2dac0a9ce6b2`

| Indicador | Valor |
| --- | ---: |
| Registros SQLite examinados | 140.699.402 |
| Registros elegiveis | 135.717.720 |
| Particoes SHA-256 verificadas | 256 / 256 |
| Chaves comparadas | 67.858.974 |
| Chaves com votos coincidentes | 67.858.746 |
| Chaves `SEM_SECAO` | 228 |
| Chaves `SEM_BU` | 0 |
| Chaves com `DIFERENTE` | 0 |
| Importacoes parciais reportadas | 0 |

Resumo: `analysis/reconciliacao_bu_secao.summary.json`.

CSV: `analysis/reconciliacao_bu_secao.csv`, SHA-256 observado:
`31db2a2915492fc07786ff79dc40c74a0d20f42d75d113a54e1c9be01c41ce5b`.

## Classificacao das 228 chaves nao pareadas

Diagnostico com `python audit_reconciliation.py`:

- todas as 228 chaves: `UF=PE`, `municipio=30015`, `zona=4`, `turno=1`, `cargo=25`;
- 10 secoes eleitorais distintas;
- 2.445 votos BU no conjunto de chaves;
- zero chaves repetidas no CSV; contadores CSV e resumo coincidem.

**Identificacao do pleito especial:** Conselho Distrital de Fernando
de Noronha, realizado no primeiro turno das eleicoes de 2026.

A pagina oficial de informacoes tecnicas do TSE distingue os codigos:

- `6257`: Eleicao Geral Federal;
- `6259`: Eleicoes Gerais Estaduais;
- `6261`: Eleicao Conselho Distrital.

Referencia: https://www.tse.jus.br/eleicoes/informacoes-tecnicas-sobre-a-divulgacao-de-resultados

O TSE divulgou que o pleito distrital teve **2.445 votantes
em 10 secoes**, concorrendo 22 candidatos com identificadores de
tres digitos. Essa estatistica corresponde aos 2.445 votos BU e
10 secoes identificados no CSV.

Referencia: https://www.tse.jus.br/comunicacao/noticias/2026/Outubro/eleitores-de-fernando-de-noronha-elegem-7-conselheiros-distritais

O portal de Resultados do TSE tambem exibe a eleicao do Conselho
Distrital como **eleicao separada** das eleicoes gerais.

Referencia: https://resultados.tse.jus.br/oficial/app/index.html

## Interpretacao e limites

**Evidencia forte de diferenca de escopo:** o motor comparou linhas
dos BU de um pleito distrital (cargo 25) com a fonte `secao` de
eleicoes gerais. Para essas 228 chaves, nao encontrou contraparte
na fonte de secao importada. Isso NAO demonstra que 2.445 votos
tenham deixado de ser totalizados pelo TSE, nem evidencia adulteracao.

Nao transformar `SEM_SECAO` em voto divergente. Preservar as
228 linhas e os arquivos originais como evidencias.

A conciliacao interna de todas as **chaves pareadas** retornou zero
diferencas numericas. Isto nao equivale a auditoria fisica das
urnas nem prova que todas as secoes possiveis e os recursos
publicados estavam no acervo. No codigo `cobertura_nacional_confirmada`
esta fixado em `false`; nao e uma medicao empirica da falta de
cobertura. `imports_incomplete=[]` indica ausencia de importacoes
incompletas registradas, nao completude do universo oficial.

## Validacao independente pendente

Para encerrar a verificacao tambem do pleito especial, obter a
fonte de resultados por secao da **eleicao 6261**, observar os
identificadores originais `CD_ELEICAO`, `CD_CARGO`,
`SG_UF`, `CD_MUNICIPIO`, `NR_ZONA`, `NR_SECAO` e
comparar por chave e por candidato com os BU ja preservados.

Se a fonte de secao detalhada nao estiver publicada, cotejar
agregados oficiais do pleito 6261 e documentar explicitamente
essa limitacao. Nao presumir conclusao a partir apenas do
numero de votantes: igualar soma de votos ao comparecimento
nao substitui cotejo candidato por candidato.

**Conduta de preservacao:** nao baixar de novo os 84 recursos
ja verificados apenas para repetir a conciliacao; nao modificar
`analysis/reconciliacao_checkpoints` nem sobrescrever o CSV atual
ate nova etapa auditavel.
