# Exame de imagem: vales recorrentes em grafico atribuido a apuracao 2022

Data: 27/10/2026. Escopo estritamente **2022, segundo turno presidencial**, conforme transcricao do video enviada pelo investigador. Nao misturar com cronologia de Flavio Bolsonaro em 2026. O grafico recortado foi fornecido como fotografia de tela, e nao como CSV original ou figura com legenda completa.

## Alegacao apresentada no video

1. Sequencia de 472 mil boletins supostamente colocados em ordem de transmissao.
2. Apenas uma troca de lideranca na curva cumulativa, embora 3.000 permutacoes aleatorias da ordem alegadamente gerassem varias.
3. Sete vales, alegadamente igualmente espacoados, e trechos de decida quase linear seguidos de recuperacao.
4. Interpretacao proposta pelo apresentador: um algoritmo ativaria e desativaria uma penalizacao sobre Bolsonaro.

Os pontos 1 e 2 sao declaracoes do video, nao verificados por dados ou codigo disponibilizados aqui. O ponto 3 pode ser avaliado parcialmente na fotografia; somente dois vales grandes aparecem na imagem recortada.

## Medicao direta da fotografia

Fonte: screenshot fornecido nesta conversa, tamanho 1080 x 1440 pixels.
O traco azul foi identificado pela dominancia do canal azul
no intervalo aproximado de x=85..1034, y=690..870.
A posicao vertical foi interpolada em 7 colunas
com traco ausente e suavizada com filtro gaussiano
sigma=8 pixels, apenas para medir a forma.
Dois minimos do sinal, correspondentes aos vales na imagem,
foram detectados com proeminencia >25 px e distancia >200 px:

- primeiro vale: x = 363 px, posicao aproximada no eixo x = 70,5 mil;
- segundo vale: x = 814 px, posicao aproximada no eixo x = 75,0 mil;
- afastamento = 451 px, aproximadamente 4,5 mil unidades de eixo;
- correlacao de Pearson entre perfis de 155 pixels
  alinhados em torno dos dois vales (-65,+90):
  aproximadamente 0,944. Em trecho -55,+70: ~0,950.

IMPORTANTE: as janelas sao escolhidas pela observacao
dos vales; esse coeficiente mede SEMELHANCA GEOMETRICA
da imagem processada e NAO tem valor-p calibrado.
A foto nao mostra escala vertical, titulo, fonte numerica,
formula de suavizacao, coluna de tempo ou codigo de ordenacao.
Nao permite verificar os outros cinco vales alegados.

## Erro metodologico mais importante a investigar

O eixo horizontal exibe marcas 68k, 70k, 72k, 74k e 76k;
**nao exibe horarios**. A recorrencia observada,
se confirmada, e uma periodicidade em POSICAO NA SERIE,
nao necessariamente em intervalo de tempo.

O teste de 3.000 permutacoes aleatorias citado pelo
apresentador pressupoe que urnas sejam permutaveis em
toda a base nacional, inclusive entre localidades com
votacoes e horarios de transmissao diferentes.
Se a ordem real for espacial e logisticamente
estruturada, esse nao e um nulo que representa
o fluxo real de transmissoes. Um resultado incomum
contra esse nulo nao distingue manipulacao de
estrutura de recepcao. Da mesma forma, observar
sawteeth no grafico nao indica ainda se eles
estao nos valores individuais ou na transformacao
da serie, como media movel, downsampling,
agregacao por lotes ou ordenacao.

Isso NAO descarta a possibilidade de padrao artificial
nos dados. E uma condicao para localizar sua origem.

## Experimentos decisivos e falsificaveis

A — Reconstruir exatamente a serie do video usando
o codigo, parametro de eixo X, ordenacao e origem do
timestamp de cada secao (TSE 2022, turno 2).
Se nao houver timestamp individual verificavel,
nao declarar que a lista representa ordem de envio.
Comparar a serie em forma BRUTA versus suavizada.
Preservar chave UF/municipio/zona/secao.

B — Registrar automaticamente TODOS os vales na
serie integral, seus centros, distancias em numero
de secoes, proeminencias, larguras, velocidades
das quedas, correlacoes de forma e homogeneidade
dos espacamentos (coeficiente de variacao).
Aplicar periodograma/autocorrelacao sobre RESIDUOS
apos tendencia, sem definir periodo ou intervalo
somente por inspeccao visual. Corrigir teste
da maior frequencia sobre todas as frequencias
experimentadas.

C — Consultar as chaves e timestamps de cada
secao nas janelas de queda, e sobrepor mudancas
de UF, municipio, zona, lote de publicacao,
regime da secao e faixa de tempo. Repetir a
analise nos votos brutos e em outras variaveis
para verificar se os vales sao efeito da
sequencia, do codigo do grafico ou das contagens.

D — Comparar com dois grupos de nulos:
(i) redistribuicao de urnas entre blocos
permutaveis da mesma UF/municipio/zona,
preservando tamanhos e preferencias;
(ii) embaralhamento apenas da ORDEM dos
blocos de recepcao de tamanho comparavel,
preservando os boletins inteiros.
Nao embaralhar votos INDIVIDUAIS como substituto
do embaralhamento de urnas. Rodar pelo menos
3.000 replicacoes, gravar seeds e distribuir
as estatisticas de maximo e periodicidade.

E — Se os vales persistirem nos BUs por secao
sob todas as alternativas do grafico e forem
estatisticamente extraordinarios sob controles
ajustados, buscar confronto material, para as
mesmas chaves, entre BU impresso/QR coletado
independentemente e arquivos digitais publicados.

**Criterios de decisao:**
- Picos so aparecem apos alguma transformacao:
  investigar artefato do grafico.
- Picos aparecem no bruto, mas coincidem com
  limites/fluxos territoriais: modelo de
  ordenacao explica parte ou todo padrao.
- Picos persistem no bruto apos condicionar
  geografia, volumes e filas, com calibracao
  estatistica: anomalia de mecanismo de geracao,
  necessitando verificacao documental.
- Desvio de votos comprovado requer evidencia
  independente do BU e reconciliacao por secao.

## Fontes de base localizaveis sem confundir votos 2026

O portal publico do TSE oferece para 2022:
historico de totalizacao para Presidente,
detalhe de apuracao por secao e BU por UF.
Consulta: https://dadosabertos.tse.jus.br/pt_PT/dataset/resultados-2022

**Estado:** dois vales repetidos confirmados na FOTO;
sem acesso aos dados numericos de 2022 usados para
gerar o grafico, nao se pode identificar a causa
nem verificar a alegada periodicidade dos sete vales.
O protocolo acima estabelece testes objetivos.
