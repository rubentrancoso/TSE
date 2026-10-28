# Fase 5R — placebos de horário dentro de zonas (opção W)

Implementação: `analyze_cutoff_placebos_2026.py`. Status em 28/10/2026:
**programa e testes sintéticos versionados; execução real no disco H ainda pendente**.

## Evidência que motiva o teste

A Fase V executada pelo investigador sobre 499.206 BWEB do primeiro
turno de 2026 e 119.300.788 votos válidos SHA-reconciliados encontrou
que, com o corte **04/10/2026 20:04:39 BRT**:

- 13.627.882 válidos foram **recebidos** no BWEB depois do corte.
- 11.982.944 desses válidos (87,93%) estavam em **2.127 zonas**
  que também possuíam votos antes do corte.
- O modelo municipal pre-corte subestimou Lula por **2,06049 pp**;
  o modelo por zona pré-corte por **2,02346 pp** (melhoria de
  somente 0,03703 pp). Seu RMSE de minuto caiu de **2,82262**
  para **2,70831 pp**.
- Nas zonas que possuíam votos antes e depois, o desvio
  observado Lula menos previsão municipal foi **257.869,23 votos**,
  de um desvio nacional líquido de cerca de **280.802 votos**
  (91,83%). Essa é uma diferença **em relação ao modelo**, não
  uma identificação de votos suspeitos/alterados.
- Em **1.380 zonas** com >=1.000 válidos em cada lado,
  a participação de Lula depois do corte superou a de antes em
  **1,99279848 ponto percentual** em média ponderada pelos
  votos posteriores.

Isso estabelece um fenômeno descritivo de composição dos BUs
tardios, inclusive dentro de zonas previamente observadas. Por
si só não prova fraude nem explica a curva de publicação EA20.

## O teste de falsificação temporal

O programa W realiza uma **única passagem sobre todos os CSVs H/M
SHA-verificados**, corrigindo os 5.246 votos de NR_VOTAVEL=28,
e monta o mesmo contraste entre BUs precoces e tardios em dez
cortes **fixados no código antes de observar o resultado de W**:

18:00, 18:30, 19:00, 19:30, 19:45, 20:00, **20:04:39**,
20:15, 20:30 e 21:00 de 04/10/2026, horário BRT.

Para cada horário:
- zela pela separação por segundos de `DT_BU_RECEBIDO`;
- escolhe apenas as zonas com >=1.000 votos válidos
  **de cada lado daquele corte**;
- calcula a média das diferenças em pontos percentuais
  **pós menos pré** para Lula e Flávio, ponderada pelos
  válidos posteriores de cada zona;
- informa quantas zonas participaram e qual fração dos
  votos da cauda foi coberta; as coortes podem mudar;
- conta zonas com aumento e queda, e apresenta mediana
  não ponderada para revelar possíveis efeitos de concentração.

No corte principal, W **exige** identidade exata com V:
total válido antes, depois, 1.380 zonas pareadas,
cobertura e média ponderada de +1,99279848 pp.
Se houver desacordo, W interrompe.

Como robustez adicional, no corte principal calcula
a média nacional excluindo uma UF por vez. Não é
bootstrap nem estimativa de causalidade.

### Como interpretar

- Se todos os cortes apresentam deslocamentos parecidos,
  a mudança após 20:04 não é específica do destravamento
  da publicação nacional; existe tendência de composição
  ao longo do recebimento.
- Se apenas 20:04 apresentar mudança ou descontinuidade
  mais acentuada, investigar a relação administrativa com
  os lotes e as mudanças de publicação, preservando as duas
  cronologias separadas.
- Se cortes com baixo número de zonas tiverem efeitos
  diferentes, a cobertura precisa ser tratada como explicação
  alternativa. Em nenhum caso os valores são ensaios
  randomizados ou medidas probabilísticas de fraude.

## Arquivos e execução

**Opção W** no `start_windows.bat`:
- `phase5r_cutoff_placebos_2026_summary.json`;
- `phase5r_cutoff_placebos_2026.csv`;
- `phase5r_uf_paired_zones_2026.csv`;
- `phase5r_paired_zones_2026.csv`.

O manifesto JSON documenta SHA dos CSV e das fontes. Os arquivos
ficam em `H:/TSE/forensics/urnas/analysis/periodicidade_bweb_2026`.
A opção **U** abre automaticamente o notebook
`notebooks/TSE_2026_Laboratorio_Forense_Fase_W.ipynb` após W.

A rotina não baixa dados eleitorais, não abre ZIP, não usa
SQLite nem dados de 2022/segundo turno.

**Distinção invariável:** o tempo `DT_BU_RECEBIDO` do BWEB
não é a publicação `EA20`. O R²=0,99044 da curva publicada
EA20 por seções continua como pergunta operacional pendente.
