"""
routes/orders.py — GET /orders/{order_id}
===========================================
Simple read-only endpoint to retrieve a completed order.

Used by tests to:
  - Confirm an order was created after a successful checkout.
  - Verify an order was NOT created after a failed checkout.
  - Compare two idempotent responses point to the same order ID.
"""

from fastapi import APIRouter

from app.models.order import Order, OrderItem, OrderStatus
from app.repositories.order_repo import order_repo

router = APIRouter(tags=["Orders"])


@router.get(
    "/orders/{order_id}",
    response_model=Order,
    summary="Get order by ID",
    description="Returns the full order details including all line items, total, and status.",
)
def get_order(order_id: str) -> Order:
    """
    GET /api/v1/orders/{order_id}

    Raises:
        404 Not Found: if order_id doesn't exist.
    """
    order_dict = order_repo.get_by_id(order_id)   # raises OrderNotFoundError if missing

    return Order(
        id=order_dict["id"],
        cart_id=order_dict["cart_id"],
        items=[OrderItem(**item) for item in order_dict["items"]],
        total=order_dict["total"],
        status=OrderStatus(order_dict["status"]),
        created_at=order_dict["created_at"],
    )
