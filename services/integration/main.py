"""ERP / external system integration gateway (Phase 3)."""

from __future__ import annotations

import json
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.app_factory import create_app
from shared.config import get_settings
from shared.db import get_db

settings = get_settings()
app = create_app(settings, title="ICB Integration Gateway", version="3.0.0")
router = APIRouter(prefix="/api/v1/erp", tags=["erp-integration"])


class ErpSalesOrder(BaseModel):
    external_id: str
    sale_date: date
    customer_id: str
    customer_name: str | None = None
    grade: str
    quantity_kg: float = Field(gt=0)
    unit_price_irr: float = Field(gt=0)
    region: str = "domestic"
    economic_indicators: dict | None = None


class ErpFinanceJournal(BaseModel):
    external_id: str
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


class WebhookCreate(BaseModel):
    name: str
    target_url: str
    event_types: list[str] = Field(default_factory=list)


async def _log_sync(
    db: AsyncSession,
    *,
    direction: str,
    entity_type: str,
    external_id: str | None,
    payload: dict,
    status: str = "accepted",
    error: str | None = None,
) -> None:
    await db.execute(
        text(
            """
            INSERT INTO integration.erp_sync_log
                (direction, entity_type, external_id, payload, status, error_message)
            VALUES (:dir, :etype, :eid, :payload::jsonb, :status, :err)
            """
        ),
        {
            "dir": direction,
            "etype": entity_type,
            "eid": external_id,
            "payload": json.dumps(payload, default=str),
            "status": status,
            "err": error,
        },
    )


@router.get("/health")
async def erp_health() -> dict:
    return {
        "status": "ok",
        "service": "integration",
        "contracts": ["sales.orders", "finance.journal", "webhooks", "export"],
    }


@router.post("/sales/orders")
async def ingest_sales_order(body: ErpSalesOrder, db: AsyncSession = Depends(get_db)) -> dict:
    """Inbound ERP → ICB sales order sync (SM-05)."""
    if body.customer_name:
        await db.execute(
            text(
                """
                INSERT INTO sales.customers (id, name, segment, industry, region)
                VALUES (:id, :name, 'erp_import', 'unknown', :region)
                ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name
                """
            ),
            {"id": body.customer_id, "name": body.customer_name, "region": body.region},
        )
    total = body.quantity_kg * body.unit_price_irr
    await db.execute(
        text(
            """
            INSERT INTO sales.orders (
                sale_date, customer_id, grade, quantity_kg, unit_price_irr, total_price_irr, region, economic_indicators
            ) VALUES (
                :sale_date, :cid, :grade, :qty, :price, :total, :region, :econ::jsonb
            )
            """
        ),
        {
            "sale_date": body.sale_date,
            "cid": body.customer_id,
            "grade": body.grade,
            "qty": body.quantity_kg,
            "price": body.unit_price_irr,
            "total": total,
            "region": body.region,
            "econ": json.dumps(body.economic_indicators or {}),
        },
    )
    await _log_sync(
        db,
        direction="inbound",
        entity_type="sales.order",
        external_id=body.external_id,
        payload=body.model_dump(mode="json"),
    )
    await db.commit()
    return {"status": "synced", "external_id": body.external_id, "total_price_irr": total}


