"""
models/cart.py — Cart Schemas
================================
Defines request and response shapes for all cart operations.

Key design decision — StrictPositiveInt:
  quantity: Annotated[int, Field(strict=True, ge=1)]

  strict=True → Pydantic will NOT coerce floats to int.
                1.5 → rejected with 422 (not silently rounded to 1).
  ge=1        → quantity must be ≥ 1 (rejects 0 and negatives).

  This fully satisfies: "Accept only positive whole-number quantities."
  And it happens automatically before your business logic runs.

Cart item storage:
  Items are stored as a dict { product_id → quantity } in the DB.
  For the response, we convert to a list of CartItemResponse for
  cleaner JSON output.
"""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


# ── Reusable type alias ───────────────────────────────────────────────────
# Used wherever quantity appears — single definition, used everywhere.
# If the rule changes (e.g. max 999), change it here only.
StrictPositiveInt = Annotated[
    int,
    Field(
        strict=True,          # reject floats like 1.5 — no silent coercion
        ge=1,                 # reject 0, -1, -99 …
        description="Positive whole number quantity (minimum 1).",
    ),
]


# ── Request bodies ─────────────────────────────────────────────────────────

class AddItemRequest(BaseModel):
    """
    Request body for POST /cart/{cart_id}/items
    Adds a product to the cart (or replaces its quantity if it already exists).
    """

    product_id: str = Field(
        ...,
        description="The ID of the product to add.",
        examples=["prod_laptop"],
    )
    quantity: StrictPositiveInt

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "product_id": "prod_laptop",
                "quantity": 2,
            }
        }
    )


class UpdateItemRequest(BaseModel):
    """
    Request body for PATCH /cart/{cart_id}/items/{product_id}
    Updates the quantity of an existing cart item.
    Setting quantity to 0 is not allowed — use DELETE to remove an item.
    """

    quantity: StrictPositiveInt

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"quantity": 3}
        }
    )


# ── Response bodies ────────────────────────────────────────────────────────

class CartItemResponse(BaseModel):
    """One line item in a cart response."""

    product_id: str
    quantity: int

    model_config = ConfigDict(from_attributes=True)


class CartResponse(BaseModel):
    """
    Full cart as returned by the API.

    items: list of CartItemResponse (not a dict — cleaner JSON for clients).
    item_count: total number of distinct products in the cart.
    """

    id: str
    items: list[CartItemResponse]
    item_count: int

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "cart_abc123",
                "items": [
                    {"product_id": "prod_laptop", "quantity": 2},
                    {"product_id": "prod_headphones", "quantity": 1},
                ],
                "item_count": 2,
            }
        },
    )
