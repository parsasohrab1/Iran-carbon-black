-- Seed actual/potential export markets + 6-month forecast for شکربن
-- Reference portals: Codal, IRICA/EPL, TPO, NTSW

INSERT INTO sales.export_markets (
    id, country_fa, country_en, status, region, annual_tonnage_kg, ytd_tonnage_kg, share_pct,
    main_grades, avg_fob_usd, growth_yoy_pct, buyers, logistics, risk, pipeline_stage, probability, source_refs
) VALUES
('IN', 'هند', 'India', 'actual', 'South Asia', 4200000, 2081000, 28,
 ARRAY['N-330','N-220','N-550'], 980, 6.5,
 'تایرسازان و کامپاوندرهای هند', 'بندرعباس → Mundra / Nhava Sheva', 'متوسط — رقابت چین و نوسان روپیه',
 NULL, NULL, ARRAY['codal','irica','enigma']),
('PK', 'پاکستان', 'Pakistan', 'actual', 'South Asia', 2100000, 1180000, 14,
 ARRAY['N-330','N-660'], 920, 4.2,
 'صنعت تایر و لاستیک بازسازی', 'زمینی / بندر کراچی', 'متوسط — مسائل بانکی و تسویه',
 NULL, NULL, ARRAY['irica','tpo']),
('TR', 'ترکیه', 'Turkey', 'actual', 'Europe / West Asia', 1800000, 980000, 12,
 ARRAY['N-550','N-660','N-330'], 1050, 8.0,
 'کامپاوندر و قطعه‌سازان لاستیکی', 'زمینی / بندر مرسین', 'کم — مسیر پایدار تجاری',
 NULL, NULL, ARRAY['codal','irica','tpo']),
('AE', 'امارات متحده عربی', 'UAE', 'actual', 'GCC', 1500000, 820000, 10,
 ARRAY['N-550','N-220'], 1020, 5.5,
 'توزیع‌کنندگان منطقه‌ای خلیج فارس', 'بندرعباس → جبل علی', 'کم — هاب توزیع',
 NULL, NULL, ARRAY['codal','ntsw']),
('CN', 'چین', 'China', 'actual', 'East Asia', 1200000, 640000, 8,
 ARRAY['N-220','N-234','P-8201'], 890, -2.0,
 'مستربچ و تایرسازان منطقه‌ای', 'دریایی شرق آسیا', 'بالا — رقابت قیمتی',
 NULL, NULL, ARRAY['irica','tpo']),
('ID', 'اندونزی', 'Indonesia', 'actual', 'SE Asia', 900000, 480000, 6,
 ARRAY['N-330','N-550'], 960, 9.5,
 'تایرسازان ASEAN', 'بندرعباس → Jakarta / Surabaya', 'متوسط — فاصله لجستیکی',
 NULL, NULL, ARRAY['tpo','irica']),
('DE', 'آلمان', 'Germany', 'potential', 'EU', 600000, 0, 0,
 ARRAY['N-220','N-234','N-375'], 1180, 12.0,
 'قطعات خودرو و تایر پرمیوم', 'از طریق ترکیه / مدیترانه', 'بالا — REACH و تحریم',
 'technical_eval', 0.35, ARRAY['tpo','enigma']),
('VN', 'ویتنام', 'Vietnam', 'potential', 'SE Asia', 750000, 40000, 0,
 ARRAY['N-330','N-550'], 970, 15.0,
 'رشد سریع صنعت تایر', 'دریایی جنوب شرق آسیا', 'متوسط — نیاز به نماینده محلی',
 'negotiation', 0.55, ARRAY['tpo','irica']),
('IQ', 'عراق', 'Iraq', 'potential', 'West Asia', 500000, 80000, 0,
 ARRAY['N-330','N-660'], 940, 10.0,
 'بازسازی و لاستیک سنگین', 'زمینی مرز شلمچه / پرویزخان', 'متوسط — تسویه و امنیت مسیر',
 'lead', 0.45, ARRAY['tpo','ntsw']),
