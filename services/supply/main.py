"""Supply chain & procurement — Phase 2 ML price forecast + tender scoring."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.app_factory import create_app
from shared.config import get_settings
from shared.db import get_db
from services.supply.models import load_price_artifact, run_price_forecast

settings = get_settings()


@asynccontextmanager
async def lifespan(app):  # noqa: ANN001, ARG001
    load_price_artifact()
    yield


app = create_app(settings, title="ICB Supply Chain Service", version="2.0.0", lifespan=lifespan)
router = APIRouter(prefix="/api/v1/supply", tags=["supply"])


class PurchaseAdviceRequest(BaseModel):
    material: str = "قطران (فورفورال اکسترکت)"
    horizon_days: int = Field(default=90, ge=7, le=180)
    crude_oil_price_usd: float = 78.0
    usd_irr_rate: float = 245000.0
    inflation_rate: float = 0.35


class TenderScoreRequest(BaseModel):
    tender_id: str
    supplier_id: str
    bid_price_irr: float
    market_benchmark_irr: float
    quantity_kg: float = 1.0


@router.get("/suppliers")
async def list_suppliers(db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(
        text(
            """
            SELECT id, name, rating, delivery_reliability, quality_rating
            FROM supply.suppliers ORDER BY rating DESC NULLS LAST
            """
        )
    )
    return [dict(r) for r in result.mappings().all()]


@router.get("/orders")
async def list_orders(limit: int = 50, db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(
        text(
            """
            SELECT id, material, supplier_id, quantity_kg, unit_price_irr, total_price_irr, delivery_date, created_at
            FROM supply.purchase_orders ORDER BY created_at DESC LIMIT :limit
            """
        ),
        {"limit": limit},
    )
    return [dict(r) for r in result.mappings().all()]


@router.get("/materials")
async def list_materials() -> dict:
    artifact = load_price_artifact()
    return {"materials": artifact.get("materials", [])}


@router.post("/purchase/advice")
async def purchase_advice(body: PurchaseAdviceRequest, db: AsyncSession = Depends(get_db)) -> dict:
    """SC-02 / SC-03 ML price forecast and buy timing."""
    result = await db.execute(
        text(
            """
            SELECT time, price_irr FROM supply.price_history
            WHERE material = :material ORDER BY time DESC LIMIT 24
            """
        ),
        {"material": body.material},
    )
    rows = list(result.mappings().all())
    if len(rows) < 2:
        raise HTTPException(status_code=404, detail="Insufficient price history for material")

    history = [float(r["price_irr"]) for r in reversed(rows)]
    prediction = run_price_forecast(
        body.material,
        history,
        body.horizon_days,
        crude_oil_price_usd=body.crude_oil_price_usd,
        usd_irr_rate=body.usd_irr_rate,
        inflation_rate=body.inflation_rate,
    )
    await db.execute(
        text(
            """
            INSERT INTO supply.price_forecasts (
                material, horizon_days, predicted_price_irr, trend, recommendation, confidence, model_version
            ) VALUES (:material, :horizon, :price, :trend, :rec, :conf, :mv)
            """
        ),
        {
            "material": body.material,
            "horizon": body.horizon_days,
            "price": prediction["predicted_price_irr"],
            "trend": prediction["trend"],
            "rec": prediction["recommendation"],
            "conf": prediction["confidence"],
            "mv": prediction["model_version"],
        },
    )
    await db.commit()
    return {
        **prediction,
        "history_points": len(history),
        "price_history": [{"time": str(r["time"]), "price_irr": float(r["price_irr"])} for r in reversed(rows[-12:])],
    }


@router.post("/tenders/score")
async def score_tender(body: TenderScoreRequest, db: AsyncSession = Depends(get_db)) -> dict:
    """SC-04 tender ranking using supplier reliability and price vs market."""
    result = await db.execute(
        text(
            """
            SELECT id, name, rating, delivery_reliability, quality_rating
            FROM supply.suppliers WHERE id = :sid
            """
        ),
        {"sid": body.supplier_id},
    )
    supplier = result.mappings().first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    price_ratio = body.market_benchmark_irr / max(body.bid_price_irr, 1.0)
    score = (
        float(supplier["rating"] or 0) * 0.25
        + float(supplier["delivery_reliability"] or 0) * 4 * 0.30
        + float(supplier["quality_rating"] or 0) * 0.25
        + min(price_ratio, 1.5) * 2.0 * 0.20
    )
    factors = {
        "supplier_rating": supplier["rating"],
        "delivery_reliability": supplier["delivery_reliability"],
        "quality_rating": supplier["quality_rating"],
        "price_ratio_vs_market": round(price_ratio, 3),
        "bid_price_irr": body.bid_price_irr,
        "market_benchmark_irr": body.market_benchmark_irr,
    }
    await db.execute(
        text(
            """
            INSERT INTO supply.tender_scores (tender_id, supplier_id, score, factors)
            VALUES (:tid, :sid, :score, :factors::jsonb)
            """
        ),
        {
            "tid": body.tender_id,
            "sid": body.supplier_id,
            "score": score,
            "factors": json.dumps(factors),
        },
    )
    await db.commit()
    return {
        "tender_id": body.tender_id,
        "supplier_id": body.supplier_id,
        "supplier_name": supplier["name"],
        "score": round(score, 3),
        "factors": factors,
        "model_version": "tender-score-v1",
    }


@router.get("/forecasts")
async def list_forecasts(limit: int = 20, db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(
        text(
            """
            SELECT material, forecast_date, horizon_days, predicted_price_irr, trend,
                   recommendation, confidence, model_version, created_at
            FROM supply.price_forecasts ORDER BY created_at DESC LIMIT :limit
            """
        ),
        {"limit": limit},
    )
    return [dict(r) for r in result.mappings().all()]


@router.get("/model/info")
async def model_info() -> dict:
    artifact = load_price_artifact()
    return {
        "model_version": artifact.get("model_version"),
        "metrics": artifact.get("metrics"),
        "materials": artifact.get("materials"),
    }


app.include_router(router)
