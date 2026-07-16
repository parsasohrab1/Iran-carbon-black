-- Phase 2: quality process optimization, demand planning, supply price forecasts

CREATE TABLE IF NOT EXISTS quality.process_recommendations (
    id                  BIGSERIAL PRIMARY KEY,
    batch_id            VARCHAR(64) REFERENCES quality.batches(batch_id),
    grade               VARCHAR(32) NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    current_params      JSONB NOT NULL,
    recommended_params  JSONB NOT NULL,
    expected_defect_reduction DOUBLE PRECISION,
    model_version       VARCHAR(64),
    rationale           TEXT
);

CREATE TABLE IF NOT EXISTS quality.anomaly_events (
    id              BIGSERIAL PRIMARY KEY,
    batch_id        VARCHAR(64),
    grade           VARCHAR(32),
    detected_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    anomaly_score   DOUBLE PRECISION NOT NULL,
    is_anomaly      BOOLEAN NOT NULL,
    features        JSONB,
    model_version   VARCHAR(64),
    source          VARCHAR(32) DEFAULT 'api'
);

CREATE TABLE IF NOT EXISTS demand.production_plans (
    id                  BIGSERIAL PRIMARY KEY,
    plan_date           DATE NOT NULL DEFAULT CURRENT_DATE,
    product_grade       VARCHAR(32) NOT NULL,
    forecast_period     VARCHAR(32) NOT NULL,
    planned_quantity_kg DOUBLE PRECISION NOT NULL,
    safety_stock_kg     DOUBLE PRECISION NOT NULL,
    production_line     VARCHAR(64),
    start_date          DATE,
    status              VARCHAR(32) DEFAULT 'draft',
    margin_score        DOUBLE PRECISION,
    model_version       VARCHAR(64),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (plan_date, product_grade, forecast_period)
);

CREATE TABLE IF NOT EXISTS demand.grade_recommendations (
    id              BIGSERIAL PRIMARY KEY,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    customer_need   JSONB NOT NULL,
    recommended_grade VARCHAR(32) NOT NULL,
    score           DOUBLE PRECISION,
    alternatives    JSONB,
    model_version   VARCHAR(64)
);

CREATE TABLE IF NOT EXISTS supply.price_forecasts (
    id                  BIGSERIAL PRIMARY KEY,
    material            VARCHAR(255) NOT NULL,
    forecast_date       DATE NOT NULL DEFAULT CURRENT_DATE,
    horizon_days        INT NOT NULL,
    predicted_price_irr DOUBLE PRECISION NOT NULL,
    trend               VARCHAR(32),
    recommendation      VARCHAR(32),
    confidence          DOUBLE PRECISION,
    model_version       VARCHAR(64),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS supply.tender_scores (
    id              BIGSERIAL PRIMARY KEY,
    tender_id       VARCHAR(64) NOT NULL,
    supplier_id     VARCHAR(64) REFERENCES supply.suppliers(id),
    score           DOUBLE PRECISION NOT NULL,
    factors         JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
