# Métodos estatísticos de investigação eleitoral — 2026

**Estado:** módulo `statistical_forensics.py` integrado à opção **1 — COLETA COMPLETA**
do menu `start_windows.bat` e ao subcomando `python urnas.py stats`.
Todos os códigos e testes são publicados diretamente na branch `main`.

## Objetivo e interpretação

Detectar padrões que mereçam conferência documental, sem deduzir fraude a
partir de um desvio estatístico. A ordem das evidências é:

1. preservação dos arquivos e SHA-256;
2. consistência aritmética BU ↔ seção ↔ município ↔ UF ↔ país;
3. análise da distribuição geográfica e temporal;
4. padrões de dígitos e outros diagnósticos exploratórios;
5. eventual verificação independente do registro do voto e dos logs.

Nenhum valor-p é tratado como prova de fraude. Resultados apresentados
não são probabilidades de que tenha ocorrido manipulação.

## Implementado automaticamente

Todos os testes estatísticos abaixo operam, por ora, em **CSV oficial de BU
para Presidente**, agrupado por seção e turno. O código documenta quantas
seções foram efetivamente analisadas. A cobertura total não é presumida.

| Relatório | Método | Condições e interpretação |
| --- | --- | --- |
| `benford.csv` | Lei de Benford, primeiro e segundo dígitos | Duas candidaturas com mais votos por UF e turno; 100 valores válidos, 30 valores distintos e alcance pelo menos 10 vezes. Mesmo quando aplicável como descrição, pode ser modelo inadequado para votos por seção. |
| `digitos_finais.csv` | Qui-quadrado descritivo e frequência de 0 e 5 | Contagens por candidato com 30 ou mais votos; no mínimo 100 observações. Teste não calibrado para efeitos de tamanho de seção. |
| `forma_distribuicao_municipal.csv` | Assimetria e excesso de curtose | Pelo menos 30 seções do município, com 40 votos válidos por seção. **Não pressupõe normalidade**. |
| `desvios_municipais.csv` | Mediana e desvio absoluto mediano (MAD) | As duas candidaturas com mais votos no município; sinaliza magnitude robusta ≥ 5, em no máximo cinco seções por candidato/município; MAD mínimo para evitar divisão por zero. |
| `participacao_correlacao.csv` | Pearson entre participação e fração de votos do candidato | A partir de 30 seções com QT_APTOS e QT_COMPARECIMENTO válidos; não atribui causalidade. |
| `perfil_participacao_voto.csv` | Histograma 2D participação × fração de votos | Grade 10 × 10 por UF/turno/candidato; não implica simulação de fraude. |
| `consistencia_por_secao.csv` | Identidades, duplicações e totais impossíveis | Verifica comparecimento > aptos, válidos > comparecimento e duplicidade de linhas da mesma candidatura na seção. Divergências devem ser examinadas contra a definição oficial dos campos. |

**Arquivos de entrada:** `H:/TSE/forensics/urnas/analysis/urna_2026.sqlite3`

**Arquivos de saída:** `H:/TSE/forensics/urnas/analysis/estatistica/`

A análise gera `estatistica_resumo.json` com versão do algoritmo, quantidade de
seções, cobertura por UF/turno, hashes SHA-256 dos insumos importados quando
disponíveis, métodos e limitações. Os relatórios anteriores são atualizados
de forma atômica. Caso não existam BUs para Presidente, o status será
`SEM_DADOS_BU_PRESIDENTE`, **não** `sem anomalias`.

A coleta completa faz tudo em uma execução:
`start_windows.bat` → opção **1**. Repetir a coleta reutiliza arquivos íntegros;
a bateria estatística reprocessa os dados disponíveis sem buscar novos arquivos.

## Análises previstas que dependem de outras evidências ou de validação

- **Sequência temporal / mudanças de regime (CUSUM, change-point):**
  comparar lotes de BUs efetivamente recebidos; horários de geração,
  recebimento, totalização e publicação são campos diferentes.
  Exige ancoragem temporal verificável, grupos comparáveis e controle
  de diferenças de composição geográfica.
- **Simulações e inferência condicionais (Monte Carlo e permutação):**
  definir uma hipótese nula empiricamente plausível, preservando
  município, seção, tamanho da urna e estrutura de correlação.
  Corrigir testes múltiplos e reportar sensibilidade.
- **Modelos de contagem e superdispersão (binomial/beta-binomial):**
  ajustar por heterogeneidade e validar em dados históricos,
  com diagnósticos fora da amostra.
- **Comparação com 2022:** diferenças de cargos, distritos,
  zonas, agregações e cadastros devem ser harmonizadas antes de interpretar.
- **Verificação independente (RLA):** requer trilha independente,
  amostragem auditável e, tipicamente, conferência manual
  de cédulas verificáveis. Não é substituída por Benford ou por dois
  CSVs emitidos pelo mesmo sistema de apuração.

Não foi implementado um "índice único de fraude". Agregar estatísticas
incompatíveis em uma nota ou porcentagem produziria uma interpretação inválida.

## Citações metodológicas

- Breunig e Goerres (2011), *Searching for electoral irregularities in an established democracy*,
  [Electoral Studies](https://doi.org/10.1016/j.electstud.2011.03.005).
- Klimek, Yegorov, Hanel e Thurner (2012), *Statistical detection of systematic election irregularities*,
  [PNAS](https://doi.org/10.1073/pnas.1210722109).
- MIT Election Lab, [post-election audits](https://electionlab.mit.edu/research/post-election-audits).
- The Carter Center, [Risk-Limiting Audits: A Guide for Election Observation Efforts](https://www.cartercenter.org/publication/risk-limiting-audits-a-guide-for-election-observation-efforts/).

## Limites científicos

A presença de Benford ou de uma curva semelhante à normal não valida uma eleição.
Sua ausência não demonstra fraude. Votos por seção dependem do número de eleitores
e de características sociais, territoriais e políticas. Os métodos são
complementares e exigem testes de robustez. É necessária correção por múltiplos
testes e calibração com dados de referência antes de fazer afirmações
estatísticas inferenciais. O componente atual emite indicadores exploratórios,
não probabilidades de adulteração.
