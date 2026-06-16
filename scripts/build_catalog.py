"""CLI: roda o pipeline sobre data/raw/ e grava o catálogo.

Uso:
    python scripts/build_catalog.py [--no-api]

--no-api: não busca câmbio atual na internet (preco_brl_atual fica null).
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from pathlib import Path

# Permite rodar como script direto (sem instalar o pacote).
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.pipeline import construir_catalogo, salvar  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera o catálogo BI de iPhones.")
    parser.add_argument(
        "--no-api",
        action="store_true",
        help="Não consultar a API de câmbio atual.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    raw_dir = ROOT / "data" / "raw"
    if not raw_dir.exists():
        print(f"Diretório de dados não encontrado: {raw_dir}", file=sys.stderr)
        return 1

    catalogo = construir_catalogo(raw_dir, usar_api=not args.no_api)

    salvar(
        catalogo,
        ROOT / "data" / "processed" / "catalog.json",
        ROOT / "web" / "catalog.json",
    )
    _copiar_imagens(ROOT / "images", ROOT / "web" / "images")

    print(
        f"OK: {len(catalogo['produtos'])} produtos, "
        f"{len(catalogo['cotacoes'])} cotações, "
        f"{len(catalogo['insights'])} insights."
    )
    return 0


def _copiar_imagens(origem: Path, destino: Path) -> None:
    """Copia os renders para dentro de web/ (frontend self-contained)."""
    if not origem.exists():
        return
    destino.mkdir(parents=True, exist_ok=True)
    for img in origem.glob("*.png"):
        shutil.copy2(img, destino / img.name)


if __name__ == "__main__":
    raise SystemExit(main())
