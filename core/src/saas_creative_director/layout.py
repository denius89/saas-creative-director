from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import re
from typing import Any, Callable


@dataclass(frozen=True)
class LayoutNode:
    """A compact, renderer-neutral description of one native Figma object."""

    semantic_id: str
    node_type: str
    role: str
    x: float
    y: float
    width: float
    height: float
    name: str
    text: str | None = None
    style: str = "surface"
    children: tuple["LayoutNode", ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "semantic_id": self.semantic_id,
            "type": self.node_type,
            "role": self.role,
            "name": self.name,
            "bounds": {
                "x": self.x,
                "y": self.y,
                "width": self.width,
                "height": self.height,
            },
            "style": self.style,
        }
        if self.text is not None:
            result["text"] = self.text
        if self.children:
            result["children"] = [child.as_dict() for child in self.children]
        if self.metadata:
            result["metadata"] = self.metadata
        return result


@dataclass(frozen=True)
class RecipeResult:
    recipe: str
    nodes: tuple[LayoutNode, ...]
    warnings: tuple[str, ...] = field(default_factory=tuple)
    recipe_version: str = "1.0"
    selection: str = "legacy-inferred"


def _node(
    scene_id: str,
    suffix: str,
    node_type: str,
    role: str,
    bounds: tuple[float, float, float, float],
    name: str,
    *,
    text: str | None = None,
    style: str = "surface",
    children: tuple[LayoutNode, ...] = (),
    metadata: dict[str, Any] | None = None,
) -> LayoutNode:
    return LayoutNode(
        semantic_id=f"{scene_id}/{suffix}",
        node_type=node_type,
        role=role,
        x=bounds[0],
        y=bounds[1],
        width=bounds[2],
        height=bounds[3],
        name=name,
        text=text,
        style=style,
        children=children,
        metadata=metadata or {},
    )


def _headline(scene_id: str, copy: str, bounds: tuple[float, float, float, float]) -> LayoutNode:
    return _node(
        scene_id,
        "copy/headline",
        "text",
        "copy",
        bounds,
        "10_COPY_HEADLINE",
        text=copy or "Copy pending",
        style="headline",
    )


def _source_convergence(scene: dict[str, Any], width: float, height: float) -> RecipeResult:
    scene_id = str(scene["id"])
    object_name = str(scene.get("objects", [{}])[0].get("name", "Combined state")) if scene.get("objects") else "Combined state"
    card_width = 320.0
    card_height = 132.0
    source_positions = (
        (96.0, 310.0),
        (160.0, 500.0),
        (96.0, 690.0),
    )
    nodes: list[LayoutNode] = [
        _headline(scene_id, str(scene.get("on_screen_copy", "")), (96, 84, 920, 132)),
        _node(
            scene_id,
            "convergence/hub",
            "ui-card",
            "primary",
            (width - 720, 350, 560, 360),
            "20_UI_CONVERGENCE_HUB",
            style="accent-surface",
            children=(
                _node(scene_id, "convergence/hub/title", "text", "label", (40, 36, 360, 48), "21_HUB_TITLE", text=object_name, style="title"),
                _node(scene_id, "convergence/hub/row/01", "ui-row", "state", (40, 124, 480, 56), "22_READY_ROW_01", text="Record 01 · ready", style="success"),
                _node(scene_id, "convergence/hub/row/02", "ui-row", "state", (40, 196, 480, 56), "23_READY_ROW_02", text="Record 02 · ready", style="success"),
                _node(scene_id, "convergence/hub/status", "pill", "state", (40, 276, 152, 36), "24_STATUS", text="READY", style="accent"),
            ),
        ),
    ]
    for index, (x, y) in enumerate(source_positions, start=1):
        nodes.append(
            _node(
                scene_id,
                f"convergence/source/{index:02d}",
                "ui-card",
                "source",
                (x, y, card_width, card_height),
                f"20_SOURCE_CARD_{index:02d}",
                style="raised",
                children=(
                    _node(scene_id, f"convergence/source/{index:02d}/badge", "pill", "label", (24, 22, 80, 28), f"21_SOURCE_BADGE_{index:02d}", text=f"SOURCE {index}", style="muted"),
                    _node(scene_id, f"convergence/source/{index:02d}/value", "text", "value", (24, 66, 248, 38), f"22_SOURCE_VALUE_{index:02d}", text=f"Input channel {index}", style="body"),
                ),
            )
        )
        nodes.append(
            _node(
                scene_id,
                f"convergence/connector/{index:02d}",
                "connector",
                "flow",
                (x + card_width, y + card_height / 2, width - 720 - (x + card_width), 1),
                f"30_FLOW_CONNECTOR_{index:02d}",
                style="accent",
            )
        )
    return RecipeResult("source-convergence", tuple(nodes))


