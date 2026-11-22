"""
tests/test_concurrency.py — Race Condition & Overselling Prevention Tests
==========================================================================
This is the most advanced test in the suite — it proves thread-safety.

The Overselling Problem (Real-world scenario):
  It is 11:59 PM on a flash sale. A single USB Hub is left in stock.
  10 users simultaneously click "Buy Now".

  WITHOUT thread-safety:
    All 10 goroutines read stock=1, all pass validation, all deduct.
    Stock becomes -9. 10 orders created. Business loses ₹22,491 extra!

  WITH our threading.Lock (this implementation):
    Only ONE request can enter the critical section at a time.
    Request 1 reads stock=1, validates, deducts → stock=0, order created.
    Requests 2-10 read stock=0, fail validation → 409 Out of Stock.
    Result: Exactly 1 order. Stock = 0. Zero overselling.

How this test works:
  - Uses Python's ThreadPoolExecutor to fire 10 checkout requests
    simultaneously from separate threads into the same FastAPI TestClient.
  - Each thread has its own cart pre-loaded with 1 USB Hub.
  - All 10 threads hit POST /checkout at the exact same time.
  - We assert strict outcomes: exactly 1 success, 9 failures, stock=0.

Why TestClient works for this:
  FastAPI's TestClient is thread-safe — multiple threads can call it
  simultaneously. The in-process ASGI transport handles concurrent requests
  through the same app instance, exercising our threading.Lock for real.
"""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi.testclient import TestClient

from app.repositories.order_repo import order_repo
from app.repositories.product_repo import product_repo
from tests.conftest import PROD_USB_HUB


def test_concurrent_checkout_prevents_overselling(client: TestClient) -> None:
    """
    TEN concurrent users attempt to buy the LAST USB Hub simultaneously.

    Expected outcome (proving thread-safety):
      ✅ Exactly 1 checkout succeeds (HTTP 200).
      ✅ Exactly 9 checkouts fail (HTTP 409 OUT_OF_STOCK).
      ✅ Stock reaches exactly 0 — never goes negative.
      ✅ Exactly 1 order exists in the database.

    If threading.Lock() were removed from checkout_service.py,
    this test would catch overselling (stock < 0 or count(orders) > 1).
    """
    NUM_USERS = 10
    assert product_repo.get_stock(PROD_USB_HUB) == 1

    # Phase 1: Pre-create 10 carts (sequential, before the race)
    carts = []
    for i in range(NUM_USERS):
        cart_id = client.post("/api/v1/cart").json()["id"]
        client.post(
            f"/api/v1/cart/{cart_id}/items",
            json={"product_id": PROD_USB_HUB, "quantity": 1},
        )
        carts.append(cart_id)

    # Phase 2: Fire all 10 checkout requests simultaneously
    results: list[int] = []
    results_lock = threading.Lock()   # protect the results list itself

    def attempt_checkout(index: int) -> int:
        """Each thread calls checkout and returns the HTTP status code."""
        response = client.post(
            "/api/v1/checkout",
            headers={"Idempotency-Key": f"concurrent-race-key-{index}"},
            json={"cart_id": carts[index]},
        )
        return response.status_code

    with ThreadPoolExecutor(max_workers=NUM_USERS) as executor:
        futures = {executor.submit(attempt_checkout, i): i for i in range(NUM_USERS)}
        for future in as_completed(futures):
            with results_lock:
                results.append(future.result())

    # Phase 3: Assert strict outcomes
    success_count = results.count(200)
    failure_count = results.count(409)

    assert success_count == 1, (
        f"Expected exactly 1 successful checkout, got {success_count}. "
        f"Results: {sorted(results)}"
    )
    assert failure_count == NUM_USERS - 1, (
        f"Expected {NUM_USERS - 1} rejected checkouts, got {failure_count}. "
        f"Results: {sorted(results)}"
    )

    # Stock must be exactly 0, never negative
    final_stock = product_repo.get_stock(PROD_USB_HUB)
    assert final_stock == 0, (
        f"Stock should be 0 after 1 successful checkout, but got {final_stock}. "
        f"Negative stock means OVERSELLING occurred!"
    )

    # Exactly 1 order in database — no duplicate orders created
    total_orders = order_repo.count()
    assert total_orders == 1, (
        f"Expected exactly 1 order in the database, found {total_orders}. "
        f"This means duplicate orders were created for the same stock!"
    )


def test_concurrent_checkout_same_key_no_duplicate_orders(client: TestClient) -> None:
    """
    FIVE concurrent retries with the SAME idempotency key.

    Simulates a client whose retry logic fires 5 requests simultaneously
    (network layer timeout + aggressive retry).

    Expected outcome:
      ✅ Exactly 1 order created.
      ✅ Stock deducted exactly once (not 5 times).
      ✅ All 5 responses return the SAME order_id.
    """
    NUM_RETRIES = 5
    IDEMPOTENCY_KEY = "aggressive-retry-key-xyz"

    # Setup: one cart with 1 Laptop
    cart_id = client.post("/api/v1/cart").json()["id"]
    client.post(
        f"/api/v1/cart/{cart_id}/items",
        json={"product_id": "prod_laptop", "quantity": 1},
    )

    order_ids: list[str] = []
    ids_lock = threading.Lock()

    def retry_checkout(_: int) -> None:
        response = client.post(
            "/api/v1/checkout",
            headers={"Idempotency-Key": IDEMPOTENCY_KEY},
            json={"cart_id": cart_id},
        )
        assert response.status_code == 200, f"Unexpected status: {response.status_code}"
        with ids_lock:
            order_ids.append(response.json()["order"]["id"])

    with ThreadPoolExecutor(max_workers=NUM_RETRIES) as executor:
        futures = [executor.submit(retry_checkout, i) for i in range(NUM_RETRIES)]
        for future in as_completed(futures):
            future.result()   # re-raise any assertion errors from threads

    # All 5 responses must return the SAME order
    assert len(set(order_ids)) == 1, (
        f"All retries must return the same order ID, but got: {set(order_ids)}"
    )

    # Stock deducted exactly once
    assert product_repo.get_stock("prod_laptop") == 9  # 10 - 1 = 9

    # Exactly 1 order in database
    assert order_repo.count() == 1
