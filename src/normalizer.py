"""Normalização de modelos, armazenamento e tipo.

Responsabilidade única: transformar tokens crus do texto em valores canônicos.
"IPHONE 17 PRO MAX" -> linha="iPhone 17", versao="Pro Max",
modelo="iPhone 17 Pro Max".
"""

from __future__ import annotations

# Versões reconhecidas, ordenadas da mais específica para a mais genérica.
# A ordem importa: "PRO MAX" deve ser testado antes de "PRO".
_VERSOES: list[tuple[str, str]] = [
    ("PRO MAX", "Pro Max"),
    ("PLUS", "Plus"),
    ("AIR", "Air"),
    ("PRO", "Pro"),
    ("E", "e"),  # iPhone 17e
]

_TIPOS_VALIDOS = {"BE", "ESIM", "HN", "CPO"}


def normalizar_fornecedor(raw: str) -> str:
    """Mapeia o remetente do WhatsApp para um nome de fornecedor amigável."""
    r = (raw or "").strip().lower()
    if "shopping china" in r:
        return "Shopping China"
    if "compushop" in r:
        return "Compushop"
    if "skyblue" in r or "595 975 299790" in r:
        return "Skyblue"
    return (raw or "").strip()


def normalizar_condicao(raw: str | None) -> str:
    """Canoniza a condição: lacrado | semi-novo | cpo.

    Swap/recondicionado/usado caem em 'semi-novo' para permitir comparar usados
    entre fornecedores. CPO (certificado de fábrica) fica à parte.
    """
    r = (raw or "").strip().lower()
    if "cpo" in r:
        return "cpo"
    if any(t in r for t in ("semi", "swap", "recond", "usad")):
        return "semi-novo"
    return "lacrado"


def normalizar_tipo(token: str | None) -> str:
    """Valida o tipo de procedência. Retorna "" se desconhecido/ausente."""
    if not token:
        return ""
    t = token.strip().upper()
    return t if t in _TIPOS_VALIDOS else ""


def normalizar_armazenamento(token: str) -> str:
    """Padroniza '256gb' -> '256GB', '1tb' -> '1TB', '128' -> '128GB'."""
    t = token.strip().upper().replace(" ", "")
    if t and t.isdigit():  # número puro: assume GB (TB sempre vem escrito)
        t += "GB"
    return t


def normalizar_modelo(linha_modelo: str) -> tuple[str, str, str]:
    """Extrai (linha, versao, modelo_normalizado) de algo como 'IPHONE 17 PRO MAX'.

    - linha: 'iPhone <numero>[e]' (ex: 'iPhone 17', 'iPhone 17e')
    - versao: 'Pro Max' | 'Air' | 'Plus' | 'Pro' | '' (base)
    - modelo_normalizado: linha + versao quando houver.
    """
    bruto = linha_modelo.strip().upper()
    bruto = bruto.replace("IPHONE", "", 1).strip()

    # Caso especial: "17e" gruda o 'e' no número (não é versão separada).
    numero, resto = _separar_numero(bruto)
    if not numero:
        # fallback resiliente: devolve o que veio, capitalizado.
        modelo = "iPhone " + _titulo(bruto)
        return ("iPhone", "", modelo.strip())

    versao_canon = ""
    resto_upper = " " + resto.strip() + " "
    for marcador, canon in _VERSOES:
        if f" {marcador} " in resto_upper:
            versao_canon = canon
            break

    linha = f"iPhone {numero}"
    if versao_canon:
        modelo = f"{linha} {versao_canon}"
    else:
        modelo = linha
    return (linha, versao_canon, modelo)


def _separar_numero(bruto: str) -> tuple[str, str]:
    """De '17 PRO MAX' -> ('17', 'PRO MAX'); de '17E 256GB' -> ('17e', '...')."""
    partes = bruto.split()
    if not partes:
        return ("", "")
    primeiro = partes[0]
    # '17e' / '17E' -> número com sufixo 'e'
    if primeiro and primeiro[0].isdigit():
        if primeiro.upper().endswith("E") and primeiro[:-1].isdigit():
            return (primeiro[:-1] + "e", " ".join(partes[1:]))
        if primeiro.isdigit():
            return (primeiro, " ".join(partes[1:]))
    return ("", bruto)


def _titulo(texto: str) -> str:
    return " ".join(p.capitalize() for p in texto.split())