def _horizontal_flow(scene: dict[str, Any], width: float, height: float) -> RecipeResult:
    scene_id = str(scene["id"])
    column_width = 430.0
    gap = 150.0
    start_x = (width - (column_width * 3 + gap * 2)) / 2
    nodes: list[LayoutNode] = [
        _headline(scene_id, str(scene.get("on_screen_copy", "")), (start_x, 72, width - start_x * 2, 112))
    ]
    column_specs = (
        ("input", "1 · INPUT", "Incoming state", "muted"),
        ("match", "2 · ACTION", "Product action", "accent"),
        ("result", "3 · RESULT", "Result state", "success"),
    )
    for column_index, (key, eyebrow, title, style) in enumerate(column_specs):
        x = start_x + column_index * (column_width + gap)
        rows = tuple(
            _node(
                scene_id,
                f"flow/{key}/row/{row_index:02d}",
                "ui-row",
                "state",
                (28, 138 + (row_index - 1) * 82, column_width - 56, 62),
                f"23_{key.upper()}_ROW_{row_index:02d}",
                text=f"{title} · item {row_index:02d}",
                style=style if row_index == 1 else "surface",
            )
            for row_index in range(1, 4)
        )
        nodes.append(
            _node(
                scene_id,
                f"flow/{key}",
                "ui-card",
                "primary" if key == "match" else "supporting",
                (x, 258, column_width, 486),
                f"20_FLOW_{key.upper()}",
                style="accent-surface" if key == "match" else "raised",
                children=(
                    _node(scene_id, f"flow/{key}/eyebrow", "text", "label", (28, 30, column_width - 56, 28), f"21_{key.upper()}_EYEBROW", text=eyebrow, style="eyebrow"),
                    _node(scene_id, f"flow/{key}/title", "text", "title", (28, 70, column_width - 56, 48), f"22_{key.upper()}_TITLE", text=title, style="title"),
                    *rows,
                ),
            )
        )
        if column_index < 2:
            nodes.append(
                _node(
                    scene_id,
                    f"flow/connector/{column_index + 1:02d}",
                    "connector",
                    "flow",
                    (x + column_width + 24, 500, gap - 48, 1),
                    f"30_FLOW_CONNECTOR_{column_index + 1:02d}",
                    style="accent",
                )
            )
    return RecipeResult("horizontal-flow", tuple(nodes))


def _focus_detail(scene: dict[str, Any], width: float, height: float) -> RecipeResult:
    scene_id = str(scene["id"])
    purpose = str(scene.get("purpose", ""))
    is_result = "result" in str(scene.get("composition_pattern", "")).lower() or "outcome" in purpose.lower()
    object_name = str(scene.get("objects", [{}])[0].get("name", "Primary product state")) if scene.get("objects") else "Primary product state"
    state_rows = (
        ("Primary record", "READY", "success"),
        ("Selected record", "REVIEW", "warning"),
        ("Supporting record", "READY", "success"),
    )
    hero_children: list[LayoutNode] = [
        _node(scene_id, "focus/hero/chrome", "ui-row", "navigation", (0, 0, 1170, 54), "21_PRODUCT_CHROME", text="PRODUCT UI / PRIMARY VIEW", style="dark"),
        _node(scene_id, "focus/hero/title", "text", "title", (48, 92, 650, 54), "22_PANEL_TITLE", text=object_name, style="title"),
        _node(scene_id, "focus/hero/filter", "pill", "control", (900, 96, 190, 36), "22_FILTER", text="VIEW STATE", style="muted"),
    ]
    for index, (label, status, style) in enumerate(state_rows, start=1):
        hero_children.append(
            _node(
                scene_id,
                f"focus/hero/row/{index:02d}",
                "ui-row",
                "state",
                (48, 186 + (index - 1) * 92, 1074, 72),
                f"23_STATE_ROW_{index:02d}",
                text=f"{label}     {status}",
                style=style,
            )
        )
    hero_children.append(
        _node(scene_id, "focus/hero/action", "pill", "action", (48, 500, 224, 48), "24_PRIMARY_ACTION", text="Continue" if is_result else "Review item", style="accent")
    )
    nodes = (
        _headline(scene_id, str(scene.get("on_screen_copy", "")), (106, 92, 760, 156)),
        _node(
            scene_id,
            "focus/hero",
            "ui-card",
            "primary",
            (650, 270, 1170, 650),
            "20_PRODUCT_HERO",
            style="raised",
            children=tuple(hero_children),
        ),
        _node(scene_id, "focus/callout", "annotation-card", "callout", (106, 340, 430, 250), "30_STATE_CALLOUT", text="OUTCOME" if is_result else "KEY STATE", style="accent-surface"),
        _node(scene_id, "focus/connector", "connector", "attention", (536, 464, 114, 1), "31_CALLOUT_CONNECTOR", style="accent"),
    )
    return RecipeResult("focus-detail", nodes)


