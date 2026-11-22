"""
tests/test_products.py — Product Catalogue Tests
===================================================
Verifies the GET /api/v1/products endpoint:
- Catalogue returns all seeded products with valid fields.
- Stock values match the expected baseline.
- Structure conforms to ProductListResponse schema.
"""

from fastapi.testclient import TestClient

from tests.conftest import PROD_HEADPHONES, PROD_LAPTOP, PROD_USB_HUB, PROD_WEBCAM


def test_list_products_returns_all_seed_items(client: TestClient) -> None:
    """Verify that GET /products returns all 4 seeded products with correct initial stock."""
    response = client.get("/api/v1/products")

    assert response.status_code == 200
    data = response.json()

    assert "products" in data
    assert "total" in data
    assert data["total"] == 4
    assert len(data["products"]) == 4

    # Map products by ID for deterministic checking
    products_by_id = {p["id"]: p for p in data["products"]}

    assert PROD_LAPTOP in products_by_id
    assert products_by_id[PROD_LAPTOP]["stock"] == 10
    assert products_by_id[PROD_LAPTOP]["price"] == 89999.0

    assert PROD_HEADPHONES in products_by_id
    assert products_by_id[PROD_HEADPHONES]["stock"] == 5

    assert PROD_USB_HUB in products_by_id
    assert products_by_id[PROD_USB_HUB]["stock"] == 1

    assert PROD_WEBCAM in products_by_id
    assert products_by_id[PROD_WEBCAM]["stock"] == 0
