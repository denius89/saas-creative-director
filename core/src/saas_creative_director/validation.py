from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover - reported clearly at runtime
    Draft202012Validator = None  # type: ignore[assignment]

from .models import EvidenceStatus, ValidationIssue
from .orchestrator import GATES, STAGES, STAGE_OUTPUTS
from .workspace import gate_revision, read_json


SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas"
ARTIFACT_SCHEMAS = {
    "source-registry.json": "source-registry.schema.json",
    "evidence.json": "evidence.schema.json",
    "video-strategy.json": "video-strategy.schema.json",
    "reference-library.json": "reference-library.schema.json",
    "pattern-library.json": "pattern-library.schema.json",
    "storyboard.json": "storyboard.schema.json",
    "figma-manifest.json": "figma-manifest.schema.json",
    "motion-direction.json": "motion-direction.schema.json",
    "visual-qa.json": "visual-qa.schema.json",
    "context-pack.json": "context-pack.schema.json",
    "usage-event.json": "usage-event.schema.json",
}


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
    if not isinstance(project, dict):
        return [ValidationIssue("project.json", "root must be an object")]

    _schema_issues(project, "project.schema.json", "project.json", issues)
    _require(project, ("schema_version", "name", "stage", "gates"), "project", issues)
    stage = project.get("stage")
    if stage not in STAGES:
        issues.append(ValidationIssue("project.stage", f"must be one of {', '.join(STAGES)}"))

    artifacts = root / "artifacts"
    registry = _load_optional(artifacts / "source-registry.json", issues)
    evidence_doc = _load_optional(artifacts / "evidence.json", issues)
    _schema_issues(registry, "source-registry.schema.json", "artifacts/source-registry.json", issues)
    _schema_issues(evidence_doc, "evidence.schema.json", "artifacts/evidence.json", issues)

    sources: set[str] = set()
    for index, source in enumerate(registry.get("sources", [])):
        path = f"artifacts/source-registry.json.sources[{index}]"
        if not isinstance(source, dict):
            continue
        source_id = source.get("id")
        if source_id in sources:
            issues.append(ValidationIssue(f"{path}.id", f"duplicate source id: {source_id}"))
        if isinstance(source_id, str):
            sources.add(source_id)
        location = source.get("location")
        if not isinstance(location, str) or not location.strip() or location.strip().lower() in {"unknown", "n/a", "none"}:
            issues.append(ValidationIssue(f"{path}.location", "must locate the source with a URL or project-relative path"))

    evidence = evidence_doc.get("evidence", [])
    evidence_ids: set[str] = set()
    for index, item in enumerate(evidence):
        path = f"artifacts/evidence.json.evidence[{index}]"
        if not isinstance(item, dict):
            issues.append(ValidationIssue(path, "must be an object"))
            continue
        _require(item, ("id", "claim", "status", "source_ids"), path, issues)
        evidence_id = item.get("id")
        if evidence_id in evidence_ids:
            issues.append(ValidationIssue(f"{path}.id", f"duplicate evidence id: {evidence_id}"))
        if isinstance(evidence_id, str):
            evidence_ids.add(evidence_id)
        if item.get("status") not in {x.value for x in EvidenceStatus}:
            issues.append(ValidationIssue(f"{path}.status", "must be CONFIRMED, SUPPORTED, or HYPOTHESIS"))
        source_ids = item.get("source_ids", [])
        if isinstance(source_ids, list):
            for source_id in source_ids:
                if source_id not in sources:
                    issues.append(ValidationIssue(f"{path}.source_ids", f"unknown source: {source_id}"))
        if item.get("status") == "CONFIRMED" and not source_ids:
            issues.append(ValidationIssue(f"{path}.source_ids", "confirmed evidence needs a direct source"))

    for filename in artifacts.glob("*.json"):
        if filename.name in {"source-registry.json", "evidence.json"}:
            continue
        doc = _load_optional(filename, issues)
        schema_name = ARTIFACT_SCHEMAS.get(filename.name)
        if schema_name:
            _schema_issues(doc, schema_name, str(filename.relative_to(root)), issues)
        if filename.name == "storyboard.json":
            _validate_storyboard_semantics(doc, str(filename.relative_to(root)), issues)
        _walk_evidence_refs(doc, str(filename.relative_to(root)), evidence_ids, issues)

    visual_qa = root / "reviews" / "visual-qa.json"
    if visual_qa.exists():
        review = _load_optional(visual_qa, issues)
        _schema_issues(review, "visual-qa.schema.json", "reviews/visual-qa.json", issues)

    if stage in STAGES:
        _validate_stage_prerequisites(root, project, stage, issues)
        _validate_required_approvals(root, project, stage, issues)
    return _deduplicate(issues)


