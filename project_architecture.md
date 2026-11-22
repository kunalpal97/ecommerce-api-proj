# Commerce API — Architecture & Build Plan

> **Challenge:** SDET-1 | Fynd Hiring Hackathon  
> **Python Version:** 3.12.3  
> **Status:** 🏗️ In Progress

---

## Problem Summary

Two release-blocking bugs must be handled:

| # | Bug | Root Cause | Solution |
|---|-----|------------|----------|
| 1 | Stock deducted, no order created | Non-atomic checkout | Validate ALL → deduct ALL → create order (all-or-nothing) |
| 2 | Duplicate order on retry | No idempotency | Idempotency key stored per request; replay = original response |

---

## Technology Stack

| Layer | Technology | Version | Reason |
|-------|-----------|---------|--------|
| Language | Python | 3.12.3 | Modern, type-safe |
| Framework | FastAPI | 0.115.x | Auto-validation, async, Swagger docs |
| Data Validation | Pydantic v2 | 2.x | Built into FastAPI, strict type enforcement |
| Testing | pytest | 8.x | Industry standard |
| HTTP Test Client | httpx | 0.27.x | Async-compatible, in-process testing |
| Test Async Support | anyio / pytest-anyio | stable | Async test execution |
| ASGI Server (dev) | uvicorn | 0.30.x | Lightweight, production-capable |

---

## Project Structure

```
commerce-api/
│
├── app/
│   ├── main.py                   # FastAPI app factory
│   ├── config.py                 # Settings & constants
│   │
│   ├── models/                   # Pydantic schemas (request/response shapes)
│   │   ├── product.py
│   │   ├── cart.py
│   │   ├── order.py
│   │   └── checkout.py
│   │
│   ├── store/                    # In-memory data store
│   │   ├── database.py           # Dicts + threading locks
│   │   └── seed.py               # Seed ≥2 products
│   │
│   ├── repositories/             # Data access layer (swappable)
│   │   ├── product_repo.py
│   │   ├── cart_repo.py
│   │   └── order_repo.py
│   │
│   ├── services/                 # Business logic
│   │   ├── checkout_service.py   # Atomic checkout
│   │   └── idempotency_service.py
│   │
│   ├── routes/                   # HTTP controllers (thin)
│   │   ├── products.py
│   │   ├── cart.py
│   │   ├── checkout.py
│   │   └── orders.py
│   │
│   └── exceptions/               # Custom errors + handlers
│       └── handlers.py
│
├── tests/
│   ├── conftest.py               # Fixtures, fresh state per test
│   ├── test_products.py
│   ├── test_cart.py
│   ├── test_checkout.py          # Critical: atomic + partial failure
│   └── test_idempotency.py       # Retry scenarios
│
├── docs/
│   └── decisions.md              # Architecture Decision Records
│
├── requirements.txt              # Pinned production deps
├── requirements-dev.txt          # Dev/test deps
└── README.md
```

---

## Layer Responsibilities

```
HTTP Request
     │
     ▼
┌─────────────┐
│   Routes    │  Parse request → call service → return response
└──────┬──────┘
       ▼
┌─────────────────┐
│    Services     │  Business logic ONLY lives here
│  checkout /     │  - Validate ALL stock (atomic)
│  idempotency    │  - Deduct + create order together
└──────┬──────────┘
       ▼
┌──────────────────┐
│  Repositories    │  All data access (swappable layer)
└──────┬───────────┘
       ▼
┌──────────────────┐
│  Store / DB      │  In-memory dicts + threading.Lock
└──────────────────┘
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/products` | List all products with stock |
| `POST` | `/cart` | Create a new cart |
| `POST` | `/cart/{cart_id}/items` | Add item to cart |
| `PATCH` | `/cart/{cart_id}/items/{product_id}` | Update item quantity |
| `DELETE` | `/cart/{cart_id}/items/{product_id}` | Remove item from cart |
| `POST` | `/checkout` | Submit checkout (requires `Idempotency-Key` header) |
| `GET` | `/orders/{order_id}` | Retrieve an order |

---

## Critical Business Rules

### Rule 1 — Atomic Checkout
```
❌ Wrong:   deduct(A) → check(B) → fail → stock corrupted
✅ Correct: validate(A) → validate(B) → deduct(A) → deduct(B) → create_order
```
If ANY product is out of stock, reject EVERYTHING. No stock is touched.

### Rule 2 — Idempotency
```
Request 1: POST /checkout  Idempotency-Key: abc123  → creates order #1
Request 2: POST /checkout  Idempotency-Key: abc123  same payload → returns order #1 (no new order)
Request 3: POST /checkout  Idempotency-Key: abc123  diff payload → 409 Conflict (rejected)
```

---

## Build Order

| Step | Component | Key Concept |
|------|-----------|-------------|
| 2 | `requirements.txt` | Dependency pinning |
| 3 | `config.py` + `main.py` | App bootstrap |
| 4 | `store/database.py` + `seed.py` | In-memory DB + thread safety |
| 5 | `models/` (4 files) | Type-safe data contracts |
| 6 | `exceptions/handlers.py` | Centralized error handling |
| 7 | `repositories/` (3 files) | Data access abstraction |
| 8 | `services/checkout_service.py` | Atomic checkout logic |
| 9 | `services/idempotency_service.py` | Retry handling |
| 10 | `routes/` (4 files) | HTTP controllers |
| 11 | `tests/conftest.py` | Test infrastructure |
| 12 | `tests/test_products.py` + `test_cart.py` | Foundation tests |
| 13 | `tests/test_checkout.py` | Core business tests |
| 14 | `tests/test_idempotency.py` | Retry tests |
| 15 | Regression proof | Break → fail → fix → pass |
| 16 | README + verdict | Final submission |

---

## Test Coverage Plan

| Test | Assert on |
|------|-----------|
| Successful multi-item checkout | Order exists, correct stock deducted |
| Invalid quantity (0, -1, 1.5) | 422 response, stock unchanged |
| Checkout at exact stock limit | Success, stock = 0 |
| Checkout above stock | 409/400, stock unchanged, no order |
| **Partial failure** (1 item short) | BOTH stocks unchanged, no order |
| Idempotent retry (same payload) | Same order ID returned, stock deducted once |
| Conflict retry (diff payload) | 409, no new order, stock unchanged |
