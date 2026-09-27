from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .cache import ArtifactCache, make_cache_key
from .orchestrator import STAGES
from .workspace import content_digest, file_digest, load_project, project_decision_inputs, read_json, write_json


STAGE_CONTEXT = {
    "intake": ("artifacts/source-registry.json", "artifacts/evidence.json", "artifacts/open-questions.md"),
    "product_intelligence": ("artifacts/product-intelligence.json", "artifacts/open-questions.md"),
    "competitor_intelligence": ("artifacts/product-intelligence.json", "artifacts/competitor-intelligence.json"),
    "video_strategy": ("artifacts/product-intelligence.json", "artifacts/competitor-intelligence.json", "artifacts/video-strategy.json"),
    "reference_research": ("artifacts/video-strategy.json", "artifacts/reference-library.json", "artifacts/pattern-library.json"),
    "narrative": ("artifacts/video-strategy.json", "artifacts/reference-library.json", "artifacts/pattern-library.json", "artifacts/narrative.json"),
    "visual_direction": ("artifacts/narrative.json", "artifacts/reference-library.json", "artifacts/pattern-library.json", "artifacts/motion-direction.json", "artifacts/visual-direction.json"),
    "storyboard": ("artifacts/narrative.json", "artifacts/motion-direction.json", "artifacts/visual-direction.json", "artifacts/storyboard.json"),
    "figma_wireframes": ("artifacts/motion-direction.json", "artifacts/visual-direction.json", "artifacts/storyboard.json", "artifacts/figma-manifest.json"),
    "production_review": ("artifacts/storyboard.json", "artifacts/figma-manifest.json", "reviews/visual-qa.json", "reviews/production-review.md"),
    "complete": ("artifacts/storyboard.json", "artifacts/figma-manifest.json", "reviews/visual-qa.json", "reviews/production-review.md"),
}

CHARS_PER_TOKEN_ESTIMATE = 4
_POLICY_INTEGER_FIELDS = (
    "stage_context_target_tokens",
    "stage_context_warning_tokens",
    "max_tool_retries",
    "max_repair_passes",
    "retrieval_top_k",
    "max_figma_qa_passes",
)


def load_execution_policy() -> dict[str, Any]:
    """Load the protected local policy, falling back to the managed factory preset."""
    product_root = Path(__file__).resolve().parents[3]
    candidates = (product_root / "config" / "local.json", product_root / "core" / "defaults" / "config" / "local.json")
    policy: Any = None
    for path in candidates:
        if path.is_file():
            value = read_json(path)
            if isinstance(value, dict) and isinstance(value.get("execution_policy"), dict):
                policy = value["execution_policy"]
                break
    if not isinstance(policy, dict):
        raise ValueError("execution_policy is missing from local and factory configuration")
    if policy.get("enforcement_scope") != "advisory":
        raise ValueError("execution_policy.enforcement_scope must be advisory")
    if policy.get("auto_enable_usage_credits") is not False:
        raise ValueError("execution_policy may not enable Usage credits")
    if policy.get("billing_mode") not in {"subscription", "usage_credits", "api", "unknown"}:
        raise ValueError("execution_policy.billing_mode is invalid")
    for field in _POLICY_INTEGER_FIELDS:
        value = policy.get(field)
        minimum = 0 if field.startswith("max_") else 1
        if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
            raise ValueError(f"execution_policy.{field} must be an integer >= {minimum}")
    if policy["stage_context_warning_tokens"] < policy["stage_context_target_tokens"]:
        raise ValueError("stage context warning must not be lower than its target")
    target_usd = policy.get("target_usd")
    if target_usd is not None and (not isinstance(target_usd, (int, float)) or isinstance(target_usd, bool) or target_usd < 0):
        raise ValueError("execution_policy.target_usd must be non-negative or null")
    return dict(policy)


def policy_snapshot(policy: dict[str, Any]) -> dict[str, Any]:
    return {
        "enforcement_scope": "advisory",
        "billing_mode": policy["billing_mode"],
        "auto_enable_usage_credits": False,
        **{field: policy[field] for field in _POLICY_INTEGER_FIELDS},
        "target_usd": policy.get("target_usd"),
        "chars_per_token_estimate": CHARS_PER_TOKEN_ESTIMATE,
    }


