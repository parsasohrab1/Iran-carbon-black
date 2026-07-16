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
from services.quality.models import load_anomaly_artifact, optimize_process, predict_anomaly

settings = get_settings()


@asynccontextmanager
async def lifespan(app):  # noqa: ANN001, ARG001
    load_anomaly_artifact()
    yield


app = create_app(settings, title="ICB Quality Service", version="2.0.0", lifespan=lifespan)
router = APIRouter(prefix="/api/v1/quality", tags=["quality"])

GRADE_TARGETS: dict[str, dict[str, tuple[float, float]]] = {
    "N110": {"iodine_absorption": (135, 150), "dbp_absorption": (110, 125), "surface_area": (125, 140)},
    "N115": {"iodine_absorption": (120, 135), "dbp_absorption": (108, 122), "surface_area": (115, 130)},
    "N220": {"iodine_absorption": (80, 85), "dbp_absorption": (110, 120), "surface_area": (75, 82)},
    "N234": {"iodine_absorption": (115, 125), "dbp_absorption": (120, 135), "surface_area": (110, 125)},
    "N330": {"iodine_absorption": (78, 84), "dbp_absorption": (100, 112), "surface_area": (72, 80)},
    "N339": {"iodine_absorption": (85, 95), "dbp_absorption": (115, 130), "surface_area": (85, 95)},
    "N347": {"iodine_absorption": (85, 95), "dbp_absorption": (115, 130), "surface_area": (82, 92)},
    "N550": {"iodine_absorption": (40, 48), "dbp_absorption": (115, 130), "surface_area": (38, 46)},
    "N660": {"iodine_absorption": (32, 40), "dbp_absorption": (85, 100), "surface_area": (30, 40)},
    "N762": {"iodine_absorption": (25, 35), "dbp_absorption": (60, 75), "surface_area": (25, 35)},
    "N774": {"iodine_absorption": (25, 35), "dbp_absorption": (65, 80), "surface_area": (25, 35)},
    "N990": {"iodine_absorption": (5, 15), "dbp_absorption": (35, 50), "surface_area": (6, 14)},
}


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
    return {"grades": list(GRADE_TARGETS.keys()), "targets": GRADE_TARGETS}


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
