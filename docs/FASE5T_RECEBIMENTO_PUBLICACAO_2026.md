# Fase 5T — teste de condicionamento temporal: BWEB recebidos vs EA20 publicados

**2026-10-28:** codigo, testes sinteticos, BAT e notebook implementados.
A **opcao Y ainda nao foi executada em H:**, portanto nao afirmar
resultado do emparelhamento de cronologias.

## Por que esta etapa e necessaria

A Fase X, executada no Windows sobre 193 capturas EA20 nacionais
versionadas, validou 152 incrementos depois de 20:04:39 BRT.
Havia 100.491.132 validos e 424.153 secoes naquele snapshot,
contra 119.300.788 validos e 499.248 contadores no final;
**18.809.656 votos validos** foram publicados apos o corte.

Os lotes foram muito irregulares: aproximadamente 4.891.708 validos
em **3** atualizacoes iniciais, e 4.392.349 em **103** atualizacoes
no quarto bloco. A participacao Lula nos lotes progrediu entre
aproximadamente 50,8% e 60,2% entre os quatro blocos.
A reta R²=0,99044 no eixo seções acumuladas nao demonstra por si
um sistema de atualizacoes uniformes. Um contrafactual que usa a
proporcao FINAL 54,08809% de Lula em todos os lotes, mantendo
volumes e quantidades INTEIRAS de candidatos, atingiu R²=0,99885;
e controle circular, nao mecanismo causal.

A Fase Y enfrenta a proxima condicao operacional.

## Hipotese formal (CONDICIONAL)

Se BWEB `DT_BU_RECEBIDO` representa a efetiva entrada do
BU do qual se alimenta a publicacao EA20, os dois registros
compartilham um mesmo relogio BRT sincronizado, e a publicacao
so ocorre apos o recebimento, entao deve valer
para **CADA** timestamp nacional observado t:

    EA20_validos_publicados(t) <= BWEB_validos_recebidos_ate(t)
    EA20_Lula_publicados(t)    <= BWEB_Lula_recebidos_ate(t)
    EA20_Flavio_publicados(t)  <= BWEB_Flavio_recebidos_ate(t)

Essas desigualdades sao **condicoes NECESSARIAS**,
nao suficientes. Uma falha **invalida pelo menos uma
das premissas conjuntas**, mas nao determina qual.
Um resultado sem falha nao comprova buffering, autenticidade
ou correspondencia entre lotes.

O universo e o **1T presidencial de 2026**. Por isso
valida o final de 119.300.788 validos, 53.879.538
Lula, 56.104.503 Flavio, 499.206 seções BWEB.
A divergencia de +42 contadores nacionais EA20
corresponde a ZZ sem votantes, investigada em O–R;
nao se compara igualdade de contadores EA20 e BWEB.

## Implementacao

`audit_receipt_publication_timing_2026.py`:

- faz uma varredura unica dos CSV H e NR28 M por UF,
  confere SHA-256 de ambos e dos metadados de origem;
- corrige exatamente os 5.246 votos NR28 e reconcilia
  os totais nacionais com votos inteiros;
- agrupa **por segundo declarado**, sem inventar ordenacao
  entre BUs empatados;
- para cada uma das 193 capturas nacionais EA20,
  calcula quantos votos BWEB foram recebidos com
  timestamp menor ou igual ao timestamp EA20;
- escreve diferencial `recebido-publicado` de validos,
  Lula e Flavio, quantifica quantas capturas violam
  cada condicao, a maior falta em votos e primeiro
  instante de cada violacao;
- calcula a primeira disponibilidade agregada por
  **CONTAGEM** de votos suficiente para cada captura
  nas tres metricas, e a folga temporal ate publicacao.
  Essa folga **nao e lag por BU**: falta identidade
  fisica do conjunto de votos publicado;
- avalia offsets **fixados antes** da execucao:
  0, -5 min, +5 min, -3 horas e +3 horas.
  Uma melhora com algum offset nao valida por si
  uma interpretacao de fuso horario;
- preserva a fonte EA20 nacional no repositorio,
  nao acessa ZIP, rede, SQLite nem segundo turno.

Saidas em H:/TSE/forensics/urnas/analysis/periodicidade_bweb_2026:

- `phase5t_receipt_vs_publication_2026_summary.json`
- `phase5t_receipt_vs_publication_timeline_2026.csv`
- `phase5t_receipt_vs_publication_offsets_2026.csv`

O JSON inclui SHA da fonte nacional, manifestos H/M,
hashes de cada UF BWEB/NR28 e SHA dos CSV de saida.
Notebook: `notebooks/TSE_2026_Laboratorio_Forense_Fase_Y.ipynb`.

Execucao: `git pull origin main` →
`start_windows.bat` → **Y**, depois **U**.

## Interpretação forense e limites

1. Primeiro confirmar semantica documental de
   `DT_BU_RECEBIDO` e `gerado_brt`, origem
   dos clocks, possivel defasagem UTC/BRT e
   versoes dos arquivos. O relogio nao foi
   independentemente certificado.
2. Uma violacao da condicao cumulativa nao e,
   por si, prova de adulteracao de qualquer BU.
   Pode indicar diferenca de clock, de origem dos
   eventos de publicacao, ou problema operacional.
3. Uma desigualdade satisfeita so demonstra
   compatibilidade necessaria em contagens agregadas,
   nao qual BU foi publicado nem seu tempo de espera.
4. Candidatos sao testados separadamente:
   validos suficientes no total nao implicam
   que os votos de Lula/Flavio individualmente
   fossem suficientes no mesmo horario.
5. Proximo passo, se disponivel: snapshots EA20
   estaduais sincronizados ou identificadores
   por secao entre recepcao e publicacao.
   Nao reconstruir o que nao foi observado.
