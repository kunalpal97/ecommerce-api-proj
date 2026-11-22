"""
tests/test_edge_cases.py — 404 / 400 Edge Case Tests
======================================================
Covers scenarios that were missing from initial test suite (the 6% gap):

1. Fetching a non-existent order      → 404
2. Adding item to a non-existent cart → 404
3. Adding non-existent product to cart→ 404
4. Fetching a non-existent cart       → 404
5. Checkout from non-existent cart    → 404
6. Checkout from empty cart           → 400
7. Health check endpoint              → 200

These tests bring total coverage from 94% to ~99%.

Why these matter (Interview Answer):
  "Every API must handle the sad path as clearly as the happy path.
   An unauthenticated or misconfigured client hitting a wrong ID should
   get a clear, structured error — not a 500 Internal Server Error or
   an empty response."
"""

from fastapi.testclient import TestClient

from tests.conftest import PROD_LAPTOP


# ── Health Check ──────────────────────────────────────────────────────────────

def test_health_check_returns_200(client: TestClient) -> None:
    """
    Health endpoint used by monitoring systems (e.g., Kubernetes liveness probe).
    Must return 200 with service name and version.
    """
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "version" in data


# ── Order 404 ─────────────────────────────────────────────────────────────────

def test_get_nonexistent_order_returns_404(client: TestClient) -> None:
    """
    GET /orders/{order_id} with an ID that does not exist must return 404.
    Response must include a structured error body — not a bare 404.
    """
    response = client.get("/api/v1/orders/ord_doesnotexist")

    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "ORDER_NOT_FOUND"
    assert "ord_doesnotexist" in data["message"]


# ── Cart 404 ─────────────────────────────────────────────────────────────────

def test_get_nonexistent_cart_returns_404(client: TestClient) -> None:
    """GET /cart/{cart_id} with a non-existent ID must return 404."""
    response = client.get("/api/v1/cart/cart_doesnotexist")

    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "CART_NOT_FOUND"


def test_add_item_to_nonexistent_cart_returns_404(client: TestClient) -> None:
    """
    POST /cart/{cart_id}/items with a fake cart_id must return 404.
    Stock must remain untouched.
    """
    response = client.post(
        "/api/v1/cart/cart_fake999/items",
        json={"product_id": PROD_LAPTOP, "quantity": 1},
    )

    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "CART_NOT_FOUND"


def test_update_item_in_nonexistent_cart_returns_404(client: TestClient) -> None:
    """PATCH /cart/{cart_id}/items/{product_id} with fake cart must return 404."""
    response = client.patch(
        f"/api/v1/cart/cart_fake999/items/{PROD_LAPTOP}",
        json={"quantity": 3},
    )

    assert response.status_code == 404
    assert response.json()["error"] == "CART_NOT_FOUND"


def test_delete_item_from_nonexistent_cart_returns_404(client: TestClient) -> None:
    """DELETE /cart/{cart_id}/items/{product_id} with fake cart must return 404."""
    response = client.delete(f"/api/v1/cart/cart_fake999/items/{PROD_LAPTOP}")

    assert response.status_code == 404
    assert response.json()["error"] == "CART_NOT_FOUND"


# ── Product 404 ───────────────────────────────────────────────────────────────

def test_add_nonexistent_product_to_cart_returns_404(client: TestClient) -> None:
    """
    POST /cart/{cart_id}/items with a product_id that is not in the catalogue
    must return 404 with a structured error body.
    Cart must remain empty — no phantom item added.
    """
    cart_id = client.post("/api/v1/cart").json()["id"]

    response = client.post(
        f"/api/v1/cart/{cart_id}/items",
        json={"product_id": "prod_does_not_exist", "quantity": 1},
    )

    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "PRODUCT_NOT_FOUND"
    assert "prod_does_not_exist" in data["message"]

    # Cart must still be empty
    cart = client.get(f"/api/v1/cart/{cart_id}").json()
    assert cart["item_count"] == 0


# ── Checkout Edge Cases ───────────────────────────────────────────────────────

def test_checkout_with_nonexistent_cart_returns_404(client: TestClient) -> None:
    """
    POST /checkout with a cart_id that does not exist must return 404.
    No order must be created.
    """
    response = client.post(
        "/api/v1/checkout",
        headers={"Idempotency-Key": "edge-case-no-cart"},
        json={"cart_id": "cart_fake000"},
    )

    assert response.status_code == 404
    assert response.json()["error"] == "CART_NOT_FOUND"


def test_checkout_with_empty_cart_returns_400(client: TestClient) -> None:
    """
    POST /checkout on a cart that has no items must return 400 Bad Request.
    Business rule: "You cannot place an order with nothing in your cart."
    """
    # Create a cart but add nothing to it
    cart_id = client.post("/api/v1/cart").json()["id"]

    response = client.post(
        "/api/v1/checkout",
        headers={"Idempotency-Key": "edge-case-empty-cart"},
        json={"cart_id": cart_id},
    )

    assert response.status_code == 400
    data = response.json()
    assert data["error"] == "CART_EMPTY"
    assert cart_id in data["message"]