def validate_for_advance(root: Path, project: dict[str, Any] | None = None) -> list[ValidationIssue]:
    project = project or read_json(root / "project.json")
    issues = validate_project(root)
    stage = project.get("stage", "intake")
    if stage in STAGE_OUTPUTS:
        _validate_outputs(root, stage, issues)
    return _deduplicate(issues)


def validate_for_gate(root: Path, project: dict[str, Any], gate_name: str) -> list[ValidationIssue]:
    if gate_name not in GATES:
        return [ValidationIssue("gate", f"unknown gate: {gate_name}")]
    issues = validate_project(root)
    _validate_outputs(root, GATES[gate_name]["after"], issues)
    if gate_name == "production":
        _validate_production_qa(root, issues)
    return _deduplicate(issues)


def validate_for_export(root: Path) -> list[ValidationIssue]:
    """Validate manifest inputs without requiring the output being generated."""
    ignored_prefixes = (
        "artifacts/figma-manifest.json",
        "reviews/production-review",
        "project.gates.production",
    )
    issues = [
        issue for issue in validate_project(root)
        if not issue.path.startswith(ignored_prefixes)
    ]
    _validate_outputs(root, "storyboard", issues)
    visual = root / "artifacts" / "visual-direction.json"
    if not visual.exists() or not visual.read_bytes().strip():
        issues.append(ValidationIssue("artifacts/visual-direction.json", "a non-empty visual direction is required for export"))
    return _deduplicate(issues)


def _schema_issues(value: Any, schema_name: str, path: str, issues: list[ValidationIssue]) -> None:
    if Draft202012Validator is None:
        issues.append(ValidationIssue(path, "jsonschema>=4 is required for runtime contract validation"))
        return
    schema_path = SCHEMA_DIR / schema_name
    if not schema_path.exists():
        issues.append(ValidationIssue(path, f"contract schema is missing: {schema_name}"))
        return
    try:
        schema = read_json(schema_path)
    except (OSError, json.JSONDecodeError) as exc:
        issues.append(ValidationIssue(path, f"contract schema cannot be read: {exc}"))
        return
    for error in sorted(
        Draft202012Validator(schema).iter_errors(value),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    ):
        suffix = "".join(f"[{part}]" if isinstance(part, int) else f".{part}" for part in error.absolute_path)
        issues.append(ValidationIssue(f"{path}{suffix}", error.message))


def _validate_stage_prerequisites(root: Path, project: dict[str, Any], stage: str, issues: list[ValidationIssue]) -> None:
    current = STAGES.index(stage)
    for prior in STAGES[:current]:
        if prior in STAGE_OUTPUTS:
            _validate_outputs(root, prior, issues)


def _validate_required_approvals(root: Path, project: dict[str, Any], stage: str, issues: list[ValidationIssue]) -> None:
    current = STAGES.index(stage)
    for gate_name, rule in GATES.items():
        if current <= STAGES.index(rule["after"]):
            continue
        gate = project.get("gates", {}).get(gate_name, {})
        if gate.get("status") != "APPROVED":
            issues.append(ValidationIssue(f"project.gates.{gate_name}", "must be approved before this stage"))
            continue
        revision = gate_revision(root, project, gate_name)
        if gate.get("revision") != revision.revision:
            issues.append(ValidationIssue(f"project.gates.{gate_name}", "approval is stale for the current inputs"))


