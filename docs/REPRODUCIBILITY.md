# Reprodutibilidade, proveniência e substituição por fontes primárias

## Princípio

A investigação deve poder ser refeita do zero e deve distinguir três camadas de trabalho: evidência bruta, normalização e teste analítico. Relatórios e resumos são derivados; nunca devem virar fonte para um teste.

Uma conclusão é reproduzível quando conseguimos identificar o código, as entradas exatas, seus hashes, a transformação aplicada e as saídas. Ela só será considerada reproduzida com fonte primária quando as entradas eleitorais materiais vierem diretamente do TSE ou de artefatos oficiais preservados, e não apenas de uma captura ou derivação feita por terceiro.

## Estado atual

A investigação já tem boa reprodutibilidade de código: cada fase possui um script próprio e os resultados derivados estão versionados.

Parte da cronologia fina de 04/10/2026, porém, depende de capturas contemporâneas independentes, principalmente ArvorCo/PNAD e vitoropereira/eleicoes2026. Essas fontes estão fixadas por commit e, quando disponível, SHA-256. Portanto as contas podem ser repetidas, mas essas fontes não são promovidas a fonte primária.

No registro de proveniência, as fases que dependem delas permanecem marcadas como PRIMARY-GAP até que a mesma análise seja refeita com o histórico primário equivalente.

Quando a fonte primária for obtida, a captura externa continuará preservada como controle independente.

## Arquivos de controle

- provenance/SOURCES.json: inventário das fontes, classe, commit/hash, estado e alvo de substituição primária.
- provenance/PHASES.json: ordem dos testes, scripts, entradas lógicas e saídas principais.
- replay_investigation.py: verificação e reexecução da sequência.
- docs/DIARIO_INVESTIGACAO.md: caderno cronológico.
- docs/ONE_PAGE_INVESTIGACAO.md: estado executivo.

## Comandos de replay

Ver a sequência e as fases que ainda têm lacuna primária:

    python replay_investigation.py --list

Auditar arquivos locais, hashes e lacunas:

    python replay_investigation.py --check

Simular a sequência sem executar:

    python replay_investigation.py --all --dry-run

Reexecutar uma fase:

    python replay_investigation.py --phase 4J

Reexecutar da Fase 3B em diante:

    python replay_investigation.py --from-phase 3B

Reexecutar toda a sequência:

    python replay_investigation.py --all

Um replay real grava data/forensics/analysis/replay_latest.json com commit do código, ambiente, comandos, fontes declaradas e hashes das saídas antes e depois.

## Arquitetura-alvo

### Camada 0 — RAW imutável

Todo arquivo original adquirido deve ser preservado sem alteração, com URL/origem, data e hora da aquisição, SHA-256, tamanho e identificadores do pleito/cargo/abrangência. Quando aplicável, também registrar hora gerada pelo TSE e hora capturada pelo coletor.

Nunca sobrescrever um bruto antigo com uma aquisição nova.

### Camada 1 — CANONICAL

Devem ser criados adaptadores que convertam fontes diferentes para esquemas internos estáveis, por exemplo: timeline nacional/UF, snapshot por UF, zona, município e seção/BU.

Os testes devem migrar gradualmente para consumir esses esquemas canônicos, e não URLs externas diretamente.

Essa camada é a chave para trocar captura externa por fonte primária sem mudar a matemática dos testes.

### Camada 2 — ANALYSIS

Os scripts de fase devem receber apenas dados canônicos e parâmetros explícitos. A mesma fase deverá poder rodar sobre um dataset canônico gerado de captura histórica e sobre outro gerado da fonte primária.

### Camada 3 — REPORT

One-page, diário e relatório detalhado são gerados a partir dos resultados das fases. Eles não servem de entrada aos testes.

## Regra para incorporar uma fonte primária

Quando uma fonte primária histórica for encontrada:

1. preservar o bruto novo e seu SHA-256;
2. adicionar a fonte ao registro SOURCES.json;
3. construir ou atualizar o adaptador para o mesmo esquema canônico;
4. não apagar o dataset derivado da captura externa;
5. rerodar a primeira fase afetada e todas as dependentes;
6. produzir um diff quantitativo resultado-antigo versus resultado-primário;
7. registrar no diário o que mudou, o que permaneceu idêntico e qualquer conclusão revisada;
8. somente então alterar o status da fase para replay primário concluído.

## Prioridades de recuperação primária

1. Histórico de versões EA20 do TSE entre aproximadamente 18:40 e 21:30 BRT, principalmente nacional e UF.
2. Versões municipais e zonais no entorno de 20:04 para decomposição geográfica fina.
3. Microdados oficiais TSE 2022 por zona e seção usados nos controles históricos.
4. Arquivos oficiais finais por cargo e UF para substituir produtos derivados de terceiros.
5. BU, RDV e logs de seções selecionadas quando um teste exigir granularidade de urna.

## Regra epistemológica

Uma captura independente pode demonstrar que um observador recebeu determinado conteúdo naquele momento. Ela não prova, sozinha, toda a história interna do sistema do TSE.

Uma fonte primária histórica fortalece a cadeia de custódia, mas ainda precisa ser validada por hash, consistência interna e reconciliação entre níveis.

A meta final é preservar os dois lados e obter, sempre que possível:

**fonte primária + captura independente + mesma conclusão reproduzida**.

Esse é o padrão desejado para o dossiê final.
