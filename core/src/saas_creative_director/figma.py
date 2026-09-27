from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Iterable

from .layout import compose_scene, recipe_names
from .workspace import read_json


FIGMA_MANIFEST_VERSION = "1.0"
SUPPORTED_FIGMA_MANIFEST_VERSIONS = frozenset({"1.0", "1.1"})
ALLOWED_NODE_TYPES = frozenset(
    {
        "annotation-card",
        "asset-placeholder",
        "connector",
        "frame",
        "pill",
        "raster-placeholder",
        "rectangle",
        "text",
        "ui-card",
        "ui-row",
    }
)
HARD_LIMITS = {
    "max_manifest_bytes": 2_000_000,
    "max_scenes": 48,
    "max_nodes": 2_500,
    "max_nodes_per_scene": 200,
    "max_text_chars": 4_000,
    "max_total_text_chars": 100_000,
    "max_canvas_dimension": 8_192,
    "max_pages": 12,
}
DOCUMENT_PAGES = (
    "01 Research",
    "02 Creative Directions",
    "03 Visual Grammar",
    "04 Storyboard",
    "05 Production Frames",
    "06 Handoff",
)
DEFAULT_RENDER_TOKENS: dict[str, dict[str, Any]] = {
    "colors": {
        "canvas": "#F9FAFB",
        "surface": "#F9FAFB",
        "raised": "#FFFFFF",
        "muted": "#F3F4F6",
        "dark": "#111827",
        "accent": "#4F46E5",
        "accent_surface": "#EEF2FF",
        "success": "#ECFDF5",
        "warning": "#FFF7ED",
        "raster": "#FFF1F2",
        "border": "#D1D5DB",
        "text_primary": "#111827",
        "text_secondary": "#4B5563",
        "text_on_accent": "#FFFFFF",
    },
    "spacing": {"base": 8, "corner_radius": 18, "stroke_width": 2},
    "type_scale": {"headline": 56, "title": 30, "body": 18, "eyebrow": 15},
}
_HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


class FigmaManifestError(ValueError):
    def __init__(self, issues: Iterable[str]):
        self.issues = tuple(issues)
        super().__init__("Invalid Figma manifest:\n- " + "\n- ".join(self.issues))


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _is_finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _digest(value: Any, length: int = 16) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()[:length]


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return normalized[:48] or "project"


def _flatten_nodes(nodes: list[dict[str, Any]]) -> Iterable[dict[str, Any]]:
    for node in nodes:
        yield node
        children = node.get("children", [])
        if isinstance(children, list):
            yield from _flatten_nodes(children)


def _normalize_render_tokens(raw: Any) -> dict[str, dict[str, Any]]:
    source = raw if isinstance(raw, dict) else {}
    normalized = {group: dict(values) for group, values in DEFAULT_RENDER_TOKENS.items()}

    colors = source.get("colors", {})
    if isinstance(colors, dict):
        for key in normalized["colors"]:
            if key not in colors:
                continue
            value = colors[key]
            if not isinstance(value, str) or not _HEX_COLOR.fullmatch(value):
                raise ValueError(f"visual-direction tokens.colors.{key}: expected #RRGGBB")
            normalized["colors"][key] = value.upper()

    spacing = source.get("spacing", {})
    if isinstance(spacing, (int, float)) and not isinstance(spacing, bool):
        spacing = {"base": spacing}
    if isinstance(spacing, dict):
        for key in normalized["spacing"]:
            if key not in spacing:
                continue
            value = spacing[key]
            if not _is_finite_number(value) or not 0 < value <= 128:
                raise ValueError(f"visual-direction tokens.spacing.{key}: expected a number from 0 to 128")
            normalized["spacing"][key] = value

    type_scale = source.get("type_scale", {})
    if isinstance(type_scale, dict):
        for key in normalized["type_scale"]:
            if key not in type_scale:
                continue
            value = type_scale[key]
            if not _is_finite_number(value) or not 8 <= value <= 144:
                raise ValueError(f"visual-direction tokens.type_scale.{key}: expected a number from 8 to 144")
            normalized["type_scale"][key] = value
    return normalized


