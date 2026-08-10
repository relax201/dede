-- =============================================================================
-- ClickHouse Schema — Time-Series Market Data / البيانات الزمنية
-- Local/dev: MergeTree. Production: switch to ReplicatedMergeTree + Keeper.
-- =============================================================================

CREATE DATABASE IF NOT EXISTS tasi;

CREATE TABLE IF NOT EXISTS tasi.ohlcv_ticks
(
    symbol          LowCardinality(String),
    ts              DateTime64(3, 'Asia/Riyadh'),
    open            Float64,
    high            Float64,
    low             Float64,
    close           Float64,
    volume          Float64,
    vwap            Float64 DEFAULT 0,
    source          LowCardinality(String) DEFAULT 'sahmk',
    ingested_at     DateTime64(3, 'Asia/Riyadh') DEFAULT now64(3)
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(ts)
ORDER BY (symbol, ts)
TTL toDateTime(ts) + INTERVAL 90 DAY
SETTINGS index_granularity = 8192;

CREATE TABLE IF NOT EXISTS tasi.ohlcv_daily
(
    symbol          LowCardinality(String),
    trade_date      Date,
    open            Float64,
    high            Float64,
    low             Float64,
    close           Float64,
    volume          Float64,
    adj_close       Float64,
    source          LowCardinality(String) DEFAULT 'lseg',
    ingested_at     DateTime64(3, 'Asia/Riyadh') DEFAULT now64(3)
)
ENGINE = ReplacingMergeTree(ingested_at)
PARTITION BY toYear(trade_date)
ORDER BY (symbol, trade_date)
SETTINGS index_granularity = 8192;

CREATE TABLE IF NOT EXISTS tasi.technical_indicators
(
    symbol          LowCardinality(String),
    ts              DateTime64(3, 'Asia/Riyadh'),
    timeframe       LowCardinality(String),
    rsi_14          Float32,
    macd            Float32,
    macd_signal     Float32,
    macd_hist       Float32,
    bb_upper        Float32,
    bb_middle       Float32,
    bb_lower        Float32,
    sma_20          Float32,
    sma_50          Float32,
    ema_12          Float32,
    ema_26          Float32,
    atr_14          Float32,
    volatility_20   Float32,
    ingested_at     DateTime64(3, 'Asia/Riyadh') DEFAULT now64(3)
)
ENGINE = ReplacingMergeTree(ingested_at)
PARTITION BY toYYYYMM(ts)
ORDER BY (symbol, timeframe, ts)
TTL toDateTime(ts) + INTERVAL 365 DAY;

CREATE TABLE IF NOT EXISTS tasi.model_predictions
(
    symbol          LowCardinality(String),
    ts              DateTime64(3, 'Asia/Riyadh'),
    model_name      LowCardinality(String),
    model_version   String,
    proba_up        Float32,
    predicted_action LowCardinality(String),
    features_hash   String,
    ingested_at     DateTime64(3, 'Asia/Riyadh') DEFAULT now64(3)
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(ts)
ORDER BY (symbol, model_name, ts)
TTL toDateTime(ts) + INTERVAL 730 DAY;

CREATE TABLE IF NOT EXISTS tasi.news_sentiment
(
    id              UUID,
    symbol          LowCardinality(String),
    published_at    DateTime64(3, 'Asia/Riyadh'),
    headline        String,
    source          LowCardinality(String) DEFAULT 'marketaux',
    sentiment_score Float32,
    sentiment_label LowCardinality(String),
    ingested_at     DateTime64(3, 'Asia/Riyadh') DEFAULT now64(3)
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(published_at)
ORDER BY (symbol, published_at)
TTL toDateTime(published_at) + INTERVAL 365 DAY;

CREATE TABLE IF NOT EXISTS tasi.latest_prices
(
    symbol          LowCardinality(String),
    ts              DateTime64(3, 'Asia/Riyadh'),
    close           Float64,
    volume          Float64
)
ENGINE = ReplacingMergeTree(ts)
ORDER BY symbol;

CREATE MATERIALIZED VIEW IF NOT EXISTS tasi.mv_latest_prices
TO tasi.latest_prices AS
SELECT symbol, ts, close, volume
FROM tasi.ohlcv_ticks;
