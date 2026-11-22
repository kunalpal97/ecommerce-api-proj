"""
exceptions/handlers.py — Custom Exceptions & Global Error Handlers
====================================================================
Two responsibilities:

1. Define domain-specific exceptions (business logic errors).
   These are raised deep in services/repositories — NOT HTTP errors.
   The service layer should NOT know about HTTP status codes.

2. Register handlers that convert those exceptions → HTTP responses.
   This mapping lives here, in ONE place, not scattered across routes.

Pattern:
  Service raises → OutOfStockError("prod_laptop")
  Handler catches → returns HTTP 409 { "error": "...", "detail": "..." }

Why not just raise HTTPException directly in services?
  - Services would then depend on FastAPI (HTTP concern bleeds into logic).
  - Harder to unit-test services in isolation.
  - Changing the HTTP status code means changing business logic code.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


# ══════════════════════════════════════════════════════════════════════════
# Custom Domain Exceptions
# ══════════════════════════════════════════════════════════════════════════

class CommerceAPIError(Exception):
    """Base class for all Commerce API errors."""
    pass


class ProductNotFoundError(CommerceAPIError):
    """Raised when a product_id does not exist in the catalogue."""
    def __init__(self, product_id: str) -> None:
        self.product_id = product_id
        super().__init__(f"Product '{product_id}' not found.")


class CartNotFoundError(CommerceAPIError):
    """Raised when a cart_id does not exist."""
    def __init__(self, cart_id: str) -> None:
        self.cart_id = cart_id
        super().__init__(f"Cart '{cart_id}' not found.")


class OrderNotFoundError(CommerceAPIError):
    """Raised when an order_id does not exist."""
    def __init__(self, order_id: str) -> None:
        self.order_id = order_id
        super().__init__(f"Order '{order_id}' not found.")


class OutOfStockError(CommerceAPIError):
    """
    Raised when checkout is attempted but one or more items cannot be fulfilled.

    Contains a list of all products that failed — not just the first one.
    This gives clients a complete picture in one response.
    """
    def __init__(self, failures: list[dict]) -> None:
        """
        Args:
            failures: list of dicts, each with keys:
                        product_id, product_name, requested, available
        """
        self.failures = failures
        names = [f["product_name"] for f in failures]
        super().__init__(f"Insufficient stock for: {', '.join(names)}")


class InvalidQuantityError(CommerceAPIError):
    """Raised when a quantity is not a positive whole number."""
    def __init__(self, quantity: int | float) -> None:
        self.quantity = quantity
        super().__init__(
            f"Invalid quantity '{quantity}'. Must be a positive whole number (≥ 1)."
        )


class CartEmptyError(CommerceAPIError):
    """Raised when checkout is attempted on an empty cart."""
    def __init__(self, cart_id: str) -> None:
        self.cart_id = cart_id
        super().__init__(f"Cart '{cart_id}' is empty. Add items before checking out.")


class IdempotencyConflictError(CommerceAPIError):
    """
    Raised when the same Idempotency-Key is reused with a DIFFERENT payload.

    This is not a duplicate request (which would be fine) —
    it is a conflicting request that must be rejected to protect data integrity.
    """
    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(
            f"Idempotency-Key '{key}' was already used with a different payload."
        )


class MissingIdempotencyKeyError(CommerceAPIError):
    """Raised when a checkout request arrives without an Idempotency-Key header."""
    def __init__(self) -> None:
        super().__init__(
            "Checkout requires an 'Idempotency-Key' header. "
            "Generate a unique key (e.g. UUID) per checkout attempt."
        )


# ══════════════════════════════════════════════════════════════════════════
# HTTP Response Handlers
# ══════════════════════════════════════════════════════════════════════════

def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all custom exception → HTTP response mappings on the FastAPI app.

    Called once during app creation in main.py.
    """

    @app.exception_handler(ProductNotFoundError)
    async def product_not_found_handler(
        request: Request, exc: ProductNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={
                "error": "PRODUCT_NOT_FOUND",
                "message": str(exc),
                "product_id": exc.product_id,
            },
        )

    @app.exception_handler(CartNotFoundError)
    async def cart_not_found_handler(
        request: Request, exc: CartNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={
                "error": "CART_NOT_FOUND",
                "message": str(exc),
                "cart_id": exc.cart_id,
            },
        )

    @app.exception_handler(OrderNotFoundError)
    async def order_not_found_handler(
        request: Request, exc: OrderNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={
                "error": "ORDER_NOT_FOUND",
                "message": str(exc),
                "order_id": exc.order_id,
            },
        )

    @app.exception_handler(OutOfStockError)
    async def out_of_stock_handler(
        request: Request, exc: OutOfStockError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={
                "error": "OUT_OF_STOCK",
                "message": str(exc),
                "failures": exc.failures,
            },
        )

    @app.exception_handler(InvalidQuantityError)
    async def invalid_quantity_handler(
        request: Request, exc: InvalidQuantityError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": "INVALID_QUANTITY",
                "message": str(exc),
            },
        )

    @app.exception_handler(CartEmptyError)
    async def cart_empty_handler(
        request: Request, exc: CartEmptyError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={
                "error": "CART_EMPTY",
                "message": str(exc),
                "cart_id": exc.cart_id,
            },
        )

    @app.exception_handler(IdempotencyConflictError)
    async def idempotency_conflict_handler(
        request: Request, exc: IdempotencyConflictError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={
                "error": "IDEMPOTENCY_CONFLICT",
                "message": str(exc),
                "idempotency_key": exc.key,
            },
        )

    @app.exception_handler(MissingIdempotencyKeyError)
    async def missing_key_handler(
        request: Request, exc: MissingIdempotencyKeyError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={
                "error": "MISSING_IDEMPOTENCY_KEY",
                "message": str(exc),
            },
        )
