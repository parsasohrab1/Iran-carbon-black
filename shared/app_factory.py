"""App factory with Phase-4 security headers, rate limit, production docs toggle."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from shared.config import Settings
from shared.logging import setup_logging

REQUEST_COUNT = Counter(
    "icb_http_requests_total",
    "Total HTTP requests",
    ["service", "method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "icb_http_request_duration_seconds",
    "HTTP request latency",
    ["service", "endpoint"],
)
RATE_LIMITED = Counter(
    "icb_http_rate_limited_total",
    "Rate-limited requests",
    ["service"],
)


class MetricsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, service_name: str):
        super().__init__(app)
        self.service_name = service_name

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in {"/metrics", "/health", "/ready"}:
            return await call_next(request)
        with REQUEST_LATENCY.labels(self.service_name, path).time():
            response = await call_next(request)
        REQUEST_COUNT.labels(self.service_name, request.method, path, response.status_code).inc()
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Cache-Control"] = "no-store"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, service_name: str, limit_per_minute: int = 120):
        super().__init__(app)
        self.service_name = service_name
        self.limit = limit_per_minute
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if request.url.path in {"/metrics", "/health", "/ready"}:
            return await call_next(request)
        client = request.client.host if request.client else "unknown"
        now = time.time()
        window = self._hits[client]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= self.limit:
            RATE_LIMITED.labels(self.service_name).inc()
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
        window.append(now)
        return await call_next(request)


def create_app(settings: Settings, title: str, version: str = "0.1.0", lifespan=None) -> FastAPI:
    setup_logging(settings.service_name, settings.log_level)
    docs_url = None if settings.is_production else "/docs"
    redoc_url = None if settings.is_production else "/redoc"
    app = FastAPI(title=title, version=version, docs_url=docs_url, redoc_url=redoc_url, lifespan=lifespan)
    app.add_middleware(MetricsMiddleware, service_name=settings.service_name)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        service_name=settings.service_name,
        limit_per_minute=settings.rate_limit_per_minute,
    )

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "service": settings.service_name, "zone": settings.network_zone}

    @app.get("/ready")
    async def ready() -> dict:
        return {
            "status": "ready",
            "service": settings.service_name,
            "environment": settings.environment,
            "zone": settings.network_zone,
        }

    @app.get("/metrics")
    async def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app
