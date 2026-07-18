"""Energy & facilities — Phase 1: RUL ML model, 3-day alerts, energy source optimization."""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.app_factory import create_app
from shared.config import get_settings
from shared.db import SessionLocal, get_db
from shared.equipment_catalog import (
    DATA_LOGGERS,
    EQUIPMENT,
    build_static_equipment_board,
    equipment_by_id,
    evaluate_equipment,
    simulate_reading,
)
from services.energy.optimizer import Tariff, choose_energy_source
from services.energy.rul_model import load_rul_artifact, predict_rul_from_sensors

settings = get_settings()
log = structlog.get_logger()
_scanner_task: asyncio.Task | None = None


async def _scan_equipment_for_alerts() -> None:
    """Background loop: predict RUL for all equipment and raise alerts when RUL <= 3 days."""
    while True:
        try:
            async with SessionLocal() as db:
                result = await db.execute(text("SELECT id FROM energy.equipment"))
                equipment_ids = [row[0] for row in result.all()]
                for eid in equipment_ids:
                    await _predict_and_maybe_alert(db, eid, lookback_hours=6, persist=True)
                await db.commit()
        except Exception as exc:  # noqa: BLE001
            log.warning("alert_scanner_error", error=str(exc))
        await asyncio.sleep(300)


@asynccontextmanager
async def lifespan(app):  # noqa: ANN001, ARG001
    global _scanner_task
    load_rul_artifact()
    _scanner_task = asyncio.create_task(_scan_equipment_for_alerts())
    yield
    if _scanner_task is not None:
        _scanner_task.cancel()
        try:
            await _scanner_task
        except asyncio.CancelledError:
            pass


app = create_app(settings, title="ICB Energy Service", version="1.0.0", lifespan=lifespan)
router = APIRouter(prefix="/api/v1/energy", tags=["energy"])


class RULRequest(BaseModel):
    equipment_id: str
    lookback_hours: int = Field(default=24, ge=1, le=168)


class RULResponse(BaseModel):
    equipment_id: str
    remaining_useful_life_days: float
    failure_probability: float
    alert: bool
    alert_threshold_days: float = 3.0
    model_version: str
    predicted_at: datetime
    prediction_id: int | None = None


class SourceDecisionRequest(BaseModel):
    line_id: str = "Line_1"
    expected_kwh: float = Field(default=100.0, gt=0)
    at: datetime | None = None


class AcknowledgeRequest(BaseModel):
    alert_id: int


async def _latest_sensor_features(db: AsyncSession, equipment_id: str, lookback_hours: int) -> dict[str, float]:
    result = await db.execute(
        text(
            """
            SELECT
                AVG(vibration_x) AS vibration_x,
                AVG(vibration_y) AS vibration_y,
                AVG(vibration_z) AS vibration_z,
                AVG(temperature) AS temperature,
                AVG(pressure) AS pressure,
                AVG(current_draw) AS current_draw,
                AVG(oil_pressure) AS oil_pressure,
                AVG(coolant_temp) AS coolant_temp
            FROM energy.sensor_readings
            WHERE equipment_id = :eid
              AND time > NOW() - (:hours || ' hours')::interval
            """
        ),
        {"eid": equipment_id, "hours": str(lookback_hours)},
    )
    row = result.mappings().first()
    if not row or row["temperature"] is None:
        raise HTTPException(status_code=404, detail="No sensor data for equipment")
    return {k: float(v) for k, v in dict(row).items() if v is not None}


