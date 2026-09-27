from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import BillingMode
from .workspace import content_digest


NULLABLE_COUNTS = (
    "input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens",
    "tool_calls", "source_reads", "searches", "screenshots", "retries",
    "cache_hits", "cache_misses", "elapsed_ms", "estimated_usd",
)
ALLOWED_FIELDS = {
    "event_id", "project_id", "run_id", "stage", "scene_ids", "billing_mode",
    "event_kind", "usage_source", "estimated", "model", "started_at", "finished_at",
    "price_snapshot_id", *NULLABLE_COUNTS,
}


def normalize_usage_event(event: dict[str, Any]) -> dict[str, Any]:
    """Drop content/tool arguments/secrets and preserve unknown numbers as null."""
    clean = {key: event[key] for key in ALLOWED_FIELDS if key in event}
    for required in ("project_id", "run_id", "stage"):
        if not isinstance(clean.get(required), str) or not clean[required]:
            raise ValueError(f"{required} is required")
    try:
        clean["billing_mode"] = BillingMode(clean.get("billing_mode", "unknown")).value
    except ValueError as exc:
        raise ValueError("invalid billing_mode") from exc
    clean.setdefault("usage_source", "unknown")
    if clean["usage_source"] not in {"provider_reported", "host_reported", "user_reported", "estimated", "unknown"}:
        raise ValueError("invalid usage_source")
    clean.setdefault("estimated", clean["usage_source"] == "estimated")
    if not isinstance(clean["estimated"], bool):
        raise ValueError("estimated must be a boolean")
    if clean["usage_source"] == "estimated" and not clean["estimated"]:
        raise ValueError("estimated usage_source requires estimated=true")
    clean.setdefault("event_kind", "model_usage")
    if clean["event_kind"] not in {"model_usage", "stage_boundary"}:
        raise ValueError("invalid event_kind")
    clean.setdefault("model", None)
    clean.setdefault("started_at", None)
    clean.setdefault("finished_at", None)
    clean.setdefault("price_snapshot_id", None)
    for field in ("model", "started_at", "finished_at", "price_snapshot_id"):
        if clean[field] is not None and (not isinstance(clean[field], str) or not clean[field]):
            raise ValueError(f"{field} must be a non-empty string or null")
    scene_ids = clean.get("scene_ids", [])
    if not isinstance(scene_ids, list) or any(not isinstance(item, str) or not item for item in scene_ids):
        raise ValueError("scene_ids must be an array of non-empty strings")
    clean["scene_ids"] = sorted(set(scene_ids))
    for field in NULLABLE_COUNTS:
        value = clean.get(field)
        if value is not None and (not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0):
            raise ValueError(f"{field} must be non-negative or null")
        if field != "estimated_usd" and value is not None and not isinstance(value, int):
            raise ValueError(f"{field} must be an integer or null")
        clean[field] = value
    if clean["estimated_usd"] is not None:
        if clean["billing_mode"] not in {"api", "usage_credits"}:
            raise ValueError("estimated_usd is not meaningful for subscription or unknown billing")
        if not clean["estimated"] or not clean.get("price_snapshot_id"):
            raise ValueError("estimated_usd requires estimated=true and price_snapshot_id")
    if "event_id" not in clean:
        clean["event_id"] = content_digest(clean)
    return {key: clean[key] for key in sorted(clean)}


def append_usage_event(path: Path, event: dict[str, Any]) -> bool:
    clean = normalize_usage_event(event)
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip() and json.loads(line).get("event_id") == clean["event_id"]:
                return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(clean, ensure_ascii=False, sort_keys=True) + "\n")
    return True


def summarize_usage(path: Path) -> dict[str, Any]:
    events = [] if not path.exists() else [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    model_events = [event for event in events if event.get("event_kind", "model_usage") == "model_usage"]
    summary: dict[str, Any] = {
        "events": len(events),
        "model_usage_events": len(model_events),
        "stage_boundaries": sum(event.get("event_kind") == "stage_boundary" for event in events),
    }
    for field in NULLABLE_COUNTS:
        known = [event[field] for event in model_events if event.get(field) is not None]
        summary[field] = sum(known) if known and len(known) == len(model_events) else None
    return summary
