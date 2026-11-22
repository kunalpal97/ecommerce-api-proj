"""
repositories/order_repo.py — Order Data Access
================================================
All reads and writes to the orders store go through this module.

Order data structure in memory:
    {
        "ord_xyz789": {
            "id": "ord_xyz789",
            "cart_id": "cart_abc123",
            "items": [
                {
                    "product_id": "prod_laptop",
                    "product_name": "Laptop Pro 15",
                    "quantity": 2,
                    "unit_price": 89999.0,
                    "subtotal": 179998.0
                }
            ],
            "total": 179998.0,
            "status": "confirmed",
            "created_at": datetime(...)
        }
    }

Why items are a list here (not a dict):
  - In the cart, items are { product_id: quantity } for fast lookup.
  - In an order, items are a list because:
      a) Order is a snapshot — no need to look up by product_id.
      b) Each OrderItem carries name + price — richer than a simple dict.
      c) Lists serialize more naturally to JSON for order display.

ID generation:
  Format: "ord_<first 8 chars of uuid4>" — same pattern as cart IDs.
"""

import uuid
from datetime import datetime, timezone

from app.exceptions.handlers import OrderNotFoundError
from app.store.database import get_orders_db


class OrderRepository:
    """Data access for the orders store."""

    def __init__(self) -> None:
        self._db = get_orders_db

    def _generate_id(self) -> str:
        """Generate a short, readable order ID."""
        return f"ord_{uuid.uuid4().hex[:8]}"

    def create(
        self,
        cart_id: str,
        items: list[dict],
        total: float,
    ) -> dict:
        """
        Persist a new order and return it.

        Args:
            cart_id: The cart this order was created from.
            items:   List of dicts — each with product_id, product_name,
                     quantity, unit_price, subtotal.
            total:   Pre-computed sum of all subtotals.

        Returns:
            The full order dict (ready to be parsed into an Order model).
        """
        order_id = self._generate_id()
        order = {
            "id": order_id,
            "cart_id": cart_id,
            "items": items,
            "total": total,
            "status": "confirmed",
            "created_at": datetime.now(timezone.utc),
        }
        self._db()[order_id] = order
        return order

    def get_by_id(self, order_id: str) -> dict:
        """
        Return one order dict.

        Raises:
            OrderNotFoundError: if order_id doesn't exist.
        """
        order = self._db().get(order_id)
        if order is None:
            raise OrderNotFoundError(order_id)
        return order

    def count(self) -> int:
        """Return the total number of orders. Used in tests to verify no duplicate was created."""
        return len(self._db())


# ── Module-level singleton ─────────────────────────────────────────────────
order_repo = OrderRepository()
