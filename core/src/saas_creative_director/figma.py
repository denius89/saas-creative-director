from __future__ import annotations

from pathlib import Path
from typing import Any

from .workspace import read_json


def build_manifest(project_root: Path) -> dict[str, Any]:
    project = read_json(project_root / "project.json")
    storyboard = read_json(project_root / "artifacts" / "storyboard.json")
    visual = read_json(project_root / "artifacts" / "visual-direction.json")
    scenes = []
    for scene in storyboard.get("scenes", []):
        layers = [
            {"name": "00_BG", "type": "rectangle", "role": "background"},
            {"name": "10_COPY", "type": "text", "text": scene.get("on_screen_copy", ""), "role": "copy"},
        ]
        for index, obj in enumerate(scene.get("objects", []), start=1):
            layers.append({
                "name": f"20_OBJECT_{index:02d}_{obj.get('name', 'placeholder').upper().replace(' ', '_')}",
                "type": obj.get("type", "placeholder"),
                "role": obj.get("role", "supporting"),
                "bounds": obj.get("bounds", {}),
            })
        scenes.append({
            "id": scene.get("id"),
            "name": f"{scene.get('id', 'SCENE')} — {scene.get('purpose', 'Untitled')}",
            "duration_seconds": scene.get("duration_seconds"),
            "composition_pattern": scene.get("composition_pattern"),
            "layers": layers,
            "annotations": {
                "message": scene.get("message"),
                "attention_sequence": scene.get("attention_sequence", []),
                "motion": scene.get("motion", []),
                "transition_out": scene.get("transition_out"),
                "evidence_ids": scene.get("evidence_ids", []),
                "locked": scene.get("locked", []),
                "creative_freedom": scene.get("creative_freedom", []),
            },
        })
    return {
        "schema_version": "0.5",
        "project": project.get("name"),
        "document_pages": [
            "01 Research",
            "02 Creative Directions",
            "03 Visual Grammar",
            "04 Storyboard",
            "05 Production Frames",
            "06 Handoff",
        ],
        "canvas": {"width": 1920, "height": 1080, "gap": 160},
        "tokens": visual.get("tokens", {}),
        "scenes": scenes,
    }
