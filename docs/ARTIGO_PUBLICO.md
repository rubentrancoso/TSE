# O gráfico travou. O que os dados realmente mostram até agora

**Uma investigação aberta e reproduzível sobre a divulgação da eleição presidencial de 2026**

Na noite da eleição, milhões de pessoas acompanhavam uma linha na tela. Então, a atualização do resultado presidencial ficou para trás enquanto números estaduais continuavam avançando. Quando o painel voltou a se mover, milhões de votos apareceram em pouco tempo e a curva mudou de direção. A pergunta surgiu imediatamente: foi apenas um problema de divulgação ou aconteceu algo com os votos?

Foi para responder a essa pergunta — sem presumir fraude, mas também sem aceitar explicações sem teste — que construímos este projeto.

## O que foi construído

O trabalho começou como um painel local para acompanhar o resultado oficial do TSE em tempo real. O sistema consulta os arquivos públicos, registra cada mudança em banco de dados, preserva o JSON bruto e permite rever a evolução da apuração. O gráfico mostra percentuais, votos acumulados, diferença entre candidatos e saldo de cada novo lote, sem confundir uma curva acumulada com a composição real dos votos que acabaram de entrar.

Depois, o painel virou uma infraestrutura de investigação. Criamos um coletor único e retomável, capaz de preservar o resultado nacional, as 27 unidades da Federação, o exterior e todos os municípios. Cada arquivo recebe hash SHA-256 e entra em um manifesto, para que qualquer cálculo posterior possa ser repetido e auditado.

Também criamos scripts separados para cada hipótese, um diário cronológico que não apaga conclusões antigas e uma arquitetura de replay. A regra é simples: dado bruto não é relatório; observação não é hipótese; anomalia não é prova de fraude.

## O que já foi preservado

Até agora, a base local contém **8 snapshots**, com **5.785 de 5.785 JSONs** no snapshot final, além de **224 arquivos oficiais do portal**, somando **372,13 MB**. A coleta terminou sem arquivos incompletos e sem erros reportados.

O resultado final nacional contém **499.248 seções** e **119.300.788 votos válidos**. A soma das 27 UFs mais o exterior coincide exatamente com o total do Brasil. Também não encontramos falhas internas nos arquivos analisados: a soma dos candidatos fecha com os votos válidos e, onde os campos são comparáveis, válidos, brancos e nulos fecham com o comparecimento.

Divergências iniciais encontradas na Bahia e em Minas Gerais foram investigadas em vez de tratadas como conclusão. Elas correspondiam a arquivos municipais defasados em relação ao agregado estadual, e não a votos soltos ou a uma quebra aritmética do resultado final.

## O que aconteceu na janela crítica

Capturas contemporâneas independentes confirmam que o arquivo nacional de Presidente ficou fortemente defasado. Entre **19h14min08s e 20h04min39s**, o agregado nacional incorporou de uma vez **100.614 seções** e **24.728.306 votos válidos**.

Depois das 20h04min39s, restavam **18.809.656 votos válidos** até o resultado final. Nesse conjunto, Lula recebeu **54,0881%** e Flávio, **39,3429%**. Em 152 atualizações consecutivas, a participação acumulada de Lula subiu e a de Flávio caiu.

À primeira vista, essa sequência parece improvável. Mas as atualizações não são 152 moedas lançadas ao acaso. São partes sucessivas do mesmo conjunto de votos, organizadas por uma ordem geográfica e operacional. Quando os lotes são dependentes e vêm de regiões politicamente diferentes, calcular a probabilidade como `(1/2)^152` produz uma aparência de impossibilidade que o modelo não sustenta.

O controle geográfico reforça essa explicação. As zonas que terminaram mais tarde eram mais favoráveis a Lula — e esse mesmo padrão já aparecia nessas zonas em 2022. No corte das 20h04, a diferença entre zonas tardias e adiantadas foi de **24,39 pontos percentuais** em 2026 e **23,64 pontos** em 2022: uma variação histórica de apenas **0,75 ponto**.

Isso não prova que todo o processo funcionou corretamente. Prova algo mais específico: a direção política dos votos tardios tem uma explicação geográfica forte e não nasceu, por si só, no travamento do painel.

## O que os resultados permitem dizer

Até este ponto, há evidência sólida de uma **defasagem operacional ou de publicação** no resultado presidencial. Há também uma explicação composicional consistente para o perfil dos votos que apareceram mais tarde.

Não encontramos, nos dados já reconciliados, uma discrepância material no total final nem uma quebra contábil que sustente a afirmação de fraude. Isso também não encerra a investigação: um resultado final que fecha não explica sozinho por que a divulgação ficou atrasada, em qual camada ocorreu o problema ou quando cada seção presidencial estava realmente disponível.

A maior limitação é temporal. Nossos snapshots locais começam tarde e cobrem apenas **999.110 votos**, ou **5,31%** do conjunto posterior às 20h04. Porém, uma captura independente feita às **20h05min57s** preservou os 28 agregados por UF e exterior. Com ela, já é possível reconstruir geograficamente **18.480.901 votos**, equivalentes a **98,25%** do período pós-retomada. Restam sem localização exata **328.755 votos**, concentrados nos 78 segundos iniciais.

## O que falta fazer

O próximo passo é executar e publicar a reconstrução por UF do trecho entre 20h05min57s e o resultado final, identificando quanto cada estado contribuiu para o lote tardio e comparando essa composição com os controles históricos.

Depois, a prioridade é obter versões oficiais antigas dos arquivos do TSE para substituir ou confirmar as capturas independentes, especialmente entre 18h40 e 21h30. Também faltam os dados completos por seção — Boletins de Urna, RDV e arquivos equivalentes — para reconciliar o resultado diretamente urna por urna e separar definitivamente recebimento, totalização e publicação.

Por fim, precisamos localizar uma série temporal de 2022 com resolução comparável e produzir o relatório final com fontes, hashes, código, limitações e hipóteses alternativas.

A investigação ainda não terminou. Mas ela já mudou a pergunta. Não estamos mais diante de uma curva estranha na tela. Estamos diante de um evento mensurável, com milhões de votos preservados, totais reconciliados, uma lacuna temporal delimitada e próximos testes definidos. É assim que uma suspeita pública pode ser transformada em uma investigação verificável.

## Dados disponíveis e contato

Todos os dados preservados, scripts de coleta e análise, resultados derivados e documentos metodológicos deste trabalho estão disponíveis publicamente no GitHub: [github.com/rubentrancoso/TSE](https://github.com/rubentrancoso/TSE). Se você tiver qualquer pergunta, dúvida, crítica, informação adicional ou interesse em acompanhar e colaborar com a investigação, pode entrar em contato pelo próprio repositório.
