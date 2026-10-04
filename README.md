# TSE Live 2026 — Presidente

Painel local para acompanhar a apuração presidencial de 2026 diretamente do JSON oficial do TSE e construir uma série temporal.

## Rodar no Windows

1. Baixe/clone este repositório.
2. Dê duplo clique em `start_windows.bat`.
3. O navegador abre em `http://127.0.0.1:8765/`.

Requer apenas Python 3. Não há `pip install`.

## O que ele faz

- consulta o EA20 nacional do TSE a cada 10 s;
- grava cada estado novo em SQLite;
- preserva o histórico entre reinicializações;
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

## Opções

```bash
python server.py --port 8765 --interval 10
python server.py --no-backfill
python server.py --no-browser
```
