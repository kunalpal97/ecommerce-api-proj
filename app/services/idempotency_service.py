"""
services/idempotency_service.py — Idempotency Key Management
=============================================================
Handles the second release-blocking bug:
  "A retry after a timeout might create a duplicate order."

How idempotency works in this API:
  1. Client generates a unique key (UUID) per checkout ATTEMPT.
  2. Client sends: POST /checkout  Idempotency-Key: <key>
  3. Server checks if this key was seen before:
       - Never seen        → process normally, store key + result.
       - Seen + same body  → return stored result (no second order).
       - Seen + diff body  → reject with 409 (conflict).

Payload hashing:
  We hash the checkout request body to detect "same key, different payload."
  SHA-256 is used (not for security — for fast, deterministic comparison).
  The hash is stored alongside the order_id when first processed.

Storage structure in _idempotency:
    {
        "abc-123-key": {
            "payload_hash": "sha256hex...",
            "order_id": "ord_xyz789"
        }
    }
"""

import hashlib
import json

from app.exceptions.handlers import IdempotencyConflictError
from app.store.database import get_idempotency_db


class IdempotencyService:
    """Manages idempotency key lookup, storage, and conflict detection."""

    def __init__(self) -> None:
        self._db = get_idempotency_db

    def _hash_payload(self, payload: dict) -> str:
        """
        Produce a stable SHA-256 hash of the checkout payload.

        json.dumps with sort_keys=True ensures the same payload always
        produces the same hash regardless of key order in the dict.
        """
        serialized = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()

    def check_and_get_existing(self, key: str, payload: dict) -> str | None:
        """
        Check if an idempotency key has been used before.

        Returns:
            The existing order_id if this is a valid replay (same payload).
            None if this is a brand-new key.

        Raises:
            IdempotencyConflictError: if the key exists but payload differs.
        """
        db = self._db()
        payload_hash = self._hash_payload(payload)

        if key not in db:
            return None   # Brand new key — proceed with checkout

        stored = db[key]

        if stored["payload_hash"] == payload_hash:
            # Same key + same payload = idempotent replay
            return stored["order_id"]
        else:
            # Same key + different payload = conflict
            raise IdempotencyConflictError(key)

    def store(self, key: str, payload: dict, order_id: str) -> None:
        """
        Persist an idempotency key after a successful checkout.

        Called immediately after the order is created.

        Args:
            key:      The Idempotency-Key from the request header.
            payload:  The checkout request body (used for hash comparison).
            order_id: The ID of the order just created.
        """
        self._db()[key] = {
            "payload_hash": self._hash_payload(payload),
            "order_id": order_id,
        }


# ── Module-level singleton ─────────────────────────────────────────────────
idempotency_service = IdempotencyService()
