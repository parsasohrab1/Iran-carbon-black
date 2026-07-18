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
from shared.production_planning import build_production_board
from shared.market_scenarios import build_market_scenario_board, scenario_presets
from shared.procurement_sources import build_static_price_board
from services.demand.models import load_demand_artifact, run_forecast, run_recommend
from ml.demand.train_forecast import GRADES

settings = get_settings()


class ProductionBoardRequest(BaseModel):
    horizon_days: int = Field(default=30, ge=7, le=90)
    schedule_days: int = Field(default=14, ge=7, le=45)
    persist: bool = True
    forecast_period: str = Field(default="1_month", pattern="^(1_month|3_months|6_months)$")


class MarketScenarioRequest(BaseModel):
    scenario_id: str = "baseline"
    usd_irr: float | None = None
    gold_irr_g: float | None = None
    oil_usd: float | None = None
    feedstock_basket_irr: float | None = None
    usd_irr_delta_pct: float = 0
    gold_delta_pct: float = 0
    oil_delta_pct: float = 0
    feedstock_delta_pct: float = 0
    horizon_days: int = Field(default=30, ge=14, le=90)
    include_all_presets: bool = True


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


async def _historical_monthly(db: AsyncSession) -> dict[str, float]:
    """Average of last 3 months demand per grade (kg/month)."""
    result = await db.execute(
        text(
            """
            SELECT product_grade, AVG(quantity_kg) AS avg_kg
            FROM (
                SELECT product_grade, quantity_kg,
                       ROW_NUMBER() OVER (PARTITION BY product_grade ORDER BY month DESC) AS rn
                FROM demand.historical_demand
            ) t
            WHERE rn <= 3
            GROUP BY product_grade
            """
        )
    )
    return {str(r["product_grade"]): float(r["avg_kg"]) for r in result.mappings().all()}


async def _persist_board_plans(
    db: AsyncSession,
    board: dict,
    *,
    forecast_period: str,
) -> None:
    start = date.today() + timedelta(days=1)
    for row in board.get("demand_by_grade") or []:
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
                    model_version = EXCLUDED.model_version,
                    status = 'draft'
                """
            ),
            {
                "grade": row["product_grade"],
                "period": forecast_period,
                "qty": row["planned_quantity_kg"],
                "safety": row["safety_stock_kg"],
                "line": row["production_line"],
                "start": start,
                "margin": row["margin_score"],
                "mv": "demand-capacity-v1",
            },
        )
    await db.commit()


@router.get("/production/board")
async def production_board(
    horizon_days: int = 30,
    schedule_days: int = 14,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Demand-driven production board: baseline + sales queue + export → schedule."""
    historical = await _historical_monthly(db)
    board = build_production_board(
        historical_monthly=historical or None,
        horizon_days=horizon_days,
        schedule_days=schedule_days,
    )
    return board


@router.post("/production/plan")
async def production_plan(body: ProductionPlanRequest, db: AsyncSession = Depends(get_db)) -> dict:
    """DM-03: build capacity-constrained production plan from demand signals."""
    period_days = {"1_month": 30, "3_months": 90, "6_months": 180}.get(body.forecast_period, 30)
    horizon = min(90, max(14, period_days if period_days <= 90 else 30))
    schedule_days = 14 if horizon <= 30 else 21

    historical = await _historical_monthly(db)
    board = build_production_board(
        historical_monthly=historical or None,
        horizon_days=horizon,
        schedule_days=schedule_days,
    )
    if body.grades:
        allowed = set(body.grades)
        board["demand_by_grade"] = [r for r in board["demand_by_grade"] if r["product_grade"] in allowed]
        board["schedule"] = [s for s in board["schedule"] if s["product_grade"] in allowed]

    await _persist_board_plans(db, board, forecast_period=body.forecast_period)

    plans = [
        {
            "product_grade": r["product_grade"],
            "planned_quantity_kg": r["planned_quantity_kg"],
            "safety_stock_kg": r["safety_stock_kg"],
            "production_line": r["production_line"],
            "start_date": str(date.today() + timedelta(days=1)),
            "margin_score": r["margin_score"],
            "forecast_quantity_kg": r["demand_total_kg"],
            "demand_baseline_kg": r["demand_baseline_kg"],
            "demand_sales_queue_kg": r["demand_sales_queue_kg"],
            "demand_export_kg": r["demand_export_kg"],
        }
        for r in board["demand_by_grade"]
    ]
    if body.prioritize_margin:
        plans.sort(key=lambda p: p["margin_score"], reverse=True)
    high_margin = [p for p in plans if p["margin_score"] >= 0.09]
    return {
        "plan_date": board["plan_date"],
        "forecast_period": body.forecast_period,
        "horizon_days": horizon,
        "plans": plans,
        "schedule": board["schedule"],
        "summary": board["summary"],
        "source": board["source"],
        "high_margin_focus": high_margin[:5],
        "model_version": "demand-capacity-v1",
        "board": board,
    }


@router.post("/production/generate")
async def generate_production_plan(body: ProductionBoardRequest, db: AsyncSession = Depends(get_db)) -> dict:
    """Explicit regenerate: merge demand signals and write a fresh production schedule."""
    historical = await _historical_monthly(db)
    board = build_production_board(
        historical_monthly=historical or None,
        horizon_days=body.horizon_days,
        schedule_days=body.schedule_days,
    )
    if body.persist:
        await _persist_board_plans(db, board, forecast_period=body.forecast_period)
    return board


async def _inventory_by_grade(db: AsyncSession) -> dict[str, float]:
    try:
        result = await db.execute(
            text("SELECT product_grade, on_hand_kg FROM maturity.inventory_positions")
        )
        rows = {str(r["product_grade"]): float(r["on_hand_kg"]) for r in result.mappings().all()}
        return rows
    except Exception:
        return {}


@router.get("/scenarios/presets")
async def list_scenario_presets() -> dict:
    return {"presets": scenario_presets()}


@router.get("/scenarios/board")
async def market_scenario_board_get(
    scenario_id: str = "baseline",
    horizon_days: int = 30,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Market-driven grade production scenarios (USD · gold · oil · feedstock)."""
    historical = await _historical_monthly(db)
    inventory = await _inventory_by_grade(db)
    return build_market_scenario_board(
        scenario_id=scenario_id,
        historical_monthly=historical or None,
        inventory_by_grade=inventory or None,
        horizon_days=horizon_days,
        price_board=build_static_price_board(),
        include_all_presets=True,
    )


@router.post("/scenarios/board")
async def market_scenario_board_post(
    body: MarketScenarioRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """What-if: override macros / deltas and recompute grade production scenario."""
    historical = await _historical_monthly(db)
    inventory = await _inventory_by_grade(db)
    return build_market_scenario_board(
        scenario_id=body.scenario_id,
        usd_irr=body.usd_irr,
        gold_irr_g=body.gold_irr_g,
        oil_usd=body.oil_usd,
        feedstock_basket_irr=body.feedstock_basket_irr,
        usd_irr_delta_pct=body.usd_irr_delta_pct,
        gold_delta_pct=body.gold_delta_pct,
        oil_delta_pct=body.oil_delta_pct,
        feedstock_delta_pct=body.feedstock_delta_pct,
        historical_monthly=historical or None,
        inventory_by_grade=inventory or None,
        horizon_days=body.horizon_days,
        price_board=build_static_price_board(),
        include_all_presets=body.include_all_presets,
    )


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
