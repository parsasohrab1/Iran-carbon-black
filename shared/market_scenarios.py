"""Market-shock production scenarios for grade mix balancing.

Goals (Persian ops language):
  - preventing warehousing (no excess finished-goods inventory)
  - preventing a material purchase backlog (no feedstock purchase backlog)
  - preventing a sales backlog / customer order (clear sales purchase-queue)

Inputs: USD/IRR, gold (IRR/g), crude oil (USD), feedstock basket shock.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from shared.procurement_sources import MATERIALS, build_static_price_board
from shared.production_planning import (
    GRADE_LINE,
    MARGIN_HINT,
    _norm_grade,
    build_demand_signals,
)
from shared.sales_pipeline import QUEUE_SEED, build_static_pipeline

# Baseline macros (planning reference — not live feeds)
BASE_USD_IRR = 620_000.0
BASE_GOLD_IRR_G = 4_850_000.0  # roughly gram gold IRR proxy
BASE_OIL_USD = 78.0

# Feedstock intensity index (relative oil/CBFS use vs plant average = 1.0)
FEEDSTOCK_INTENSITY: dict[str, float] = {
    "N-220": 1.12,
    "N-234": 1.15,
    "N-326": 1.05,
    "N-330": 1.00,
    "N-330-SV": 1.02,
    "N-339": 1.08,
    "N-375": 1.10,
    "N-550-ICC": 0.92,
    "N-550-VJ": 0.90,
    "N-660": 0.85,
    "P-8201": 1.18,
}

# Export / FX sensitivity (higher → more upside when IRR weakens / USD rises)
FX_EXPORT_BETA: dict[str, float] = {
    "N-220": 0.85,
    "N-234": 0.90,
    "N-326": 0.55,
    "N-330": 0.70,
    "N-330-SV": 0.65,
    "N-339": 0.75,
    "N-375": 0.80,
    "N-550-ICC": 0.95,
    "N-550-VJ": 0.90,
    "N-660": 1.00,
    "P-8201": 1.10,
}

# Default on-hand proxy (kg) when DB inventory unavailable — skewed to create warehouse pressure
DEFAULT_INVENTORY_KG: dict[str, float] = {
    "N-220": 95_000,
    "N-234": 40_000,
    "N-326": 120_000,  # high stock → drawdown
    "N-330": 180_000,
    "N-330-SV": 55_000,
    "N-339": 70_000,
    "N-375": 35_000,
    "N-550-ICC": 140_000,
    "N-550-VJ": 85_000,
    "N-660": 160_000,  # soft grade warehouse risk
    "P-8201": 18_000,
}


def _feedstock_basket_irr(price_board: dict[str, Any] | None = None) -> float:
    board = price_board or build_static_price_board()
    weighted = 0.0
    wsum = 0.0
    for mat in board.get("materials") or MATERIALS:
        mid = mat.get("id")
        share = float(mat.get("typical_share_pct") or 0) / 100.0
        price = mat.get("latest_price_irr") or mat.get("avg_market_irr")
        if price is None:
            continue
        weighted += float(price) * share
        wsum += share
    return weighted / wsum if wsum else 42_000.0


def _base_macros(price_board: dict[str, Any] | None = None) -> dict[str, float]:
    return {
        "usd_irr": BASE_USD_IRR,
        "gold_irr_g": BASE_GOLD_IRR_G,
        "oil_usd": BASE_OIL_USD,
        "feedstock_basket_irr": round(_feedstock_basket_irr(price_board), 0),
    }


def scenario_presets() -> list[dict[str, Any]]:
    """Named global-market scenarios for side-by-side planning."""
    return [
        {
            "id": "baseline",
            "name_fa": "Baseline (current market)",
            "description_fa": "Exchange rate, gold, oil and feedstock at the reference level — balanced production for the sales queue and inventory control.",
            "usd_irr_delta_pct": 0,
            "gold_delta_pct": 0,
            "oil_delta_pct": 0,
            "feedstock_delta_pct": 0,
        },
        {
            "id": "usd_shock",
            "name_fa": "Dollar shock (FX↑)",
            "description_fa": "Rial weakness / dollar↑ → priority to exports and grades with high FX beta; reduction of low-margin stock.",
            "usd_irr_delta_pct": 18,
            "gold_delta_pct": 8,
            "oil_delta_pct": 4,
            "feedstock_delta_pct": 6,
        },
        {
            "id": "gold_oil_up",
            "name_fa": "Gold and oil rally",
            "description_fa": "Gold and oil↑ → feedstock inflation pressure; lighter production, priority for the firm sales queue, cautious material purchasing.",
            "usd_irr_delta_pct": 5,
            "gold_delta_pct": 15,
            "oil_delta_pct": 20,
            "feedstock_delta_pct": 14,
        },
        {
            "id": "feedstock_spike",
            "name_fa": "Raw material price spike",
            "description_fa": "CBFS/naphtha spike → stop stock-building production, focus on high-margin grades and soft inventory drawdown.",
            "usd_irr_delta_pct": 3,
            "gold_delta_pct": 5,
            "oil_delta_pct": 12,
            "feedstock_delta_pct": 28,
        },
        {
            "id": "soft_landing",
            "name_fa": "Soft landing (commodities↓)",
            "description_fa": "Calmer dollar and feedstock → opportunity to pre-buy materials without creating a purchase backlog, production to fill the sales queue.",
            "usd_irr_delta_pct": -6,
            "gold_delta_pct": -4,
            "oil_delta_pct": -10,
            "feedstock_delta_pct": -12,
        },
    ]


def resolve_macros(
    *,
    usd_irr: float | None = None,
    gold_irr_g: float | None = None,
    oil_usd: float | None = None,
    feedstock_basket_irr: float | None = None,
    usd_irr_delta_pct: float = 0,
    gold_delta_pct: float = 0,
    oil_delta_pct: float = 0,
    feedstock_delta_pct: float = 0,
    price_board: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base = _base_macros(price_board)
    usd = float(usd_irr if usd_irr is not None else base["usd_irr"]) * (1 + usd_irr_delta_pct / 100.0)
    gold = float(gold_irr_g if gold_irr_g is not None else base["gold_irr_g"]) * (1 + gold_delta_pct / 100.0)
    oil = float(oil_usd if oil_usd is not None else base["oil_usd"]) * (1 + oil_delta_pct / 100.0)
    feed = float(
        feedstock_basket_irr if feedstock_basket_irr is not None else base["feedstock_basket_irr"]
    ) * (1 + feedstock_delta_pct / 100.0)

    # Composite cost/pressure indices vs baseline
    usd_idx = usd / BASE_USD_IRR
    gold_idx = gold / BASE_GOLD_IRR_G
    oil_idx = oil / BASE_OIL_USD
    feed_idx = feed / max(base["feedstock_basket_irr"], 1)
    # Gold often co-moves with inflation expectations → soft domestic demand damper
    cost_pressure = 0.45 * feed_idx + 0.25 * oil_idx + 0.20 * gold_idx + 0.10 * usd_idx
    fx_tailwind = usd_idx  # >1 helps export IRR revenue

    return {
        "baseline": base,
        "current": {
            "usd_irr": round(usd, 0),
            "gold_irr_g": round(gold, 0),
            "oil_usd": round(oil, 2),
            "feedstock_basket_irr": round(feed, 0),
        },
        "deltas_pct": {
            "usd_irr": round((usd / BASE_USD_IRR - 1) * 100, 1),
            "gold_irr_g": round((gold / BASE_GOLD_IRR_G - 1) * 100, 1),
            "oil_usd": round((oil / BASE_OIL_USD - 1) * 100, 1),
            "feedstock_basket_irr": round((feed / max(base["feedstock_basket_irr"], 1) - 1) * 100, 1),
        },
        "indices": {
            "usd_idx": round(usd_idx, 3),
            "gold_idx": round(gold_idx, 3),
            "oil_idx": round(oil_idx, 3),
            "feed_idx": round(feed_idx, 3),
            "cost_pressure": round(cost_pressure, 3),
            "fx_tailwind": round(fx_tailwind, 3),
        },
    }


def _sales_queue_detail() -> dict[str, dict[str, float]]:
    """Weighted queue kg + open item count by grade."""
    out: dict[str, dict[str, float]] = {}
    for item in QUEUE_SEED:
        if item.get("status") == "cancelled":
            continue
        g = _norm_grade(str(item["grade"]))
        slot = out.setdefault(g, {"queue_kg": 0.0, "items": 0.0, "confirmed_kg": 0.0})
        w = float(item["requested_tonnage_kg"]) * float(item.get("probability", 0.6))
        slot["queue_kg"] += w
        slot["items"] += 1
        if item.get("status") == "confirmed":
            slot["confirmed_kg"] += float(item["requested_tonnage_kg"])
    return out


def _adjusted_margin(grade: str, macros: dict[str, Any]) -> float:
    base = MARGIN_HINT.get(grade, 0.10)
    intensity = FEEDSTOCK_INTENSITY.get(grade, 1.0)
    fx_beta = FX_EXPORT_BETA.get(grade, 0.7)
    idx = macros["indices"]
    # Feedstock/oil/gold raise costs more for oil-intense grades
    cost_hit = (idx["cost_pressure"] - 1.0) * 0.07 * intensity
    # USD strength lifts export-oriented IRR realization
    fx_lift = (idx["fx_tailwind"] - 1.0) * 0.05 * fx_beta
    return max(0.02, min(0.22, base - cost_hit + fx_lift))


def _recommend_action(
    *,
    grade: str,
    produce_kg: float,
    inventory_kg: float,
    queue_kg: float,
    demand_kg: float,
    margin: float,
    macros: dict[str, Any],
) -> tuple[str, str]:
    """Return (action_code, reason_fa)."""
    cover_days = (inventory_kg / (demand_kg / 30.0)) if demand_kg > 0 else 99
    cost_p = macros["indices"]["cost_pressure"]
    feed_idx = macros["indices"]["feed_idx"]

    if queue_kg > 5000 and inventory_kg < queue_kg * 0.5:
        return "produce_for_sales_queue", "Sales queue priority — insufficient inventory for queued orders"
    if cover_days > 45 and queue_kg < 3000:
        return "drawdown_inventory", "High inventory — production halted/reduced to prevent warehousing"
    if feed_idx > 1.15 and margin < 0.09:
        return "hold_low_margin", "Expensive feedstock and low margin — stock-building production prohibited"
    if cost_p > 1.12 and cover_days > 25:
        return "produce_queue_only", "Cost pressure — produce only the amount of the firm sales queue"
    if feed_idx < 0.92 and queue_kg > 0:
        return "produce_and_prebuy_feed", "Feedstock soft landing — produce for the queue + pre-buy materials without a purchase backlog"
    if margin >= 0.12 and macros["indices"]["fx_tailwind"] > 1.08:
        return "boost_export_grade", "Dollar↑ and good margin — increase the export share of this grade"
    if produce_kg > demand_kg * 1.15:
        return "trim_to_demand", "Reduce the plan to the demand level to prevent inventory build-up"
    return "balanced_produce", "Balanced production with sales queue coverage and inventory control"


def build_grade_plan_for_macros(
    macros: dict[str, Any],
    *,
    historical_monthly: dict[str, float] | None = None,
    inventory_by_grade: dict[str, float] | None = None,
    horizon_days: int = 30,
) -> list[dict[str, Any]]:
    demand_rows = build_demand_signals(historical_monthly=historical_monthly, horizon_days=horizon_days)
    queue_map = _sales_queue_detail()
    inv = inventory_by_grade or DEFAULT_INVENTORY_KG
    cost_p = macros["indices"]["cost_pressure"]
    fx = macros["indices"]["fx_tailwind"]
    feed_idx = macros["indices"]["feed_idx"]

    # Safety stock shrinks when warehousing risk / cost pressure high
    safety_factor = max(0.04, 0.12 - max(0.0, cost_p - 1.0) * 0.08 - max(0.0, (sum(inv.values()) / 1e6) * 0.01))

    rows: list[dict[str, Any]] = []
    for d in demand_rows:
        grade = d["product_grade"]
        q = queue_map.get(grade, {"queue_kg": 0.0, "items": 0.0, "confirmed_kg": 0.0})
        inv_kg = float(inv.get(grade, DEFAULT_INVENTORY_KG.get(grade, 50_000)))
        base_demand = float(d["demand_total_kg"])
        # Domestic softens slightly when gold/inflation pressure up; export lifts with USD
        domestic = base_demand * (1.0 - max(0.0, cost_p - 1.0) * 0.12)
        export_boost = base_demand * max(0.0, fx - 1.0) * 0.25 * FX_EXPORT_BETA.get(grade, 0.7)
        # Always cover sales queue first (anti sales-queue)
        queue_need = float(q["queue_kg"])
        effective_demand = max(queue_need * 1.05, domestic * 0.75 + export_boost + queue_need * 0.35)

        # Anti-warehouse: subtract excess inventory above ~20 days cover
        daily = max(effective_demand / horizon_days, 1.0)
        excess = max(0.0, inv_kg - daily * 20)
        net_need = max(0.0, effective_demand - excess * 0.85)
        safety = net_need * safety_factor
        # When feedstock spiked, do not build safety stock
        if feed_idx > 1.18:
            safety *= 0.25

        margin = _adjusted_margin(grade, macros)
        produce = net_need + safety
        # Cap speculative production if margin crushed
        if margin < 0.07:
            produce = min(produce, queue_need * 1.1 + max(0.0, effective_demand - inv_kg) * 0.5)

        action, reason = _recommend_action(
            grade=grade,
            produce_kg=produce,
            inventory_kg=inv_kg,
            queue_kg=queue_need,
            demand_kg=effective_demand,
            margin=margin,
            macros=macros,
        )

        # Feedstock purchase pressure from this grade plan (kg oil-equivalent proxy)
        feed_kg = produce * FEEDSTOCK_INTENSITY.get(grade, 1.0) * 1.35
        buy_advice = "hold"
        if feed_idx < 0.95:
            buy_advice = "prebuy_window"
        elif feed_idx > 1.2:
            buy_advice = "delay_noncritical"
        elif queue_need > inv_kg:
            buy_advice = "buy_for_queue"

        rows.append(
            {
                "product_grade": grade,
                "production_line": GRADE_LINE.get(grade, "Line_1"),
                "sales_queue_kg": round(queue_need, 0),
                "sales_queue_items": int(q["items"]),
                "confirmed_queue_kg": round(float(q["confirmed_kg"]), 0),
                "inventory_on_hand_kg": round(inv_kg, 0),
                "inventory_cover_days": round(inv_kg / daily, 1),
                "effective_demand_kg": round(effective_demand, 0),
                "excess_inventory_kg": round(excess, 0),
                "planned_produce_kg": round(produce, 0),
                "safety_stock_kg": round(safety, 0),
                "adjusted_margin": round(margin, 4),
                "base_margin": MARGIN_HINT.get(grade, 0.10),
                "feedstock_intensity": FEEDSTOCK_INTENSITY.get(grade, 1.0),
                "feedstock_need_kg": round(feed_kg, 0),
                "feedstock_buy_advice": buy_advice,
                "action": action,
                "reason_fa": reason,
                "priority_score": round(
                    queue_need / 1000.0 * 2.0
                    + margin * 100
                    + max(0.0, 30 - inv_kg / daily) * 0.5
                    - excess / 5000.0,
                    2,
                ),
            }
        )

    rows.sort(key=lambda r: r["priority_score"], reverse=True)
    return rows


def _scenario_balance_summary(grades: list[dict[str, Any]], macros: dict[str, Any]) -> dict[str, Any]:
    total_produce = sum(r["planned_produce_kg"] for r in grades)
    total_queue = sum(r["sales_queue_kg"] for r in grades)
    total_excess = sum(r["excess_inventory_kg"] for r in grades)
    total_feed = sum(r["feedstock_need_kg"] for r in grades)
    uncovered_queue = sum(max(0.0, r["sales_queue_kg"] - r["inventory_on_hand_kg"] - r["planned_produce_kg"] * 0.3) for r in grades)
    warehouse_risk = "High" if total_excess > 250_000 else ("Medium" if total_excess > 100_000 else "Low")
    sales_queue_risk = "High" if uncovered_queue > 40_000 else ("Medium" if uncovered_queue > 10_000 else "Low")
    purchase_queue_risk = (
        "High"
        if macros["indices"]["feed_idx"] > 1.2 and total_feed > 1_500_000
        else ("Medium" if macros["indices"]["feed_idx"] > 1.08 else "Low")
    )
    # Proxy realization price (IRR/kg) and feedstock basket (IRR/kg)
    avg_sell_irr = 185_000.0
    feed_price = float(macros["current"].get("feedstock_basket_irr") or 42_000)
    estimated_revenue_irr = sum(r["planned_produce_kg"] * avg_sell_irr for r in grades)
    estimated_feed_cost_irr = total_feed * feed_price
    estimated_gross_profit_irr = sum(
        r["planned_produce_kg"] * avg_sell_irr * float(r["adjusted_margin"]) for r in grades
    )
    # Net after inbound freight (~4.5% feed) + outbound distribution (~3.5% revenue)
    inbound_freight = estimated_feed_cost_irr * 0.045
    outbound_dist = estimated_revenue_irr * 0.035
    estimated_profit_irr = estimated_gross_profit_irr - inbound_freight - outbound_dist
    return {
        "total_produce_kg": round(total_produce, 0),
        "total_sales_queue_kg": round(total_queue, 0),
        "total_excess_inventory_kg": round(total_excess, 0),
        "total_feedstock_need_kg": round(total_feed, 0),
        "uncovered_sales_queue_kg": round(uncovered_queue, 0),
        "warehouse_risk": warehouse_risk,
        "sales_queue_risk": sales_queue_risk,
        "purchase_queue_risk": purchase_queue_risk,
        "estimated_revenue_irr": round(estimated_revenue_irr, 0),
        "estimated_feed_cost_irr": round(estimated_feed_cost_irr, 0),
        "estimated_gross_profit_irr": round(estimated_gross_profit_irr, 0),
        "estimated_profit_irr": round(estimated_profit_irr, 0),
        "balance_score": round(
            100
            - (10 if warehouse_risk == "High" else 5 if warehouse_risk == "Medium" else 0)
            - (12 if sales_queue_risk == "High" else 6 if sales_queue_risk == "Medium" else 0)
            - (10 if purchase_queue_risk == "High" else 5 if purchase_queue_risk == "Medium" else 0),
            0,
        ),
        "policy_fa": (
            "Priority 1: customer sales queue coverage · Priority 2: no inventory build-up · "
            "Priority 3: material purchasing only for the production plan (no extra purchase backlog)"
        ),
    }


def build_market_scenario_board(
    *,
    scenario_id: str | None = None,
    usd_irr: float | None = None,
    gold_irr_g: float | None = None,
    oil_usd: float | None = None,
    feedstock_basket_irr: float | None = None,
    usd_irr_delta_pct: float = 0,
    gold_delta_pct: float = 0,
    oil_delta_pct: float = 0,
    feedstock_delta_pct: float = 0,
    historical_monthly: dict[str, float] | None = None,
    inventory_by_grade: dict[str, float] | None = None,
    horizon_days: int = 30,
    price_board: dict[str, Any] | None = None,
    include_all_presets: bool = True,
) -> dict[str, Any]:
    """Full board: macros + selected scenario grade plan + optional all-preset comparison."""
    presets = {p["id"]: p for p in scenario_presets()}
    selected = presets.get(scenario_id or "baseline", presets["baseline"])

    # Merge preset deltas with explicit overrides (explicit deltas add on top if custom)
    macros = resolve_macros(
        usd_irr=usd_irr,
        gold_irr_g=gold_irr_g,
        oil_usd=oil_usd,
        feedstock_basket_irr=feedstock_basket_irr,
        usd_irr_delta_pct=selected["usd_irr_delta_pct"] + usd_irr_delta_pct,
        gold_delta_pct=selected["gold_delta_pct"] + gold_delta_pct,
        oil_delta_pct=selected["oil_delta_pct"] + oil_delta_pct,
        feedstock_delta_pct=selected["feedstock_delta_pct"] + feedstock_delta_pct,
        price_board=price_board,
    )

    grades = build_grade_plan_for_macros(
        macros,
        historical_monthly=historical_monthly,
        inventory_by_grade=inventory_by_grade,
        horizon_days=horizon_days,
    )
    summary = _scenario_balance_summary(grades, macros)
    pipeline = build_static_pipeline()

    comparisons: list[dict[str, Any]] = []
    if include_all_presets:
        for p in scenario_presets():
            m = resolve_macros(
                usd_irr_delta_pct=p["usd_irr_delta_pct"],
                gold_delta_pct=p["gold_delta_pct"],
                oil_delta_pct=p["oil_delta_pct"],
                feedstock_delta_pct=p["feedstock_delta_pct"],
                price_board=price_board,
            )
            g = build_grade_plan_for_macros(
                m,
                historical_monthly=historical_monthly,
                inventory_by_grade=inventory_by_grade,
                horizon_days=horizon_days,
            )
            s = _scenario_balance_summary(g, m)
            top = [x["product_grade"] for x in g[:3]]
            comparisons.append(
                {
                    "id": p["id"],
                    "name_fa": p["name_fa"],
                    "description_fa": p["description_fa"],
                    "macros": m["current"],
                    "deltas_pct": m["deltas_pct"],
                    "indices": m["indices"],
                    "summary": s,
                    "top_grades": top,
                    "recommended": s["balance_score"] >= 85,
                }
            )
        comparisons.sort(key=lambda c: c["summary"]["balance_score"], reverse=True)

    buy_actions = []
    for r in grades:
        if r["feedstock_buy_advice"] != "hold":
            buy_actions.append(
                {
                    "product_grade": r["product_grade"],
                    "advice": r["feedstock_buy_advice"],
                    "feedstock_need_kg": r["feedstock_need_kg"],
                    "note_fa": {
                        "prebuy_window": "Pre-buy window — favorable feedstock price; without creating an extra purchase backlog",
                        "delay_noncritical": "Delay non-essential purchases — raw material spike",
                        "buy_for_queue": "Buy only to cover the sales queue",
                    }.get(r["feedstock_buy_advice"], ""),
                }
            )

    return {
        "source": "Global market volatility (dollar · gold · oil · raw materials) → grade production scenario",
        "plan_date": str(date.today()),
        "horizon_days": horizon_days,
        "selected_scenario": {
            "id": selected["id"],
            "name_fa": selected["name_fa"],
            "description_fa": selected["description_fa"],
        },
        "macros": macros,
        "presets": scenario_presets(),
        "grades": grades,
        "summary": summary,
        "comparisons": comparisons,
        "feedstock_actions": buy_actions[:12],
        "sales_pipeline_summary": pipeline.get("summary"),
        "objectives_fa": [
            "Preventing finished-product warehousing",
            "Preventing a raw material purchase backlog",
            "Preventing unanswered sales backlog / customer orders",
        ],
    }
