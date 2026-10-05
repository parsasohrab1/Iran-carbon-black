-- Seed synthetic / reference data aligned with SRS appendix samples

INSERT INTO supply.suppliers (id, name, rating, delivery_reliability, quality_rating) VALUES
    ('SUP-0012', 'Tabriz Petrochemical', 4.2, 0.92, 4.5),
    ('SUP-0003', 'Isfahan Refinery', 4.0, 0.88, 4.1),
    ('SUP-0008', 'Bandar Imam Petrochemical', 3.8, 0.85, 4.0)
ON CONFLICT DO NOTHING;

INSERT INTO sales.customers (id, name, segment, industry, annual_consumption_kg, region) VALUES
    ('CUST-0047', 'Sahand Tire', 'tire_manufacturer', 'tire', 180000, 'domestic'),
    ('CUST-0012', 'Barez Rubber', 'tire_manufacturer', 'tire', 220000, 'domestic'),
    ('CUST-0099', 'Export Partner UAE', 'distributor', 'rubber', 95000, 'export')
ON CONFLICT DO NOTHING;

INSERT INTO demand.historical_demand (month, product_grade, quantity_kg) VALUES
    ('2026-01-01', 'N220', 165000),
    ('2026-02-01', 'N220', 172000),
    ('2026-03-01', 'N220', 168000),
    ('2026-04-01', 'N220', 175000),
    ('2026-05-01', 'N220', 180000),
    ('2026-06-01', 'N220', 178000),
    ('2026-01-01', 'N330', 210000),
    ('2026-02-01', 'N330', 205000),
    ('2026-03-01', 'N330', 215000),
    ('2026-04-01', 'N330', 220000),
    ('2026-05-01', 'N330', 218000),
    ('2026-06-01', 'N330', 225000)
ON CONFLICT DO NOTHING;

INSERT INTO supply.price_history (time, material, price_irr, source) VALUES
    ('2026-01-15', 'Coal tar (furfural extract)', 38000, 'market'),
    ('2026-02-15', 'Coal tar (furfural extract)', 39500, 'market'),
    ('2026-03-15', 'Coal tar (furfural extract)', 41000, 'market'),
    ('2026-04-15', 'Coal tar (furfural extract)', 40500, 'market'),
    ('2026-05-15', 'Coal tar (furfural extract)', 41800, 'market'),
    ('2026-06-15', 'Coal tar (furfural extract)', 42500, 'market');

INSERT INTO sales.orders (sale_date, customer_id, grade, quantity_kg, unit_price_irr, total_price_irr, region, economic_indicators) VALUES
    ('2026-07-15', 'CUST-0047', 'N330', 24500, 185000, 4532500000, 'domestic',
     '{"usd_irr_rate":245000,"crude_oil_price_usd":78.5,"inflation_rate":35.2,"tire_production_index":112.5}'::jsonb),
    ('2026-06-20', 'CUST-0012', 'N220', 18000, 195000, 3510000000, 'domestic',
     '{"usd_irr_rate":240000,"crude_oil_price_usd":76.0,"inflation_rate":34.8}'::jsonb),
    ('2026-05-10', 'CUST-0099', 'N550', 12000, 160000, 1920000000, 'export',
     '{"usd_irr_rate":238000,"crude_oil_price_usd":74.5}'::jsonb);

INSERT INTO finance.daily_reports (
    report_date, revenue_ytd, cost_of_goods_sold, gross_profit, operating_expenses,
    net_profit, current_ratio, debt_to_equity, inventory_turnover, profit_margin,
    operational_kpis, forecast
) VALUES (
    '2026-07-16',
    245000000000, 195000000000, 50000000000, 32000000000,
    18000000000, 1.2, 2.8, 4.5, 0.073,
    '{"production_volume_kg":42500,"capacity_utilization":0.85,"defect_rate":0.023,"downtime_hours":12.5,"grade_mix_efficiency":0.78}'::jsonb,
    '{"next_month_revenue":42000000000,"next_month_production":45000,"risk_level":"moderate"}'::jsonb
) ON CONFLICT DO NOTHING;

-- Sample sensor readings for GEN-001 (predictive maintenance demos)
INSERT INTO energy.sensor_readings (
    time, equipment_id, vibration_x, vibration_y, vibration_z,
    temperature, pressure, current_draw, oil_pressure, coolant_temp
)
SELECT
    NOW() - (g || ' minutes')::interval,
    'GEN-001',
    2.1 + random(),
    1.6 + random(),
    2.8 + random() * 1.5,
    72 + random() * 12,
    11 + random() * 2,
    140 + random() * 20,
    4.5 + random() * 0.6,
    60 + random() * 10
FROM generate_series(0, 59) AS g;
