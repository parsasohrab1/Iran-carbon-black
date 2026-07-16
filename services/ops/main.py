"""Ops / SLA monitoring service — availability ≥ 99.9%, RTO/RPO tracking."""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.app_factory import create_app
from shared.config import get_settings
from shared.db import SessionLocal, get_db

settings = get_settings()

MONITORED_SERVICES = {
    "auth": "http://auth:8001/health",
    "ingestion": "http://ingestion:8002/health",
    "energy": "http://energy:8003/health",
    "supply": "http://supply:8004/health",
    "quality": "http://quality:8005/health",
    "sales": "http://sales:8006/health",
    "finance": "http://finance:8007/health",
    "demand": "http://demand:8008/health",
    "integration": "http://integration:8009/health",
    "training": "http://training:8010/health",
    "ops": "http://ops:8011/health",
    "maturity": "http://maturity:8012/health",
}

_probe_task: asyncio.Task | None = None


async def _probe_once() -> dict:
    results = {}
    async with httpx.AsyncClient(timeout=3.0) as client:
        for name, url in MONITORED_SERVICES.items():
            started = time.perf_counter()
            status = "down"
            detail = {}
            try:
                resp = await client.get(url)
                latency = (time.perf_counter() - started) * 1000
                status = "up" if resp.status_code == 200 else "degraded"
                detail = {"http_status": resp.status_code}
            except Exception as exc:  # noqa: BLE001
                latency = (time.perf_counter() - started) * 1000
                detail = {"error": str(exc)}
            results[name] = {"status": status, "latency_ms": round(latency, 2), "detail": detail}
    return results


async def _persist_probe(results: dict) -> None:
    import json

    async with SessionLocal() as db:
        for name, item in results.items():
            await db.execute(
                text(
                    """
                    INSERT INTO ops.service_heartbeats (service_name, checked_at, status, latency_ms, detail)
                    VALUES (:name, NOW(), :status, :latency, :detail::jsonb)
                    """
                ),
                {
                    "name": name,
                    "status": item["status"],
                    "latency": item["latency_ms"],
                    "detail": json.dumps(item["detail"]),
                },
            )
        # Daily SLA rollup (best-effort)
        rollup = await db.execute(
            text(
                """
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE status <> 'up') AS failed
                FROM ops.service_heartbeats
                WHERE checked_at::date = CURRENT_DATE
                """
            )
        )
        row = rollup.mappings().first()
        total = int(row["total"] or 0)
        failed = int(row["failed"] or 0)
        availability = 100.0 if total == 0 else round(100.0 * (total - failed) / total, 4)
        await db.execute(
            text(
                """
                INSERT INTO ops.sla_daily (day, availability_pct, checks_total, checks_failed, rto_seconds, rpo_seconds)
                VALUES (CURRENT_DATE, :avail, :total, :failed, :rto, :rpo)
                ON CONFLICT (day) DO UPDATE SET
                    availability_pct = EXCLUDED.availability_pct,
                    checks_total = EXCLUDED.checks_total,
                    checks_failed = EXCLUDED.checks_failed
                """
            ),
            {
                "avail": availability,
                "total": total,
                "failed": failed,
                "rto": settings.rto_seconds,
                "rpo": settings.rpo_seconds,
            },
        )
        await db.commit()


async def _probe_loop() -> None:
    while True:
        try:
            results = await _probe_once()
            await _persist_probe(results)
        except Exception:
            pass
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app):  # noqa: ANN001, ARG001
    global _probe_task
    _probe_task = asyncio.create_task(_probe_loop())
    yield
    if _probe_task:
        _probe_task.cancel()
        try:
            await _probe_task
        except asyncio.CancelledError:
            pass


app = create_app(settings, title="ICB Ops / SLA Service", version="4.0.0", lifespan=lifespan)
router = APIRouter(prefix="/api/v1/ops", tags=["ops"])


class BackupReport(BaseModel):
    status: str = "success"
    backup_path: str | None = None
    size_bytes: int | None = None
    components: dict | None = None
    error_message: str | None = None


@router.get("/status")
async def live_status() -> dict:
    results = await _probe_once()
    up = sum(1 for v in results.values() if v["status"] == "up")
    total = len(results)
    availability = round(100.0 * up / max(total, 1), 3)
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "services": results,
        "availability_pct": availability,
        "target_availability_pct": settings.sla_availability_target,
        "sla_met": availability >= settings.sla_availability_target,
        "rto_seconds": settings.rto_seconds,
        "rpo_seconds": settings.rpo_seconds,
    }


@router.get("/sla")
async def sla_history(days: int = 14, db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(
        text(
            """
            SELECT day, availability_pct, checks_total, checks_failed, rto_seconds, rpo_seconds
            FROM ops.sla_daily
            ORDER BY day DESC
            LIMIT :days
            """
        ),
        {"days": days},
    )
    rows = [dict(r) for r in result.mappings().all()]
    avg = round(sum(r["availability_pct"] for r in rows) / len(rows), 4) if rows else None
    return {
        "target_availability_pct": settings.sla_availability_target,
        "average_availability_pct": avg,
        "rto_seconds": settings.rto_seconds,
        "rpo_seconds": settings.rpo_seconds,
        "history": rows,
    }


@router.post("/backups/report")
async def report_backup(body: BackupReport, db: AsyncSession = Depends(get_db)) -> dict:
    import json

    await db.execute(
        text(
            """
            INSERT INTO ops.backup_runs (finished_at, status, backup_path, size_bytes, components, error_message)
            VALUES (NOW(), :status, :path, :size, :components::jsonb, :err)
            """
        ),
        {
            "status": body.status,
            "path": body.backup_path,
            "size": body.size_bytes,
            "components": json.dumps(body.components or {}),
            "err": body.error_message,
        },
    )
    await db.commit()
    return {"status": "recorded", "day": str(date.today())}


@router.get("/backups")
async def list_backups(limit: int = 20, db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(
        text(
            """
            SELECT id, started_at, finished_at, status, backup_path, size_bytes, components, error_message
            FROM ops.backup_runs ORDER BY started_at DESC LIMIT :limit
            """
        ),
        {"limit": limit},
    )
    return [dict(r) for r in result.mappings().all()]


@router.get("/zones")
async def network_zones() -> dict:
    """OT/IT zoning map for on-premise hardening."""
    return {
        "zones": {
            "ot": {
                "description": "Operational technology — sensors, DCS, MQTT, ingestion",
                "allowed_paths": settings.ot_api_allowlist.split(","),
                "services": ["mosquitto", "ingestion", "energy"],
            },
            "it": {
                "description": "Information technology — business apps, dashboards, ERP sync",
                "services": ["sales", "finance", "demand", "supply", "integration", "training", "auth"],
            },
            "dmz": {
                "description": "API gateway / reverse proxy edge",
                "services": ["gateway"],
            },
        },
        "policy": "OT data stays on-premise; no direct internet egress from OT VLAN.",
    }


app.include_router(router)
