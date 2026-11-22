"""
tests/test_checkout.py — Core Checkout & Atomic Transaction Tests
===================================================================
Covers the critical release-readiness requirements:
1. Successful multi-item checkout (order created, stock deducted once).
2. Checkout at exact stock limit (stock reaches 0, order created).
3. Checkout above available stock (rejected, stock unchanged, no order).
4. CRITICAL: Multi-item checkout where only ONE item is short on stock:
   - Prove BOTH products' stock remains completely untouched.
   - Prove no order was created in the database.
   - Asserting HTTP response alone is NOT enough — state is strictly checked.
"""

from fastapi.testclient import TestClient

from app.repositories.order_repo import order_repo
from app.repositories.product_repo import product_repo
from tests.conftest import PROD_HEADPHONES, PROD_LAPTOP, PROD_USB_HUB, PROD_WEBCAM


def test_successful_multi_item_checkout(client: TestClient) -> None:
    """
    Test standard successful multi-item checkout:
    - 2 Laptops (10 -> 8)
    - 1 Headphone (5 -> 4)
    - Order is confirmed and persisted.
    """
    # Baseline checks
    assert product_repo.get_stock(PROD_LAPTOP) == 10
    assert product_repo.get_stock(PROD_HEADPHONES) == 5
    initial_order_count = order_repo.count()

    # 1. Create cart and add items
    cart_id = client.post("/api/v1/cart").json()["id"]
    client.post(
        f"/api/v1/cart/{cart_id}/items",
        json={"product_id": PROD_LAPTOP, "quantity": 2},
    )
    client.post(
        f"/api/v1/cart/{cart_id}/items",
        json={"product_id": PROD_HEADPHONES, "quantity": 1},
    )

    # 2. Checkout
    checkout_res = client.post(
        "/api/v1/checkout",
        headers={"Idempotency-Key": "test-multi-item-key-1"},
        json={"cart_id": cart_id},
    )

    assert checkout_res.status_code == 200
    data = checkout_res.json()
    order_id = data["order"]["id"]
    assert data["order"]["status"] == "confirmed"
    assert data["order"]["total"] == (89999.0 * 2) + (4999.0 * 1)

    # 3. VERIFY STATE: Stock must be deducted correctly
    assert product_repo.get_stock(PROD_LAPTOP) == 8
    assert product_repo.get_stock(PROD_HEADPHONES) == 4

    # 4. VERIFY STATE: Exactly one order created in database
    assert order_repo.count() == initial_order_count + 1
    persisted_order = client.get(f"/api/v1/orders/{order_id}").json()
    assert persisted_order["id"] == order_id


def test_checkout_at_exact_stock_limit(client: TestClient) -> None:
    """
    USB Hub has stock = 1.
    Requesting 1 should succeed, stock should drop to exactly 0.
    """
    assert product_repo.get_stock(PROD_USB_HUB) == 1

    cart_id = client.post("/api/v1/cart").json()["id"]
    client.post(
        f"/api/v1/cart/{cart_id}/items",
        json={"product_id": PROD_USB_HUB, "quantity": 1},
    )

    res = client.post(
        "/api/v1/checkout",
        headers={"Idempotency-Key": "exact-limit-key"},
        json={"cart_id": cart_id},
    )

    assert res.status_code == 200
    assert product_repo.get_stock(PROD_USB_HUB) == 0


def test_checkout_above_available_stock_rejected(client: TestClient) -> None:
    """
    Attempting to checkout 15 Laptops (available = 10) must fail:
    - 409 Conflict returned
    - Stock stays 10
    - No order created
    """
    initial_stock = product_repo.get_stock(PROD_LAPTOP)
    initial_orders = order_repo.count()

    cart_id = client.post("/api/v1/cart").json()["id"]
    client.post(
        f"/api/v1/cart/{cart_id}/items",
        json={"product_id": PROD_LAPTOP, "quantity": 15},
    )

    res = client.post(
        "/api/v1/checkout",
        headers={"Idempotency-Key": "above-stock-key"},
        json={"cart_id": cart_id},
    )

    assert res.status_code == 409
    assert res.json()["error"] == "OUT_OF_STOCK"

    # State verification
    assert product_repo.get_stock(PROD_LAPTOP) == initial_stock
    assert order_repo.count() == initial_orders


def test_checkout_zero_stock_product_rejected(client: TestClient) -> None:
    """Webcam has 0 stock. Purchasing 1 must be rejected without creating an order."""
    cart_id = client.post("/api/v1/cart").json()["id"]
    client.post(
        f"/api/v1/cart/{cart_id}/items",
        json={"product_id": PROD_WEBCAM, "quantity": 1},
    )

    res = client.post(
        "/api/v1/checkout",
        headers={"Idempotency-Key": "zero-stock-key"},
        json={"cart_id": cart_id},
    )

    assert res.status_code == 409
    assert res.json()["error"] == "OUT_OF_STOCK"
    assert product_repo.get_stock(PROD_WEBCAM) == 0


def test_multi_item_partial_stock_failure_leaves_all_stock_untouched(
    client: TestClient,
) -> None:
    """
    CRITICAL TEST CASE (Problem 1 in challenge description):
    "A failed checkout might deduct stock without creating an order.
     Test a multi-item checkout where only one product is short on stock.
     Verify both products' stock and confirm no order was created."

    Scenario:
    - Item 1: Laptop (stock = 10, requesting 2 -> Available!)
    - Item 2: Headphones (stock = 5, requesting 10 -> SHORT by 5!)

    Expectations:
    - Request fails with 409 OUT_OF_STOCK.
    - Laptop stock remains EXACTLY 10 (Item 1 is NOT partially deducted!).
    - Headphones stock remains EXACTLY 5.
    - Order count in repository does not increase.
    """
    initial_laptop_stock = product_repo.get_stock(PROD_LAPTOP)      # 10
    initial_headphone_stock = product_repo.get_stock(PROD_HEADPHONES)  # 5
    initial_orders = order_repo.count()

    cart_id = client.post("/api/v1/cart").json()["id"]
    client.post(
        f"/api/v1/cart/{cart_id}/items",
        json={"product_id": PROD_LAPTOP, "quantity": 2},
    )
    client.post(
        f"/api/v1/cart/{cart_id}/items",
        json={"product_id": PROD_HEADPHONES, "quantity": 10},
    )

    # Submit checkout
    response = client.post(
        "/api/v1/checkout",
        headers={"Idempotency-Key": "partial-fail-key"},
        json={"cart_id": cart_id},
    )

    # 1. HTTP verification
    assert response.status_code == 409
    data = response.json()
    assert data["error"] == "OUT_OF_STOCK"

    # 2. STATE VERIFICATION: Crucial assertion proving atomicity!
    assert (
        product_repo.get_stock(PROD_LAPTOP) == initial_laptop_stock
    ), "REGRESSION DETECTED: First product stock was deducted despite checkout failure!"
    assert (
        product_repo.get_stock(PROD_HEADPHONES) == initial_headphone_stock
    ), "Headphone stock corrupted!"

    # 3. STATE VERIFICATION: No order was created
    assert order_repo.count() == initial_orders, "Orphan order was created!"
