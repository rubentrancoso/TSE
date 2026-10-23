# TSE Live 2026 — Presidente

Painel local para acompanhar a apuração presidencial de 2026 diretamente do JSON oficial do TSE e construir uma série temporal.

## Leitura pública

- [O gráfico travou. O que os dados realmente mostram até agora](docs/ARTIGO_PUBLICO.md) — artigo de uma página, em linguagem acessível, com o que foi feito, os resultados atuais e os próximos passos.
- [Estado executivo da investigação](docs/ONE_PAGE_INVESTIGACAO.md) — resumo técnico dos achados e das fases.

## Rodar no Windows

1. Abra a pasta do repositório.
2. Dê duplo clique em `start_windows.bat`, o menu principal.
3. **Opção 1: COLETA COMPLETA** — descobre os arquivos oficiais, baixa tudo o que falta, valida SHA-256/ZIP, reutiliza recursos já presentes, indexa os CSVs para análise, cataloga arquivos transmitidos e gera relatórios de reconciliação. **Não é preciso executar outros comandos**.
4. A opção 2 abre o painel em `http://127.0.0.1:8765/`.

Arquivos novos e volumosos ficam no drive H:. Um arquivo já baixado e válido é reutilizado. Um download interrompido pode continuar de onde parou, quando o servidor permite. O banco SQLite e os relatórios ficam em `H:\\TSE\\forensics\\urnas\\analysis`. Há registro persistente de erros e arquivos ainda pendentes.

Requer apenas Python 3. Não há `pip install`.

## O que ele faz

- consulta o EA20 nacional do TSE a cada 10 s e permite pausar/retomar as consultas;
- grava cada estado novo em SQLite;
- preserva o histórico entre reinicializações;
- permite baixar um backup JSON completo para simulações futuras;
- plota a evolução por horário ou por % de seções;
- alterna entre % dos votos válidos e votos acumulados;
- mostra seções, válidos, comparecimento, brancos e nulos;
- exporta CSV;
- marca quedas anômalas de seções/votos entre snapshots;
- tenta importar snapshots anteriores capturados por um projeto público independente que gravou o mesmo JSON do TSE durante a apuração.

## Fontes

Atual, oficial:
`https://resultados.tse.jus.br/oficial/ele2026/6257/dados/br/br-c0001-e006257-u.json`

Backfill auxiliar:
`https://raw.githubusercontent.com/pedreirorr/painel-eleicao-2026/dados/historico-6257.json`

O backfill é uma captura externa de respostas públicas do TSE; por isso o painel mantém `source=public-capture` separado de `source=tse-live`.

## Preservação dos dados

O histórico local fica em `data/tse_history.sqlite3` e não é apagado quando o programa ou o navegador são fechados. Para manter uma segunda cópia portátil, use o botão **Backup JSON**; o arquivo inclui a série normalizada, o horário UTC de captura e os JSONs brutos recebidos do TSE.

## Coleta forense oficial

O script `collect_forensics.py` usa somente a biblioteca padrão do Python, grava cada arquivo com SHA-256 e produz manifestos para auditoria posterior.

Para executar **toda a coleta de uma vez** — snapshot nacional/UF/municípios e download de todos os arquivos oficiais encontrados no portal:

```bash
python collect_forensics.py
```


Os comandos abaixo são opcionais, apenas para executar partes isoladas:

```bash
# Descobre os conjuntos oficiais de 2026 disponíveis hoje e salva os metadados
python collect_forensics.py portal

# Preserva um snapshot nacional, por UF e de todos os municípios
python collect_forensics.py snapshot

# Baixa também todos os ZIP/CSV oficiais encontrados no portal
# Atenção: o volume pode chegar a muitos GB.
python collect_forensics.py portal --download-portal-files

# Executa snapshot e coleta do portal numa única chamada
python collect_forensics.py all --download-portal-files
```

