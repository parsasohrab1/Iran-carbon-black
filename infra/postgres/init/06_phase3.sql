-- Phase 3: sales CRM, pricing, finance forecasts, ERP sync

CREATE TABLE IF NOT EXISTS sales.forecasts (
    id                      BIGSERIAL PRIMARY KEY,
    forecast_date           DATE NOT NULL DEFAULT CURRENT_DATE,
    grade                   VARCHAR(32),
    months_ahead            INT NOT NULL,
    forecast_quantity_kg    DOUBLE PRECISION NOT NULL,
    forecast_revenue_irr    DOUBLE PRECISION NOT NULL,
    recommended_unit_price  DOUBLE PRECISION,
    confidence              DOUBLE PRECISION,
    model_version           VARCHAR(64),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sales.price_recommendations (
    id                  BIGSERIAL PRIMARY KEY,
    grade               VARCHAR(32) NOT NULL,
    region              VARCHAR(32) NOT NULL DEFAULT 'domestic',
    current_price_irr   DOUBLE PRECISION,
    recommended_price_irr DOUBLE PRECISION NOT NULL,
    rationale           TEXT,
    model_version       VARCHAR(64),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sales.customer_profiles (
    customer_id         VARCHAR(64) PRIMARY KEY REFERENCES sales.customers(id),
    preferred_grades    JSONB DEFAULT '[]'::jsonb,
    avg_order_kg        DOUBLE PRECISION,
    last_order_date     DATE,
    churn_risk          DOUBLE PRECISION,
    lifetime_value_irr  DOUBLE PRECISION,
    needs               JSONB DEFAULT '{}'::jsonb,
    notes               TEXT,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sales.interactions (
    id              BIGSERIAL PRIMARY KEY,
    customer_id     VARCHAR(64) REFERENCES sales.customers(id),
    interaction_type VARCHAR(64) NOT NULL,
    subject         VARCHAR(255),
    detail          JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS finance.cashflow_forecasts (
    id                  BIGSERIAL PRIMARY KEY,
    forecast_date       DATE NOT NULL DEFAULT CURRENT_DATE,
    horizon_days        INT NOT NULL,
    projected_inflow    DOUBLE PRECISION NOT NULL,
    projected_outflow   DOUBLE PRECISION NOT NULL,
    net_cashflow        DOUBLE PRECISION NOT NULL,
    liquidity_risk      VARCHAR(32),
    recommendations     JSONB,
    model_version       VARCHAR(64),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS finance.ratio_snapshots (
    id              BIGSERIAL PRIMARY KEY,
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,
    ratios          JSONB NOT NULL,
    improvement_areas JSONB,
    model_version   VARCHAR(64),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE SCHEMA IF NOT EXISTS integration;

CREATE TABLE IF NOT EXISTS integration.erp_sync_log (
    id              BIGSERIAL PRIMARY KEY,
    direction       VARCHAR(16) NOT NULL, -- inbound | outbound
    entity_type     VARCHAR(64) NOT NULL,
    external_id     VARCHAR(128),
    payload         JSONB,
    status          VARCHAR(32) NOT NULL DEFAULT 'accepted',
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS integration.webhook_subscriptions (
    id              BIGSERIAL PRIMARY KEY,
    name            VARCHAR(128) NOT NULL,
    target_url      TEXT NOT NULL,
    event_types     JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
