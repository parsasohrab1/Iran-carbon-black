"""Phase 1 smoke checks against a running stack (gateway :8080)."""

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
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode())


def main() -> None:
    checks = []
    try:
        checks.append(("gateway", call("GET", "/health")))
        checks.append(("topics", call("GET", "/api/v1/ingestion/topics")))
        checks.append(("equipment", call("GET", "/api/v1/energy/equipment")))
        checks.append(("model", call("GET", "/api/v1/energy/model/info")))
        checks.append(
            ("rul", call("POST", "/api/v1/energy/rul/predict", {"equipment_id": "GEN-001", "lookback_hours": 24}))
        )
        checks.append(
            ("source", call("POST", "/api/v1/energy/source/decide", {"line_id": "Line_1", "expected_kwh": 120}))
        )
        checks.append(("summary", call("GET", "/api/v1/energy/consumption/summary?hours=48")))
        checks.append(("alerts", call("GET", "/api/v1/energy/alerts")))
    except urllib.error.URLError as exc:
        print(f"FAIL: stack not reachable at {BASE}: {exc}")
        print("Start with: .\\scripts\\bootstrap.ps1")
        sys.exit(1)

    for name, result in checks:
        print(f"OK {name}: {json.dumps(result, default=str)[:180]}")
    print("Phase 1 smoke checks passed.")


if __name__ == "__main__":
    main()
