-- =============================================================================
-- 3 استعلامات SQL أساسية
-- =============================================================================

-- 1) آخر 30 سعر (من ClickHouse — بيانات زمنية)
-- ملاحظة: يُنفَّذ على ClickHouse وليس PostgreSQL
/*
SELECT
    symbol,
    ts,
    open,
    high,
    low,
    close,
    volume
FROM tasi.ohlcv_daily
WHERE symbol = {symbol:String}
ORDER BY trade_date DESC
LIMIT 30;
*/

-- بديل PostgreSQL إن وُجدت مرآة للأسعار اليومية:
-- (جدول اختياري للواجهات التي تحتاج JOIN مع الشركات)
CREATE TABLE IF NOT EXISTS price_daily_mirror (
    company_id  UUID NOT NULL REFERENCES companies(id),
    trade_date  DATE NOT NULL,
    open        NUMERIC(18, 4) NOT NULL,
    high        NUMERIC(18, 4) NOT NULL,
    low         NUMERIC(18, 4) NOT NULL,
    close       NUMERIC(18, 4) NOT NULL,
    volume      NUMERIC(20, 2) NOT NULL DEFAULT 0,
    PRIMARY KEY (company_id, trade_date)
);

-- استعلام 1: آخر 30 سعر لسهم معيّن
SELECT
    c.symbol,
    p.trade_date,
    p.open,
    p.high,
    p.low,
    p.close,
    p.volume
FROM price_daily_mirror p
JOIN companies c ON c.id = p.company_id
WHERE c.symbol = :symbol
ORDER BY p.trade_date DESC
LIMIT 30;


-- استعلام 2: أفضل التوصيات النشطة مرتبة حسب الثقة
SELECT
    r.id,
    c.symbol,
    c.name_ar,
    c.sector,
    r.action,
    r.confidence,
    r.entry_price,
    r.stop_loss,
    r.take_profit,
    r.risk_reward,
    r.explanation_ar,
    r.shap_summary,
    r.generated_at
FROM recommendations r
JOIN companies c ON c.id = r.company_id
WHERE r.status = 'active'
  AND r.expires_at IS NULL OR r.expires_at > NOW()
ORDER BY r.confidence DESC, r.generated_at DESC
LIMIT 50;


-- استعلام 3: أداء المحفظة (قيمة سوقية، تكلفة، عائد)
WITH holdings AS (
    SELECT
        ph.portfolio_id,
        ph.company_id,
        ph.quantity,
        ph.avg_cost,
        c.symbol,
        latest.close AS last_price
    FROM portfolio_holdings ph
    JOIN companies c ON c.id = ph.company_id
    JOIN LATERAL (
        SELECT close
        FROM price_daily_mirror pdm
        WHERE pdm.company_id = ph.company_id
        ORDER BY trade_date DESC
        LIMIT 1
    ) latest ON TRUE
    WHERE ph.portfolio_id = :portfolio_id
)
SELECT
    p.id AS portfolio_id,
    p.name,
    p.capital,
    COALESCE(SUM(h.quantity * h.avg_cost), 0) AS total_cost,
    COALESCE(SUM(h.quantity * h.last_price), 0) AS market_value,
    COALESCE(SUM(h.quantity * h.last_price) - SUM(h.quantity * h.avg_cost), 0) AS unrealized_pnl,
    CASE
        WHEN COALESCE(SUM(h.quantity * h.avg_cost), 0) = 0 THEN 0
        ELSE ROUND(
            ((SUM(h.quantity * h.last_price) - SUM(h.quantity * h.avg_cost))
             / SUM(h.quantity * h.avg_cost)) * 100,
            4
        )
    END AS return_pct
FROM portfolios p
LEFT JOIN holdings h ON h.portfolio_id = p.id
WHERE p.id = :portfolio_id
GROUP BY p.id, p.name, p.capital;
