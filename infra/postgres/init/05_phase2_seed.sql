-- Phase 2 seed: 12 carbon black grades demand history + richer supply prices

INSERT INTO demand.historical_demand (month, product_grade, quantity_kg)
SELECT
    (DATE '2025-01-01' + (m || ' months')::interval)::date,
    g.grade,
    (g.base * (1 + 0.02 * sin(m / 2.0) + (random() - 0.5) * 0.06))::int
FROM generate_series(0, 17) AS m
CROSS JOIN (
    VALUES
        ('N110', 95000),
        ('N115', 88000),
        ('N220', 170000),
        ('N234', 125000),
        ('N330', 215000),
        ('N339', 140000),
        ('N347', 110000),
        ('N550', 160000),
        ('N660', 98000),
        ('N762', 72000),
        ('N774', 85000),
        ('N990', 45000)
) AS g(grade, base)
ON CONFLICT DO NOTHING;

-- Additional feedstock price history (weekly-ish over 24 points)
INSERT INTO supply.price_history (time, material, price_irr, source)
SELECT
    TIMESTAMP '2025-01-01' + (w || ' weeks')::interval,
    'Coal tar (furfural extract)',
    36000 + w * 280 + (random() * 800)::int,
    'market'
FROM generate_series(0, 23) AS w;

INSERT INTO supply.price_history (time, material, price_irr, source)
SELECT
    TIMESTAMP '2025-01-01' + (w || ' weeks')::interval,
    'Naphtha',
    52000 + w * 310 + (random() * 1000)::int,
    'market'
FROM generate_series(0, 23) AS w;

-- Sample quality batches for anomaly / optimization demos
INSERT INTO quality.batches (batch_id, production_line, grade, started_at, status) VALUES
    ('CB-2026-07-16-0042', 1, 'N220', NOW() - INTERVAL '2 hours', 'in_progress'),
    ('CB-2026-07-16-0043', 2, 'N330', NOW() - INTERVAL '90 minutes', 'in_progress'),
    ('CB-2026-07-16-0044', 1, 'N550', NOW() - INTERVAL '1 hour', 'in_progress')
ON CONFLICT DO NOTHING;

INSERT INTO quality.process_readings (
    time, batch_id, reactor_temp, feed_rate, air_flow, residence_time, pressure, oil_to_air_ratio
)
SELECT
    NOW() - (g || ' minutes')::interval,
    'CB-2026-07-16-0042',
    1410 + random() * 30,
    2.3 + random() * 0.3,
    17.5 + random() * 2,
    2.1 + random() * 0.4,
    1.35 + random() * 0.2,
    0.72 + random() * 0.12
FROM generate_series(0, 29) AS g;

INSERT INTO quality.quality_metrics (
    time, batch_id, iodine_absorption, dbp_absorption, surface_area, particle_size, tint_strength
)
SELECT
    NOW() - (g || ' minutes')::interval,
    'CB-2026-07-16-0042',
    80 + random() * 6,
    110 + random() * 12,
    74 + random() * 8,
    20 + random() * 5,
    110 + random() * 15
FROM generate_series(0, 29) AS g;