def _production_semantics(scene: dict[str, Any]) -> dict[str, Any]:
    objects: list[dict[str, Any]] = []
    for index, value in enumerate(scene.get("objects", []), start=1):
        obj = value if isinstance(value, dict) else {}
        bounds = obj.get("bounds") if isinstance(obj.get("bounds"), dict) else {}
        objects.append(
            {
                "semantic_id": str(obj.get("semantic_id") or f"{scene['id']}/object/{index:02d}"),
                "name": str(obj.get("name") or f"Object {index}"),
                "type": str(obj.get("type") or "placeholder"),
                "role": str(obj.get("role") or "supporting"),
                "bounds": {
                    "x": float(bounds.get("x", 0)),
                    "y": float(bounds.get("y", 0)),
                    "width": float(bounds.get("width", 1)),
                    "height": float(bounds.get("height", 1)),
                },
                "asset_id": str(obj["asset_id"]) if obj.get("asset_id") is not None else None,
                "editable": bool(obj.get("editable", str(obj.get("type", "")).casefold() not in {"image", "screenshot", "raster", "raster-ui"})),
            }
        )
    return {"objects": objects}


def _compile_scene(scene: dict[str, Any], canvas: dict[str, Any], render_context: dict[str, Any], manifest_version: str = "1.0") -> dict[str, Any]:
    result = compose_scene(scene, canvas)
    states = scene.get("states", []) if isinstance(scene.get("states", []), list) else []
    events = scene.get("events", []) if isinstance(scene.get("events", []), list) else []
    transition_anchors = scene.get("transition_anchors", []) if isinstance(scene.get("transition_anchors", []), list) else []
    production_semantics = _production_semantics(scene)
    sequence_mode = "panel-sequence" if scene.get("render_mode") == "panel-sequence" else "single-frame-legacy"
    scene_source: dict[str, Any] = {
        "id": scene.get("id"),
        "declared_revision": scene.get("revision"),
        "purpose": scene.get("purpose"),
        "message": scene.get("message"),
        "voiceover": scene.get("voiceover"),
        "on_screen_copy": scene.get("on_screen_copy"),
        "composition_pattern": scene.get("composition_pattern"),
        "pattern_version": scene.get("pattern_version", "legacy-0.5"),
        "recipe": result.recipe,
        "recipe_version": result.recipe_version,
        "recipe_selection": result.selection,
        "objects": scene.get("objects", []),
        "attention_sequence": scene.get("attention_sequence", []),
        "states": states,
        "events": events,
        "motion": scene.get("motion", []),
        "transition_anchors": transition_anchors,
        "transition_out": scene.get("transition_out"),
        "locked": scene.get("locked", []),
        "creative_freedom": scene.get("creative_freedom", []),
        "reference_ids": scene.get("reference_ids", []),
        "evidence_ids": scene.get("evidence_ids", []),
        "production_semantics": production_semantics,
    }
    if manifest_version == "1.1":
        scene_source["sequence_mode"] = sequence_mode
        scene_source["panels"] = scene.get("panels", [])
    layout_nodes = [node.as_dict() for node in result.nodes]
    compiled_panels: list[dict[str, Any]] = []
    if sequence_mode == "panel-sequence":
        panel_nodes = {str(node.metadata.get("panel_id")): node for node in result.nodes}
        for panel in scene.get("panels", []):
            panel_id = str(panel["id"])
            panel_node = panel_nodes[panel_id]
            children = [child.as_dict() for child in panel_node.children]
            compiled_panels.append({
                "semantic_id": f"scene/{scene['id']}/panel/{panel_id}",
                "id": panel_id,
                "name": str(panel.get("purpose", panel_id)),
                "at_seconds": panel.get("at_seconds"),
                "duration_seconds": panel.get("hold_seconds"),
                "state_id": panel.get("state_id"),
                "event_ids": list(panel.get("event_ids", [])),
                "continuity": panel.get("continuity"),
                "transition_from_previous": panel.get("transition_from_previous"),
                "focal_object_id": panel.get("focal_object_id"),
                "nodes": children,
                "object_instance_ids": [
                    str(node["semantic_id"])
                    for node in _flatten_nodes(children)
                    if isinstance(node.get("metadata"), dict) and node["metadata"].get("object_id")
                ],
            })
        nodes: list[dict[str, Any]] = []
    else:
        nodes = layout_nodes
    hash_source = {
        "scene": scene_source,
        "recipe": result.recipe,
        "nodes": nodes,
        "render_context": render_context,
    }
    if manifest_version == "1.1":
        hash_source["panels"] = compiled_panels
    scene_hash = _digest(hash_source)
    scene_revision = str(scene.get("revision") or f"scene-{scene_hash}")
    rendered_nodes = nodes if sequence_mode == "single-frame-legacy" else [
        node for panel in compiled_panels for node in panel["nodes"]
    ]
    raster_ids = [
        node["semantic_id"]
        for node in _flatten_nodes(rendered_nodes)
        if node["type"] == "raster-placeholder"
    ]
    compiled: dict[str, Any] = {
        "semantic_id": f"scene/{scene['id']}",
        "id": scene["id"],
        "name": f"{scene['id']} — {scene.get('purpose', 'Untitled')}",
        "source_revision": scene_revision,
        "content_hash": scene_hash,
        "duration_seconds": scene.get("duration_seconds"),
        "composition_pattern": scene.get("composition_pattern"),
        "pattern_version": str(scene.get("pattern_version", "legacy-0.5")),
        "recipe": result.recipe,
        "recipe_version": result.recipe_version,
        "recipe_selection": result.selection,
        "nodes": nodes,
        "states": states,
        "events": events,
        "transition_anchors": transition_anchors,
        "production_semantics": production_semantics,
        "annotations": {
            "purpose": scene.get("purpose", ""),
            "message": scene.get("message", ""),
            "voiceover": scene.get("voiceover", ""),
            "on_screen_copy": scene.get("on_screen_copy", ""),
            "attention_sequence": scene.get("attention_sequence", []),
            "motion": scene.get("motion", []),
            "transition_out": scene.get("transition_out", ""),
            "reference_ids": scene.get("reference_ids", []),
            "evidence_ids": scene.get("evidence_ids", []),
            "locked": scene.get("locked", []),
            "creative_freedom": scene.get("creative_freedom", []),
        },
        "assets": {"raster_semantic_ids": raster_ids, "missing": raster_ids},
        "warnings": list(result.warnings),
    }
    if manifest_version == "1.1":
        compiled["sequence_mode"] = sequence_mode
        compiled["panels"] = compiled_panels
    return compiled


