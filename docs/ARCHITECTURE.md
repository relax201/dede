# منصة تحليل سوق الأسهم السعودي (تاسي) — مخطط تنفيذي شامل

## ملخص تنفيذي

منصة مؤسسية لتحليل سوق تاسي وإصدار توصيات استثمارية مدعومة بـ Ensemble (XGBoost + LSTM + Prophet + AraBERT) بدقة مستهدفة ≥ 78% AUC-ROC. تعتمد البنية على Clean Architecture مع FastAPI و React و PostgreSQL/ClickHouse/Redis، وتدفق بيانات عبر Kafka + Spark + Airflow من SAHMK و LSEG و MarketAux. تُنشر على AWS EKS مع GitOps (ArgoCD) ومراقبة Prometheus/Grafana، مع أهداف تشغيل: uptime 99.9% واستجابة API أقل من 200ms. هذا المستودع جاهز لتسليمه لفريق تطوير للبدء مباشرة بعد الإجابة على الأسئلة المفتوحة في نهاية الوثيقة.

---

## المرحلة الأولى: التصميم المعماري (Architecture Design)

### 1.1 رسم البنية التحتية (Mermaid)

```mermaid
flowchart TB
  subgraph Clients["العملاء"]
    WEB["React Dashboard<br/>RTL / TypeScript"]
    MOB["مستهلكو API<br/>محللون / مؤسسات"]
  end

  subgraph Edge["طبقة الحافة"]
    ALB["AWS ALB + TLS 1.3"]
    WAF["AWS WAF + Rate Limit"]
  end

  subgraph K8s["Amazon EKS Cluster"]
    subgraph API["API Layer"]
      GW["API Gateway Pods<br/>FastAPI"]
      WS["WebSocket Workers<br/>/ws/live"]
      AUTH["Auth Service<br/>JWT + MFA + RBAC"]
    end

    subgraph Rec["Recommendation Engine"]
      REC["Recommendation Service"]
      SHAP["SHAP Explainer"]
      RISK["Risk Engine<br/>SL/TP / Position Sizing"]
    end

    subgraph MLServing["ML Serving"]
      INF["Inference Service"]
      ENS["Ensemble Orchestrator"]
      MLflowS["MLflow Model Registry"]
    end

    subgraph ETL["Data Platform"]
      KAFKA["Apache Kafka"]
      SPARK["Apache Spark Jobs"]
      AIRFLOW["Airflow Scheduler"]
    end
  end

  subgraph External["مصادر البيانات الخارجية"]
    SAHMK["SAHMK API<br/>كل 5 ثوانٍ"]
    LSEG["LSEG API<br/>يومي"]
    MAUX["MarketAux API<br/>كل ساعة"]
  end

  subgraph Data["طبقة البيانات"]
    PG[("PostgreSQL<br/>مستخدمين / محافظ / توصيات")]
    CH[("ClickHouse<br/>أسعار / مؤشرات / تنبؤات")]
    REDIS[("Redis<br/>Cache + Pub/Sub")]
  end

  subgraph Obs["المراقبة والحوكمة"]
    PROM["Prometheus"]
    GRAF["Grafana"]
    AUDIT["Audit Log 90 يوم"]
  end

  WEB --> ALB
  MOB --> ALB
  ALB --> WAF --> GW
  GW --> AUTH
  GW --> REC
  GW --> WS
  WS --> REDIS
  REC --> INF
  REC --> SHAP
  REC --> RISK
  INF --> ENS
  ENS --> MLflowS

  SAHMK --> KAFKA
  LSEG --> AIRFLOW
  MAUX --> AIRFLOW
  AIRFLOW --> SPARK
  KAFKA --> SPARK
  SPARK --> CH
  SPARK --> PG
  SPARK --> REDIS

  GW --> PG
  GW --> CH
  GW --> REDIS
  REC --> PG
  REC --> CH

  GW --> PROM
  SPARK --> PROM
  PROM --> GRAF
  AUTH --> AUDIT
```

### 1.2 تفاعل المكونات

