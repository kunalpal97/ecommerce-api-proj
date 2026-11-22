"""
tests/test_cart.py — Cart & Quantity Validation Tests
========================================================
Verifies cart operations and strict quantity validation:
- Cart creation returns 201 with an empty item list.
- Adding valid positive whole-number quantities succeeds.
- Invalid quantities (0, negative, floats, non-numeric) are strictly rejected with 422.
- Updating and deleting cart items works as expected.
"""

import pytest
from fastapi.testclient import TestClient

from tests.conftest import PROD_LAPTOP


def test_create_empty_cart(client: TestClient) -> None:
    """Verify that creating a cart returns an ID and empty item list."""
    response = client.post("/api/v1/cart")

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["id"].startswith("cart_")
    assert data["items"] == []
    assert data["item_count"] == 0


def test_add_item_to_cart_valid_quantity(client: TestClient) -> None:
    """Verify adding an item with positive whole number quantity."""
    cart_res = client.post("/api/v1/cart").json()
    cart_id = cart_res["id"]

    add_res = client.post(
        f"/api/v1/cart/{cart_id}/items",
        json={"product_id": PROD_LAPTOP, "quantity": 2},
    )

    assert add_res.status_code == 200
    data = add_res.json()
    assert data["item_count"] == 1
    assert data["items"][0]["product_id"] == PROD_LAPTOP
    assert data["items"][0]["quantity"] == 2


@pytest.mark.parametrize(
    "invalid_quantity,description",
    [
        (0, "zero quantity"),
        (-1, "negative integer"),
        (-99, "large negative integer"),
        (1.5, "floating point number"),
        (0.99, "fractional number"),
        ("two", "string value"),
    ],
)
def test_add_item_rejects_invalid_quantities(
    client: TestClient, invalid_quantity, description
) -> None:
    """
    Requirement: 'Accept only positive whole-number quantities.'
    Ensure that 0, negative integers, floats, and strings are rejected with HTTP 422.
    """
    cart_res = client.post("/api/v1/cart").json()
    cart_id = cart_res["id"]

    response = client.post(
        f"/api/v1/cart/{cart_id}/items",
        json={"product_id": PROD_LAPTOP, "quantity": invalid_quantity},
    )

    assert response.status_code == 422, f"Failed for {description}: {invalid_quantity}"

    # Verify cart remains empty
    cart_get = client.get(f"/api/v1/cart/{cart_id}").json()
    assert cart_get["item_count"] == 0
    assert cart_get["items"] == []


def test_update_item_quantity_in_cart(client: TestClient) -> None:
    """Verify PATCH updates quantity of an existing item."""
    cart_res = client.post("/api/v1/cart").json()
    cart_id = cart_res["id"]

    # First add item with qty 1
    client.post(
        f"/api/v1/cart/{cart_id}/items",
        json={"product_id": PROD_LAPTOP, "quantity": 1},
    )

    # Patch to qty 3
    patch_res = client.patch(
        f"/api/v1/cart/{cart_id}/items/{PROD_LAPTOP}",
        json={"quantity": 3},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["items"][0]["quantity"] == 3


def test_remove_item_from_cart(client: TestClient) -> None:
    """Verify DELETE removes an item from cart."""
    cart_res = client.post("/api/v1/cart").json()
    cart_id = cart_res["id"]

    client.post(
        f"/api/v1/cart/{cart_id}/items",
        json={"product_id": PROD_LAPTOP, "quantity": 1},
    )

    del_res = client.delete(f"/api/v1/cart/{cart_id}/items/{PROD_LAPTOP}")
    assert del_res.status_code == 200
    assert del_res.json()["item_count"] == 0
    assert del_res.json()["items"] == []
