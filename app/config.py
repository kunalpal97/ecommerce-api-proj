"""
config.py — Application Configuration
======================================
Single source of truth for all app-level settings and constants.

Design decisions:
- Pure Python class (no extra dependencies like pydantic-settings)
- Class attributes = immutable constants (no instantiation needed)
- If this grows to need .env support, swap to pydantic-settings without
  changing any other file — just this one.
"""


class AppConfig:
    """Central configuration for the Commerce API."""

    # ── Application Identity ──────────────────────────────────────────────
    APP_NAME: str = "Commerce API"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = (
        "A minimal commerce API with atomic checkout and idempotency support. "
        "Built for the Fynd SDET-1 hiring challenge."
    )

    # ── API Routing ───────────────────────────────────────────────────────
    API_PREFIX: str = "/api/v1"

    # ── Idempotency ───────────────────────────────────────────────────────
    # Header name clients must send with checkout requests
    IDEMPOTENCY_HEADER: str = "Idempotency-Key"

    # ── Validation Rules ──────────────────────────────────────────────────
    # Quantities must be positive whole numbers: 1, 2, 3 …
    MIN_QUANTITY: int = 1

    # ── Contact / Docs ────────────────────────────────────────────────────
    CONTACT: dict = {
        "name": "Commerce API Support",
        "email": "support@commerce-api.local",
    }
    LICENSE_INFO: dict = {
        "name": "MIT",
    }


# Export a single shared instance
settings = AppConfig()
