"""
store/database.py — In-Memory Data Store
=========================================
Acts as our database. Uses plain Python dicts (fast, no I/O).

Structure:
    _products      → { product_id: { id, name, price, stock } }
    _carts         → { cart_id:    { id, items: { product_id: quantity } } }
    _orders        → { order_id:   { id, cart_id, items, total, created_at } }
    _idempotency   → { key:        { payload_hash, order_id } }

Thread safety:
    One Lock guards all checkout operations — prevents two concurrent
    checkouts from both reading stock=5 and both deducting from it.
    Read-only routes (GET /products, GET /orders) don't need the lock.

Repository pattern:
    Nothing outside this module touches _products/_carts/_orders directly.
    All reads/writes go through the repositories/ layer.
    This means swapping to PostgreSQL = rewrite repositories only.
"""

import threading
from typing import Any

# ── Raw data stores (treat as private — use repositories to access) ───────

_products: dict[str, dict[str, Any]] = {}
_carts: dict[str, dict[str, Any]] = {}
_orders: dict[str, dict[str, Any]] = {}
_idempotency: dict[str, dict[str, Any]] = {}

# ── Single lock for all write operations ─────────────────────────────────
# Using one lock keeps deadlock risk zero.
# Granular per-product locks would be faster at scale but overkill here.
_checkout_lock = threading.Lock()


# ── Public accessors (used by repositories only) ──────────────────────────

def get_products_db() -> dict[str, dict[str, Any]]:
    """Return the live products dict."""
    return _products


def get_carts_db() -> dict[str, dict[str, Any]]:
    """Return the live carts dict."""
    return _carts


def get_orders_db() -> dict[str, dict[str, Any]]:
    """Return the live orders dict."""
    return _orders


def get_idempotency_db() -> dict[str, dict[str, Any]]:
    """Return the live idempotency store."""
    return _idempotency


def get_checkout_lock() -> threading.Lock:
    """Return the checkout lock. Always use as a context manager: with get_checkout_lock()."""
    return _checkout_lock


# ── Reset helper (used by tests to restore a known state) ─────────────────

def reset_database() -> None:
    """
    Clear all data stores.

    Called by test fixtures before each test to guarantee isolation.
    Never call this in production code.
    """
    _products.clear()
    _carts.clear()
    _orders.clear()
    _idempotency.clear()
