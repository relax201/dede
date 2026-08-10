"""Portfolio create + performance"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.infrastructure.cache.redis_client import redis_client
from app.infrastructure.db.models import Company, Portfolio, PortfolioHolding, User
from app.schemas.stock import PortfolioCreate, PortfolioPerformanceResponse, PortfolioResponse


class PortfolioService:
    def __init__(self, db: Session) -> None:
        self.db = db

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
            company = self.db.scalar(select(Company).where(Company.symbol == holding.symbol.upper()))
            if company is None:
                raise LookupError(f"Symbol not found: {holding.symbol}")
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

    def performance(self, portfolio_id: UUID) -> PortfolioPerformanceResponse:
        cache_key = f"portfolio:{portfolio_id}:perf"
        cached = redis_client.get_json(cache_key)
        if isinstance(cached, dict):
            return PortfolioPerformanceResponse.model_validate(cached)

        portfolio = self.db.get(Portfolio, portfolio_id)
        if portfolio is None:
            raise LookupError("Portfolio not found")

        # Prefer SQL query from queries.sql (performance aggregation)
        row = self.db.execute(
            text(
                """
                WITH holdings AS (
                    SELECT
                        ph.portfolio_id,
                        ph.quantity,
                        ph.avg_cost,
                        c.symbol,
                        COALESCE(pdm.close, ph.avg_cost) AS last_price
                    FROM portfolio_holdings ph
                    JOIN companies c ON c.id = ph.company_id
                    LEFT JOIN LATERAL (
                        SELECT close
                        FROM price_daily_mirror pdm
                        WHERE pdm.company_id = ph.company_id
                        ORDER BY trade_date DESC
                        LIMIT 1
                    ) pdm ON TRUE
                    WHERE ph.portfolio_id = :portfolio_id
                )
                SELECT
                    COALESCE(SUM(quantity * avg_cost), 0) AS total_cost,
                    COALESCE(SUM(quantity * last_price), 0) AS market_value
                FROM holdings
                """
            ),
            {"portfolio_id": str(portfolio_id)},
        ).mappings().first()

        total_cost = Decimal(str(row["total_cost"])) if row else Decimal("0")
        market_value = Decimal(str(row["market_value"])) if row else Decimal("0")
        unrealized = market_value - total_cost
        return_pct = float((unrealized / total_cost) * 100) if total_cost > 0 else 0.0

        holdings_detail = []
        for h in portfolio.holdings:
            holdings_detail.append(
                {
                    "symbol": h.company.symbol if h.company else str(h.company_id),
                    "quantity": float(h.quantity),
                    "avg_cost": float(h.avg_cost),
                }
            )

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
        redis_client.set_json(cache_key, response.model_dump(mode="json"), ttl_seconds=120)
        return response
