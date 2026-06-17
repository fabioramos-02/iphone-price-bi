"""Dataclasses do domínio — espelham o schema da saída JSON.

Responsabilidade única: definir as estruturas tipadas e sua serialização.
Nenhuma lógica de negócio aqui.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Cotacao:
    """Câmbio de uma coleta. Histórico vem do texto; atual vem da API."""

    data: str  # ISO YYYY-MM-DD
    fornecedor: str
    exchange_rate_brl_historic: Optional[float]
    exchange_rate_brl_current: Optional[float] = None
    exchange_rate_pyg: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "data": self.data,
            "fornecedor": self.fornecedor,
            "exchange_rate_brl_historic": self.exchange_rate_brl_historic,
            "exchange_rate_brl_current": self.exchange_rate_brl_current,
            "exchange_rate_pyg": self.exchange_rate_pyg,
        }


@dataclass
class Produto:
    """Um item de catálogo numa data específica."""

    data: str  # ISO YYYY-MM-DD
    fornecedor: str
    linha: str  # ex: "iPhone 17"
    versao: str  # ex: "Pro Max", "Air", "e", "Plus", "" (base)
    modelo_normalizado: str  # ex: "iPhone 17 Pro Max"
    armazenamento: str  # ex: "256GB", "1TB"
    tipo: str  # BE | ESIM | HN | CPO | ""  (variante/chip do fornecedor)
    preco_usd: Optional[float] = None  # None quando moeda_base == "BRL"
    condicao: str = "lacrado"  # lacrado | semi-novo | swap | recondicionado | cpo
    cores: list[str] = field(default_factory=list)
    observacoes: str = ""
    moeda_base: str = "USD"  # USD (import) | BRL (preço já em real)
    preco_brl_historico: Optional[float] = None
    preco_brl_atual: Optional[float] = None

    @property
    def chave_grupo(self) -> str:
        """Unidade de comparação: mesmo modelo, armazenamento e condição.

        Não inclui `tipo` (BE/ESIM) nem fornecedor, para comparar o mesmo aparelho
        entre fornecedores. Inclui `condicao` para nunca comparar lacrado com usado.
        """
        return f"{self.modelo_normalizado}|{self.armazenamento}|{self.condicao}"

    def to_dict(self) -> dict:
        return {
            "data": self.data,
            "fornecedor": self.fornecedor,
            "linha": self.linha,
            "versao": self.versao,
            "modelo_normalizado": self.modelo_normalizado,
            "armazenamento": self.armazenamento,
            "tipo": self.tipo,
            "condicao": self.condicao,
            "preco_usd": self.preco_usd,
            "moeda_base": self.moeda_base,
            "cores": self.cores,
            "observacoes": self.observacoes,
            "preco_brl_historico": self.preco_brl_historico,
            "preco_brl_atual": self.preco_brl_atual,
        }


@dataclass
class Insight:
    """Mensagem analítica gerada para o usuário final."""

    tipo: str  # "melhor_momento" | "impacto_dolar" | "queda_real" | "queda_falsa"
    chave_grupo: str
    mensagem: str
    severidade: str = "info"  # info | alerta

    def to_dict(self) -> dict:
        return {
            "tipo": self.tipo,
            "chave_grupo": self.chave_grupo,
            "mensagem": self.mensagem,
            "severidade": self.severidade,
        }
