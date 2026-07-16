-- Phase 4: security hardening, training, change management, SLA

ALTER TABLE platform.users
    ADD COLUMN IF NOT EXISTS failed_login_attempts INT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS locked_until TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMPTZ DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS platform.security_events (
    id              BIGSERIAL PRIMARY KEY,
    username        VARCHAR(64),
    event_type      VARCHAR(64) NOT NULL,
    detail          JSONB,
    ip_address      INET,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE SCHEMA IF NOT EXISTS training;

CREATE TABLE IF NOT EXISTS training.courses (
    id              VARCHAR(64) PRIMARY KEY,
    title           VARCHAR(255) NOT NULL,
    description     TEXT,
    domain          VARCHAR(64),
    duration_minutes INT NOT NULL DEFAULT 60,
    target_roles    JSONB DEFAULT '[]'::jsonb,
    is_mandatory    BOOLEAN NOT NULL DEFAULT FALSE,
    content_url     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS training.enrollments (
    id              BIGSERIAL PRIMARY KEY,
    course_id       VARCHAR(64) NOT NULL REFERENCES training.courses(id),
    user_id         UUID REFERENCES platform.users(id),
    username        VARCHAR(64) NOT NULL,
    status          VARCHAR(32) NOT NULL DEFAULT 'enrolled', -- enrolled|in_progress|completed
    progress_pct    DOUBLE PRECISION NOT NULL DEFAULT 0,
    enrolled_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    UNIQUE (course_id, username)
);

CREATE TABLE IF NOT EXISTS training.change_requests (
    id              BIGSERIAL PRIMARY KEY,
    title           VARCHAR(255) NOT NULL,
    description     TEXT,
    domain          VARCHAR(64),
    status          VARCHAR(32) NOT NULL DEFAULT 'proposed', -- proposed|accepted|rejected|deployed
    impact_level    VARCHAR(32) DEFAULT 'medium',
    created_by      VARCHAR(64),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decided_at      TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS training.acceptance_surveys (
    id              BIGSERIAL PRIMARY KEY,
    change_request_id BIGINT REFERENCES training.change_requests(id),
    username        VARCHAR(64) NOT NULL,
    acceptance_score INT NOT NULL CHECK (acceptance_score BETWEEN 1 AND 5),
    feedback        TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE SCHEMA IF NOT EXISTS ops;

CREATE TABLE IF NOT EXISTS ops.service_heartbeats (
    service_name    VARCHAR(64) NOT NULL,
    checked_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status          VARCHAR(32) NOT NULL,
    latency_ms      DOUBLE PRECISION,
    detail          JSONB,
    PRIMARY KEY (service_name, checked_at)
);

SELECT create_hypertable('ops.service_heartbeats', 'checked_at', if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS ops.sla_daily (
    day             DATE PRIMARY KEY,
    availability_pct DOUBLE PRECISION NOT NULL,
    checks_total    INT NOT NULL,
    checks_failed   INT NOT NULL,
    rto_seconds     INT DEFAULT 7200,
    rpo_seconds     INT DEFAULT 3600,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS ops.backup_runs (
    id              BIGSERIAL PRIMARY KEY,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    status          VARCHAR(32) NOT NULL DEFAULT 'running',
    backup_path     TEXT,
    size_bytes      BIGINT,
    components      JSONB,
    error_message   TEXT
);
