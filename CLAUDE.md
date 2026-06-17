# CLAUDE.md — BI Catálogo de Preços de iPhone

Contexto para agentes de IA que trabalharem neste repositório.

## O que é

Pipeline em Python que lê **textos brutos de cotações de iPhone** recebidos por
WhatsApp (fornecedor *Shopping China*, filial Pedro Juan Caballero/PY), extrai,
normaliza e analisa os dados, gerando um `catalog.json` consumido por um dashboard
web estático (deploy Vercel).

## Multi-fornecedor e moeda

Há fornecedores em **USD** (import — Shopping China; `parser.py`) e em **BRL** (preço já
em real — Skyblue/Compushop; `parser_brl.py`). `parse_arquivo` faz o dispatch por moeda
(`U$` → USD, `R$` → BRL). Produtos BRL têm `preco_usd=null`, `moeda_base="BRL"` e o preço
já entra como `preco_brl_historico` (atual = histórico, sem câmbio).

`condicao` ∈ `lacrado | semi-novo | cpo` (swap/recondicionado → semi-novo; CPO à parte).
A **chave de comparação** é `modelo|armazenamento|condicao` — compara o mesmo aparelho
**entre fornecedores**, nunca lacrado com usado. O dashboard filtra por condição e mostra
`menor_preco_fornecedor` (quem está mais barato).

## Regra crítica de domínio (NÃO violar)

Comparações de preço usam **SEMPRE** `preco_brl_historico` — o preço em BRL calculado
com o câmbio USD→BRL **da própria data da cotação** (extraído do texto). Nunca usar o
câmbio atual para comparar tendência.

- `exchange_rate_brl_historic`: vem do texto. É a base confiável.
- `exchange_rate_brl_current`: vem da API (AwesomeAPI) ou `null`. É só **simulação**.
- `preco_brl_atual`: só preenchido se houver câmbio atual; caso contrário `null`.
- Distinguir **queda real** (preço USD caiu) de **queda falsa** (USD igual, BRL caiu
  só porque o dólar caiu). Nunca inventar dados.

`meta.exchange_strategy = "historical_priority"`. O **melhor dia de compra** (bloco
`ranking`) e o "menor preço histórico" por modelo derivam só do BRL histórico.

## Arquitetura (responsabilidade única por módulo, máx. 250 linhas)

```
src/
  models.py      dataclasses (Cotacao, Produto, Insight) + serialização
  parser.py      texto bruto -> Cotacao + Produtos (regex resiliente)
  exchange.py    câmbio histórico (texto) + atual (API)
  normalizer.py  nomes -> linha/versão/modelo; tipo BE/ESIM/HN; armazenamento
  analyzer.py    agrupa por modelo; min/max, variação %, tendência; ranking_datas
  insights.py    melhor momento, impacto do dólar, alertas real vs falsa, melhor dia
  specs.py       carrega/valida fichas técnicas (data/specs) por slug do modelo
  pipeline.py    orquestra raw/*.txt -> catalog.json (inclui bloco ranking)
scripts/
  build_catalog.py   CLI; copia images/ -> web/images/ e specs -> web/specs.json
web/             dashboard estático (index.html, styles.css, app.js, catalog.json, specs.json)
data/raw/        coletas brutas (.txt, 1 por data)
data/processed/  catalog.json gerado
data/specs/      iphone-specs.json (ficha técnica curada, chaveada por modelo)
images/          renders dos iPhones (PNG por modelo, ex: iphone-17-pro-max.png)
```

Bloco `ranking` (no catálogo): `{melhor_dia, por_data: {data: {n_menores, cesta_media}}}`
— qual coleta concentrou os menores preços históricos.

As specs ficam **separadas** do preço (`data/specs/iphone-specs.json` → `web/specs.json`,
via `specs.carregar_specs`/`salvar_specs`); o frontend junta por **nome do modelo**.
Schema rico chaveado por nome, com seções `preco/sistema/design/avaliacao/hardware/tela/
camera/video/conectividade/sensores/bateria` (origem: export do tudocelular que o usuário
envia; campo desconhecido = `null`, nunca inventar). O card usa `specs.preco.melhor_preco`
(varejo BR) para mostrar a **economia vs varejo** do preço importado — sem misturar com a
regra do BRL histórico.

Fluxo: `parser -> normalizer/exchange -> analyzer -> insights -> pipeline`.

## Como rodar

```bash
pip install -r requirements.txt
python scripts/build_catalog.py            # com câmbio atual (rede)
python scripts/build_catalog.py --no-api   # offline; preco_brl_atual = null
```

Visualizar o dashboard local:

```bash
cd web && python -m http.server 8000   # http://localhost:8000
```

## Convenções

- Resiliência primeiro: linha truncada (`…`), preço malformado ou modelo desconhecido
  é ignorado com `log.warning`, nunca quebra o pipeline nem inventa valor.
- O core de parsing usa só stdlib. `requests` aparece apenas em `exchange.py`
  (import tardio), então o pipeline roda offline com `--no-api`.
- Imagens seguem a convenção de nome `iphone-<modelo-em-kebab>.png`; o slug é derivado
  de `modelo_normalizado` em `web/app.js` (`slug()`).
- Schema da saída: `{ cotacoes, produtos, analise, insights, meta }`.

## Formato do texto de entrada (exemplo)

```
[10:09, 24/04/2026] Shopping China: ...
IPHONE 17 PRO MAX 256GB BEU$1.520,00 BLUE SILVER     <- note 'BEU$' colado
IPHONE 17 PRO BE 256GB U$1.290,00 BLUE               <- tipo antes do armazen.
👉(OFERTA ORANGE U$1.549,00)                          <- observação inline
[10:09, 24/04/2026] Shopping China: 🇧🇷 Dólar x Real 5,18 ...
```
