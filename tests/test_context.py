import tempfile
import unittest
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from saas_creative_director.context import build_checkpoint, build_context_pack, prepare_stage_runtime
from saas_creative_director.workspace import initialize_project, write_json


class ContextTests(unittest.TestCase):
    def test_pack_is_deterministic_and_preserves_referenced_evidence(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name) / "project"
            initialize_project(root, "Test")
            write_json(root / "artifacts" / "source-registry.json", {"sources": [{
                "id": "SRC-001", "kind": "product", "title": "Docs",
                "location": "inputs/docs.pdf", "authority": "primary", "captured_at": "2026-09-27",
            }]})
            write_json(root / "artifacts" / "evidence.json", {"evidence": [{
                "id": "EV-001", "claim": "Fast", "status": "CONFIRMED", "source_ids": ["SRC-001"], "reasoning": "Direct",
            }]})
            write_json(root / "artifacts" / "narrative.json", {"direction": "A", "evidence_ids": ["EV-001"]})

            first = build_context_pack(root, "narrative", max_chars=10)
            second = build_context_pack(root, "narrative", max_chars=10)
            self.assertEqual(first, second)
            self.assertEqual([item["id"] for item in first["evidence"]], ["EV-001"])
            self.assertEqual([item["id"] for item in first["sources"]], ["SRC-001"])

    def test_checkpoint_is_stable_and_contains_pointers_not_content(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name) / "project"
            initialize_project(root, "Secret client")
            first = build_checkpoint(root, ["Continue"], ["Need proof"])
            second = build_checkpoint(root, ["Continue"], ["Need proof"])
            self.assertEqual(first, second)
            self.assertNotIn("Secret client", str(first))

    def test_runtime_state_uses_policy_cache_and_writes_resumable_files(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name) / "project"
            initialize_project(root, "Test")
            first = prepare_stage_runtime(root)
            second = prepare_stage_runtime(root)
            self.assertFalse(first["cache_hit"])
            self.assertTrue(second["cache_hit"])
            self.assertTrue(second["context_path"].is_file())
            self.assertTrue(second["checkpoint_path"].is_file())
            pack = json.loads(second["context_path"].read_text())
            schema = json.loads((Path(__file__).resolve().parents[1] / "core" / "schemas" / "context-pack.schema.json").read_text())
            Draft202012Validator(schema).validate(pack)
            self.assertEqual(pack["execution_policy"]["enforcement_scope"], "advisory")
            self.assertFalse(pack["execution_policy"]["auto_enable_usage_credits"])


if __name__ == "__main__":
    unittest.main()
