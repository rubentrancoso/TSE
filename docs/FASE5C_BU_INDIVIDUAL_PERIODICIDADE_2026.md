# Fase 5C — periodicidade dos BU individuais, primeiro turno de 2026

**Status em 27/10/2026:** Fase 5C executada com 499.206 BU reais de 2026. Fase 5E concluida com 2026 real; I e K disponiveis, ainda sem dados locais de execucao.. Nao usar microdados de 2022.

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

**A opcao H foi executada no disco H: em 27/10/2026.**

## Execucao empirica real H: — 27/10/2026

O investigador executou **opcao H** no Windows, e disponibilizou
a saida integral da execucao. O teste de 3 testes e o teste
de 5 testes, que aparecem no comeco da saida com arquivos
C:\Users\PC\AppData\Local\Temp, sao fixtures SINTETICAS.
O periodo de aproximadamente 7,11 minutos e p=0,009901
foi INJETADO nesse teste pequeno e NAO corresponde ao
resultado eleitoral real.

**Resultado real, 28 origens (27 UFs + ZZ):**
- 28 ZIPs BWEB locais identificados e SHA-256 validados;
- 499.206 secoes presidenciais individuais extraidas e associadas
  a DT_BU_RECEBIDO; zero horarios em branco;
- 354 minutos de recebimento, 254 deles com >=10 mil
  votos validos e submetidos ao teste;
- apenas um vale local ultrapassou proeminencia de 8 pp:
  21:31 BRT em 04/10, apos 496.190 secoes,
  com 15.312 votos validos no respectivo minuto,
  residuo = -4,43335 pp e proeminencia = 9,24395 pp;
- pico de periodo = 14,208199 MINUTOS;
  melhor R-quadrado senoidal = 0,03954052;
- controle de 1000 permutacoes individuais: p = 0,3086913;
- controle de 1000 permutacoes em blocos de 5: p = 0,4945055.

**Leitura do resultado:** nesse recorte e com esses controles,
nao foi detectada periodicidade extraordinaria.
Isso NAO e veredito de regularidade de cada BU; em particular,
os BUs empatados no mesmo minuto nao foram postos numa
ordem artificial.

**Conferencia de cobertura em aberto:** 499.206 BU
presidenciais extraidos contra 499.248 secoes
exibidas no ultimo snapshot presidencial nacional
da fase 5A. Sao **42 chaves de diferenca**, que
podem ter origem em escopo ou categoria de secao.
Nao se conclui perda de votos a partir desse numero.
O JSON da Fase 5C inclui diferencas de votos entre
o conjunto BWEB e os totais nacionais, que devem
ser examinadas antes de concluir abrangencia completa.

**Interpretacao do campo coverage=0.0 na saida anterior:**
trata-se de fraction_sections_in_UF_span_under_5min,
isto e, proporcao de secoes em UFs cujos horarios
ficam todos concentrados em menos de 5 minutos.
O valor zero nao significa falta de cobertura de
horarios; o campo com_hora confirma 499.206/499.206.

**Proximos testes implementados:**
- Opcao I, Fase 5D: sensibilidade a filtros de volume
  e janela de suavizacao, usando a serie por MINUTO
  previamente calculada. Nao relê ZIPs, SQLite ou BU.
- Opcao J, Fase 5E: usa o campo original
  DT_BU_RECEBIDO com SEGUNDOS, que ja foi
  preservado nos shards received-XX.csv.
  Agrega primeiro BUs de mesmo segundo (nao
  inventa a ordem desses BUs) e forma blocos
  consecutivos de 500, 1000 e 2000 secoes.
  Mede vales, periodo em secao e minutos e
  contrasta com permutacoes. Esta abordagem
  esta mais proxima da escala do video.
Os testes empiricos I e J NAO ocorreram ainda.

## Resultados empiricos J — Fase 5E, 27/10/2026

A saida enviada pelo investigador inclui PRIMEIRO uma fixture
de teste com 120 BU e 60 segundos, no diretorio Temp,
que NAO faz parte dos resultados eleitorais.

**Fase real, primeiro turno 2026:**
499.206 BUs, 9.039 segundos distintos, 100% dos horarios
com segundos explicitos. Blocos de 500/1000/2000 BUs
produziram 893/470/243 pontos analisaveis. Zero vales
residuais acima de 8 pontos percentuais (pode haver menores).

| Bloco alvo | Periodo preferido (BU) | R2 | p individual | p bloco cinco |
|---|---:|---:|---:|---:|
| 500 | 4.829,436671 | 0,01776219 | 0,039801 | 0,2089552 |
| 1000 | 4.829,436671 | 0,01976418 | 0,6368159 | 0,8706468 |
| 2000 | 35.103,147196 | 0,04767183 | 0,159204 | 0,6069652 |

O periodo 4.829 BU e uma frequencia CANDIDATA,
nao confirmacao independente em duas escalas: a
base e a mesma. O p exploratorio individual de 500 BU
nao resiste a blocos de cinco atualizacoes. A escolha
do minimo entre varios testes nao tem ajuste conjunto
adicional para a grade de blocos, e as permutacoes
nao preservam toda a estrutura geografica.

**A conciliacao aritmetica nacional encontrou:**
- Flavio: 56.104.503 BWEB = 56.104.503 oficial.
- Lula: 53.879.538 BWEB = 53.879.538 oficial.
- Validos BU: 119.306.034; validos nacional: 119.300.788;
  diferenca **+5.246** atribuivel ARITMETICAMENTE
  ao grupo dos outros candidatos e sua classificacao.
- Demais BU = 9.321.993 e demais nacional = 9.316.747.
  Isso nao identifica o candidato nem a origem da diferenca.
- BWEB 499.206 secoes x nacional snapshot 499.248:
  diferenca de contagem = -42. Escopos podem diferir.

O antigo diagnostico de BA/MG exibia diferencas municipais
de 6 e 36 secoes respectivamente, somando 42; nao foi
demonstrado serem as mesmas 42 secoes da discrepancia
nacional (correspondencia nao verificada).

Nova opcao **K** foi programada para localizar a diferenca
de 5.246 validos por UF, sem reabrir os ZIPs BWEB,
sem downloads, SQLite ou dados de 2022. Usa os arquivos
received-UF.csv da opcao H e a tabela oficial nacional
uf_candidate_reconciliation.csv versionada no repositorio.

A opcao **I** continua disponivel para sensibilidade de
limiares e suavizacao; nao substitui uma pesquisa de
anomalias calibrada pela composicao territorial.
