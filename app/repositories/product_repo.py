"""
repositories/product_repo.py — Product Data Access
======================================================
All reads and writes to the products store go through this module.

Responsibilities:
  - get_all()       → list all products
  - get_by_id()     → fetch one product (raises if not found)
  - get_stock()     → get current stock count for a product
  - deduct_stock()  → reduce stock by quantity (called only inside checkout lock)
  - restore_stock() → undo a deduction (used in rollback scenarios)

Thread safety note:
  deduct_stock() and restore_stock() must only be called while holding
  the checkout lock (get_checkout_lock()). The checkout service handles this.
  These functions do NOT acquire the lock themselves — that would risk deadlock.
"""

from app.exceptions.handlers import ProductNotFoundError
from app.store.database import get_products_db


class ProductRepository:
    """Data access for the products store."""

    def __init__(self) -> None:
        # Always use the accessor — never store a local reference to the dict,
        # so we always see the live state.
        self._db = get_products_db

    def get_all(self) -> list[dict]:
        """Return all products as a list of dicts."""
        return list(self._db().values())

    def get_by_id(self, product_id: str) -> dict:
        """
        Return one product dict.

        Raises:
            ProductNotFoundError: if product_id doesn't exist.
        """
        product = self._db().get(product_id)
        if product is None:
            raise ProductNotFoundError(product_id)
        return product

    def get_stock(self, product_id: str) -> int:
        """
        Return the current stock level for a product.

        Raises:
            ProductNotFoundError: if product_id doesn't exist.
        """
        product = self.get_by_id(product_id)
        return product["stock"]

    def deduct_stock(self, product_id: str, quantity: int) -> None:
        """
        Reduce stock by `quantity`.

        IMPORTANT: Call this ONLY while holding the checkout lock.
        Does NOT validate that enough stock exists — the checkout service
        does that validation BEFORE calling this.

        Raises:
            ProductNotFoundError: if product_id doesn't exist.
        """
        product = self.get_by_id(product_id)
        product["stock"] -= quantity

    def restore_stock(self, product_id: str, quantity: int) -> None:
        """
        Add `quantity` back to stock. Used for rollback if order creation fails
        after stock was already deducted.

        Raises:
            ProductNotFoundError: if product_id doesn't exist.
        """
        product = self.get_by_id(product_id)
        product["stock"] += quantity


# ── Module-level singleton ────────────────────────────────────────────────
# Services import this instance — no need to instantiate it everywhere.
product_repo = ProductRepository()