def _instance_key(value: str) -> str:
    """Return a stable path-safe suffix without replacing the logical object id."""
    readable = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")[:72] or "object"
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]
    return f"{readable}-{digest}"


def compose_panel_nodes(scene: dict[str, Any], panel: dict[str, Any]) -> tuple[LayoutNode, ...]:
    """Compile one explicit temporal panel from object/presentation references.

    Logical object identity is retained in metadata while every rendered instance
    receives a panel-scoped semantic id. This permits the same object to continue
    through several panels without creating duplicate manifest node ids.
    """
    scene_id = str(scene["id"])
    panel_id = str(panel["id"])
    objects = {
        str(obj.get("semantic_id")): obj
        for obj in scene.get("objects", [])
        if isinstance(obj, dict) and obj.get("semantic_id")
    }
    nodes: list[LayoutNode] = []
    for index, layer in enumerate(panel.get("layers", []), start=1):
        object_id = str(layer["object_id"])
        presentation_id = str(layer["presentation_id"])
        obj = objects.get(object_id, {})
        presentations = {
            str(item.get("id")): item
            for item in obj.get("presentations", [])
            if isinstance(item, dict) and item.get("id")
        }
        presentation = presentations.get(presentation_id, {})
        bounds = presentation.get("bounds", obj.get("bounds", {}))
        object_type = str(obj.get("type", "frame")).casefold()
        if object_type in {"text", "copy", "headline", "label"}:
            node_type = "text"
        elif object_type in {"image", "screenshot", "raster", "raster-ui"}:
            node_type = "raster-placeholder"
        elif object_type in {"button", "pill", "toggle"}:
            node_type = "pill"
        elif object_type in {"row", "ui-row"}:
            node_type = "ui-row"
        elif object_type in {"card", "ui-card", "ui-panel", "ui-summary", "ui-flow", "native-ui", "component", "vehicle"}:
            node_type = "ui-card"
        else:
            node_type = "frame"
        instance_key = _instance_key(object_id)
        text = presentation.get("text")
        if text is None and node_type in {"text", "pill", "ui-row", "ui-card", "raster-placeholder"}:
            text = str(obj.get("name", f"Object {index}"))
        nodes.append(
            _node(
                scene_id,
                f"panel/{panel_id}/instance/{instance_key}",
                node_type,
                str(obj.get("role", "supporting")),
                (
                    float(bounds.get("x", 0)),
                    float(bounds.get("y", 0)),
                    float(bounds.get("width", 1)),
                    float(bounds.get("height", 1)),
                ),
                f"{panel_id}_{index:02d}_{str(obj.get('name', 'OBJECT')).upper()}",
                text=str(text) if text is not None else None,
                style=str(presentation.get("style", "raised")),
                metadata={
                    "object_id": object_id,
                    "presentation_id": presentation_id,
                    "panel_id": panel_id,
                    "variant": presentation.get("variant"),
                    "editable": bool(obj.get("editable", object_type not in {"image", "screenshot", "raster", "raster-ui"})),
                },
            )
        )
    return tuple(nodes)


