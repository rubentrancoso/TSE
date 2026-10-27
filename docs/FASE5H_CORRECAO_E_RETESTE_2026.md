# Fase 5H — corrigir nulos tecnicos e testar novamente a periodicidade em 2026

**Estado em 27/10/2026:** a fase **L** foi executada e CONCLUIDA
nos arquivos reais BWEB locais do primeiro turno de 2026;
a fase **M** foi implementada na main e validada por testes
sinteticos, mas sua execucao empirica no disco H: ainda e pendente.

## Resultado da opcao L: reconciliacao exata

O operador executou `L — IDENTIFICAR 5246 VOTOS` no Windows.
A rotina leu novamente os ZIPs BWEB originais, validou SHA-256
e verificou os votos do numero presidencial **28** contra a
diferenca de votos validos da opcao K.

Resultado nacional, **28/28 UFs e ZZ reconciliadas**:
- 5.246 votos do numero 28 nos BWEB;
- 5.246 votos a mais na definicao antiga de validos
  (total menos branco e nulo convencionais);
- residuo da conciliacao apos retirar o numero 28: **zero**;
- diferencas de votos dos candidatos 13 e 22: zero em cada UF.

Todos os arquivos originais foram mantidos.

**Nao confundir o prologo de testes:**
a linha inicial no diretorio Temp com
`[NR28 AC] BWEB=5 excedente_K=6` e apenas uma
fixture artificial destinada a testar que uma
divergencia sera detectada. Os dados reais
comecam em `[NR28 AC] BWEB=23 excedente_K=23`;
nao ha UF com residuo real diferente de zero.

Esse resultado encerra a discrepancia de **5.246 votos**
como erro de classificacao do nosso extrator. Os votos
do numero 28 estao nos BWEB, mas nao integram os
validos oficiais. Os totais 13 e 22 bateram exatamente.

## Correcao de denominadores: opcao M

O algoritmo da fase H usava
`validos_antigos = total_de_votos - branco - nulo_convencional`.
A correcao e:

`validos_corrigidos_secao =
   validos_antigos_secao - votos_numero_28_secao`.

Nao basta subtrair 5.246 do denominador nacional:
a classificacao e aplicada na MESMA chave
UF, municipio, zona, secao e por minuto/segundo de
recebimento, preservando a dinamica real dos lotes.

**Pipeline implementado:**

1. Confere o estado final `CONCILIACAO_COMPLETA_NR_28`
   do relatorio L e os SHA-256 do resultado K.
2. Para cada UF, extrai do ZIP BWEB SHA-validado
   o mapa compacto `secao -> votos28`; guarda
   checkpoint com SHA-256, para nunca mais reler
   essa UF se os arquivos nao mudarem.
3. Reune esse mapa aos `received-UF.csv` da fase H,
   cujo SHA continua inalterado. Bloqueia voto
   negativo, chave nao encontrada, contagem divergente
   ou variacao de hash.
4. Confere totais nacionais corrigidos:
   **119.300.788 validos, 53.879.538 de Lula,
   56.104.503 de Flavio e 5.246 anulados da
   contagem antiga**. Se qualquer valor divergir,
   interrompe antes da interpretacao estatistica.
5. Reconstrói as curvas por minuto de recepcao
   (354 instantes, expectativa) e por segundos
   (9.039 instantes, expectativa), SEM inventar
   ordem dentro do mesmo segundo.
6. Refaz as simulacoes por minuto (1.000) e por
   blocos-alvo de 500, 1.000 e 2.000 urnas
   (200 simulacoes por grupo), usando exatamente
   as configuracoes exploratorias da H/J para
   comparar antes vs depois da correcao.
7. Escreve somente novos arquivos `phase5h_*`
   e seus hashes, sem sobrescrever nenhum
   arquivo original das opcoes H, J, K ou L.

**Nao exige downloads, SQLite ou microdados de 2022.**
A primeira execucao necessita ler uma vez os ZIPs BWEB
locais para recuperar a distribuicao do numero 28 por
secao, pois a L arquivou apenas os somatorios por UF.
Reexecucoes passam a usar os checkpoints pequenos.

## Execucao

    cd C:\Users\PC\Documents\git\TSE
    git pull
    start_windows.bat

Selecionar **M — CORRIGIR VALIDADE E REFAZER PERIODICIDADE 2026**.

Ou:

    python correct_bweb_28_periodicity_2026.py

Relatorio resultante:

    H:\TSE\forensics\urnas\analysis\periodicidade_bweb_2026\phase5h_corrected_periodicity_2026_summary.json

## Verificacao de software

Testes sinteticos passaram em **Windows e Linux,
176 testes por sistema**, incluindo arquivo BWEB
ficticio, numero 28 por secao, retoma da UF sem
releitura ZIP, divergencias de integridade e
ausencia de amostra suficiente:

https://github.com/rubentrancoso/TSE/actions/runs/40522038862

Esses testes de software NAO significam que a
fase M tenha sido executada sobre os 499.206
BU reais. Resultado real somente apos
o operador enviar a saida da opcao M.

## Pendencia distinta: 42 secoes

A diferenca entre 499.206 seções da base BWEB e
499.248 seções do ultimo snapshot nacional
continua **NAO CONCILIADA**. Ela nao e explicada
pela reclassificacao dos 5.246 votos.
A referencia estatal versus municipal possui
alguns desvios na BA e MG, mas ainda faltam
chaves para demonstrar sua relacao com essas 42.

A pesquisa de periodicidade continua exploratoria:
p-valores sobre permutacoes de residuos nao
representam probabilidade de fraude e nao
corrigem toda a heterogeneidade territorial.
