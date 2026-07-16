"""Shared persistence helpers for energy sensor ingestion."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config import Settings
from shared.storage import put_json_object


async def persist_sensor_reading(
    db: AsyncSession,
    *,
    equipment_id: str,
    sensors: dict,
    operational_status: str = "running",
    timestamp: datetime | None = None,
    settings: Settings | None = None,
    write_datalake: bool = True,
) -> dict:
    ts = timestamp or datetime.now(timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    payload = {
        "equipment_id": equipment_id,
        "timestamp": ts.isoformat(),
        "sensors": sensors,
        "operational_status": operational_status,
    }

    await db.execute(
        text(
            """
            INSERT INTO energy.sensor_readings (
                time, equipment_id, vibration_x, vibration_y, vibration_z,
                temperature, pressure, current_draw, oil_pressure, coolant_temp, raw
            ) VALUES (
                :time, :equipment_id, :vx, :vy, :vz, :temp, :pressure, :current, :oil, :coolant, :raw::jsonb
            )
            """
        ),
        {
            "time": ts,
            "equipment_id": equipment_id,
            "vx": sensors.get("vibration_x"),
            "vy": sensors.get("vibration_y"),
            "vz": sensors.get("vibration_z"),
            "temp": sensors.get("temperature"),
            "pressure": sensors.get("pressure"),
            "current": sensors.get("current_draw"),
            "oil": sensors.get("oil_pressure"),
            "coolant": sensors.get("coolant_temp"),
            "raw": json.dumps(payload),
        },
    )
    await db.commit()

    uri = None
    if write_datalake and settings is not None:
        object_name = f"energy/sensors/{equipment_id}/{ts.strftime('%Y/%m/%d/%H%M%S%f')}.json"
        try:
            uri = put_json_object(
                settings.minio_bucket_raw,
                object_name,
                json.dumps(payload).encode(),
                settings=settings,
            )
        except Exception:
            uri = None

    return {"status": "accepted", "equipment_id": equipment_id, "timestamp": ts.isoformat(), "datalake_uri": uri}