def _panel_sequence(scene: dict[str, Any], width: float, height: float, recipe: str, recipe_version: str, selection: str) -> RecipeResult:
    gap = 64.0
    columns = 3
    nodes: list[LayoutNode] = []
    for index, panel in enumerate(scene.get("panels", [])):
        panel_id = str(panel["id"])
        column = index % columns
        row = index // columns
        children = compose_panel_nodes(scene, panel)
        nodes.append(
            _node(
                str(scene["id"]),
                f"panel/{panel_id}",
                "frame",
                "storyboard-panel",
                (column * (width + gap), row * (height + gap), width, height),
                f"00_PANEL_{panel_id}",
                style="surface",
                children=children,
                metadata={
                    "panel_id": panel_id,
                    "at_seconds": panel.get("at_seconds"),
                    "hold_seconds": panel.get("hold_seconds"),
                    "state_id": panel.get("state_id"),
                    "event_ids": list(panel.get("event_ids", [])),
                    "focal_object_id": panel.get("focal_object_id"),
                    "camera": dict(panel.get("camera", {})),
                },
            )
        )
    return RecipeResult(recipe, tuple(nodes), (), recipe_version, selection)


_RECIPE_BUILDERS: dict[str, Callable[[dict[str, Any], float, float], RecipeResult]] = {
    "source-convergence": _source_convergence,
    "horizontal-flow": _horizontal_flow,
    "focus-detail": _focus_detail,
}


def select_recipe(composition_pattern: str) -> str:
    normalized = composition_pattern.casefold()
    if any(key in normalized for key in ("multi-source", "convergence", "many-to-one")):
        return "source-convergence"
    if any(key in normalized for key in ("horizontal", "workflow", "process", "flow")):
        return "horizontal-flow"
    return "focus-detail"


def compose_scene(scene: dict[str, Any], canvas: dict[str, Any]) -> RecipeResult:
    declared_recipe = scene.get("recipe")
    if declared_recipe is not None:
        recipe = str(declared_recipe)
        if recipe not in _RECIPE_BUILDERS:
            raise ValueError(f"{scene.get('id', 'scene')}: unsupported explicit recipe {recipe!r}")
        recipe_version = str(scene.get("recipe_version", ""))
        if recipe_version != "1.0":
            raise ValueError(
                f"{scene.get('id', 'scene')}: recipe {recipe!r} requires supported recipe_version '1.0'"
            )
        selection = "explicit"
    else:
        recipe = select_recipe(str(scene.get("composition_pattern", "")))
        recipe_version = "1.0"
        selection = "legacy-inferred"
    if scene.get("render_mode") == "panel-sequence":
        return _panel_sequence(
            scene,
            float(canvas["width"]),
            float(canvas["height"]),
            recipe,
            recipe_version,
            selection,
        )
    result = _RECIPE_BUILDERS[recipe](scene, float(canvas["width"]), float(canvas["height"]))
    extra_nodes: list[LayoutNode] = []
    warnings = list(result.warnings)
    known_types = {"cards", "ui-flow", "ui-panel", "ui-summary", "native-ui", "component"}
    raster_types = {"image", "screenshot", "raster", "raster-ui"}
    for index, obj in enumerate(scene.get("objects", []), start=1):
        object_type = str(obj.get("type", "placeholder")).casefold()
        if object_type in known_types:
            continue
        name = str(obj.get("name", f"Object {index}"))
        if object_type in raster_types:
            extra_nodes.append(
                _node(
                    str(scene["id"]),
                    f"asset/{index:02d}",
                    "raster-placeholder",
                    str(obj.get("role", "supporting")),
                    (1320, 760 - (index - 1) * 116, 420, 92),
                    f"80_RASTER_ASSET_{index:02d}",
                    text=f"RASTER · {name}",
                    style="raster",
                    metadata={"editable": False, "source_type": object_type},
                )
            )
            warnings.append(f"{scene['id']}: raster asset '{name}' is not natively editable")
        else:
            extra_nodes.append(
                _node(
                    str(scene["id"]),
                    f"unsupported/{index:02d}",
                    "asset-placeholder",
                    str(obj.get("role", "supporting")),
                    (1320, 760 - (index - 1) * 116, 420, 92),
                    f"90_UNSUPPORTED_OBJECT_{index:02d}",
                    text=f"UNSUPPORTED · {object_type} · {name}",
                    style="warning",
                    metadata={"editable": False, "source_type": object_type},
                )
            )
            warnings.append(f"{scene['id']}: unsupported object type '{object_type}' rendered as an explicit placeholder")
    return RecipeResult(
        result.recipe,
        (*result.nodes, *extra_nodes),
        tuple(warnings),
        recipe_version,
        selection,
    )


def recipe_names() -> tuple[str, ...]:
    return tuple(_RECIPE_BUILDERS)
