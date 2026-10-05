# TSE Live 2026 — Presidente

Painel local para acompanhar a apuração presidencial de 2026 diretamente do JSON oficial do TSE e construir uma série temporal.

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

Os arquivos ficam em `data/forensics/`. Cada snapshot recebe um diretório com timestamp UTC; downloads interrompidos usam arquivo temporário e podem ser retomados. Em toda execução, o próprio script informa se boletins de urna, arquivos `.bu/.imgbu/.rdv` e votação por seção estão disponíveis, e registra a tentativa em `urn_availability_history.jsonl`. Execute novamente o coletor quando o TSE publicar novos conjuntos.

## Opções

```bash
python server.py --port 8765 --interval 10
python server.py --no-backfill
python server.py --no-browser
```
