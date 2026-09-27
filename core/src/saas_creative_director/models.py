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
    STALE = "STALE"


class BillingMode(str, Enum):
    SUBSCRIPTION = "subscription"
    USAGE_CREDITS = "usage_credits"
    API = "api"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    message: str
    severity: str = "error"

    def as_dict(self) -> dict[str, str]:
        return {"path": self.path, "message": self.message, "severity": self.severity}


@dataclass(frozen=True)
class GateRevision:
    stage: str
    revision: str
    artifact_digests: dict[str, str]
    dependency_digests: dict[str, str]
    dependency_digest: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "revision": self.revision,
            "artifact_digests": dict(sorted(self.artifact_digests.items())),
            "dependency_digests": dict(sorted(self.dependency_digests.items())),
            "dependency_digest": self.dependency_digest,
        }


def ensure_dict(value: Any, path: str, issues: list[ValidationIssue]) -> dict[str, Any]:
    if not isinstance(value, dict):
        issues.append(ValidationIssue(path, "must be an object"))
        return {}
    return value
