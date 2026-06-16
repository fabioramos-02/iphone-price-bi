"""Orquestração do ETL: raw/*.txt -> catalog.json.

Responsabilidade única: encadear parser -> exchange -> analyzer -> insights
e montar o documento final no schema da spec.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .analyzer import analisar
from .exchange import fetch_current_brl
from .insights import gerar_insights
from .models import Cotacao, Produto
from .parser import parse_arquivo

log = logging.getLogger(__name__)

META = {"exchange_strategy": "historical_priority"}


def construir_catalogo(raw_dir: Path, usar_api: bool = True) -> dict:
    """Lê todos os .txt de raw_dir e devolve o catálogo completo."""
    cotacoes: list[Cotacao] = []
    produtos: list[Produto] = []

    for arquivo in sorted(raw_dir.glob("*.txt")):
        texto = arquivo.read_text(encoding="utf-8")
        cotacao, prods = parse_arquivo(texto)
        if cotacao is None:
            log.warning("Arquivo sem cabeçalho válido: %s", arquivo.name)
            continue
        cotacoes.append(cotacao)
        produtos.extend(prods)
        log.info("%s: %d produtos.", arquivo.name, len(prods))

    cambio_atual = fetch_current_brl() if usar_api else None
    _aplicar_cambio(cotacoes, produtos, cambio_atual)

    analise = analisar(produtos)
    insights = gerar_insights(analise)

    return {
        "cotacoes": [c.to_dict() for c in cotacoes],
        "produtos": [p.to_dict() for p in produtos],
        "analise": analise,
        "insights": insights,
        "meta": {**META, "exchange_rate_brl_current": cambio_atual},
    }


def _aplicar_cambio(
    cotacoes: list[Cotacao],
    produtos: list[Produto],
    cambio_atual: float | None,
) -> None:
    """Preenche BRL histórico (por data) e BRL atual (global) nos produtos."""
    hist_por_data = {
        c.data: c.exchange_rate_brl_historic for c in cotacoes
    }
    for c in cotacoes:
        c.exchange_rate_brl_current = cambio_atual

    for p in produtos:
        taxa_hist = hist_por_data.get(p.data)
        if taxa_hist is not None:
            p.preco_brl_historico = round(p.preco_usd * taxa_hist, 2)
        if cambio_atual is not None:
            p.preco_brl_atual = round(p.preco_usd * cambio_atual, 2)


def salvar(catalogo: dict, *destinos: Path) -> None:
    """Grava o catálogo em um ou mais caminhos (ex: data/processed e web/)."""
    payload = json.dumps(catalogo, ensure_ascii=False, indent=2)
    for destino in destinos:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(payload, encoding="utf-8")
        log.info("Catálogo salvo em %s", destino)
