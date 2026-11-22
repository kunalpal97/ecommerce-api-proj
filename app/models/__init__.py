"""
models/__init__.py — Public model exports
==========================================
Import all models from this package using:
    from app.models import Product, Order, CartResponse, ...

This avoids long import paths like:
    from app.models.product import Product
    from app.models.cart import CartResponse
"""

from app.models.cart import (
    AddItemRequest,
    CartItemResponse,
    CartResponse,
    StrictPositiveInt,
    UpdateItemRequest,
)
from app.models.checkout import CheckoutRequest, CheckoutResponse
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product, ProductListResponse

__all__ = [
    # Product
    "Product",
    "ProductListResponse",
    # Cart
    "StrictPositiveInt",
    "AddItemRequest",
    "UpdateItemRequest",
    "CartItemResponse",
    "CartResponse",
    # Order
    "OrderStatus",
    "OrderItem",
    "Order",
    # Checkout
    "CheckoutRequest",
    "CheckoutResponse",
]
