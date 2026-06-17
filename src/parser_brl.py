"""Parser de cotações já em reais (R$), em formato de lista.

Responsabilidade única: ler coletas BRL-nativas (ex: Skyblue, Compushop curado)
e produzir Cotacao (sem câmbio) + Produtos com preço já em BRL.
Seções de texto (LACRADOS / SEMI NOVO / SWAP) definem a `condicao` corrente.
Resiliente: linhas sem preço válido (R$ vazio, ❌) são ignoradas.
"""

from __future__ import annotations

import logging
import re

from .models import Cotacao, Produto
from .normalizer import (
    normalizar_armazenamento,
    normalizar_condicao,
    normalizar_fornecedor,
    normalizar_modelo,
)
from .parser import _br_para_iso, _dividir_em_blocos  # reuso do split de blocos

log = logging.getLogger(__name__)

# Linha de produto BRL: modelo + armazenamento + (cor)? -> R$ preço.
# Tolera ausência do prefixo "iPhone", seta de "->", e cor entre parênteses.
_BRL_PRODUTO = re.compile(
    r"(?:iphone\s*)?"
    r"(?P<modelo>\d{2}e?(?:\s+(?:pro\s+max|pro|plus|air|max))?)\s+"
    r"(?P<arm>\d+\s*(?:gb|tb)?)\s+"
    r".*?R\$\s*"
    r"(?P<preco>\d{1,3}(?:\.\d{3})*(?:,\d{2})?)",
    re.IGNORECASE,
)

# Marcadores de seção que trocam a condição corrente.
_SECAO = re.compile(r"(semi[\s-]?novo|swap|recondicionado|usado|lacrad)", re.IGNORECASE)

_COR = re.compile(r"\(([^)]*)\)")


def _preco_brl(bruto: str) -> float:
    return float(bruto.replace(".", "").replace(",", "."))


def parse_brl(texto: str) -> tuple[Cotacao | None, list[Produto]]:
    """Processa uma coleta em reais. Câmbio histórico fica None (preço já é BRL)."""
    blocos = _dividir_em_blocos(texto)
    if not blocos:
        log.warning("BRL: nenhum cabeçalho de mensagem encontrado.")
        return None, []

    data_iso = blocos[0][0]
    produtos: list[Produto] = []
    fornecedor = ""
    for _, sender, corpo in blocos:
        prods = _parse_corpo(corpo, data_iso, normalizar_fornecedor(sender))
        if prods and not fornecedor:
            fornecedor = normalizar_fornecedor(sender)
        produtos.extend(prods)

    cotacao = Cotacao(
        data=data_iso,
        fornecedor=fornecedor or "Fornecedor BRL",
        exchange_rate_brl_historic=None,
    )
    return cotacao, produtos


def _parse_corpo(corpo: str, data_iso: str, fornecedor: str) -> list[Produto]:
    produtos: list[Produto] = []
    condicao = "lacrado"  # padrão até um marcador de seção dizer o contrário
    for linha in corpo.splitlines():
        linha = linha.strip()
        if not linha:
            continue
        secao = _SECAO.search(linha)
        # Linha que é só um cabeçalho de seção (sem preço) troca a condição.
        if secao and "R$" not in linha:
            condicao = normalizar_condicao(secao.group(1))
            continue
        prod = _parse_linha(linha, data_iso, fornecedor, condicao)
        if prod:
            produtos.append(prod)
    return produtos


def _parse_linha(
    linha: str, data_iso: str, fornecedor: str, condicao: str
) -> Produto | None:
    if "iphone" not in linha.lower() and not re.match(r"\s*\d{2}\b", linha):
        return None
    m = _BRL_PRODUTO.search(linha)
    if not m:
        return None

    linha_canon, versao, modelo_norm = normalizar_modelo("iphone " + m.group("modelo"))
    cor_match = _COR.search(linha)
    cores = _extrair_cores(cor_match.group(1)) if cor_match else []
    preco = _preco_brl(m.group("preco"))

    return Produto(
        data=data_iso,
        fornecedor=fornecedor,
        linha=linha_canon,
        versao=versao,
        modelo_normalizado=modelo_norm,
        armazenamento=normalizar_armazenamento(m.group("arm")),
        tipo="",
        condicao=condicao,
        moeda_base="BRL",
        preco_usd=None,
        preco_brl_historico=preco,
        cores=cores,
    )


def _extrair_cores(bruto: str) -> list[str]:
    mapa = {
        "LARANJA": "Orange", "AZUL": "Blue", "SILVER": "Silver", "PRETO": "Black",
        "BLACK": "Black", "BRANCO": "White", "WHITE": "White", "VERDE": "Green",
        "ROSA": "Pink", "DESERT": "Desert", "NATURAL": "Natural",
    }
    cores: list[str] = []
    for token in re.split(r"[\s,\-]+", bruto.strip().upper()):
        cor = mapa.get(token)
        if cor and cor not in cores:
            cores.append(cor)
    return cores