def _validate_outputs(root: Path, stage: str, issues: list[ValidationIssue]) -> None:
    for relative in STAGE_OUTPUTS.get(stage, ()):
        path = root / relative
        if not path.exists() or not path.is_file():
            issues.append(ValidationIssue(relative, f"required output for {stage} is missing"))
            continue
        if not path.read_bytes().strip():
            issues.append(ValidationIssue(relative, f"required output for {stage} is empty"))
            continue
        if path.suffix == ".json":
            try:
                value = read_json(path)
            except (OSError, json.JSONDecodeError) as exc:
                issues.append(ValidationIssue(relative, f"cannot be read: {exc}"))
                continue
            if (not relative.endswith(("source-registry.json", "evidence.json"))) and (
                value in ({}, []) or (isinstance(value, dict) and all(child in (None, "", [], {}) for child in value.values()))
            ):
                issues.append(ValidationIssue(relative, f"required output for {stage} has no substantive content"))
            if relative.endswith("source-registry.json") and (not isinstance(value, dict) or not value.get("sources")):
                issues.append(ValidationIssue(relative + ".sources", "at least one locatable source is required"))
            if relative.endswith("evidence.json") and (not isinstance(value, dict) or not value.get("evidence")):
                issues.append(ValidationIssue(relative + ".evidence", "at least one evidence record is required"))
            if relative.endswith("storyboard.json") and (not isinstance(value, dict) or not value.get("scenes")):
                issues.append(ValidationIssue(relative + ".scenes", "at least one scene is required"))
            schema_name = ARTIFACT_SCHEMAS.get(path.name)
            if schema_name:
                _schema_issues(value, schema_name, relative, issues)
            if relative.endswith("storyboard.json") and isinstance(value, dict):
                _validate_storyboard_semantics(value, relative, issues)


def _validate_production_qa(root: Path, issues: list[ValidationIssue]) -> None:
    path = root / "reviews" / "visual-qa.json"
    if not path.is_file():
        issues.append(ValidationIssue("reviews/visual-qa.json", "visual QA is required before production approval"))
        return
    try:
        review = read_json(path)
    except (OSError, json.JSONDecodeError) as exc:
        issues.append(ValidationIssue("reviews/visual-qa.json", f"cannot be read: {exc}"))
        return
    if not isinstance(review, dict):
        issues.append(ValidationIssue("reviews/visual-qa.json", "root must be an object"))
        return
    if review.get("status") == "BLOCKED":
        issues.append(ValidationIssue("reviews/visual-qa.json.status", "BLOCKED visual QA cannot be production-approved"))
    for index, finding in enumerate(review.get("findings", [])):
        if not isinstance(finding, dict):
            continue
        if finding.get("severity") == "blocker" and finding.get("status") == "open":
            issues.append(
                ValidationIssue(
                    f"reviews/visual-qa.json.findings[{index}]",
                    "open blocker must be resolved or explicitly accepted before production approval",
                )
            )


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


