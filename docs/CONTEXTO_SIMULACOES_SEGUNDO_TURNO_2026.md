# Comparação histórica: probabilidades anunciadas antes do segundo turno de 2026

**Situação:** fonte exógena, **segundo turno presidencial de 25/10/2026**.
Não é uma auditoria de BUs/EA20 do primeiro turno em 04/10.

## Afirmação recebida

"Houve simulações das pesquisas nas quais Lula teria menos de 2%
de chance de vencer Flávio Bolsonaro."

### Verificação

**Existe um exemplo real e anterior à eleição**: no projeto
[berndof/eleicao-2026](https://github.com/berndof/eleicao-2026),
a metodologia M1 (projeção estrutural de transferência de votos)
atribuiu a Lula **0,3% de chances de vencer o segundo turno**,
ou ~3 em cada 1.000 simulações do método.

O dado já aparece no [primeiro commit do projeto,
f976e78 (criado em 05/10/2026 02:44:29 UTC =
04/10/2026 23:44:29 BRT)](
https://github.com/berndof/eleicao-2026/commit/f976e78b04c999e3c7833c181c564fd1e5e299c3).
O documento textual com os números após correção da base de pesquisas
consta do [commit 528b1d8 (05/10/2026 03:44 UTC)](
https://github.com/berndof/eleicao-2026/blob/528b1d8b6bf8c46c71e2d0d9159cb47b5f847e6a/docs/artigo.pt.md).
Esses commits são anteriores ao pleito de 25/10,
independentemente de eventuais atualizações posteriores do site.
O próprio autor alerta que o M1 tem intervalos possivelmente
estreitos demais.

**Não é correto** dizer que "menos de 2% de todas as simulações"
apontavam vitória de Lula: os métodos alternativos desse
mesmo projeto não são tão restritivos:

| Modelo | Lula venceria em | Lula média dos válidos | Intervalo central de 90% |
|---|---:|---:|---|
| M1 transferência de votos | 0,3% | 47,19% | 45,44–48,91% |
| M2 pesquisas corrigidas | 31,7% | 48,86% | 44,91–52,83% |
| M3 histórico eleitoral | 41,1% | 49,35% | 43,41–55,29% |
| Combinação M1/M2/M3 | 17,9% | 48,12% | 45,12–52,58% |

O peso da combinação (50%/30%/20%) foi uma decisão subjetiva
do autor. As metodologias têm correlações de informações
e premissas, logo não são três experimentos totalmente
independentes; a proporção de cenários vencedores só vale
DENTRO de cada modelo.

Projeções posteriores, publicadas em **24/10**, também
atribuíam chances de vitória de Lula **bem superiores a 2%**:
- [Plano Político](https://www.planopolitico.com.br/modelos-eleitorais/presidencial/):
  16% de vitória;
- [Opinião Inteligência Política](https://eleicoes2026.opiniao.inf.br/analises/segundo-turno/):
  17% de vitória.

**Possível confusão adicional:** o modelo Plano Político
apresentou **2% das simulações com Lula terminando com MAIS
DE 52% dos votos**, o que é distinto de vencer com
50,01% a 52%. O resultado oficial foi **51,79%**,
portanto esse evento de 2% não ocorreu.

Resultado oficial anunciado pelo
[Tribunal Superior Eleitoral em 26/10/2026](
https://www.tse.jus.br/comunicacao/noticias/2026/Outubro/presidente-do-tse-anuncia-reeleicao-de-lula-e-faz-balanco-do-2o-turno-das-eleicoes-2026):
**Lula 64.256.232 votos válidos (51,79%)**,
**Flávio Bolsonaro 59.826.041 (48,21%)**,
num total de 124.082.273 votos válidos.

Esse resultado ficou **4,60 pontos percentuais acima
da média do M1** e **2,88 pontos acima do limite superior
do intervalo central de 90% do M1**; já estava dentro
dos intervalos centrais de M2, M3 e combinação.
Foi um resultado de baixa probabilidade sob M1,
mas não uma vitória impossível ou igualmente improvável
sob todas as metodologias.

## O que pode explicar a divergência

O M1 utiliza o comportamento de transferência de votos,
mobilização e retenção territorial calibrados principalmente
em 2022 e pesquisas de transferência disponíveis em outubro.
A previsão foi condicionada aos dados conhecidos no começo
do mês, com choque de campanha genérico de ±1,5 ponto na margem.
Se a transferência, a mobilização, a abstenção ou a campanha
mudaram depois, seu intervalo preditivo ficou inadequado.
O próprio backtest do primeiro turno já indicava subestimação
de incerteza em componente do modelo.

Outros modelos (M2, M3, agregadores posteriores) usaram premissas
diferentes e produziram intervalos mais amplos. A literatura
estatística distingue a probabilidade que um modelo atribui
a um evento de um teste de integridade da contagem.

## Uso forense apropriado

1. Registrar **a previsão anterior à eleição**, suas versões,
   método, data e possíveis revisões posteriores.
2. Revisar calibração e poder preditivo fora da amostra em
   eleições anteriores: um modelo que exclui o resultado real
   de seus intervalos com frequência pode ser mal calibrado.
3. Verificar diferenças entre transferência por UF,
   abstenção e votos entre os dois turnos com dados oficiais
   separados, sem somar 1T e 2T.
4. Para a hipótese de fraude, continuar confrontando BUs
   assinados, chaves de seção, totalizações e eventos de
   recepção/publicação que possam ser certificados.
5. **Jamais** converter "chance de vitória de Lula estimada
   em 0,3%" em "probabilidade de não haver fraude de 0,3%"
   ou "probabilidade de fraude de 99,7%". Seria uma
   inversão lógica incorreta.

Os valores e URLs, incluindo o resultado oficial,
estão preservados em
`data/forensics/external/segundo_turno_previsoes_2026_proveniencia.json`,
e são visualizados em apêndice do notebook público
`notebooks/TSE_2026_Painel_Publico_Forense.ipynb`.
A fonte principal é um modelo **independente do nosso projeto**,
mas não um controle independente dos votos por seção.
