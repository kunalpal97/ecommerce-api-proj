"""
tests/conftest.py — Shared Test Fixtures
==========================================
Fixtures defined here are automatically available to ALL test files
in the tests/ directory — no import needed.

Key fixture: `client`
  - Creates a fresh FastAPI TestClient for every single test.
  - Resets + re-seeds the database before each test.
  - This guarantees complete test isolation:
      "No test can see side-effects from another test."

Why TestClient (not a real server)?
  - Runs the full FastAPI app in-process — same middleware, same handlers.
  - No network I/O — tests are fast and reliable.
  - No port management needed.

Why reset + reseed per test?
  - Tests that modify stock/orders would pollute later tests.
  - Each test starts from the EXACT same known state:
      prod_laptop:      stock 10
      prod_headphones:  stock 5
      prod_usb_hub:     stock 1
      prod_webcam:      stock 0
"""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.store.database import reset_database
from app.store.seed import seed_database


@pytest.fixture
def client() -> TestClient:
    """
    Provide a fresh HTTP test client with a clean database for each test.

    Usage in tests:
        def test_something(client):
            response = client.get("/api/v1/products")
            assert response.status_code == 200
    """
    # 1. Reset all in-memory data (products, carts, orders, idempotency keys)
    reset_database()

    # 2. Reload the product catalogue from seed data
    seed_database()

    # 3. Create the app + test client
    #    TestClient handles the lifespan context automatically.
    app = create_app()

    with TestClient(app, raise_server_exceptions=True) as test_client:
        yield test_client

    # Cleanup after the test (belt-and-suspenders)
    reset_database()


# ── Reusable product ID constants ─────────────────────────────────────────
# Use these in tests instead of hardcoding strings — typos cause false fails.

PROD_LAPTOP = "prod_laptop"           # stock: 10
PROD_HEADPHONES = "prod_headphones"   # stock: 5
PROD_USB_HUB = "prod_usb_hub"         # stock: 1
PROD_WEBCAM = "prod_webcam"           # stock: 0  (always fails)
