from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from .models import EvidenceStatus, ValidationIssue
from .orchestrator import STAGES
from .workspace import read_json


def _require(obj: dict[str, Any], fields: Iterable[str], path: str, issues: list[ValidationIssue]) -> None:
    for field in fields:
        if field not in obj or obj[field] in (None, "", []):
            issues.append(ValidationIssue(f"{path}.{field}", "is required"))


def validate_project(root: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    project_file = root / "project.json"
    if not project_file.exists():
        return [ValidationIssue("project.json", "file is missing")]
    try:
        project = read_json(project_file)
    except (OSError, json.JSONDecodeError) as exc:
        return [ValidationIssue("project.json", f"cannot be read: {exc}")]

    _require(project, ("schema_version", "name", "stage", "gates"), "project", issues)
    if project.get("stage") not in STAGES:
        issues.append(ValidationIssue("project.stage", f"must be one of {', '.join(STAGES)}"))

    artifacts = root / "artifacts"
    registry = _load_optional(artifacts / "source-registry.json", issues)
    evidence_doc = _load_optional(artifacts / "evidence.json", issues)
    sources = {x.get("id") for x in registry.get("sources", []) if isinstance(x, dict)}
    evidence = evidence_doc.get("evidence", [])
    evidence_ids: set[str] = set()
    for index, item in enumerate(evidence):
        path = f"artifacts/evidence.json.evidence[{index}]"
        if not isinstance(item, dict):
            issues.append(ValidationIssue(path, "must be an object"))
            continue
        _require(item, ("id", "claim", "status", "source_ids"), path, issues)
        evidence_ids.add(item.get("id"))
        if item.get("status") not in {x.value for x in EvidenceStatus}:
            issues.append(ValidationIssue(f"{path}.status", "must be CONFIRMED, SUPPORTED, or HYPOTHESIS"))
        for source_id in item.get("source_ids", []):
            if source_id not in sources:
                issues.append(ValidationIssue(f"{path}.source_ids", f"unknown source: {source_id}"))
        if item.get("status") == "CONFIRMED" and not item.get("source_ids"):
            issues.append(ValidationIssue(f"{path}.source_ids", "confirmed evidence needs a direct source"))

    for filename in artifacts.glob("*.json"):
        if filename.name in {"source-registry.json", "evidence.json"}:
            continue
        doc = _load_optional(filename, issues)
        _walk_evidence_refs(doc, str(filename.relative_to(root)), evidence_ids, issues)
    return issues


def _load_optional(path: Path, issues: list[ValidationIssue]) -> dict[str, Any]:
    if not path.exists():
        issues.append(ValidationIssue(str(path.name), "file is missing"))
        return {}
    try:
        value = read_json(path)
    except (OSError, json.JSONDecodeError) as exc:
        issues.append(ValidationIssue(str(path.name), f"cannot be read: {exc}"))
        return {}
    if not isinstance(value, dict):
        issues.append(ValidationIssue(str(path.name), "root must be an object"))
        return {}
    return value


def _walk_evidence_refs(value: Any, path: str, known: set[str], issues: list[ValidationIssue]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key == "evidence_ids" and isinstance(child, list):
                for evidence_id in child:
                    if evidence_id not in known:
                        issues.append(ValidationIssue(child_path, f"unknown evidence id: {evidence_id}"))
            else:
                _walk_evidence_refs(child, child_path, known, issues)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk_evidence_refs(child, f"{path}[{index}]", known, issues)