@router.post("/finance/journal")
async def ingest_finance_journal(body: ErpFinanceJournal, db: AsyncSession = Depends(get_db)) -> dict:
    """Inbound ERP → ICB finance daily report sync."""
    await db.execute(
        text(
            """
            INSERT INTO finance.daily_reports (
                report_date, revenue_ytd, cost_of_goods_sold, gross_profit, operating_expenses,
                net_profit, current_ratio, debt_to_equity, inventory_turnover, profit_margin,
                operational_kpis, forecast
            ) VALUES (
                :report_date, :revenue_ytd, :cogs, :gross, :opex, :net, :cr, :de, :inv, :pm,
                :kpis::jsonb, '{}'::jsonb
            )
            ON CONFLICT (report_date) DO UPDATE SET
                revenue_ytd = COALESCE(EXCLUDED.revenue_ytd, finance.daily_reports.revenue_ytd),
                cost_of_goods_sold = COALESCE(EXCLUDED.cost_of_goods_sold, finance.daily_reports.cost_of_goods_sold),
                gross_profit = COALESCE(EXCLUDED.gross_profit, finance.daily_reports.gross_profit),
                operating_expenses = COALESCE(EXCLUDED.operating_expenses, finance.daily_reports.operating_expenses),
                net_profit = COALESCE(EXCLUDED.net_profit, finance.daily_reports.net_profit),
                current_ratio = COALESCE(EXCLUDED.current_ratio, finance.daily_reports.current_ratio),
                debt_to_equity = COALESCE(EXCLUDED.debt_to_equity, finance.daily_reports.debt_to_equity),
                inventory_turnover = COALESCE(EXCLUDED.inventory_turnover, finance.daily_reports.inventory_turnover),
                profit_margin = COALESCE(EXCLUDED.profit_margin, finance.daily_reports.profit_margin),
                operational_kpis = COALESCE(EXCLUDED.operational_kpis, finance.daily_reports.operational_kpis)
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
        },
    )
    await _log_sync(
        db,
        direction="inbound",
        entity_type="finance.journal",
        external_id=body.external_id,
        payload=body.model_dump(mode="json"),
    )
    await db.commit()
    return {"status": "synced", "external_id": body.external_id, "report_date": str(body.report_date)}


@router.get("/export/sales-forecasts")
async def export_sales_forecasts(limit: int = 50, db: AsyncSession = Depends(get_db)) -> dict:
    """Outbound ICB → ERP export of latest sales forecasts."""
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
    rows = [dict(r) for r in result.mappings().all()]
    await _log_sync(
        db,
        direction="outbound",
        entity_type="sales.forecast",
        external_id=None,
        payload={"count": len(rows)},
    )
    await db.commit()
    return {"exported_at": datetime.utcnow().isoformat() + "Z", "items": rows}


@router.get("/export/production-plans")
async def export_production_plans(db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(
        text(
            """
            SELECT plan_date, product_grade, forecast_period, planned_quantity_kg, safety_stock_kg,
                   production_line, start_date, margin_score, status
            FROM demand.production_plans
            WHERE plan_date = CURRENT_DATE
            ORDER BY margin_score DESC NULLS LAST
            """
        )
    )
    rows = [dict(r) for r in result.mappings().all()]
    await _log_sync(
        db,
        direction="outbound",
        entity_type="demand.production_plan",
        external_id=None,
        payload={"count": len(rows)},
    )
    await db.commit()
    return {"exported_at": datetime.utcnow().isoformat() + "Z", "items": rows}


@router.post("/webhooks")
async def create_webhook(body: WebhookCreate, db: AsyncSession = Depends(get_db)) -> dict:
    await db.execute(
        text(
            """
            INSERT INTO integration.webhook_subscriptions (name, target_url, event_types)
            VALUES (:name, :url, :events::jsonb)
            """
        ),
        {"name": body.name, "url": body.target_url, "events": json.dumps(body.event_types)},
    )
    await db.commit()
    return {"status": "created", "name": body.name}


@router.get("/webhooks")
async def list_webhooks(db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(
        text(
            """
            SELECT id, name, target_url, event_types, is_active, created_at
            FROM integration.webhook_subscriptions ORDER BY id
            """
        )
    )
    return [dict(r) for r in result.mappings().all()]


@router.get("/sync-log")
async def sync_log(limit: int = 50, db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(
        text(
            """
            SELECT id, direction, entity_type, external_id, status, error_message, created_at
            FROM integration.erp_sync_log ORDER BY created_at DESC LIMIT :limit
            """
        ),
        {"limit": limit},
    )
    return [dict(r) for r in result.mappings().all()]


@router.get("/openapi-contract")
async def openapi_contract() -> dict:
    """Lightweight contract description for ERP integrators (IN-05)."""
    return {
        "version": "3.0.0",
        "base_path": "/api/v1/erp",
        "auth": "Bearer JWT via /api/v1/auth/login",
        "endpoints": [
            {"method": "POST", "path": "/sales/orders", "direction": "inbound"},
            {"method": "POST", "path": "/finance/journal", "direction": "inbound"},
            {"method": "GET", "path": "/export/sales-forecasts", "direction": "outbound"},
            {"method": "GET", "path": "/export/production-plans", "direction": "outbound"},
            {"method": "POST", "path": "/webhooks", "direction": "config"},
        ],
    }


app.include_router(router)
