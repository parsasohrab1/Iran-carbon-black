"""Phase 4 smoke checks (security / training / ops / SLA)."""

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
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def main() -> None:
    try:
        checks = [
            ("zones", call("GET", "/api/v1/ops/zones")),
            ("ops_status", call("GET", "/api/v1/ops/status")),
            ("sla", call("GET", "/api/v1/ops/sla")),
            ("courses", call("GET", "/api/v1/training/courses")),
            ("enroll", call("POST", "/api/v1/training/enroll", {"course_id": "TRN-SEC-01", "username": "admin"})),
            ("compliance", call("GET", "/api/v1/training/compliance")),
            ("changes", call("GET", "/api/v1/training/changes")),
            (
                "survey",
                call(
                    "POST",
                    "/api/v1/training/surveys",
                    {
                        "change_request_id": 1,
                        "username": "admin",
                        "acceptance_score": 4,
                        "feedback": "Ready for rollout",
                    },
                ),
            ),
            (
                "login_flow",
                call("POST", "/api/v1/auth/login", {"username": "admin", "password": "Admin@ChangeMe1"}),
            ),
        ]
    except urllib.error.URLError as exc:
        print(f"FAIL: stack not reachable at {BASE}: {exc}")
        print("Start with: .\\scripts\\bootstrap.ps1")
        sys.exit(1)

    for name, result in checks:
        print(f"OK {name}: {json.dumps(result, default=str)[:220]}")
    print("Phase 4 smoke checks passed.")


if __name__ == "__main__":
    main()
