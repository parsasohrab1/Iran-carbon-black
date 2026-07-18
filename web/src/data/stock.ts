/** Offline/static fallback for شکربن TSE board. */

export type StockTicker = {
  symbol_fa: string;
  symbol_en: string;
  company_fa: string;
  company_en: string;
  isin: string;
  market: string;
  industry: string;
};

export type StockQuote = {
  last_price: number;
  open_price: number;
  high_price: number;
  low_price: number;
  previous_close: number;
  day_change: number;
  day_change_pct: number;
  week_change_pct: number;
  month_change_pct: number;
  volume: number;
  value_irr: number;
  trade_count: number;
  as_of: string;
  trend: string;
  status: string;
};

export type StockTick = {
  time: string;
  price: number;
  volume: number;
  value_irr?: number;
  side?: string;
  change_pct?: number;
};

export type StockDaily = {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  value_irr?: number;
  change_pct?: number;
};

export type StockTrade = {
  id?: number | string;
  time: string;
  side: string;
  price: number;
  volume: number;
  value_irr: number;
  broker?: string;
};

export type StockBoard = {
  source?: string;
  ticker: StockTicker;
  quote: StockQuote;
  intraday: StockTick[];
  history_daily: StockDaily[];
  recent_trades: StockTrade[];
  order_book?: {
    bids: Array<{ price: number; volume: number }>;
    asks: Array<{ price: number; volume: number }>;
  };
};

export function buildLocalStockBoard(): StockBoard {
  const base = 28500;
  const now = Date.now();
  const intraday: StockTick[] = Array.from({ length: 60 }, (_, i) => {
    const price = base * (1 + Math.sin(i / 8) * 0.012 + (i - 30) * 0.00015);
    return {
      time: new Date(now - (60 - i) * 180000).toISOString(),
      price: Math.round(price),
      volume: 80000 + i * 1200,
      side: i % 2 === 0 ? "buy" : "sell",
      change_pct: Number((((price - base) / base) * 100).toFixed(2)),
    };
  });
  const history_daily: StockDaily[] = Array.from({ length: 40 }, (_, i) => {
    const open = base * (0.92 + i * 0.002);
    const close = open * (0.99 + (i % 5) * 0.004);
    return {
      date: new Date(now - (40 - i) * 86400000).toISOString().slice(0, 10),
      open: Math.round(open),
      high: Math.round(Math.max(open, close) * 1.01),
      low: Math.round(Math.min(open, close) * 0.99),
      close: Math.round(close),
      volume: 2000000 + i * 10000,
      change_pct: Number((((close - open) / open) * 100).toFixed(2)),
    };
  });
  const last = intraday[intraday.length - 1];
  const first = intraday[0];
  return {
    source: "static شکربن board",
    ticker: {
      symbol_fa: "شکربن",
      symbol_en: "SHOKRBAN",
      company_fa: "شرکت کربن ایران (سهامی عام)",
      company_en: "Iran Carbon Black Co.",
      isin: "IRO1CRBN0001",
      market: "بورس — بازار اول (تابلوی فرعی)",
      industry: "محصولات شیمیایی / دوده صنعتی",
    },
    quote: {
      last_price: last.price,
      open_price: first.price,
      high_price: Math.max(...intraday.map((t) => t.price)),
      low_price: Math.min(...intraday.map((t) => t.price)),
      previous_close: history_daily[history_daily.length - 2]?.close ?? first.price,
      day_change: last.price - first.price,
      day_change_pct: Number((((last.price - first.price) / first.price) * 100).toFixed(2)),
      week_change_pct: 1.8,
      month_change_pct: 4.2,
      volume: intraday.reduce((s, t) => s + t.volume, 0),
      value_irr: intraday.reduce((s, t) => s + t.price * t.volume, 0),
      trade_count: intraday.length,
      as_of: last.time,
      trend: last.price >= first.price ? "up" : "down",
      status: "شبیه‌سازی لحظه‌ای (آفلاین)",
    },
    intraday,
    history_daily,
    recent_trades: [...intraday].reverse().slice(0, 20).map((t, i) => ({
      id: i + 1,
      time: t.time,
      side: t.side ?? "buy",
      price: t.price,
      volume: t.volume,
      value_irr: t.price * t.volume,
      broker: i % 2 ? "کارگزاری آگاه" : "کارگزاری مفید",
    })),
    order_book: {
      bids: [1, 2, 3, 4, 5].map((i) => ({ price: last.price - i * 50, volume: 100000 * (6 - i) })),
      asks: [1, 2, 3, 4, 5].map((i) => ({ price: last.price + i * 50, volume: 90000 * (6 - i) })),
    },
  };
}
