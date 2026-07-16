"""Auth service — Phase 4 hardened JWT + mandatory 2FA + lockout + password policy."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pyotp
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.app_factory import create_app
from shared.config import get_settings
from shared.db import get_db
from shared.security import (
    create_access_token,
    get_current_user,
    hash_password,
    validate_password_strength,
    verify_password,
)

settings = get_settings()
app = create_app(settings, title="ICB Auth Service", version="4.0.0")
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str
    totp_code: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    requires_2fa: bool = False
    must_change_password: bool = False
    must_setup_2fa: bool = False


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str | None = None
    role: str = "operator"


class Setup2FAResponse(BaseModel):
    secret: str
    otpauth_url: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


async def _security_event(
    db: AsyncSession,
    *,
    username: str | None,
    event_type: str,
    detail: dict | None = None,
    ip: str | None = None,
) -> None:
    await db.execute(
        text(
            """
            INSERT INTO platform.security_events (username, event_type, detail, ip_address)
            VALUES (:username, :etype, :detail::jsonb, :ip)
            """
        ),
        {
            "username": username,
            "etype": event_type,
            "detail": json.dumps(detail or {}),
            "ip": ip,
        },
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    ip = request.client.host if request.client else None
    result = await db.execute(
        text(
            """
            SELECT id, username, password_hash, role, is_active, totp_secret, totp_enabled,
                   failed_login_attempts, locked_until, must_change_password
            FROM platform.users WHERE username = :username
            """
        ),
        {"username": body.username},
    )
    user = result.mappings().first()
    if not user or not user["is_active"]:
        await _security_event(db, username=body.username, event_type="login_failed", detail={"reason": "unknown_user"}, ip=ip)
        await db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if user["locked_until"] and user["locked_until"] > datetime.now(timezone.utc):
        await _security_event(db, username=body.username, event_type="login_locked", ip=ip)
        await db.commit()
        raise HTTPException(status_code=423, detail="Account temporarily locked")

    if not verify_password(body.password, user["password_hash"]):
        attempts = int(user["failed_login_attempts"] or 0) + 1
        locked_until = None
        if attempts >= settings.auth_max_failed_logins:
            locked_until = datetime.now(timezone.utc) + timedelta(minutes=settings.auth_lockout_minutes)
            attempts = 0
        await db.execute(
            text(
                """
                UPDATE platform.users
                SET failed_login_attempts = :attempts, locked_until = :locked, updated_at = NOW()
                WHERE id = :id
                """
            ),
            {"attempts": attempts, "locked": locked_until, "id": user["id"]},
        )
        await _security_event(
            db,
            username=body.username,
            event_type="login_failed",
            detail={"attempts": attempts, "locked": locked_until is not None},
            ip=ip,
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    require_2fa = settings.auth_2fa_required or settings.is_production
    if require_2fa and not user["totp_enabled"]:
        await db.execute(
            text("UPDATE platform.users SET failed_login_attempts = 0, last_login_at = NOW() WHERE id = :id"),
            {"id": user["id"]},
        )
        await _security_event(db, username=body.username, event_type="login_requires_2fa_setup", ip=ip)
        await db.commit()
        return TokenResponse(access_token="", must_setup_2fa=True)

    if (require_2fa or settings.auth_2fa_enabled) and user["totp_enabled"]:
        if not body.totp_code:
            return TokenResponse(access_token="", requires_2fa=True)
        if not user["totp_secret"] or not pyotp.TOTP(user["totp_secret"]).verify(body.totp_code, valid_window=1):
            await _security_event(db, username=body.username, event_type="login_2fa_failed", ip=ip)
            await db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid 2FA code")

    token = create_access_token(
        subject=str(user["id"]),
        claims={"username": user["username"], "role": user["role"]},
        settings=settings,
    )
    await db.execute(
        text(
            """
            UPDATE platform.users
            SET failed_login_attempts = 0, locked_until = NULL, last_login_at = NOW(), updated_at = NOW()
            WHERE id = :id
            """
        ),
        {"id": user["id"]},
    )
    await db.execute(
        text(
            "INSERT INTO platform.audit_log (user_id, action, resource, detail) "
            "VALUES (:uid, 'login', 'auth', :detail::jsonb)"
        ),
        {"uid": user["id"], "detail": json.dumps({"at": datetime.now(timezone.utc).isoformat(), "ip": ip})},
    )
    await _security_event(db, username=body.username, event_type="login_success", ip=ip)
    await db.commit()
    return TokenResponse(
        access_token=token,
        must_change_password=bool(user["must_change_password"]),
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)) -> dict:
    if settings.is_production:
        raise HTTPException(status_code=403, detail="Open registration disabled in production")
    validate_password_strength(body.password, settings)
    await db.execute(
        text(
            "INSERT INTO platform.users (username, email, password_hash, full_name, role, must_change_password) "
            "VALUES (:username, :email, :password_hash, :full_name, :role, FALSE)"
        ),
        {
            "username": body.username,
            "email": body.email,
            "password_hash": hash_password(body.password),
            "full_name": body.full_name,
            "role": body.role,
        },
    )
    await db.commit()
    return {"status": "created", "username": body.username}


@router.post("/password/change")
async def change_password(
    body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
) -> dict:
    validate_password_strength(body.new_password, settings)
    result = await db.execute(
        text("SELECT id, username, password_hash FROM platform.users WHERE id = CAST(:id AS uuid)"),
        {"id": user["sub"]},
    )
    row = result.mappings().first()
    if not row or not verify_password(body.current_password, row["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    await db.execute(
        text(
            """
            UPDATE platform.users
            SET password_hash = :hash, must_change_password = FALSE,
                password_changed_at = NOW(), updated_at = NOW()
            WHERE id = :id
            """
        ),
        {"hash": hash_password(body.new_password), "id": row["id"]},
    )
    await _security_event(db, username=row["username"], event_type="password_changed")
    await db.commit()
    return {"status": "password_changed"}


@router.post("/2fa/setup", response_model=Setup2FAResponse)
async def setup_2fa(username: str, db: AsyncSession = Depends(get_db)) -> Setup2FAResponse:
    secret = pyotp.random_base32()
    await db.execute(
        text("UPDATE platform.users SET totp_secret = :secret, updated_at = NOW() WHERE username = :username"),
        {"secret": secret, "username": username},
    )
    await db.commit()
    url = pyotp.totp.TOTP(secret).provisioning_uri(name=username, issuer_name="IranCarbonBlack")
    return Setup2FAResponse(secret=secret, otpauth_url=url)


@router.post("/2fa/enable")
async def enable_2fa(username: str, totp_code: str, db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(
        text("SELECT totp_secret FROM platform.users WHERE username = :username"),
        {"username": username},
    )
    row = result.mappings().first()
    if not row or not row["totp_secret"]:
        raise HTTPException(status_code=400, detail="2FA not set up")
    if not pyotp.TOTP(row["totp_secret"]).verify(totp_code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    await db.execute(
        text("UPDATE platform.users SET totp_enabled = TRUE, updated_at = NOW() WHERE username = :username"),
        {"username": username},
    )
    await _security_event(db, username=username, event_type="2fa_enabled")
    await db.commit()
    return {"status": "2fa_enabled"}


@router.get("/security/events")
async def security_events(limit: int = 50, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)) -> list[dict]:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    result = await db.execute(
        text(
            """
            SELECT id, username, event_type, detail, ip_address, created_at
            FROM platform.security_events ORDER BY created_at DESC LIMIT :limit
            """
        ),
        {"limit": limit},
    )
    return [dict(r) for r in result.mappings().all()]


@router.get("/me")
async def me(user=Depends(get_current_user)) -> dict:
    return user


app.include_router(router)
