# Teste de um mecanismo matematico hipotetico — somente 2026

**Estado:** protocolo falsificavel; nenhuma formula de alteracao esta
estabelecida. **Nao utilizar dados eleitorais de 2022.** A referencia
aos dois pleitos e sobre uma hipotese conceitual de mecanismo geral.

## O que os resultados atuais mostram

1. A reconciliacao interna do BU digital de 2026 com CSV de secao fechou.
2. As relacoes de denominadores por cargo e as duas vagas do Senado fecham.
3. As 778 correlacoes entre cargos incluem efeitos geograficos;
   13 pares do Senado inverteram sinal apos ajuste.
4. Para nove candidatos ao Senado, os limites de sobreposicao com
   candidatos presidenciais sao deduzidos das margens por secao.
5. Isso nao constitui o vetor de diferencas entre urna e publicacao.

Nenhum desses fatos, isoladamente, identifica uma formula de
alteracao. Em especial, **voto cruzado politicamente inesperado
nao e diferenca material entre BU original e totalizacao**.

## Definir as variaveis observaveis

Por secao s e candidatura c:

- `X[s,c]`: contagem PRESERVADA por fonte independente
  do momento de encerramento na urna (BU impresso/QR de fiscal,
  com origem/tempo verificados, ou artefato original autenticado).
- `Y[s,c]`: contagem oficial publicada, pareada na mesma
  secao, turno, codigo de eleicao e candidatura.
- `D[s,c]=Y[s,c]-X[s,c]`: diferenca observada;
  **indefinida** quando X nao existe ou nao e autenticavel.
- `N[s]`: numero de eleitores com voto presidencial na secao,
  separando presenca de eleitores em transito.

E necessario controlar versao final, anulacao, substituicao
de urna, contingencia e eventual reprocessamento.

## Hipoteses que podem ser refutadas

- **H0 — Sem alteracao de votos:** `D[s,c]=0` para
  todos os pares de BU originais e publicados,
  apos reconciliar versoes e regras.
- **H1 — Transferencia conservativa entre candidaturas:**
  algum subconjunto de secoes tem `D[s,13]=-D[s,22]`,
  com `sum_c D[s,c]=0`, e valores nao triviais.
  Predizer onde a regra atua antes de verificar a amostra.
- **H2 — Regra proporcional de transferencia:**
  `D[s,13] ~= arredondamento(alpha * N[s])` e
  `D[s,22] ~= -D[s,13]` com `alpha` comum,
  respeitando limites de nao negatividade e votos
  totais. Ajustar `alpha` somente no conjunto
  de calibracao, validar em secoes disjuntas.
- **H3 — Mudanca na selecao/publicacao de secoes:**
  o conteudo de X e Y coincide quando pareado,
  mas a lista de secoes efetivamente publicada
  em um instante difere da lista esperada a partir
  dos registros de recepcao assinados. Testar
  latencia e ordem operacional antes de supor
  exclusao/alteracao intencional.

Esses modelos sao **hipoteses de teste**, nao
descricao do que aconteceu. Mudanca de percentuais
sem D observado nao identifica H1/H2. A propria
ausencia de versoes de BU originais independentes
impede estimar D e, consequentemente, distinguir
uma regra arbitraria de mera composicao eleitoral.

## Protocolo minimo

1. Inventariar artefatos disponiveis em 2026 com
   `inventory_material_evidence_2026.py`.
   O catalogo `archive_entries` registra hashes de
   membros de ZIP oficiais, mas eles **nao sao**
   por si mesmos fontes independentes.
2. Localizar fotografias/QR capturados na secao por
   fiscais, observadores e eleitores; registrar autor,
   local, momento e hash do original preservado.
3. Verificar autenticidade/assinatura dos dados
   quando a ferramenta oficial permitir.
4. Escolher secoes **antes** de examinar seu
   `D[s,c]`, incluindo grupos de comparacao
   na mesma UF/municipio/zona e casos neutros.
5. Parear X e Y por `eleicao, turno, UF, municipio,
   zona, secao, cargo, votavel`.
6. Testar H0, H1, H2 e H3 com controle
   geográfico e separacao calibracao/validacao
   usando apenas secoes de 2026.
7. Registrar nao correspondencias, faltas de origem,
   divergencias de assinatura, limites de cobertura,
   resultados negativos e predicoes refutadas.

Nao calcular p-valores ou acusar fraude a partir de
fragmentos eleitorais agregados. Se nao houver X
independente, o resultado correto para H1/H2
e `DADO_INSUFICIENTE`, nao `D=0` nem
`FRAUDE_DEMONSTRADA`.

## Comando da proxima verificacao do ambiente

```bat
git pull
python -m unittest discover -s tests -p test_inventory_material_evidence_2026.py -v
python inventory_material_evidence_2026.py
```

