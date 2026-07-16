"""Finance & executive reporting — Phase 3 cashflow ML + board dashboard."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.app_factory import create_app
from shared.config import get_settings
from shared.db import get_db
from services.finance.models import load_finance_artifact, run_cashflow_forecast, run_ratio_analysis

settings = get_settings()


@asynccontextmanager
async def lifespan(app):  # noqa: ANN001, ARG001
    load_finance_artifact()
    yield


app = create_app(settings, title="ICB Finance Service", version="3.0.0", lifespan=lifespan)
router = APIRouter(prefix="/api/v1/finance", tags=["finance"])


class ReportUpsert(BaseModel):
    report_date: date
    revenue_ytd: float | None = None
    cost_of_goods_sold: float | None = None
    gross_profit: float | None = None
    operating_expenses: float | None = None
    net_profit: float | None = None
    current_ratio: float | None = None
    debt_to_equity: float | None = None
    inventory_turnover: float | None = None
    profit_margin: float | None = None
    operational_kpis: dict | None = None
    forecast: dict | None = None


class CashflowRequest(BaseModel):
    horizon_days: int = Field(default=90, ge=30, le=365)
    capacity_utilization: float | None = None
    defect_rate: float | None = None
    usd_irr_rate: float = 245000.0
    crude_oil_price_usd: float = 78.0


@router.get("/reports/latest")
async def latest_report(db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(text("SELECT * FROM finance.daily_reports ORDER BY report_date DESC LIMIT 1"))
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="No financial reports yet")
    return dict(row)


@router.post("/reports")
async def upsert_report(body: ReportUpsert, db: AsyncSession = Depends(get_db)) -> dict:
    await db.execute(
        text(
            """
            INSERT INTO finance.daily_reports (
                report_date, revenue_ytd, cost_of_goods_sold, gross_profit, operating_expenses,
                net_profit, current_ratio, debt_to_equity, inventory_turnover, profit_margin,
                operational_kpis, forecast
            ) VALUES (
                :report_date, :revenue_ytd, :cogs, :gross, :opex, :net, :cr, :de, :inv, :pm,
                :kpis::jsonb, :forecast::jsonb
            )
            ON CONFLICT (report_date) DO UPDATE SET
                revenue_ytd = EXCLUDED.revenue_ytd,
                cost_of_goods_sold = EXCLUDED.cost_of_goods_sold,
                gross_profit = EXCLUDED.gross_profit,
                operating_expenses = EXCLUDED.operating_expenses,
                net_profit = EXCLUDED.net_profit,
                current_ratio = EXCLUDED.current_ratio,
                debt_to_equity = EXCLUDED.debt_to_equity,
                inventory_turnover = EXCLUDED.inventory_turnover,
                profit_margin = EXCLUDED.profit_margin,
                operational_kpis = EXCLUDED.operational_kpis,
                forecast = EXCLUDED.forecast
            """
        ),
        {
            "report_date": body.report_date,
            "revenue_ytd": body.revenue_ytd,
            "cogs": body.cost_of_goods_sold,
            "gross": body.gross_profit,
            "opex": body.operating_expenses,
            "net": body.net_profit,
            "cr": body.current_ratio,
            "de": body.debt_to_equity,
            "inv": body.inventory_turnover,
            "pm": body.profit_margin,
            "kpis": json.dumps(body.operational_kpis or {}),
            "forecast": json.dumps(body.forecast or {}),
        },
    )
    await db.commit()
    return {"status": "upserted", "report_date": str(body.report_date)}


@router.post("/cashflow/forecast")
async def cashflow_forecast(body: CashflowRequest, db: AsyncSession = Depends(get_db)) -> dict:
    """FI-01 / FI-05 cashflow & liquidity forecast (target accuracy ≥ 80%)."""
    report = await db.execute(text("SELECT * FROM finance.daily_reports ORDER BY report_date DESC LIMIT 1"))
    fin = report.mappings().first() or {}
    kpis = fin.get("operational_kpis") or {}
    if isinstance(kpis, str):
        kpis = json.loads(kpis)

    prediction = run_cashflow_forecast(
        horizon_days=body.horizon_days,
        capacity_utilization=body.capacity_utilization
        if body.capacity_utilization is not None
        else float(kpis.get("capacity_utilization", 0.85)),
        defect_rate=body.defect_rate if body.defect_rate is not None else float(kpis.get("defect_rate", 0.023)),
        usd_irr_rate=body.usd_irr_rate,
        crude_oil_price_usd=body.crude_oil_price_usd,
        revenue_ytd=float(fin.get("revenue_ytd") or 245e9),
        cogs=float(fin.get("cost_of_goods_sold") or 195e9),
        opex=float(fin.get("operating_expenses") or 32e9),
    )
    await db.execute(
        text(
            """
            INSERT INTO finance.cashflow_forecasts (
                horizon_days, projected_inflow, projected_outflow, net_cashflow,
                liquidity_risk, recommendations, model_version
            ) VALUES (:h, :iin, :out, :net, :risk, :recs::jsonb, :mv)
            """
        ),
        {
            "h": body.horizon_days,
            "iin": prediction["projected_inflow"],
            "out": prediction["projected_outflow"],
            "net": prediction["net_cashflow"],
            "risk": prediction["liquidity_risk"],
            "recs": json.dumps(prediction["recommendations"]),
            "mv": prediction["model_version"],
        },
    )
    await db.commit()
    return {"forecast_date": str(date.today()), **prediction}


@router.get("/ratios/analyze")
async def ratios_analyze(db: AsyncSession = Depends(get_db)) -> dict:
    """FI-02 financial ratio analysis and improvement areas."""
    report = await db.execute(text("SELECT * FROM finance.daily_reports ORDER BY report_date DESC LIMIT 1"))
    fin = report.mappings().first()
    if not fin:
        raise HTTPException(status_code=404, detail="No financial reports yet")
    analysis = run_ratio_analysis(dict(fin))
    await db.execute(
        text(
            """
            INSERT INTO finance.ratio_snapshots (ratios, improvement_areas, model_version)
            VALUES (:ratios::jsonb, :areas::jsonb, :mv)
            """
        ),
        {
            "ratios": json.dumps(analysis["ratios"]),
            "areas": json.dumps(analysis["improvement_areas"]),
            "mv": analysis["model_version"],
        },
    )
    await db.commit()
    return analysis


@router.get("/dashboard")
async def management_dashboard(db: AsyncSession = Depends(get_db)) -> dict:
    """FI-03 integrated executive dashboard for board/management."""
    finance = await db.execute(text("SELECT * FROM finance.daily_reports ORDER BY report_date DESC LIMIT 1"))
    fin = finance.mappings().first()

    production = await db.execute(
        text(
            """
            SELECT COUNT(*) AS open_batches,
                   COUNT(DISTINCT grade) AS active_grades
            FROM quality.batches WHERE status = 'in_progress'
            """
        )
    )
    prod = production.mappings().first()

    sales = await db.execute(
        text(
            """
            SELECT COALESCE(SUM(total_price_irr), 0) AS month_revenue,
                   COALESCE(SUM(quantity_kg), 0) AS month_qty
            FROM sales.orders
            WHERE sale_date >= date_trunc('month', CURRENT_DATE)
            """
        )
    )
    sale = sales.mappings().first()

    sales_fc = await db.execute(
        text(
            """
            SELECT grade, forecast_quantity_kg, forecast_revenue_irr, recommended_unit_price, confidence
            FROM sales.forecasts ORDER BY created_at DESC LIMIT 5
            """
        )
    )

    demand_plans = await db.execute(
        text(
            """
            SELECT product_grade, planned_quantity_kg, margin_score, production_line
            FROM demand.production_plans
            WHERE plan_date = CURRENT_DATE
            ORDER BY margin_score DESC NULLS LAST
            LIMIT 5
            """
        )
    )

    alerts = await db.execute(
        text(
            """
            SELECT COUNT(*) AS open_alerts
            FROM energy.maintenance_alerts WHERE acknowledged = FALSE
            """
        )
    )
    alert_row = alerts.mappings().first()
    quality_anom = await db.execute(
        text(
            """
            SELECT COUNT(*) AS anomalies_24h
            FROM quality.anomaly_events
            WHERE is_anomaly AND detected_at > NOW() - INTERVAL '24 hours'
            """
        )
    )
    quality_row = quality_anom.mappings().first()
    cash = await db.execute(
        text(
            """
            SELECT horizon_days, net_cashflow, liquidity_risk, projected_inflow, projected_outflow
            FROM finance.cashflow_forecasts ORDER BY created_at DESC LIMIT 1
            """
        )
    )
    cash_row = cash.mappings().first()
    supply = await db.execute(
        text(
            """
            SELECT material, recommendation, predicted_price_irr, trend
            FROM supply.price_forecasts ORDER BY created_at DESC LIMIT 3
            """
        )
    )
    crm_risk = await db.execute(
        text(
            """
            SELECT COUNT(*) AS at_risk_customers
            FROM sales.customer_profiles WHERE churn_risk >= 0.2
            """
        )
    )
    crm_row = crm_risk.mappings().first()

    fin_dict = dict(fin) if fin else None
    ratio_block = run_ratio_analysis(fin_dict) if fin_dict else None

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": "finance-service-v3",
        "finance": fin_dict,
        "ratios": ratio_block,
        "cashflow": dict(cash_row) if cash_row else None,
        "production": dict(prod) if prod else {},
        "sales_mtd": dict(sale) if sale else {},
        "sales_forecasts": [dict(r) for r in sales_fc.mappings().all()],
        "high_margin_production": [dict(r) for r in demand_plans.mappings().all()],
        "maintenance_alerts_open": int(alert_row["open_alerts"]) if alert_row else 0,
        "quality_anomalies_24h": int(quality_row["anomalies_24h"]) if quality_row else 0,
        "supply_signals": [dict(r) for r in supply.mappings().all()],
        "crm_at_risk_customers": int(crm_row["at_risk_customers"]) if crm_row else 0,
    }


@router.get("/cashflow/forecasts")
async def list_cashflow(limit: int = 20, db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(
        text(
            """
            SELECT forecast_date, horizon_days, projected_inflow, projected_outflow, net_cashflow,
                   liquidity_risk, recommendations, model_version, created_at
            FROM finance.cashflow_forecasts ORDER BY created_at DESC LIMIT :limit
            """
        ),
        {"limit": limit},
    )
    return [dict(r) for r in result.mappings().all()]


@router.get("/model/info")
async def model_info() -> dict:
    artifact = load_finance_artifact()
    return {"model_version": artifact.get("model_version"), "metrics": artifact.get("metrics")}


app.include_router(router)
