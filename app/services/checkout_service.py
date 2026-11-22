"""
services/checkout_service.py — Atomic Checkout Logic
=======================================================
Orchestrates the entire checkout flow:
idempotency check → stock validation → stock deduction → order creation.

Two-Phase Mutation Algorithm:
- Phase 1: Validate ALL items. If ANY item is short, collect and raise OutOfStockError.
           ZERO stock is deducted.
- Phase 2: Deduct stock for all items (safe, all items guaranteed available).
- Phase 3: Create order snapshot and store idempotency key.
"""

from app.exceptions.handlers import CartEmptyError, OutOfStockError
from app.repositories.cart_repo import cart_repo
from app.repositories.order_repo import order_repo
from app.repositories.product_repo import product_repo
from app.services.idempotency_service import idempotency_service
from app.store.database import get_checkout_lock


class CheckoutService:
    """
    Orchestrates the entire checkout flow:
    idempotency check → stock validation → stock deduction → order creation.
    """

    def checkout(self, cart_id: str, idempotency_key: str, payload: dict) -> tuple[dict, bool]:
        """
        Process a checkout request.

        Args:
            cart_id:          ID of the cart to check out.
            idempotency_key:  Value of the Idempotency-Key header.
            payload:          The raw request body dict (for idempotency hashing).

        Returns:
            A tuple (order_dict, is_replay):
                order_dict: The created or replayed order dict.
                is_replay:  True if this was an idempotent replay.

        Raises:
            CartNotFoundError:        if cart_id doesn't exist.
            CartEmptyError:           if cart has no items.
            ProductNotFoundError:     if a product_id in the cart doesn't exist.
            OutOfStockError:          if any item cannot be fulfilled.
            IdempotencyConflictError: if same key was used with different payload.
        """
        # Step 1: Idempotency check (fast path)
        existing_order_id = idempotency_service.check_and_get_existing(
            idempotency_key, payload
        )
        if existing_order_id is not None:
            order = order_repo.get_by_id(existing_order_id)
            return order, True

        # Step 2: Load cart
        items = cart_repo.get_items(cart_id)
        if not items:
            raise CartEmptyError(cart_id)

        # Step 3: Thread-safe atomic checkout
        with get_checkout_lock():
            # PHASE 1 — Validate ALL stock BEFORE touching anything
            failures = []
            for product_id, requested_qty in items.items():
                product = product_repo.get_by_id(product_id)
                available = product["stock"]

                if available < requested_qty:
                    failures.append({
                        "product_id": product_id,
                        "product_name": product["name"],
                        "requested": requested_qty,
                        "available": available,
                    })

            # If ANY product failed validation -> reject EVERYTHING
            if failures:
                raise OutOfStockError(failures)

            # PHASE 2 — Deduct stock for ALL items (safe now)
            order_items = []
            total = 0.0

            for product_id, requested_qty in items.items():
                product = product_repo.get_by_id(product_id)
                unit_price = product["price"]
                subtotal = unit_price * requested_qty

                product_repo.deduct_stock(product_id, requested_qty)

                order_items.append({
                    "product_id": product_id,
                    "product_name": product["name"],
                    "quantity": requested_qty,
                    "unit_price": unit_price,
                    "subtotal": subtotal,
                })
                total += subtotal

            # PHASE 3 — Create order snapshot
            order = order_repo.create(
                cart_id=cart_id,
                items=order_items,
                total=round(total, 2),
            )

            # Store idempotency key
            idempotency_service.store(idempotency_key, payload, order["id"])

        return order, False


# Module-level singleton
checkout_service = CheckoutService()
