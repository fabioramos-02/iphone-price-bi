"""Parsing do texto bruto do WhatsApp em Cotacao + lista de Produto.

Responsabilidade única: transformar texto em estruturas de domínio.
Não calcula câmbio nem BRL (isso é do exchange.py / pipeline.py).
Resiliente: linhas truncadas ('…') ou malformadas são ignoradas com warning.
"""

from __future__ import annotations

import logging
import re

from .exchange import parse_historic
from .models import Cotacao, Produto
from .normalizer import (
    normalizar_armazenamento,
    normalizar_modelo,
    normalizar_tipo,
)

log = logging.getLogger(__name__)

FORNECEDOR_DEFAULT = "Shopping China"

# Cabeçalho de mensagem do WhatsApp: [10:09, 24/04/2026] Shopping China:
_HEADER = re.compile(
    r"\[\d{1,2}:\d{2},\s*(\d{1,2}/\d{1,2}/\d{2,4})\]\s*([^:]+):"
)

# Linha de produto. Resiliente ao 'BEU$' colado e ao espaço duplo.
# Captura: modelo livre + armazenamento + tipo opcional + preço + cores.
_PRODUTO = re.compile(
    r"IPHONE\s+(?P<modelo>.+?)\s+"
    r"(?P<arm>\d+\s*(?:GB|TB))\s*"
    r"(?P<tipo>BE|ESIM|HN)?\s*"
    r"U?\$?\s*(?P<preco>\d{1,3}(?:\.\d{3})*(?:,\d{2})?)"
    r"(?P<cores>.*)$",
    re.IGNORECASE,
)

# Tipo pode aparecer ANTES do armazenamento: "IPHONE 17 PRO BE 256GB U$..."
_TIPO_ANTES = re.compile(r"\b(BE|ESIM|HN)\b", re.IGNORECASE)

# Oferta inline: (OFERTA ORANGE U$1.549,00)
_OFERTA = re.compile(r"\(OFERTA[^)]*\)", re.IGNORECASE)

_CORES_VALIDAS = {
    "WHITE", "BLACK", "BLUE", "SILVER", "ORANGE", "PINK", "GOLD",
    "SAGE", "LAVANDER", "LAVENDER", "TEAL", "ULTRAMARINE",
}


def _br_para_iso(data_br: str) -> str:
    d, m, a = data_br.split("/")
    if len(a) == 2:
        a = "20" + a
    return f"{a}-{int(m):02d}-{int(d):02d}"


def _preco_para_float(bruto: str) -> float:
    return float(bruto.replace(".", "").replace(",", "."))


def parse_arquivo(texto: str) -> tuple[Cotacao | None, list[Produto]]:
    """Processa um arquivo de coleta inteiro (produtos + bloco de câmbio)."""
    blocos = _dividir_em_blocos(texto)
    if not blocos:
        log.warning("Nenhum cabeçalho de mensagem encontrado.")
        return None, []

    data_iso = blocos[0][0]
    fornecedor = blocos[0][1] or FORNECEDOR_DEFAULT

    produtos: list[Produto] = []
    historic = None
    pyg = None
    for _, _, corpo in blocos:
        h, p = parse_historic(corpo)
        if h is not None:
            historic = h
        if p is not None:
            pyg = p
        produtos.extend(_parse_produtos(corpo, data_iso, fornecedor))

    cotacao = Cotacao(
        data=data_iso,
        fornecedor=fornecedor,
        exchange_rate_brl_historic=historic,
        exchange_rate_pyg=pyg,
    )
    return cotacao, produtos


def _dividir_em_blocos(texto: str) -> list[tuple[str, str, str]]:
    """Devolve [(data_iso, fornecedor, corpo)] por mensagem do WhatsApp."""
    matches = list(_HEADER.finditer(texto))
    blocos: list[tuple[str, str, str]] = []
    for i, m in enumerate(matches):
        ini = m.end()
        fim = matches[i + 1].start() if i + 1 < len(matches) else len(texto)
        data_iso = _br_para_iso(m.group(1))
        fornecedor = m.group(2).strip()
        blocos.append((data_iso, fornecedor, texto[ini:fim]))
    return blocos


def _parse_produtos(corpo: str, data_iso: str, fornecedor: str) -> list[Produto]:
    produtos: list[Produto] = []
    for linha in corpo.splitlines():
        linha = linha.strip()
        if not linha.upper().startswith("IPHONE"):
            continue
        if linha.endswith("…") or linha.endswith("..."):
            log.info("Linha truncada ignorada: %r", linha)
            continue
        prod = _parse_linha(linha, data_iso, fornecedor)
        if prod:
            produtos.append(prod)
        else:
            log.warning("Linha de produto não reconhecida: %r", linha)
    return produtos


def _parse_linha(linha: str, data_iso: str, fornecedor: str) -> Produto | None:
    oferta = _OFERTA.search(linha)
    observacoes = oferta.group(0).strip("()") if oferta else ""
    limpa = _OFERTA.sub("", linha).strip()

    m = _PRODUTO.search(limpa)
    if not m:
        return None

    modelo_bruto = m.group("modelo")
    tipo = normalizar_tipo(m.group("tipo"))

    # Tipo pode estar embutido no 'modelo' (ex: 'PRO BE'): extrai e remove.
    if not tipo:
        mt = _TIPO_ANTES.search(modelo_bruto)
        if mt:
            tipo = normalizar_tipo(mt.group(1))
            modelo_bruto = _TIPO_ANTES.sub("", modelo_bruto).strip()

    linha_canon, versao, modelo_norm = normalizar_modelo(modelo_bruto)

    return Produto(
        data=data_iso,
        fornecedor=fornecedor,
        linha=linha_canon,
        versao=versao,
        modelo_normalizado=modelo_norm,
        armazenamento=normalizar_armazenamento(m.group("arm")),
        tipo=tipo,
        preco_usd=_preco_para_float(m.group("preco")),
        cores=_extrair_cores(m.group("cores")),
        observacoes=observacoes,
    )


def _extrair_cores(bruto: str) -> list[str]:
    cores: list[str] = []
    for token in re.split(r"\s+", bruto.strip().upper()):
        if token in _CORES_VALIDAS and token not in cores:
            cores.append(token.capitalize())
    return cores
