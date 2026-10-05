-- Seed active / potential customers with tonnage and purchase queue

UPDATE sales.customers SET
    status = 'active',
    monthly_tonnage_kg = COALESCE(monthly_tonnage_kg, annual_consumption_kg / 12.0)
WHERE status IS NULL OR status = 'active';

INSERT INTO sales.customers (id, name, segment, industry, annual_consumption_kg, region, status, monthly_tonnage_kg, contact_person, notes) VALUES
    ('CUST-0047', 'Sahand Tire', 'tire_manufacturer', 'tire', 180000, 'domestic', 'active', 15000, 'Eng. Rezaei', 'Key domestic account'),
    ('CUST-0012', 'Barez Rubber', 'tire_manufacturer', 'tire', 220000, 'domestic', 'active', 18300, 'Ms. Karimi', 'N220/N234 order growth'),
    ('CUST-0021', 'Kavir Tire', 'tire_manufacturer', 'tire', 150000, 'domestic', 'active', 12500, 'Mr. Mousavi', 'Price sensitive'),
    ('CUST-0033', 'Iran Tire', 'tire_manufacturer', 'tire', 195000, 'domestic', 'active', 16250, 'Eng. Ahmadi', 'Strategic account'),
    ('CUST-0099', 'Export Partner UAE', 'distributor', 'rubber', 95000, 'export', 'active', 7900, 'Mr. Al-Farsi', 'Export distributor'),
    ('CUST-0055', 'RubberTech TR', 'compounder', 'rubber', 60000, 'export', 'active', 5000, 'Ms. Yilmaz', 'Turkish compounder'),
    ('CUST-0070', 'Cable Poly Iran', 'industrial', 'cable', 40000, 'domestic', 'active', 3300, 'Eng. Nouri', 'Cable and industrial'),
    -- Potential customers (pipeline)
    ('CUST-0101', 'Yazd Tire', 'tire_manufacturer', 'tire', 90000, 'domestic', 'potential', 7500, 'Mr. Hosseini', 'In technical negotiation'),
    ('CUST-0102', 'Dena Rubber', 'tire_manufacturer', 'tire', 110000, 'domestic', 'potential', 9200, 'Ms. Moradi', 'N330 grade trial'),
    ('CUST-0103', 'Pars Rubber', 'compounder', 'rubber', 45000, 'domestic', 'potential', 3750, 'Eng. Kazemi', 'Needs HAF-HS'),
    ('CUST-0104', 'Gulf Tire Co.', 'tire_manufacturer', 'tire', 130000, 'export', 'potential', 10800, 'Mr. Rahman', 'Persian Gulf export potential'),
    ('CUST-0105', 'Arya Wire & Cable', 'industrial', 'cable', 28000, 'domestic', 'potential', 2300, 'Ms. Jafari', 'Import substitution')
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    segment = EXCLUDED.segment,
    industry = EXCLUDED.industry,
    annual_consumption_kg = EXCLUDED.annual_consumption_kg,
    region = EXCLUDED.region,
    status = EXCLUDED.status,
    monthly_tonnage_kg = EXCLUDED.monthly_tonnage_kg,
    contact_person = EXCLUDED.contact_person,
    notes = EXCLUDED.notes;

INSERT INTO sales.customer_profiles (customer_id, preferred_grades, avg_order_kg, churn_risk, lifetime_value_irr, needs, notes)
VALUES
    ('CUST-0101', '["N330","N220"]'::jsonb, 7000, 0.08, 0, '{"stage":"technical_eval"}'::jsonb, 'Potential — tire'),
    ('CUST-0102', '["N330","N339"]'::jsonb, 8500, 0.10, 0, '{"stage":"sample"}'::jsonb, 'Potential — Dena'),
    ('CUST-0103', '["N339","N375"]'::jsonb, 4000, 0.12, 0, '{"stage":"proposal"}'::jsonb, 'Potential — compounder'),
    ('CUST-0104', '["N220","N234"]'::jsonb, 10000, 0.15, 0, '{"stage":"commercial"}'::jsonb, 'Potential — export'),
    ('CUST-0105', '["N550","N660"]'::jsonb, 2500, 0.09, 0, '{"stage":"discovery"}'::jsonb, 'Potential — cable')
ON CONFLICT DO NOTHING;

-- Purchase queue — open demand reflected in sales forecast
DELETE FROM sales.purchase_queue WHERE source = 'seed-pipeline';

INSERT INTO sales.purchase_queue (
    customer_id, grade, requested_tonnage_kg, priority, status,
    expected_close_date, unit_price_irr, probability, source, notes
) VALUES
    ('CUST-0047', 'N330', 18000, 1, 'queued', CURRENT_DATE + 12, 188000, 0.85, 'seed-pipeline', 'Recurring monthly order'),
    ('CUST-0012', 'N220', 22000, 1, 'queued', CURRENT_DATE + 8, 196000, 0.90, 'seed-pipeline', 'Line 1 delivery priority'),
    ('CUST-0012', 'N234', 12000, 2, 'negotiating', CURRENT_DATE + 18, 205000, 0.70, 'seed-pipeline', 'Price under negotiation'),
    ('CUST-0033', 'N330', 15000, 2, 'queued', CURRENT_DATE + 15, 187000, 0.80, 'seed-pipeline', 'Quarterly contract'),
    ('CUST-0021', 'N550', 10000, 3, 'queued', CURRENT_DATE + 20, 165000, 0.65, 'seed-pipeline', 'Price sensitive'),
    ('CUST-0099', 'N550', 9000, 2, 'confirmed', CURRENT_DATE + 10, 172000, 0.95, 'seed-pipeline', 'Export — initial confirmation'),
    ('CUST-0055', 'N660', 6000, 3, 'queued', CURRENT_DATE + 25, 158000, 0.60, 'seed-pipeline', 'Compound'),
    ('CUST-0101', 'N330', 8000, 2, 'queued', CURRENT_DATE + 30, 185000, 0.45, 'seed-pipeline', 'Potential customer — sample approved'),
    ('CUST-0102', 'N339', 7000, 3, 'negotiating', CURRENT_DATE + 35, 190000, 0.40, 'seed-pipeline', 'Factory trial'),
    ('CUST-0104', 'N220', 14000, 1, 'queued', CURRENT_DATE + 28, 210000, 0.55, 'seed-pipeline', 'Large export potential'),
    ('CUST-0103', 'N375', 4500, 4, 'queued', CURRENT_DATE + 40, 192000, 0.35, 'seed-pipeline', 'Technical proposal sent'),
    ('CUST-0105', 'N550', 3000, 4, 'queued', CURRENT_DATE + 45, 160000, 0.30, 'seed-pipeline', 'Import substitution');
