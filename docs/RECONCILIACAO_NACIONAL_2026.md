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


## Checagem focal por JSON oficial da zona 4

Foi publicado na main `verify_noronha_6261.py`, uma verificacao
**somente-leitura** do CSV nacional final. Este script nao acessa o
SQLite nem modifica os 256 checkpoints. Ele monta um consolidado
BU por votavel das 228 linhas de PE/30015/zona 4/cargo 25,
e consulta **um unico** arquivo de resultado unificado do TSE
para a eleicao `6261` em nivel de zona.

O formato do endpoint decorre da especificacao EA20 do portal
e de amostras de arquivos de 2026; a URL exata ainda requer
confirmacao HTTP no computador do investigador:
`https://resultados.tse.jus.br/oficial/ele2026/6261/dados/pe/pe30015-z0004-c0025-e006261-u.json`.

O programa preserva o JSON bruto no H:, mostra seu SHA-256,
valida ID da eleicao, zona e cargo, confronta todos os votaveis
`n`/`vap` (com `vb` e `tvn` para branco/nulo), confere
10 secoes e 2.445 votos totais, e salva um relatorio
versionado por hash. A rede nao sera chamada novamente ao
encontrar o arquivo original salvo.

Passos apos finalizar a reconciliacao:

```bat
git pull
python -m unittest discover -s tests -p test_verify_noronha_6261.py -v
python verify_noronha_6261.py
```

**Escopo da evidencia:** o JSON EA20 agrega por zona,
nao fornece votacao individual por secao. Se houver igualdade,
sera uma validacao independente por candidato **da zona inteira**,
e nao 228 comparacoes por secao. Ausencia de dados oficiais ou
falha de acesso deve permanecer como pendencia explicita,
sem inferir desvio de votos.


## Execucao real da checagem focal 6261 (24/10/2026)

O investigador confirmou execucao no H: com seis testes unitarios OK.
`python verify_noronha_6261.py` acessou o endpoint oficial
`https://resultados.tse.jus.br/oficial/ele2026/6261/dados/pe/pe30015-z0004-c0025-e006261-u.json`,
preservou JSON SHA-256
`96463db912ac20355cddcd0cfbfd6bee5b8ed63feb04aad33e9d28264cae5ddf`
e gerou
`analysis/validacao_6261/comparacao_96463db912ac2035.json`.

**Resultado validado por candidato na zona eleitoral:** 228 chaves
BU, 10 secoes, 2.445 votos, 24 votaveis pareados, 0 diferentes,
0 sem par. Brancos=44 e nulos=62 tambem coincidem.
`RESULTADO: EQUIVALENCIA_AGREGADA_CONFIRMADA`.

**Interpretacao limitada:** encerra a diferenca de escopo
daquelas 228 chaves no nivel de totalizacao **por zona**,
mas nao compara as dez secoes uma a uma por fonte independente.
Nao converter "igualdade de total oficial" em prova de
seguranca fisica ou de ausencia universal de fraude.

**Proxima fase:** gerar base por secao/cargo/candidato dos mesmos BU,
abrangendo Presidente, Governador, Senado e deputados para testar
hipoteses de compatibilidade ecologica (sem deduzir voto individual).
Script versionado: `cross_office_sections.py` e testes
`tests/test_cross_office_sections.py`. Comecar com piloto
`--pilot-buckets 2` antes da execucao integral. Entrada unica:
particoes TSV do motor stream, com validacao SHA-256 original.
