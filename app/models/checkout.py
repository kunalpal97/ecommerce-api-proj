"""
models/checkout.py — Checkout Schemas
========================================
Defines request and response shapes for POST /checkout.

This is the most important endpoint in the system — it ties everything together.

CheckoutRequest:
  The client sends a cart_id. That's it. The server looks up the cart,
  validates all stock, deducts, creates the order.

  Why not send items directly in the checkout request?
    - The cart is the source of truth for what the user wants.
    - Sending items again would create a "double-entry" problem.
    - What if the cart has 3 items but the checkout payload only has 2?
    - Using cart_id keeps it simple and unambiguous.

CheckoutResponse:
  On success: wraps the created Order.
  On idempotent replay: wraps the SAME original Order.
  Client cannot tell the difference — both return 200 with the same order.

  Why wrap in an envelope rather than returning Order directly?
    - Allows adding metadata later (e.g. payment_url, tracking_id).
    - Consistent structure across all responses.
"""

from pydantic import BaseModel, ConfigDict, Field

from app.models.order import Order


class CheckoutRequest(BaseModel):
    """
    Request body for POST /checkout.

    The Idempotency-Key is passed as a HEADER (not in this body).
    See routes/checkout.py for how it's extracted.

    Why header, not body?
      - RFC 7231 defines Idempotency-Key as a header.
      - Keeps the business payload clean.
      - Middleware/proxies can inspect and log it without parsing the body.
    """

    cart_id: str = Field(
        ...,
        description="ID of the cart to check out.",
        examples=["cart_abc123"],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"cart_id": "cart_abc123"}
        }
    )


class CheckoutResponse(BaseModel):
    """
    Response body for a successful POST /checkout.

    message: human-readable status ("Order created." or "Order already exists.")
    order:   the created (or replayed) order.
    """

    message: str
    order: Order

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Order created successfully.",
                "order": {
                    "id": "ord_xyz789",
                    "cart_id": "cart_abc123",
                    "items": [
                        {
                            "product_id": "prod_laptop",
                            "product_name": "Laptop Pro 15",
                            "quantity": 1,
                            "unit_price": 89999.00,
                            "subtotal": 89999.00,
                        }
                    ],
                    "total": 89999.00,
                    "status": "confirmed",
                    "created_at": "2026-11-22T08:00:00Z",
                },
            }
        }
    )
