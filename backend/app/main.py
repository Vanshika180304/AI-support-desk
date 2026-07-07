from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import RequestIDMiddleware, configure_logging, get_logger

settings = get_settings()

# Configure logging before anything else
configure_logging(env=settings.app_env)
log = get_logger(__name__)

# Wire LangSmith tracing if configured
if settings.langchain_tracing_v2 and settings.langchain_api_key:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
    log.info("LangSmith tracing enabled", project=settings.langchain_project)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup / shutdown lifecycle."""
    log.info(
        "Starting AI Support Desk API",
        env=settings.app_env,
        model=settings.openai_chat_model,
    )
    # DB tables are created via Alembic migrations, not here.
    # Import and initialise the async engine so the pool is ready.
    from app.db.session import engine  # noqa: F401 — triggers engine creation

    yield

    log.info("Shutting down AI Support Desk API")
    from app.db.session import engine

    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Support Desk",
        description=(
            "Multi-agent triage system: tickets are classified, routed to a "
            "specialist AI agent, answered via RAG, and escalated when confidence is low."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── Middleware ─────────────────────────────────────────────────────────────
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.app_env == "development" else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    from app.api.routes.auth import router as auth_router
    from app.api.routes.tickets import router as tickets_router
    from app.api.routes.kb import router as kb_router

    app.include_router(auth_router, prefix="/auth", tags=["Auth"])
    app.include_router(tickets_router, prefix="/tickets", tags=["Tickets"])
    app.include_router(kb_router, prefix="/kb", tags=["Knowledge Base"])

    # ── Health endpoints ───────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"], summary="Liveness check")
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok", "env": settings.app_env})

    @app.get("/ready", tags=["Health"], summary="Readiness check")
    async def ready() -> JSONResponse:
        """Check DB + Redis connectivity."""
        checks: dict[str, str] = {}

        # DB
        try:
            from app.db.session import engine
            async with engine.connect() as conn:
                await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
            checks["db"] = "ok"
        except Exception as exc:  # noqa: BLE001
            checks["db"] = f"error: {exc}"

        # Redis
        try:
            import redis.asyncio as aioredis
            r = aioredis.from_url(settings.redis_url, socket_connect_timeout=2)
            await r.ping()
            await r.aclose()
            checks["redis"] = "ok"
        except Exception as exc:  # noqa: BLE001
            checks["redis"] = f"error: {exc}"

        all_ok = all(v == "ok" for v in checks.values())
        return JSONResponse(
            {"status": "ok" if all_ok else "degraded", "checks": checks},
            status_code=200 if all_ok else 503,
        )

    return app


app = create_app()
