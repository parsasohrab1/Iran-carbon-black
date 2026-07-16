#!/usr/bin/env python3
"""Generate synthetic IoT/OT payloads matching SRS samples and POST to ingestion."""

from __future__ import annotations

import argparse
import json
import random
import urllib.request
from datetime import datetime, timezone


def post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def sensor_sample(equipment_id: str = "GEN-001") -> dict:
    return {
        "equipment_id": equipment_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sensors": {
            "vibration_x": round(2.0 + random.random(), 2),
            "vibration_y": round(1.5 + random.random(), 2),
            "vibration_z": round(2.5 + random.random() * 1.5, 2),
            "temperature": round(70 + random.random() * 15, 1),
            "pressure": round(11 + random.random() * 2, 1),
            "current_draw": round(140 + random.random() * 20, 1),
            "oil_pressure": round(4.5 + random.random() * 0.8, 1),
            "coolant_temp": round(60 + random.random() * 10, 1),
        },
        "operational_status": "running",
    }


def quality_sample(batch_suffix: int = 42) -> dict:
    return {
        "batch_id": f"CB-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}-{batch_suffix:04d}",
        "production_line": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "process_parameters": {
            "reactor_temp": round(1400 + random.random() * 50, 1),
            "feed_rate": round(2.2 + random.random() * 0.5, 2),
            "air_flow": round(17 + random.random() * 3, 1),
            "residence_time": round(2.0 + random.random() * 0.5, 1),
            "pressure": round(1.3 + random.random() * 0.3, 2),
            "oil_to_air_ratio": round(0.7 + random.random() * 0.15, 2),
        },
        "quality_metrics": {
            "iodine_absorption": round(80 + random.random() * 5, 1),
            "DBP_absorption": round(110 + random.random() * 10, 1),
            "surface_area": round(75 + random.random() * 7, 1),
            "particle_size": round(20 + random.random() * 5, 1),
            "tint_strength": round(110 + random.random() * 15, 1),
        },
        "grade": "N220",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed synthetic data into ICB ingestion API")
    parser.add_argument("--base-url", default="http://localhost:8080")
    parser.add_argument("--sensors", type=int, default=5)
    parser.add_argument("--batches", type=int, default=2)
    args = parser.parse_args()

    for i in range(args.sensors):
        eq = random.choice(["GEN-001", "CMP-001", "FUR-001", "CLR-001"])
        result = post_json(f"{args.base_url}/api/v1/ingestion/sensors", sensor_sample(eq))
        print(f"sensor[{i}] -> {result}")

    for i in range(args.batches):
        result = post_json(f"{args.base_url}/api/v1/ingestion/quality", quality_sample(100 + i))
        print(f"quality[{i}] -> {result}")


if __name__ == "__main__":
    main()
