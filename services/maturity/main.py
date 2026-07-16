"""Phase 5 maturity service — MLOps, inventory, grade mix, ROI/benefits."""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ml.demand.train_forecast import GRADE_PROPERTIES
from ml.mlops import list_minio_models, retrain_domain
from shared.app_factory import create_app
from shared.config import get_settings
from shared.db import SessionLocal, get_db

settings = get_settings()

# Proposal targets (billion IRR converted to IRR)
ANNUAL_BENEFIT_TARGET = 200_000_000_000
ANNUAL_OPEX = 36_000_000_000
CUMULATIVE_CAPEX = 141_000_000_000
FULL_MATURITY_MONTHS = 24

CATEGORY_FULL_YEAR = {
    "emergency_maintenance": 35_000_000_000,
    "energy": 40_000_000_000,
    "quality_waste": 30_000_000_000,
    "pricing_sales": 40_000_000_000,
    "procurement": 20_000_000_000,
    "demand_driven": 35_000_000_000,
}

_scheduler_task: asyncio.Task | None = None


async def _weekly_retrain_loop() -> None:
    """Background MLOps loop — weekly retrain all domains (accelerated interval in container)."""
    interval = 7 * 24 * 3600 if settings.is_production else 3600  # 1h in non-prod for demo
    domains = ["energy", "quality", "demand", "supply", "sales", "finance"]
    while True:
        await asyncio.sleep(interval)
        for domain in domains:
            try:
                async with SessionLocal() as db:
                    await _run_retrain_job(db, domain, trigger_source="scheduler")
            except Exception:
                continue


@asynccontextmanager
async def lifespan(app):  # noqa: ANN001, ARG001
    global _scheduler_task
    _scheduler_task = asyncio.create_task(_weekly_retrain_loop())
    yield
    if _scheduler_task:
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass


app = create_app(settings, title="ICB Maturity / MLOps Service", version="5.0.0", lifespan=lifespan)
router = APIRouter(prefix="/api/v1/maturity", tags=["maturity"])


class RetrainRequest(BaseModel):
    domain: str
    promote: bool = False


class InventoryUpdate(BaseModel):
    product_grade: str
    on_hand_kg: float | None = None
    safety_stock_kg: float | None = None
    reorder_point_kg: float | None = None
    target_days_cover: int | None = None


class BenefitUpsert(BaseModel):
    period_month: date
    category: str
    amount_irr: float
    maturity_factor: float = Field(default=1.0, ge=0, le=1)
    notes: str | None = None


async def _run_retrain_job(db: AsyncSession, domain: str, trigger_source: str = "api", promote: bool = False) -> dict:
    job = await db.execute(
        text(
            """
            INSERT INTO maturity.retrain_jobs (domain, status, started_at, trigger_source)
            VALUES (:domain, 'running', NOW(), :src)
            RETURNING id
            """
        ),
        {"domain": domain, "src": trigger_source},
    )
    job_id = job.scalar_one()
    await db.commit()
    try:
        # train is CPU-bound; run in thread to avoid blocking event loop
        result = await asyncio.to_thread(retrain_domain, domain, settings)
        metrics = {k: v for k, v in result.items() if k not in {"model_path", "local_path", "minio_warning"}}
        status = "production" if promote else "staged"
        await db.execute(
            text(
                """
                INSERT INTO maturity.model_registry
                    (domain, model_name, version, artifact_uri, metrics, status, promoted_at)
                VALUES (:domain, :name, :version, :uri, :metrics::jsonb, :status, CASE WHEN :promote THEN NOW() ELSE NULL END)
                ON CONFLICT (domain, model_name, version) DO UPDATE SET
                    artifact_uri = EXCLUDED.artifact_uri,
                    metrics = EXCLUDED.metrics,
                    status = EXCLUDED.status,
                    promoted_at = COALESCE(EXCLUDED.promoted_at, maturity.model_registry.promoted_at)
                """
            ),
            {
                "domain": domain,
                "name": result["model_name"],
                "version": result["version"],
                "uri": result.get("artifact_uri"),
                "metrics": json.dumps(metrics, default=str),
                "status": status,
                "promote": promote,
            },
        )
        await db.execute(
            text(
                """
                UPDATE maturity.retrain_jobs
                SET status = 'succeeded', finished_at = NOW(), metrics = :metrics::jsonb, artifact_uri = :uri
                WHERE id = :id
                """
            ),
            {"metrics": json.dumps(metrics, default=str), "uri": result.get("artifact_uri"), "id": job_id},
        )
        await db.commit()
        return {"job_id": job_id, "status": "succeeded", **result}
    except Exception as exc:  # noqa: BLE001
        await db.execute(
            text(
                """
                UPDATE maturity.retrain_jobs
                SET status = 'failed', finished_at = NOW(), error_message = :err
                WHERE id = :id
                """
            ),
            {"err": str(exc), "id": job_id},
        )
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Retrain failed: {exc}") from exc


