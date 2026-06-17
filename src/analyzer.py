"""Análise de preços por modelo ao longo do tempo.

Responsabilidade única: agrupar produtos e calcular estatísticas.
Comparações usam SEMPRE preco_brl_historico (base confiável) — nunca o atual.
"""

from __future__ import annotations

from collections import defaultdict

from .models import Produto


def _serie_historica(produtos: list[Produto]) -> list[Produto]:
    """Ordena por data e mantém só itens com BRL histórico calculado."""
    validos = [p for p in produtos if p.preco_brl_historico is not None]
    return sorted(validos, key=lambda p: p.data)


def analisar(produtos: list[Produto]) -> dict:
    """Devolve o bloco 'analise' do catálogo, agrupado por chave de produto."""
    grupos: dict[str, list[Produto]] = defaultdict(list)
    for p in produtos:
        grupos[p.chave_grupo].append(p)

    resultado: dict[str, dict] = {}
    for chave, itens in grupos.items():
        serie = _serie_historica(itens)
        if not serie:
            continue
        resultado[chave] = _analisar_grupo(serie)
    return resultado


def ranking_datas(produtos: list[Produto]) -> dict:
    """Ranking de datas: qual coleta concentrou os menores preços históricos.

    Para cada grupo de produto, identifica em que data o BRL histórico foi mínimo
    e contabiliza "vitórias" por data. Também calcula a cesta média (BRL) por data.
    Devolve {melhor_dia, por_data: {data: {n_menores, cesta_media, n_itens}}}.
    """
    grupos: dict[str, list[Produto]] = defaultdict(list)
    for p in produtos:
        grupos[p.chave_grupo].append(p)

    por_data: dict[str, dict] = {}
    for chave, itens in grupos.items():
        serie = _serie_historica(itens)
        if not serie:
            continue
        menor = min(serie, key=lambda p: p.preco_brl_historico)
        for p in serie:
            slot = por_data.setdefault(
                p.data, {"n_menores": 0, "_soma": 0.0, "n_itens": 0}
            )
            slot["_soma"] += p.preco_brl_historico
            slot["n_itens"] += 1
        por_data[menor.data]["n_menores"] += 1

    for data, slot in por_data.items():
        slot["cesta_media"] = round(slot.pop("_soma") / slot["n_itens"], 2)

    melhor_dia = None
    if por_data:
        melhor_dia = max(
            por_data,
            key=lambda d: (por_data[d]["n_menores"], -por_data[d]["cesta_media"]),
        )
    return {"melhor_dia": melhor_dia, "por_data": por_data}


def _analisar_grupo(serie: list[Produto]) -> dict:
    precos_brl = [p.preco_brl_historico for p in serie]
    precos_usd = [p.preco_usd for p in serie]

    menor = min(serie, key=lambda p: p.preco_brl_historico)
    maior = max(serie, key=lambda p: p.preco_brl_historico)

    variacao_pct = None
    variacao_usd_pct = None
    if len(serie) >= 2:
        primeiro, ultimo = serie[0], serie[-1]
        variacao_pct = _pct(primeiro.preco_brl_historico, ultimo.preco_brl_historico)
        if primeiro.preco_usd is not None and ultimo.preco_usd is not None:
            variacao_usd_pct = _pct(primeiro.preco_usd, ultimo.preco_usd)

    return {
        "modelo_normalizado": serie[0].modelo_normalizado,
        "armazenamento": serie[0].armazenamento,
        "condicao": serie[0].condicao,
        "tipo": serie[0].tipo,
        "n_observacoes": len(serie),
        "fornecedores": sorted({p.fornecedor for p in serie}),
        "datas": [p.data for p in serie],
        "precos_brl_historico": precos_brl,
        "precos_usd": precos_usd,
        "menor_preco_brl_historico": menor.preco_brl_historico,
        "menor_preco_data": menor.data,
        "menor_preco_fornecedor": menor.fornecedor,
        "maior_preco_brl_historico": maior.preco_brl_historico,
        "maior_preco_data": maior.data,
        "variacao_pct_brl": variacao_pct,
        "variacao_pct_usd": variacao_usd_pct,
        "tendencia": _tendencia(precos_brl),
    }


def _pct(inicial: float, final: float) -> float | None:
    if not inicial:
        return None
    return round((final - inicial) / inicial * 100, 2)


def _tendencia(precos: list[float]) -> str:
    if len(precos) < 2:
        return "estavel"
    delta = precos[-1] - precos[0]
    limiar = abs(precos[0]) * 0.01  # 1% de tolerância
    if delta > limiar:
        return "alta"
    if delta < -limiar:
        return "baixa"
    return "estavel"