def build_context_pack(
    root: Path,
    stage: str,
    scene_ids: list[str] | None = None,
    max_chars: int | None = None,
    execution_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a stable, bounded packet while preserving cited evidence and sources."""
    if stage not in STAGES:
        raise ValueError(f"Unknown stage: {stage}")
    policy = execution_policy or load_execution_policy()
    context_limit = max_chars if max_chars is not None else policy["stage_context_target_tokens"] * CHARS_PER_TOKEN_ESTIMATE
    if not isinstance(context_limit, int) or isinstance(context_limit, bool) or context_limit <= 0:
        raise ValueError("max_chars must be a positive integer")
    selected_scenes = sorted(set(scene_ids or []))
    documents: dict[str, Any] = {}
    manifest: list[dict[str, str]] = []
    omitted: list[str] = []
    evidence_ids: set[str] = set()

    for relative in STAGE_CONTEXT[stage]:
        path = root / relative
        if not path.exists() or not path.is_file():
            continue
        manifest.append({"path": relative, "digest": file_digest(path)})
        if path.suffix == ".json":
            value = read_json(path)
            if selected_scenes and relative.endswith("storyboard.json") and isinstance(value, dict):
                value = dict(value)
                value["scenes"] = [
                    scene for scene in value.get("scenes", [])
                    if isinstance(scene, dict) and scene.get("id") in selected_scenes
                ]
        else:
            value = path.read_text(encoding="utf-8")
        evidence_ids.update(_collect_ids(value, "evidence_ids"))
        candidate = {**documents, relative: value}
        if _json_size(candidate) <= context_limit:
            documents[relative] = value
        else:
            omitted.append(relative)

    evidence_doc = _optional_json(root / "artifacts" / "evidence.json", {"evidence": []})
    all_evidence = [item for item in evidence_doc.get("evidence", []) if isinstance(item, dict)]
    if not evidence_ids and stage in {"intake", "product_intelligence", "competitor_intelligence", "video_strategy"}:
        evidence = all_evidence
    else:
        evidence = [item for item in all_evidence if item.get("id") in evidence_ids]
    evidence.sort(key=lambda item: str(item.get("id", "")))

    source_ids = {source_id for item in evidence for source_id in item.get("source_ids", [])}
    registry = _optional_json(root / "artifacts" / "source-registry.json", {"sources": []})
    sources = [
        source for source in registry.get("sources", [])
        if isinstance(source, dict) and (source.get("id") in source_ids or stage == "intake")
    ]
    sources.sort(key=lambda item: str(item.get("id", "")))
    manifest.extend(
        {"path": relative, "digest": file_digest(root / relative)}
        for relative in ("artifacts/evidence.json", "artifacts/source-registry.json")
        if (root / relative).exists() and relative not in {item["path"] for item in manifest}
    )
    manifest.sort(key=lambda item: item["path"])

    project = load_project(root)
    decision_digest = content_digest(project_decision_inputs(project))
    manifest.append({"path": "project.json#decision_inputs", "digest": decision_digest})
    manifest.sort(key=lambda item: item["path"])
    project_id = content_digest({"root": root.name, "name": project.get("name")})[:16]
    revision_material = {"stage": stage, "scene_ids": selected_scenes, "artifacts": manifest}
    pack = {
        "schema_version": "1.0",
        "project_id": project_id,
        "stage": stage,
        "revision": content_digest(revision_material),
        "scene_ids": selected_scenes,
        "artifacts": manifest,
        "documents": documents,
        "evidence": evidence,
        "sources": sources,
        "omitted": sorted(omitted),
        "warnings": [],
        "execution_policy": policy_snapshot(policy),
    }
    if _json_size({"evidence": evidence, "sources": sources}) > context_limit:
        pack["warnings"].append("Required evidence exceeds the context target; it was preserved for traceability.")
    if omitted:
        pack["warnings"].append("Some optional documents were omitted by the advisory context limit.")
    return pack


def save_context_pack(root: Path, pack: dict[str, Any]) -> Path:
    scene_suffix = "-" + content_digest(pack.get("scene_ids", []))[:8] if pack.get("scene_ids") else ""
    path = root / "artifacts" / "context-packs" / f"{pack['stage']}{scene_suffix}-{pack['revision'][:12]}.json"
    write_json(path, pack)
    return path


def build_checkpoint(
    root: Path,
    next_actions: list[str] | None = None,
    unresolved: list[str] | None = None,
) -> dict[str, Any]:
    project = load_project(root)
    artifact_paths = sorted({path for values in STAGE_CONTEXT.values() for path in values if (root / path).is_file()})
    pointers = [{"path": path, "digest": file_digest(root / path)} for path in artifact_paths]
    gates = {
        name: {"status": gate.get("status"), "revision": gate.get("revision")}
        for name, gate in sorted(project.get("gates", {}).items())
    }
    checkpoint = {
        "schema_version": "1.0",
        "project_id": content_digest({"root": root.name, "name": project.get("name")})[:16],
        "stage": project.get("stage"),
        "gates": gates,
        "artifacts": pointers,
        "next_actions": list(next_actions or []),
        "unresolved": list(unresolved or []),
    }
    checkpoint["revision"] = content_digest(checkpoint)
    return checkpoint


def save_checkpoint(root: Path, checkpoint: dict[str, Any]) -> Path:
    path = root / "reviews" / "checkpoint.json"
    write_json(path, checkpoint)
    return path


def prepare_stage_runtime(
    root: Path,
    stage: str | None = None,
    scene_ids: list[str] | None = None,
    next_actions: list[str] | None = None,
    unresolved: list[str] | None = None,
) -> dict[str, Any]:
    """Materialize bounded context and a resumable checkpoint for one stage."""
    project = load_project(root)
    selected_stage = stage or str(project.get("stage", "intake"))
    policy = load_execution_policy()
    pack = build_context_pack(root, selected_stage, scene_ids, execution_policy=policy)
    dependencies = {item["path"]: item["digest"] for item in pack["artifacts"]}
    key = make_cache_key(
        {"kind": "context-pack", "stage": selected_stage, "scene_ids": pack["scene_ids"], "revision": pack["revision"]},
        {"context_contract": "1.0"},
    )
    cache = ArtifactCache(root / ".scd" / "cache", pack["project_id"])
    cached = cache.get(key, dependencies)
    cache_hit = isinstance(cached, dict) and cached.get("revision") == pack["revision"]
    if cache_hit:
        pack = cached
    else:
        cache.put(key, pack, dependencies)
    context_path = save_context_pack(root, pack)

    checkpoint = build_checkpoint(root, next_actions, unresolved)
    checkpoint["context_pack"] = {
        "path": str(context_path.relative_to(root)),
        "revision": pack["revision"],
        "cache_hit": cache_hit,
    }
    checkpoint["execution_policy"] = policy_snapshot(policy)
    checkpoint.pop("revision", None)
    checkpoint["revision"] = content_digest(checkpoint)
    checkpoint_path = save_checkpoint(root, checkpoint)
    return {
        "project_id": pack["project_id"],
        "stage": selected_stage,
        "context_path": context_path,
        "checkpoint_path": checkpoint_path,
        "context_revision": pack["revision"],
        "checkpoint_revision": checkpoint["revision"],
        "cache_hit": cache_hit,
        "execution_policy": policy_snapshot(policy),
    }


def _collect_ids(value: Any, key: str) -> set[str]:
    result: set[str] = set()
    if isinstance(value, dict):
        for child_key, child in value.items():
            if child_key == key and isinstance(child, list):
                result.update(item for item in child if isinstance(item, str))
            else:
                result.update(_collect_ids(child, key))
    elif isinstance(value, list):
        for child in value:
            result.update(_collect_ids(child, key))
    return result


def _optional_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    value = read_json(path)
    return value if isinstance(value, dict) else default


def _json_size(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
