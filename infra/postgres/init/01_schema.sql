-- Iran Carbon Black — initial schema (TimescaleDB)
-- Domains: energy, supply, quality, sales, finance, demand + platform auth

CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ─── Platform / Auth ───────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS platform;

CREATE TABLE platform.users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username        VARCHAR(64) UNIQUE NOT NULL,
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    full_name       VARCHAR(255),
    role            VARCHAR(64) NOT NULL DEFAULT 'operator',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    totp_secret     TEXT,
    totp_enabled    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE platform.audit_log (
    id          BIGSERIAL PRIMARY KEY,
    user_id     UUID REFERENCES platform.users(id),
    action      VARCHAR(128) NOT NULL,
    resource    VARCHAR(255),
    detail      JSONB,
    ip_address  INET,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Energy / Facilities (Domain 1) ────────────────────────
CREATE SCHEMA IF NOT EXISTS energy;

CREATE TABLE energy.equipment (
    id              VARCHAR(64) PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    equipment_type  VARCHAR(64) NOT NULL,
    location        VARCHAR(255),
    line_id         VARCHAR(64),
    status          VARCHAR(32) DEFAULT 'running',
    installed_at    DATE,
    metadata        JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE energy.sensor_readings (
    time            TIMESTAMPTZ NOT NULL,
    equipment_id    VARCHAR(64) NOT NULL REFERENCES energy.equipment(id),
    vibration_x     DOUBLE PRECISION,
    vibration_y     DOUBLE PRECISION,
    vibration_z     DOUBLE PRECISION,
    temperature     DOUBLE PRECISION,
    pressure        DOUBLE PRECISION,
    current_draw    DOUBLE PRECISION,
    oil_pressure    DOUBLE PRECISION,
    coolant_temp    DOUBLE PRECISION,
    raw             JSONB
);

SELECT create_hypertable('energy.sensor_readings', 'time', if_not_exists => TRUE);

CREATE TABLE energy.rul_predictions (
    id              BIGSERIAL PRIMARY KEY,
    equipment_id    VARCHAR(64) NOT NULL REFERENCES energy.equipment(id),
    predicted_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    rul_days        DOUBLE PRECISION NOT NULL,
    failure_probability DOUBLE PRECISION,
    model_version   VARCHAR(64),
    alert_issued    BOOLEAN DEFAULT FALSE
);

CREATE TABLE energy.energy_consumption (
    time            TIMESTAMPTZ NOT NULL,
    line_id         VARCHAR(64) NOT NULL,
    source          VARCHAR(32) NOT NULL, -- grid | generator
    kwh             DOUBLE PRECISION NOT NULL,
    cost_irr        DOUBLE PRECISION,
    price_forecast  DOUBLE PRECISION
);

SELECT create_hypertable('energy.energy_consumption', 'time', if_not_exists => TRUE);

-- ─── Supply Chain (Domain 2) ───────────────────────────────
CREATE SCHEMA IF NOT EXISTS supply;

CREATE TABLE supply.suppliers (
    id                      VARCHAR(64) PRIMARY KEY,
    name                    VARCHAR(255) NOT NULL,
    rating                  DOUBLE PRECISION,
    delivery_reliability    DOUBLE PRECISION,
    quality_rating          DOUBLE PRECISION,
    metadata                JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE supply.purchase_orders (
    id              VARCHAR(64) PRIMARY KEY,
    material        VARCHAR(255) NOT NULL,
    supplier_id     VARCHAR(64) REFERENCES supply.suppliers(id),
    quantity_kg     DOUBLE PRECISION NOT NULL,
    unit_price_irr  DOUBLE PRECISION NOT NULL,
    total_price_irr DOUBLE PRECISION NOT NULL,
    delivery_date   DATE,
    market_benchmark JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE supply.price_history (
    time            TIMESTAMPTZ NOT NULL,
    material        VARCHAR(255) NOT NULL,
    price_irr       DOUBLE PRECISION NOT NULL,
    source          VARCHAR(64)
);

SELECT create_hypertable('supply.price_history', 'time', if_not_exists => TRUE);

-- ─── Production / Quality (Domain 3) ───────────────────────
CREATE SCHEMA IF NOT EXISTS quality;

CREATE TABLE quality.batches (
    batch_id            VARCHAR(64) PRIMARY KEY,
    production_line     INT NOT NULL,
    grade               VARCHAR(32) NOT NULL,
    started_at          TIMESTAMPTZ NOT NULL,
    finished_at         TIMESTAMPTZ,
    status              VARCHAR(32) DEFAULT 'in_progress'
);

CREATE TABLE quality.process_readings (
    time                TIMESTAMPTZ NOT NULL,
    batch_id            VARCHAR(64) NOT NULL REFERENCES quality.batches(batch_id),
    reactor_temp        DOUBLE PRECISION,
    feed_rate           DOUBLE PRECISION,
    air_flow            DOUBLE PRECISION,
    residence_time      DOUBLE PRECISION,
    pressure            DOUBLE PRECISION,
    oil_to_air_ratio    DOUBLE PRECISION,
    raw                 JSONB
);

SELECT create_hypertable('quality.process_readings', 'time', if_not_exists => TRUE);

CREATE TABLE quality.quality_metrics (
    time                TIMESTAMPTZ NOT NULL,
    batch_id            VARCHAR(64) NOT NULL REFERENCES quality.batches(batch_id),
    iodine_absorption   DOUBLE PRECISION,
    dbp_absorption      DOUBLE PRECISION,
    surface_area        DOUBLE PRECISION,
    particle_size       DOUBLE PRECISION,
    tint_strength       DOUBLE PRECISION,
    anomaly_score       DOUBLE PRECISION,
    is_anomaly          BOOLEAN DEFAULT FALSE
);

SELECT create_hypertable('quality.quality_metrics', 'time', if_not_exists => TRUE);

-- ─── Sales (Domain 4) ──────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS sales;

CREATE TABLE sales.customers (
    id                      VARCHAR(64) PRIMARY KEY,
    name                    VARCHAR(255) NOT NULL,
    segment                 VARCHAR(64),
    industry                VARCHAR(64),
    annual_consumption_kg   DOUBLE PRECISION,
    region                  VARCHAR(64)
);

CREATE TABLE sales.orders (
    id                  BIGSERIAL PRIMARY KEY,
    sale_date           DATE NOT NULL,
    customer_id         VARCHAR(64) REFERENCES sales.customers(id),
    grade               VARCHAR(32) NOT NULL,
    quantity_kg         DOUBLE PRECISION NOT NULL,
    unit_price_irr      DOUBLE PRECISION NOT NULL,
    total_price_irr     DOUBLE PRECISION NOT NULL,
    region              VARCHAR(32),
    economic_indicators JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Finance (Domain 5) ────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS finance;

CREATE TABLE finance.daily_reports (
    report_date         DATE PRIMARY KEY,
    revenue_ytd         DOUBLE PRECISION,
    cost_of_goods_sold  DOUBLE PRECISION,
    gross_profit        DOUBLE PRECISION,
    operating_expenses  DOUBLE PRECISION,
    net_profit          DOUBLE PRECISION,
    current_ratio       DOUBLE PRECISION,
    debt_to_equity      DOUBLE PRECISION,
    inventory_turnover  DOUBLE PRECISION,
    profit_margin       DOUBLE PRECISION,
    operational_kpis    JSONB,
    forecast            JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Demand-driven production (Domain 7) ───────────────────
CREATE SCHEMA IF NOT EXISTS demand;

CREATE TABLE demand.forecasts (
    id                      BIGSERIAL PRIMARY KEY,
    forecast_date           DATE NOT NULL,
    product_grade           VARCHAR(32) NOT NULL,
    forecast_period         VARCHAR(32) NOT NULL,
    forecast_quantity_kg    DOUBLE PRECISION NOT NULL,
    confidence_lower        DOUBLE PRECISION,
    confidence_upper        DOUBLE PRECISION,
    confidence_level        DOUBLE PRECISION DEFAULT 0.90,
    influencing_factors     JSONB,
    recommended_production  JSONB,
    model_version           VARCHAR(64),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (forecast_date, product_grade, forecast_period)
);

CREATE TABLE demand.historical_demand (
    month           DATE NOT NULL,
    product_grade   VARCHAR(32) NOT NULL,
    quantity_kg     DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (month, product_grade)
);

-- ─── Seed minimal reference data ───────────────────────────
INSERT INTO energy.equipment (id, name, equipment_type, location, line_id) VALUES
    ('GEN-001', 'Generator Unit 1', 'generator', 'Power House', 'UTIL'),
    ('CMP-001', 'Compressor A', 'compressor', 'Utility Bay', 'UTIL'),
    ('FUR-001', 'Furnace Line 1', 'furnace', 'Reactor Hall', 'Line_1'),
    ('CLR-001', 'Vertical Cooler 38m', 'cooler', 'Cooling Tower', 'Line_1')
ON CONFLICT DO NOTHING;

INSERT INTO platform.users (username, email, password_hash, full_name, role)
VALUES (
    'admin',
    'admin@carbon-iran.local',
    '$2b$12$rbCoU4Unp/GQt1Pr6fH8ouCvagpwyXfphXIbNGNL8gh/hhrxzZZsO',
    'System Administrator',
    'admin'
) ON CONFLICT DO NOTHING;