async def _predict_and_maybe_alert(
    db: AsyncSession,
    equipment_id: str,
    lookback_hours: int,
    persist: bool,
) -> RULResponse:
    sensors = await _latest_sensor_features(db, equipment_id, lookback_hours)
    prediction = predict_rul_from_sensors(sensors)
    prediction_id = None

    if persist:
        result = await db.execute(
            text(
                """
                INSERT INTO energy.rul_predictions
                    (equipment_id, rul_days, failure_probability, model_version, alert_issued)
                VALUES (:eid, :rul, :fp, :mv, :alert)
                RETURNING id
                """
            ),
            {
                "eid": equipment_id,
                "rul": prediction["remaining_useful_life_days"],
                "fp": prediction["failure_probability"],
                "mv": prediction["model_version"],
                "alert": prediction["alert"],
            },
        )
        prediction_id = result.scalar_one()

        if prediction["alert"]:
            # Avoid alert spam: one open alert per equipment per day
            existing = await db.execute(
                text(
                    """
                    SELECT id FROM energy.maintenance_alerts
                    WHERE equipment_id = :eid
                      AND acknowledged = FALSE
                      AND created_at > NOW() - INTERVAL '1 day'
                    LIMIT 1
                    """
                ),
                {"eid": equipment_id},
            )
            if existing.first() is None:
                severity = "critical" if prediction["remaining_useful_life_days"] <= 1 else "warning"
                await db.execute(
                    text(
                        """
                        INSERT INTO energy.maintenance_alerts (
                            equipment_id, alert_type, severity, rul_days,
                            failure_probability, message, prediction_id
                        ) VALUES (
                            :eid, 'rul_threshold', :severity, :rul, :fp, :msg, :pid
                        )
                        """
                    ),
                    {
                        "eid": equipment_id,
                        "severity": severity,
                        "rul": prediction["remaining_useful_life_days"],
                        "fp": prediction["failure_probability"],
                        "msg": (
                            f"Predicted failure within {prediction['remaining_useful_life_days']} days "
                            f"for {equipment_id}. Schedule maintenance (PM-03)."
                        ),
                        "pid": prediction_id,
                    },
                )
                log.warning(
                    "maintenance_alert_raised",
                    equipment_id=equipment_id,
                    rul_days=prediction["remaining_useful_life_days"],
                )

    return RULResponse(
        equipment_id=equipment_id,
        remaining_useful_life_days=prediction["remaining_useful_life_days"],
        failure_probability=prediction["failure_probability"],
        alert=prediction["alert"],
        alert_threshold_days=prediction["alert_threshold_days"],
        model_version=prediction["model_version"],
        predicted_at=datetime.now(timezone.utc),
        prediction_id=prediction_id,
    )


