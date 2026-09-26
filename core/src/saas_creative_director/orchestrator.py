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
    "creative_direction": {"after": "narrative", "unlocks": "visual_direction"},
    "production": {"after": "production_review", "unlocks": "complete"},
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
        "visual_direction": "visual-direction",
        "storyboard": "storyboard-composition",
        "figma_wireframes": "storyboard-composition",
        "production_review": "production-review",
    }.get(stage, "production-review")


def advance(project: dict[str, Any]) -> str:
    stage = project.get("stage", "intake")
    if stage == "complete":
        return stage
    for gate_name, rule in GATES.items():
        if stage == rule["after"] and project.get("gates", {}).get(gate_name, {}).get("status") != "APPROVED":
            raise ValueError(f"Approve {gate_name.replace('_', ' ')} before advancing.")
    next_stage = STAGES[STAGES.index(stage) + 1]
    project["stage"] = next_stage
    return next_stage
