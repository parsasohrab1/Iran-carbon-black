-- Stock market tables for Shekarbon (Iran Carbon Black TSE listing)

CREATE TABLE IF NOT EXISTS finance.stock_quotes (
    time            TIMESTAMPTZ NOT NULL,
    symbol          VARCHAR(32) NOT NULL DEFAULT 'Shekarbon',
    price           DOUBLE PRECISION NOT NULL,
    volume          BIGINT NOT NULL DEFAULT 0,
    value_irr       DOUBLE PRECISION,
    side            VARCHAR(8),
    source          VARCHAR(64) DEFAULT 'simulator'
);

SELECT create_hypertable('finance.stock_quotes', 'time', if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS finance.stock_daily (
    trade_date      DATE NOT NULL,
    symbol          VARCHAR(32) NOT NULL DEFAULT 'Shekarbon',
    open_price      DOUBLE PRECISION NOT NULL,
    high_price      DOUBLE PRECISION NOT NULL,
    low_price       DOUBLE PRECISION NOT NULL,
    close_price     DOUBLE PRECISION NOT NULL,
    volume          BIGINT NOT NULL DEFAULT 0,
    value_irr       DOUBLE PRECISION,
    change_pct      DOUBLE PRECISION,
    PRIMARY KEY (trade_date, symbol)
);

CREATE TABLE IF NOT EXISTS finance.stock_trades (
    id              BIGSERIAL PRIMARY KEY,
    traded_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    symbol          VARCHAR(32) NOT NULL DEFAULT 'Shekarbon',
    side            VARCHAR(8) NOT NULL,
    price           DOUBLE PRECISION NOT NULL,
    volume          BIGINT NOT NULL,
    value_irr       DOUBLE PRECISION NOT NULL,
    broker          VARCHAR(128),
    source          VARCHAR(64) DEFAULT 'simulator'
);

CREATE INDEX IF NOT EXISTS idx_stock_quotes_symbol_time ON finance.stock_quotes (symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_stock_trades_symbol_time ON finance.stock_trades (symbol, traded_at DESC);
