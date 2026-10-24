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
