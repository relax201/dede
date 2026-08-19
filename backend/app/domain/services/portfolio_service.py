"""Portfolio create + performance (mark-to-market via live quotes)."""

from __future__ import annotations

import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.cache import memory_quotes
from app.infrastructure.cache.redis_client import redis_client
from app.infrastructure.db.models import Company, Portfolio, PortfolioHolding
from app.infrastructure.external.quote_router import QuoteRouter
from app.schemas.stock import PortfolioCreate, PortfolioPerformanceResponse, PortfolioResponse

logger = logging.getLogger(__name__)


class PortfolioService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.quotes = QuoteRouter()

    def create(self, user_id: UUID, payload: PortfolioCreate) -> PortfolioResponse:
        portfolio = Portfolio(
            user_id=user_id,
            name=payload.name,
            capital=payload.capital,
            currency=payload.currency,
            risk_per_trade=payload.risk_per_trade,
        )
        self.db.add(portfolio)
        self.db.flush()

        for holding in payload.holdings:
            symbol = holding.symbol.upper().replace(".SR", "")
            company = self.db.scalar(select(Company).where(Company.symbol == symbol))
            if company is None:
                # Auto-create from memory company cache so portfolios work after first sync
                from app.domain.services.company_sync_service import CompanySyncService

                meta = next(
                    (c for c in CompanySyncService(db=None).list_cached() if c.get("symbol") == symbol),
                    None,
                )
                company = Company(
                    symbol=symbol,
                    symbol_lseg=f"{symbol}.SR",
                    name_ar=(meta or {}).get("name_ar") or symbol,
                    name_en=(meta or {}).get("name_en") or symbol,
                    sector=(meta or {}).get("sector") or "غير محدد",
                    market=(meta or {}).get("market") or "TASI",
                    coverage_tier=(meta or {}).get("coverage_tier") or "basic",
                    is_active=True,
                )
                self.db.add(company)
                self.db.flush()
            self.db.add(
                PortfolioHolding(
                    portfolio_id=portfolio.id,
                    company_id=company.id,
                    quantity=holding.quantity,
                    avg_cost=holding.avg_cost,
                )
            )

        self.db.commit()
        self.db.refresh(portfolio)
        return PortfolioResponse(
            id=portfolio.id,
            name=portfolio.name,
            capital=portfolio.capital,
            currency=portfolio.currency,
            holdings_count=len(payload.holdings),
        )

    async def performance(self, portfolio_id: UUID, user_id: UUID | None = None) -> PortfolioPerformanceResponse:
        cache_key = f"portfolio:{portfolio_id}:perf"
        cached = redis_client.get_json(cache_key)
        if isinstance(cached, dict):
            return PortfolioPerformanceResponse.model_validate(cached)

        portfolio = self.db.get(Portfolio, portfolio_id)
        if portfolio is None:
            raise LookupError("Portfolio not found")
        if user_id is not None and portfolio.user_id != user_id:
            raise PermissionError("لا تملك هذه المحفظة")

        total_cost = Decimal("0")
        market_value = Decimal("0")
        holdings_detail: list[dict] = []

        for h in portfolio.holdings:
            symbol = h.company.symbol if h.company else ""
            qty = Decimal(str(h.quantity))
            avg = Decimal(str(h.avg_cost))
            last = await self._last_price(symbol, fallback=float(avg))
            last_d = Decimal(str(last))
            cost = qty * avg
            value = qty * last_d
            total_cost += cost
            market_value += value
            holdings_detail.append(
                {
                    "symbol": symbol,
                    "quantity": float(qty),
                    "avg_cost": float(avg),
                    "last_price": float(last_d),
                    "market_value": float(value),
                    "unrealized_pnl": float(value - cost),
                }
            )

        unrealized = market_value - total_cost
        return_pct = float((unrealized / total_cost) * 100) if total_cost > 0 else 0.0
        response = PortfolioPerformanceResponse(
            portfolio_id=portfolio.id,
            name=portfolio.name,
            capital=portfolio.capital,
            total_cost=total_cost,
            market_value=market_value,
            unrealized_pnl=unrealized,
            return_pct=return_pct,
            holdings=holdings_detail,
        )
        redis_client.set_json(cache_key, response.model_dump(mode="json"), ttl_seconds=60)
        return response

    async def _last_price(self, symbol: str, fallback: float) -> float:
        if not symbol:
            return fallback
        mem = memory_quotes.get_quote(symbol)
        if isinstance(mem, dict) and mem.get("price") is not None:
            return float(mem["price"])
        cached = redis_client.get_json(f"quote:{symbol}")
        if isinstance(cached, dict) and cached.get("price") is not None:
            return float(cached["price"])
        try:
            quote = await self.quotes.get_quote(symbol)
            return float(quote.price)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Portfolio price fallback for %s: %s", symbol, exc)
            return fallback
