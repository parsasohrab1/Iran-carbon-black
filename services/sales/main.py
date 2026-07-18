"""Sales & marketing — Phase 3 ML forecast, pricing, CRM."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.app_factory import create_app
from shared.config import get_settings
from shared.db import get_db
from shared.export_markets import (
    build_export_forecast,
    build_static_export_board,
    merge_markets_with_catalog,
)
from shared.sales_pipeline import build_static_pipeline, sanitize_customer_row, sanitize_pipeline_board
from services.sales.models import load_sales_artifact, run_sales_forecast

settings = get_settings()


@asynccontextmanager
async def lifespan(app):  # noqa: ANN001, ARG001
    load_sales_artifact()
    yield


app = create_app(settings, title="ICB Sales Service", version="3.0.0", lifespan=lifespan)
router = APIRouter(prefix="/api/v1/sales", tags=["sales"])


class SalesForecastRequest(BaseModel):
    grade: str | None = None
    months_ahead: int = Field(default=1, ge=1, le=6)
    tire_production_index: float = 112.0
    usd_irr_rate: float = 245000.0
    crude_oil_price_usd: float = 78.0
    include_purchase_queue: bool = True


class QueueItemCreate(BaseModel):
    customer_id: str
    grade: str
    requested_tonnage_kg: float = Field(gt=0)
    priority: int = Field(default=3, ge=1, le=5)
    status: str = "queued"
    expected_close_date: date | None = None
    unit_price_irr: float | None = None
    probability: float = Field(default=0.6, ge=0, le=1)
    notes: str | None = None


class PriceRequest(BaseModel):
    grade: str
    region: str = "domestic"
    current_price_irr: float | None = None


class InteractionRequest(BaseModel):
    customer_id: str
    interaction_type: str = Field(description="call|meeting|complaint|opportunity")
    subject: str | None = None
    detail: dict | None = None


class ProfileUpdate(BaseModel):
    preferred_grades: list[str] | None = None
    needs: dict | None = None
    notes: str | None = None


OPEN_QUEUE_STATUSES = ("queued", "negotiating", "confirmed")


async def _queue_demand_by_grade(db: AsyncSession, grade: str | None = None) -> dict[str, dict]:
    params: dict = {}
    grade_filter = ""
    if grade:
        grade_filter = "AND q.grade = :grade"
        params["grade"] = grade
    result = await db.execute(
        text(
            f"""
            SELECT q.grade,
                   SUM(q.requested_tonnage_kg) AS requested_kg,
                   SUM(q.requested_tonnage_kg * COALESCE(q.probability, 0.6)) AS weighted_kg,
                   SUM(q.requested_tonnage_kg * COALESCE(q.probability, 0.6)
                       * COALESCE(q.unit_price_irr, 180000)) AS expected_revenue_irr,
                   COUNT(*) AS items
            FROM sales.purchase_queue q
            WHERE q.status IN ('queued', 'negotiating', 'confirmed')
            {grade_filter}
            GROUP BY q.grade
            """
        ),
        params,
    )
    return {r["grade"]: dict(r) for r in result.mappings().all()}


@router.get("/customers")
async def list_customers(status: str | None = None, db: AsyncSession = Depends(get_db)) -> list[dict]:
    params: dict = {}
    status_filter = ""
    if status:
        status_filter = "AND COALESCE(c.status, 'active') = :status"
        params["status"] = status
    result = await db.execute(
        text(
            f"""
            SELECT c.id, c.name, c.segment, c.industry, c.annual_consumption_kg, c.region,
                   COALESCE(c.status, 'active') AS status,
                   COALESCE(c.monthly_tonnage_kg, c.annual_consumption_kg / 12.0) AS monthly_tonnage_kg,
                   c.contact_person, c.notes,
                   p.preferred_grades, p.churn_risk, p.lifetime_value_irr, p.last_order_date,
                   p.needs->>'stage' AS pipeline_stage
            FROM sales.customers c
            LEFT JOIN sales.customer_profiles p ON p.customer_id = c.id
            WHERE TRUE {status_filter}
            ORDER BY COALESCE(c.monthly_tonnage_kg, 0) DESC, c.name
            """
        ),
        params,
    )
    rows = [dict(r) for r in result.mappings().all()]
    for row in rows:
        grades = row.get("preferred_grades")
        if isinstance(grades, str):
            try:
                row["preferred_grades"] = json.loads(grades)
            except json.JSONDecodeError:
                pass
    return [sanitize_customer_row(r) for r in rows]


@router.get("/customers/{customer_id}")
async def customer_detail(customer_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    cust = await db.execute(
        text(
            """
            SELECT c.*, p.preferred_grades, p.avg_order_kg, p.churn_risk, p.lifetime_value_irr,
                   p.needs, p.notes, p.updated_at AS profile_updated_at
            FROM sales.customers c
            LEFT JOIN sales.customer_profiles p ON p.customer_id = c.id
            WHERE c.id = :id
            """
        ),
        {"id": customer_id},
    )
    row = cust.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Customer not found")

    orders = await db.execute(
        text(
            """
            SELECT sale_date, grade, quantity_kg, unit_price_irr, total_price_irr, region
            FROM sales.orders WHERE customer_id = :id
            ORDER BY sale_date DESC LIMIT 20
            """
        ),
        {"id": customer_id},
    )
    interactions = await db.execute(
        text(
            """
            SELECT id, interaction_type, subject, detail, created_at
            FROM sales.interactions WHERE customer_id = :id
            ORDER BY created_at DESC LIMIT 20
            """
        ),
        {"id": customer_id},
    )
    return {
        "customer": dict(row),
        "recent_orders": [dict(r) for r in orders.mappings().all()],
        "interactions": [dict(r) for r in interactions.mappings().all()],
    }


@router.patch("/customers/{customer_id}/profile")
async def update_profile(customer_id: str, body: ProfileUpdate, db: AsyncSession = Depends(get_db)) -> dict:
    exists = await db.execute(text("SELECT id FROM sales.customers WHERE id = :id"), {"id": customer_id})
    if not exists.first():
        raise HTTPException(status_code=404, detail="Customer not found")
    await db.execute(
        text(
            """
            INSERT INTO sales.customer_profiles (customer_id, preferred_grades, needs, notes, updated_at)
            VALUES (:id, :grades::jsonb, :needs::jsonb, :notes, NOW())
            ON CONFLICT (customer_id) DO UPDATE SET
                preferred_grades = COALESCE(EXCLUDED.preferred_grades, sales.customer_profiles.preferred_grades),
                needs = COALESCE(EXCLUDED.needs, sales.customer_profiles.needs),
                notes = COALESCE(EXCLUDED.notes, sales.customer_profiles.notes),
                updated_at = NOW()
            """
        ),
        {
            "id": customer_id,
            "grades": json.dumps(body.preferred_grades) if body.preferred_grades is not None else None,
            "needs": json.dumps(body.needs) if body.needs is not None else None,
            "notes": body.notes,
        },
    )
    await db.commit()
    return {"status": "updated", "customer_id": customer_id}


@router.post("/customers/{customer_id}/interactions")
async def add_interaction(customer_id: str, body: InteractionRequest, db: AsyncSession = Depends(get_db)) -> dict:
    await db.execute(
        text(
            """
            INSERT INTO sales.interactions (customer_id, interaction_type, subject, detail)
            VALUES (:cid, :itype, :subject, :detail::jsonb)
            """
        ),
        {
            "cid": customer_id,
            "itype": body.interaction_type,
            "subject": body.subject,
            "detail": json.dumps(body.detail or {}),
        },
    )
    await db.commit()
    return {"status": "created", "customer_id": customer_id}


@router.get("/crm/at-risk")
async def at_risk_customers(threshold: float = 0.2, db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(
        text(
            """
            SELECT c.id, c.name, c.segment, p.churn_risk, p.lifetime_value_irr, p.preferred_grades
            FROM sales.customer_profiles p
            JOIN sales.customers c ON c.id = p.customer_id
            WHERE p.churn_risk >= :th
            ORDER BY p.churn_risk DESC
            """
        ),
        {"th": threshold},
    )
    return [sanitize_customer_row(dict(r)) for r in result.mappings().all()]


@router.get("/orders")
async def list_orders(limit: int = 100, db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(
        text(
            """
            SELECT id, sale_date, customer_id, grade, quantity_kg, unit_price_irr, total_price_irr, region
            FROM sales.orders ORDER BY sale_date DESC LIMIT :limit
            """
        ),
        {"limit": limit},
    )
    return [dict(r) for r in result.mappings().all()]


@router.post("/forecast")
async def forecast_sales(body: SalesForecastRequest, db: AsyncSession = Depends(get_db)) -> dict:
    """SM-01 ML sales forecast (target accuracy ≥ 85%)."""
    params: dict = {}
    grade_filter = ""
    if body.grade:
        grade_filter = "AND grade = :grade"
        params["grade"] = body.grade

    result = await db.execute(
        text(
            f"""
            SELECT date_trunc('month', sale_date)::date AS month,
                   SUM(quantity_kg) AS qty,
                   AVG(unit_price_irr) AS avg_price,
                   SUM(total_price_irr) AS revenue
            FROM sales.orders
            WHERE TRUE {grade_filter}
            GROUP BY 1
            ORDER BY 1 DESC
            LIMIT 12
            """
        ),
        params,
    )
    rows = list(result.mappings().all())
    history_qty = [float(r["qty"]) for r in reversed(rows)] if rows else []
    recent_price = float(rows[0]["avg_price"]) if rows and rows[0]["avg_price"] is not None else None

    prediction = run_sales_forecast(
        grade=body.grade,
        months_ahead=body.months_ahead,
        history_qty=history_qty,
        recent_price=recent_price,
        tire_production_index=body.tire_production_index,
        usd_irr_rate=body.usd_irr_rate,
        crude_oil_price_usd=body.crude_oil_price_usd,
    )

    queue_requested = 0.0
    queue_weighted = 0.0
    queue_revenue = 0.0
    if body.include_purchase_queue:
        try:
            demand = await _queue_demand_by_grade(db, body.grade)
            if body.grade and body.grade in demand:
                slots = [demand[body.grade]]
            else:
                slots = list(demand.values())
            queue_requested = sum(float(s["requested_kg"] or 0) for s in slots)
            queue_weighted = sum(float(s["weighted_kg"] or 0) for s in slots)
            queue_revenue = sum(float(s["expected_revenue_irr"] or 0) for s in slots)
        except Exception:  # noqa: BLE001
            queue_requested = queue_weighted = queue_revenue = 0.0

    base_qty = float(prediction["forecast_quantity_kg"])
    base_rev = float(prediction["forecast_revenue_irr"])
    combined_qty = round(base_qty + queue_weighted, 2)
    combined_rev = round(base_rev + queue_revenue, 2)
    prediction["base_ml_quantity_kg"] = base_qty
    prediction["base_ml_revenue_irr"] = base_rev
    prediction["queue_requested_kg"] = round(queue_requested, 2)
    prediction["queue_weighted_kg"] = round(queue_weighted, 2)
    prediction["forecast_quantity_kg"] = combined_qty
    prediction["forecast_revenue_irr"] = combined_rev
    prediction["pipeline_share_pct"] = round((queue_weighted / combined_qty) * 100, 1) if combined_qty else 0.0

    await db.execute(
        text(
            """
            INSERT INTO sales.forecasts (
                grade, months_ahead, forecast_quantity_kg, forecast_revenue_irr,
                recommended_unit_price, confidence, model_version
            ) VALUES (:grade, :months, :qty, :rev, :price, :conf, :mv)
            """
        ),
        {
            "grade": prediction["grade"],
            "months": body.months_ahead,
            "qty": prediction["forecast_quantity_kg"],
            "rev": prediction["forecast_revenue_irr"],
            "price": prediction["recommended_unit_price_irr"],
            "conf": prediction["confidence"],
            "mv": prediction["model_version"],
        },
    )
    await db.commit()
    return {
        "forecast_date": str(date.today()),
        "history_months_used": len(rows),
        "history": [
            {"month": str(r["month"]), "quantity_kg": float(r["qty"]), "revenue_irr": float(r["revenue"])}
            for r in reversed(rows)
        ],
        "includes_purchase_queue": body.include_purchase_queue,
        **prediction,
    }


@router.post("/pricing/recommend")
async def recommend_price(body: PriceRequest, db: AsyncSession = Depends(get_db)) -> dict:
    """SM-02 pricing recommendation for domestic/export markets."""
    result = await db.execute(
        text(
            """
            SELECT AVG(unit_price_irr) AS avg_price, SUM(quantity_kg) AS qty
            FROM sales.orders
            WHERE grade = :grade AND region = :region
              AND sale_date > CURRENT_DATE - INTERVAL '90 days'
            """
        ),
        {"grade": body.grade, "region": body.region},
    )
    row = result.mappings().first()
    current = body.current_price_irr or (float(row["avg_price"]) if row and row["avg_price"] else None)
    history_qty = [float(row["qty"])] if row and row["qty"] else [15000.0]
    prediction = run_sales_forecast(
        grade=body.grade,
        months_ahead=1,
        history_qty=history_qty,
        recent_price=current,
    )
    # Export premium
    rec_price = prediction["recommended_unit_price_irr"]
    if body.region == "export":
        rec_price = round(rec_price * 1.04, 2)
        rationale = prediction["pricing_rationale"] + " Export premium applied (+4%)."
    else:
        rationale = prediction["pricing_rationale"]

    await db.execute(
        text(
            """
            INSERT INTO sales.price_recommendations
                (grade, region, current_price_irr, recommended_price_irr, rationale, model_version)
            VALUES (:grade, :region, :current, :rec, :rationale, :mv)
            """
        ),
        {
            "grade": body.grade,
            "region": body.region,
            "current": current,
            "rec": rec_price,
            "rationale": rationale,
            "mv": prediction["model_version"],
        },
    )
    await db.commit()
    return {
        "grade": body.grade,
        "region": body.region,
        "current_price_irr": current,
        "recommended_price_irr": rec_price,
        "rationale": rationale,
        "model_version": prediction["model_version"],
    }


@router.get("/forecasts")
async def list_forecasts(limit: int = 20, db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(
        text(
            """
            SELECT forecast_date, grade, months_ahead, forecast_quantity_kg, forecast_revenue_irr,
                   recommended_unit_price, confidence, model_version, created_at
            FROM sales.forecasts ORDER BY created_at DESC LIMIT :limit
            """
        ),
        {"limit": limit},
    )
    return [dict(r) for r in result.mappings().all()]


@router.get("/model/info")
async def model_info() -> dict:
    artifact = load_sales_artifact()
    return {"model_version": artifact.get("model_version"), "metrics": artifact.get("metrics"), "grades": artifact.get("grades")}


@router.get("/pipeline/queue")
async def list_purchase_queue(status: str | None = None, db: AsyncSession = Depends(get_db)) -> list[dict]:
    params: dict = {}
    status_filter = ""
    if status:
        status_filter = "AND q.status = :status"
        params["status"] = status
    result = await db.execute(
        text(
            f"""
            SELECT q.id, q.customer_id, c.name AS customer_name, c.status AS customer_status,
                   COALESCE(c.monthly_tonnage_kg, c.annual_consumption_kg / 12.0) AS customer_monthly_tonnage_kg,
                   q.grade, q.requested_tonnage_kg, q.priority, q.status, q.expected_close_date,
                   q.unit_price_irr, q.probability, q.source, q.notes, q.created_at,
                   (q.requested_tonnage_kg * COALESCE(q.probability, 0.6)) AS weighted_tonnage_kg,
                   (q.requested_tonnage_kg * COALESCE(q.probability, 0.6)
                    * COALESCE(q.unit_price_irr, 180000)) AS expected_revenue_irr
            FROM sales.purchase_queue q
            JOIN sales.customers c ON c.id = q.customer_id
            WHERE TRUE {status_filter}
            ORDER BY q.priority ASC, q.expected_close_date NULLS LAST, q.created_at DESC
            """
        ),
        params,
    )
    return [dict(r) for r in result.mappings().all()]


@router.post("/pipeline/queue")
async def create_queue_item(body: QueueItemCreate, db: AsyncSession = Depends(get_db)) -> dict:
    exists = await db.execute(text("SELECT id FROM sales.customers WHERE id = :id"), {"id": body.customer_id})
    if not exists.first():
        raise HTTPException(status_code=404, detail="Customer not found")
    result = await db.execute(
        text(
            """
            INSERT INTO sales.purchase_queue (
                customer_id, grade, requested_tonnage_kg, priority, status,
                expected_close_date, unit_price_irr, probability, notes
            ) VALUES (
                :cid, :grade, :ton, :priority, :status,
                :close, :price, :prob, :notes
            )
            RETURNING id
            """
        ),
        {
            "cid": body.customer_id,
            "grade": body.grade,
            "ton": body.requested_tonnage_kg,
            "priority": body.priority,
            "status": body.status,
            "close": body.expected_close_date,
            "price": body.unit_price_irr,
            "prob": body.probability,
            "notes": body.notes,
        },
    )
    await db.commit()
    row = result.first()
    return {"status": "created", "id": row[0] if row else None}


@router.get("/pipeline/dashboard")
async def pipeline_dashboard(db: AsyncSession = Depends(get_db)) -> dict:
    """Active/potential customers, purchase queue, and sales forecast with queue uplift."""
    fallback = build_static_pipeline()
    try:
        active = await list_customers(status="active", db=db)
        potential = await list_customers(status="potential", db=db)
        queue = await list_purchase_queue(db=db)
        demand = await _queue_demand_by_grade(db)

        forecasts = []
        for grade, agg in sorted(demand.items()):
            history = await db.execute(
                text(
                    """
                    SELECT COALESCE(SUM(quantity_kg), 0) AS qty, COALESCE(AVG(unit_price_irr), 180000) AS avg_price
                    FROM sales.orders
                    WHERE grade = :grade AND sale_date > CURRENT_DATE - INTERVAL '90 days'
                    """
                ),
                {"grade": grade},
            )
            hist = history.mappings().first()
            base = run_sales_forecast(
                grade=grade,
                months_ahead=1,
                history_qty=[float(hist["qty"])] if hist and float(hist["qty"]) > 0 else [float(agg["weighted_kg"])],
                recent_price=float(hist["avg_price"]) if hist else 180000.0,
            )
            base_qty = float(base["forecast_quantity_kg"])
            queue_w = float(agg["weighted_kg"] or 0)
            queue_r = float(agg["requested_kg"] or 0)
            queue_rev = float(agg["expected_revenue_irr"] or 0)
            combined = base_qty + queue_w
            forecasts.append(
                {
                    "grade": grade,
                    "base_ml_quantity_kg": round(base_qty, 1),
                    "queue_requested_kg": round(queue_r, 1),
                    "queue_weighted_kg": round(queue_w, 1),
                    "forecast_quantity_kg": round(combined, 1),
                    "forecast_revenue_irr": round(float(base["forecast_revenue_irr"]) + queue_rev, 0),
                    "recommended_unit_price": base["recommended_unit_price_irr"],
                    "pipeline_share_pct": round((queue_w / combined) * 100, 1) if combined else 0.0,
                    "queue_items": int(agg["items"] or 0),
                    "confidence": base.get("confidence"),
                    "source": "ml+purchase_queue",
                }
            )

            await db.execute(
                text(
                    """
                    INSERT INTO sales.forecasts (
                        grade, months_ahead, forecast_quantity_kg, forecast_revenue_irr,
                        recommended_unit_price, confidence, model_version
                    ) VALUES (:grade, 1, :qty, :rev, :price, :conf, :mv)
                    """
                ),
                {
                    "grade": grade,
                    "qty": round(combined, 1),
                    "rev": round(float(base["forecast_revenue_irr"]) + queue_rev, 0),
                    "price": base["recommended_unit_price_irr"],
                    "conf": base.get("confidence"),
                    "mv": f"{base.get('model_version', 'sales')}+queue",
                },
            )
        await db.commit()

        return sanitize_pipeline_board(
            {
                "source": "sales.customers + purchase_queue + ML forecast",
                "active_customers": active,
                "potential_customers": potential,
                "purchase_queue": queue,
                "summary": {
                    "active_count": len(active),
                    "potential_count": len(potential),
                    "queue_items": len(queue),
                    "active_monthly_tonnage_kg": round(
                        sum(float(c.get("monthly_tonnage_kg") or 0) for c in active), 1
                    ),
                    "potential_monthly_tonnage_kg": round(
                        sum(float(c.get("monthly_tonnage_kg") or 0) for c in potential), 1
                    ),
                    "queue_requested_tonnage_kg": round(
                        sum(float(q.get("requested_tonnage_kg") or 0) for q in queue), 1
                    ),
                    "queue_weighted_tonnage_kg": round(
                        sum(float(q.get("weighted_tonnage_kg") or 0) for q in queue), 1
                    ),
                },
                "sales_forecast_with_queue": forecasts,
            }
        )
    except Exception:  # noqa: BLE001
        return fallback


@router.get("/export/board")
async def export_board(db: AsyncSession = Depends(get_db)) -> dict:
    """Actual/potential export markets + 6-month forecast (Codal/IRICA/TPO references)."""
    fallback = build_static_export_board()
    try:
        markets_q = await db.execute(
            text(
                """
                SELECT id, country_fa, country_en, status, region, annual_tonnage_kg, ytd_tonnage_kg,
                       share_pct, main_grades, avg_fob_usd, growth_yoy_pct, buyers, logistics, risk,
                       pipeline_stage, probability, source_refs
                FROM sales.export_markets
                ORDER BY CASE WHEN status = 'actual' THEN 0 ELSE 1 END, annual_tonnage_kg DESC
                """
            )
        )
        rows = [dict(r) for r in markets_q.mappings().all()]
        if not rows:
            return fallback

        for r in rows:
            if r.get("main_grades") is not None:
                r["main_grades"] = list(r["main_grades"])
            if r.get("source_refs") is not None:
                r["source_refs"] = list(r["source_refs"])

        rows = merge_markets_with_catalog(rows)
        actual = [r for r in rows if r.get("status") == "actual"]
        potential = [r for r in rows if r.get("status") == "potential"]
        # Forecast from catalog tonnage/probability (stable) while preserving DB numeric overrides already merged
        forecast = build_export_forecast(actual, potential)

        for f in forecast:
            month_date = date.fromisoformat(f"{f['month']}-01")
            await db.execute(
                text(
                    """
                    INSERT INTO sales.export_forecasts (
                        forecast_month, baseline_tonnage_kg, pipeline_uplift_kg, forecast_tonnage_kg,
                        forecast_revenue_usd, forecast_revenue_irr, avg_fob_usd, confidence,
                        model_version, source
                    ) VALUES (
                        :m, :base, :uplift, :qty, :usd, :irr, :fob, :conf, :mv, 'live-board'
                    )
                    ON CONFLICT (forecast_month, model_version) DO UPDATE SET
                        baseline_tonnage_kg = EXCLUDED.baseline_tonnage_kg,
                        pipeline_uplift_kg = EXCLUDED.pipeline_uplift_kg,
                        forecast_tonnage_kg = EXCLUDED.forecast_tonnage_kg,
                        forecast_revenue_usd = EXCLUDED.forecast_revenue_usd,
                        forecast_revenue_irr = EXCLUDED.forecast_revenue_irr,
                        confidence = EXCLUDED.confidence,
                        created_at = NOW()
                    """
                ),
                {
                    "m": month_date,
                    "base": f["baseline_tonnage_kg"],
                    "uplift": f["pipeline_uplift_kg"],
                    "qty": f["forecast_tonnage_kg"],
                    "usd": f["forecast_revenue_usd"],
                    "irr": f["forecast_revenue_irr"],
                    "fob": f["avg_fob_usd"],
                    "conf": f["confidence"],
                    "mv": f["model_version"],
                },
            )
        await db.commit()

        ytd = sum(float(m.get("ytd_tonnage_kg") or 0) for m in actual)
        annual = sum(float(m.get("annual_tonnage_kg") or 0) for m in actual)
        potential_annual = sum(
            float(m.get("annual_tonnage_kg") or 0) * float(m.get("probability") or 0.4) for m in potential
        )
        return {
            "source": "sales.export_markets + Codal/IRICA/TPO reference board",
            "hs_code": fallback["hs_code"],
            "product": fallback["product"],
            "company": fallback["company"],
            "iranian_sources": fallback["iranian_sources"],
            "actual_markets": actual,
            "potential_markets": potential,
            "export_forecast": forecast,
            "summary": {
                "actual_markets_count": len(actual),
                "potential_markets_count": len(potential),
                "ytd_export_tonnage_kg": ytd,
                "annual_actual_tonnage_kg": annual,
                "potential_weighted_tonnage_kg": round(potential_annual, 0),
                "next_month_forecast_kg": forecast[0]["forecast_tonnage_kg"] if forecast else 0,
                "six_month_forecast_kg": round(sum(f["forecast_tonnage_kg"] for f in forecast), 0),
                "six_month_revenue_usd": round(sum(f["forecast_revenue_usd"] for f in forecast), 0),
                "top_market": actual[0]["country_fa"] if actual else "—",
                "avg_growth_yoy_pct": round(
                    sum(float(m.get("growth_yoy_pct") or 0) for m in actual) / max(len(actual), 1), 1
                ),
            },
        }
    except Exception:  # noqa: BLE001
        return fallback


app.include_router(router)
