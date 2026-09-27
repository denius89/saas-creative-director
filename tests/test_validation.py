import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from saas_creative_director.validation import validate_for_export, validate_for_gate, validate_project
from saas_creative_director.orchestrator import advance
from saas_creative_director.workspace import initialize_project, load_project, write_json


class ValidationTests(unittest.TestCase):
    def test_initialized_project_is_structurally_valid(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name) / "project"
            initialize_project(root, "Test")
            self.assertEqual(validate_project(root), [])

    def test_unknown_evidence_reference_fails(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name) / "project"
            initialize_project(root, "Test")
            (root / "artifacts" / "strategy.json").write_text(json.dumps({"evidence_ids": ["EV-404"]}))
            issues = validate_project(root)
            self.assertTrue(any("unknown evidence id" in issue.message for issue in issues))

    def test_runtime_schema_and_locator_are_enforced(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name) / "project"
            initialize_project(root, "Test")
            write_json(root / "artifacts" / "source-registry.json", {"sources": [{
                "id": "bad-id", "kind": "product", "title": "Product", "location": "unknown",
                "authority": "primary", "captured_at": "2026-09-27",
            }]})
            issues = validate_project(root)
            self.assertTrue(any("does not match" in issue.message for issue in issues))
            self.assertTrue(any("must locate the source" in issue.message for issue in issues))

    def test_advance_requires_substantive_current_stage_output(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name) / "project"
            initialize_project(root, "Test")
            project = load_project(root)
            with self.assertRaisesRegex(ValueError, "at least one locatable source"):
                advance(project, root)
            self.assertEqual(project["stage"], "intake")

    def test_later_stage_requires_prior_outputs(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name) / "project"
            initialize_project(root, "Test")
            project = load_project(root)
            project["stage"] = "video_strategy"
            write_json(root / "project.json", project)
            issues = validate_project(root)
            self.assertTrue(any("product-intelligence.json" in issue.path for issue in issues))
            self.assertTrue(any("competitor-intelligence.json" in issue.path for issue in issues))

    def test_v1_storyboard_events_are_bound_to_scene_and_objects(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name) / "project"
            initialize_project(root, "Test")
            write_json(root / "artifacts" / "storyboard.json", {
                "schema_version": "1.0", "revision": "sb-1", "title": "Board",
                "total_duration_seconds": 5,
                "scenes": [{
                    "id": "S01", "semantic_id": "scene/S01", "revision": "s1",
                    "duration_seconds": 5, "purpose": "Explain", "message": "Message",
                    "composition_pattern": "flow", "pattern_version": "1", "recipe": "horizontal-flow",
                    "recipe_version": "1", "objects": [{
                        "semantic_id": "S01/hero", "name": "Hero", "type": "frame", "role": "primary",
                        "bounds": {"x": 0, "y": 0, "width": 100, "height": 100},
                    }],
                    "attention_sequence": ["hero"],
                    "states": [{"id": "start", "at_seconds": 0, "object_ids": ["S01/hero"], "description": "Start"}],
                    "events": [{"id": "late", "at_seconds": 6, "type": "move", "object_ids": ["missing"], "description": "Late"}],
                    "motion": [],
                    "transition_anchors": [{"id": "out", "edge": "out", "at_seconds": 5, "object_id": "S01/hero", "carry_to_scene_id": "S99"}],
                    "transition_out": "cut", "locked": [], "creative_freedom": [], "evidence_ids": [],
                }],
            })
            issues = validate_project(root)
            self.assertTrue(any("must not exceed scene duration" in issue.message for issue in issues))
            self.assertTrue(any("unknown semantic object id: missing" in issue.message for issue in issues))
            self.assertTrue(any("unknown scene id: S99" in issue.message for issue in issues))

    def test_v1_1_panel_sequence_validates_temporal_and_identity_references(self):
        fixture_path = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "figma" / "TEMPORAL_PANEL_STORYBOARD.json"
        fixture = json.loads(fixture_path.read_text())
        with tempfile.TemporaryDirectory() as name:
            root = Path(name) / "project"
            initialize_project(root, "Test")
            write_json(root / "artifacts" / "storyboard.json", fixture)
            issues = validate_project(root)
            self.assertFalse(any(issue.path.startswith("artifacts/storyboard.json") for issue in issues), issues)

            broken = copy.deepcopy(fixture)
            panels = broken["scenes"][0]["panels"]
            panels[1]["id"] = panels[0]["id"]
            panels[2]["at_seconds"] = panels[1]["at_seconds"]
            panels[3]["layers"][0]["presentation_id"] = "missing-presentation"
            panels[4]["event_ids"] = []
            panels[5]["focal_object_id"] = "S03/object/missing"
            write_json(root / "artifacts" / "storyboard.json", broken)
            issues = validate_project(root)
            messages = [issue.message for issue in issues if issue.path.startswith("artifacts/storyboard.json")]
            self.assertTrue(any("duplicate panel id" in message for message in messages))
            self.assertTrue(any("strictly increasing" in message for message in messages))
            self.assertTrue(any("unknown presentation id" in message for message in messages))
            self.assertTrue(any("visual event is not represented" in message for message in messages))
            self.assertTrue(any("focal object must be visible" in message for message in messages))

    def test_manifest_preflight_does_not_require_manifest_output(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name) / "project"
            initialize_project(root, "Test")
            project = load_project(root)
            project["stage"] = "production_review"
            write_json(root / "project.json", project)
            write_json(root / "artifacts" / "visual-direction.json", {"tokens": {}})
            write_json(root / "artifacts" / "storyboard.json", {
                "title": "Board", "total_duration_seconds": 1,
                "scenes": [{
                    "id": "S01", "duration_seconds": 1, "purpose": "P", "message": "M",
                    "composition_pattern": "flow", "objects": [{}], "attention_sequence": [],
                    "motion": [], "transition_out": "cut", "locked": [], "creative_freedom": [],
                    "evidence_ids": [],
                }],
            })
            issues = validate_for_export(root)
            self.assertFalse(any(issue.path.startswith("artifacts/figma-manifest.json") for issue in issues))

    def test_creative_gate_requires_motion_direction(self):
        source = Path(__file__).resolve().parents[1] / "examples" / "ledgerly"
        with tempfile.TemporaryDirectory() as name:
            root = Path(name) / "project"
            shutil.copytree(source, root)
            project = load_project(root)
            project["stage"] = "visual_direction"
            write_json(root / "project.json", project)
            (root / "artifacts" / "motion-direction.json").unlink()
            issues = validate_for_gate(root, project, "creative_direction")
            self.assertTrue(any(issue.path == "artifacts/motion-direction.json" for issue in issues))

    def test_production_gate_rejects_blocked_or_open_blocker_qa(self):
        source = Path(__file__).resolve().parents[1] / "examples" / "ledgerly"
        with tempfile.TemporaryDirectory() as name:
            root = Path(name) / "project"
            shutil.copytree(source, root)
            project = load_project(root)
            project["stage"] = "production_review"
            write_json(root / "project.json", project)
            review = json.loads((root / "reviews" / "visual-qa.json").read_text())
            review["status"] = "BLOCKED"
            review["findings"].append({
                "id": "BLOCK-1", "scene_id": "S01", "object_id": None,
                "criterion": "Product truth", "observed_evidence": "State is invented.",
                "severity": "blocker", "suggested_repair": "Use a verified state.", "status": "open",
            })
            write_json(root / "reviews" / "visual-qa.json", review)
            issues = validate_for_gate(root, project, "production")
            self.assertTrue(any("BLOCKED visual QA" in issue.message for issue in issues))
            self.assertTrue(any("open blocker" in issue.message for issue in issues))


if __name__ == "__main__":
    unittest.main()