| التدفق | الوصف |
|--------|--------|
| Live Ingest | SAHMK → Kafka topic `tasi.ticks` كل 5 ثوانٍ → Spark Streaming يطبّع الشموع ويكتب إلى ClickHouse + ينشر إلى Redis Pub/Sub |
| Daily History | Airflow DAG يومي يسحب LSEG → Spark batch → ClickHouse `ohlcv_daily` + تحديث ميزات ML |
| News/NLP | Airflow كل ساعة → MarketAux → AraBERT sentiment → ClickHouse `news_sentiment` |
| Inference | عند طلب توصية أو جدولة دقائقية: Inference Service يحمّل أحدث نموذج من MLflow → Ensemble → Risk Engine → PostgreSQL `recommendations` |
| Live Push | Redis Pub/Sub → WebSocket workers → العملاء المتصلون على `/ws/live` |
| Explainability | SHAP يحسب مساهمة الميزات ويُخزَّن ملخص نصي عربي مع التوصية |

### 1.3 اختيار التقنيات مع التبرير

| التقنية | التبرير |
|---------|---------|
| **FastAPI** | أداء عالٍ async، OpenAPI تلقائي، Type Hints أصلية — مثالي لـ API مالي حساس للزمن |
| **React + TypeScript** | نظام بيئي ناضج، Lightweight Charts، RTL، قابلية صيانة للمؤسسات |
| **PostgreSQL** | ACID للمعاملات (مستخدمين، محافظ، صلاحيات، توصيات) |
| **ClickHouse** | استعلامات زمنية مجمّعة سريعة على OHLCV والمؤشرات والتنبؤات |
| **Redis** | Cache للقراءات الساخنة + Pub/Sub للتحديثات اللحظية + Rate Limiting |
| **Kafka + Spark** | فصل المنتجين عن المستهلكين، تحمل ضغط التحديث كل 5 ثوانٍ، معالجة دفعية وتدفقية |
| **Airflow** | جدولة ETL واضحة وقابلة للمراقبة (يومي/ساعي) |
| **XGBoost / LSTM / Prophet / AraBERT** | تغطية أنماط جدولية + تسلسلية + موسمية + مشاعر عربية |
| **MLflow + Kubeflow** | تتبّع التجارب، تسجيل النماذج، خطوط تدريب على EKS |
| **EKS + ArgoCD + GitHub Actions** | تشغيل سحابي مؤسسي مع GitOps |
| **Prometheus + Grafana** | SLOs: latency، uptime، أخطاء الاستدلال |

### 1.4 Failover واستمرارية الخدمة

- **API**: Deployment بـ ≥ 3 replicas خلف ALB مع readiness/liveness probes و PodDisruptionBudget.
- **PostgreSQL**: Multi-AZ RDS مع failover تلقائي؛ نسخ احتياطي يومي + PITR.
- **ClickHouse**: مجموعة replicas (2+) مع ZooKeeper/ClickHouse Keeper؛ كتابة مع `ReplicatedMergeTree`.
- **Redis**: ElastiCache Redis في وضع Cluster/Failover؛ إن فشل الكاش يتم الرجوع إلى المصدر (cache-aside) دون انقطاع.
- **Kafka**: عامل replication factor = 3 و `min.insync.replicas = 2`.
- **ML Serving**: نموذجان نشطان (blue/green) عبر MLflow aliases (`champion`/`challenger`) مع rollback فوري.
- **Circuit Breaker**: تجاه مصادر SAHMK/LSEG/MarketAux مع تخزين آخر قيمة صالحة وعلامة `stale`.
- **DR**: نسخ لقطة يومية إلى منطقة ثانوية؛ RPO ≤ 15 دقيقة، RTO ≤ 1 ساعة للمسار الحرج.
- **هدف Uptime**: 99.9% عبر فحوصات صحية ومناطق توافر متعددة.

### Checklist — المرحلة الأولى

- [ ] اعتماد مخطط EKS ومناطق التوافر (AZs)
- [ ] تأكيد عقود SAHMK / LSEG / MarketAux وحدود المعدل
- [ ] تعريف SLOs في Grafana (p95 latency، error rate، uptime)
- [ ] تصميم استراتيجية blue/green لنماذج MLflow
- [ ] توثيق Runbooks للـ Failover

---

## المرحلة الثانية: هيكل قاعدة البيانات (Database Schema)

انظر الملفات التنفيذية:

- `database/postgres/001_schema.sql`
- `database/clickhouse/001_schema.sql`
- `database/redis/KEYS.md`
- `database/postgres/queries.sql`

### 2.1 PostgreSQL ERD (Mermaid)

