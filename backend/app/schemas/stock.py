"""Pydantic schemas — Stocks / Recommendations / Portfolios"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class IndicatorSnapshot(BaseModel):
    rsi_14: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    bb_upper: float | None = None
    bb_middle: float | None = None
    bb_lower: float | None = None
    atr_14: float | None = None
    sma_20: float | None = None
    sma_50: float | None = None
    volatility_20: float | None = None


class StockResponse(BaseModel):
    symbol: str
    name_ar: str
    name_en: str
    sector: str
    price: float
    change_pct: float
    volume: float
    high: float | None = None
    low: float | None = None
    indicators: IndicatorSnapshot
    updated_at: datetime
    stale: bool = False


class ShapContribution(BaseModel):
    feature: str
    shap_value: float


class RecommendationResponse(BaseModel):
    symbol: str
    action: Literal["strong_buy", "buy", "hold", "sell"]
    confidence: float = Field(ge=0, le=1)
    ensemble_score: float = Field(ge=0, le=1)
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward: float = 2.5
    atr_value: float | None = None
    shap: list[ShapContribution] = Field(default_factory=list)
    explanation_ar: str
    model_version: str
    generated_at: datetime


class HoldingCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=16)
    quantity: Decimal = Field(gt=0)
    avg_cost: Decimal = Field(ge=0)


class PortfolioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    capital: Decimal = Field(gt=0)
    currency: str = Field(default="SAR", min_length=3, max_length=3)
    holdings: list[HoldingCreate] = Field(default_factory=list)
    risk_per_trade: Decimal = Field(default=Decimal("0.015"), gt=0, le=Decimal("0.02"))

    @field_validator("currency")
    @classmethod
    def upper_currency(cls, v: str) -> str:
        return v.upper()


class PortfolioResponse(BaseModel):
    id: UUID
    name: str
    capital: Decimal
    currency: str
    holdings_count: int


class PortfolioPerformanceResponse(BaseModel):
    portfolio_id: UUID
    name: str
    capital: Decimal
    total_cost: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    return_pct: float
    holdings: list[dict[str, Any]] = Field(default_factory=list)


class MarketOverview(BaseModel):
    tasi_index: float
    tasi_change_pct: float
    advancers: int
    decliners: int
    volume_total: float
    updated_at: datetime


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    message: str
