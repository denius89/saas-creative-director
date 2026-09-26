from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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


def initialize_project(root: Path, name: str) -> None:
    if root.exists() and any(root.iterdir()):
        raise FileExistsError(f"Refusing to initialize non-empty directory: {root}")
    (root / "inputs").mkdir(parents=True, exist_ok=True)
    (root / "artifacts").mkdir(parents=True, exist_ok=True)
    (root / "reviews").mkdir(parents=True, exist_ok=True)
    (root / "inputs" / ".gitkeep").touch()

    project = {
        "schema_version": "0.5",
        "name": name,
        "created_at": utc_now(),
        "stage": "intake",
        "business_goal": "",
        "channel": "",
        "duration_seconds": None,
        "gates": {
            key: {"status": "PENDING", "approved_by": None, "approved_at": None, "notes": ""}
            for key in ("strategy", "creative_direction", "production")
        },
    }
    write_json(root / "project.json", project)
    write_json(root / "artifacts" / "source-registry.json", {"sources": []})
    write_json(root / "artifacts" / "evidence.json", {"evidence": []})
    (root / "artifacts" / "open-questions.md").write_text(
        "# Open questions\n\n- Add questions whose answers could materially change strategy.\n",
        encoding="utf-8",
    )


def load_project(root: Path) -> dict[str, Any]:
    return read_json(root / "project.json")
