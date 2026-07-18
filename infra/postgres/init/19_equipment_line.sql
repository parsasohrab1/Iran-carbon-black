-- Production-line equipment catalog tables + process range alerts

ALTER TABLE energy.equipment
    ADD COLUMN IF NOT EXISTS name_fa VARCHAR(255),
    ADD COLUMN IF NOT EXISTS area VARCHAR(64);

CREATE TABLE IF NOT EXISTS energy.sensor_defs (
    id              BIGSERIAL PRIMARY KEY,
    equipment_id    VARCHAR(64) NOT NULL REFERENCES energy.equipment(id) ON DELETE CASCADE,
    sensor_key      VARCHAR(64) NOT NULL,
    name_fa         VARCHAR(255) NOT NULL,
    unit            VARCHAR(32) NOT NULL,
    min_op          DOUBLE PRECISION NOT NULL,
    max_op          DOUBLE PRECISION NOT NULL,
    channel         VARCHAR(64),
    criticality     VARCHAR(32) DEFAULT 'high',
    UNIQUE (equipment_id, sensor_key)
);

CREATE TABLE IF NOT EXISTS energy.process_alerts (
    id              BIGSERIAL PRIMARY KEY,
    equipment_id    VARCHAR(64) NOT NULL REFERENCES energy.equipment(id),
    sensor_key      VARCHAR(64) NOT NULL,
    severity        VARCHAR(32) NOT NULL,
    measured_value  DOUBLE PRECISION,
    min_op          DOUBLE PRECISION,
    max_op          DOUBLE PRECISION,
    unit            VARCHAR(32),
    message         TEXT NOT NULL,
    acknowledged    BOOLEAN NOT NULL DEFAULT FALSE,
    acknowledged_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_process_alerts_open
    ON energy.process_alerts (acknowledged, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sensor_defs_eq
    ON energy.sensor_defs (equipment_id);
