"""Demand-driven production planning for Iran Carbon Black (Shekarbon).

Combines:
  - ML / historical demand run-rate
  - Sales purchase-queue weighted demand
  - Export market grade shares
into a capacity-constrained weekly production schedule.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from shared.export_markets import ACTUAL_MARKETS, build_export_forecast
from shared.product_catalog import CURRENT_PRODUCTS
from shared.sales_pipeline import QUEUE_SEED, build_static_pipeline

# Daily nameplate capacity (kg) by production line
LINE_CAPACITY_KG_DAY: dict[str, float] = {
    "Line_1": 48_000,
    "Line_2": 42_000,
    "UTIL": 0,  # utilities — not a product line
}

# Prefer hard grades on Line_1, soft/filler on Line_2
GRADE_LINE: dict[str, str] = {
    "N-220": "Line_1",
    "N-234": "Line_1",
    "N-326": "Line_1",
    "N-330": "Line_1",
    "N-330-SV": "Line_1",
    "N-339": "Line_1",
    "N-375": "Line_1",
    "N-550-ICC": "Line_2",
    "N-550-VJ": "Line_2",
    "N-550": "Line_2",
    "N-660": "Line_2",
    "P-8201": "Line_2",
}

MARGIN_HINT: dict[str, float] = {
    "N-220": 0.12,
    "N-234": 0.13,
    "N-326": 0.10,
    "N-330": 0.11,
    "N-330-SV": 0.11,
    "N-339": 0.12,
    "N-375": 0.12,
    "N-550-ICC": 0.09,
    "N-550-VJ": 0.09,
    "N-660": 0.08,
    "P-8201": 0.14,
}


def _norm_grade(code: str) -> str:
    c = code.strip().upper().replace("_", "-")
    catalog_by_code = {p["code"].upper(): p["code"] for p in CURRENT_PRODUCTS}
    if c in catalog_by_code:
        return catalog_by_code[c]
    compact = c.replace("-", "")
    # Prefer canonical (non-variant) commercial code when ASTM maps to several SKUs
    preferred = {
        "N330": "N-330",
        "N550": "N-550-ICC",
    }
    if compact in preferred and preferred[compact] in catalog_by_code.values():
        return preferred[compact]
    for p in CURRENT_PRODUCTS:
        if p["astm_code"].upper() == compact:
            return p["code"]
    return code


def _base_monthly_demand() -> dict[str, float]:
    """Baseline monthly demand kg per commercial grade (planning defaults)."""
    return {
        "N-220": 380_000,
        "N-234": 220_000,
        "N-326": 180_000,
        "N-330": 420_000,
        "N-330-SV": 160_000,
        "N-339": 200_000,
        "N-375": 150_000,
        "N-550-ICC": 280_000,
        "N-550-VJ": 210_000,
        "N-660": 260_000,
        "P-8201": 90_000,
    }


def demand_from_sales_queue() -> dict[str, float]:
    """Weighted purchase-queue demand (kg) by grade."""
    out: dict[str, float] = {}
    for item in QUEUE_SEED:
        if item.get("status") == "cancelled":
            continue
        g = _norm_grade(str(item["grade"]))
        ton = float(item["requested_tonnage_kg"]) * float(item.get("probability", 0.6))
        out[g] = out.get(g, 0.0) + ton
    return out


def demand_from_export(horizon_days: int = 30) -> dict[str, float]:
    """Allocate near-term export forecast across grades by market main_grades share."""
    forecast = build_export_forecast()
    month0 = float(forecast[0]["forecast_tonnage_kg"]) if forecast else 0.0
    # scale to horizon
    export_kg = month0 * (horizon_days / 30.0)
    weights: dict[str, float] = {}
    for m in ACTUAL_MARKETS:
        share = float(m.get("share_pct") or 0) / 100.0
        grades = m.get("main_grades") or []
        if not grades:
            continue
        per = share / len(grades)
        for g in grades:
            g2 = _norm_grade(str(g))
            weights[g2] = weights.get(g2, 0.0) + per
    total_w = sum(weights.values()) or 1.0
    return {g: export_kg * (w / total_w) for g, w in weights.items()}


def build_demand_signals(
    *,
    historical_monthly: dict[str, float] | None = None,
    horizon_days: int = 30,
) -> list[dict[str, Any]]:
    """Merge baseline / historical + sales queue + export into per-grade demand."""
    raw_hist = historical_monthly or {}
    # Normalize DB grade keys into commercial codes; keep only active products
    hist_norm: dict[str, float] = {}
    for k, v in raw_hist.items():
        g = _norm_grade(str(k))
        hist_norm[g] = hist_norm.get(g, 0.0) + float(v)

    active_codes = {p["code"] for p in CURRENT_PRODUCTS}
    base = _base_monthly_demand()
    # Prefer historical for active grades; fall back to planning defaults
    for code in active_codes:
        if code in hist_norm and hist_norm[code] > 0:
            base[code] = hist_norm[code]
        elif code not in base:
            # try ASTM compact match from hist keys
            compact = code.replace("-", "").upper()
            for hk, hv in hist_norm.items():
                if hk.replace("-", "").upper() == compact or hk.upper() == compact:
                    base[code] = hv
                    break

    queue = demand_from_sales_queue()
    export = demand_from_export(horizon_days=horizon_days)
    scale = horizon_days / 30.0

    rows = []
    for grade in sorted(active_codes):
        hist = float(base.get(grade, 0.0)) * scale
        q = float(queue.get(grade, 0.0))
        ex = float(export.get(grade, 0.0))
        # Blend: 55% run-rate + 30% sales pipeline + 15% export allocation
        total = hist * 0.55 + q * 0.30 + ex * 0.15
        safety = total * 0.12
        planned = total + safety
        line = GRADE_LINE.get(grade, "Line_1")
        rows.append(
            {
                "product_grade": grade,
                "demand_baseline_kg": round(hist, 0),
                "demand_sales_queue_kg": round(q, 0),
                "demand_export_kg": round(ex, 0),
                "demand_total_kg": round(total, 0),
                "safety_stock_kg": round(safety, 0),
                "planned_quantity_kg": round(planned, 0),
                "production_line": line,
                "margin_score": MARGIN_HINT.get(grade, 0.10),
                "horizon_days": horizon_days,
            }
        )
    rows.sort(key=lambda r: r["planned_quantity_kg"], reverse=True)
    return rows


def build_schedule(
    demand_rows: list[dict[str, Any]],
    *,
    days: int = 14,
    start: date | None = None,
) -> list[dict[str, Any]]:
    """Allocate planned quantities across calendar days under line capacity."""
    start = start or (date.today() + timedelta(days=1))
    # remaining to schedule per grade
    remaining = {r["product_grade"]: float(r["planned_quantity_kg"]) for r in demand_rows}
    line_of = {r["product_grade"]: r["production_line"] for r in demand_rows}
    margin_of = {r["product_grade"]: r["margin_score"] for r in demand_rows}

    # priority: higher margin first within each day
    grade_order = sorted(remaining.keys(), key=lambda g: margin_of.get(g, 0), reverse=True)

    schedule: list[dict[str, Any]] = []
    for d in range(days):
        day = start + timedelta(days=d)
        # skip Thu/Fri (Iran weekend proxy) lightly — still allow 70% capacity
        weekend = day.weekday() in (3, 4)
        capacity_left = {
            line: cap * (0.7 if weekend else 1.0) for line, cap in LINE_CAPACITY_KG_DAY.items() if cap > 0
        }
        for grade in grade_order:
            need = remaining.get(grade, 0.0)
            if need <= 1:
                continue
            line = line_of.get(grade, "Line_1")
            avail = capacity_left.get(line, 0.0)
            if avail <= 1:
                continue
            qty = min(need, avail)
            # prefer larger campaigns: at least 8t if possible
            if qty < 8000 and need > 8000 and avail >= 8000:
                qty = 8000.0
            qty = min(qty, need, avail)
            if qty < 500:
                continue
            remaining[grade] = need - qty
            capacity_left[line] -= qty
            util = 1 - (capacity_left[line] / max(LINE_CAPACITY_KG_DAY[line], 1))
            schedule.append(
                {
                    "date": str(day),
                    "weekday": day.strftime("%A"),
                    "product_grade": grade,
                    "production_line": line,
                    "quantity_kg": round(qty, 0),
                    "line_utilization_pct": round(util * 100, 1),
                    "demand_source": "forecast+sales+export",
                }
            )

    # any leftover noted as backlog
    for grade, left in remaining.items():
        if left > 500:
            schedule.append(
                {
                    "date": str(start + timedelta(days=days)),
                    "weekday": "backlog",
                    "product_grade": grade,
                    "production_line": line_of.get(grade, "Line_1"),
                    "quantity_kg": round(left, 0),
                    "line_utilization_pct": 100.0,
                    "demand_source": "backlog",
                }
            )
    return schedule


def build_production_board(
    *,
    historical_monthly: dict[str, float] | None = None,
    horizon_days: int = 30,
    schedule_days: int = 14,
) -> dict[str, Any]:
    pipeline = build_static_pipeline()
    demand_rows = build_demand_signals(historical_monthly=historical_monthly, horizon_days=horizon_days)
    schedule = build_schedule(demand_rows, days=schedule_days)
    total_demand = sum(r["demand_total_kg"] for r in demand_rows)
    total_planned = sum(r["planned_quantity_kg"] for r in demand_rows)
    total_scheduled = sum(s["quantity_kg"] for s in schedule if s.get("weekday") != "backlog")
    backlog = sum(s["quantity_kg"] for s in schedule if s.get("demand_source") == "backlog")
    by_line: dict[str, float] = {}
    for s in schedule:
        if s.get("demand_source") == "backlog":
            continue
        by_line[s["production_line"]] = by_line.get(s["production_line"], 0.0) + float(s["quantity_kg"])

    return {
        "source": "Demand (base + sales queue + exports) → capacity-based production plan",
        "horizon_days": horizon_days,
        "schedule_days": schedule_days,
        "plan_date": str(date.today()),
        "demand_by_grade": demand_rows,
        "schedule": schedule,
        "sales_pipeline_summary": pipeline.get("summary"),
        "line_capacity_kg_day": LINE_CAPACITY_KG_DAY,
        "summary": {
            "grades_count": len(demand_rows),
            "total_demand_kg": round(total_demand, 0),
            "total_planned_kg": round(total_planned, 0),
            "total_scheduled_kg": round(total_scheduled, 0),
            "backlog_kg": round(backlog, 0),
            "schedule_slots": len([s for s in schedule if s.get("demand_source") != "backlog"]),
            "lines_used": sorted(by_line.keys()),
            "line_load_kg": {k: round(v, 0) for k, v in by_line.items()},
            "coverage_pct": round((total_scheduled / total_planned) * 100, 1) if total_planned else 0,
        },
    }