Os arquivos ficam em `data/forensics/`. O coletor é idempotente: um snapshot final em 100% não é baixado novamente, execuções interrompidas reutilizam os JSONs concluídos e arquivos do portal já existentes são apenas conferidos por SHA-256. Em toda execução, o próprio script informa se boletins de urna, arquivos `.bu/.imgbu/.rdv` e votação por seção estão disponíveis, e registra a tentativa em `urn_availability_history.jsonl`. Execute novamente o coletor quando o TSE publicar novos conjuntos.

## Opções

```bash
python server.py --port 8765 --interval 10
python server.py --no-backfill
python server.py --no-browser
```


## Reprodutibilidade da investigação

A cadeia de proveniência e replay está documentada em docs/REPRODUCIBILITY.md.

Comandos principais:

    python replay_investigation.py --list
    python replay_investigation.py --check
    python replay_investigation.py --all --dry-run

As dependências por fase estão em provenance/PHASES.json e as fontes, com classificação primária/captura/derivado e gaps de substituição, em provenance/SOURCES.json.


## Correção da cobertura de Presidente e reparo de São Paulo (23/10/2026)

O diagnóstico mostrou **3.800.511** chaves de Presidente sem
correspondência na reconciliação anterior (espalhadas pelo país).
A lógica antiga ignorava a fonte nacional `secao_nacional`
de votação presidencial, mesmo após importá-la. O reconciliador
incremental **v2** agora usa a fonte estadual `secao` com prioridade
por chave e complementa as chaves presidenciais ausentes com
`secao_nacional`; nunca soma ambas para a mesma chave.

**Importante:** a causa de software foi demonstrada por inspeção
do código, mas a redução das 3.800.511 ausências ainda precisa ser
medida com a base real. Execute a opção **9** para conferir, na
seção `IMPORTADO secao_nacional`, a presença de linhas nacionais
antes de repetir a comparação (opção **6**).

