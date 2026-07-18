"""Production quality & process control — Phase 2 ML anomaly + optimization."""

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
from shared.product_catalog import GRADE_TARGETS, build_product_catalog
from services.quality.models import load_anomaly_artifact, optimize_process, predict_anomaly

settings = get_settings()


@asynccontextmanager
async def lifespan(app):  # noqa: ANN001, ARG001
    load_anomaly_artifact()
    yield


app = create_app(settings, title="ICB Quality Service", version="2.0.0", lifespan=lifespan)
router = APIRouter(prefix="/api/v1/quality", tags=["quality"])



class AnomalyCheckRequest(BaseModel):
    batch_id: str | None = None
    grade: str = "N220"
    process_parameters: dict[str, float] = Field(default_factory=dict)
    quality_metrics: dict[str, float] = Field(default_factory=dict)
    iodine_absorption: float | None = None
    dbp_absorption: float | None = None
    surface_area: float | None = None


class OptimizeRequest(BaseModel):
    batch_id: str | None = None
    grade: str = "N220"
    process_parameters: dict[str, float]


@router.get("/batches")
async def list_batches(limit: int = 50, db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(
        text(
            """
            SELECT batch_id, production_line, grade, started_at, finished_at, status
            FROM quality.batches ORDER BY started_at DESC LIMIT :limit
            """
        ),
        {"limit": limit},
    )
    return [dict(r) for r in result.mappings().all()]


@router.get("/batches/{batch_id}/metrics")
async def batch_metrics(batch_id: str, db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(
        text(
            """
            SELECT time, iodine_absorption, dbp_absorption, surface_area, particle_size,
                   tint_strength, anomaly_score, is_anomaly
            FROM quality.quality_metrics
            WHERE batch_id = :batch_id
            ORDER BY time DESC LIMIT 100
            """
        ),
        {"batch_id": batch_id},
    )
    return [dict(r) for r in result.mappings().all()]


@router.get("/grades")
async def list_grades() -> dict:
    return {
        "grades": list(GRADE_TARGETS.keys()),
        "targets": GRADE_TARGETS,
        "current_production": build_product_catalog()["grade_codes"],
    }


@router.get("/products")
async def current_products() -> dict:
    """Active commercial grades with full ASTM quality specification sheet."""
    return build_product_catalog()


@router.get("/products/{grade_code}")
async def product_detail(grade_code: str) -> dict:
    catalog = build_product_catalog()
    normalized = grade_code.strip().upper()
    if normalized.startswith("N") and "-" not in normalized and normalized[1:].isdigit():
        normalized = f"N-{normalized[1:]}"
    astm_key = normalized.replace("-", "")
    for product in catalog["products"]:
        if product["code"].upper() == normalized or product["astm_code"].upper() == astm_key:
            return product
    raise HTTPException(status_code=404, detail=f"Grade not in current production catalog: {grade_code}")


@router.post("/anomaly/check")
async def check_anomaly(body: AnomalyCheckRequest, db: AsyncSession = Depends(get_db)) -> dict:
    """QC-02 ML anomaly detection (target accuracy ≥ 95%)."""
    quality = dict(body.quality_metrics)
    if body.iodine_absorption is not None:
        quality["iodine_absorption"] = body.iodine_absorption
    if body.dbp_absorption is not None:
        quality["dbp_absorption"] = body.dbp_absorption
    if body.surface_area is not None:
        quality["surface_area"] = body.surface_area

    process = dict(body.process_parameters)
    if not process and body.batch_id:
        result = await db.execute(
            text(
                """
                SELECT reactor_temp, feed_rate, air_flow, residence_time, pressure, oil_to_air_ratio
                FROM quality.process_readings
                WHERE batch_id = :batch_id ORDER BY time DESC LIMIT 1
                """
            ),
            {"batch_id": body.batch_id},
        )
        row = result.mappings().first()
        if row:
            process = {k: float(v) for k, v in dict(row).items() if v is not None}
    if not quality and body.batch_id:
        result = await db.execute(
            text(
                """
                SELECT iodine_absorption, dbp_absorption, surface_area, particle_size, tint_strength
                FROM quality.quality_metrics
                WHERE batch_id = :batch_id ORDER BY time DESC LIMIT 1
                """
            ),
            {"batch_id": body.batch_id},
        )
        row = result.mappings().first()
        if row:
            quality = {k: float(v) for k, v in dict(row).items() if v is not None}

    if not process or not quality:
        raise HTTPException(status_code=400, detail="process_parameters and quality_metrics required")

    prediction = predict_anomaly(process, quality)

    # Spec-window deviations as explainability layer
    deviations = []
    targets = GRADE_TARGETS.get(body.grade, {})
    for key, bounds in targets.items():
        value = quality.get(key)
        if value is None:
            continue
        low, high = bounds
        if value < low or value > high:
            deviations.append({"metric": key, "value": value, "target": [low, high]})

    if body.batch_id:
        await db.execute(
            text(
                """
                UPDATE quality.quality_metrics
                SET anomaly_score = :score, is_anomaly = :flag
                WHERE batch_id = :batch_id
                  AND time = (SELECT MAX(time) FROM quality.quality_metrics WHERE batch_id = :batch_id)
                """
            ),
            {"score": prediction["anomaly_score"], "flag": prediction["is_anomaly"], "batch_id": body.batch_id},
        )
        await db.execute(
            text(
                """
                INSERT INTO quality.anomaly_events
                    (batch_id, grade, anomaly_score, is_anomaly, features, model_version, source)
                VALUES (:batch_id, :grade, :score, :flag, :features::jsonb, :mv, 'api')
                """
            ),
            {
                "batch_id": body.batch_id,
                "grade": body.grade,
                "score": prediction["anomaly_score"],
                "flag": prediction["is_anomaly"],
                "features": json.dumps({"process": process, "quality": quality}),
                "mv": prediction["model_version"],
            },
        )
        await db.commit()

    return {
        "batch_id": body.batch_id,
        "grade": body.grade,
        "is_anomaly": prediction["is_anomaly"],
        "anomaly_score": prediction["anomaly_score"],
        "deviations": deviations,
        "model_version": prediction["model_version"],
        "model_metrics": prediction.get("metrics"),
    }


@router.post("/process/optimize")
async def process_optimize(body: OptimizeRequest, db: AsyncSession = Depends(get_db)) -> dict:
    """QC-05 process parameter recommendations to reduce off-spec output."""
    result = optimize_process(body.process_parameters, body.grade)
    await db.execute(
        text(
            """
            INSERT INTO quality.process_recommendations
                (batch_id, grade, current_params, recommended_params, expected_defect_reduction, model_version, rationale)
            VALUES (:batch_id, :grade, :current::jsonb, :rec::jsonb, :edr, :mv, :rationale)
            """
        ),
        {
            "batch_id": body.batch_id,
            "grade": body.grade,
            "current": json.dumps(body.process_parameters),
            "rec": json.dumps(result["recommended_params"]),
            "edr": result["expected_defect_reduction"],
            "mv": result["model_version"],
            "rationale": result["rationale"],
        },
    )
    await db.commit()
    return {"batch_id": body.batch_id, **result}


@router.get("/anomaly/events")
async def anomaly_events(limit: int = 50, db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(
        text(
            """
            SELECT id, batch_id, grade, detected_at, anomaly_score, is_anomaly, model_version, source
            FROM quality.anomaly_events ORDER BY detected_at DESC LIMIT :limit
            """
        ),
        {"limit": limit},
    )
    return [dict(r) for r in result.mappings().all()]


@router.get("/model/info")
async def model_info() -> dict:
    artifact = load_anomaly_artifact()
    return {
        "model_version": artifact.get("model_version"),
        "metrics": artifact.get("metrics"),
        "feature_names": artifact.get("feature_names"),
    }


app.include_router(router)
