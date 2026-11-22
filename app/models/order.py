"""
models/order.py — Order Schemas
==================================
Defines the shape of an order as created by checkout and returned by GET /orders.

Order lifecycle:
  Cart  →  Checkout  →  Order (created, immutable)

An order is a snapshot in time:
  - It records the product names, prices, and quantities AT THE TIME OF PURCHASE.
  - If a product's price changes later, the order still shows the original price.
  - This is why we store name + unit_price on OrderItem, not just product_id.

OrderStatus:
  For this challenge, orders are always "confirmed" on creation.
  Using an Enum (not a bare string) means:
    - Only valid statuses can appear in responses.
    - Future statuses (shipped, delivered, refunded) are easy to add.
    - OpenAPI docs automatically show allowed values.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class OrderStatus(str, Enum):
    """
    Allowed order statuses.

    Inheriting from str means the enum serializes to its string value
    in JSON responses automatically — no custom serializer needed.
    """

    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class OrderItem(BaseModel):
    """
    One line item within an order.

    Records the full price snapshot so the order remains accurate
    even if the product catalogue changes later.
    """

    product_id: str
    product_name: str
    quantity: int
    unit_price: float = Field(..., description="Price per unit at time of purchase.")
    subtotal: float = Field(..., description="unit_price × quantity")

    model_config = ConfigDict(from_attributes=True)


class Order(BaseModel):
    """
    A completed order returned by the checkout and GET /orders endpoints.

    Fields:
      id:           Unique order identifier (e.g. "ord_xyz789").
      cart_id:      The cart this order was created from.
      items:        Line items — each is a price+quantity snapshot.
      total:        Sum of all subtotals (pre-computed for the client).
      status:       Always "confirmed" for now.
      created_at:   ISO-8601 timestamp of when the order was created.
    """

    id: str
    cart_id: str
    items: list[OrderItem]
    total: float = Field(..., description="Sum of all item subtotals.")
    status: OrderStatus = OrderStatus.CONFIRMED
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "ord_xyz789",
                "cart_id": "cart_abc123",
                "items": [
                    {
                        "product_id": "prod_laptop",
                        "product_name": "Laptop Pro 15",
                        "quantity": 1,
                        "unit_price": 89999.00,
                        "subtotal": 89999.00,
                    },
                    {
                        "product_id": "prod_headphones",
                        "product_name": "Wireless Headphones",
                        "quantity": 2,
                        "unit_price": 4999.00,
                        "subtotal": 9998.00,
                    },
                ],
                "total": 99997.00,
                "status": "confirmed",
                "created_at": "2026-11-22T08:00:00Z",
            }
        },
    )
