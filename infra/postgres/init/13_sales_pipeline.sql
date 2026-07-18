-- Sales pipeline: active/potential customers + purchase queue

ALTER TABLE sales.customers
    ADD COLUMN IF NOT EXISTS status VARCHAR(32) DEFAULT 'active',
    ADD COLUMN IF NOT EXISTS monthly_tonnage_kg DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS contact_person VARCHAR(255),
    ADD COLUMN IF NOT EXISTS notes TEXT;

COMMENT ON COLUMN sales.customers.status IS 'active | potential';

CREATE TABLE IF NOT EXISTS sales.purchase_queue (
    id                  BIGSERIAL PRIMARY KEY,
    customer_id         VARCHAR(64) NOT NULL REFERENCES sales.customers(id),
    grade               VARCHAR(32) NOT NULL,
    requested_tonnage_kg DOUBLE PRECISION NOT NULL,
    priority            INT NOT NULL DEFAULT 3,
    status              VARCHAR(32) NOT NULL DEFAULT 'queued',
    expected_close_date DATE,
    unit_price_irr      DOUBLE PRECISION,
    probability         DOUBLE PRECISION DEFAULT 0.6,
    source              VARCHAR(64) DEFAULT 'crm',
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_purchase_queue_status ON sales.purchase_queue(status);
CREATE INDEX IF NOT EXISTS idx_purchase_queue_grade ON sales.purchase_queue(grade);
CREATE INDEX IF NOT EXISTS idx_customers_status ON sales.customers(status);
