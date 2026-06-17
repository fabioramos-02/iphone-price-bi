"""Carregamento das fichas técnicas (specs) dos iPhones.

Responsabilidade única: ler/validar o JSON de specs (schema rico, chaveado por
nome do modelo) e devolvê-lo pronto para o frontend.
Não toca em preço/câmbio do catálogo — specs são dados estáticos separados.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

# Seções de primeiro nível esperadas em cada ficha (presença não obrigatória).
SECOES = (
    "preco", "sistema", "design", "avaliacao", "hardware",
    "tela", "camera", "video", "conectividade", "sensores", "bateria",
)


def carregar_specs(path: Path) -> dict:
    """Lê o JSON de specs e devolve {nome_modelo: ficha}.

    Resiliente: arquivo ausente/inválido -> {} com warning (cards seguem sem ficha).
    Aceita tanto `{ "iPhone 17": {...} }` quanto o formato bruto
    `{ "iPhone 17": { "produto": {...} } }` (desembrulha "produto").
    """
    if not path.exists():
        log.warning("Arquivo de specs não encontrado: %s", path)
        return {}
    try:
        bruto = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("Falha ao ler specs: %s", exc)
        return {}

    fichas: dict[str, dict] = {}
    for nome, ficha in bruto.items():
        if isinstance(ficha, dict) and isinstance(ficha.get("produto"), dict):
            ficha = ficha["produto"]  # desembrulha formato exportado
        if not isinstance(ficha, dict):
            log.warning("Ficha inválida ignorada: %r", nome)
            continue
        fichas[nome] = ficha
    log.info("Specs carregadas: %d modelo(s).", len(fichas))
    return fichas


def salvar_specs(fichas: dict, destino: Path) -> None:
    """Grava as fichas validadas em destino (ex: web/specs.json)."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(fichas, ensure_ascii=False, indent=2), encoding="utf-8"
    )
