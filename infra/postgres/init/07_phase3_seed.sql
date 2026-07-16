-- Phase 3 seed: richer sales history, CRM profiles, ERP webhook stub

INSERT INTO sales.customers (id, name, segment, industry, annual_consumption_kg, region) VALUES
    ('CUST-0021', 'کویر تایر', 'tire_manufacturer', 'tire', 150000, 'domestic'),
    ('CUST-0033', 'ایران تایر', 'tire_manufacturer', 'tire', 195000, 'domestic'),
    ('CUST-0055', 'RubberTech TR', 'compounder', 'rubber', 60000, 'export'),
    ('CUST-0070', 'Cable Poly Iran', 'industrial', 'cable', 40000, 'domestic')
ON CONFLICT DO NOTHING;

-- Synthetic monthly-ish sales over ~18 months for key grades
INSERT INTO sales.orders (sale_date, customer_id, grade, quantity_kg, unit_price_irr, total_price_irr, region, economic_indicators)
SELECT
    (DATE '2025-01-05' + (m * 10 || ' days')::interval)::date,
    (ARRAY['CUST-0047','CUST-0012','CUST-0021','CUST-0033','CUST-0099'])[1 + (m % 5)],
    (ARRAY['N220','N330','N550','N660','N234'])[1 + (m % 5)],
    8000 + (random() * 18000)::int,
    160000 + (m * 800)::int + (random() * 5000)::int,
    0,
    CASE WHEN m % 7 = 0 THEN 'export' ELSE 'domestic' END,
    jsonb_build_object(
        'usd_irr_rate', 230000 + m * 800,
        'crude_oil_price_usd', 72 + (m % 10),
        'inflation_rate', 32 + (m % 5),
        'tire_production_index', 100 + m
    )
FROM generate_series(0, 53) AS m;

UPDATE sales.orders
SET total_price_irr = quantity_kg * unit_price_irr
WHERE total_price_irr = 0 OR total_price_irr IS NULL;

INSERT INTO sales.customer_profiles (customer_id, preferred_grades, avg_order_kg, churn_risk, lifetime_value_irr, needs, notes)
VALUES
    ('CUST-0047', '["N330","N220"]'::jsonb, 20000, 0.18, 12000000000, '{"conductivity":"medium","dispersion":"high"}'::jsonb, 'Key domestic tire account'),
    ('CUST-0012', '["N220","N234"]'::jsonb, 18000, 0.12, 15000000000, '{"conductivity":"high","tint_strength":"high"}'::jsonb, 'Growing offtake'),
    ('CUST-0021', '["N550","N660"]'::jsonb, 12000, 0.25, 7000000000, '{"dispersion":"very_high"}'::jsonb, 'Price sensitive'),
    ('CUST-0033', '["N330","N339"]'::jsonb, 16000, 0.15, 11000000000, '{"conductivity":"medium"}'::jsonb, 'Strategic account'),
    ('CUST-0099', '["N550"]'::jsonb, 10000, 0.30, 5000000000, '{"region":"export"}'::jsonb, 'Export distributor')
ON CONFLICT DO NOTHING;

INSERT INTO integration.webhook_subscriptions (name, target_url, event_types)
SELECT * FROM (VALUES
    ('ERP-Sales-Mirror', 'http://erp.local/hooks/icb-sales', '["sales.order.created","sales.forecast.ready"]'::jsonb),
    ('ERP-Finance-Mirror', 'http://erp.local/hooks/icb-finance', '["finance.report.upserted","finance.cashflow.ready"]'::jsonb)
) AS v(name, target_url, event_types)
WHERE NOT EXISTS (SELECT 1 FROM integration.webhook_subscriptions w WHERE w.name = v.name);
