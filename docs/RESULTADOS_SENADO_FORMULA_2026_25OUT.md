# Resultado empirico: Senado v1/v2 e formula fixa presidencial — 25/10/2026

## Escopo e fonte

Eleicao de 2026, primeiro turno, apenas BU ja extraidos em
`H:/TSE/forensics/urnas`. Execucao local pelo investigador
em Windows, sem download ou novo indice SQLite.
Testes sinteticos locais: 122 OK. CI Windows e Linux:
https://github.com/rubentrancoso/TSE/actions/runs/40231252600

Acervo: `analysis/entre_cargos/8ab3ce83c8992b9a-94fc637b4737c20d/`.
256 particoes BU de candidatos validadas por SHA-256;
67.858.746 linhas; 497.897 secoes pareadas
Presidencia/Senado; 308 candidaturas senatoriais nas 27 UFs;
616 pares envolvendo os candidatos presidenciais 13 e 22.

## Comparacao das correlacoes v1 e v2

| Medida | Valor |
| --- | ---: |
| Pares comparados | 616 |
| Inversoes v1 (|r bruto| e |r ajustado| >= 0,10) | 13 |
| Inversoes v2 | 13 |
| Persistentes | 13 |
| Apenas v1 | 0 |
| Apenas v2 | 0 |
| Coeficientes alterados (> 0,000001) | 0 |

Distribuicao das inversoes: AC 2, AL 1, AM 1,
PI 1, RN 2, RR 1, SP 1, TO 4.
**13 pares nao sao necessariamente 13 senadores**;
pares com P13 e P22 podem envolver o mesmo senador.

| UF | Presidente | Senador (numero) | r bruto | r ajustado v2 | Secoes |
| --- | --- | --- | ---: | ---: | ---: |
| AC | 13 | 277 | +0,158107 | -0,215486 | 2.270 |
| AC | 22 | 277 | -0,155372 | +0,191363 | 2.270 |
| AL | 22 | 111 | -0,405826 | +0,109550 | 7.101 |
| AM | 22 | 455 | -0,166983 | +0,105302 | 8.157 |
| PI | 13 | 111 | +0,137806 | -0,211450 | 10.225 |
| RN | 13 | 444 | -0,170840 | +0,118039 | 8.115 |
| RN | 22 | 444 | +0,151042 | -0,127813 | 8.115 |
| RR | 13 | 155 | -0,119537 | +0,223131 | 1.519 |
| SP | 13 | 232 | +0,138230 | -0,117541 | 103.656 |
| TO | 13 | 153 | +0,187639 | -0,102593 | 4.384 |
| TO | 13 | 222 | +0,181175 | -0,328465 | 4.384 |
| TO | 22 | 153 | -0,159814 | +0,111438 | 4.384 |
| TO | 22 | 222 | -0,148700 | +0,341408 | 4.384 |

Arquivo v2:
`correlacao_presidente_senado_v2/pares_por_uf.csv`
SHA-256:
`7fc29f2f8a040e7880b72782e45ae60df01a8b2e908b2021e477dcdb08443dcd`.

Comparacao v1/v2:
`correlacao_presidente_senado_v2/comparacao_metodologica/todos_pares_v1_v2.csv`
SHA-256:
`5074153e7a658287405ee1508005d7c6e5d5e711b94a8395e77e49c98a6c7a37`.

### Retificacao de metodologia

A hipótese anterior de que um mesmo municipio+zona
poderia aparecer em vários buckets nao se confirmou
para o processo de extração empregado neste acervo.
`reconcile_stream.bucket_for(record, count)`
calcula `crc32(UF|municipio|zona|turno) % count`.
Logo, todas as secoes/cargos/candidatos dessa zona
e turno pertencem ao mesmo bucket. A v1 centralizava
por zona **dentro** de cada bucket, mas esse conjunto
ja continha a zona inteira. A v2 soma as marginais
territoriais globalmente e e robusta a particionamentos
alternativos. Os coeficientes identicos nas 616 comparacoes
corroboram a equivalencia para os arquivos estudados.

Correlacao que troca sinal ao controlar geografia
e fenomeno descritivo possivel, inclusive por efeitos
de composicao (paradoxo de Simpson). Nao se inferem
votos individuais, blocos politicos, transferencias
ou fraude a partir dessa estatistica.

## Modelo nacional de proporcao fixa

**Hipotese estreita testada:**
`votos_c(secao)=round(alpha_c*N_pres(secao))`,
com `N_pres` incluindo brancos/nulos.
Alphas estimados apenas nas secoes de treino; validacao
deterministica por hash da chave de secao.

- Treino: **397.341** secoes.
- Validacao: **101.266** secoes.
- Alpha P13: **0,4300515021**.
- Alpha P22: **0,4478353145**.

| Candidato | Modelo | % previsoes exatas | MAE (votos/secao) | RMSE |
| --- | --- | ---: | ---: | ---: |
| 13 | Nacional | 0,834436% | 33,551123 | 41,097144 |
| 13 | UF | 1,479272% | 21,479885 | 27,552984 |
| 13 | Municipio+zona | 2,915095% | 11,971461 | 16,102812 |
| 22 | Nacional | 0,935161% | 31,844696 | 39,102931 |
| 22 | UF | 1,515810% | 21,679893 | 27,550989 |
| 22 | Municipio+zona | 2,863745% | 12,140975 | 16,103509 |

Regra predefinida para nao refutar a forma nacional:
pelo menos 95% de previsoes exatas e MAE nacional
nao superior ao ajuste por municipio+zona.
**Resultado: ambos os candidatos refutam
essa forma nacional no criterio empregado.**

Arquivo:
`formula_fixa_presidencial_2026/predicao_fora_amostra.csv`
SHA-256:
`3b90e6e26a6a250eeee61c868822248b9f3a3b4c35562e645a27f8aed61bad5c`.

Este teste **nao** estabelece nem elimina uma possivel
transferencia encoberta `D[s,c]=Y[s,c]-X[s,c]`:
sem um `X` de BU original autenticado independentemente
da publicacao, nao se observa `D`. Nao foram utilizados
microdados de 2022.

## Proxima etapa prioritaria

1. Conservar os relatorios e checksums acima.
2. Investigar as 13 inversoes com modelos nulos que
   preservem municipio/zona e estrutura espacial;
   controlar tamanho de secao, denominadores, multipla
   comparacao e repeticoes do mesmo senador.
3. Para testar alteracao entre a urna e o resultado
   oficial, obter BU impresso/QR contemporaneo de
   procedencia independente ou artefato original
   autenticado; parear mesmo codigo de eleicao,
   secao, turno, cargo e candidato.
4. Registrar resultados negativos e seções sem fonte
   independente explicitamente, sem imputar `D=0`.

**Estado:** concluido como estudo descritivo
correlacional e teste falsificavel de uma forma fixa.
**Nao constitui auditoria fisica independente da urna.**
