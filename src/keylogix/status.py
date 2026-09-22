"""Canonical failure/success semantics.

Statuses match docs/SPECIFICATION.md §20 plus UNAVAILABLE_CONTEXT from
CONTEXT.md. Do not collapse distinct states into generic success.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Mapping, Optional, TypeVar

T = TypeVar("T")


class Status(str, Enum):
    SUCCESS_WITH_DATA = "SUCCESS_WITH_DATA"
    SUCCESS_NO_DATA = "SUCCESS_NO_DATA"
    INVALID_INPUT = "INVALID_INPUT"
    UNREACHABLE = "UNREACHABLE"
    TIMEOUT = "TIMEOUT"
    PROVIDER_FAILURE = "PROVIDER_FAILURE"
    PARTIAL = "PARTIAL"
    INCONCLUSIVE = "INCONCLUSIVE"
    SKIPPED = "SKIPPED"
    INTERRUPTED = "INTERRUPTED"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    UNAVAILABLE_CONTEXT = "UNAVAILABLE_CONTEXT"


_SUCCESS = frozenset({Status.SUCCESS_WITH_DATA, Status.SUCCESS_NO_DATA})
_COMPLETED_WITH_PAYLOAD = frozenset(
    {Status.SUCCESS_WITH_DATA, Status.PARTIAL, Status.UNAVAILABLE_CONTEXT}
)


@dataclass(frozen=True)
class Result:
    """Operation outcome. `ok` means the operation completed as requested."""

    status: Status
    value: Any = None
    message: str = ""
    details: Mapping[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status in _SUCCESS

    @property
    def has_data(self) -> bool:
        if self.status == Status.SUCCESS_NO_DATA:
            return False
        if self.status in _COMPLETED_WITH_PAYLOAD:
            return self.value is not None
        return False

    @property
    def completed(self) -> bool:
        """True when the operation ran to a terminal state that is not skip/interrupt.

        PARTIAL and INCONCLUSIVE are completed-but-not-fully-successful.
        """
        return self.status not in {
            Status.SKIPPED,
            Status.INTERRUPTED,
            Status.OUT_OF_SCOPE,
        }

    def to_dict(self) -> Dict[str, Any]:
        val = self.value
        if hasattr(val, "to_dict") and callable(val.to_dict):
            val = val.to_dict()
        elif isinstance(val, (list, tuple)):
            val = [item.to_dict() if hasattr(item, "to_dict") and callable(item.to_dict) else item for item in val]
        return {
            "status": self.status.value,
            "value": val,
            "message": self.message,
            "details": dict(self.details),
        }

    @staticmethod
    def success(
        value: Any,
        message: str = "",
        details: Optional[Mapping[str, Any]] = None,
    ) -> "Result":
        if value is None:
            return Result(
                Status.SUCCESS_NO_DATA,
                None,
                message or "completed with no data",
                dict(details or {}),
            )
        return Result(Status.SUCCESS_WITH_DATA, value, message, dict(details or {}))

    @staticmethod
    def no_data(
        message: str = "completed with no data",
        details: Optional[Mapping[str, Any]] = None,
    ) -> "Result":
        return Result(Status.SUCCESS_NO_DATA, None, message, dict(details or {}))

    @staticmethod
    def invalid(message: str, details: Optional[Mapping[str, Any]] = None) -> "Result":
        return Result(Status.INVALID_INPUT, None, message, dict(details or {}))

    @staticmethod
    def failure(
        status: Status,
        message: str,
        value: Any = None,
        details: Optional[Mapping[str, Any]] = None,
    ) -> "Result":
        if status in _SUCCESS:
            raise ValueError("failure() cannot be used with a success status")
        return Result(status, value, message, dict(details or {}))