def build_manifest(project_root: Path) -> dict[str, Any]:
    project = read_json(project_root / "project.json")
    storyboard = read_json(project_root / "artifacts" / "storyboard.json")
    visual = read_json(project_root / "artifacts" / "visual-direction.json")
    frame_tokens = visual.get("tokens", {}).get("frame", {})
    canvas = {
        "width": float(frame_tokens.get("width", 1920)),
        "height": float(frame_tokens.get("height", 1080)),
        "scene_gap": 160,
        "annotation_width": 480,
        "annotation_gap": 32,
    }
    raw_tokens = visual.get("tokens", {})
    tokens = _normalize_render_tokens(raw_tokens)
    typography = {
        "family": str(raw_tokens.get("font_family", "Inter")) if isinstance(raw_tokens, dict) else "Inter",
        "style": "Regular",
        "fallbacks": ["Inter", "Roboto"],
    }
    render_context = {
        "renderer": "figma-layout-v1",
        "canvas": canvas,
        "typography": typography,
        "tokens": tokens,
    }
    source_revision = str(
        storyboard.get("revision")
        or project.get("content_revision")
        or f"storyboard-{_digest(storyboard, 12)}"
    )
    storyboard_version = str(storyboard.get("schema_version", "0.5"))
    manifest_version = "1.1" if storyboard_version == "1.1" else FIGMA_MANIFEST_VERSION
    scenes = [_compile_scene(scene, canvas, render_context, manifest_version) for scene in storyboard.get("scenes", [])]
    manifest: dict[str, Any] = {
        "schema_version": manifest_version,
        "contract": "saas-creative-director/figma-manifest",
        "project": {
            "id": _slug(str(project.get("name", project_root.name))),
            "name": str(project.get("name", project_root.name)),
        },
        "source_revision": source_revision,
        "document_pages": list(DOCUMENT_PAGES),
        "target_page": "04 Storyboard",
        "canvas": canvas,
        "typography": typography,
        "tokens": tokens,
        "recipes": list(recipe_names()),
        "limits": dict(HARD_LIMITS),
        "scenes": scenes,
        "warnings": [warning for scene in scenes for warning in scene["warnings"]],
    }
    manifest_hash = _digest(manifest, 24)
    manifest["operation"] = {
        "id": f"figma-import/{manifest['project']['id']}/{manifest_hash}",
        "manifest_hash": manifest_hash,
        "mode": "preserve-human-create-revision",
    }
    preflight_manifest(manifest)
    return manifest


