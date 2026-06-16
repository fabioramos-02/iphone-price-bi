"""Geração de insights a partir do bloco de análise.

Responsabilidade única: traduzir números em mensagens acionáveis.
Distingue 'queda real' (USD caiu) de 'queda falsa' (só o câmbio caiu).
"""

from __future__ import annotations

from .models import Insight


def gerar_insights(analise: dict) -> list[dict]:
    """Recebe o dict de analisar() e devolve lista de insights serializados."""
    insights: list[Insight] = []
    for chave, g in analise.items():
        insights.append(_melhor_momento(chave, g))
        impacto = _impacto_dolar(chave, g)
        if impacto:
            insights.append(impacto)
        alerta = _alerta_queda(chave, g)
        if alerta:
            insights.append(alerta)
    return [i.to_dict() for i in insights]


def _melhor_momento(chave: str, g: dict) -> Insight:
    modelo = g["modelo_normalizado"]
    arm = g["armazenamento"]
    preco = g["menor_preco_brl_historico"]
    data = g["menor_preco_data"]
    return Insight(
        tipo="melhor_momento",
        chave_grupo=chave,
        mensagem=(
            f"{modelo} {arm}: menor preço histórico real foi "
            f"R$ {preco:,.2f} em {data}."
        ),
    )


def _impacto_dolar(chave: str, g: dict) -> Insight | None:
    v_brl = g.get("variacao_pct_brl")
    v_usd = g.get("variacao_pct_usd")
    if v_brl is None or v_usd is None:
        return None
    cambio = round(v_brl - v_usd, 2)  # parte da variação BRL não explicada pelo USD
    modelo = g["modelo_normalizado"]
    arm = g["armazenamento"]
    return Insight(
        tipo="impacto_dolar",
        chave_grupo=chave,
        mensagem=(
            f"{modelo} {arm}: preço em USD variou {v_usd:+.2f}% (produto) e "
            f"em BRL {v_brl:+.2f}%. Efeito do câmbio: {cambio:+.2f} p.p."
        ),
    )


def _alerta_queda(chave: str, g: dict) -> Insight | None:
    v_brl = g.get("variacao_pct_brl")
    v_usd = g.get("variacao_pct_usd")
    if v_brl is None or v_usd is None:
        return None

    modelo = g["modelo_normalizado"]
    arm = g["armazenamento"]

    # Queda real: o preço de fábrica (USD) caiu de verdade.
    if v_usd < -0.01:
        return Insight(
            tipo="queda_real",
            chave_grupo=chave,
            severidade="alerta",
            mensagem=(
                f"QUEDA REAL: {modelo} {arm} ficou {v_usd:+.2f}% mais barato em "
                f"USD. Boa janela de compra."
            ),
        )

    # Queda falsa: USD igual/maior, mas BRL caiu só por causa do câmbio.
    if v_brl < -0.01 and v_usd >= -0.01:
        return Insight(
            tipo="queda_falsa",
            chave_grupo=chave,
            severidade="alerta",
            mensagem=(
                f"QUEDA FALSA: {modelo} {arm} parece mais barato em BRL "
                f"({v_brl:+.2f}%), mas o preço em USD não caiu ({v_usd:+.2f}%). "
                f"É efeito do dólar, não do produto."
            ),
        )
    return None
