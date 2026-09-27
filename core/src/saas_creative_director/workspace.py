from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import GateRevision
from .orchestrator import GATES, GATE_DEPENDENCIES, STAGE_OUTPUTS


ARTIFACT_FILES = (
    "source-registry.json",
    "evidence.json",
    "product-intelligence.json",
    "competitor-intelligence.json",
    "video-strategy.json",
    "reference-library.json",
    "narrative.json",
    "visual-direction.json",
    "storyboard.json",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def content_digest(value: Any) -> str:
    """Return a stable digest for JSON-like content or bytes."""
    if isinstance(value, bytes):
        payload = value
    else:
        payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def file_digest(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return "missing"
    if path.suffix == ".json":
        try:
            return content_digest(read_json(path))
        except (OSError, json.JSONDecodeError):
            pass
    return content_digest(path.read_bytes())


def project_decision_inputs(project: dict[str, Any]) -> dict[str, Any]:
    ignored = {"schema_version", "created_at", "stage", "gates", "workflow_revision"}
    return {key: value for key, value in project.items() if key not in ignored}


def gate_revision(root: Path, project: dict[str, Any], gate_name: str) -> GateRevision:
    if gate_name not in GATES:
        raise KeyError(f"Unknown gate: {gate_name}")
    output_paths = set(STAGE_OUTPUTS[GATES[gate_name]["after"]])
    artifact_digests: dict[str, str] = {}
    dependency_digests: dict[str, str] = {}
    for relative in GATE_DEPENDENCIES[gate_name]:
        if relative == "project.json#decision_inputs":
            digest = content_digest(project_decision_inputs(project))
        else:
            digest = file_digest(root / relative)
        target = artifact_digests if relative in output_paths else dependency_digests
        target[relative] = digest
    dependency_digest = content_digest(dependency_digests)
    revision = content_digest({"artifacts": artifact_digests, "dependencies": dependency_digests})
    return GateRevision(
        stage=GATES[gate_name]["after"],
        revision=revision,
        artifact_digests=artifact_digests,
        dependency_digests=dependency_digests,
        dependency_digest=dependency_digest,
    )


def refresh_gate_approvals(root: Path, project: dict[str, Any]) -> list[str]:
    """Mark approvals stale only when their own reviewed inputs changed."""
    stale: list[str] = []
    gates = project.setdefault("gates", {})
    for gate_name in GATES:
        gate = gates.setdefault(gate_name, default_gate())
        if gate.get("status") != "APPROVED":
            continue
        current = gate_revision(root, project, gate_name)
        if not gate.get("revision") or gate.get("revision") != current.revision:
            gate["status"] = "STALE"
            gate["stale_reason"] = "Reviewed artifacts or dependencies changed."
            gate["current_revision"] = current.revision
            write_json(root / "reviews" / "gates" / f"{gate_name}.json", {"gate": gate_name, **gate})
            stale.append(gate_name)
    if stale:
        write_json(root / "project.json", project)
    return stale


def default_gate() -> dict[str, Any]:
    return {
        "status": "PENDING",
        "approved_by": None,
        "approved_at": None,
        "notes": "",
        "revision": None,
        "artifact_digests": {},
        "dependency_digests": {},
        "dependency_digest": None,
        "provenance": None,
    }


def record_approval(
    root: Path,
    project: dict[str, Any],
    gate_name: str,
    approved_by: str,
    notes: str = "",
    provenance: str = "human_cli",
) -> dict[str, Any]:
    from .validation import validate_for_gate

    expected_stage = GATES[gate_name]["after"]
    if project.get("stage") != expected_stage:
        raise ValueError(f"The {gate_name} gate can only be approved at stage {expected_stage}.")
    issues = validate_for_gate(root, project, gate_name)
    if issues:
        first = issues[0]
        raise ValueError(f"Cannot approve: {first.path}: {first.message}")
    revision = gate_revision(root, project, gate_name)
    record = {
        "status": "APPROVED",
        "approved_by": approved_by,
        "approved_at": utc_now(),
        "notes": notes,
        "provenance": provenance,
        **revision.as_dict(),
    }
    project.setdefault("gates", {})[gate_name] = record
    write_json(root / "reviews" / "gates" / f"{gate_name}.json", {"gate": gate_name, **record})
    return record


def record_changes_requested(
    root: Path,
    project: dict[str, Any],
    gate_name: str,
    requested_by: str,
    notes: str,
    provenance: str = "human_cli",
) -> dict[str, Any]:
    if gate_name not in GATES:
        raise KeyError(f"Unknown gate: {gate_name}")
    expected_stage = GATES[gate_name]["after"]
    if project.get("stage") != expected_stage:
        raise ValueError(f"The {gate_name} gate can only be reviewed at stage {expected_stage}.")
    if not notes.strip():
        raise ValueError("Change-request notes are required.")
    record = default_gate()
    record.update({
        "status": "CHANGES_REQUESTED",
        "approved_by": requested_by,
        "approved_at": utc_now(),
        "notes": notes,
        "provenance": provenance,
    })
    project.setdefault("gates", {})[gate_name] = record
    write_json(root / "reviews" / "gates" / f"{gate_name}.json", {"gate": gate_name, **record})
    return record


def initialize_project(root: Path, name: str) -> None:
    if root.exists() and any(root.iterdir()):
        raise FileExistsError(f"Refusing to initialize non-empty directory: {root}")
    (root / "inputs").mkdir(parents=True, exist_ok=True)
    (root / "artifacts").mkdir(parents=True, exist_ok=True)
    (root / "reviews").mkdir(parents=True, exist_ok=True)
    (root / "inputs" / ".gitkeep").touch()

    project = {
        "schema_version": "0.5",
        "language": "ru",
        "name": name,
        "created_at": utc_now(),
        "stage": "intake",
        "business_goal": "",
        "channel": "",
        "duration_seconds": None,
        "gates": {key: default_gate() for key in ("strategy", "creative_direction", "production")},
    }
    write_json(root / "project.json", project)
    write_json(root / "artifacts" / "source-registry.json", {"sources": []})
    write_json(root / "artifacts" / "evidence.json", {"evidence": []})
    (root / "artifacts" / "open-questions.md").write_text(
        "# Open questions\n\n- Add questions whose answers could materially change strategy.\n",
        encoding="utf-8",
    )


def load_project(root: Path) -> dict[str, Any]:
    project = read_json(root / "project.json")
    # 0.5 projects remain readable. Missing fields are added in memory and are
    # persisted only by the next explicit workflow operation.
    project.setdefault("schema_version", "0.5")
    gates = project.setdefault("gates", {})
    for gate_name in GATES:
        merged = default_gate()
        merged.update(gates.get(gate_name, {}))
        gates[gate_name] = merged
    return project
