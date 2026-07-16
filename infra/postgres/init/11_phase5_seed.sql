-- Phase 5 seed: inventory, specialty grades, baseline benefits toward 200B IRR/year

INSERT INTO maturity.inventory_positions (product_grade, on_hand_kg, safety_stock_kg, reorder_point_kg, target_days_cover) VALUES
    ('N110', 42000, 12000, 25000, 25),
    ('N115', 38000, 11000, 23000, 25),
    ('N220', 95000, 20000, 45000, 21),
    ('N234', 52000, 15000, 30000, 21),
    ('N330', 120000, 25000, 55000, 18),
    ('N339', 48000, 14000, 28000, 21),
    ('N347', 40000, 12000, 25000, 21),
    ('N550', 88000, 18000, 40000, 18),
    ('N660', 35000, 10000, 22000, 20),
    ('N762', 22000, 8000, 16000, 20),
    ('N774', 26000, 9000, 18000, 20),
    ('N990', 15000, 5000, 10000, 25)
ON CONFLICT DO NOTHING;

INSERT INTO maturity.grade_portfolio (product_grade, margin_score, strategic_flag, specialty_tag, target_share_pct, notes) VALUES
    ('N110', 0.12, TRUE, 'conductive_specialty', 8, 'High-margin conductive applications'),
    ('N115', 0.11, TRUE, 'conductive_specialty', 6, 'Specialty tire / industrial'),
    ('N220', 0.10, TRUE, 'reinforcing', 14, 'Core reinforcing grade'),
    ('N234', 0.105, TRUE, 'reinforcing', 10, 'High-structure reinforcing'),
    ('N330', 0.09, FALSE, 'general', 18, 'Volume workhorse'),
    ('N339', 0.095, TRUE, 'reinforcing', 9, 'Improved margin vs N330'),
    ('N347', 0.092, FALSE, 'reinforcing', 7, 'Balanced portfolio'),
    ('N550', 0.08, FALSE, 'semi_reinforcing', 12, 'Semi-reinforcing volume'),
    ('N660', 0.075, FALSE, 'carcass', 6, 'Carcass / mechanical rubber'),
    ('N762', 0.07, FALSE, 'carcass', 4, 'Lower margin carcass'),
    ('N774', 0.072, FALSE, 'carcass', 4, 'Lower margin carcass'),
    ('N990', 0.06, FALSE, 'thermal', 2, 'Thermal black niche')
ON CONFLICT DO NOTHING;

-- Maturity ramp benefits (proposal annual target 200B IRR at full maturity)
INSERT INTO maturity.benefits_ledger (period_month, category, amount_irr, maturity_factor, notes) VALUES
    ('2026-01-01', 'emergency_maintenance', 8000000000, 0.35, 'Phase1 RUL pilot'),
    ('2026-01-01', 'energy', 9000000000, 0.35, 'Grid vs generator decisions'),
    ('2026-01-01', 'quality_waste', 5000000000, 0.35, 'Anomaly catch rate'),
    ('2026-01-01', 'pricing_sales', 6000000000, 0.35, 'Pricing recommendations'),
    ('2026-01-01', 'procurement', 4000000000, 0.35, 'Buy-timing advice'),
    ('2026-01-01', 'demand_driven', 7000000000, 0.35, 'Inventory + grade mix'),
    ('2026-04-01', 'emergency_maintenance', 15000000000, 0.55, NULL),
    ('2026-04-01', 'energy', 18000000000, 0.55, NULL),
    ('2026-04-01', 'quality_waste', 11000000000, 0.55, NULL),
    ('2026-04-01', 'pricing_sales', 14000000000, 0.55, NULL),
    ('2026-04-01', 'procurement', 8000000000, 0.55, NULL),
    ('2026-04-01', 'demand_driven', 15000000000, 0.55, NULL),
    ('2026-07-01', 'emergency_maintenance', 28000000000, 0.80, NULL),
    ('2026-07-01', 'energy', 32000000000, 0.80, NULL),
    ('2026-07-01', 'quality_waste', 22000000000, 0.80, NULL),
    ('2026-07-01', 'pricing_sales', 30000000000, 0.80, NULL),
    ('2026-07-01', 'procurement', 15000000000, 0.80, NULL),
    ('2026-07-01', 'demand_driven', 28000000000, 0.80, NULL)
ON CONFLICT DO NOTHING;

INSERT INTO maturity.model_registry (domain, model_name, version, artifact_uri, metrics, status, promoted_at) VALUES
    ('energy', 'rul', 'rul-gbr-v1', 's3://ml-models/energy/rul/rul-gbr-v1.joblib', '{"alert_accuracy":0.986}'::jsonb, 'production', NOW()),
    ('quality', 'anomaly', 'quality-anomaly-rf-v1', 's3://ml-models/quality/anomaly/quality-anomaly-rf-v1.joblib', '{"accuracy":0.9975}'::jsonb, 'production', NOW()),
    ('demand', 'forecast', 'demand-gbr-v1', 's3://ml-models/demand/forecast/demand-gbr-v1.joblib', '{"accuracy":0.972}'::jsonb, 'production', NOW()),
    ('supply', 'price', 'supply-price-gbr-v1', 's3://ml-models/supply/price/supply-price-gbr-v1.joblib', '{"accuracy":0.99}'::jsonb, 'production', NOW()),
    ('sales', 'forecast', 'sales-gbr-v1', 's3://ml-models/sales/forecast/sales-gbr-v1.joblib', '{"accuracy":0.977}'::jsonb, 'production', NOW()),
    ('finance', 'cashflow', 'finance-gbr-v1', 's3://ml-models/finance/cashflow/finance-gbr-v1.joblib', '{"accuracy":0.986}'::jsonb, 'production', NOW())
ON CONFLICT DO NOTHING;