```mermaid
erDiagram
  USERS ||--o{ PORTFOLIOS : owns
  USERS ||--o{ AUDIT_LOGS : generates
  USERS ||--o{ WATCHLISTS : has
  COMPANIES ||--o{ PORTFOLIO_HOLDINGS : included_in
  COMPANIES ||--o{ RECOMMENDATIONS : has
  COMPANIES ||--o{ WATCHLISTS : tracked
  PORTFOLIOS ||--o{ PORTFOLIO_HOLDINGS : contains
  RECOMMENDATIONS ||--o{ RECOMMENDATION_OUTCOMES : evaluated

  USERS {
    uuid id PK
    string email
    string password_hash
    string role
    boolean mfa_enabled
    timestamptz created_at
  }
  COMPANIES {
    uuid id PK
    string symbol UK
    string name_ar
    string name_en
    string sector
    string market
    boolean is_active
  }
  PORTFOLIOS {
    uuid id PK
    uuid user_id FK
    string name
    numeric capital
    string currency
  }
  PORTFOLIO_HOLDINGS {
    uuid id PK
    uuid portfolio_id FK
    uuid company_id FK
    numeric quantity
    numeric avg_cost
  }
  RECOMMENDATIONS {
    uuid id PK
    uuid company_id FK
    string action
    numeric confidence
    numeric entry_price
    numeric stop_loss
    numeric take_profit
    jsonb shap_summary
    string explanation_ar
  }
```

### Checklist — المرحلة الثانية

- [ ] تشغيل ترحيلات Alembic على بيئة التطوير
- [ ] إنشاء جداول ClickHouse مع TTL للبيانات الدقيقة
- [ ] ضبط مفاتيح Redis وTTL حسب `KEYS.md`
- [ ] التحقق من الاستعلامات الثلاثة الأساسية على بيانات عيّنة
- [ ] سياسات تشفير AES-256 للحقول الحساسة (PII)

---

## المرحلة الثالثة: تنفيذ نموذج الذكاء الاصطناعي

انظر:

- `ml/features/technical_indicators.py`
- `ml/models/xgboost_model.py`
- `ml/models/lstm_model.py`
- `ml/ensemble/ensemble_model.py`
- `ml/training/train_pipeline.py`

### Checklist — المرحلة الثالثة

- [ ] تجهيز بيانات تاريخية ≥ 5 سنوات لأسهم تاسي السائلة
- [ ] تدريب XGBoost مع تقسيم زمني و Hyperparameter Tuning
- [ ] تدريب LSTM على GPU مع EarlyStopping
- [ ] تسجيل النماذج في MLflow + تقييم SHAP
- [ ] بناء Ensemble والتحقق من AUC ≥ 0.78 على out-of-time test

---

## المرحلة الرابعة: Backend API والواجهة الأمامية

انظر:

- `backend/app/` — FastAPI Clean Architecture
- `frontend/src/pages/Dashboard.tsx`
- `docker-compose.yml`
- `.env.example`

### Checklist — المرحلة الرابعة

- [ ] تشغيل `docker compose up` محلياً
- [ ] التحقق من Swagger على `/docs`
- [ ] اختبار WebSocket `/ws/live`
- [ ] ربط Dashboard بالمؤشرات والتوصيات والفلاتر
- [ ] اجتياز اختبارات `pytest` و معايير القبول (latency / hit-rate stub)

---

## خطة التنفيذ المرحلية (8 أشهر)

| الفترة | المخرجات |
|--------|----------|
| الأشهر 1–2 | بيئات AWS/EKS، PostgreSQL/ClickHouse/Redis، ETL أساسي (Kafka + Airflow) |
| الأشهر 3–4 | XGBoost + Prophet، خطوط ميزات، تقييم أولي |
| الأشهر 5–6 | LSTM + AraBERT + Ensemble + SHAP + Risk Engine |
| الأشهر 7–8 | FastAPI كامل، React Dashboard، تكامل، اختبارات قبول، إطلاق تجريبي |

## معايير القبول

| المعيار | الهدف |
|---------|-------|
| Ensemble AUC-ROC | ≥ 78% |
| Sharpe Ratio | > 1.5 |
| Hit Rate | > 60% |
| Max Drawdown | < 15% |
| Uptime | 99.9% |
| API Response | < 200ms |
| Live Latency | < 1s |

---

## قرارات معتمدة

جميع الأسئلة المفتوحة أُجيبت وثُبّتت في [`docs/DECISIONS.md`](DECISIONS.md)  
(مصادر البيانات، الرموز، التغطية، الآفاق، CMA، AWS، الهوية، تسعير المحفظة).
