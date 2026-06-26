"""Parser de listas em USD com preço no FIM da linha (sem símbolo U$).

Cobre dois sub-formatos:
- Planilha 'CELULAR [SWAP] IPHONE <modelo> <arm> <cores> <preço>'.
- Lista conversacional 'iphone <modelo> <arm> <cor> - <preço> [dolares]'.

Responsabilidade única: extrair Produtos em dólar desses formatos.
Condição: linha/lista com 'SWAP' ou 'SEMI' -> semi-novo; senão -> lacrado.
Câmbio histórico vem de uma linha 'Dólar x Real' no próprio texto.
"""

from __future__ import annotations

import logging
import re

from .exchange import parse_historic
from .models import Cotacao, Produto
from .normalizer import normalizar_armazenamento, normalizar_modelo
from .parser import _dividir_em_blocos, normalizar_fornecedor

log = logging.getLogger(__name__)

# Corrige erros de digitação comuns do nome 'iphone'.
_TYPOS = re.compile(r"\b(ihone|iphne|ipone|iphonne|ifone|phone)\b", re.IGNORECASE)

_LINHA = re.compile(
    r"^\s*#?\s*(?:CELULAR\s+)?(?P<swap>SWAP\s+)?iphone\s+"
    r"(?P<modelo>\d{2}e?(?:\s+(?:pro\s+max|pro|plus|air|max))?)"
    r"(?:\s+(?P<arm>\d+\s*(?:gb|tb)?))?"
    r"(?P<resto>.*?)"
    r"\s*[-–]?\s*(?P<preco>\d[\d.]*(?:,\d{2})?)\s*(?:dolares|dólares|usd)?\s*$",
    re.IGNORECASE,
)

# Cores compostas primeiro (match guloso), depois simples. PT + EN.
_CORES = [
    "ALPINE GREEN", "SIERRA BLUE", "COSMIC ORANGE", "DEEP BLUE",
    "MIDNIGHT", "STARLIGHT", "GRAPHITE", "ULTRAMARINE", "DESERT", "NATURAL",
    "SILVER", "ORANGE", "PURPLE", "GREEN", "BLUE", "BLACK", "WHITE",
    "PINK", "GOLD", "SAGE", "TEAL", "LAVANDER",
    "PRETO", "BRANCO", "AZUL", "PRATA", "LARANJA", "VERDE", "ROSA", "DOURADO",
]
_COR_PT = {
    "PRETO": "Black", "BRANCO": "White", "AZUL": "Blue", "PRATA": "Silver",
    "LARANJA": "Orange", "VERDE": "Green", "ROSA": "Pink", "DOURADO": "Gold",
}


def _preco(bruto: str) -> float:
    b = bruto.strip()
    if "," in b:  # formato BR com centavos: 1.120,00
        return float(b.replace(".", "").replace(",", "."))
    return float(b.replace(".", ""))  # inteiro em milhar: 1.725 / 1725


def parse_swap(texto: str) -> tuple[Cotacao | None, list[Produto]]:
    """Processa a lista. Devolve Cotacao (câmbio do texto) + Produtos USD."""
    texto = _TYPOS.sub("iphone", texto)
    blocos = _dividir_em_blocos(texto)
    if blocos:
        data_iso, sender = blocos[0][0], blocos[0][1]
    else:
        data_iso, sender = "", "Outlet"

    historic, _ = parse_historic(texto)
    fornecedor = normalizar_fornecedor(sender) or "Outlet"
    semi_global = bool(re.search(r"semi[\s-]?novo", texto, re.IGNORECASE))

    produtos: list[Produto] = []
    for linha in texto.splitlines():
        prod = _parse_linha(linha.strip(), data_iso, fornecedor, semi_global)
        if prod:
            produtos.append(prod)

    cotacao = Cotacao(
        data=data_iso, fornecedor=fornecedor, exchange_rate_brl_historic=historic
    )
    return cotacao, produtos


def _parse_linha(
    linha: str, data_iso: str, fornecedor: str, semi_global: bool
) -> Produto | None:
    if "iphone" not in linha.lower() or "xiaomi" in linha.lower():
        return None
    m = _LINHA.search(linha)
    if not m:
        return None

    resto = m.group("resto").upper()
    condicao = "semi-novo" if (m.group("swap") or semi_global) else "lacrado"
    tipo = "ESIM" if "ESIM" in resto else ("BE" if "ANATEL" in resto else "")

    flags = []
    if "AS IS" in resto:
        flags.append("as is")
    if "ANATEL" in resto:
        flags.append("Anatel")
    cod = re.search(r"A\d{4}", resto)
    if cod:
        flags.append(cod.group(0))

    arm = m.group("arm")
    linha_canon, versao, modelo_norm = normalizar_modelo("iphone " + m.group("modelo"))
    return Produto(
        data=data_iso,
        fornecedor=fornecedor,
        linha=linha_canon,
        versao=versao,
        modelo_normalizado=modelo_norm,
        armazenamento=normalizar_armazenamento(arm) if arm else "",
        tipo=tipo,
        condicao=condicao,
        moeda_base="USD",
        preco_usd=_preco(m.group("preco")),
        cores=_extrair_cores(resto),
        observacoes=" · ".join(flags),
    )


def _extrair_cores(resto: str) -> list[str]:
    achadas: list[str] = []
    restante = " " + resto + " "
    for cor in _CORES:
        if f" {cor} " in restante:
            achadas.append(_COR_PT.get(cor, cor.title()))
            restante = restante.replace(f" {cor} ", " ", 1)
    return achadas