@router.get("/models")
async def list_models(db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(
        text(
            """
            SELECT id, domain, model_name, version, artifact_uri, metrics, status, trained_at, promoted_at
            FROM maturity.model_registry
            ORDER BY trained_at DESC
            """
        )
    )
    return [dict(r) for r in result.mappings().all()]


@router.get("/models/minio")
async def list_models_minio() -> dict:
    return {"bucket": settings.minio_bucket_models, "objects": list_minio_models(settings)}


@router.post("/retrain")
async def retrain(body: RetrainRequest, db: AsyncSession = Depends(get_db)) -> dict:
    return await _run_retrain_job(db, body.domain, trigger_source="api", promote=body.promote)


@router.post("/models/{domain}/{version}/promote")
async def promote_model(domain: str, version: str, db: AsyncSession = Depends(get_db)) -> dict:
    # retire previous production for domain
    await db.execute(
        text(
            """
            UPDATE maturity.model_registry
            SET status = 'retired'
            WHERE domain = :domain AND status = 'production'
            """
        ),
        {"domain": domain},
    )
    result = await db.execute(
        text(
            """
            UPDATE maturity.model_registry
            SET status = 'production', promoted_at = NOW()
            WHERE domain = :domain AND version = :version
            RETURNING id, model_name, version, artifact_uri
            """
        ),
        {"domain": domain, "version": version},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Model version not found")
    await db.commit()
    return {"status": "promoted", **dict(row)}


@router.get("/retrain/jobs")
async def retrain_jobs(limit: int = 30, db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(
        text(
            """
            SELECT id, domain, status, started_at, finished_at, metrics, artifact_uri, error_message, trigger_source
            FROM maturity.retrain_jobs ORDER BY created_at DESC LIMIT :limit
            """
        ),
        {"limit": limit},
    )
    return [dict(r) for r in result.mappings().all()]


@router.get("/inventory")
async def inventory(db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(text("SELECT * FROM maturity.inventory_positions ORDER BY product_grade"))
    return [dict(r) for r in result.mappings().all()]


@router.put("/inventory/{grade}")
async def update_inventory(grade: str, body: InventoryUpdate, db: AsyncSession = Depends(get_db)) -> dict:
    await db.execute(
        text(
            """
            INSERT INTO maturity.inventory_positions (product_grade, on_hand_kg, safety_stock_kg, reorder_point_kg, target_days_cover)
            VALUES (:grade, COALESCE(:on_hand, 0), COALESCE(:safety, 0), COALESCE(:reorder, 0), COALESCE(:days, 21))
            ON CONFLICT (product_grade) DO UPDATE SET
                on_hand_kg = COALESCE(:on_hand, maturity.inventory_positions.on_hand_kg),
                safety_stock_kg = COALESCE(:safety, maturity.inventory_positions.safety_stock_kg),
                reorder_point_kg = COALESCE(:reorder, maturity.inventory_positions.reorder_point_kg),
                target_days_cover = COALESCE(:days, maturity.inventory_positions.target_days_cover),
                updated_at = NOW()
            """
        ),
        {
            "grade": grade,
            "on_hand": body.on_hand_kg,
            "safety": body.safety_stock_kg,
            "reorder": body.reorder_point_kg,
            "days": body.target_days_cover,
        },
    )
    await db.commit()
    return {"status": "updated", "product_grade": grade}


@router.post("/inventory/optimize")
async def optimize_inventory(db: AsyncSession = Depends(get_db)) -> dict:
    """Reduce excess stock and flag replenishment using demand + margin signals."""
    positions = await db.execute(text("SELECT * FROM maturity.inventory_positions"))
    demand = await db.execute(
        text(
            """
            SELECT DISTINCT ON (product_grade) product_grade, forecast_quantity_kg
            FROM demand.forecasts
            WHERE forecast_period = '3_months'
            ORDER BY product_grade, created_at DESC
            """
        )
    )
    demand_map = {r["product_grade"]: float(r["forecast_quantity_kg"]) for r in demand.mappings().all()}
    actions = []
    for row in positions.mappings().all():
        grade = row["product_grade"]
        on_hand = float(row["on_hand_kg"])
        safety = float(row["safety_stock_kg"])
        reorder = float(row["reorder_point_kg"])
        forecast_3m = demand_map.get(grade)
        monthly = (forecast_3m / 3.0) if forecast_3m else on_hand / max(int(row["target_days_cover"]) / 30, 0.5)
        target_cover = monthly * (int(row["target_days_cover"]) / 30.0)
        margin = float(GRADE_PROPERTIES.get(grade, {}).get("margin", 0.08))
        if on_hand > target_cover * 1.25:
            excess = on_hand - target_cover
            saving = excess * 50000 * margin  # proxy carrying-cost avoidance
            action = {
                "product_grade": grade,
                "action": "drawdown",
                "quantity_kg": round(excess, 2),
                "reason": "On-hand exceeds target cover; reduce overproduction / prioritize sales.",
                "expected_saving_irr": round(saving, 2),
            }
        elif on_hand < reorder:
            need = max(reorder - on_hand, safety)
            action = {
                "product_grade": grade,
                "action": "produce" if margin >= 0.09 else "expedite",
                "quantity_kg": round(need, 2),
                "reason": "Below reorder point; replenish with margin-aware priority.",
                "expected_saving_irr": round(need * 20000 * margin, 2),
            }
        else:
            action = {
                "product_grade": grade,
                "action": "hold",
                "quantity_kg": 0,
                "reason": "Within band.",
                "expected_saving_irr": 0,
            }
        actions.append(action)
        await db.execute(
            text(
                """
                INSERT INTO maturity.inventory_actions
                    (product_grade, action, quantity_kg, reason, expected_saving_irr)
                VALUES (:grade, :action, :qty, :reason, :saving)
                """
            ),
            {
                "grade": action["product_grade"],
                "action": action["action"],
                "qty": action["quantity_kg"],
                "reason": action["reason"],
                "saving": action["expected_saving_irr"],
            },
        )
    await db.commit()
    total_saving = sum(a["expected_saving_irr"] for a in actions)
    priority = sorted(
        [a for a in actions if a["action"] in {"produce", "expedite"}],
        key=lambda a: GRADE_PROPERTIES.get(a["product_grade"], {}).get("margin", 0),
        reverse=True,
    )
    return {
        "actions": actions,
        "priority_replenish": priority[:5],
        "expected_total_saving_irr": round(total_saving, 2),
        "model_version": "inventory-optimizer-v1",
    }


@router.get("/portfolio")
async def portfolio(db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(
        text(
            """
            SELECT product_grade, margin_score, strategic_flag, specialty_tag, target_share_pct, notes
            FROM maturity.grade_portfolio
            ORDER BY margin_score DESC
            """
        )
    )
    rows = [dict(r) for r in result.mappings().all()]
    high_margin = [r for r in rows if r["margin_score"] >= 0.09]
    return {
        "grades": rows,
        "high_margin_focus": high_margin,
        "recommended_shift": "Increase share of conductive/specialty grades (N110/N115/N234) vs low-margin carcass.",
    }


@router.post("/portfolio/recommend-mix")
async def recommend_mix(db: AsyncSession = Depends(get_db)) -> dict:
    """Suggest production mix tilted to higher-margin specialty grades."""
    port = await db.execute(text("SELECT * FROM maturity.grade_portfolio ORDER BY margin_score DESC"))
    inv = await db.execute(text("SELECT product_grade, on_hand_kg FROM maturity.inventory_positions"))
    inv_map = {r["product_grade"]: float(r["on_hand_kg"]) for r in inv.mappings().all()}
    recommendations = []
    for row in port.mappings().all():
        grade = row["product_grade"]
        margin = float(row["margin_score"])
        target = float(row["target_share_pct"] or 0)
        on_hand = inv_map.get(grade, 0)
        if margin >= 0.1:
            delta = "increase"
            rationale = "High-margin specialty — expand allocation if demand allows."
        elif on_hand > 0 and margin < 0.075:
            delta = "decrease"
            rationale = "Low-margin grade with inventory — tighten production."
        else:
            delta = "maintain"
            rationale = "Keep near target share."
        recommendations.append(
            {
                "product_grade": grade,
                "margin_score": margin,
                "target_share_pct": target,
                "on_hand_kg": on_hand,
                "action": delta,
                "rationale": rationale,
                "specialty_tag": row["specialty_tag"],
            }
        )
    return {"mix": recommendations, "model_version": "grade-mix-v1"}


@router.post("/benefits")
async def upsert_benefit(body: BenefitUpsert, db: AsyncSession = Depends(get_db)) -> dict:
    await db.execute(
        text(
            """
            INSERT INTO maturity.benefits_ledger (period_month, category, amount_irr, maturity_factor, notes)
            VALUES (:month, :cat, :amount, :factor, :notes)
            ON CONFLICT (period_month, category) DO UPDATE SET
                amount_irr = EXCLUDED.amount_irr,
                maturity_factor = EXCLUDED.maturity_factor,
                notes = EXCLUDED.notes
            """
        ),
        {
            "month": body.period_month,
            "cat": body.category,
            "amount": body.amount_irr,
            "factor": body.maturity_factor,
            "notes": body.notes,
        },
    )
    await db.commit()
    return {"status": "upserted"}


@router.get("/benefits")
async def list_benefits(db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(
        text(
            """
            SELECT period_month, category, amount_irr, maturity_factor, source, notes, created_at
            FROM maturity.benefits_ledger ORDER BY period_month DESC, category
            """
        )
    )
    return [dict(r) for r in result.mappings().all()]


@router.post("/roi/snapshot")
async def roi_snapshot(maturity_pct: float | None = None, db: AsyncSession = Depends(get_db)) -> dict:
    """Track progress toward ~200B IRR annual benefits and ~24 month payback."""
    latest = await db.execute(
        text(
            """
            SELECT DISTINCT ON (category) category, amount_irr, maturity_factor, period_month
            FROM maturity.benefits_ledger
            ORDER BY category, period_month DESC
            """
        )
    )
    rows = list(latest.mappings().all())
    if rows:
        annual_benefits = sum(float(r["amount_irr"]) for r in rows)
        observed_maturity = sum(float(r["maturity_factor"]) for r in rows) / len(rows)
    else:
        factor = maturity_pct if maturity_pct is not None else 0.65
        annual_benefits = ANNUAL_BENEFIT_TARGET * factor
        observed_maturity = factor

    if maturity_pct is not None:
        annual_benefits = ANNUAL_BENEFIT_TARGET * maturity_pct
        observed_maturity = maturity_pct

    net_annual = annual_benefits - ANNUAL_OPEX
    payback_months = (CUMULATIVE_CAPEX / net_annual * 12) if net_annual > 0 else None
    # Simple NPV proxy over 5 years at 25% WACC (proposal)
    wacc = 0.25
    npv = -CUMULATIVE_CAPEX
    for year in range(1, 6):
        # ramp benefits in early years
        year_factor = min(1.0, observed_maturity + 0.1 * (year - 1))
        cash = ANNUAL_BENEFIT_TARGET * year_factor - ANNUAL_OPEX
        npv += cash / ((1 + wacc) ** year)

    details = {
        "by_category": {r["category"]: float(r["amount_irr"]) for r in rows},
        "category_targets": CATEGORY_FULL_YEAR,
        "annual_benefit_target_irr": ANNUAL_BENEFIT_TARGET,
        "wacc": wacc,
    }
    await db.execute(
        text(
            """
            INSERT INTO maturity.roi_snapshots (
                annual_benefits_irr, annual_opex_irr, cumulative_capex_irr,
                net_annual_irr, payback_months, npv_proxy_irr, maturity_pct, details
            ) VALUES (:ben, :opex, :capex, :net, :payback, :npv, :mat, :details::jsonb)
            """
        ),
        {
            "ben": annual_benefits,
            "opex": ANNUAL_OPEX,
            "capex": CUMULATIVE_CAPEX,
            "net": net_annual,
            "payback": payback_months,
            "npv": npv,
            "mat": observed_maturity,
            "details": json.dumps(details),
        },
    )
    await db.commit()
    return {
        "snapshot_date": str(date.today()),
        "annual_benefits_irr": round(annual_benefits, 2),
        "annual_opex_irr": ANNUAL_OPEX,
        "cumulative_capex_irr": CUMULATIVE_CAPEX,
        "net_annual_irr": round(net_annual, 2),
        "payback_months": round(payback_months, 2) if payback_months else None,
        "target_payback_months": FULL_MATURITY_MONTHS,
        "npv_proxy_irr": round(npv, 2),
        "maturity_pct": round(observed_maturity * 100, 2),
        "on_track": bool(payback_months and payback_months <= FULL_MATURITY_MONTHS + 6),
        "details": details,
    }


@router.get("/roi/snapshots")
async def list_roi(limit: int = 20, db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(
        text(
            """
            SELECT snapshot_date, annual_benefits_irr, annual_opex_irr, cumulative_capex_irr,
                   net_annual_irr, payback_months, npv_proxy_irr, maturity_pct, created_at
            FROM maturity.roi_snapshots ORDER BY created_at DESC LIMIT :limit
            """
        ),
        {"limit": limit},
    )
    return [dict(r) for r in result.mappings().all()]


@router.get("/dashboard")
async def maturity_dashboard(db: AsyncSession = Depends(get_db)) -> dict:
    models = await db.execute(
        text("SELECT domain, version, status, trained_at FROM maturity.model_registry WHERE status='production'")
    )
    jobs = await db.execute(
        text("SELECT status, COUNT(*) AS n FROM maturity.retrain_jobs GROUP BY status")
    )
    roi = await db.execute(
        text("SELECT * FROM maturity.roi_snapshots ORDER BY created_at DESC LIMIT 1")
    )
    roi_row = roi.mappings().first()
    inv_actions = await db.execute(
        text(
            """
            SELECT action, COUNT(*) AS n, COALESCE(SUM(expected_saving_irr),0) AS saving
            FROM maturity.inventory_actions
            WHERE created_at > NOW() - INTERVAL '7 days'
            GROUP BY action
            """
        )
    )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "production_models": [dict(r) for r in models.mappings().all()],
        "retrain_job_stats": {r["status"]: int(r["n"]) for r in jobs.mappings().all()},
        "latest_roi": dict(roi_row) if roi_row else None,
        "inventory_actions_7d": [dict(r) for r in inv_actions.mappings().all()],
        "targets": {
            "annual_benefits_irr": ANNUAL_BENEFIT_TARGET,
            "payback_months": FULL_MATURITY_MONTHS,
            "availability_pct": settings.sla_availability_target,
        },
    }


app.include_router(router)
