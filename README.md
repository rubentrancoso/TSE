# TSE Live 2026 — Presidente

Painel local para acompanhar a apuração presidencial de 2026 diretamente do JSON oficial do TSE e construir uma série temporal.

## Leitura pública

- [O gráfico travou. O que os dados realmente mostram até agora](docs/ARTIGO_PUBLICO.md) — artigo de uma página, em linguagem acessível, com o que foi feito, os resultados atuais e os próximos passos.
- [Estado executivo da investigação](docs/ONE_PAGE_INVESTIGACAO.md) — resumo técnico dos achados e das fases.

## Rodar no Windows

1. Baixe/clone este repositório.
2. Dê duplo clique em `start_windows.bat`.
3. O navegador abre em `http://127.0.0.1:8765/`.

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


## Gestao dos boletins de urna (2026) — unidade H:

O novo `urnas.py` busca dados oficiais nos tres conjuntos do TSE:
[BU por UF](https://dadosabertos.tse.jus.br/dataset/resultados-2026-boletim-de-urna),
[Resultados e votacao por secao](https://dadosabertos.tse.jus.br/dataset/resultados-2026) e
[arquivos de urna transmitidos](https://dadosabertos.tse.jus.br/dataset/resultados-2026-arquivos-transmitidos-para-totalizacao).
Nao exige `pip install`. No Windows, grava exclusivamente em `H:/TSE/forensics/urnas` por padrao.
Se H: nao existir, aborta em vez de cair silenciosamente no C:.

**Uso facil:** execute `urnas_windows.bat`, que oferece menu de disponibilidade,
download por UF, download completo, verificacao, exportacao e conciliacao.

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
O programa nao foi validado ainda com um download completo de todas as UFs;
recomenda-se comecar por uma UF pequena e conferir o resumo antes de usar
resultados na investigacao.


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
