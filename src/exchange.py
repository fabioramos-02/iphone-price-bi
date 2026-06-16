"""Câmbio: histórico (extraído do texto) e atual (API externa).

Responsabilidade única: fornecer taxas USD->BRL/PYG.
Regra crítica do domínio:
  - histórico SEMPRE vem do próprio texto da cotação;
  - atual SEMPRE vem da API (ou None em falha) — nunca inventado.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

log = logging.getLogger(__name__)

_API_URL = "https://economia.awesomeapi.com.br/last/USD-BRL"
_TIMEOUT = 6  # segundos

# "Dólar x Real 🇧🇷 5,18"  -> 5.18
_BRL = re.compile(r"Real[^\d]*(\d+[.,]\d+)", re.IGNORECASE)
# "Dólar x Guaranís 🇵🇾 6.650" / "6400" -> 6650.0
_PYG = re.compile(r"Guaran[íi]s[^\d]*([\d.]+)", re.IGNORECASE)


def parse_historic(texto: str) -> tuple[Optional[float], Optional[float]]:
    """Extrai (brl, pyg) do bloco de câmbio. Campos ausentes viram None."""
    brl = None
    pyg = None

    mb = _BRL.search(texto)
    if mb:
        brl = float(mb.group(1).replace(".", "").replace(",", "."))

    mp = _PYG.search(texto)
    if mp:
        # PYG usa '.' como separador de milhar: 6.650 -> 6650
        pyg = float(mp.group(1).replace(".", ""))

    return brl, pyg


def fetch_current_brl() -> Optional[float]:
    """Busca a cotação USD->BRL atual via AwesomeAPI.

    Retorna float ou None (sem rede / erro / parsing). Nunca lança.
    """
    try:
        import requests  # import tardio: core de parsing não depende de rede
    except ImportError:
        log.warning("requests não instalado; câmbio atual indisponível.")
        return None

    try:
        resp = requests.get(_API_URL, timeout=_TIMEOUT)
        resp.raise_for_status()
        dados = resp.json()
        bid = dados["USDBRL"]["bid"]
        return float(bid)
    except Exception as exc:  # resiliente por design
        log.warning("Falha ao buscar câmbio atual: %s", exc)
        return None
