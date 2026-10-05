-- Export markets schema (Iran Carbon Black / Shekarbon)

CREATE TABLE IF NOT EXISTS sales.export_markets (
    id                  VARCHAR(8) PRIMARY KEY,
    country_fa          VARCHAR(128) NOT NULL,
    country_en          VARCHAR(128),
    status              VARCHAR(32) NOT NULL DEFAULT 'actual',
    region              VARCHAR(64),
    annual_tonnage_kg   DOUBLE PRECISION NOT NULL DEFAULT 0,
    ytd_tonnage_kg      DOUBLE PRECISION NOT NULL DEFAULT 0,
    share_pct           DOUBLE PRECISION DEFAULT 0,
    main_grades         TEXT[],
    avg_fob_usd         DOUBLE PRECISION,
    growth_yoy_pct      DOUBLE PRECISION,
    buyers              TEXT,
    logistics           TEXT,
    risk                TEXT,
    pipeline_stage      VARCHAR(64),
    probability         DOUBLE PRECISION,
    source_refs         TEXT[],
    notes               TEXT,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON COLUMN sales.export_markets.status IS 'actual | potential';

CREATE TABLE IF NOT EXISTS sales.export_forecasts (
    id                      BIGSERIAL PRIMARY KEY,
    forecast_month          DATE NOT NULL,
    baseline_tonnage_kg     DOUBLE PRECISION NOT NULL,
    pipeline_uplift_kg      DOUBLE PRECISION NOT NULL DEFAULT 0,
    forecast_tonnage_kg     DOUBLE PRECISION NOT NULL,
    forecast_revenue_usd    DOUBLE PRECISION,
    forecast_revenue_irr    DOUBLE PRECISION,
    avg_fob_usd             DOUBLE PRECISION,
    confidence              DOUBLE PRECISION,
    model_version           VARCHAR(64) DEFAULT 'export-forecast-v1',
    source                  VARCHAR(128) DEFAULT 'dashboard',
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (forecast_month, model_version)
);

CREATE INDEX IF NOT EXISTS idx_export_markets_status ON sales.export_markets(status);
CREATE INDEX IF NOT EXISTS idx_export_forecasts_month ON sales.export_forecasts(forecast_month);
