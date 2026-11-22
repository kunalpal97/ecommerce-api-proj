"""
tests/test_idempotency.py — Idempotency & Retry Scenario Tests
================================================================
Covers Problem 2 in challenge description:
"A retry after a timeout might create a duplicate order."
Requirements:
1. Reusing the SAME idempotency key with the SAME payload must return
   the original order and NOT deduct stock again or create another order.
2. Reusing the SAME key with a DIFFERENT payload must be rejected (409 Conflict)
   without changing stock or creating another order.
3. Assert both order count and stock after each request.
"""

from fastapi.testclient import TestClient

from app.repositories.order_repo import order_repo
from app.repositories.product_repo import product_repo
from tests.conftest import PROD_LAPTOP


def test_idempotent_retry_same_payload_returns_original_order(
    client: TestClient,
) -> None:
    """
    Scenario: Client sends checkout, network times out, client retries.
    - Request 1: Succeeds, creates order_1, deducts 2 laptops (stock 10 -> 8).
    - Request 2: Replays same key and payload.
      * Must return order_1.
      * Must NOT deduct 2 more laptops (stock remains 8).
      * Must NOT create order_2 (total orders in DB remains 1).
    """
    idempotency_key = "retry-token-uuid-12345"

    # Setup cart
    cart_id = client.post("/api/v1/cart").json()["id"]
    client.post(
        f"/api/v1/cart/{cart_id}/items",
        json={"product_id": PROD_LAPTOP, "quantity": 2},
    )

    # First attempt
    res_1 = client.post(
        "/api/v1/checkout",
        headers={"Idempotency-Key": idempotency_key},
        json={"cart_id": cart_id},
    )
    assert res_1.status_code == 200
    order_1 = res_1.json()["order"]
    order_1_id = order_1["id"]

    # Verify state after attempt 1
    assert product_repo.get_stock(PROD_LAPTOP) == 8
    assert order_repo.count() == 1

    # Second attempt (Retry after timeout)
    res_2 = client.post(
        "/api/v1/checkout",
        headers={"Idempotency-Key": idempotency_key},
        json={"cart_id": cart_id},
    )
    assert res_2.status_code == 200
    data_2 = res_2.json()
    assert "already exists" in data_2["message"].lower()

    # Verify same order is returned
    assert data_2["order"]["id"] == order_1_id

    # VERIFY STATE: Stock must NOT have been deducted a second time
    assert (
        product_repo.get_stock(PROD_LAPTOP) == 8
    ), "Duplicate deduction occurred on retry!"

    # VERIFY STATE: Database must contain strictly 1 order
    assert order_repo.count() == 1, "Duplicate order created on retry!"


def test_idempotent_retry_different_payload_is_rejected(client: TestClient) -> None:
    """
    Scenario: Client tries to reuse an existing idempotency key with different data.
    - Request 1: Key 'fraud-key' used for Cart A (1 Laptop).
    - Request 2: Same key 'fraud-key' used for Cart B (2 Laptops).
      * Must be rejected with 409 Conflict.
      * Stock of Cart B must NOT be deducted.
      * No new order created.
    """
    idempotency_key = "fraud-key-abc"

    # Cart A
    cart_a = client.post("/api/v1/cart").json()["id"]
    client.post(
        f"/api/v1/cart/{cart_a}/items",
        json={"product_id": PROD_LAPTOP, "quantity": 1},
    )

    # Cart B
    cart_b = client.post("/api/v1/cart").json()["id"]
    client.post(
        f"/api/v1/cart/{cart_b}/items",
        json={"product_id": PROD_LAPTOP, "quantity": 2},
    )

    # 1. Checkout Cart A with the key
    res_a = client.post(
        "/api/v1/checkout",
        headers={"Idempotency-Key": idempotency_key},
        json={"cart_id": cart_a},
    )
    assert res_a.status_code == 200
    assert product_repo.get_stock(PROD_LAPTOP) == 9  # 10 - 1
    assert order_repo.count() == 1

    # 2. Checkout Cart B with the SAME key but DIFFERENT payload (different cart_id)
    res_b = client.post(
        "/api/v1/checkout",
        headers={"Idempotency-Key": idempotency_key},
        json={"cart_id": cart_b},
    )

    assert res_b.status_code == 409
    assert res_b.json()["error"] == "IDEMPOTENCY_CONFLICT"

    # VERIFY STATE: Cart B items NOT deducted (stock remains 9, not 7)
    assert product_repo.get_stock(PROD_LAPTOP) == 9

    # VERIFY STATE: Still only 1 order in the system
    assert order_repo.count() == 1


def test_checkout_missing_idempotency_key_header_rejected(client: TestClient) -> None:
    """Checkout without an Idempotency-Key header must return 400 Bad Request."""
    cart_id = client.post("/api/v1/cart").json()["id"]
    client.post(
        f"/api/v1/cart/{cart_id}/items",
        json={"product_id": PROD_LAPTOP, "quantity": 1},
    )

    # Call checkout with NO Idempotency-Key header
    res = client.post(
        "/api/v1/checkout",
        json={"cart_id": cart_id},
    )

    assert res.status_code == 400
    assert res.json()["error"] == "MISSING_IDEMPOTENCY_KEY"
    assert product_repo.get_stock(PROD_LAPTOP) == 10
    assert order_repo.count() == 0
