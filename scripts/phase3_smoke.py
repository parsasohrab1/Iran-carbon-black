"""Phase 3 smoke checks (sales / finance / ERP) against gateway :8080."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import date

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"


def call(method: str, path: str, body: dict | None = None) -> dict | list:
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
            ("sales_model", call("GET", "/api/v1/sales/model/info")),
            ("forecast", call("POST", "/api/v1/sales/forecast", {"grade": "N330", "months_ahead": 1})),
            ("pricing", call("POST", "/api/v1/sales/pricing/recommend", {"grade": "N330", "region": "domestic"})),
            ("crm_risk", call("GET", "/api/v1/sales/crm/at-risk")),
            ("customer", call("GET", "/api/v1/sales/customers/CUST-0047")),
            ("finance_model", call("GET", "/api/v1/finance/model/info")),
            ("cashflow", call("POST", "/api/v1/finance/cashflow/forecast", {"horizon_days": 90})),
            ("ratios", call("GET", "/api/v1/finance/ratios/analyze")),
            ("dashboard", call("GET", "/api/v1/finance/dashboard")),
            (
                "erp_sales",
                call(
                    "POST",
                    "/api/v1/erp/sales/orders",
                    {
                        "external_id": "ERP-SO-1001",
                        "sale_date": str(date.today()),
                        "customer_id": "CUST-0047",
                        "grade": "N330",
                        "quantity_kg": 5000,
                        "unit_price_irr": 186000,
                        "region": "domestic",
                    },
                ),
            ),
            ("erp_contract", call("GET", "/api/v1/erp/openapi-contract")),
            ("erp_export", call("GET", "/api/v1/erp/export/sales-forecasts?limit=5")),
        ]
    except urllib.error.URLError as exc:
        print(f"FAIL: stack not reachable at {BASE}: {exc}")
        print("Start with: .\\scripts\\bootstrap.ps1")
        sys.exit(1)

    for name, result in checks:
        print(f"OK {name}: {json.dumps(result, default=str)[:200]}")
    print("Phase 3 smoke checks passed.")


if __name__ == "__main__":
    main()
