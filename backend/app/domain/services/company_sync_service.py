"""Sync TASI company universe from SAHMK → Redis (+ PostgreSQL when available)"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from app.domain.symbols import normalize_symbol
from app.infrastructure.cache.redis_client import redis_client
from app.infrastructure.external.sahmk_client import SahmkClient
from app.infrastructure.external.sahmk_universe import PRIORITY_SYMBOLS

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

COMPANIES_FILE = Path(__file__).resolve().parents[4] / "data" / "companies_tasi.json"


class CompanySyncService:
    def __init__(self, db: "Session | None" = None, client: SahmkClient | None = None) -> None:
        self.db = db
        self.client = client or SahmkClient()

    async def sync_tasi(self, enrich_sectors: bool = True, enrich_limit: int = 80) -> dict[str, Any]:
        if not self.client.configured:
            raise RuntimeError("SAHMK_API_KEY is not configured")

        rows = await self.client.iter_all_companies(market="TASI", page_size=50)
        companies: list[dict[str, Any]] = []
        for row in rows:
            if row.get("is_etf"):
                continue
            try:
                forms = normalize_symbol(str(row["symbol"]))
            except (KeyError, ValueError):
                continue
            companies.append(
                {
                    "symbol": forms.bare,
                    "symbol_lseg": forms.lseg,
                    "name_ar": row.get("name_ar") or row.get("name") or forms.bare,
                    "name_en": row.get("name_en") or forms.bare,
                    "sector": "غير محدد",
                    "sector_en": None,
                    "market": row.get("market") or row.get("market_segment") or "TASI",
                    "coverage_tier": "advanced" if forms.bare in set(PRIORITY_SYMBOLS) else "basic",
                    "is_active": str(row.get("status", "active")).lower() == "active",
                }
            )

        # Enrich sectors for priority + first N symbols (rate-limit friendly)
        if enrich_sectors and companies:
            targets = []
            by_sym = {c["symbol"]: c for c in companies}
            for s in PRIORITY_SYMBOLS:
                if s in by_sym:
                    targets.append(s)
            for c in companies:
                if c["symbol"] not in targets:
                    targets.append(c["symbol"])
                if len(targets) >= enrich_limit:
                    break
            for sym in targets:
                try:
                    detail = await self.client.get_company(sym)
                    by_sym[sym]["sector"] = detail.get("sector_name_ar") or detail.get("sector_name") or "غير محدد"
                    by_sym[sym]["sector_en"] = detail.get("sector_name")
                    if detail.get("name"):
                        by_sym[sym]["name_ar"] = detail["name"]
                    if detail.get("name_en"):
                        by_sym[sym]["name_en"] = detail["name_en"]
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Sector enrich failed for %s: %s", sym, exc)

        redis_client.set_json("symbols:all", companies, ttl_seconds=3600)
        redis_client.set_json(
            "symbols:meta",
            {"market": "TASI", "count": len(companies), "source": "sahmk"},
            ttl_seconds=3600,
        )
        self._persist_file(companies)

        db_upserts = 0
        if self.db is not None:
            db_upserts = self._upsert_postgres(companies)

        return {
            "ok": True,
            "source": "sahmk",
            "market": "TASI",
            "count": len(companies),
            "db_upserts": db_upserts,
            "sample": companies[:5],
        }

    def list_cached(self) -> list[dict[str, Any]]:
        cached = redis_client.get_json("symbols:all")
        if isinstance(cached, list):
            return cached
        if COMPANIES_FILE.exists():
            try:
                data = json.loads(COMPANIES_FILE.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return data
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed reading companies file: %s", exc)
        return []

    def _persist_file(self, companies: list[dict[str, Any]]) -> None:
        try:
            COMPANIES_FILE.parent.mkdir(parents=True, exist_ok=True)
            COMPANIES_FILE.write_text(
                json.dumps(companies, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("Companies file persist failed: %s", exc)

    def _upsert_postgres(self, companies: list[dict[str, Any]]) -> int:
        assert self.db is not None
        changed = 0
        try:
            from sqlalchemy import select

            from app.infrastructure.db.models import Company

            for item in companies:
                existing = self.db.scalar(select(Company).where(Company.symbol == item["symbol"]))
                if existing is None:
                    self.db.add(
                        Company(
                            symbol=item["symbol"],
                            symbol_lseg=item["symbol_lseg"],
                            name_ar=item["name_ar"],
                            name_en=item["name_en"],
                            sector=item["sector"],
                            market=item["market"],
                            coverage_tier=item["coverage_tier"],
                            is_active=item["is_active"],
                        )
                    )
                    changed += 1
                else:
                    existing.name_ar = item["name_ar"]
                    existing.name_en = item["name_en"]
                    existing.sector = item["sector"]
                    existing.symbol_lseg = item["symbol_lseg"]
                    existing.coverage_tier = item["coverage_tier"]
                    existing.is_active = item["is_active"]
                    changed += 1
            self.db.commit()
        except Exception as exc:  # noqa: BLE001
            logger.warning("PostgreSQL upsert skipped/failed: %s", exc)
            try:
                self.db.rollback()
            except Exception:  # noqa: BLE001
                pass
            return 0
        return changed
