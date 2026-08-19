# هيكل مجلدات المشروع / Project Structure

```text
TASI2050/
├── README.md
├── .env.example
├── docker-compose.yml
├── docs/
│   ├── ARCHITECTURE.md          # المراحل الأربع + Mermaid
│   └── PROJECT_STRUCTURE.md
├── database/
│   ├── postgres/
│   │   ├── 001_schema.sql
│   │   └── queries.sql
│   ├── clickhouse/
│   │   └── 001_schema.sql
│   └── redis/
│       └── KEYS.md
├── backend/                     # FastAPI — Clean Architecture
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py
│   │   ├── api/v1/endpoints/    # stock, recommendation, portfolio, market
│   │   ├── core/                # config, security
│   │   ├── domain/services/     # historical, market_book, recommendations
│   │   ├── infrastructure/      # db, redis, sahmk_client (quotes/history/depth/trades)
│   │   ├── schemas/             # Pydantic / OpenAPI
│   │   └── websockets/          # /ws/live
│   └── tests/unit/
├── ml/
│   ├── Dockerfile
│   ├── features/technical_indicators.py
│   ├── models/xgboost_model.py
│   ├── models/lstm_model.py
│   ├── ensemble/ensemble_model.py
│   ├── training/train_pipeline.py
│   └── tests/
├── etl/
│   └── dags/tasi_etl_dag.py     # Airflow: LSEG daily + MarketAux hourly
├── frontend/                    # React + TypeScript + Vite
│   ├── Dockerfile
│   ├── src/pages/Dashboard.tsx
│   ├── src/components/PriceChart.tsx
│   ├── src/components/OrderBook.tsx
│   ├── src/components/TradeTape.tsx
│   └── src/styles/dashboard.css
└── infrastructure/
    └── monitoring/prometheus.yml
```

## SAHMK data surfaces (v2.4)

| Endpoint | Source |
|----------|--------|
| `GET /api/stock/{symbol}/candles` | `GET /historical/{symbol}/` (1d/1w/1m/30m/60m) |
| `GET /api/stock/{symbol}/depth` | `GET /market/depth/{symbol}/` |
| `GET /api/stock/{symbol}/trades` | `GET /market/trades/{symbol}/` |

## طبقات Clean Architecture (Backend)

1. **api** — HTTP/WebSocket adapters (FastAPI routers)
2. **schemas** — Pydantic DTOs (OpenAPI contract)
3. **domain/services** — قواعد العمل (توصيات، محافظ، مخاطر)
4. **infrastructure** — PostgreSQL / Redis / مزودو البيانات
5. **core** — إعدادات، أمان، RBAC
