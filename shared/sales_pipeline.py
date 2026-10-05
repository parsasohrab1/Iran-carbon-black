"""Sales CRM pipeline — active/potential customers and purchase queue helpers."""

from __future__ import annotations

from typing import Any

ACTIVE_CUSTOMERS: list[dict[str, Any]] = [
    {
        "id": "CUST-0047",
        "name": "Sahand Tire",
        "status": "active",
        "segment": "tire_manufacturer",
        "region": "domestic",
        "monthly_tonnage_kg": 15000,
        "annual_consumption_kg": 180000,
        "preferred_grades": ["N330", "N220"],
        "contact_person": "Eng. Rezaei",
    },
    {
        "id": "CUST-0012",
        "name": "Barez Rubber",
        "status": "active",
        "segment": "tire_manufacturer",
        "region": "domestic",
        "monthly_tonnage_kg": 18300,
        "annual_consumption_kg": 220000,
        "preferred_grades": ["N220", "N234"],
        "contact_person": "Ms. Karimi",
    },
    {
        "id": "CUST-0021",
        "name": "Kavir Tire",
        "status": "active",
        "segment": "tire_manufacturer",
        "region": "domestic",
        "monthly_tonnage_kg": 12500,
        "annual_consumption_kg": 150000,
        "preferred_grades": ["N550", "N660"],
        "contact_person": "Mr. Mousavi",
    },
    {
        "id": "CUST-0033",
        "name": "Iran Tire",
        "status": "active",
        "segment": "tire_manufacturer",
        "region": "domestic",
        "monthly_tonnage_kg": 16250,
        "annual_consumption_kg": 195000,
        "preferred_grades": ["N330", "N339"],
        "contact_person": "Eng. Ahmadi",
    },
    {
        "id": "CUST-0099",
        "name": "Export Partner UAE",
        "status": "active",
        "segment": "distributor",
        "region": "export",
        "monthly_tonnage_kg": 7900,
        "annual_consumption_kg": 95000,
        "preferred_grades": ["N550"],
        "contact_person": "Mr. Al-Farsi",
    },
    {
        "id": "CUST-0055",
        "name": "RubberTech TR",
        "status": "active",
        "segment": "compounder",
        "region": "export",
        "monthly_tonnage_kg": 5000,
        "annual_consumption_kg": 60000,
        "preferred_grades": ["N660"],
        "contact_person": "Ms. Yilmaz",
    },
    {
        "id": "CUST-0070",
        "name": "Cable Poly Iran",
        "status": "active",
        "segment": "industrial",
        "region": "domestic",
        "monthly_tonnage_kg": 3300,
        "annual_consumption_kg": 40000,
        "preferred_grades": ["N550", "N660"],
        "contact_person": "Eng. Nouri",
    },
]

POTENTIAL_CUSTOMERS: list[dict[str, Any]] = [
    {
        "id": "CUST-0101",
        "name": "Yazd Tire",
        "status": "potential",
        "segment": "tire_manufacturer",
        "region": "domestic",
        "monthly_tonnage_kg": 7500,
        "annual_consumption_kg": 90000,
        "preferred_grades": ["N330", "N220"],
        "contact_person": "Mr. Hosseini",
        "pipeline_stage": "technical_eval",
    },
    {
        "id": "CUST-0102",
        "name": "Dena Rubber",
        "status": "potential",
        "segment": "tire_manufacturer",
        "region": "domestic",
        "monthly_tonnage_kg": 9200,
        "annual_consumption_kg": 110000,
        "preferred_grades": ["N330", "N339"],
        "contact_person": "Ms. Moradi",
        "pipeline_stage": "sample",
    },
    {
        "id": "CUST-0103",
        "name": "Pars Rubber",
        "status": "potential",
        "segment": "compounder",
        "region": "domestic",
        "monthly_tonnage_kg": 3750,
        "annual_consumption_kg": 45000,
        "preferred_grades": ["N339", "N375"],
        "contact_person": "Eng. Kazemi",
        "pipeline_stage": "proposal",
    },
    {
        "id": "CUST-0104",
        "name": "Gulf Tire Co.",
        "status": "potential",
        "segment": "tire_manufacturer",
        "region": "export",
        "monthly_tonnage_kg": 10800,
        "annual_consumption_kg": 130000,
        "preferred_grades": ["N220", "N234"],
        "contact_person": "Mr. Rahman",
        "pipeline_stage": "commercial",
    },
    {
        "id": "CUST-0105",
        "name": "Arya Wire & Cable",
        "status": "potential",
        "segment": "industrial",
        "region": "domestic",
        "monthly_tonnage_kg": 2300,
        "annual_consumption_kg": 28000,
        "preferred_grades": ["N550", "N660"],
        "contact_person": "Ms. Jafari",
        "pipeline_stage": "discovery",
    },
]

