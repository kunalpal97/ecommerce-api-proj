"""
main.py — FastAPI Application Factory
========================================
Creates and configures the FastAPI application instance.

Responsibilities:
  1. Define app metadata (name, version, docs URLs).
  2. Register startup/shutdown lifecycle via lifespan context manager.
  3. Mount all route handlers under the /api/v1 prefix.
  4. Register global exception handlers (map custom exceptions → HTTP codes).

Why lifespan (not @app.on_event)?
  @app.on_event("startup") is deprecated since FastAPI 0.93.
  The lifespan context manager is the modern, recommended approach.
  It also makes teardown (yield → cleanup) cleaner.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.store.database import reset_database
from app.store.seed import seed_database


# ── Lifespan: startup + shutdown ──────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifecycle manager.

    Everything before `yield` runs on startup.
    Everything after `yield` runs on shutdown.
    """
    # ── Startup ───────────────────────────────────────────────────────────
    reset_database()     # start clean (important when server restarts in dev)
    seed_database()      # load product catalogue into memory
    print(f"✅ {settings.APP_NAME} v{settings.APP_VERSION} started — catalogue seeded.")

    yield  # ← app is running and serving requests here

    # ── Shutdown ──────────────────────────────────────────────────────────
    print(f"🛑 {settings.APP_NAME} shutting down.")


# ── App factory ───────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    """
    Build and return the configured FastAPI application.

    Using a factory function (instead of a module-level `app = FastAPI()`)
    makes the app easier to test — tests can call create_app() and get a
    fresh instance with clean state.
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=settings.APP_DESCRIPTION,
        contact=settings.CONTACT,
        license_info=settings.LICENSE_INFO,
        docs_url="/docs",          # Swagger UI at /docs
        redoc_url="/redoc",        # ReDoc UI at /redoc
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────
    # Allow all origins in development. In production, restrict to your
    # frontend domain(s) only.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Register exception handlers ───────────────────────────────────────
    # Imported here (after app creation) to avoid circular imports.
    from app.exceptions.handlers import register_exception_handlers
    register_exception_handlers(app)

    # ── Register route handlers ───────────────────────────────────────────
    from app.routes.products import router as products_router
    from app.routes.cart import router as cart_router
    from app.routes.checkout import router as checkout_router
    from app.routes.orders import router as orders_router

    app.include_router(products_router, prefix=settings.API_PREFIX)
    app.include_router(cart_router, prefix=settings.API_PREFIX)
    app.include_router(checkout_router, prefix=settings.API_PREFIX)
    app.include_router(orders_router, prefix=settings.API_PREFIX)

    # ── Health check ─────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"], summary="Health check")
    async def health_check() -> dict:
        """Returns 200 OK if the service is up. Used by monitoring tools."""
        return {
            "status": "healthy",
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
        }

    return app


# ── Module-level app instance (used by uvicorn) ───────────────────────────
# uvicorn runs: uvicorn app.main:app
# This calls create_app() once at import time.
app = create_app()
