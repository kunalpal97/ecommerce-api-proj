"""
routes/products.py — GET /products
=====================================
Thin controller — only responsibility is:
  1. Call the repository.
  2. Build and return the response model.

No business logic lives here.
"""

from fastapi import APIRouter

from app.models.product import Product, ProductListResponse
from app.repositories.product_repo import product_repo

router = APIRouter(tags=["Products"])


@router.get(
    "/products",
    response_model=ProductListResponse,
    summary="List all products",
    description="Returns all products in the catalogue with their current stock levels.",
)
def list_products() -> ProductListResponse:
    """
    GET /api/v1/products

    Returns the full product catalogue with live stock counts.
    Stock reflects what has already been deducted by completed checkouts.
    """
    all_products = product_repo.get_all()
    return ProductListResponse(
        products=[Product(**p) for p in all_products],
        total=len(all_products),
    )