QUEUE_SEED: list[dict[str, Any]] = [
    {"customer_id": "CUST-0047", "customer_name": "Sahand Tire", "grade": "N330", "requested_tonnage_kg": 18000, "priority": 1, "status": "queued", "probability": 0.85, "unit_price_irr": 188000},
    {"customer_id": "CUST-0012", "customer_name": "Barez Rubber", "grade": "N220", "requested_tonnage_kg": 22000, "priority": 1, "status": "queued", "probability": 0.90, "unit_price_irr": 196000},
    {"customer_id": "CUST-0012", "customer_name": "Barez Rubber", "grade": "N234", "requested_tonnage_kg": 12000, "priority": 2, "status": "negotiating", "probability": 0.70, "unit_price_irr": 205000},
    {"customer_id": "CUST-0033", "customer_name": "Iran Tire", "grade": "N330", "requested_tonnage_kg": 15000, "priority": 2, "status": "queued", "probability": 0.80, "unit_price_irr": 187000},
    {"customer_id": "CUST-0021", "customer_name": "Kavir Tire", "grade": "N550", "requested_tonnage_kg": 10000, "priority": 3, "status": "queued", "probability": 0.65, "unit_price_irr": 165000},
    {"customer_id": "CUST-0099", "customer_name": "Export Partner UAE", "grade": "N550", "requested_tonnage_kg": 9000, "priority": 2, "status": "confirmed", "probability": 0.95, "unit_price_irr": 172000},
    {"customer_id": "CUST-0055", "customer_name": "RubberTech TR", "grade": "N660", "requested_tonnage_kg": 6000, "priority": 3, "status": "queued", "probability": 0.60, "unit_price_irr": 158000},
    {"customer_id": "CUST-0101", "customer_name": "Yazd Tire", "grade": "N330", "requested_tonnage_kg": 8000, "priority": 2, "status": "queued", "probability": 0.45, "unit_price_irr": 185000},
    {"customer_id": "CUST-0102", "customer_name": "Dena Rubber", "grade": "N339", "requested_tonnage_kg": 7000, "priority": 3, "status": "negotiating", "probability": 0.40, "unit_price_irr": 190000},
    {"customer_id": "CUST-0104", "customer_name": "Gulf Tire Co.", "grade": "N220", "requested_tonnage_kg": 14000, "priority": 1, "status": "queued", "probability": 0.55, "unit_price_irr": 210000},
    {"customer_id": "CUST-0103", "customer_name": "Pars Rubber", "grade": "N375", "requested_tonnage_kg": 4500, "priority": 4, "status": "queued", "probability": 0.35, "unit_price_irr": 192000},
    {"customer_id": "CUST-0105", "customer_name": "Arya Wire & Cable", "grade": "N550", "requested_tonnage_kg": 3000, "priority": 4, "status": "queued", "probability": 0.30, "unit_price_irr": 160000},
]


