"""
repositories/cart_repo.py — Cart Data Access
==============================================
All reads and writes to the carts store go through this module.

Cart data structure in memory:
    {
        "cart_abc123": {
            "id": "cart_abc123",
            "items": {
                "prod_laptop": 2,
                "prod_headphones": 1
            }
        }
    }

Items are stored as a dict (product_id → quantity) for O(1) lookup
and easy overwrite when updating quantities.

ID generation:
    We use uuid4 for cart IDs — globally unique, no central coordination needed.
    Format: "cart_<first 8 chars of uuid>" → readable + unique enough.
"""

import uuid

from app.exceptions.handlers import CartNotFoundError, ProductNotFoundError
from app.store.database import get_carts_db


class CartRepository:
    """Data access for the carts store."""

    def __init__(self) -> None:
        self._db = get_carts_db

    def _generate_id(self) -> str:
        """Generate a short, readable cart ID."""
        return f"cart_{uuid.uuid4().hex[:8]}"

    def create(self) -> dict:
        """
        Create a new empty cart and return it.

        Returns the full cart dict (id + empty items dict).
        """
        cart_id = self._generate_id()
        cart = {
            "id": cart_id,
            "items": {},   # { product_id: quantity }
        }
        self._db()[cart_id] = cart
        return cart

    def get_by_id(self, cart_id: str) -> dict:
        """
        Return one cart dict.

        Raises:
            CartNotFoundError: if cart_id doesn't exist.
        """
        cart = self._db().get(cart_id)
        if cart is None:
            raise CartNotFoundError(cart_id)
        return cart

    def add_or_update_item(self, cart_id: str, product_id: str, quantity: int) -> dict:
        """
        Set the quantity for product_id in the cart.

        If the product is already in the cart, its quantity is replaced
        (not added to). This is the standard "add to cart" behavior:
          - First call:  add 2 → cart has 2
          - Second call: add 2 → cart still has 2 (not 4)
        To truly update quantity, use this same method.

        Raises:
            CartNotFoundError:   if cart_id doesn't exist.
        """
        cart = self.get_by_id(cart_id)
        cart["items"][product_id] = quantity
        return cart

    def update_item_quantity(self, cart_id: str, product_id: str, quantity: int) -> dict:
        """
        Update the quantity of an existing item (PATCH semantics).

        Raises:
            CartNotFoundError:   if cart_id doesn't exist.
            ProductNotFoundError: if product_id is not in this cart.
        """
        cart = self.get_by_id(cart_id)

        if product_id not in cart["items"]:
            raise ProductNotFoundError(product_id)

        cart["items"][product_id] = quantity
        return cart

    def remove_item(self, cart_id: str, product_id: str) -> dict:
        """
        Remove a product from the cart entirely.

        Raises:
            CartNotFoundError:   if cart_id doesn't exist.
            ProductNotFoundError: if product_id is not in this cart.
        """
        cart = self.get_by_id(cart_id)

        if product_id not in cart["items"]:
            raise ProductNotFoundError(product_id)

        del cart["items"][product_id]
        return cart

    def get_items(self, cart_id: str) -> dict[str, int]:
        """
        Return the items dict { product_id: quantity } for a cart.

        Raises:
            CartNotFoundError: if cart_id doesn't exist.
        """
        cart = self.get_by_id(cart_id)
        return cart["items"]


# ── Module-level singleton ─────────────────────────────────────────────────
cart_repo = CartRepository()
