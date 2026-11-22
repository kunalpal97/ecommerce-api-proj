"""
routes/cart.py — Cart Endpoints
==================================
Endpoints:
  POST   /cart                              → Create a new empty cart
  POST   /cart/{cart_id}/items              → Add or set an item in the cart
  PATCH  /cart/{cart_id}/items/{product_id} → Update quantity of existing item
  DELETE /cart/{cart_id}/items/{product_id} → Remove item from cart
  GET    /cart/{cart_id}                    → Get current cart state

Each route validates:
  - Cart exists (CartNotFoundError → 404 handled globally)
  - Product exists (ProductNotFoundError → 404 handled globally)
  - Quantity is valid (Pydantic StrictPositiveInt → 422 auto-handled)
"""

from fastapi import APIRouter

from app.models.cart import (
    AddItemRequest,
    CartItemResponse,
    CartResponse,
    UpdateItemRequest,
)
from app.repositories.cart_repo import cart_repo
from app.repositories.product_repo import product_repo

router = APIRouter(tags=["Cart"])


def _build_cart_response(cart: dict) -> CartResponse:
    """Convert raw cart dict → CartResponse model."""
    items = [
        CartItemResponse(product_id=pid, quantity=qty)
        for pid, qty in cart["items"].items()
    ]
    return CartResponse(
        id=cart["id"],
        items=items,
        item_count=len(items),
    )


@router.post(
    "/cart",
    response_model=CartResponse,
    status_code=201,
    summary="Create a new cart",
    description="Creates an empty cart and returns its ID. Use this ID for all subsequent cart operations.",
)
def create_cart() -> CartResponse:
    """POST /api/v1/cart — Create an empty cart."""
    cart = cart_repo.create()
    return _build_cart_response(cart)


@router.get(
    "/cart/{cart_id}",
    response_model=CartResponse,
    summary="Get cart by ID",
    description="Returns the current state of a cart including all items and quantities.",
)
def get_cart(cart_id: str) -> CartResponse:
    """GET /api/v1/cart/{cart_id}"""
    cart = cart_repo.get_by_id(cart_id)
    return _build_cart_response(cart)


@router.post(
    "/cart/{cart_id}/items",
    response_model=CartResponse,
    summary="Add item to cart",
    description=(
        "Adds a product to the cart. If the product already exists in the cart, "
        "its quantity is replaced with the new value. "
        "Quantity must be a positive whole number (≥ 1)."
    ),
)
def add_item_to_cart(cart_id: str, body: AddItemRequest) -> CartResponse:
    """
    POST /api/v1/cart/{cart_id}/items

    Validates that the product exists in the catalogue before adding.
    Does NOT validate stock here — stock is validated at checkout time only.
    (Checking stock at add-to-cart would be inaccurate: stock can change
    between add and checkout.)
    """
    # Verify product exists in catalogue (raises ProductNotFoundError if not)
    product_repo.get_by_id(body.product_id)

    cart = cart_repo.add_or_update_item(cart_id, body.product_id, body.quantity)
    return _build_cart_response(cart)


@router.patch(
    "/cart/{cart_id}/items/{product_id}",
    response_model=CartResponse,
    summary="Update item quantity",
    description=(
        "Updates the quantity of a product already in the cart. "
        "The product must already be in the cart (use POST /items to add first). "
        "Quantity must be a positive whole number (≥ 1)."
    ),
)
def update_cart_item(
    cart_id: str,
    product_id: str,
    body: UpdateItemRequest,
) -> CartResponse:
    """PATCH /api/v1/cart/{cart_id}/items/{product_id}"""
    cart = cart_repo.update_item_quantity(cart_id, product_id, body.quantity)
    return _build_cart_response(cart)


@router.delete(
    "/cart/{cart_id}/items/{product_id}",
    response_model=CartResponse,
    summary="Remove item from cart",
    description="Removes a product from the cart entirely.",
)
def remove_cart_item(cart_id: str, product_id: str) -> CartResponse:
    """DELETE /api/v1/cart/{cart_id}/items/{product_id}"""
    cart = cart_repo.remove_item(cart_id, product_id)
    return _build_cart_response(cart)
