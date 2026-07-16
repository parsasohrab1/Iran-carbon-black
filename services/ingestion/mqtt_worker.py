"""MQTT OT edge consumer — icb/energy/+/sensors → TimescaleDB + MinIO."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
import structlog
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from shared.config import Settings
from shared.storage import put_json_object

log = structlog.get_logger()

SENSOR_TOPIC = "icb/energy/+/sensors"
ENERGY_TOPIC = "icb/energy/+/consumption"
QUALITY_TOPIC = "icb/quality/+/process"


class MqttIngestionWorker:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: mqtt.Client | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
        self._Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def start(self) -> None:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="icb-ingestion-worker")
        client.on_connect = self._on_connect
        client.on_message = self._on_message
        client.connect(self.settings.mqtt_host, self.settings.mqtt_port, keepalive=60)
        self._client = client
        self._thread = threading.Thread(target=client.loop_forever, name="mqtt-ingestion", daemon=True)
        self._thread.start()
        log.info("mqtt_worker_started", host=self.settings.mqtt_host, port=self.settings.mqtt_port)

    def stop(self) -> None:
        self._stop.set()
        if self._client is not None:
            self._client.disconnect()
            self._client.loop_stop()
        log.info("mqtt_worker_stopped")

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):  # noqa: ANN001
        client.subscribe(SENSOR_TOPIC, qos=1)
        client.subscribe(ENERGY_TOPIC, qos=1)
        client.subscribe(QUALITY_TOPIC, qos=1)
        log.info(
            "mqtt_subscribed",
            topics=[SENSOR_TOPIC, ENERGY_TOPIC, QUALITY_TOPIC],
            reason=str(reason_code),
        )

    def _on_message(self, client, userdata, msg):  # noqa: ANN001
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            parts = msg.topic.split("/")
            equipment_or_line = parts[2] if len(parts) >= 3 else "unknown"
            if msg.topic.endswith("/sensors"):
                self._handle_sensor(equipment_or_line, payload)
            elif msg.topic.endswith("/consumption"):
                self._handle_consumption(equipment_or_line, payload)
            elif msg.topic.endswith("/process"):
                self._handle_quality(equipment_or_line, payload)
        except Exception as exc:  # noqa: BLE001
            log.error("mqtt_message_error", topic=msg.topic, error=str(exc))

    def _handle_sensor(self, equipment_id: str, payload: dict) -> None:
        sensors = payload.get("sensors") or payload
        eid = payload.get("equipment_id") or equipment_id
        ts_raw = payload.get("timestamp")
        ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00")) if ts_raw else datetime.now(timezone.utc)

        with self._Session() as session:
            self._ensure_equipment(session, eid)
            session.execute(
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
                    "equipment_id": eid,
                    "vx": sensors.get("vibration_x"),
                    "vy": sensors.get("vibration_y"),
                    "vz": sensors.get("vibration_z"),
                    "temp": sensors.get("temperature"),
                    "pressure": sensors.get("pressure"),
                    "current": sensors.get("current_draw"),
                    "oil": sensors.get("oil_pressure"),
                    "coolant": sensors.get("coolant_temp"),
                    "raw": json.dumps({"topic": "sensors", **payload}, default=str),
                },
            )
            session.commit()

        try:
            object_name = f"energy/sensors/{eid}/{ts.strftime('%Y/%m/%d/%H%M%S%f')}.json"
            put_json_object(
                self.settings.minio_bucket_raw,
                object_name,
                json.dumps({"equipment_id": eid, "timestamp": ts.isoformat(), "sensors": sensors}).encode(),
                settings=self.settings,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("datalake_write_failed", error=str(exc))

        log.info("sensor_ingested_mqtt", equipment_id=eid)

    def _handle_consumption(self, line_id: str, payload: dict) -> None:
        lid = payload.get("line_id") or line_id
        ts_raw = payload.get("timestamp")
        ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00")) if ts_raw else datetime.now(timezone.utc)
        kwh = float(payload.get("kwh", 0))
        source = payload.get("source", "grid")
        price = payload.get("price_irr_per_kwh")
        cost = float(price) * kwh if price is not None else payload.get("cost_irr")

        with self._Session() as session:
            session.execute(
                text(
                    """
                    INSERT INTO energy.energy_consumption (time, line_id, source, kwh, cost_irr, price_forecast)
                    VALUES (:time, :line_id, :source, :kwh, :cost, :price)
                    """
                ),
                {
                    "time": ts,
                    "line_id": lid,
                    "source": source,
                    "kwh": kwh,
                    "cost": cost,
                    "price": price,
                },
            )
            session.commit()
        log.info("consumption_ingested_mqtt", line_id=lid, source=source, kwh=kwh)

    def _handle_quality(self, batch_hint: str, payload: dict) -> None:
        batch_id = payload.get("batch_id") or f"CB-MQTT-{batch_hint}"
        grade = payload.get("grade", "N220")
        line = int(payload.get("production_line", 1))
        ts_raw = payload.get("timestamp")
        ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00")) if ts_raw else datetime.now(timezone.utc)
        process = payload.get("process_parameters") or {}
        quality = payload.get("quality_metrics") or {}

        with self._Session() as session:
            session.execute(
                text(
                    """
                    INSERT INTO quality.batches (batch_id, production_line, grade, started_at, status)
                    VALUES (:batch_id, :line, :grade, :started, 'in_progress')
                    ON CONFLICT (batch_id) DO NOTHING
                    """
                ),
                {"batch_id": batch_id, "line": line, "grade": grade, "started": ts},
            )
            if process:
                session.execute(
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
                        "batch_id": batch_id,
                        "rt": process.get("reactor_temp"),
                        "fr": process.get("feed_rate"),
                        "af": process.get("air_flow"),
                        "res": process.get("residence_time"),
                        "pr": process.get("pressure"),
                        "oar": process.get("oil_to_air_ratio"),
                        "raw": json.dumps(payload, default=str),
                    },
                )
            if quality:
                session.execute(
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
                        "batch_id": batch_id,
                        "iodine": quality.get("iodine_absorption"),
                        "dbp": quality.get("DBP_absorption") or quality.get("dbp_absorption"),
                        "sa": quality.get("surface_area"),
                        "ps": quality.get("particle_size"),
                        "tint": quality.get("tint_strength"),
                    },
                )
            session.commit()
        log.info("quality_ingested_mqtt", batch_id=batch_id, grade=grade)

    @staticmethod
    def _ensure_equipment(session: Session, equipment_id: str) -> None:
        session.execute(
            text(
                """
                INSERT INTO energy.equipment (id, name, equipment_type, location, line_id)
                VALUES (:id, :name, 'unknown', 'OT-edge', 'UTIL')
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {"id": equipment_id, "name": equipment_id},
        )