def _check_string(value: Any, path: str, issues: list[str], *, allow_empty: bool = False) -> None:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        issues.append(f"{path}: must be {'a' if allow_empty else 'a non-empty'} string")


def preflight_manifest(manifest: Any) -> dict[str, int]:
    """Validate every bounded input before a renderer performs any write."""

    issues: list[str] = []
    if not isinstance(manifest, dict):
        raise FigmaManifestError(("$: must be an object",))
    if manifest.get("schema_version") not in SUPPORTED_FIGMA_MANIFEST_VERSIONS:
        issues.append(f"schema_version: expected one of {sorted(SUPPORTED_FIGMA_MANIFEST_VERSIONS)}")
    if manifest.get("contract") != "saas-creative-director/figma-manifest":
        issues.append("contract: unsupported contract")
    _check_string(manifest.get("target_page"), "target_page", issues)
    operation = manifest.get("operation")
    if not isinstance(operation, dict):
        issues.append("operation: must be an object")
    else:
        _check_string(operation.get("id"), "operation.id", issues)
        _check_string(operation.get("manifest_hash"), "operation.manifest_hash", issues)
        if operation.get("mode") != "preserve-human-create-revision":
            issues.append("operation.mode: unsupported write mode")

    pages = manifest.get("document_pages")
    if not isinstance(pages, list) or not pages:
        issues.append("document_pages: must be a non-empty array")
        pages = []
    elif len(pages) > HARD_LIMITS["max_pages"]:
        issues.append(f"document_pages: exceeds {HARD_LIMITS['max_pages']}")
    if len(pages) != len(set(value for value in pages if isinstance(value, str))):
        issues.append("document_pages: page names must be unique")

    canvas = manifest.get("canvas")
    if not isinstance(canvas, dict):
        issues.append("canvas: must be an object")
        canvas = {}
    for key in ("width", "height", "scene_gap", "annotation_width", "annotation_gap"):
        value = canvas.get(key)
        if not _is_finite_number(value) or value <= 0:
            issues.append(f"canvas.{key}: must be a positive finite number")
        elif key in ("width", "height") and value > HARD_LIMITS["max_canvas_dimension"]:
            issues.append(f"canvas.{key}: exceeds {HARD_LIMITS['max_canvas_dimension']}")

    tokens = manifest.get("tokens")
    if not isinstance(tokens, dict):
        issues.append("tokens: must be an object")
    else:
        if set(tokens) != set(DEFAULT_RENDER_TOKENS):
            issues.append("tokens: must contain only colors, spacing, and type_scale")
        colors = tokens.get("colors")
        if not isinstance(colors, dict) or set(colors) != set(DEFAULT_RENDER_TOKENS["colors"]):
            issues.append("tokens.colors: must contain the supported color roles")
        elif any(not isinstance(value, str) or not _HEX_COLOR.fullmatch(value) for value in colors.values()):
            issues.append("tokens.colors: every value must be #RRGGBB")
        for group, lower, upper in (("spacing", 0, 128), ("type_scale", 8, 144)):
            values = tokens.get(group)
            if not isinstance(values, dict) or set(values) != set(DEFAULT_RENDER_TOKENS[group]):
                issues.append(f"tokens.{group}: must contain the supported roles")
            elif any(
                not _is_finite_number(value)
                or not lower < value <= upper
                for value in values.values()
            ):
                issues.append(f"tokens.{group}: contains an out-of-range value")

    scenes = manifest.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        issues.append("scenes: must be a non-empty array")
        scenes = []
    elif len(scenes) > HARD_LIMITS["max_scenes"]:
        issues.append(f"scenes: exceeds {HARD_LIMITS['max_scenes']}")

    semantic_ids: set[str] = set()
    scene_ids: set[str] = set()
    total_nodes = 0
    total_text_chars = 0
    raster_nodes = 0
    for scene_index, scene in enumerate(scenes):
        scene_path = f"scenes[{scene_index}]"
        if not isinstance(scene, dict):
            issues.append(f"{scene_path}: must be an object")
            continue
        if manifest.get("schema_version") == "1.0" and ("sequence_mode" in scene or "panels" in scene):
            issues.append(f"{scene_path}: manifest 1.0 must not contain panel-sequence fields")
        if manifest.get("schema_version") == "1.1" and ("sequence_mode" not in scene or "panels" not in scene):
            issues.append(f"{scene_path}: manifest 1.1 requires sequence_mode and panels")
        scene_id = scene.get("id")
        if not isinstance(scene_id, str) or not re.fullmatch(r"S[0-9]{2,}", scene_id):
            issues.append(f"{scene_path}.id: must match S followed by at least two digits")
        elif scene_id in scene_ids:
            issues.append(f"{scene_path}.id: duplicate {scene_id}")
        else:
            scene_ids.add(scene_id)
        if scene.get("recipe") not in recipe_names():
            issues.append(f"{scene_path}.recipe: unsupported recipe")
        if scene.get("recipe_version") != "1.0":
            issues.append(f"{scene_path}.recipe_version: expected 1.0")
        if scene.get("recipe_selection") not in {"explicit", "legacy-inferred"}:
            issues.append(f"{scene_path}.recipe_selection: unsupported selection mode")
        _check_string(scene.get("pattern_version"), f"{scene_path}.pattern_version", issues)
        for required_string in ("semantic_id", "name", "source_revision", "content_hash"):
            _check_string(scene.get(required_string), f"{scene_path}.{required_string}", issues)
        duration = scene.get("duration_seconds")
        if not _is_finite_number(duration) or duration <= 0:
            issues.append(f"{scene_path}.duration_seconds: must be a positive finite number")
        sequence_mode = scene.get("sequence_mode", "single-frame-legacy")
        if sequence_mode not in {"single-frame-legacy", "panel-sequence"}:
            issues.append(f"{scene_path}.sequence_mode: unsupported mode")
        nodes = scene.get("nodes")
        if not isinstance(nodes, list) or (sequence_mode != "panel-sequence" and not nodes):
            issues.append(f"{scene_path}.nodes: must be a non-empty array unless panel-sequence is used")
            nodes = []
        panels = scene.get("panels", [])
        if sequence_mode == "panel-sequence":
            if not isinstance(panels, list) or not panels or len(panels) > 24:
                issues.append(f"{scene_path}.panels: must contain 1-24 panels")
                panels = []
        elif panels not in (None, []):
            issues.append(f"{scene_path}.panels: legacy scenes must not contain panels")
            panels = []
        render_node_roots = list(nodes)
        for panel in panels:
            if isinstance(panel, dict) and isinstance(panel.get("nodes"), list):
                render_node_roots.extend(panel["nodes"])
        flat_nodes = list(_flatten_nodes(render_node_roots))
        total_nodes += len(flat_nodes)
        if len(flat_nodes) > HARD_LIMITS["max_nodes_per_scene"]:
            issues.append(f"{scene_path}.nodes: exceeds {HARD_LIMITS['max_nodes_per_scene']}")
        for node_index, node in enumerate(flat_nodes):
            node_path = f"{scene_path}.nodes[*:{node_index}]"
            if not isinstance(node, dict):
                issues.append(f"{node_path}: must be an object")
                continue
            semantic_id = node.get("semantic_id")
            _check_string(semantic_id, f"{node_path}.semantic_id", issues)
            if isinstance(semantic_id, str):
                if semantic_id in semantic_ids:
                    issues.append(f"{node_path}.semantic_id: duplicate {semantic_id}")
                semantic_ids.add(semantic_id)
            if node.get("type") not in ALLOWED_NODE_TYPES:
                issues.append(f"{node_path}.type: unsupported type {node.get('type')!r}")
            for key in ("role", "name", "style"):
                _check_string(node.get(key), f"{node_path}.{key}", issues)
            bounds = node.get("bounds")
            if not isinstance(bounds, dict):
                issues.append(f"{node_path}.bounds: must be an object")
            else:
                for key in ("x", "y", "width", "height"):
                    value = bounds.get(key)
                    if not _is_finite_number(value):
                        issues.append(f"{node_path}.bounds.{key}: must be a finite number")
                    elif key in ("width", "height") and value <= 0:
                        issues.append(f"{node_path}.bounds.{key}: must be positive")
                    elif abs(value) > HARD_LIMITS["max_canvas_dimension"]:
                        issues.append(f"{node_path}.bounds.{key}: exceeds safe dimension")
            text = node.get("text")
            if text is not None:
                if not isinstance(text, str):
                    issues.append(f"{node_path}.text: must be a string")
                else:
                    total_text_chars += len(text)
                    if len(text) > HARD_LIMITS["max_text_chars"]:
                        issues.append(f"{node_path}.text: exceeds {HARD_LIMITS['max_text_chars']} characters")
            metadata = node.get("metadata")
            if metadata is not None and not isinstance(metadata, dict):
                issues.append(f"{node_path}.metadata: must be an object")
            if node.get("type") == "raster-placeholder":
                raster_nodes += 1

        for collection_name in ("states", "events", "transition_anchors"):
            collection = scene.get(collection_name)
            if not isinstance(collection, list) or any(not isinstance(item, dict) for item in collection):
                issues.append(f"{scene_path}.{collection_name}: must be an array of objects")
            else:
                for item_index, item in enumerate(collection):
                    item_path = f"{scene_path}.{collection_name}[{item_index}]"
                    at_seconds = item.get("at_seconds")
                    if not _is_finite_number(at_seconds) or at_seconds < 0:
                        issues.append(f"{item_path}.at_seconds: must be a non-negative finite number")
                    if "duration_seconds" in item:
                        item_duration = item.get("duration_seconds")
                        if not _is_finite_number(item_duration) or item_duration < 0:
                            issues.append(f"{item_path}.duration_seconds: must be a non-negative finite number")
                try:
                    total_text_chars += len(_canonical_json(collection))
                except (TypeError, ValueError):
                    # A path-specific issue is recorded above for non-finite timing;
                    # the final strict-JSON check covers any other invalid value.
                    pass

        production_semantics = scene.get("production_semantics")
        if not isinstance(production_semantics, dict) or not isinstance(production_semantics.get("objects"), list):
            issues.append(f"{scene_path}.production_semantics.objects: must be an array")
        else:
            for object_index, obj in enumerate(production_semantics["objects"]):
                object_path = f"{scene_path}.production_semantics.objects[{object_index}]"
                if not isinstance(obj, dict):
                    issues.append(f"{object_path}: must be an object")
                    continue
                for key in ("semantic_id", "name", "type", "role"):
                    _check_string(obj.get(key), f"{object_path}.{key}", issues)
                if not isinstance(obj.get("editable"), bool):
                    issues.append(f"{object_path}.editable: must be a boolean")
                bounds = obj.get("bounds")
                if not isinstance(bounds, dict):
                    issues.append(f"{object_path}.bounds: must be an object")
                else:
                    for key in ("x", "y", "width", "height"):
                        value = bounds.get(key)
                        if not _is_finite_number(value):
                            issues.append(f"{object_path}.bounds.{key}: must be a finite number")
                        elif key in ("width", "height") and value <= 0:
                            issues.append(f"{object_path}.bounds.{key}: must be positive")
                        elif abs(value) > HARD_LIMITS["max_canvas_dimension"]:
                            issues.append(f"{object_path}.bounds.{key}: exceeds safe dimension")
                total_text_chars += sum(
                    len(value) for value in obj.values() if isinstance(value, str)
                )

        if sequence_mode == "panel-sequence":
            state_ids = {item.get("id") for item in scene.get("states", []) if isinstance(item, dict)}
            event_ids = {item.get("id") for item in scene.get("events", []) if isinstance(item, dict)}
            object_ids = {
                item.get("semantic_id")
                for item in (production_semantics.get("objects", []) if isinstance(production_semantics, dict) else [])
                if isinstance(item, dict)
            }
            prior_at = -1.0
            panel_ids: set[str] = set()
            panel_semantic_ids: set[str] = set()
            for panel_index, panel in enumerate(panels):
                panel_path = f"{scene_path}.panels[{panel_index}]"
                if not isinstance(panel, dict):
                    issues.append(f"{panel_path}: must be an object")
                    continue
                panel_id = panel.get("id")
                if not isinstance(panel_id, str) or not re.fullmatch(r"P[0-9]{2,}", panel_id):
                    issues.append(f"{panel_path}.id: must match P followed by at least two digits")
                elif panel_id in panel_ids:
                    issues.append(f"{panel_path}.id: duplicate {panel_id}")
                else:
                    panel_ids.add(panel_id)
                panel_semantic_id = panel.get("semantic_id")
                _check_string(panel_semantic_id, f"{panel_path}.semantic_id", issues)
                if isinstance(panel_semantic_id, str):
                    if panel_semantic_id in panel_semantic_ids:
                        issues.append(f"{panel_path}.semantic_id: duplicate {panel_semantic_id}")
                    panel_semantic_ids.add(panel_semantic_id)
                _check_string(panel.get("name"), f"{panel_path}.name", issues)
                at_seconds = panel.get("at_seconds")
                panel_duration = panel.get("duration_seconds")
                if not _is_finite_number(at_seconds) or at_seconds < 0:
                    issues.append(f"{panel_path}.at_seconds: must be a non-negative finite number")
                elif at_seconds <= prior_at:
                    issues.append(f"{panel_path}.at_seconds: must be strictly increasing")
                else:
                    prior_at = float(at_seconds)
                if not _is_finite_number(panel_duration) or panel_duration <= 0:
                    issues.append(f"{panel_path}.duration_seconds: must be a positive finite number")
                elif _is_finite_number(at_seconds) and _is_finite_number(duration) and at_seconds + panel_duration > duration:
                    issues.append(f"{panel_path}.duration_seconds: panel must end within the scene")
                if panel.get("state_id") not in state_ids:
                    issues.append(f"{panel_path}.state_id: unknown state id: {panel.get('state_id')}")
                represented_events = panel.get("event_ids")
                if not isinstance(represented_events, list) or any(item not in event_ids for item in represented_events):
                    issues.append(f"{panel_path}.event_ids: contains an unknown event id")
                if panel.get("continuity") not in {"continuous", "cut", "hold"}:
                    issues.append(f"{panel_path}.continuity: unsupported value")
                transition = panel.get("transition_from_previous")
                if transition is not None and not isinstance(transition, str):
                    issues.append(f"{panel_path}.transition_from_previous: must be a string or null")
                if panel.get("focal_object_id") not in object_ids:
                    issues.append(f"{panel_path}.focal_object_id: unknown semantic object id: {panel.get('focal_object_id')}")
                instance_ids = panel.get("object_instance_ids")
                actual_instance_ids = {
                    node.get("semantic_id")
                    for node in _flatten_nodes(panel.get("nodes", []))
                    if isinstance(node, dict) and isinstance(node.get("metadata"), dict) and node["metadata"].get("object_id")
                }
                if not isinstance(instance_ids, list) or set(instance_ids) != actual_instance_ids:
                    issues.append(f"{panel_path}.object_instance_ids: must exactly list rendered object instances")

        annotations = scene.get("annotations")
        if not isinstance(annotations, dict):
            issues.append(f"{scene_path}.annotations: must be an object")
        else:
            for key in ("purpose", "message", "voiceover", "on_screen_copy", "transition_out"):
                value = annotations.get(key)
                if not isinstance(value, str):
                    issues.append(f"{scene_path}.annotations.{key}: must be a string")
                else:
                    total_text_chars += len(value)
            for key in ("attention_sequence", "motion", "reference_ids", "evidence_ids", "locked", "creative_freedom"):
                value = annotations.get(key)
                if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                    issues.append(f"{scene_path}.annotations.{key}: must be an array of strings")
                else:
                    total_text_chars += sum(len(item) for item in value)

    if total_nodes > HARD_LIMITS["max_nodes"]:
        issues.append(f"nodes: exceeds {HARD_LIMITS['max_nodes']}")
    if total_text_chars > HARD_LIMITS["max_total_text_chars"]:
        issues.append(f"text: exceeds {HARD_LIMITS['max_total_text_chars']} total characters")
    try:
        manifest_bytes = len(_canonical_json(manifest).encode("utf-8"))
    except (TypeError, ValueError) as exc:
        issues.append(f"manifest: must be strict JSON ({exc})")
        manifest_bytes = 0
    if manifest_bytes > HARD_LIMITS["max_manifest_bytes"]:
        issues.append(f"manifest: exceeds {HARD_LIMITS['max_manifest_bytes']} bytes")
    if issues:
        raise FigmaManifestError(issues)
    return {
        "scene_count": len(scenes),
        "node_count": total_nodes,
        "text_chars": total_text_chars,
        "raster_count": raster_nodes,
        "manifest_bytes": manifest_bytes,
    }
