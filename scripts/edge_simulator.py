"""OT edge simulator — publishes pilot sensor + consumption MQTT messages."""

from __future__ import annotations

import json
import os
import random
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
INTERVAL_SEC = float(os.getenv("EDGE_INTERVAL_SEC", "10"))
EQUIPMENT = ["GEN-001", "CMP-001", "FUR-001", "CLR-001"]
LINES = ["Line_1", "UTIL"]

# Slowly degrade GEN-001 so RUL alerts can be demonstrated
_gen_stress = 0.0


def sensor_payload(equipment_id: str) -> dict:
    global _gen_stress
    stress = 0.0
    if equipment_id == "GEN-001":
        _gen_stress = min(1.0, _gen_stress + 0.01)
        stress = _gen_stress

    return {
        "equipment_id": equipment_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operational_status": "running",
        "sensors": {
            "vibration_x": round(2.0 + stress * 3 + random.random() * 0.2, 3),
            "vibration_y": round(1.6 + stress * 2.5 + random.random() * 0.2, 3),
            "vibration_z": round(2.8 + stress * 4 + random.random() * 0.3, 3),
            "temperature": round(72 + stress * 30 + random.random() * 2, 2),
            "pressure": round(12 + stress * 2 + random.random() * 0.3, 2),
            "current_draw": round(145 + stress * 40 + random.random() * 5, 2),
            "oil_pressure": round(4.8 - stress * 1.5 + random.random() * 0.1, 2),
            "coolant_temp": round(62 + stress * 18 + random.random() * 1.5, 2),
        },
    }


def consumption_payload(line_id: str) -> dict:
    hour = datetime.now().hour
    source = "generator" if 18 <= hour < 22 else "grid"
    price = 8200 if source == "generator" else (4500 * (1.6 if 18 <= hour < 22 else 1.0))
    kwh = round(70 + random.random() * 50, 2)
    return {
        "line_id": line_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "kwh": kwh,
        "price_irr_per_kwh": price,
        "cost_irr": round(kwh * price, 2),
    }


def quality_payload(batch_suffix: int = 42) -> dict:
    anomalous = random.random() < 0.15
    return {
        "batch_id": f"CB-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}-{batch_suffix:04d}",
        "production_line": 1,
        "grade": random.choice(["N220", "N330", "N550"]),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "process_parameters": {
            "reactor_temp": round((1480 if anomalous else 1420) + random.random() * 15, 1),
            "feed_rate": round(2.3 + random.random() * 0.3, 2),
            "air_flow": round(17.5 + random.random() * 2, 1),
            "residence_time": round(2.1 + random.random() * 0.4, 2),
            "pressure": round(1.35 + random.random() * 0.2, 2),
            "oil_to_air_ratio": round((0.95 if anomalous else 0.75) + random.random() * 0.08, 2),
        },
        "quality_metrics": {
            "iodine_absorption": round((70 if anomalous else 82) + random.random() * 4, 1),
            "DBP_absorption": round(110 + random.random() * 10, 1),
            "surface_area": round(75 + random.random() * 6, 1),
            "particle_size": round(20 + random.random() * 5, 1),
            "tint_strength": round(110 + random.random() * 12, 1),
        },
    }


def main() -> None:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="icb-edge-simulator")
    while True:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            break
        except Exception as exc:  # noqa: BLE001
            print(f"Waiting for MQTT broker at {MQTT_HOST}:{MQTT_PORT}: {exc}")
            time.sleep(3)

    client.loop_start()
    print(f"Edge simulator publishing every {INTERVAL_SEC}s to {MQTT_HOST}:{MQTT_PORT}")
    batch_n = 200
    try:
        while True:
            for eid in EQUIPMENT:
                topic = f"icb/energy/{eid}/sensors"
                payload = sensor_payload(eid)
                client.publish(topic, json.dumps(payload), qos=1)
                print(f"published {topic}")
            for line in LINES:
                topic = f"icb/energy/{line}/consumption"
                payload = consumption_payload(line)
                client.publish(topic, json.dumps(payload), qos=1)
                print(f"published {topic} source={payload['source']}")
            q = quality_payload(batch_n)
            batch_n += 1
            q_topic = f"icb/quality/{q['batch_id']}/process"
            client.publish(q_topic, json.dumps(q), qos=1)
            print(f"published {q_topic} grade={q['grade']}")
            time.sleep(INTERVAL_SEC)
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
