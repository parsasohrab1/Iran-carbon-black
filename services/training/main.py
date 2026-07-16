"""Training & organizational change management (Phase 4 / IN-03 / IN-04)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.app_factory import create_app
from shared.config import get_settings
from shared.db import get_db

settings = get_settings()
app = create_app(settings, title="ICB Training & Change Service", version="4.0.0")
router = APIRouter(prefix="/api/v1/training", tags=["training"])


class EnrollRequest(BaseModel):
    course_id: str
    username: str


class ProgressRequest(BaseModel):
    progress_pct: float = Field(ge=0, le=100)


class ChangeRequestCreate(BaseModel):
    title: str
    description: str | None = None
    domain: str | None = None
    impact_level: str = "medium"
    created_by: str = "admin"


class SurveyCreate(BaseModel):
    change_request_id: int
    username: str
    acceptance_score: int = Field(ge=1, le=5)
    feedback: str | None = None


@router.get("/courses")
async def list_courses(db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(
        text(
            """
            SELECT id, title, description, domain, duration_minutes, target_roles,
                   is_mandatory, content_url, created_at
            FROM training.courses ORDER BY is_mandatory DESC, title
            """
        )
    )
    return [dict(r) for r in result.mappings().all()]


@router.post("/enroll")
async def enroll(body: EnrollRequest, db: AsyncSession = Depends(get_db)) -> dict:
    course = await db.execute(text("SELECT id FROM training.courses WHERE id = :id"), {"id": body.course_id})
    if not course.first():
        raise HTTPException(status_code=404, detail="Course not found")
    await db.execute(
        text(
            """
            INSERT INTO training.enrollments (course_id, username, status, progress_pct)
            VALUES (:cid, :username, 'enrolled', 0)
            ON CONFLICT (course_id, username) DO NOTHING
            """
        ),
        {"cid": body.course_id, "username": body.username},
    )
    await db.commit()
    return {"status": "enrolled", "course_id": body.course_id, "username": body.username}


@router.post("/enrollments/{enrollment_id}/progress")
async def update_progress(enrollment_id: int, body: ProgressRequest, db: AsyncSession = Depends(get_db)) -> dict:
    status = "completed" if body.progress_pct >= 100 else "in_progress"
    completed_at = datetime.now(timezone.utc) if status == "completed" else None
    result = await db.execute(
        text(
            """
            UPDATE training.enrollments
            SET progress_pct = :pct, status = :status, completed_at = COALESCE(:completed, completed_at)
            WHERE id = :id
            RETURNING id, course_id, username, status, progress_pct, completed_at
            """
        ),
        {"pct": body.progress_pct, "status": status, "completed": completed_at, "id": enrollment_id},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    await db.commit()
    return dict(row)


@router.get("/enrollments")
async def list_enrollments(username: str | None = None, limit: int = 100, db: AsyncSession = Depends(get_db)) -> list[dict]:
    if username:
        result = await db.execute(
            text(
                """
                SELECT e.id, e.course_id, c.title, e.username, e.status, e.progress_pct, e.enrolled_at, e.completed_at
                FROM training.enrollments e
                JOIN training.courses c ON c.id = e.course_id
                WHERE e.username = :username
                ORDER BY e.enrolled_at DESC LIMIT :limit
                """
            ),
            {"username": username, "limit": limit},
        )
    else:
        result = await db.execute(
            text(
                """
                SELECT e.id, e.course_id, c.title, e.username, e.status, e.progress_pct, e.enrolled_at, e.completed_at
                FROM training.enrollments e
                JOIN training.courses c ON c.id = e.course_id
                ORDER BY e.enrolled_at DESC LIMIT :limit
                """
            ),
            {"limit": limit},
        )
    return [dict(r) for r in result.mappings().all()]


@router.get("/compliance")
async def training_compliance(db: AsyncSession = Depends(get_db)) -> dict:
    """Rollout readiness for 350+ staff — mandatory course completion rate."""
    totals = await db.execute(
        text(
            """
            SELECT
                (SELECT COUNT(*) FROM training.courses WHERE is_mandatory) AS mandatory_courses,
                (SELECT COUNT(*) FROM training.enrollments e
                   JOIN training.courses c ON c.id = e.course_id
                  WHERE c.is_mandatory AND e.status = 'completed') AS mandatory_completions,
                (SELECT COUNT(DISTINCT username) FROM training.enrollments) AS learners,
                (SELECT COUNT(*) FROM training.enrollments) AS total_enrollments
            """
        )
    )
    row = dict(totals.mappings().first() or {})
    target_headcount = 350
    learners = int(row.get("learners") or 0)
    return {
        **row,
        "target_headcount": target_headcount,
        "coverage_pct": round(100.0 * learners / target_headcount, 2),
        "note": "coverage_pct is share of 350 target staff enrolled at least once",
    }


@router.get("/changes")
async def list_changes(db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(
        text(
            """
            SELECT id, title, description, domain, status, impact_level, created_by, created_at, decided_at
            FROM training.change_requests ORDER BY created_at DESC
            """
        )
    )
    return [dict(r) for r in result.mappings().all()]


@router.post("/changes")
async def create_change(body: ChangeRequestCreate, db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(
        text(
            """
            INSERT INTO training.change_requests (title, description, domain, impact_level, created_by)
            VALUES (:title, :description, :domain, :impact, :created_by)
            RETURNING id
            """
        ),
        {
            "title": body.title,
            "description": body.description,
            "domain": body.domain,
            "impact": body.impact_level,
            "created_by": body.created_by,
        },
    )
    new_id = result.scalar_one()
    await db.commit()
    return {"status": "created", "id": new_id}


@router.post("/changes/{change_id}/decide")
async def decide_change(change_id: int, status: str = "accepted", db: AsyncSession = Depends(get_db)) -> dict:
    if status not in {"accepted", "rejected", "deployed"}:
        raise HTTPException(status_code=400, detail="Invalid status")
    result = await db.execute(
        text(
            """
            UPDATE training.change_requests
            SET status = :status, decided_at = NOW()
            WHERE id = :id
            RETURNING id
            """
        ),
        {"status": status, "id": change_id},
    )
    if not result.first():
        raise HTTPException(status_code=404, detail="Change request not found")
    await db.commit()
    return {"status": status, "id": change_id}


@router.post("/surveys")
async def submit_survey(body: SurveyCreate, db: AsyncSession = Depends(get_db)) -> dict:
    await db.execute(
        text(
            """
            INSERT INTO training.acceptance_surveys
                (change_request_id, username, acceptance_score, feedback)
            VALUES (:cid, :username, :score, :feedback)
            """
        ),
        {
            "cid": body.change_request_id,
            "username": body.username,
            "score": body.acceptance_score,
            "feedback": body.feedback,
        },
    )
    await db.commit()
    return {"status": "recorded"}


@router.get("/surveys/summary")
async def survey_summary(db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(
        text(
            """
            SELECT change_request_id,
                   COUNT(*) AS responses,
                   ROUND(AVG(acceptance_score)::numeric, 2) AS avg_score
            FROM training.acceptance_surveys
            GROUP BY change_request_id
            ORDER BY change_request_id
            """
        )
    )
    return {"by_change": [dict(r) for r in result.mappings().all()]}


app.include_router(router)
