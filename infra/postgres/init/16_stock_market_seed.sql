-- Seed شکربن daily history + intraday ticks

INSERT INTO finance.stock_daily (trade_date, symbol, open_price, high_price, low_price, close_price, volume, value_irr, change_pct)
SELECT
    d::date,
    'شکربن',
    26000 + (row_number() OVER (ORDER BY d)) * 35 + (random() * 400)::int,
    0, 0, 0,
    (1800000 + random() * 2200000)::bigint,
    0,
    0
FROM generate_series(CURRENT_DATE - 90, CURRENT_DATE - 1, '1 day') AS d
WHERE EXTRACT(DOW FROM d) NOT IN (4, 5)  -- skip Thu/Fri
ON CONFLICT DO NOTHING;

UPDATE finance.stock_daily SET
    close_price = open_price * (0.985 + random() * 0.03),
    high_price = GREATEST(open_price, open_price * (0.985 + random() * 0.03)) * (1 + random() * 0.012),
    low_price = LEAST(open_price, open_price * (0.985 + random() * 0.03)) * (1 - random() * 0.012)
WHERE close_price = 0 OR high_price = 0;

UPDATE finance.stock_daily SET
    value_irr = close_price * volume,
    change_pct = ROUND((((close_price - open_price) / NULLIF(open_price, 0)) * 100)::numeric, 2)
WHERE value_irr = 0 OR value_irr IS NULL;

-- Intraday ticks for today
INSERT INTO finance.stock_quotes (time, symbol, price, volume, value_irr, side, source)
SELECT
    date_trunc('day', NOW()) + (m || ' minutes')::interval + INTERVAL '5 hours 30 minutes',
    'شکربن',
    (
        SELECT close_price FROM finance.stock_daily
        WHERE symbol = 'شکربن' ORDER BY trade_date DESC LIMIT 1
    ) * (1 + (random() - 0.48) * 0.02),
    (50000 + random() * 250000)::bigint,
    0,
    CASE WHEN random() > 0.5 THEN 'buy' ELSE 'sell' END,
    'simulator'
FROM generate_series(0, 90, 3) AS m;

UPDATE finance.stock_quotes
SET value_irr = price * volume
WHERE value_irr = 0 OR value_irr IS NULL;

INSERT INTO finance.stock_trades (traded_at, symbol, side, price, volume, value_irr, broker, source)
SELECT
    q.time,
    q.symbol,
    q.side,
    q.price,
    q.volume,
    q.value_irr,
    CASE WHEN random() > 0.5 THEN 'کارگزاری مفید' ELSE 'کارگزاری آگاه' END,
    'simulator'
FROM finance.stock_quotes q
ORDER BY q.time DESC
LIMIT 40;
