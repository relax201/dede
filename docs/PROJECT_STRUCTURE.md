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
│   │   ├── domain/services/     # business logic
│   │   ├── infrastructure/      # db, redis
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
│   └── src/styles/dashboard.css
└── infrastructure/
    └── monitoring/prometheus.yml
```

## طبقات Clean Architecture (Backend)

1. **api** — HTTP/WebSocket adapters (FastAPI routers)
2. **schemas** — Pydantic DTOs (OpenAPI contract)
3. **domain/services** — قواعد العمل (توصيات، محافظ، مخاطر)
4. **infrastructure** — PostgreSQL / Redis / مزودو البيانات
5. **core** — إعدادات، أمان، RBAC
