# Fase 5C — periodicidade dos BU individuais, primeiro turno de 2026

**Status em 27/10/2026:** software concluido e testado; execucao empirica dos ZIPs BWEB locais do H: ainda pendente. Nao usar microdados de 2022.

## Problema estudado

Transpor a hipotese do video para a votacao presidencial de 2026:
procurar vales estatisticamente repetidos na curva das urnas
individuais, e nao apenas nos snapshots nacionais agregados.

## Descoberta metodologica: EA16 nao fornece ordem confiavel

O relatorio existente phase3_arrivals_summary.json registra
497.897 secoes com EA16 da/ha. Em 25 das 27 UFs, incluindo
475.873 secoes (95,58%), o intervalo de todos os horarios
EA16 da UF e inferior a cinco minutos. Exemplos:
AC: 2.270 secoes em 3 s; BA: 35.476 em 53 s;
SP: 103.656 em 171 s; AM: 8.157 em 6 s.

O TSE define EA16 da/ha como horario de geracao do
auxiliar da secao, que pode indicar o recebimento. Mas a
concentracao em massa encontrada e compativel com um
processo de geracao em lotes, e nao com a real sequencia
de recepcao individual de 497 mil urnas.
Logo, a opcao G cruza BU com EA16 e bloqueia alegacoes
de periodicidade cronologica produzidas dessa ordem.

## Solucao implementada: DT_BU_RECEBIDO dos BWEB originais

Os BWEB de 2026 ja arquivados no H: contêm
DT_BU_RECEBIDO por secao, com resolucao disponivel
de minuto. O campo e uma fonte temporal mais apropriada.

Opcao H do start_windows.bat:

1. Localiza os ZIPs BWEB primeiro turno ja existentes no
   diretorio H:/TSE/forensics/urnas/raw/bu por UF, 27 + ZZ.
2. Confere SHA-256 de cada ZIP perante o arquivo meta.json
   criado na coleta anterior, antes de examinar o CSV.
3. Le as linhas presidenciais turno 1, obtendo uma linha
   por BU com UF, municipio, zona, secao, minutos de
   DT_BU_RECEBIDO, votos 13, votos 22, validos e invalidos.
4. Confere consistencia de timestamps repetidos e contagens.
   Nao arbitra ordenacao exata entre urnas empatadas no minuto.
5. Faz checkpoints por UF com SHA, permitindo retomada sem
   processar novamente as UFs ja concluidas.
6. Agrega BUs recebidos em cada minuto e reconstroi a curva
   acumulada presidencial e o numero de urnas recebidas.
7. Procura vales no percentual do lote apos retirar tendencia
   local, em eixos de minutos e BU acumulados.
8. Varre 144 periodos com teste senoidal e estatistica maxima.
   Calibra por 1000 permutacoes estratificadas por quartis,
   individuais e em blocos de cinco.
9. Se a cobertura de horario for inferior a 90%, ou houver
   concentracao temporal absurda como a do EA16, bloqueia
   a inferencia, em vez de produzir periodicidade ilusoria.

Parametros iniciais predefinidos: filtro de >=10 mil
votos validos por minuto, mediana movel 15 pontos,
minimo local com proeminencia >=8 pontos percentuais,
periodos de 2–120 minutos e 2.000–100.000 BUs,
semente 20261027. Esses filtros sao exploratorios,
nao constituem teste confirmatorio de fraude.

## Execucao local sem download nem SQLite

cd C:\Users\PC\Documents\git\TSE
git pull
start_windows.bat

Selecionar **H — BU RECEBIDOS 2026**.

Pode executar diretamente:

python extract_bweb_received_2026.py
python analyze_bweb_receipt_periodicity_2026.py

Saida esperada:

H:\TSE\forensics\urnas\analysis\periodicidade_bweb_2026\phase5c_summary.json

Arquivos locais:
- received-XX.csv e received-XX.summary.json para cada UF
- serie_2026_por_minuto.csv
- residuos_2026_por_minuto.csv, se os horarios forem utilizaveis
- phase5c_summary.json com cobertura, totais, hashes, testes e limites

## Limites e status da conclusao

O horario DT_BU_RECEBIDO vem dos dados publicados pelo
TSE, nao de captura independente. A resolucao pode ser
so de minuto; a ordem exata entre BUs empatados permanece
desconhecida. Recebimento de BUs e publicacao no site sao
eventos distintos. A existencia de um periodo nao indica
automaticamente alteracao de votos: processamento em lote,
selecoes geograficas e outras causas devem ser comparadas.

Codigo executado em testes sinteticos no Windows e Linux:
155 testes em cada sistema, todos aprovados:
https://github.com/rubentrancoso/TSE/actions/runs/40508062650

**A execucao nacional real da opcao H ainda NAO foi feita
no disco H:; nenhum resultado de periodograma por BU
recebido deve ser anunciado antes de ver o resumo local.**
