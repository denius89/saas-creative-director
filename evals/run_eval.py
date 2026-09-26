from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "examples/ledgerly")
    artifacts = root / "artifacts"
    evidence = json.loads((artifacts / "evidence.json").read_text())["evidence"]
    strategy = json.loads((artifacts / "video-strategy.json").read_text())
    references = json.loads((artifacts / "reference-library.json").read_text())
    narrative = json.loads((artifacts / "narrative.json").read_text())
    storyboard = json.loads((artifacts / "storyboard.json").read_text())
    benchmark_root = Path(__file__).resolve().parent / "reference-research"
    benchmark_count = sum(1 for line in (benchmark_root / "benchmark-index.yaml").read_text().splitlines() if line.lstrip().startswith("- {id:"))
    annotations = json.loads((benchmark_root / "annotations.json").read_text())["annotations"]
    checks = {
        "evidence_registry": bool(evidence) and all(item.get("status") in {"CONFIRMED", "SUPPORTED", "HYPOTHESIS"} for item in evidence),
        "strategy_options": bool(strategy.get("recommendation")) and bool(strategy.get("alternatives")),
        "reference_principles": all(item.get("reusable_visual_principles") for item in references.get("references", [])),
        "narrative_directions": len(narrative.get("directions", [])) >= 2,
        "storyboard_timing": abs(sum(scene["duration_seconds"] for scene in storyboard["scenes"]) - storyboard["total_duration_seconds"]) < 0.001,
        "handoff_annotations": all(scene.get("locked") and scene.get("creative_freedom") for scene in storyboard["scenes"]),
        "reference_benchmark_size": 20 <= benchmark_count <= 30,
        "manual_reference_annotations": len(annotations) >= 8 and all(item.get("risks_non_copy") for item in annotations),
        "honest_reference_confidence": all(item.get("inspection", {}).get("confidence") in {"low", "medium", "high"} for item in annotations),
    }
    for name, passed in checks.items():
        print(f"{'PASS' if passed else 'FAIL'} {name}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
