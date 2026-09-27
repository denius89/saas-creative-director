from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .workspace import content_digest, read_json, write_json


def make_cache_key(inputs: dict[str, Any], versions: dict[str, str] | None = None) -> str:
    return content_digest({"inputs": inputs, "versions": versions or {}})


class ArtifactCache:
    """A project-isolated cache whose hits require exact dependency digests."""

    def __init__(self, base: Path, project_id: str) -> None:
        if not project_id:
            raise ValueError("project_id is required")
        self.base = base
        self.project_id = project_id
        self.scope = content_digest({"project_id": project_id})[:24]
        self.root = base / self.scope

    def put(self, key: str, value: Any, dependencies: dict[str, str]) -> Path:
        _validate_key(key)
        path = self.root / f"{key}.json"
        write_json(path, {
            "schema_version": "1.0",
            "project_scope": self.scope,
            "key": key,
            "dependencies": dict(sorted(dependencies.items())),
            "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "value": value,
        })
        return path

    def get(self, key: str, dependencies: dict[str, str]) -> Any | None:
        _validate_key(key)
        path = self.root / f"{key}.json"
        if not path.exists():
            return None
        try:
            entry = read_json(path)
        except (OSError, ValueError):
            return None
        if entry.get("project_scope") != self.scope:
            return None
        if entry.get("dependencies") != dict(sorted(dependencies.items())):
            return None
        return entry.get("value")

    def invalidate(self, dependency_names: set[str]) -> int:
        count = 0
        if not self.root.exists():
            return count
        for path in self.root.glob("*.json"):
            try:
                entry = read_json(path)
            except (OSError, ValueError):
                path.unlink(missing_ok=True)
                count += 1
                continue
            if dependency_names.intersection(entry.get("dependencies", {})):
                path.unlink()
                count += 1
        return count


def _validate_key(key: str) -> None:
    if len(key) != 64 or any(character not in "0123456789abcdef" for character in key):
        raise ValueError("cache key must be a lowercase SHA-256 digest")