def build_static_pipeline() -> dict[str, Any]:
    active = ACTIVE_CUSTOMERS
    potential = POTENTIAL_CUSTOMERS
    queue = QUEUE_SEED
    by_grade: dict[str, dict[str, float]] = {}
    for item in queue:
        if item["status"] == "cancelled":
            continue
        g = item["grade"]
        slot = by_grade.setdefault(g, {"requested_kg": 0.0, "weighted_kg": 0.0, "expected_revenue_irr": 0.0})
        ton = float(item["requested_tonnage_kg"])
        prob = float(item["probability"])
        price = float(item["unit_price_irr"])
        slot["requested_kg"] += ton
        slot["weighted_kg"] += ton * prob
        slot["expected_revenue_irr"] += ton * prob * price

    forecasts = []
    for grade, agg in sorted(by_grade.items()):
        forecasts.append(
            {
                "grade": grade,
                "base_ml_quantity_kg": round(agg["weighted_kg"] * 0.35, 1),
                "queue_requested_kg": round(agg["requested_kg"], 1),
                "queue_weighted_kg": round(agg["weighted_kg"], 1),
                "forecast_quantity_kg": round(agg["weighted_kg"] * 0.35 + agg["weighted_kg"], 1),
                "forecast_revenue_irr": round(agg["expected_revenue_irr"] + agg["weighted_kg"] * 0.35 * 180000, 0),
                "recommended_unit_price": 180000,
                "pipeline_share_pct": 100.0,
                "source": "catalog+queue",
            }
        )

    return {
        "source": "static sales pipeline catalog",
        "active_customers": active,
        "potential_customers": potential,
        "purchase_queue": queue,
        "summary": {
            "active_count": len(active),
            "potential_count": len(potential),
            "queue_items": len(queue),
            "active_monthly_tonnage_kg": sum(c["monthly_tonnage_kg"] for c in active),
            "potential_monthly_tonnage_kg": sum(c["monthly_tonnage_kg"] for c in potential),
            "queue_requested_tonnage_kg": sum(q["requested_tonnage_kg"] for q in queue),
            "queue_weighted_tonnage_kg": round(sum(q["requested_tonnage_kg"] * q["probability"] for q in queue), 1),
        },
        "sales_forecast_with_queue": forecasts,
    }


def _is_garbled(value: Any) -> bool:
    if value is None:
        return True
    text = str(value)
    if not text.strip():
        return True
    if "\ufffd" in text:
        return True
    q = text.count("?")
    return q >= max(1, len(text) // 3)


def _customer_catalog() -> dict[str, dict[str, Any]]:
    return {c["id"]: c for c in (*ACTIVE_CUSTOMERS, *POTENTIAL_CUSTOMERS)}


def sanitize_customer_row(row: dict[str, Any], catalog: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    cat = catalog or _customer_catalog()
    base = cat.get(str(row.get("id") or ""), {})
    out = {**base, **row}
    for key in ("name", "contact_person", "notes", "region"):
        if key in base and (_is_garbled(out.get(key)) or key in ("name", "contact_person")):
            out[key] = base[key]
        elif key == "notes" and _is_garbled(out.get(key)):
            out[key] = None
    if base.get("preferred_grades") and (
        not out.get("preferred_grades")
        or (isinstance(out.get("preferred_grades"), list) and all(_is_garbled(g) for g in out["preferred_grades"]))
    ):
        out["preferred_grades"] = list(base["preferred_grades"])
    return out


def sanitize_pipeline_board(board: dict[str, Any]) -> dict[str, Any]:
    """Overlay Persian CRM labels from catalog so DB ??? never reaches the UI."""
    catalog = _customer_catalog()
    active = [sanitize_customer_row(dict(c), catalog) for c in board.get("active_customers") or []]
    potential = [sanitize_customer_row(dict(c), catalog) for c in board.get("potential_customers") or []]
    queue = []
    for q in board.get("purchase_queue") or []:
        item = dict(q)
        cid = str(item.get("customer_id") or "")
        base = catalog.get(cid, {})
        if base and (_is_garbled(item.get("customer_name")) or not item.get("customer_name")):
            item["customer_name"] = base.get("name")
        if _is_garbled(item.get("notes")):
            item["notes"] = None
        queue.append(item)
    # Ensure catalog customers appear if DB missed some
    seen_a = {c["id"] for c in active}
    seen_p = {c["id"] for c in potential}
    for c in ACTIVE_CUSTOMERS:
        if c["id"] not in seen_a:
            active.append(dict(c))
    for c in POTENTIAL_CUSTOMERS:
        if c["id"] not in seen_p:
            potential.append(dict(c))
    out = dict(board)
    out["active_customers"] = active
    out["potential_customers"] = potential
    out["purchase_queue"] = queue
    summary = dict(board.get("summary") or {})
    summary["active_count"] = len(active)
    summary["potential_count"] = len(potential)
    summary["queue_items"] = len(queue)
    summary["active_monthly_tonnage_kg"] = round(sum(float(c.get("monthly_tonnage_kg") or 0) for c in active), 1)
    summary["potential_monthly_tonnage_kg"] = round(
        sum(float(c.get("monthly_tonnage_kg") or 0) for c in potential), 1
    )
    out["summary"] = summary
    return out
