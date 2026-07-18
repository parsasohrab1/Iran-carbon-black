-- Procurement board: expand suppliers + feedstock price history for live prices

INSERT INTO supply.suppliers (id, name, rating, delivery_reliability, quality_rating, metadata) VALUES
    ('SUP-0012', 'پتروشیمی تبریز', 4.2, 0.92, 4.5,
     '{"city":"تبریز","province":"آذربایجان شرقی","type":"پتروشیمی داخلی","materials":["cbfs","naphtha","ethylene_tar"]}'::jsonb),
    ('SUP-0003', 'پالایشگاه اصفهان', 4.0, 0.88, 4.1,
     '{"city":"اصفهان","province":"اصفهان","type":"پالایشگاه","materials":["cbfs","naphtha","anthracene_oil"]}'::jsonb),
    ('SUP-0008', 'پتروشیمی بندر امام', 3.8, 0.85, 4.0,
     '{"city":"ماهشهر","province":"خوزستان","type":"پتروشیمی داخلی","materials":["cbfs","ethylene_tar","naphtha"]}'::jsonb),
    ('SUP-0015', 'پالایشگاه آبادان', 3.9, 0.83, 3.9,
     '{"city":"آبادان","province":"خوزستان","type":"پالایشگاه","materials":["cbfs","anthracene_oil"]}'::jsonb),
    ('SUP-0021', 'پتروشیمی شازند اراک', 4.1, 0.90, 4.3,
     '{"city":"اراک","province":"مرکزی","type":"پتروشیمی داخلی","materials":["ethylene_tar","naphtha"]}'::jsonb),
    ('SUP-0030', 'شرکت ملی گاز — منطقه ۳', 4.4, 0.96, 4.6,
     '{"city":"اهواز","province":"خوزستان","type":"انرژی / گاز","materials":["natural_gas"]}'::jsonb),
    ('SUP-0042', 'بازرگانی انرژی خلیج فارس', 3.6, 0.78, 3.7,
     '{"city":"تهران","province":"تهران","type":"بازرگان / واردات","materials":["cbfs","anthracene_oil"]}'::jsonb)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    rating = EXCLUDED.rating,
    delivery_reliability = EXCLUDED.delivery_reliability,
    quality_rating = EXCLUDED.quality_rating,
    metadata = EXCLUDED.metadata;

-- Recent market prices (last ~8 weeks) for live "قیمت به‌روز"
INSERT INTO supply.price_history (time, material, price_irr, source)
SELECT
    NOW() - ((8 - w) || ' weeks')::interval,
    mat.name,
    mat.base + w * mat.step + (random() * mat.noise)::int,
    'market'
FROM generate_series(0, 8) AS w
CROSS JOIN (
    VALUES
        ('قطران (فورفورال اکسترکت)', 41000, 220, 600),
        ('نفتا', 58000, 280, 900),
        ('تار اتیلن', 37500, 180, 500),
        ('روغن آنتراسن', 43000, 200, 700),
        ('گاز طبیعی (سوخت فرآیند)', 17200, 90, 300)
) AS mat(name, base, step, noise);

-- Supplier-specific quote snapshots (source = supplier id)
INSERT INTO supply.price_history (time, material, price_irr, source) VALUES
    (NOW() - INTERVAL '1 day', 'قطران (فورفورال اکسترکت)', 42800, 'SUP-0012'),
    (NOW() - INTERVAL '1 day', 'قطران (فورفورال اکسترکت)', 42100, 'SUP-0003'),
    (NOW() - INTERVAL '1 day', 'قطران (فورفورال اکسترکت)', 43500, 'SUP-0008'),
    (NOW() - INTERVAL '1 day', 'قطران (فورفورال اکسترکت)', 41900, 'SUP-0015'),
    (NOW() - INTERVAL '1 day', 'قطران (فورفورال اکسترکت)', 44500, 'SUP-0042'),
    (NOW() - INTERVAL '1 day', 'نفتا', 61200, 'SUP-0012'),
    (NOW() - INTERVAL '1 day', 'نفتا', 59800, 'SUP-0003'),
    (NOW() - INTERVAL '1 day', 'نفتا', 60500, 'SUP-0008'),
    (NOW() - INTERVAL '1 day', 'نفتا', 59100, 'SUP-0021'),
    (NOW() - INTERVAL '1 day', 'تار اتیلن', 39500, 'SUP-0012'),
    (NOW() - INTERVAL '1 day', 'تار اتیلن', 38800, 'SUP-0008'),
    (NOW() - INTERVAL '1 day', 'تار اتیلن', 40200, 'SUP-0021'),
    (NOW() - INTERVAL '1 day', 'روغن آنتراسن', 45200, 'SUP-0003'),
    (NOW() - INTERVAL '1 day', 'روغن آنتراسن', 44800, 'SUP-0015'),
    (NOW() - INTERVAL '1 day', 'روغن آنتراسن', 46800, 'SUP-0042'),
    (NOW() - INTERVAL '1 day', 'گاز طبیعی (سوخت فرآیند)', 18500, 'SUP-0030');
