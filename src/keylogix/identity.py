"""Event and session identity.

event_id is UUID4. Collision within a factory is treated as an error, not
silently reused.
"""

from __future__ import annotations

import uuid
from typing import Callable, Optional, Set


class IdentityError(ValueError):
    pass


class IdentityFactory:
    def __init__(self, uuid_fn: Optional[Callable[[], uuid.UUID]] = None) -> None:
        self._uuid_fn = uuid_fn or uuid.uuid4
        self._issued: Set[str] = set()

    def new_id(self) -> str:
        for _ in range(8):
            value = str(self._uuid_fn())
            if value in self._issued:
                continue
            self._issued.add(value)
            return value
        raise IdentityError("unable to allocate a unique identifier")

    def register(self, existing: str) -> str:
        if not existing or not isinstance(existing, str):
            raise IdentityError("identifier must be a non-empty string")
        if existing in self._issued:
            raise IdentityError("identifier collision: {0}".format(existing))
        self._issued.add(existing)
        return existing

    def seen(self, value: str) -> bool:
        return value in self._issued

    def issued_count(self) -> int:
        return len(self._issued)


class SequentialUUID:
    """Deterministic UUID-like values for tests. Not RFC 4122 random."""

    def __init__(self, prefix: str = "00000000-0000-4000-8000-") -> None:
        self._prefix = prefix
        self._n = 0

    def __call__(self) -> uuid.UUID:
        self._n += 1
        hex_part = "{0:012x}".format(self._n)
        return uuid.UUID(self._prefix + hex_part)
