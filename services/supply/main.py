"""Supply chain & procurement — Phase 2 ML price forecast + tender scoring."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.app_factory import create_app
from shared.config import get_settings
from shared.db import get_db
from shared.procurement_sources import (
    MATERIAL_DB_NAMES,
    MATERIALS,
    SUPPLIERS,
    build_static_price_board,
)
from services.supply.models import load_price_artifact, run_price_forecast

settings = get_settings()


@asynccontextmanager
async def lifespan(app):  # noqa: ANN001, ARG001
    load_price_artifact()
    yield


app = create_app(settings, title="ICB Supply Chain Service", version="2.0.0", lifespan=lifespan)
router = APIRouter(prefix="/api/v1/supply", tags=["supply"])


class PurchaseAdviceRequest(BaseModel):
    material: str = "Coal tar (furfural extract)"
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


@router.get("/procurement/board")
async def procurement_board(db: AsyncSession = Depends(get_db)) -> dict:
    """Live purchase sources + up-to-date feedstock prices for the dashboard."""
    board = build_static_price_board()
    try:
        # Latest market price per material (non-supplier sources)
        market = await db.execute(
            text(
                """
                SELECT DISTINCT ON (material)
                    material, price_irr, time, source
                FROM supply.price_history
                WHERE source IS NULL OR source = 'market' OR source NOT LIKE 'SUP-%'
                ORDER BY material, time DESC
                """
            )
        )
        market_map = {r["material"]: dict(r) for r in market.mappings().all()}

        # Price ~7 days ago for change %
        week_ago = await db.execute(
            text(
                """
                SELECT DISTINCT ON (material)
                    material, price_irr
                FROM supply.price_history
                WHERE time <= NOW() - INTERVAL '7 days'
                  AND (source IS NULL OR source = 'market' OR source NOT LIKE 'SUP-%')
                ORDER BY material, time DESC
                """
            )
        )
        week_map = {r["material"]: float(r["price_irr"]) for r in week_ago.mappings().all()}

        # Latest supplier quotes
        quotes = await db.execute(
            text(
                """
                SELECT DISTINCT ON (material, source)
                    material, source AS supplier_id, price_irr, time
                FROM supply.price_history
                WHERE source LIKE 'SUP-%'
                ORDER BY material, source, time DESC
                """
            )
        )
        quote_rows = [dict(r) for r in quotes.mappings().all()]

        suppliers_db = await db.execute(
            text(
                """
                SELECT id, name, rating, delivery_reliability, quality_rating, metadata
                FROM supply.suppliers ORDER BY rating DESC NULLS LAST
                """
            )
        )
        db_suppliers = {r["id"]: dict(r) for r in suppliers_db.mappings().all()}

        # Enrich numeric fields from DB; keep Persian display strings from catalog
        # (Windows seed pipes can corrupt UTF-8 in Postgres — never trust DB for FA labels.)
        enriched_suppliers = []
        for catalog_sup in SUPPLIERS:
            row = db_suppliers.get(catalog_sup["id"], {})
            enriched_suppliers.append(
                {
                    **catalog_sup,
                    "rating": float(row["rating"]) if row.get("rating") is not None else catalog_sup["rating"],
                    "delivery_reliability": float(row["delivery_reliability"])
                    if row.get("delivery_reliability") is not None
                    else catalog_sup["delivery_reliability"],
                    "quality_rating": float(row["quality_rating"])
                    if row.get("quality_rating") is not None
                    else catalog_sup["quality_rating"],
                }
            )

        # Resolve DB material labels → catalog id (handles garbled UTF-8 rows)
        reverse_db_names = {v: k for k, v in MATERIAL_DB_NAMES.items()}

        def material_id_of(db_label: str | None) -> str | None:
            if not db_label:
                return None
            if db_label in reverse_db_names:
                return reverse_db_names[db_label]
            # garbled / unknown: try match via latest quotes keyed by supplier only later
            return None

        materials_out = []
        for mat in MATERIALS:
            db_name = MATERIAL_DB_NAMES[mat["id"]]
            mkt = market_map.get(db_name)
            # If market rows were stored with corrupted labels, fall back to any market price
            # matched through supplier quotes for this material id, or catalog.
            latest = float(mkt["price_irr"]) if mkt else None
            prev = week_map.get(db_name)
            change = None
            trend = "stable"

            mat_quotes = []
            for q in quote_rows:
                q_mid = material_id_of(q.get("material"))
                if q_mid != mat["id"] and q.get("material") != db_name:
                    continue
                sid = q["supplier_id"]
                sup = next((s for s in enriched_suppliers if s["id"] == sid), None)
                mat_quotes.append(
                    {
                        "supplier_id": sid,
                        "supplier_name": (sup["name"] if sup else sid),
                        "city": (sup["city"] if sup else "—"),
                        "price_irr": float(q["price_irr"]),
                        "lead_time_days": sup["lead_time_days"] if sup else None,
                        "rating": sup["rating"] if sup else None,
                        "quoted_at": str(q["time"]),
                    }
                )
            # Fallback to catalog quotes if DB has none for this material
            if not mat_quotes:
                for s in enriched_suppliers:
                    if mat["id"] in s.get("quotes_irr", {}):
                        mat_quotes.append(
                            {
                                "supplier_id": s["id"],
                                "supplier_name": s["name"],
                                "city": s["city"],
                                "price_irr": s["quotes_irr"][mat["id"]],
                                "lead_time_days": s["lead_time_days"],
                                "rating": s["rating"],
                                "quoted_at": None,
                            }
                        )
            mat_quotes.sort(key=lambda x: x["price_irr"])
            best = mat_quotes[0] if mat_quotes else None
            if latest is None:
                latest = catalog_sup_quote_avg(mat["id"])
                if latest is None and best:
                    latest = best["price_irr"]
            if latest is not None and prev and prev > 0:
                change = round(((latest - prev) / prev) * 100, 2)
                if change > 1.0:
                    trend = "up"
                elif change < -1.0:
                    trend = "down"
            avg = round(sum(q["price_irr"] for q in mat_quotes) / len(mat_quotes), 0) if mat_quotes else latest

            materials_out.append(
                {
                    **mat,
                    "db_name": db_name,
                    "latest_price_irr": latest,
                    "avg_market_irr": avg,
                    "best_supplier": best,
                    "change_pct_7d": change,
                    "trend": trend,
                    "quotes": mat_quotes,
                    "price_source": "database" if mkt or any(
                        material_id_of(q.get("material")) == mat["id"] or q.get("material") == db_name
                        for q in quote_rows
                    ) else "catalog",
                    "market_as_of": str(mkt["time"]) if mkt else None,
                }
            )

        forecasts = await db.execute(
            text(
                """
                SELECT DISTINCT ON (material)
                    material, predicted_price_irr, trend, recommendation, confidence, created_at
                FROM supply.price_forecasts
                ORDER BY material, created_at DESC
                """
            )
        )
        forecast_map = {r["material"]: dict(r) for r in forecasts.mappings().all()}
        for item in materials_out:
            fc = forecast_map.get(item["db_name"])
            if fc:
                item["forecast"] = {
                    "predicted_price_irr": float(fc["predicted_price_irr"]),
                    "trend": fc["trend"],
                    "recommendation": fc["recommendation"],
                    "confidence": float(fc["confidence"]) if fc.get("confidence") is not None else None,
                }

        return {
            "source": "live supply.price_history + procurement catalog",
            "updated_label": "Updated market prices and supplier suggestions",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "materials": materials_out,
            "suppliers": enriched_suppliers,
            "summary": {
                "supplier_count": len(enriched_suppliers),
                "material_count": len(materials_out),
                "critical_materials": sum(1 for m in materials_out if m["criticality"] == "critical"),
                "best_cbfs": next((m["best_supplier"] for m in materials_out if m["id"] == "cbfs"), None),
            },
        }
    except Exception:  # noqa: BLE001
        # DB may be unavailable offline — fall back to static catalog
        return board


def catalog_sup_quote_avg(material_id: str) -> float | None:
    prices = [s["quotes_irr"][material_id] for s in SUPPLIERS if material_id in s.get("quotes_irr", {})]
    if not prices:
        return None
    return round(sum(prices) / len(prices), 0)


app.include_router(router)
