# Fase 5G — reconciliacao de +5.246 votos BWEB no primeiro turno 2026

**Data:** 27/10/2026. **Fonte empirica interna:** opcao K executada
pelo investigador em H:/TSE/forensics/urnas com dados 2026.

## Resultado K e erro de classificacao identificado

O codigo da opcao H originalmente calculava
`votos_pres_validos = soma(QT_VOTOS) - Branco - Nulo`.
Essa operacao classifica indevidamente como VALIDOS os votos que
continuam nos BWEB nominais embora nao integrem a lista
de candidaturas validas da totalizacao.

Resultado K com 499.206 secoes, 27 UFs + exterior ZZ:
- Presidente 13, Lula: 53.879.538 BWEB vs 53.879.538 oficial,
  diferenca 0 em todas as UFs.
- Presidente 22, Flavio Bolsonaro: 56.104.503 BWEB vs
  56.104.503 oficial, diferenca 0 em todas as UFs.
- BWEB `validos` ingenuamente contados: 119.306.034;
  oficiais: 119.300.788; excesso +5.246, distribuido
  positivamente entre todas as 28 UFs.
- Os outros candidatos, por subtracao: BWEB 9.321.993
  contra total oficial 9.316.747, excesso +5.246.
- Nulo convencional de urna (tipo 'Nulo'): 3.669.003,
  contra NULOS TOTAIS oficiais 3.674.249, diferenca 5.246.
- Branco: 2.300.798, sem diferenca.

**Identificacao externa do numero:**
- Leonardo Avalanche, PRTB, numero **28**, obteve **5.246 votos
  registrados nos boletins BWEB** mas nao consta dos
  votos validos oficiais, de acordo com a
  conferencia independente dos boletins
  https://multiversodigital.com.br/eleicoes2026/index.php .
- Outra plataforma oficializada a partir de dados TSE
  registra explicitamente **5.246 votos anulados** do candidato:
  https://politica.one/eleicoes/2026/br/presidente .
- Total nulos oficiais e separacao tecnica:
  3.674.249 = 3.669.003 + 5.246:
  https://urna360.com.br/eleicoes/2026/1-turno/presidente .
- A imprensa documentou a renuncia do candidato em 01/10/2026,
  apos as urnas terem sido preparadas, e o tratamento de
  votos nessa situacao:
  https://www1.folha.uol.com.br/poder/2026/10/leonardo-avalanche-desiste-de-candidatura-a-presidencia.shtml .
- Os resultados do TSE por UF e candidato versionados no repo
  estao em data/forensics/analysis/uf_candidate_reconciliation.csv
  (336 linhas, 28 UFs e 12 candidatos, sem candidato 28).

**Conclusao documental:** a diferenca de 5.246 tem uma
explicacao de CLASSIFICACAO dos votos recebidos: o extrator
contou os votos anulados ao numero 28 como validos.
Nao ha qualquer evidencia nesses numeros de transferencia
de votos entre 13 e 22, que fecham exatamente em cada UF.

**Conferencia no proprio H:** opcao **L** foi implementada
para CONFIRMAR, e nao presumir, a igualdade UF a UF entre
`NR_VOTAVEL == 28` dentro dos 28 ZIPs BWEB
originais SHA-validados e as diferencas emitidas pela
opcao K. O resultado empirico de L permanece **PENDENTE**
de execucao no disco H:; fontes externas nao sao
substitutas de prova de proveniencia local.

## Resultados da opcao K (divergencia de 'validos' por UF)

| UF | Excesso bruto | UF | Excesso bruto |
|---|---:|---|---:|
| SP | 1.355 | MG | 561 |
| RJ | 387 | MA | 345 |
| PR | 268 | RS | 253 |
| BA | 251 | SC | 184 |
| PA | 183 | CE | 177 |
| PE | 138 | ZZ | 123 |
| ES | 121 | GO | 107 |
| MT | 95 | PB | 90 |
| AM | 82 | MS | 76 |
| AL | 73 | RO | 66 |
| RN | 63 | DF | 57 |
| SE | 57 | PI | 52 |
| TO | 28 | AC | 23 |
| AP | 17 | RR | 14 |

Em cada UF, excesso 13=0 e 22=0; excesso
da categoria residual 'outros' = excesso de validos.

## Execucao da opcao L

No Windows:

    cd C:\Users\PC\Documents\git\TSE
    git pull
    start_windows.bat

Selecionar `L — IDENTIFICAR 5246 VOTOS: conferir NR_VOTAVEL 28`.
O programa abre somente os ZIPs locais ja arquivados, confere
SHA contra manifestos, faz uma passagem nos CSVs BWEB, soma
as linhas de NR_VOTAVEL 28 do cargo Presidente, turno 1,
e compara com as diferencas K em cada UF.
Nao baixa, nao reindexa SQLite, nao le 2022 e NAO sobrescreve
os arquivos received-UF.csv de H, preservando proveniencia.

Saidas:
- H:/TSE/forensics/urnas/analysis/periodicidade_bweb_2026/phase5g_nr28_by_uf_2026.csv
- H:/TSE/forensics/urnas/analysis/periodicidade_bweb_2026/phase5g_nr28_reconciliation_2026_summary.json

## Distincao da divergencia de 42 secoes

BWEB de 2026: 499.206 secoes com dados presidenciais.
Ultimo snapshot nacional: 499.248 secoes totalizadas.
A diferenca -42 e uma questao de **ESCOPOS DE CONTAGEM
DE SECOES**, distinta da correcao de 5.246 votos do
candidato 28. A fase 2 apresenta 6 secoes de diferenca
entre UF e somatorio municipal na BA e 36 em MG, mas
a coincidencia aritmetica 6+36=42 nao identifica
necessariamente as chaves divergentes.

Nao afirmar que 42 urnas tenham perdido votos, sido
substituidas ou adulteradas antes de reconciliar
as definicoes de 'secao totalizada' e 'BU com dados'.

## Fases temporais

Os testes H/J de periodicidade usaram denominator
`total - brancos - nulos convencionais` e incluíram
os 5.246 votos nominais nao validos. A afetacao e
pequena no total nacional mas pode ser relevante para
lotes minimos/vales, por isso **antes de declarar
resultados confirmatorios deve-se refazer a estatistica
com validos corrigidos por secao/minuto**.
O material anterior continua valendo como
DESCRITIVO da transformacao original, sem adulterar
retroativamente checkpoints. A opcao L identifica
as chaves e votos nominais 28; uma fase posterior
pode derivar (nao sobrescrever) series corrigidas.

**Estado:** K nacional executada; L programada,
resultado L e fase de correcao de denominadores
ainda pendentes no H. Esta nota registra a
identificacao corroborada externamente, sem fabricar
uma confirmacao local ainda nao executada.
