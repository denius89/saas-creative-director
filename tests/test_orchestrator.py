import unittest

from saas_creative_director.orchestrator import advance, next_action


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


if __name__ == "__main__":
    unittest.main()

