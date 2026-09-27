from __future__ import annotations

from dataclasses import dataclass
from typing import Any


STAGES = (
    "intake",
    "product_intelligence",
    "competitor_intelligence",
    "video_strategy",
    "reference_research",
    "narrative",
    "visual_direction",
    "storyboard",
    "figma_wireframes",
    "production_review",
    "complete",
)

GATES = {
    "strategy": {"after": "video_strategy", "unlocks": "reference_research"},
    "creative_direction": {"after": "visual_direction", "unlocks": "storyboard"},
    "production": {"after": "production_review", "unlocks": "complete"},
}

# Files that prove a stage produced something useful. The two registries are
# initialized empty and therefore are checked semantically by validation.py.
STAGE_OUTPUTS = {
    "intake": ("artifacts/source-registry.json", "artifacts/evidence.json", "artifacts/project-context.md"),
    "product_intelligence": ("artifacts/product-intelligence.json",),
    "competitor_intelligence": ("artifacts/competitor-intelligence.json",),
    "video_strategy": ("artifacts/video-strategy.json",),
    "reference_research": ("artifacts/reference-library.json", "artifacts/pattern-library.json"),
    "narrative": ("artifacts/narrative.json",),
    "visual_direction": ("artifacts/motion-direction.json", "artifacts/visual-direction.json"),
    "storyboard": ("artifacts/storyboard.json",),
    "figma_wireframes": ("artifacts/figma-manifest.json", "reviews/visual-qa.json"),
    "production_review": ("reviews/production-review.md",),
}

# Each approval binds exactly the material available at that decision point.
# Comparing these sets independently gives targeted invalidation: a storyboard
# change invalidates production, while it leaves strategy approval untouched.
GATE_DEPENDENCIES = {
    "strategy": (
        "project.json#decision_inputs",
        "artifacts/source-registry.json",
        "artifacts/evidence.json",
        "artifacts/product-intelligence.json",
        "artifacts/competitor-intelligence.json",
        "artifacts/video-strategy.json",
    ),
    "creative_direction": (
        "project.json#decision_inputs",
        "artifacts/source-registry.json",
        "artifacts/evidence.json",
        "artifacts/video-strategy.json",
        "artifacts/reference-library.json",
        "artifacts/pattern-library.json",
        "artifacts/narrative.json",
        "artifacts/motion-direction.json",
        "artifacts/visual-direction.json",
    ),
    "production": (
        "project.json#decision_inputs",
        "artifacts/source-registry.json",
        "artifacts/evidence.json",
        "artifacts/video-strategy.json",
        "artifacts/narrative.json",
        "artifacts/motion-direction.json",
        "artifacts/visual-direction.json",
        "artifacts/storyboard.json",
        "artifacts/figma-manifest.json",
        "reviews/visual-qa.json",
        "reviews/production-review.md",
    ),
}


@dataclass(frozen=True)
class NextAction:
    kind: str
    name: str
    instruction: str


def next_action(project: dict[str, Any]) -> NextAction:
    stage = project.get("stage", "intake")
    if stage not in STAGES:
        return NextAction("error", stage, "Project has an unknown stage.")

    if stage == "complete":
        return NextAction("complete", stage, "Handoff is approved and ready for production.")

    gates = project.get("gates", {})
    for gate_name, rule in GATES.items():
        gate = gates.get(gate_name, {})
        if stage == rule["after"] and gate.get("status") == "CHANGES_REQUESTED":
            notes = gate.get("notes") or "Review the requested changes."
            return NextAction("changes_requested", gate_name, str(notes))
    for gate_name, rule in GATES.items():
        if stage == rule["after"] and gates.get(gate_name, {}).get("status") == "APPROVED":
            return NextAction("advance", stage, f"{gate_name.replace('_', ' ').title()} is approved; advance to {rule['unlocks']}.")

    gate = next((name for name, rule in GATES.items() if rule["after"] == stage), None)
    suffix = f" Then request the `{gate}` approval and stop." if gate else ""
    return NextAction("stage", stage, f"Run the `{skill_for(stage)}` skill and validate its artifacts.{suffix}")


def skill_for(stage: str) -> str:
    return {
        "intake": "client-project-intake",
        "product_intelligence": "saas-product-strategist",
        "competitor_intelligence": "competitor-intelligence",
        "video_strategy": "saas-video-strategist",
        "reference_research": "creative-reference-research",
        "narrative": "saas-narrative-director",
        "visual_direction": "motion-design-director",
        "storyboard": "storyboard-composition",
        "figma_wireframes": "storyboard-composition",
        "production_review": "production-review",
    }.get(stage, "production-review")


def advance(project: dict[str, Any], project_root: Any | None = None) -> str:
    stage = project.get("stage", "intake")
    if stage not in STAGES:
        raise ValueError(f"Unknown stage: {stage}")
    if stage == "complete":
        return stage
    if project_root is not None:
        # Lazy imports keep the small orchestration model independent and avoid
        # a validation/orchestrator import cycle.
        from pathlib import Path

        from .validation import validate_for_advance
        from .workspace import refresh_gate_approvals

        refresh_gate_approvals(Path(project_root), project)
        issues = validate_for_advance(Path(project_root), project)
        if issues:
            first = issues[0]
            raise ValueError(f"Cannot advance: {first.path}: {first.message}")
    for gate_name, rule in GATES.items():
        if stage == rule["after"] and project.get("gates", {}).get(gate_name, {}).get("status") != "APPROVED":
            raise ValueError(f"Approve {gate_name.replace('_', ' ')} before advancing.")
    next_stage = STAGES[STAGES.index(stage) + 1]
    project["stage"] = next_stage
    return next_stage
