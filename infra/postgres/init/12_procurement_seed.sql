-- Procurement board: expand suppliers + feedstock price history for live prices

INSERT INTO supply.suppliers (id, name, rating, delivery_reliability, quality_rating, metadata) VALUES
    ('SUP-0012', 'Tabriz Petrochemical', 4.2, 0.92, 4.5,
     '{"city":"Tabriz","province":"East Azerbaijan","type":"Domestic petrochemical","materials":["cbfs","naphtha","ethylene_tar"]}'::jsonb),
    ('SUP-0003', 'Isfahan Refinery', 4.0, 0.88, 4.1,
     '{"city":"Isfahan","province":"Isfahan","type":"Refinery","materials":["cbfs","naphtha","anthracene_oil"]}'::jsonb),
    ('SUP-0008', 'Bandar Imam Petrochemical', 3.8, 0.85, 4.0,
     '{"city":"Mahshahr","province":"Khuzestan","type":"Domestic petrochemical","materials":["cbfs","ethylene_tar","naphtha"]}'::jsonb),
    ('SUP-0015', 'Abadan Refinery', 3.9, 0.83, 3.9,
     '{"city":"Abadan","province":"Khuzestan","type":"Refinery","materials":["cbfs","anthracene_oil"]}'::jsonb),
    ('SUP-0021', 'Shazand Arak Petrochemical', 4.1, 0.90, 4.3,
     '{"city":"Arak","province":"Markazi","type":"Domestic petrochemical","materials":["ethylene_tar","naphtha"]}'::jsonb),
    ('SUP-0030', 'National Gas Company — Region 3', 4.4, 0.96, 4.6,
     '{"city":"Ahvaz","province":"Khuzestan","type":"Energy / Gas","materials":["natural_gas"]}'::jsonb),
    ('SUP-0042', 'Persian Gulf Energy Trading', 3.6, 0.78, 3.7,
     '{"city":"Tehran","province":"Tehran","type":"Trader / Importer","materials":["cbfs","anthracene_oil"]}'::jsonb)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    rating = EXCLUDED.rating,
    delivery_reliability = EXCLUDED.delivery_reliability,
    quality_rating = EXCLUDED.quality_rating,
    metadata = EXCLUDED.metadata;

-- Recent market prices (last ~8 weeks) for live "updated price"
INSERT INTO supply.price_history (time, material, price_irr, source)
SELECT
    NOW() - ((8 - w) || ' weeks')::interval,
    mat.name,
    mat.base + w * mat.step + (random() * mat.noise)::int,
    'market'
FROM generate_series(0, 8) AS w
CROSS JOIN (
    VALUES
        ('Coal tar (furfural extract)', 41000, 220, 600),
        ('Naphtha', 58000, 280, 900),
        ('Ethylene tar', 37500, 180, 500),
        ('Anthracene oil', 43000, 200, 700),
        ('Natural gas (process fuel)', 17200, 90, 300)
) AS mat(name, base, step, noise);

-- Supplier-specific quote snapshots (source = supplier id)
INSERT INTO supply.price_history (time, material, price_irr, source) VALUES
    (NOW() - INTERVAL '1 day', 'Coal tar (furfural extract)', 42800, 'SUP-0012'),
    (NOW() - INTERVAL '1 day', 'Coal tar (furfural extract)', 42100, 'SUP-0003'),
    (NOW() - INTERVAL '1 day', 'Coal tar (furfural extract)', 43500, 'SUP-0008'),
    (NOW() - INTERVAL '1 day', 'Coal tar (furfural extract)', 41900, 'SUP-0015'),
    (NOW() - INTERVAL '1 day', 'Coal tar (furfural extract)', 44500, 'SUP-0042'),
    (NOW() - INTERVAL '1 day', 'Naphtha', 61200, 'SUP-0012'),
    (NOW() - INTERVAL '1 day', 'Naphtha', 59800, 'SUP-0003'),
    (NOW() - INTERVAL '1 day', 'Naphtha', 60500, 'SUP-0008'),
    (NOW() - INTERVAL '1 day', 'Naphtha', 59100, 'SUP-0021'),
    (NOW() - INTERVAL '1 day', 'Ethylene tar', 39500, 'SUP-0012'),
    (NOW() - INTERVAL '1 day', 'Ethylene tar', 38800, 'SUP-0008'),
    (NOW() - INTERVAL '1 day', 'Ethylene tar', 40200, 'SUP-0021'),
    (NOW() - INTERVAL '1 day', 'Anthracene oil', 45200, 'SUP-0003'),
    (NOW() - INTERVAL '1 day', 'Anthracene oil', 44800, 'SUP-0015'),
    (NOW() - INTERVAL '1 day', 'Anthracene oil', 46800, 'SUP-0042'),
    (NOW() - INTERVAL '1 day', 'Natural gas (process fuel)', 18500, 'SUP-0030');
