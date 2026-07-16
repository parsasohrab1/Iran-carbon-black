-- Phase 1: predictive maintenance alerts + energy source decisions

CREATE TABLE IF NOT EXISTS energy.maintenance_alerts (
    id              BIGSERIAL PRIMARY KEY,
    equipment_id    VARCHAR(64) NOT NULL REFERENCES energy.equipment(id),
    alert_type      VARCHAR(64) NOT NULL DEFAULT 'rul_threshold',
    severity        VARCHAR(32) NOT NULL DEFAULT 'warning',
    rul_days        DOUBLE PRECISION,
    failure_probability DOUBLE PRECISION,
    message         TEXT NOT NULL,
    prediction_id   BIGINT REFERENCES energy.rul_predictions(id),
    acknowledged    BOOLEAN NOT NULL DEFAULT FALSE,
    acknowledged_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_maintenance_alerts_open
    ON energy.maintenance_alerts (equipment_id, created_at DESC)
    WHERE acknowledged = FALSE;

CREATE TABLE IF NOT EXISTS energy.tariffs (
    id              SERIAL PRIMARY KEY,
    source          VARCHAR(32) NOT NULL UNIQUE, -- grid | generator
    price_irr_per_kwh DOUBLE PRECISION NOT NULL,
    peak_multiplier DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    peak_hours_start INT NOT NULL DEFAULT 18,
    peak_hours_end   INT NOT NULL DEFAULT 22,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO energy.tariffs (source, price_irr_per_kwh, peak_multiplier, peak_hours_start, peak_hours_end)
VALUES
    ('grid', 4500, 1.6, 18, 22),
    ('generator', 8200, 1.0, 0, 0)
ON CONFLICT (source) DO NOTHING;

CREATE TABLE IF NOT EXISTS energy.source_decisions (
    id              BIGSERIAL PRIMARY KEY,
    decided_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    line_id         VARCHAR(64) NOT NULL,
    recommended_source VARCHAR(32) NOT NULL,
    grid_cost_irr_per_kwh DOUBLE PRECISION,
    generator_cost_irr_per_kwh DOUBLE PRECISION,
    expected_kwh    DOUBLE PRECISION,
    estimated_saving_irr DOUBLE PRECISION,
    reason          TEXT,
    is_peak         BOOLEAN DEFAULT FALSE
);

-- Seed consumption history for pilot dashboards (last 48h)
INSERT INTO energy.energy_consumption (time, line_id, source, kwh, cost_irr, price_forecast)
SELECT
    NOW() - (g || ' hours')::interval,
    CASE WHEN g % 2 = 0 THEN 'Line_1' ELSE 'UTIL' END,
    CASE
        WHEN EXTRACT(HOUR FROM NOW() - (g || ' hours')::interval) BETWEEN 18 AND 21 THEN 'generator'
        ELSE 'grid'
    END,
    80 + random() * 40,
    NULL,
    NULL
FROM generate_series(0, 47) AS g;
