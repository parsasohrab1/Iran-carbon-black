"""Phase 5 smoke checks (MLOps / inventory / ROI / portfolio)."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"


def call(method: str, path: str, body: dict | None = None) -> dict | list:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"} if body else {},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def main() -> None:
    try:
        checks = [
            ("models", call("GET", "/api/v1/maturity/models")),
            ("portfolio", call("GET", "/api/v1/maturity/portfolio")),
            ("mix", call("POST", "/api/v1/maturity/portfolio/recommend-mix")),
            ("inventory", call("GET", "/api/v1/maturity/inventory")),
            ("optimize", call("POST", "/api/v1/maturity/inventory/optimize")),
            ("benefits", call("GET", "/api/v1/maturity/benefits")),
            ("roi", call("POST", "/api/v1/maturity/roi/snapshot")),
            ("dashboard", call("GET", "/api/v1/maturity/dashboard")),
            # Retrain one lightweight domain to validate MLOps path
            ("retrain_supply", call("POST", "/api/v1/maturity/retrain", {"domain": "supply", "promote": False})),
        ]
    except urllib.error.URLError as exc:
        print(f"FAIL: stack not reachable at {BASE}: {exc}")
        print("Start with: .\\scripts\\bootstrap.ps1")
        sys.exit(1)

    for name, result in checks:
        print(f"OK {name}: {json.dumps(result, default=str)[:220]}")
    print("Phase 5 smoke checks passed.")


if __name__ == "__main__":
    main()
