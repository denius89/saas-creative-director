import tempfile
import unittest
from pathlib import Path

from saas_creative_director.orchestrator import advance, next_action
from saas_creative_director.workspace import gate_revision, initialize_project, load_project, refresh_gate_approvals, write_json


class OrchestratorTests(unittest.TestCase):
    def project(self, stage="intake"):
        return {
            "stage": stage,
            "gates": {
                "strategy": {"status": "PENDING"},
                "creative_direction": {"status": "PENDING"},
                "production": {"status": "PENDING"},
            },
        }

    def test_routes_to_one_skill(self):
        action = next_action(self.project())
        self.assertEqual(action.kind, "stage")
        self.assertIn("client-project-intake", action.instruction)

    def test_gate_blocks_advance(self):
        project = self.project("video_strategy")
        with self.assertRaisesRegex(ValueError, "Approve strategy"):
            advance(project)
        self.assertEqual(project["stage"], "video_strategy")

    def test_approval_unlocks_next_stage(self):
        project = self.project("video_strategy")
        project["gates"]["strategy"]["status"] = "APPROVED"
        self.assertEqual(advance(project), "reference_research")

    def test_creative_gate_follows_motion_direction(self):
        narrative = next_action(self.project("narrative"))
        self.assertNotIn("creative_direction", narrative.instruction)
        visual = next_action(self.project("visual_direction"))
        self.assertIn("motion-design-director", visual.instruction)
        self.assertIn("creative_direction", visual.instruction)
        with self.assertRaisesRegex(ValueError, "Approve creative direction"):
            advance(self.project("visual_direction"))

    def test_requested_changes_are_exposed_as_next_action(self):
        project = self.project("video_strategy")
        project["gates"]["strategy"] = {"status": "CHANGES_REQUESTED", "notes": "Clarify proof."}
        action = next_action(project)
        self.assertEqual(action.kind, "changes_requested")
        self.assertEqual(action.instruction, "Clarify proof.")

    def test_revision_change_invalidates_only_affected_gates(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name) / "project"
            initialize_project(root, "Test")
            project = load_project(root)
            for relative in (
                "artifacts/video-strategy.json", "artifacts/narrative.json",
                "artifacts/visual-direction.json", "artifacts/storyboard.json",
                "artifacts/figma-manifest.json", "reviews/production-review.md",
            ):
                if relative.endswith(".json"):
                    write_json(root / relative, {"value": relative})
                else:
                    (root / relative).write_text("Production review passed", encoding="utf-8")
            for gate_name in project["gates"]:
                revision = gate_revision(root, project, gate_name)
                project["gates"][gate_name].update({"status": "APPROVED", **revision.as_dict()})

            write_json(root / "artifacts" / "storyboard.json", {"value": "changed"})
            self.assertEqual(refresh_gate_approvals(root, project), ["production"])
            self.assertEqual(project["gates"]["strategy"]["status"], "APPROVED")
            self.assertEqual(project["gates"]["creative_direction"]["status"], "APPROVED")
            self.assertEqual(project["gates"]["production"]["status"], "STALE")
            persisted = __import__("json").loads((root / "reviews" / "gates" / "production.json").read_text())
            self.assertEqual(persisted["status"], "STALE")
            self.assertEqual(persisted["current_revision"], project["gates"]["production"]["current_revision"])


if __name__ == "__main__":
    unittest.main()
