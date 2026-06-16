# 📱 BI Catálogo de Preços de iPhone

Pipeline em **Python** que transforma cotações brutas de iPhone recebidas por WhatsApp
(fornecedor *Shopping China* — Pedro Juan Caballero/PY) em um **catálogo estruturado**
com análise de preços, e um **dashboard web** para visualização.

> **Regra de ouro:** comparações de preço usam sempre o **BRL histórico** (câmbio da
> data da cotação). O câmbio atual entra só como **simulação** — nunca para comparar
> tendência. Isso separa *queda real* de produto de *queda falsa* causada só pelo dólar.

## ✨ Recursos

- **Extração estruturada** de texto bruto → JSON (`cotacoes`, `produtos`, `analise`,
  `insights`, `meta`).
- **Parser resiliente**: lida com `BEU$` colado, tipo antes do armazenamento, ofertas
  inline e ignora linhas truncadas sem quebrar.
- **Câmbio duplo**: histórico (do texto) + atual (API AwesomeAPI, opcional).
- **Análise**: menor/maior preço, variação %, tendência — tudo na base histórica.
- **Insights**: melhor momento de compra, impacto do dólar e alertas *queda real* vs
  *queda falsa*.
- **Dashboard** estático (HTML/CSS/JS + Chart.js), pronto para deploy na Vercel.

## 🚀 Uso

```bash
pip install -r requirements.txt

# Gera data/processed/catalog.json e web/catalog.json
python scripts/build_catalog.py            # com câmbio atual (rede)
python scripts/build_catalog.py --no-api   # offline; preco_brl_atual = null

# Visualizar o dashboard
cd web && python -m http.server 8000       # http://localhost:8000
```

Coloque novas coletas em `data/raw/<data>.txt` (copie o texto direto do WhatsApp) e
rode o build de novo.

## 🗂 Estrutura

```
src/        core ETL (1 responsabilidade por módulo, <250 linhas)
scripts/    CLI build_catalog.py
data/raw/   coletas brutas (.txt)
web/        dashboard estático (deploy Vercel)
images/     renders dos iPhones
```

Detalhes de arquitetura e regras em [CLAUDE.md](CLAUDE.md).

## ☁️ Deploy (Vercel)

O `vercel.json` serve a pasta `web/` como site estático. Basta importar o repositório
na Vercel — sem build step necessário (o `catalog.json` e as imagens já são versionados
em `web/`).

## 📦 Schema da saída

```json
{
  "cotacoes": [ { "data", "exchange_rate_brl_historic", "exchange_rate_brl_current", "exchange_rate_pyg" } ],
  "produtos": [ { "modelo_normalizado", "armazenamento", "tipo", "preco_usd", "cores", "preco_brl_historico", "preco_brl_atual" } ],
  "analise":  { "<modelo|arm|tipo>": { "variacao_pct_brl", "tendencia", "menor_preco_brl_historico" } },
  "insights": [ { "tipo": "melhor_momento|impacto_dolar|queda_real|queda_falsa", "mensagem" } ],
  "meta":     { "exchange_strategy": "historical_priority" }
}
```
