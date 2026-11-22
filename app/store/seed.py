"""
store/seed.py — Catalogue Seed Data
======================================
Populates the in-memory database with an initial product catalogue.

Rules from the challenge:
  - At least 2 products required.

Design:
  - Each product has a unique string ID (UUID-style prefix for readability).
  - Stock values are chosen to enable specific test scenarios:
      * "laptop"    → stock 10 (enough for multi-item + stock limit tests)
      * "headphones"→ stock 5  (used in partial-failure test: order 6, fail)
      * "usb_hub"   → stock 1  (used in exact-limit test: order 1, succeed)
      * "webcam"    → stock 0  (used in zero-stock test: always fails)

  Having 4 products makes every test scenario expressible without
  tests interfering with each other's stock.
"""

from app.store.database import get_products_db


# ── Catalogue definition ──────────────────────────────────────────────────

SEED_PRODUCTS = [
    {
        "id": "prod_laptop",
        "name": "Laptop Pro 15",
        "description": "High-performance laptop with 16GB RAM and 512GB SSD.",
        "price": 89999.00,   # price in paise/cents (₹ 89,999)
        "stock": 10,
    },
    {
        "id": "prod_headphones",
        "name": "Wireless Headphones",
        "description": "Noise-cancelling over-ear headphones with 30hr battery.",
        "price": 4999.00,
        "stock": 5,
    },
    {
        "id": "prod_usb_hub",
        "name": "USB-C Hub 7-in-1",
        "description": "7-port USB-C hub with HDMI, USB 3.0, and SD card reader.",
        "price": 2499.00,
        "stock": 1,
    },
    {
        "id": "prod_webcam",
        "name": "4K Webcam",
        "description": "4K USB webcam with built-in ring light and microphone.",
        "price": 5999.00,
        "stock": 0,          # intentionally 0 — used to test zero-stock rejection
    },
]


def seed_database() -> None:
    """
    Load the seed catalogue into the in-memory products store.

    Called once at application startup (via FastAPI lifespan).
    Also called by test fixtures after reset_database() to restore known state.
    """
    products_db = get_products_db()

    for product in SEED_PRODUCTS:
        products_db[product["id"]] = {
            "id": product["id"],
            "name": product["name"],
            "description": product["description"],
            "price": product["price"],
            "stock": product["stock"],
        }
