"""
models/product.py — Product Schemas
======================================
Defines the shape of product data as it appears in API responses.

We have two separate models:
  - Product:             one product with all fields
  - ProductListResponse: the envelope wrapping the list of products

Why an envelope (ProductListResponse)?
  Instead of returning a bare list `[...]`, we return:
    { "products": [...], "total": 4 }

  Benefits:
  - You can add pagination metadata later without breaking clients.
  - Clients can always expect a dict, never sometimes a list.
  - This is the standard production API pattern.

Note: There is no "create product" schema here because the challenge
does not require a product management endpoint. Products come from seed data.
"""

from pydantic import BaseModel, ConfigDict


class Product(BaseModel):
    """
    Represents a single product as returned by the API.

    model_config: by default Pydantic v2 uses "lax" validation.
    We set from_attributes=True so we can build this from ORM-style
    objects in the future (useful if we swap to SQLAlchemy later).
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    price: float
    stock: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "prod_laptop",
                "name": "Laptop Pro 15",
                "description": "High-performance laptop with 16GB RAM.",
                "price": 89999.00,
                "stock": 10,
            }
        }
    )


class ProductListResponse(BaseModel):
    """Envelope for the GET /products response."""

    products: list[Product]
    total: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "products": [
                    {
                        "id": "prod_laptop",
                        "name": "Laptop Pro 15",
                        "description": "High-performance laptop.",
                        "price": 89999.00,
                        "stock": 10,
                    }
                ],
                "total": 1,
            }
        }
    )
