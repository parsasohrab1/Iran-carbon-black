-- Phase 5: MLOps registry, inventory optimization, benefits tracking

CREATE SCHEMA IF NOT EXISTS maturity;

CREATE TABLE IF NOT EXISTS maturity.model_registry (
    id              BIGSERIAL PRIMARY KEY,
    domain          VARCHAR(64) NOT NULL, -- energy|quality|demand|supply|sales|finance
    model_name      VARCHAR(128) NOT NULL,
    version         VARCHAR(64) NOT NULL,
    artifact_uri    TEXT,
    metrics         JSONB DEFAULT '{}'::jsonb,
    status          VARCHAR(32) NOT NULL DEFAULT 'staged', -- staged|production|retired
    trained_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    promoted_at     TIMESTAMPTZ,
    created_by      VARCHAR(64) DEFAULT 'mlops',
    UNIQUE (domain, model_name, version)
);

CREATE TABLE IF NOT EXISTS maturity.retrain_jobs (
    id              BIGSERIAL PRIMARY KEY,
    domain          VARCHAR(64) NOT NULL,
    status          VARCHAR(32) NOT NULL DEFAULT 'queued', -- queued|running|succeeded|failed
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    metrics         JSONB,
    artifact_uri    TEXT,
    error_message   TEXT,
    trigger_source  VARCHAR(64) DEFAULT 'scheduler',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS maturity.inventory_positions (
    product_grade   VARCHAR(32) PRIMARY KEY,
    on_hand_kg      DOUBLE PRECISION NOT NULL DEFAULT 0,
    safety_stock_kg DOUBLE PRECISION NOT NULL DEFAULT 0,
    reorder_point_kg DOUBLE PRECISION NOT NULL DEFAULT 0,
    target_days_cover INT NOT NULL DEFAULT 21,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS maturity.inventory_actions (
    id              BIGSERIAL PRIMARY KEY,
    product_grade   VARCHAR(32) NOT NULL,
    action          VARCHAR(64) NOT NULL, -- produce|hold|drawdown|expedite
    quantity_kg     DOUBLE PRECISION,
    reason          TEXT,
    expected_saving_irr DOUBLE PRECISION,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS maturity.grade_portfolio (
    product_grade   VARCHAR(32) PRIMARY KEY,
    margin_score    DOUBLE PRECISION NOT NULL,
    strategic_flag  BOOLEAN NOT NULL DEFAULT FALSE,
    specialty_tag   VARCHAR(64),
    target_share_pct DOUBLE PRECISION,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS maturity.benefits_ledger (
    id              BIGSERIAL PRIMARY KEY,
    period_month    DATE NOT NULL,
    category        VARCHAR(64) NOT NULL,
    -- emergency_maintenance|energy|quality_waste|pricing_sales|procurement|demand_driven
    amount_irr      DOUBLE PRECISION NOT NULL,
    maturity_factor DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    source          VARCHAR(64) DEFAULT 'model',
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (period_month, category)
);

CREATE TABLE IF NOT EXISTS maturity.roi_snapshots (
    id              BIGSERIAL PRIMARY KEY,
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,
    annual_benefits_irr DOUBLE PRECISION NOT NULL,
    annual_opex_irr DOUBLE PRECISION NOT NULL DEFAULT 36000000000,
    cumulative_capex_irr DOUBLE PRECISION NOT NULL DEFAULT 141000000000,
    net_annual_irr  DOUBLE PRECISION NOT NULL,
    payback_months  DOUBLE PRECISION,
    npv_proxy_irr   DOUBLE PRECISION,
    maturity_pct    DOUBLE PRECISION,
    details         JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