('EG', 'مصر', 'Egypt', 'potential', 'North Africa', 400000, 0, 0,
 ARRAY['N-550','N-660'], 990, 8.0,
 'تایر و کامپاند منطقه‌ای', 'دریای سرخ / سوئز', 'متوسط — رقابت ترکیه',
 'market_study', 0.30, ARRAY['tpo']),
('RU', 'روسیه / CIS', 'Russia / CIS', 'potential', 'CIS', 850000, 120000, 0,
 ARRAY['N-220','N-330','N-550'], 1010, 11.0,
 'تایرسازان و صنایع لاستیک', 'دریای خزر / مسیر زمینی', 'متوسط — جایگزینی واردات غربی',
 'negotiation', 0.50, ARRAY['tpo','codal']),
('BD', 'بنگلادش', 'Bangladesh', 'potential', 'South Asia', 350000, 0, 0,
 ARRAY['N-330','N-660'], 910, 14.0,
 'تایر نوپا و لاستیک دوچرخه/موتور', 'چیتاگونگ', 'کم تا متوسط',
 'lead', 0.40, ARRAY['tpo','irica'])
ON CONFLICT (id) DO UPDATE SET
    annual_tonnage_kg = EXCLUDED.annual_tonnage_kg,
    ytd_tonnage_kg = EXCLUDED.ytd_tonnage_kg,
    share_pct = EXCLUDED.share_pct,
    growth_yoy_pct = EXCLUDED.growth_yoy_pct,
    probability = EXCLUDED.probability,
    updated_at = NOW();

-- 6-month forecast rows (from current month)
INSERT INTO sales.export_forecasts (
    forecast_month, baseline_tonnage_kg, pipeline_uplift_kg, forecast_tonnage_kg,
    forecast_revenue_usd, forecast_revenue_irr, avg_fob_usd, confidence, model_version, source
)
SELECT
    (date_trunc('month', CURRENT_DATE) + (g.i || ' months')::interval)::date,
    round((11700000.0 / 12.0) * (1.0 + 0.008 * g.i) * (1.0 + 0.04 * ((g.i % 3) - 1))),
    round((1443750.0 / 12.0) * (0.15 + 0.12 * g.i)),
    round(
        (11700000.0 / 12.0) * (1.0 + 0.008 * g.i) * (1.0 + 0.04 * ((g.i % 3) - 1))
        + (1443750.0 / 12.0) * (0.15 + 0.12 * g.i)
    ),
    round(
        (
            (11700000.0 / 12.0) * (1.0 + 0.008 * g.i) * (1.0 + 0.04 * ((g.i % 3) - 1))
            + (1443750.0 / 12.0) * (0.15 + 0.12 * g.i)
        ) / 1000.0 * (980 + g.i * 5)
    ),
    round(
        (
            (11700000.0 / 12.0) * (1.0 + 0.008 * g.i) * (1.0 + 0.04 * ((g.i % 3) - 1))
            + (1443750.0 / 12.0) * (0.15 + 0.12 * g.i)
        ) / 1000.0 * (980 + g.i * 5) * 620000
    ),
    980 + g.i * 5,
    round((0.82 - g.i * 0.04)::numeric, 2),
    'export-forecast-v1',
    'seed-codal-tpo-irica'
FROM generate_series(0, 5) AS g(i)
ON CONFLICT (forecast_month, model_version) DO UPDATE SET
    baseline_tonnage_kg = EXCLUDED.baseline_tonnage_kg,
    pipeline_uplift_kg = EXCLUDED.pipeline_uplift_kg,
    forecast_tonnage_kg = EXCLUDED.forecast_tonnage_kg,
    forecast_revenue_usd = EXCLUDED.forecast_revenue_usd,
    forecast_revenue_irr = EXCLUDED.forecast_revenue_irr,
    confidence = EXCLUDED.confidence,
    created_at = NOW();
