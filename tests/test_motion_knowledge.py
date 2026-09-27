from __future__ import annotations

import json
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_current_motion_has_traceable_freshness_and_known_sources() -> None:
    current = json.loads((ROOT / "knowledge/current-motion/2026-h2.json").read_text())
    curated_text = (ROOT / "knowledge/references/curated-sources.yaml").read_text()

    assert current["status"] in {"provisional", "reviewed", "stale"}
    assert current["confidence"] in {"low", "medium", "high"}
    assert date.fromisoformat(current["review_after"]) > date.fromisoformat(current["observed_at"])
    assert current["inspection_method"]
    assert current["signals"]
    for source_id in current["source_ids"]:
        assert f"id: {source_id}" in curated_text
    for signal in current["signals"]:
        assert signal["statement"]
        assert signal["use"]
        assert signal["limits"]
        assert signal["confidence"] in {"confirmed", "supported", "hypothesis"}


def test_anti_patterns_are_conditional_and_repairable() -> None:
    library = json.loads((ROOT / "knowledge/anti-patterns/generic-ai-storyboard.json").read_text())
    ids = [item["id"] for item in library["items"]]

    assert len(ids) == len(set(ids))
    assert len(ids) >= 6
    for item in library["items"]:
        assert item["trigger"]
        assert item["why_it_fails"]
        assert item["repair"]
        assert item["exceptions"]
        assert item["severity"] in {"minor", "major", "blocking"}


def test_pattern_ids_are_unique() -> None:
    pattern_files = sorted((ROOT / "knowledge/patterns").glob("*/*.md"))
    ids: list[str] = []
    for path in pattern_files:
        marker = "- Pattern ID: `"
        line = next(line for line in path.read_text().splitlines() if line.startswith(marker))
        ids.append(line.removeprefix(marker).removesuffix("`"))

    assert ids
    assert len(ids) == len(set(ids))
