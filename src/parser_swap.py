"""Parser de planilha de estoque 'swap' (semi-novos importados em USD).

Responsabilidade única: ler listas no formato 'CELULAR [SWAP] IPHONE <modelo>
<arm> <cores/flags> <preço>' (cor ANTES do preço, sem símbolo U$), em dólar.
Condição: linha com 'SWAP' -> semi-novo; sem -> lacrado.
O câmbio histórico vem de uma linha 'Dólar x Real' no próprio texto.
"""

from __future__ import annotations

import logging
import re

from .exchange import parse_historic
from .models import Cotacao, Produto
from .normalizer import normalizar_armazenamento, normalizar_modelo
from .parser import _dividir_em_blocos, normalizar_fornecedor

log = logging.getLogger(__name__)

_SWAP_LINHA = re.compile(
    r"^\s*#?\s*CELULAR\s+(?P<swap>SWAP\s+)?IPHONE\s+"
    r"(?P<modelo>\d{2}e?(?:\s+(?:PRO\s+MAX|PRO|PLUS|AIR|MAX))?)\s+"
    r"(?P<arm>\d+\s*(?:GB|TB)?)\s+"
    r"(?P<resto>.+?)\s+"
    r"(?P<preco>\d{1,3}(?:\.\d{3})*,\d{2})\s*$",
    re.IGNORECASE,
)

# Cores compostas primeiro (match guloso), depois simples.
_CORES = [
    "ALPINE GREEN", "SIERRA BLUE", "COSMIC ORANGE", "DEEP BLUE",
    "MIDNIGHT", "STARLIGHT", "GRAPHITE", "ULTRAMARINE", "DESERT", "NATURAL",
    "SILVER", "ORANGE", "PURPLE", "GREEN", "BLUE", "BLACK", "WHITE",
    "PINK", "GOLD", "SAGE", "TEAL", "LAVANDER",
]


def parse_swap(texto: str) -> tuple[Cotacao | None, list[Produto]]:
    """Processa a planilha swap. Devolve Cotacao (câmbio do texto) + Produtos USD."""
    blocos = _dividir_em_blocos(texto)
    if blocos:
        data_iso = blocos[0][0]
        sender = blocos[0][1]
    else:  # sem cabeçalho: usa data/fornecedor padrão
        data_iso = ""
        sender = "Swap"

    historic, _ = parse_historic(texto)
    fornecedor = normalizar_fornecedor(sender) or "Swap"

    produtos: list[Produto] = []
    for linha in texto.splitlines():
        prod = _parse_linha(linha.strip(), data_iso, fornecedor)
        if prod:
            produtos.append(prod)

    cotacao = Cotacao(
        data=data_iso,
        fornecedor=fornecedor,
        exchange_rate_brl_historic=historic,
    )
    return cotacao, produtos


def _parse_linha(linha: str, data_iso: str, fornecedor: str) -> Produto | None:
    if "iphone" not in linha.lower() or "xiaomi" in linha.lower():
        return None
    m = _SWAP_LINHA.search(linha)
    if not m:
        return None

    resto = m.group("resto").upper()
    condicao = "semi-novo" if m.group("swap") else "lacrado"
    tipo = "ESIM" if "ESIM" in resto else ("BE" if "ANATEL" in resto else "")

    flags = []
    if "AS IS" in resto:
        flags.append("as is")
    if "ANATEL" in resto:
        flags.append("Anatel")
    cod = re.search(r"A\d{4}", resto)
    if cod:
        flags.append(cod.group(0))

    linha_canon, versao, modelo_norm = normalizar_modelo("iphone " + m.group("modelo"))
    return Produto(
        data=data_iso,
        fornecedor=fornecedor,
        linha=linha_canon,
        versao=versao,
        modelo_normalizado=modelo_norm,
        armazenamento=normalizar_armazenamento(m.group("arm")),
        tipo=tipo,
        condicao=condicao,
        moeda_base="USD",
        preco_usd=float(m.group("preco").replace(".", "").replace(",", ".")),
        cores=_extrair_cores(resto),
        observacoes=" · ".join(flags),
    )


def _extrair_cores(resto: str) -> list[str]:
    achadas: list[str] = []
    restante = " " + resto + " "
    for cor in _CORES:
        if f" {cor} " in restante:
            achadas.append(cor.title())
            restante = restante.replace(f" {cor} ", " ", 1)
    return achadas
