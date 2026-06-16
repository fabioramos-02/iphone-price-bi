"""Carregamento das fichas técnicas (specs) dos iPhones.

Responsabilidade única: ler/validar o JSON de specs e expô-lo por slug do modelo.
Não toca em preço nem em câmbio — specs são dados estáticos, separados do catálogo.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

# Campos esperados por modelo (presença não é obrigatória; faltante = ausente).
CAMPOS = (
    "tela", "chip", "ram", "bateria", "cameras",
    "dimensoes", "peso", "so", "conectividade", "ano", "fonte",
)


def slug(modelo: str) -> str:
    """Mesma convenção de web/app.js: 'iPhone 17 Pro Max' -> 'iphone-17-pro-max'."""
    base = modelo.replace("iPhone", "").replace("iphone", "").strip().lower()
    return "iphone-" + "-".join(base.split())


def carregar_specs(path: Path) -> dict:
    """Lê o JSON de specs e devolve {slug: {campos...}}.

    Resiliente: arquivo ausente/ inválido -> {} com warning (cards seguem sem ficha).
    """
    if not path.exists():
        log.warning("Arquivo de specs não encontrado: %s", path)
        return {}
    try:
        bruto = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("Falha ao ler specs: %s", exc)
        return {}

    indexado: dict[str, dict] = {}
    for modelo, ficha in bruto.items():
        if not isinstance(ficha, dict):
            log.warning("Ficha inválida ignorada: %r", modelo)
            continue
        indexado[slug(modelo)] = {
            "modelo": modelo,
            **{c: ficha.get(c) for c in CAMPOS},
        }
    return indexado
