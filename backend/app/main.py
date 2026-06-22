"""
TradeSense — FastAPI Application Entry Point
Configures the application instance, middleware, routers, and lifecycle events.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import check_db_connection

# ── Router Imports (will be activated as they are built in subsequent days) ────
from app.api.v1.endpoints import auth, portfolios, uploads, analytics


# ── Lifespan ───────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler.
    Startup: verify database connection, initialise caches.
    Shutdown: release resources cleanly.
    """
    # Startup
    db_ok = await check_db_connection()
    if not db_ok:
        raise RuntimeError(
            "Cannot connect to PostgreSQL. "
            "Check DATABASE_URL and ensure the database container is running."
        )
    print(f"✅  TradeSense API started | env={settings.environment}")

    yield  # Application runs here

    # Shutdown
    print("🛑  TradeSense API shutting down")


# ── Application Factory ─────────────────────────────────────────────────────────
def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Behavioral analytics platform for retail investors. "
            "Turn trading history into behavioral intelligence."
        ),
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
        lifespan=lifespan,
    )

    # ── CORS ───────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
    )

    # ── Routers ────────────────────────────────────────────────────────────────
    # Uncomment each router as you build it during the 4-week sprint:
    app.include_router(auth.router,            prefix="/v1")
    app.include_router(portfolios.router,      prefix="/v1")
    app.include_router(uploads.router,         prefix="/v1")
    app.include_router(analytics.router,       prefix="/v1")

    # ── Health & Root ──────────────────────────────────────────────────────────
    @app.get("/health", tags=["System"], summary="System health check")
    async def health_check():
        """
        Returns API status and database connectivity.
        Used by Docker HEALTHCHECK and load balancer probes.
        """
        db_status = await check_db_connection()
        payload = {
            "status": "ok" if db_status else "degraded",
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "database": "connected" if db_status else "unreachable",
        }
        status_code = 200 if db_status else 503
        return JSONResponse(content=payload, status_code=status_code)

    @app.get("/", tags=["System"], include_in_schema=False)
    async def root():
        return {"message": "TradeSense API", "docs": "/docs"}

    return app


# ── Instantiate App ─────────────────────────────────────────────────────────────
app = create_app()