def _validate_storyboard_semantics(value: dict[str, Any], path: str, issues: list[ValidationIssue]) -> None:
    scenes = value.get("scenes", [])
    if not isinstance(scenes, list):
        return
    scene_ids = {scene.get("id") for scene in scenes if isinstance(scene, dict)}
    global_object_ids: set[str] = set()
    for index, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            continue
        scene_path = f"{path}.scenes[{index}]"
        duration = scene.get("duration_seconds")
        objects = scene.get("objects", [])
        object_ids = {
            item.get("semantic_id") for item in objects
            if isinstance(item, dict) and isinstance(item.get("semantic_id"), str)
        }
        duplicates = global_object_ids.intersection(object_ids)
        for object_id in sorted(duplicates):
            issues.append(ValidationIssue(f"{scene_path}.objects", f"duplicate semantic object id: {object_id}"))
        global_object_ids.update(object_ids)

        states = scene.get("states", [])
        state_ids = {item.get("id") for item in states if isinstance(item, dict)}
        for collection_name in ("states", "events", "transition_anchors"):
            collection = scene.get(collection_name, [])
            if not isinstance(collection, list):
                continue
            ids: set[str] = set()
            for item_index, item in enumerate(collection):
                if not isinstance(item, dict):
                    continue
                item_path = f"{scene_path}.{collection_name}[{item_index}]"
                item_id = item.get("id")
                if item_id in ids:
                    issues.append(ValidationIssue(f"{item_path}.id", f"duplicate id: {item_id}"))
                if isinstance(item_id, str):
                    ids.add(item_id)
                at_seconds = item.get("at_seconds")
                if isinstance(duration, (int, float)) and isinstance(at_seconds, (int, float)) and at_seconds > duration:
                    issues.append(ValidationIssue(f"{item_path}.at_seconds", "must not exceed scene duration"))
                event_duration = item.get("duration_seconds", 0)
                if (
                    isinstance(duration, (int, float)) and isinstance(at_seconds, (int, float))
                    and isinstance(event_duration, (int, float)) and at_seconds + event_duration > duration
                ):
                    issues.append(ValidationIssue(f"{item_path}.duration_seconds", "event must end within the scene"))
                for object_id in item.get("object_ids", []):
                    if object_id not in object_ids:
                        issues.append(ValidationIssue(f"{item_path}.object_ids", f"unknown semantic object id: {object_id}"))
                anchor_object = item.get("object_id")
                if anchor_object is not None and anchor_object not in object_ids:
                    issues.append(ValidationIssue(f"{item_path}.object_id", f"unknown semantic object id: {anchor_object}"))
                for state_field in ("state_id", "from_state_id", "to_state_id"):
                    state_id = item.get(state_field)
                    if state_id is not None and state_id not in state_ids:
                        issues.append(ValidationIssue(f"{item_path}.{state_field}", f"unknown state id: {state_id}"))
                target_scene = item.get("carry_to_scene_id")
                if target_scene is not None and target_scene not in scene_ids:
                    issues.append(ValidationIssue(f"{item_path}.carry_to_scene_id", f"unknown scene id: {target_scene}"))

        if value.get("schema_version") != "1.1" or scene.get("render_mode") != "panel-sequence":
            continue

        event_ids = {item.get("id") for item in scene.get("events", []) if isinstance(item, dict)}
        visual_event_ids = {
            item.get("id") for item in scene.get("events", [])
            if isinstance(item, dict) and item.get("type") != "hold"
        }
        presentations: dict[str, set[str]] = {}
        for object_index, obj in enumerate(objects):
            if not isinstance(obj, dict) or not isinstance(obj.get("semantic_id"), str):
                continue
            presentation_ids: set[str] = set()
            for presentation_index, presentation in enumerate(obj.get("presentations", [])):
                if not isinstance(presentation, dict):
                    continue
                presentation_id = presentation.get("id")
                presentation_path = f"{scene_path}.objects[{object_index}].presentations[{presentation_index}].id"
                if presentation_id in presentation_ids:
                    issues.append(ValidationIssue(presentation_path, f"duplicate presentation id: {presentation_id}"))
                if isinstance(presentation_id, str):
                    presentation_ids.add(presentation_id)
            presentations[obj["semantic_id"]] = presentation_ids

        panels = scene.get("panels", [])
        panel_ids: set[str] = set()
        represented_states: set[str] = set()
        represented_events: set[str] = set()
        previous_at = -1.0
        previous_objects: set[str] = set()
        for panel_index, panel in enumerate(panels):
            if not isinstance(panel, dict):
                continue
            panel_path = f"{scene_path}.panels[{panel_index}]"
            panel_id = panel.get("id")
            if panel_id in panel_ids:
                issues.append(ValidationIssue(f"{panel_path}.id", f"duplicate panel id: {panel_id}"))
            if isinstance(panel_id, str):
                panel_ids.add(panel_id)
            at_seconds = panel.get("at_seconds")
            hold_seconds = panel.get("hold_seconds")
            if isinstance(at_seconds, (int, float)) and not isinstance(at_seconds, bool):
                if at_seconds <= previous_at:
                    issues.append(ValidationIssue(f"{panel_path}.at_seconds", "panel times must be strictly increasing"))
                previous_at = float(at_seconds)
                if (
                    isinstance(hold_seconds, (int, float)) and not isinstance(hold_seconds, bool)
                    and isinstance(duration, (int, float)) and not isinstance(duration, bool)
                    and at_seconds + hold_seconds > duration
                ):
                    issues.append(ValidationIssue(f"{panel_path}.hold_seconds", "panel must end within the scene"))
            state_id = panel.get("state_id")
            if state_id not in state_ids:
                issues.append(ValidationIssue(f"{panel_path}.state_id", f"unknown state id: {state_id}"))
            elif isinstance(state_id, str):
                represented_states.add(state_id)
            for event_id in panel.get("event_ids", []):
                if event_id not in event_ids:
                    issues.append(ValidationIssue(f"{panel_path}.event_ids", f"unknown event id: {event_id}"))
                elif isinstance(event_id, str):
                    represented_events.add(event_id)
            layer_objects: set[str] = set()
            for layer_index, layer in enumerate(panel.get("layers", [])):
                if not isinstance(layer, dict):
                    continue
                layer_path = f"{panel_path}.layers[{layer_index}]"
                object_id = layer.get("object_id")
                presentation_id = layer.get("presentation_id")
                if object_id not in object_ids:
                    issues.append(ValidationIssue(f"{layer_path}.object_id", f"unknown semantic object id: {object_id}"))
                    continue
                if isinstance(object_id, str):
                    layer_objects.add(object_id)
                if presentation_id not in presentations.get(str(object_id), set()):
                    issues.append(ValidationIssue(f"{layer_path}.presentation_id", f"unknown presentation id for {object_id}: {presentation_id}"))
            focal_object_id = panel.get("focal_object_id")
            if focal_object_id not in layer_objects:
                issues.append(ValidationIssue(f"{panel_path}.focal_object_id", "focal object must be visible in panel layers"))
            if panel_index == 0 and panel.get("transition_from_previous") is not None:
                issues.append(ValidationIssue(f"{panel_path}.transition_from_previous", "first panel cannot transition from a previous panel"))
            if panel_index > 0 and panel.get("continuity") == "continuous" and not previous_objects.intersection(layer_objects):
                issues.append(ValidationIssue(f"{panel_path}.continuity", "continuous panels must share at least one logical object"))
            previous_objects = layer_objects

        missing_events = sorted(event_id for event_id in visual_event_ids if isinstance(event_id, str) and event_id not in represented_events)
        for event_id in missing_events:
            issues.append(ValidationIssue(f"{scene_path}.panels", f"visual event is not represented by any panel: {event_id}"))
        endpoint_states = {
            state_id
            for event in scene.get("events", []) if isinstance(event, dict)
            for state_id in (event.get("from_state_id"), event.get("to_state_id"))
            if isinstance(state_id, str)
        }
        for state_id in sorted(endpoint_states - represented_states):
            issues.append(ValidationIssue(f"{scene_path}.panels", f"event endpoint state is not represented by any panel: {state_id}"))


def _deduplicate(issues: list[ValidationIssue]) -> list[ValidationIssue]:
    seen: set[tuple[str, str, str]] = set()
    result: list[ValidationIssue] = []
    for issue in issues:
        key = (issue.path, issue.message, issue.severity)
        if key not in seen:
            result.append(issue)
            seen.add(key)
    return result
