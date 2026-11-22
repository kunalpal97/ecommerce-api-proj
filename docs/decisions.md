# Architecture Decision Records (ADRs)

## ADR-001: Separation of Cart and Checkout Flow
- **Decision:** Split into `POST /cart` -> `POST /cart/{id}/items` -> `POST /checkout`.
- **Reason:** Real-world ecommerce decoupling. Checking stock at add-to-cart is an anti-pattern because stock can change between adding an item and making payment. Stock must be validated atomically at checkout time.

## ADR-002: In-Memory Storage via Repository Pattern
- **Decision:** Use Python dictionaries wrapped inside dedicated Repository classes (`ProductRepository`, `CartRepository`, `OrderRepository`).
- **Reason:** Challenge allows in-memory storage. The Repository Pattern ensures zero coupling between business logic and storage. Swapping in-memory storage for PostgreSQL or MongoDB requires touching only the repository layer.

## ADR-003: Atomic Checkout via Two-Phase Mutation
- **Decision:** Split checkout into Phase 1 (validate all items) and Phase 2 (deduct all items), protected by a `threading.Lock`.
- **Reason:** Prevents race conditions and guarantees all-or-nothing transactions. If any item is out of stock, validation raises `OutOfStockError` before any stock is modified.

## ADR-004: Idempotency Key via HTTP Header
- **Decision:** Enforce `Idempotency-Key` as an HTTP Header and verify payload integrity via deterministic SHA-256 hash.
- **Reason:** Adheres to RFC 7231 / IETF Idempotency Key specifications used by industry leaders like Stripe and Shopify. Same key + same payload replays the cached order; same key + different payload is rejected with 409 Conflict.