O inventario gera
`H:/TSE/forensics/urnas/analysis/evidencia_material_2026/inventario.json`.
Nenhuma fonte bruta e modificada e nenhum CSV de votos
e reprocessado por esse script.

## Formato opcional para capturas de terceiros

Caso existam arquivos autenticamente capturados de forma
independente, colocar os **originais** sob
`H:/TSE/forensics/urnas/evidencia_independente_2026/`
sem reencodar ou sobrescrever. Um manifesto opcional
`manifest.csv`, separado por ponto e virgula,
usa o cabecalho:

```csv
id;uf;municipio;zona;secao;turno;tipo;arquivo;origem;captura_utc;sha256
```

`arquivo` e um caminho relativo dentro do diretorio.
O hash SHA-256 informado deve ser calculado dos bytes
originais. Registrar origens honestamente; escrever
"observador" nao valida por si so a procedencia.

**Notas:** fotos/QR precisam validacao de legibilidade,
identidade de urna e integridade. Nao compartilhar
dados pessoais de fiscais sem consentimento.


## Primeira experiencia computacional de forma funcional (25/10/2026)

**Forma especifica falsificavel:**

```text
H_F: votos_P13(secao) = round(alpha_13 * N_pres_secao)
H_F: votos_P22(secao) = round(alpha_22 * N_pres_secao)
```

Aqui `N_pres_secao` inclui brancos e nulos, os dois
alphas sao ajustados **somente com secoes de treino**
e sao constantes nacionais. Este e um modelo simples
da alegada "formula geral", **nao** a hipotese de
transferencia H1/H2 definida acima: sem BU independente
nao existem as diferencas D necessarias a H1/H2.

`test_fixed_vote_formula_2026.py` le os
CSV BU por candidato de 2026 ja validados por
SHA-256, com `N >= 50` por padrao.
Reserva aproximadamente 20% das secoes para
validacao usando
`SHA256(UF|municipio|zona|secao|turno)[0] % 5 == 0`,
independente da ordenacao de buckets.
Com as outras 80%, estima os alphas nacionais,
taxas por UF e taxas por municipio+zona.
Avalia no conjunto de validacao, sem ajustar
parametros com ele, a taxa de previsoes
exatas, taxa com erro <=1 voto e erro medio
absoluto dos tres modelos.

**Regra descritiva predefinida e exigente:**
a forma nacional fica "nao refutada por este criterio"
apenas com >=95% de previsoes exatas nas
secoes de validacao e erro medio nacional
nao superior ao modelo territorial.
Isso **nao e p-valor nem evidencia de manipulacao**.
Mesmo com previsoes exatas a origem pode
ser natural. Se nao passar, somente esta
**forma fixa muito restrita** perde suporte;
outras formulas hipoteticas nao estao
descartadas automaticamente.

```bat
git pull
python -m unittest discover -s tests -p test_fixed_vote_formula_2026.py -v
python test_fixed_vote_formula_2026.py
```

Saida de 2026 em
`analysis/entre_cargos/<fingerprint>/formula_fixa_presidencial_2026/`
contendo `predicao_fora_amostra.csv`, `summary.json`
e SHA-256. E uma unica leitura das particoes
de BU por candidato depois da verificacao
automatica de seus 256 hashes; nao abre SQLite.

### Resultado empirico e revisao metodologica — 25/10/2026

Execucao real no H: com os 256 CSVs de BU por candidato,
verificados por SHA-256, concluida. A v2 do ajuste de
municipio+zona usa as medias globais por zona e e robusta
a particoes arbitrarias. No acervo real, `reconcile_stream.bucket_for`
manteve cada `UF|municipio|zona|turno` num so bucket.
A alegacao anterior de que a mesma zona poderia estar espalhada
entre as particoes nao se aplicava a esses dados.

**Senado:** 67.858.746 linhas de candidatos conferidas,
497.897 secoes pareadas, 616 pares e 13 inversoes.
V1 e v2 concordam nos 616 coeficientes dentro
da precisao reportada; as 13 inversoes persistem.
As inversoes nao demonstram transferencia individual
de voto nem fraude.

**Forma fixa nacional:** 397.341 secoes no treinamento
e 101.266 na validacao. P13: 0,834436% de predicoes
exatas, MAE 33,551123 votos/seção; P22: 0,935161%
de predicoes exatas, MAE 31,844696.
No modelo municipio+zona, MAE 11,971461 (P13)
e 12,140975 (P22). Ambos os candidatos
ficaram abaixo do criterio de 95% de acerto exato.
O modelo restrito `round(alpha_c*N_pres)` foi refutado
segundo o criterio predefinido.

**Nao** foram testadas transferencias ocultas H1/H2,
porque ainda nao ha vetor independente `D=Y-X`.
Sem BU de terceiros contemporaneo ou artefato
original autenticado, o teste nao identifica mudancas
entre a urna e a publicacao oficial.

Relatorio consolidado:
`docs/RESULTADOS_SENADO_FORMULA_2026_25OUT.md`.
