import json
import tempfile
import unittest
from pathlib import Path

from saas_creative_director.validation import validate_project
from saas_creative_director.workspace import initialize_project


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


if __name__ == "__main__":
    unittest.main()

