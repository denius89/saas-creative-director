from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class EvidenceStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    SUPPORTED = "SUPPORTED"
    HYPOTHESIS = "HYPOTHESIS"


class GateStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    message: str
    severity: str = "error"

    def as_dict(self) -> dict[str, str]:
        return {"path": self.path, "message": self.message, "severity": self.severity}


def ensure_dict(value: Any, path: str, issues: list[ValidationIssue]) -> dict[str, Any]:
    if not isinstance(value, dict):
        issues.append(ValidationIssue(path, "must be an object"))
        return {}
    return value