As outras **228** chaves são do cargo **25** somente em PE:
**Conselheiro Distrital de Fernando de Noronha**, eleito em um
pleito local simultâneo à eleição geral. Exigem a fonte adequada
ao pleito municipal (documentação:
[TSE](https://www.tse.jus.br/comunicacao/noticias/2026/Outubro/eleitores-de-fernando-de-noronha-elegem-7-conselheiros-distritais)).
O diagnóstico registra o município, a zona e a seção desses casos.

O único download com falha é o ZIP de **artefatos transmitidos
de São Paulo** (`artefatos/SP/*.zip.part`), com erro de CRC.
Isso não equivale a votos diferentes; trata-se de falha de integridade
do arquivo baixado. O downloader agora preserva os bytes inválidos
em `quarantine/artefatos/SP/`, com hash e motivo, e tenta uma nova
cópia desde o início uma única vez.

Após atualizar a `main`, use a nova **opção A — Reparar APENAS
arquivos em erro**. Ela executa `python urnas.py repair` e
**não reexecuta a conciliação ou os métodos estatísticos**.
Reutiliza tudo o que estiver íntegro, indexa apenas o ZIP recuperado
e preserva um novo registro histórico.

Ordem para conferir o resultado atual:
`git pull` → menu **9** (cobertura das fontes) →
menu **A** (reparar SP) → menu **6** (nova reconciliação
incremental com fonte nacional), apenas quando confirmada a
presença do arquivo nacional de Presidente no banco.

## Diagnosticar recursos faltantes e divergencias (23/10/2026)

A coleta pode produzir relatorios estatisticos e reconciliacao mesmo quando
**um dos recursos oficiais falha**. Antes de publicar conclusoes, e necessario
identificar esse recurso e medir quais estados, turnos e cargos aparecem
sem correspondente na segunda fonte.

Apos `git pull`, use **opcao 9** no `start_windows.bat`:
`Diagnosticar ultima coleta`. Essa opcao executa
`diagnose_forensics.py`, **nao baixa arquivos, nao executa nova
importacao e nao refaz a reconciliacao**.

A etapa le `download_manifest_latest.json`, mostra os nomes e motivos
dos recursos com erro, o resumo da conciliacao e, por leitura sequencial
do CSV existente, a distribuicao dos `SEM_SECAO` por UF/turno/cargo.
O diagnostico e salvo em:

`H:/TSE/forensics/urnas/analysis/diagnostico_execucao.json`

A execucao de 23/10/2026 reportou 67.858.974 chaves comparadas,
64.058.235 coincidencias e 3.800.739 casos `SEM_SECAO`; nenhum
`SEM_BU` e nenhuma divergencia numerica `DIFERENTE` foi
contabilizada naquele resumo. **Essas unidades sao chaves, nao
eleitores, votos individuais nem secoes unicas.** Nao sabemos o
recurso com erro nem a distribuicao geografica ate executar o
diagnostico no ambiente local.

## Aceleração da reconciliação: busca indexada e multiprocessamento (23/10/2026)

A amostra do terminal mostrou avanço de ~150/6.251 zonas após
mais de 14.000 segundos e ETA instável de 156 a 189 horas.
O gargalo estava na execução de SQL com
`WITH grouped`, vários `JOIN` e antijunções por **zona**;
simplesmente executar várias cópias dessa consulta seria
desperdiçar ainda mais leituras do drive H:.

O novo `reconcile_fast.py` realiza **uma única busca indexada
por zona**, carrega apenas os registros da zona e agrega as
fontes em memória antes de comparar. Mantém prioridade de
`secao` estadual; usa `secao_nacional` somente na ausência da
chave presidencial. O código antigo permanece disponível
para testes de equivalência, não é usado na execução nova.

O agendador em `reconcile_incremental.py` permite **1–8 processos
independentes**, com limite de tarefas simultâneas para não
sobrecarregar H:. O padrão é **4 processos**; em um HDD ou
USB lento, reduzir para 2 pode ser mais rápido. O ETA agora mede
o tempo de parede do trabalho paralelo, não soma tempos de
tarefas executadas simultaneamente.

A lista de zonas/linhas planejadas é compactada e identificada
pelos hashes dos recursos e filtros; as próximas retomadas
reutilizam o planejamento em vez de repetir o `GROUP BY`
nacional. A regra de comparação e seu fingerprint v2 permanecem
**idênticos**, então os checkpoints de zonas anteriores,
validados por SHA-256, são reaproveitados.

Para usar o código novo depois de encerrar o processo anterior:

```bat
git pull
python urnas.py reconcile --workers 4
```

Se a unidade H: ficar em 100% de utilização, sem ganho de
velocidade, interrompa com Q (checkpoints preservados) e tente
`python urnas.py reconcile --workers 2` (ou `--workers 1`).
O menu opção 6 também usa quatro processos por padrão.

**Não há promessa de velocidade sem medição na máquina real.**
O novo programa precisa medir o processamento dos primeiros
grupos após a atualização para recalcular o ETA; o tempo de
planejamento, consolidação final, limitações do HDD e Windows
podem influenciar o tempo total. Não apague o SQLite, os ZIPs
ou `analysis/reconciliacao_checkpoints`.

## Reconciliação retomável com estimativa de tempo (22/10/2026)

A reconciliação anterior fazia uma única consulta SQLite nacional e não
registrava avanço parcial. Interromper aquele processo perdia as horas
**de cálculo da consulta**, mas não apagava ZIPs, importações SQLite
confirmadas ou arquivos originais.

A versão nova utiliza `reconcile_incremental.py`. A comparação
BU × seção é dividida em unidades por **UF, município, zona e turno**.
Depois de cada unidade, grava um arquivo CSV de divergências com
SHA-256 e confirma a conclusão no SQLite dos checkpoints:

```text
H:/TSE/forensics/urnas/analysis/reconciliacao_checkpoints/
  estado.sqlite3
  <fingerprint-das-fontes>/
    fontes_e_parametros.json
    partes/<hash-da-zona>.csv
```

O identificador `fingerprint` inclui versão do método, filtros,
SHA-256 dos recursos já importados, quantidade de linhas elegíveis e
escopo. **Se os arquivos oficiais ou a importação mudarem**, checkpoints
antigos não serão reutilizados. Eles continuam preservados para auditoria.

A cada 10 grupos (e nos dois primeiros), o programa mostra
grupos concluídos, percentual das linhas elegíveis cobertas,
quantos grupos foram reutilizados, divergências encontradas e
uma **estimativa aproximada do tempo restante**, calculada com base
na velocidade real dos grupos novos processados. A estimativa
é apresentada apenas depois de cinco grupos novos e não é uma promessa
de horário exato.

A coleta completa (opção **1**) usa esse mecanismo automaticamente.
A opção **6** realiza **somente a reconciliação dos dados já existentes**,
sem download nem importação. Interrompa com **Q ou Ctrl+C**; o processo
reaproveita todas as zonas concluídas na próxima execução.

O resultado final `reconciliacao_bu_secao.csv` só é substituído
**depois** de consolidadas todas as zonas. Relatórios cancelados
não são apresentados como análises completas. O resumo informa
a cobertura conhecida e sinaliza importações de urna ainda incompletas.

**Importante:** a versão nova não recupera o trabalho da consulta
nacional longa executada pelo código antigo, pois ela não gravava
checkpoints intermediários. Reaproveita, porém, os dados
baixados e indexados existentes. O próximo processamento
será retomável a partir dos novos checkpoints.

## Coleta longa: progresso, interrupção e retomada (17/10/2026)

A coleta completa da opção **1** anuncia cada etapa, inclusive o preparo
dos índices SQLite **antes de começar a percorrer os arquivos**. A cada
15 segundos, o programa confirma qual etapa continua executando.

Se a importação de um CSV grande demorar, aparecem checkpoints a cada
20 mil linhas. Esses blocos são gravados em SQLite e reutilizados na
próxima execução caso o computador pare, sem duplicação de linhas.
Os arquivos completos e as partes `.part` já baixadas também são
reutilizados, quando ainda válidos.

Para interromper a execução no Windows, use **Ctrl+C** ou, como
alternativa, **a tecla Q** com foco na janela do terminal. Também há
suporte a Ctrl+Break. A saída por cancelamento é identificada com
código 130, diferente de um erro comum. Caso o terminal esteja no modo
de seleção de texto, pressione **Esc** antes de tentar interromper;
nesse modo o Windows pode usar Ctrl+C para copiar em vez de cancelar.

Um registro persistente de cada etapa fica em:

`H:/TSE/forensics/urnas/analysis/logs/<run-id>.jsonl`

Não execute `git pull` dentro da pasta durante uma coleta ativa.
Se já tiver encerrado o programa anterior, `git pull` seguido
da **opção 1** usa as correções e reaproveita os dados locais.

O incidente da listagem de 113 recursos e do relato de parada em
recurso 58 está no evento E0073 do diário cronológico. O recurso 58
naquele catálogo era o CSV nacional de votos por seção de Presidente.
Sua importação pesada é hipótese plausível, **não causa comprovada**
da ausência de saída no terminal.

## Histórico de análises e continuação do artigo

A **opção 1 — COLETA COMPLETA** preserva automaticamente uma versão dos
relatórios anteriores **antes** dos novos cálculos e outra **depois**
da análise. O mesmo ocorre ao executar estatísticas ou reconciliação
separadamente. Não é necessário executar nenhum comando extra.

`history_forensics.py` produz manifestos por execução com ID, UTC,
versão Git, hashes dos scripts e arquivos de relatório, além do
inventário de entradas importadas. Os conteúdos ficam compactados
e deduplicados em
`H:/TSE/forensics/urnas/analysis/history/objects/`. O registro
cronológico de cada execução fica em `history/ledger.jsonl`.

O primeiro artigo está preservado:
[O gráfico travou](docs/ARTIGO_PUBLICO.md).
O [roteiro do artigo 2](docs/ARTIGO_02_PLANO.md) explica o que será
exigido antes de publicar novos resultados por urna. O
[diário cronológico](docs/DIARIO_INVESTIGACAO.md) agora registra a
transição para os novos dados, os métodos estatísticos e a política
de preservação. Nenhuma conclusão de BU foi acrescentada sem
resultado real validado.

Os dados brutos originais e o SQLite vivo não são duplicados por
esse mecanismo. A versão histórica de um relatório pode ser
restaurada sem alterar o arquivo atual; detalhes em
[Reprodutibilidade](docs/REPRODUCIBILITY.md).

## Bateria estatística automática por seção

A **opção 1 do menu** agora executa a análise estatística ao final de cada
coleta: Benford (primeiro e segundo dígitos), testes de dígitos finais,
assimetria, curtose, desvios robustos de votação por município, correlação
entre comparecimento e votação, histogramas 2D e testes contábeis.

Os relatórios são gerados em `H:/TSE/forensics/urnas/analysis/estatistica/`
e o status/cobertura está em `estatistica_resumo.json`.

Para reanalisar os dados já baixados, **sem fazer novo download**, use a
**opção 8** do `start_windows.bat`. Não há etapa manual obrigatória para
a análise estatística quando se escolhe a coleta completa.

Esses métodos produzem indicadores exploratórios, e não um veredito
de fraude. A documentação detalha pré-condições, limites e os métodos
ainda dependentes de outras fontes:
[Metodologia estatística 2026](docs/METODOS_ESTATISTICOS_2026.md).

## Coleta integral em uma só execução (opção 1 do menu)

**Este é o fluxo principal.** A opção 1 de `start_windows.bat` executa `collect_forensics.py all --download-portal-files`. A rotina descobre todos os recursos da eleição 2026 publicados até o momento, preserva/reutiliza os snapshots históricos, baixa os dados do catálogo oficial sem repetir arquivos válidos e passa automaticamente os CSVs de boletim e votação por seção para `urnas.py`. A coleta inclui arquivos binários originais; a indexação faz o inventário de seus tipos e SHA-256 por arquivo de urna. Ao final produz `votos_por_cargo_candidato.csv`, `arquivos_por_uf.csv`, `reconciliacao_bu_secao.csv`, SQLite e manifesto de downloads.

O TSE publica arquivos de votação por seção estaduais e um arquivo nacional específico de Presidente. Essas fontes são preservadas separadamente no SQLite para **não duplicar votos** na comparação. Reexecutar a opção 1 consulta a disponibilidade e reutiliza arquivos íntegros. Arquivos revisados pelo TSE são armazenados com preservação da versão anterior; não se descartam evidências. Se um item falhar, a rotina registra o erro e continua com os demais. Na próxima execução, ela tenta concluir o que ficou faltando.

**Limite técnico explícito:** `.bu`, `.rdv` e `.log` têm SHA-256, nomes e identificação de seção indexados quando disponíveis. Eles ainda **não** são convertidos de seu formato binário para todos os campos de conteúdo. A reconciliação matemática automatizada utiliza os CSVs oficiais de BU e seção. Não se deve apresentar o inventário dos binários como se fosse uma decodificação integral.

## Gestao dos boletins de urna (2026) — unidade H:

O novo `urnas.py` busca dados oficiais nos tres conjuntos do TSE:
[BU por UF](https://dadosabertos.tse.jus.br/dataset/resultados-2026-boletim-de-urna),
[Resultados e votacao por secao](https://dadosabertos.tse.jus.br/dataset/resultados-2026) e
[arquivos de urna transmitidos](https://dadosabertos.tse.jus.br/dataset/resultados-2026-arquivos-transmitidos-para-totalizacao).
Nao exige `pip install`. No Windows, grava exclusivamente em `H:/TSE/forensics/urnas` por padrao.
Se H: nao existir, aborta em vez de cair silenciosamente no C:.

**Uso principal:** execute `start_windows.bat` e selecione a opção 1 para baixar e analisar tudo. `urnas_windows.bat` abre o mesmo menu por compatibilidade. Os comandos abaixo são opcionais.

```bat
:: Apenas consulta os recursos no catalogo; nao baixa
python urnas.py status

:: Baixa e indexa BU e votacao por secao de BA, primeiro turno
python urnas.py fetch --uf BA --kind bu --kind secao

:: Outra UF, sem baixar novamente o que ja existe
python urnas.py fetch --uf MG --kind bu --kind secao

:: Baixa arquivos originais transmitidos: BU, RDV, log etc. (ZIP por UF)
python urnas.py fetch --uf BA --kind artefatos

:: Faz coleta completa de todos os tipos por UF (necessita muito espaco)
python urnas.py fetch --all --kind bu --kind secao --kind artefatos

:: Apenas reprocessa os arquivos locais, sem rede
python urnas.py import

:: Consulta uma secao individual depois de baixar a UF respectiva
python urnas.py export --uf BA --municipio 33693 --zona 177 --secao 111

:: Compara por candidato/cargo/secao as duas fontes oficiais disponiveis
python urnas.py reconcile --uf BA

:: Recalcula SHA-256 dos arquivos gravados
python urnas.py verify
```

**Arquivos locais:** `H:/TSE/forensics/urnas/raw/` preserva os ZIPs/CSVs
originais e metadados com SHA-256; `H:/TSE/forensics/urnas/analysis/urna_2026.sqlite3`
guarda linhas de CSV de BU e de votacao por secao, com todos os campos originais
em `dados_json` e colunas indexadas (`uf`, `municipio`, `zona`,
`secao`, `turno`, `cargo`, `votavel`, `votos`).
`reconcile` produz `reconciliacao_bu_secao.csv` somente com chaves
divergentes ou ausentes, mais resumo JSON.
Nao confundir o hash SHA-256 local com a verificacao de assinatura
criptografica da urna: sao controles distintos.

**Limites atuais importantes:** O catalogo oferece ZIPs por UF, nao entrega
necessariamente cada secao isoladamente. O parametro de secao filtra a analise
depois do download da UF. Os formatos binarios `.bu`, `.rdv` e `.log`
sao preservados e catalogados, mas nao decodificados nesta versao.
A analise por votos usa os CSVs oficiais publicados. Diferencas entre
fontes podem incluir secoes agregadas, atualizacoes e divergencias de esquema;
nao indicam automaticamente fraude. A integracao de um decodificador
validado dos arquivos binarios permanece etapa independente.
O programa ainda não foi validado em uma coleta real completa de todas as UFs.
Os arquivos disponíveis no computador do usuário não são acessíveis a partir do GitHub; a execução integral e os relatórios precisam ser confirmados no ambiente Windows antes de publicação de conclusões.


O mesmo modulo tambem pode ser acionado pelo coletor existente, sem alterar
os comandos anteriores:

```bat
python collect_forensics.py urnas status
python collect_forensics.py urnas fetch --uf BA --kind bu --kind secao
python collect_forensics.py urnas reconcile --uf BA
```

Teste offline com dados sinteticos:
`python -m unittest discover -s tests -p test_urnas.py -v`.


**Integracao da coleta completa:** `python collect_forensics.py` e
`python collect_forensics.py all --download-portal-files` continuam
preservando snapshots e outros recursos do portal no diretorio anterior, mas
agora encaminham BU, arquivos transmitidos e votacao por secao de 2026
automaticamente para `H:/TSE/forensics/urnas`. Nunca duplicam esses
recursos novos no antigo diretorio do portal. Para consultar sem downloads,
use `python urnas.py status`.
