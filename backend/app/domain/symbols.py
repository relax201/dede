"""
Symbol normalization across providers
توحيد الرموز بين SAHMK / MarketAux / Tadawul (2222) و LSEG (2222.SR)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Provider = Literal["sahmk", "lseg", "marketaux", "tadawul", "alpha_vantage", "internal"]


@dataclass(frozen=True)
class SymbolForms:
    """Canonical internal form is bare TASI code, e.g. 2222."""

    bare: str          # 2222 — SAHMK / MarketAux / Tadawul
    lseg: str          # 2222.SR
    display: str       # 2222

    def for_provider(self, provider: Provider) -> str:
        if provider == "lseg":
            return self.lseg
        if provider == "alpha_vantage":
            return self.lseg  # Alpha Vantage often uses .SR for Saudi
        return self.bare


def normalize_symbol(raw: str) -> SymbolForms:
    """
    Accept '2222', '2222.SR', '2222.sr' and return all provider forms.
    """
    if not raw or not str(raw).strip():
        raise ValueError("Empty symbol")
    cleaned = str(raw).strip().upper().replace(" ", "")
    if cleaned.endswith(".SR"):
        bare = cleaned[:-3]
    else:
        bare = cleaned
    if not bare.isdigit() and not bare.replace(".", "").isalnum():
        # Allow alphanumeric tickers if Tadawul expands later; still strip .SR
        pass
    if not bare:
        raise ValueError(f"Invalid symbol: {raw}")
    return SymbolForms(bare=bare, lseg=f"{bare}.SR", display=bare)


def to_provider_symbol(raw: str, provider: Provider) -> str:
    return normalize_symbol(raw).for_provider(provider)
