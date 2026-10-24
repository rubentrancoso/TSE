# Revisao das 13 inversoes de correlacao Presidente x Senado — 2026

**Data:** 24/10/2026
**Fonte numerica:** `review_cross_office_correlations.py`,
executado localmente, 5 testes OK e SHA verificados no
encadeamento do acervo BU. O registro integral da execucao
permanece no computador do investigador.
**Criterio:** correlacoes bruta e apos retirar medias
por municipio+zona mudam de sinal; em cada lado
`abs(Pearson) >= 0,10`. Limites de cobertura
predefinidos: 1.000 secoes, 10 zonas com variacao
e 1.000 votos senatoriais. E uma triagem descritiva.

## Todos os 13 pares

| UF | Senador | Partido | Numero | Presidencial | r bruto | r ajustado | Secoes | Votos senador |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| AC | Dr. Junior Feitosa | DC | 277 | 13 | +0,158107 | -0,215486 | 2.270 | 19.283 |
| AC | Dr. Junior Feitosa | DC | 277 | 22 | -0,155372 | +0,191363 | 2.270 | 19.283 |
| AL | Arthur Lira | PP | 111 | 22 | -0,405826 | +0,109550 | 7.101 | 948.703 |
| AM | Plinio Valerio | PSDB | 455 | 22 | -0,166983 | +0,105302 | 8.157 | 948.793 |
| PI | Ciro Nogueira | PP | 111 | 13 | +0,137806 | -0,211450 | 10.225 | 904.961 |
| RN | Tercio Tinoco | UNIAO | 444 | 13 | -0,170840 | +0,118039 | 8.115 | 102.834 |
| RN | Tercio Tinoco | UNIAO | 444 | 22 | +0,151042 | -0,127813 | 8.115 | 102.834 |
| RR | Teresa Surita | MDB | 155 | 13 | -0,119537 | +0,223131 | 1.519 | 117.270 |
| SP | Soninha Francine | CIDADANIA | 232 | 13 | +0,138230 | -0,117541 | 103.656 | 165.707 |
| TO | Alexandre Guimaraes | MDB | 153 | 13 | +0,187639 | -0,102593 | 4.384 | 316.786 |
| TO | Alexandre Guimaraes | MDB | 153 | 22 | -0,159814 | +0,111438 | 4.384 | 316.786 |
| TO | Eduardo Gomes | PL | 222 | 13 | +0,181175 | -0,328465 | 4.384 | 450.191 |
| TO | Eduardo Gomes | PL | 222 | 22 | -0,148700 | +0,341408 | 4.384 | 450.191 |

**Cobertura:** 13 pares, **nove candidaturas senatoriais
distintas**, oito UFs, sete siglas partidarias distintas.
As duas correlacoes de um mesmo senador com os
presidenciaveis 13/22 compartilham as mesmas secoes;
**nao sao eventos estatisticamente independentes**.

**Identificacao e filiacoes** provêm do Senado Federal,
lista divulgada em 24/08/2026 (nao confundida com a
situacao juridica final de cada candidatura):
- AC https://www12.senado.leg.br/noticias/candidatos-2026/acre
- AL https://www12.senado.leg.br/noticias/candidatos-2026/alagoas
- AM https://www12.senado.leg.br/noticias/candidatos-2026/amazonas
- PI https://www12.senado.leg.br/noticias/candidatos-2026/piaui
- RN https://www12.senado.leg.br/noticias/candidatos-2026/rio-grande-do-norte
- RR https://www12.senado.leg.br/noticias/candidatos-2026/roraima
- SP https://www12.senado.leg.br/noticias/candidatos-2026/sao-paulo
- TO https://www12.senado.leg.br/noticias/candidatos-2026/tocantins

A fonte estruturada e versionada dos nove nomes
e `docs/CANDIDATOS_SENADO_INVERSOES_2026.csv`.
Em etapa posterior, reconciliar esses nomes/partidos
com o **cadastro final de candidatos do TSE e o EA20
oficial** (nome, cargo, UF, numero, situacao juridica).

## Interpretacao e proximas provas

Inversao por controle de municipio/zona e compativel
com efeito de composicao territorial, inclusive
paradoxo de Simpson. Nao atesta transferencias
de votos individuais, adulteracao nem fraude.

Para investigar a compatibilidade **matematica**
entre cargos, executar `senate_ecological_bounds.py`
sobre os mesmos BU seccionais ja preservados.
Para cada secao, senador S, voto presidencial P
e comparecimento presidencial N, os votos
na intersecao satisfazem:

```text
max(0, S + P - N) <= sobreposicao <= min(S, P)
```

Isso calcula limites necessarios e possiveis sem
reconstruir nenhum voto individual. Um eleitor
pode escolher dois senadores, mas so pode escolher
**um determinado senador uma vez**; portanto
S representa pessoas distintas para a candidatura.
N inclui pessoas aptas apenas para Presidente
em algumas secoes e torna o limite inferior
conservador.

**Roteiro local (sem reler SQLite):**

```bat
git pull
python -m unittest discover -s tests -p test_senate_ecological_bounds.py -v
python senate_ecological_bounds.py
```

Este programa percorre novamente os CSVs BU
particionados para obter novas contagens por secao,
com verificação dos 256 SHA-256. Nao modifica as
fontes, nem os resultados das correlacoes.
A execucao real ainda esta pendente; qualquer
numero futuro deve vir da saida observada.

**Perguntas posteriores:**
- modelos nulos condicionados por municipio/zona
  e simulacoes respeitando heterogeneidade;
- limites por secao e municipio para blocos
  partidarios documentados, com ambiguidade e
  aliancas locais;
- repetibilidade em turnos e controles historicos
  de 2022 e 2024, harmonizados;
- evidencias materiais independentes da cadeia
  urna/transmissao/publicacao.

Uma anomalia exploratoria nao constitui
determinacao de fraude ou de preferencia politica.
