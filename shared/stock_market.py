"""Tehran Stock Exchange — شکربن (Iran Carbon Black) market data helpers."""

from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone
from typing import Any

# Official listing metadata (TSE / کدال)
TICKER = {
    "symbol_fa": "شکربن",
    "symbol_en": "SHOKRBAN",
    "company_fa": "شرکت کربن ایران (سهامی عام)",
    "company_en": "Iran Carbon Black Co.",
    "isin": "IRO1CRBN0001",
    "market": "بورس — بازار اول (تابلوی فرعی)",
    "industry": "محصولات شیمیایی / دوده صنعتی",
    "base_volume": 1_000_000,
    "par_value_irr": 1000,
}


def _rng(seed: int | None = None) -> random.Random:
    return random.Random(seed if seed is not None else 42)


def generate_intraday_ticks(base_price: float = 28500.0, points: int = 78) -> list[dict[str, Any]]:
    """Simulate one trading day (~09:00–12:30) minute-ish ticks."""
    rng = _rng(int(base_price) % 997)
    now = datetime.now(timezone.utc)
    # Align to a local-feeling session window
    start = now.replace(hour=5, minute=30, second=0, microsecond=0)  # ~09:00 IRST ≈ 05:30 UTC
    if now < start:
        start = start - timedelta(days=1)
    price = base_price
    ticks = []
    for i in range(points):
        ts = start + timedelta(minutes=i * 3)
        shock = rng.gauss(0, 0.0045)
        drift = 0.00015 * math.sin(i / 9)
        price = max(1000.0, price * (1 + shock + drift))
        vol = int(abs(rng.gauss(180_000, 90_000)))
        side = "buy" if shock >= 0 else "sell"
        ticks.append(
            {
                "time": ts.isoformat(),
                "price": round(price, 0),
                "volume": vol,
                "value_irr": round(price * vol, 0),
                "side": side,
                "change_pct": round(((price - base_price) / base_price) * 100, 2),
            }
        )
    return ticks


def generate_daily_history(base_price: float = 27000.0, days: int = 60) -> list[dict[str, Any]]:
    rng = _rng(17)
    price = base_price
    rows = []
    today = datetime.now(timezone.utc).date()
    for i in range(days, 0, -1):
        d = today - timedelta(days=i)
        # Skip Fri/Sat-ish weekends roughly (Iran: Thu/Fri) — keep simple weekday feel
        if d.weekday() in (3, 4):  # Thu/Fri
            continue
        open_p = price
        close_p = max(1000.0, open_p * (1 + rng.gauss(0.001, 0.018)))
        high_p = max(open_p, close_p) * (1 + abs(rng.gauss(0, 0.008)))
        low_p = min(open_p, close_p) * (1 - abs(rng.gauss(0, 0.008)))
        vol = int(abs(rng.gauss(2_500_000, 800_000)))
        rows.append(
            {
                "date": d.isoformat(),
                "open": round(open_p, 0),
                "high": round(high_p, 0),
                "low": round(low_p, 0),
                "close": round(close_p, 0),
                "volume": vol,
                "value_irr": round(close_p * vol, 0),
                "change_pct": round(((close_p - open_p) / open_p) * 100, 2),
            }
        )
        price = close_p
    return rows


def build_static_stock_board() -> dict[str, Any]:
    history = generate_daily_history()
    ticks = generate_intraday_ticks(base_price=history[-1]["close"] if history else 28500)
    last = ticks[-1]
    first = ticks[0]
    day_change = last["price"] - first["price"]
    day_change_pct = (day_change / first["price"]) * 100 if first["price"] else 0
    week = history[-5:] if len(history) >= 5 else history
    month = history[-20:] if len(history) >= 20 else history
    week_chg = ((week[-1]["close"] - week[0]["open"]) / week[0]["open"] * 100) if week else 0
    month_chg = ((month[-1]["close"] - month[0]["open"]) / month[0]["open"] * 100) if month else 0

    trades = []
    for i, t in enumerate(reversed(ticks[-25:])):
        trades.append(
            {
                "id": f"TRD-{i+1:04d}",
                "time": t["time"],
                "side": t["side"],
                "price": t["price"],
                "volume": t["volume"],
                "value_irr": t["value_irr"],
                "broker": "کارگزاری نمونه" if i % 2 == 0 else "معاملات برخط",
            }
        )

    return {
        "source": "TSE listing metadata + live simulator (شکربن)",
        "ticker": TICKER,
        "quote": {
            "last_price": last["price"],
            "open_price": first["price"],
            "high_price": max(t["price"] for t in ticks),
            "low_price": min(t["price"] for t in ticks),
            "previous_close": history[-2]["close"] if len(history) >= 2 else first["price"],
            "day_change": round(day_change, 0),
            "day_change_pct": round(day_change_pct, 2),
            "week_change_pct": round(week_chg, 2),
            "month_change_pct": round(month_chg, 2),
            "volume": sum(t["volume"] for t in ticks),
            "value_irr": sum(t["value_irr"] for t in ticks),
            "trade_count": len(ticks),
            "as_of": last["time"],
            "trend": "up" if day_change_pct >= 0 else "down",
            "status": "معاملات پیوسته (شبیه‌سازی لحظه‌ای)",
        },
        "intraday": ticks,
        "history_daily": history,
        "recent_trades": trades,
        "order_book": {
            "bids": [
                {"price": round(last["price"] * (1 - 0.002 * i), 0), "volume": int(120000 * (6 - i))}
                for i in range(1, 6)
            ],
            "asks": [
                {"price": round(last["price"] * (1 + 0.002 * i), 0), "volume": int(110000 * (6 - i))}
                for i in range(1, 6)
            ],
        },
    }
