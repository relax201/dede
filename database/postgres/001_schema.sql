-- =============================================================================
-- PostgreSQL Schema — TASI AI Platform (Structured Data)
-- مخطط قاعدة البيانات العلائقية: مستخدمين، شركات، محافظ، توصيات
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "citext";

CREATE TYPE user_role AS ENUM ('user', 'analyst', 'admin');
CREATE TYPE recommendation_action AS ENUM (
    'strong_buy',  -- شراء قوي > 80%
    'buy',         -- شراء 60-80%
    'hold',        -- محايد 40-60%
    'sell'         -- بيع < 40%
);
CREATE TYPE recommendation_status AS ENUM ('active', 'hit_tp', 'hit_sl', 'expired', 'cancelled');

-- ---------------------------------------------------------------------------
-- Users / المصادقة والصلاحيات
-- ---------------------------------------------------------------------------
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           CITEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    full_name       TEXT,
    role            user_role NOT NULL DEFAULT 'user',
    mfa_enabled     BOOLEAN NOT NULL DEFAULT FALSE,
    mfa_secret_enc  BYTEA,                          -- AES-256 encrypted TOTP secret
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_role ON users(role) WHERE is_active;

-- ---------------------------------------------------------------------------
-- Companies / الشركات المدرجة في تاسي
-- ---------------------------------------------------------------------------
-- coverage_tier:
--   basic    = ضمن تغطية 350+ (بيانات أساسية)
--   advanced = ضمن 120 سهماً لنماذج ML المتقدمة (تحديث القائمة شهرياً)
--   manual   = مضاف يدوياً من المستخدم/المسؤول
CREATE TYPE coverage_tier AS ENUM ('basic', 'advanced', 'manual');

CREATE TABLE companies (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol          VARCHAR(16) NOT NULL UNIQUE,    -- الشكل الداخلي الموحّد: 2222 (بدون .SR)
    symbol_lseg     VARCHAR(16) NOT NULL UNIQUE,    -- 2222.SR لـ LSEG
    name_ar         TEXT NOT NULL,
    name_en         TEXT NOT NULL,
    sector          VARCHAR(64) NOT NULL,
    market          VARCHAR(32) NOT NULL DEFAULT 'TASI',
    isin            VARCHAR(16),
    coverage_tier   coverage_tier NOT NULL DEFAULT 'basic',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_companies_sector ON companies(sector);
CREATE INDEX idx_companies_active ON companies(is_active) WHERE is_active;
CREATE INDEX idx_companies_coverage ON companies(coverage_tier) WHERE is_active;

-- ---------------------------------------------------------------------------
-- Portfolios / المحافظ
-- ---------------------------------------------------------------------------
CREATE TABLE portfolios (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    capital         NUMERIC(18, 2) NOT NULL CHECK (capital >= 0),
    currency        CHAR(3) NOT NULL DEFAULT 'SAR',
    risk_per_trade  NUMERIC(5, 4) NOT NULL DEFAULT 0.015
                        CHECK (risk_per_trade > 0 AND risk_per_trade <= 0.02),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, name)
);

CREATE INDEX idx_portfolios_user ON portfolios(user_id);

CREATE TABLE portfolio_holdings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id    UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    company_id      UUID NOT NULL REFERENCES companies(id),
    quantity        NUMERIC(18, 4) NOT NULL CHECK (quantity >= 0),
    avg_cost        NUMERIC(18, 4) NOT NULL CHECK (avg_cost >= 0),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (portfolio_id, company_id)
);

CREATE INDEX idx_holdings_portfolio ON portfolio_holdings(portfolio_id);

-- ---------------------------------------------------------------------------
-- Watchlists
-- ---------------------------------------------------------------------------
CREATE TABLE watchlists (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, company_id)
);

-- ---------------------------------------------------------------------------
-- Recommendations / التوصيات مع تفسير SHAP
-- ---------------------------------------------------------------------------
CREATE TABLE recommendations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id      UUID NOT NULL REFERENCES companies(id),
    model_version   TEXT NOT NULL,
    horizon_days    SMALLINT NOT NULL DEFAULT 5
                        CHECK (horizon_days IN (5, 10, 20)),  -- أساسي 5 + اختياري 10/20
    action          recommendation_action NOT NULL,
    confidence      NUMERIC(5, 4) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    ensemble_score  NUMERIC(5, 4) NOT NULL,
    entry_price     NUMERIC(18, 4) NOT NULL,
    stop_loss       NUMERIC(18, 4) NOT NULL,       -- ATR × 2
    take_profit     NUMERIC(18, 4) NOT NULL,       -- R:R = 2.5:1
    atr_value       NUMERIC(18, 6),
    risk_reward     NUMERIC(6, 3) NOT NULL DEFAULT 2.500,
    shap_summary    JSONB NOT NULL DEFAULT '{}'::JSONB,
    explanation_ar  TEXT NOT NULL,
    status          recommendation_status NOT NULL DEFAULT 'active',
    generated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_reco_company_time ON recommendations(company_id, generated_at DESC);
CREATE INDEX idx_reco_horizon ON recommendations(company_id, horizon_days, generated_at DESC);
CREATE INDEX idx_reco_action_conf ON recommendations(action, confidence DESC)
    WHERE status = 'active';
CREATE INDEX idx_reco_shap ON recommendations USING GIN (shap_summary);

CREATE TABLE recommendation_outcomes (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recommendation_id   UUID NOT NULL UNIQUE REFERENCES recommendations(id),
    hit_target          BOOLEAN,
    return_pct          NUMERIC(10, 6),
    max_drawdown_pct    NUMERIC(10, 6),
    closed_at           TIMESTAMPTZ,
    notes               TEXT
);

-- ---------------------------------------------------------------------------
-- Audit Log — احتفاظ 5 سنوات (متطلب حوكمة / موافقة CMA المبدئية)
-- ---------------------------------------------------------------------------
CREATE TABLE audit_logs (
    id              BIGSERIAL PRIMARY KEY,
    user_id         UUID REFERENCES users(id),
    action          TEXT NOT NULL,
    resource        TEXT NOT NULL,
    ip_address      INET,
    user_agent      TEXT,
    details         JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_created ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_user ON audit_logs(user_id, created_at DESC);

COMMENT ON TABLE audit_logs IS 'Retention policy: 5 years (CMA governance); archive cold after active window';

-- ---------------------------------------------------------------------------
-- updated_at trigger
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_companies_updated BEFORE UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_portfolios_updated BEFORE UPDATE ON portfolios
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_holdings_updated BEFORE UPDATE ON portfolio_holdings
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
