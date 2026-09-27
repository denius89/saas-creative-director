import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from saas_creative_director.cli import main


class RuntimeCliTests(unittest.TestCase):
    def test_init_prepare_and_unknown_usage_are_resumable_and_private(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name) / "project"
            with redirect_stdout(StringIO()):
                self.assertEqual(main(["init", str(root), "--name", "Private client"]), 0)
                self.assertEqual(main(["prepare-runtime", str(root)]), 0)
                self.assertEqual(main([
                    "record-usage", str(root), "--run-id", "host-run-1", "--stage", "intake",
                ]), 0)
            checkpoint = json.loads((root / "reviews" / "checkpoint.json").read_text())
            self.assertEqual(checkpoint["execution_policy"]["enforcement_scope"], "advisory")
            self.assertNotIn("Private client", json.dumps(checkpoint))
            event = json.loads((root / "reviews" / "usage-ledger.jsonl").read_text())
            self.assertEqual(event["event_kind"], "model_usage")
            self.assertIsNone(event["input_tokens"])
            self.assertIsNone(event["estimated_usd"])
            self.assertNotIn("prompt", event)


if __name__ == "__main__":
    unittest.main()
