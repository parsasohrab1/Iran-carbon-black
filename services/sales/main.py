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


@router.get("/customers")
async def list_customers(db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(
        text(
            """
            SELECT c.id, c.name, c.segment, c.industry, c.annual_consumption_kg, c.region,
                   p.preferred_grades, p.churn_risk, p.lifetime_value_irr, p.last_order_date
            FROM sales.customers c
            LEFT JOIN sales.customer_profiles p ON p.customer_id = c.id
            ORDER BY c.name
            """
        )
    )
    return [dict(r) for r in result.mappings().all()]


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
    return [dict(r) for r in result.mappings().all()]


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


app.include_router(router)