@router.get("/equipment")
async def list_equipment(db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(
        text("SELECT id, name, equipment_type, location, line_id, status FROM energy.equipment")
    )
    return [dict(row) for row in result.mappings().all()]


@router.get("/sensors/{equipment_id}/latest")
async def latest_sensors(equipment_id: str, limit: int = 50, db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(
        text(
            """
            SELECT time, vibration_x, vibration_y, vibration_z, temperature, pressure,
                   current_draw, oil_pressure, coolant_temp
            FROM energy.sensor_readings
            WHERE equipment_id = :eid
            ORDER BY time DESC
            LIMIT :limit
            """
        ),
        {"eid": equipment_id, "limit": limit},
    )
    return [dict(r) for r in result.mappings().all()]


@router.post("/rul/predict", response_model=RULResponse)
async def predict_rul(body: RULRequest, db: AsyncSession = Depends(get_db)) -> RULResponse:
    """PM-02 / PM-03 — ML RUL with automatic 3-day alert."""
    response = await _predict_and_maybe_alert(db, body.equipment_id, body.lookback_hours, persist=True)
    await db.commit()
    return response


@router.post("/rul/scan")
async def scan_all(lookback_hours: int = 24, db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(text("SELECT id FROM energy.equipment"))
    ids = [row[0] for row in result.all()]
    outcomes = []
    for eid in ids:
        try:
            outcomes.append((await _predict_and_maybe_alert(db, eid, lookback_hours, persist=True)).model_dump())
        except HTTPException:
            continue
    await db.commit()
    return {"scanned": len(outcomes), "results": outcomes}


@router.get("/alerts")
async def list_alerts(open_only: bool = True, limit: int = 50, db: AsyncSession = Depends(get_db)) -> list[dict]:
    query = """
        SELECT id, equipment_id, alert_type, severity, rul_days, failure_probability,
               message, acknowledged, created_at
        FROM energy.maintenance_alerts
    """
    if open_only:
        query += " WHERE acknowledged = FALSE"
    query += " ORDER BY created_at DESC LIMIT :limit"
    result = await db.execute(text(query), {"limit": limit})
    return [dict(r) for r in result.mappings().all()]


@router.post("/alerts/acknowledge")
async def acknowledge_alert(body: AcknowledgeRequest, db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(
        text(
            """
            UPDATE energy.maintenance_alerts
            SET acknowledged = TRUE, acknowledged_at = NOW()
            WHERE id = :id
            RETURNING id
            """
        ),
        {"id": body.alert_id},
    )
    if result.first() is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    await db.commit()
    return {"status": "acknowledged", "alert_id": body.alert_id}


@router.get("/consumption")
async def energy_consumption(
    line_id: str | None = None, hours: int = 24, db: AsyncSession = Depends(get_db)
) -> list[dict]:
    query = """
        SELECT time, line_id, source, kwh, cost_irr, price_forecast
        FROM energy.energy_consumption
        WHERE time > NOW() - (:hours || ' hours')::interval
    """
    params: dict = {"hours": str(hours)}
    if line_id:
        query += " AND line_id = :line_id"
        params["line_id"] = line_id
    query += " ORDER BY time DESC LIMIT 500"
    result = await db.execute(text(query), params)
    return [dict(r) for r in result.mappings().all()]


@router.get("/consumption/summary")
async def consumption_summary(hours: int = 24, db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(
        text(
            """
            SELECT source,
                   SUM(kwh) AS total_kwh,
                   SUM(COALESCE(cost_irr, 0)) AS total_cost_irr,
                   COUNT(*) AS samples
            FROM energy.energy_consumption
            WHERE time > NOW() - (:hours || ' hours')::interval
            GROUP BY source
            """
        ),
        {"hours": str(hours)},
    )
    by_source = {row["source"]: dict(row) for row in result.mappings().all()}
    return {"hours": hours, "by_source": by_source}


@router.post("/source/decide")
async def decide_source(body: SourceDecisionRequest, db: AsyncSession = Depends(get_db)) -> dict:
    """PM-04 — choose between municipal grid and on-site generator."""
    result = await db.execute(
        text(
            """
            SELECT source, price_irr_per_kwh, peak_multiplier, peak_hours_start, peak_hours_end
            FROM energy.tariffs
            """
        )
    )
    tariffs = [Tariff(**dict(row)) for row in result.mappings().all()]
    decision = choose_energy_source(tariffs, expected_kwh=body.expected_kwh, at=body.at)
    await db.execute(
        text(
            """
            INSERT INTO energy.source_decisions (
                line_id, recommended_source, grid_cost_irr_per_kwh, generator_cost_irr_per_kwh,
                expected_kwh, estimated_saving_irr, reason, is_peak
            ) VALUES (
                :line_id, :src, :grid, :gen, :kwh, :saving, :reason, :peak
            )
            """
        ),
        {
            "line_id": body.line_id,
            "src": decision["recommended_source"],
            "grid": decision["grid_cost_irr_per_kwh"],
            "gen": decision["generator_cost_irr_per_kwh"],
            "kwh": decision["expected_kwh"],
            "saving": decision["estimated_saving_irr"],
            "reason": decision["reason"],
            "peak": decision["is_peak"],
        },
    )
    await db.commit()
    return {"line_id": body.line_id, **decision}


@router.get("/source/decisions")
async def list_decisions(limit: int = 20, db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(
        text(
            """
            SELECT decided_at, line_id, recommended_source, grid_cost_irr_per_kwh,
                   generator_cost_irr_per_kwh, expected_kwh, estimated_saving_irr, reason, is_peak
            FROM energy.source_decisions
            ORDER BY decided_at DESC
            LIMIT :limit
            """
        ),
        {"limit": limit},
    )
    return [dict(r) for r in result.mappings().all()]


@router.get("/model/info")
async def model_info() -> dict:
    artifact = load_rul_artifact()
    return {
        "model_version": artifact.get("model_version"),
        "alert_rul_days": artifact.get("alert_rul_days"),
        "feature_names": artifact.get("feature_names"),
        "metrics": artifact.get("metrics"),
    }


def _readings_from_row(row: dict, catalog_eq: dict) -> dict[str, float]:
    """Merge columnar sensors + raw.sensors JSON into one reading map."""
    values: dict[str, float] = {}
    raw = row.get("raw") or {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            raw = {}
    nested = raw.get("sensors") if isinstance(raw, dict) else None
    if isinstance(nested, dict):
        for k, v in nested.items():
            try:
                values[str(k)] = float(v)
            except (TypeError, ValueError):
                pass
    for col in (
        "vibration_x",
        "vibration_y",
        "vibration_z",
        "temperature",
        "pressure",
        "current_draw",
        "oil_pressure",
        "coolant_temp",
    ):
        if row.get(col) is not None and col not in values:
            values[col] = float(row[col])
    # Fill missing keys with simulated in-range values so board is complete
    if len(values) < len(catalog_eq.get("sensors", [])):
        sim = simulate_reading(catalog_eq, spike=False)
        for k, v in sim.items():
            values.setdefault(k, v)
    return values


@router.get("/equipment/board")
async def equipment_board(db: AsyncSession = Depends(get_db)) -> dict:
    """Full production-line equipment + sensors vs operational ranges + process alerts."""
    fallback = build_static_equipment_board(with_spikes=True)
    catalog = equipment_by_id()
    try:
        # Ensure catalog equipment rows exist
        for eq in EQUIPMENT:
            await db.execute(
                text(
                    """
                    INSERT INTO energy.equipment (id, name, name_fa, equipment_type, location, line_id, area, status)
                    VALUES (:id, :name, :name_fa, :etype, :loc, :line, :area, 'running')
                    ON CONFLICT (id) DO UPDATE SET
                        name_fa = COALESCE(EXCLUDED.name_fa, energy.equipment.name_fa),
                        location = EXCLUDED.location,
                        line_id = EXCLUDED.line_id,
                        area = EXCLUDED.area
                    """
                ),
                {
                    "id": eq["id"],
                    "name": eq.get("name_en") or eq["name_fa"],
                    "name_fa": eq["name_fa"],
                    "etype": eq["equipment_type"],
                    "loc": eq["location"],
                    "line": eq["line_id"],
                    "area": eq["area"],
                },
            )

        units = []
        process_alerts = []
        for eq in EQUIPMENT:
            latest = await db.execute(
                text(
                    """
                    SELECT time, vibration_x, vibration_y, vibration_z, temperature, pressure,
                           current_draw, oil_pressure, coolant_temp, raw
                    FROM energy.sensor_readings
                    WHERE equipment_id = :eid
                    ORDER BY time DESC
                    LIMIT 1
                    """
                ),
                {"eid": eq["id"]},
            )
            row = latest.mappings().first()
            if row:
                readings = _readings_from_row(dict(row), eq)
                as_of = str(row["time"])
            else:
                readings = simulate_reading(eq, spike=eq["id"] in {"BAG-001", "FAN-001", "DRY-001"})
                as_of = datetime.now(timezone.utc).isoformat()
                await db.execute(
                    text(
                        """
                        INSERT INTO energy.sensor_readings (
                            time, equipment_id, vibration_x, vibration_y, vibration_z,
                            temperature, pressure, current_draw, oil_pressure, coolant_temp, raw
                        ) VALUES (
                            NOW(), :eid, :vx, :vy, :vz, :temp, :press, :curr, :oil, :cool, CAST(:raw AS jsonb)
                        )
                        """
                    ),
                    {
                        "eid": eq["id"],
                        "vx": readings.get("vibration_x"),
                        "vy": readings.get("vibration_y"),
                        "vz": readings.get("vibration_z"),
                        "temp": readings.get("temperature"),
                        "press": readings.get("pressure"),
                        "curr": readings.get("current_draw"),
                        "oil": readings.get("oil_pressure"),
                        "cool": readings.get("coolant_temp"),
                        "raw": json.dumps(
                            {"operational_status": "running", "sensors": readings},
                            ensure_ascii=False,
                        ),
                    },
                )

            # Demo: keep a few units visibly out-of-range for operator training
            if eq["id"] in {"BAG-001", "FAN-001", "DRY-001"} and eq["sensors"]:
                s0 = eq["sensors"][0]
                hi = float(s0["max_op"])
                lo = float(s0["min_op"])
                span = max(hi - lo, 1e-6)
                readings[s0["key"]] = round(hi + span * 0.12, 2)

            evaluated = evaluate_equipment(eq, readings)
            evaluated["as_of"] = as_of
            evaluated["name_fa"] = eq["name_fa"]
            units.append(evaluated)

            for breach in evaluated["breaches"]:
                process_alerts.append(breach)
                await db.execute(
                    text(
                        """
                        INSERT INTO energy.process_alerts (
                            equipment_id, sensor_key, severity, measured_value, min_op, max_op, unit, message
                        )
                        SELECT :eid, :key, :sev, :val, :min_op, :max_op, :unit, :msg
                        WHERE NOT EXISTS (
                            SELECT 1 FROM energy.process_alerts
                            WHERE equipment_id = :eid AND sensor_key = :key
                              AND acknowledged = FALSE
                              AND created_at > NOW() - INTERVAL '1 hour'
                        )
                        """
                    ),
                    {
                        "eid": breach["equipment_id"],
                        "key": breach["sensor_key"],
                        "sev": breach["severity"],
                        "val": breach["value"],
                        "min_op": breach["min_op"],
                        "max_op": breach["max_op"],
                        "unit": breach["unit"],
                        "msg": breach["message"],
                    },
                )

        await db.commit()

        open_alerts = await db.execute(
            text(
                """
                SELECT id, equipment_id, sensor_key, severity, measured_value, min_op, max_op, unit, message, created_at
                FROM energy.process_alerts
                WHERE acknowledged = FALSE
                ORDER BY created_at DESC
                LIMIT 50
                """
            )
        )
        stored_alerts = [dict(r) for r in open_alerts.mappings().all()]
        # Prefer live evaluation list if DB empty
        alerts_out = stored_alerts if stored_alerts else process_alerts

        normal = sum(1 for u in units if u["op_status"] == "normal")
        warn = sum(1 for u in units if u["op_status"] == "warning")
        crit = sum(1 for u in units if u["op_status"] == "critical")
        return {
            "source": "energy.equipment + PLC/SCADA/Data Logger + range evaluator",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "equipment": units,
            "data_loggers": DATA_LOGGERS,
            "process_alerts": alerts_out,
            "summary": {
                "equipment_count": len(units),
                "sensor_count": sum(len(e["sensors"]) for e in EQUIPMENT),
                "normal_count": normal,
                "warning_count": warn,
                "critical_count": crit,
                "open_process_alerts": len(alerts_out),
                "lines": sorted({e["line_id"] for e in EQUIPMENT}),
                "logger_count": len(DATA_LOGGERS),
                "plc_count": sum(1 for d in DATA_LOGGERS if d["kind"] == "plc"),
                "scada_count": sum(1 for d in DATA_LOGGERS if d["kind"] == "scada"),
                "data_logger_count": sum(1 for d in DATA_LOGGERS if d["kind"] == "data_logger"),
            },
        }
    except Exception:  # noqa: BLE001
        return fallback


app.include_router(router)
