"""Seed full production-line equipment + sensors + sample readings (UTF-8 safe)."""

from __future__ import annotations

import json
import os
import random

from sqlalchemy import create_engine, text

from shared.equipment_catalog import EQUIPMENT, simulate_reading

DSN = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://icb_admin:change_me_strong_password@postgres:5432/carbon_black",
)


def main() -> None:
    raw = DSN
    if raw.startswith("postgresql://"):
        raw = raw.replace("postgresql://", "postgresql+psycopg2://", 1)
    elif "+psycopg://" in raw:
        raw = raw.replace("+psycopg://", "+psycopg2://", 1)
    engine = create_engine(raw)

    with engine.begin() as conn:
        for eq in EQUIPMENT:
            conn.execute(
                text(
                    """
                    INSERT INTO energy.equipment (
                        id, name, name_fa, equipment_type, location, line_id, area, status, metadata
                    ) VALUES (
                        :id, :name, :name_fa, :etype, :loc, :line, :area, 'running', CAST(:meta AS jsonb)
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        name_fa = EXCLUDED.name_fa,
                        equipment_type = EXCLUDED.equipment_type,
                        location = EXCLUDED.location,
                        line_id = EXCLUDED.line_id,
                        area = EXCLUDED.area,
                        metadata = EXCLUDED.metadata
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
                    "meta": json.dumps({"sensors": [s["key"] for s in eq["sensors"]]}, ensure_ascii=False),
                },
            )
            for s in eq["sensors"]:
                conn.execute(
                    text(
                        """
                        INSERT INTO energy.sensor_defs (
                            equipment_id, sensor_key, name_fa, unit, min_op, max_op, channel, criticality
                        ) VALUES (
                            :eid, :key, :name_fa, :unit, :min_op, :max_op, :channel, :crit
                        )
                        ON CONFLICT (equipment_id, sensor_key) DO UPDATE SET
                            name_fa = EXCLUDED.name_fa,
                            unit = EXCLUDED.unit,
                            min_op = EXCLUDED.min_op,
                            max_op = EXCLUDED.max_op,
                            channel = EXCLUDED.channel,
                            criticality = EXCLUDED.criticality
                        """
                    ),
                    {
                        "eid": eq["id"],
                        "key": s["key"],
                        "name_fa": s["name_fa"],
                        "unit": s["unit"],
                        "min_op": s["min_op"],
                        "max_op": s["max_op"],
                        "channel": s.get("channel"),
                        "crit": s["criticality"],
                    },
                )

        spike_ids = {"BAG-001", "FAN-001", "DRY-001", "OIL-001"}
        for eq in EQUIPMENT:
            for i in range(5):
                # i==0 is newest (NOW()); spike latest sample for demo alerts
                readings = simulate_reading(eq, spike=(i == 0 and eq["id"] in spike_ids))
                conn.execute(
                    text(
                        """
                        INSERT INTO energy.sensor_readings (
                            time, equipment_id, vibration_x, vibration_y, vibration_z,
                            temperature, pressure, current_draw, oil_pressure, coolant_temp, raw
                        ) VALUES (
                            NOW() - ((:i)::text || ' minutes')::interval,
                            :eid,
                            :vx, :vy, :vz, :temp, :press, :curr, :oil, :cool,
                            CAST(:raw AS jsonb)
                        )
                        """
                    ),
                    {
                        "i": i * 3,
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

    print(f"equipment line seed OK: {len(EQUIPMENT)} units")


if __name__ == "__main__":
    random.seed(42)
    main()
