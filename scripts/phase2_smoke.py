"""Phase 2 smoke checks (quality / demand / supply) against gateway :8080."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"


def call(method: str, path: str, body: dict | None = None) -> dict:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"} if body else {},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def main() -> None:
    try:
        checks = [
            ("quality_model", call("GET", "/api/v1/quality/model/info")),
            (
                "anomaly",
                call(
                    "POST",
                    "/api/v1/quality/anomaly/check",
                    {
                        "batch_id": "CB-2026-07-16-0042",
                        "grade": "N220",
                        "process_parameters": {
                            "reactor_temp": 1425,
                            "feed_rate": 2.45,
                            "air_flow": 18.7,
                            "residence_time": 2.3,
                            "pressure": 1.45,
                            "oil_to_air_ratio": 0.78,
                        },
                        "quality_metrics": {
                            "iodine_absorption": 82.5,
                            "dbp_absorption": 115.0,
                            "surface_area": 78.0,
                            "particle_size": 22.0,
                            "tint_strength": 118.0,
                        },
                    },
                ),
            ),
            (
                "optimize",
                call(
                    "POST",
                    "/api/v1/quality/process/optimize",
                    {
                        "batch_id": "CB-2026-07-16-0042",
                        "grade": "N220",
                        "process_parameters": {
                            "reactor_temp": 1460,
                            "feed_rate": 2.6,
                            "air_flow": 17.0,
                            "residence_time": 2.1,
                            "pressure": 1.5,
                            "oil_to_air_ratio": 0.85,
                        },
                    },
                ),
            ),
            ("demand_model", call("GET", "/api/v1/demand/model/info")),
            (
                "forecast_n220",
                call(
                    "POST",
                    "/api/v1/demand/forecast",
                    {"product_grade": "N220", "forecast_period": "3_months"},
                ),
            ),
            (
                "production_plan",
                call("POST", "/api/v1/demand/production/plan", {"forecast_period": "3_months"}),
            ),
            (
                "recommend",
                call(
                    "POST",
                    "/api/v1/demand/recommend-grade",
                    {"conductivity": "high", "dispersion": "medium", "tint_strength": "high"},
                ),
            ),
            ("supply_model", call("GET", "/api/v1/supply/model/info")),
            (
                "purchase",
                call(
                    "POST",
                    "/api/v1/supply/purchase/advice",
                    {"material": "Coal tar (furfural extract)", "horizon_days": 90},
                ),
            ),
        ]
    except urllib.error.URLError as exc:
        print(f"FAIL: stack not reachable at {BASE}: {exc}")
        print("Start with: .\\scripts\\bootstrap.ps1")
        sys.exit(1)

    for name, result in checks:
        print(f"OK {name}: {json.dumps(result, default=str)[:200]}")
    print("Phase 2 smoke checks passed.")


if __name__ == "__main__":
    main()
