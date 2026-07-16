"""Demand-driven smart production — Phase 2 ML forecasts + planning."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.app_factory import create_app
from shared.config import get_settings
from shared.db import get_db
from services.demand.models import load_demand_artifact, run_forecast, run_recommend
from ml.demand.train_forecast import GRADES

settings = get_settings()


@asynccontextmanager
async def lifespan(app):  # noqa: ANN001, ARG001
    load_demand_artifact()
    yield


app = create_app(settings, title="ICB Demand Service", version="2.0.0", lifespan=lifespan)
router = APIRouter(prefix="/api/v1/demand", tags=["demand"])


class DemandForecastRequest(BaseModel):
    product_grade: str
    forecast_period: str = Field(default="3_months", pattern="^(1_month|3_months|6_months)$")
    tire_industry_growth: float = 0.04
    exchange_rate_volatility: float = 0.1
    crude_oil_price_usd: float = 78.0


class GradeRecommendRequest(BaseModel):
    conductivity: str = Field(description="low|medium|high|very_high|very_low")
    dispersion: str = Field(description="low|medium|high|very_high")
    tint_strength: str = Field(description="low|medium|high|very_high|very_low")
    prefer_margin: bool = True


class ProductionPlanRequest(BaseModel):
    forecast_period: str = Field(default="3_months", pattern="^(1_month|3_months|6_months)$")
    grades: list[str] | None = None
    tire_industry_growth: float = 0.04
    exchange_rate_volatility: float = 0.1
    prioritize_margin: bool = True


@router.get("/grades")
async def list_grades() -> dict:
    artifact = load_demand_artifact()
    return {"grades": artifact["grades"], "properties": artifact["grade_properties"]}


@router.post("/forecast")
async def forecast_demand(body: DemandForecastRequest, db: AsyncSession = Depends(get_db)) -> dict:
    """DM-01 ML demand forecast (1/3/6 months) for each grade."""
    if body.product_grade not in GRADES:
        raise HTTPException(status_code=400, detail=f"Grade must be one of {GRADES}")

    result = await db.execute(
        text(
            """
            SELECT month, quantity_kg FROM demand.historical_demand
            WHERE product_grade = :grade ORDER BY month DESC LIMIT 12
            """
        ),
        {"grade": body.product_grade},
    )
    history_rows = list(result.mappings().all())
    history = [float(r["quantity_kg"]) for r in reversed(history_rows)]
    prediction = run_forecast(
        body.product_grade,
        history,
        body.forecast_period,
        tire_industry_growth=body.tire_industry_growth,
        exchange_rate_volatility=body.exchange_rate_volatility,
        crude_oil_price_usd=body.crude_oil_price_usd,
    )
    factors = {
        "tire_industry_growth": body.tire_industry_growth,
        "exchange_rate_volatility": body.exchange_rate_volatility,
        "crude_oil_price_usd": body.crude_oil_price_usd,
    }
    await db.execute(
        text(
            """
            INSERT INTO demand.forecasts (
                forecast_date, product_grade, forecast_period, forecast_quantity_kg,
                confidence_lower, confidence_upper, confidence_level,
                influencing_factors, recommended_production, model_version
            ) VALUES (
                CURRENT_DATE, :grade, :period, :qty, :lo, :hi, 0.90,
                :factors::jsonb, :rec::jsonb, :mv
            )
            ON CONFLICT (forecast_date, product_grade, forecast_period) DO UPDATE SET
                forecast_quantity_kg = EXCLUDED.forecast_quantity_kg,
                confidence_lower = EXCLUDED.confidence_lower,
                confidence_upper = EXCLUDED.confidence_upper,
                influencing_factors = EXCLUDED.influencing_factors,
                recommended_production = EXCLUDED.recommended_production,
                model_version = EXCLUDED.model_version
            """
        ),
        {
            "grade": body.product_grade,
            "period": body.forecast_period,
            "qty": prediction["forecast_quantity_kg"],
            "lo": prediction["confidence_interval"]["lower"],
            "hi": prediction["confidence_interval"]["upper"],
            "factors": json.dumps(factors),
            "rec": json.dumps(prediction["recommended_production"]),
            "mv": prediction["model_version"],
        },
    )
    await db.commit()
    return {
        "forecast_date": str(date.today()),
        "historical_demand": [{"month": str(r["month"]), "quantity": float(r["quantity_kg"])} for r in reversed(history_rows)],
        "influencing_factors": factors,
        **prediction,
    }


@router.post("/forecast/all")
async def forecast_all(period: str = "3_months", db: AsyncSession = Depends(get_db)) -> dict:
    results = []
    for grade in GRADES:
        try:
            results.append(
                await forecast_demand(
                    DemandForecastRequest(product_grade=grade, forecast_period=period),
                    db,
                )
            )
        except HTTPException:
            continue
    return {"period": period, "count": len(results), "forecasts": results}


@router.post("/recommend-grade")
async def recommend_grade(body: GradeRecommendRequest, db: AsyncSession = Depends(get_db)) -> dict:
    """DM-04 grade recommender for customer formulation needs."""
    need = body.model_dump()
    result = run_recommend(need)
    await db.execute(
        text(
            """
            INSERT INTO demand.grade_recommendations
                (customer_need, recommended_grade, score, alternatives, model_version)
            VALUES (:need::jsonb, :grade, :score, :alts::jsonb, :mv)
            """
        ),
        {
            "need": json.dumps(need),
            "grade": result["recommendation"],
            "score": result["ranked"][0]["score"] if result.get("ranked") else None,
            "alts": json.dumps(result.get("alternatives", [])),
            "mv": result["model_version"],
        },
    )
    await db.commit()
    return result


@router.post("/production/plan")
async def production_plan(body: ProductionPlanRequest, db: AsyncSession = Depends(get_db)) -> dict:
    """DM-03 integrate demand forecast into production planning."""
    grades = body.grades or GRADES
    plans = []
    for grade in grades:
        hist = await db.execute(
            text(
                """
                SELECT quantity_kg FROM demand.historical_demand
                WHERE product_grade = :grade ORDER BY month DESC LIMIT 6
                """
            ),
            {"grade": grade},
        )
        history = [float(r[0]) for r in reversed(hist.all())]
        if not history:
            continue
        prediction = run_forecast(
            grade,
            history,
            body.forecast_period,
            tire_industry_growth=body.tire_industry_growth,
            exchange_rate_volatility=body.exchange_rate_volatility,
        )
        rec = prediction["recommended_production"]
        start = date.today() + timedelta(days=7)
        await db.execute(
            text(
                """
                INSERT INTO demand.production_plans (
                    plan_date, product_grade, forecast_period, planned_quantity_kg,
                    safety_stock_kg, production_line, start_date, status, margin_score, model_version
                ) VALUES (
                    CURRENT_DATE, :grade, :period, :qty, :safety, :line, :start, 'draft', :margin, :mv
                )
                ON CONFLICT (plan_date, product_grade, forecast_period) DO UPDATE SET
                    planned_quantity_kg = EXCLUDED.planned_quantity_kg,
                    safety_stock_kg = EXCLUDED.safety_stock_kg,
                    production_line = EXCLUDED.production_line,
                    start_date = EXCLUDED.start_date,
                    margin_score = EXCLUDED.margin_score,
                    model_version = EXCLUDED.model_version
                """
            ),
            {
                "grade": grade,
                "period": body.forecast_period,
                "qty": rec["quantity_kg"],
                "safety": rec["safety_stock_kg"],
                "line": rec["production_line"],
                "start": start,
                "margin": rec["margin_score"],
                "mv": prediction["model_version"],
            },
        )
        plans.append(
            {
                "product_grade": grade,
                "planned_quantity_kg": rec["quantity_kg"],
                "safety_stock_kg": rec["safety_stock_kg"],
                "production_line": rec["production_line"],
                "start_date": str(start),
                "margin_score": rec["margin_score"],
                "forecast_quantity_kg": prediction["forecast_quantity_kg"],
            }
        )
    await db.commit()
    if body.prioritize_margin:
        plans.sort(key=lambda p: p["margin_score"], reverse=True)
    high_margin = [p for p in plans if p["margin_score"] >= 0.09]
    return {
        "plan_date": str(date.today()),
        "forecast_period": body.forecast_period,
        "plans": plans,
        "high_margin_focus": high_margin[:5],
        "model_version": "demand-gbr-v1",
    }


@router.get("/production/plans")
async def list_plans(limit: int = 50, db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(
        text(
            """
            SELECT plan_date, product_grade, forecast_period, planned_quantity_kg, safety_stock_kg,
                   production_line, start_date, status, margin_score, model_version, created_at
            FROM demand.production_plans ORDER BY created_at DESC LIMIT :limit
            """
        ),
        {"limit": limit},
    )
    return [dict(r) for r in result.mappings().all()]


@router.get("/forecasts")
async def list_forecasts(limit: int = 50, db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(
        text(
            """
            SELECT forecast_date, product_grade, forecast_period, forecast_quantity_kg,
                   confidence_lower, confidence_upper, model_version, created_at
            FROM demand.forecasts ORDER BY created_at DESC LIMIT :limit
            """
        ),
        {"limit": limit},
    )
    return [dict(r) for r in result.mappings().all()]


@router.get("/model/info")
async def model_info() -> dict:
    artifact = load_demand_artifact()
    return {
        "model_version": artifact.get("model_version"),
        "metrics": artifact.get("metrics"),
        "grades": artifact.get("grades"),
    }


app.include_router(router)
