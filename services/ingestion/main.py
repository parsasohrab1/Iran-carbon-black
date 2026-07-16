"""Ingestion service — MQTT / REST → TimescaleDB + MinIO data lake (Domain 6 / Phase 1)."""

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
from shared.storage import put_json_object
from services.ingestion.mqtt_worker import MqttIngestionWorker
from services.ingestion.repository import persist_sensor_reading

settings = get_settings()
_mqtt_worker: MqttIngestionWorker | None = None


@asynccontextmanager
async def lifespan(app):  # noqa: ANN001, ARG001
    global _mqtt_worker
    worker = MqttIngestionWorker(settings)
    try:
        worker.start()
        _mqtt_worker = worker
    except Exception:
        _mqtt_worker = None
    yield
    if _mqtt_worker is not None:
        _mqtt_worker.stop()
        _mqtt_worker = None


app = create_app(settings, title="ICB Data Ingestion", version="1.0.0", lifespan=lifespan)
router = APIRouter(prefix="/api/v1/ingestion", tags=["ingestion"])


class SensorPayload(BaseModel):
    equipment_id: str
    timestamp: datetime | None = None
    sensors: dict[str, float] = Field(default_factory=dict)
    operational_status: str = "running"
    raw: dict | None = None


class BatchQualityPayload(BaseModel):
    batch_id: str
    production_line: int
    timestamp: datetime | None = None
    process_parameters: dict[str, float] = Field(default_factory=dict)
    quality_metrics: dict[str, float] = Field(default_factory=dict)
    grade: str


class ConsumptionPayload(BaseModel):
    line_id: str
    source: str = Field(pattern="^(grid|generator)$")
    kwh: float = Field(gt=0)
    price_irr_per_kwh: float | None = None
    cost_irr: float | None = None
    timestamp: datetime | None = None


@router.post("/sensors")
async def ingest_sensor(payload: SensorPayload, db: AsyncSession = Depends(get_db)) -> dict:
    return await persist_sensor_reading(
        db,
        equipment_id=payload.equipment_id,
        sensors=payload.sensors,
        operational_status=payload.operational_status,
        timestamp=payload.timestamp,
        settings=settings,
        write_datalake=True,
    )


@router.post("/consumption")
async def ingest_consumption(payload: ConsumptionPayload, db: AsyncSession = Depends(get_db)) -> dict:
    ts = payload.timestamp or datetime.now(timezone.utc)
    cost = payload.cost_irr
    if cost is None and payload.price_irr_per_kwh is not None:
        cost = payload.price_irr_per_kwh * payload.kwh
    await db.execute(
        text(
            """
            INSERT INTO energy.energy_consumption (time, line_id, source, kwh, cost_irr, price_forecast)
            VALUES (:time, :line_id, :source, :kwh, :cost, :price)
            """
        ),
        {
            "time": ts,
            "line_id": payload.line_id,
            "source": payload.source,
            "kwh": payload.kwh,
            "cost": cost,
            "price": payload.price_irr_per_kwh,
        },
    )
    await db.commit()
    return {"status": "accepted", "line_id": payload.line_id, "source": payload.source}


@router.post("/quality")
async def ingest_quality(payload: BatchQualityPayload, db: AsyncSession = Depends(get_db)) -> dict:
    ts = payload.timestamp or datetime.now(timezone.utc)
    await db.execute(
        text(
            """
            INSERT INTO quality.batches (batch_id, production_line, grade, started_at, status)
            VALUES (:batch_id, :line, :grade, :started, 'in_progress')
            ON CONFLICT (batch_id) DO NOTHING
            """
        ),
        {
            "batch_id": payload.batch_id,
            "line": payload.production_line,
            "grade": payload.grade,
            "started": ts,
        },
    )
    p = payload.process_parameters
    await db.execute(
        text(
            """
            INSERT INTO quality.process_readings (
                time, batch_id, reactor_temp, feed_rate, air_flow,
                residence_time, pressure, oil_to_air_ratio, raw
            ) VALUES (
                :time, :batch_id, :rt, :fr, :af, :res, :pr, :oar, :raw::jsonb
            )
            """
        ),
        {
            "time": ts,
            "batch_id": payload.batch_id,
            "rt": p.get("reactor_temp"),
            "fr": p.get("feed_rate"),
            "af": p.get("air_flow"),
            "res": p.get("residence_time"),
            "pr": p.get("pressure"),
            "oar": p.get("oil_to_air_ratio"),
            "raw": json.dumps(payload.model_dump(mode="json")),
        },
    )
    q = payload.quality_metrics
    await db.execute(
        text(
            """
            INSERT INTO quality.quality_metrics (
                time, batch_id, iodine_absorption, dbp_absorption,
                surface_area, particle_size, tint_strength
            ) VALUES (:time, :batch_id, :iodine, :dbp, :sa, :ps, :tint)
            """
        ),
        {
            "time": ts,
            "batch_id": payload.batch_id,
            "iodine": q.get("iodine_absorption"),
            "dbp": q.get("DBP_absorption") or q.get("dbp_absorption"),
            "sa": q.get("surface_area"),
            "ps": q.get("particle_size"),
            "tint": q.get("tint_strength"),
        },
    )
    await db.commit()

    object_name = f"quality/batches/{payload.batch_id}/{ts.strftime('%Y%m%dT%H%M%S')}.json"
    try:
        uri = put_json_object(
            settings.minio_bucket_raw,
            object_name,
            json.dumps(payload.model_dump(mode="json")).encode(),
            settings=settings,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Data lake write failed: {exc}") from exc

    return {"status": "accepted", "datalake_uri": uri}


@router.get("/topics")
async def mqtt_topics() -> dict:
    return {
        "broker": f"{settings.mqtt_host}:{settings.mqtt_port}",
        "mqtt_worker_alive": _mqtt_worker is not None,
        "topics": {
            "energy.sensors": "icb/energy/{equipment_id}/sensors",
            "energy.consumption": "icb/energy/{line_id}/consumption",
            "quality.process": "icb/quality/{batch_id}/process",
            "energy.alerts": "icb/energy/+/alerts",
        },
    }


app.include_router(router)
