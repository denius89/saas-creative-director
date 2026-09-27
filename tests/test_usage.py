import json
import tempfile
import unittest
from pathlib import Path

from saas_creative_director.usage import append_usage_event, normalize_usage_event, summarize_usage


class UsageTests(unittest.TestCase):
    def base_event(self):
        return {"project_id": "p1", "run_id": "r1", "stage": "storyboard"}

    def test_unknown_usage_is_null_and_secrets_are_dropped(self):
        event = normalize_usage_event({**self.base_event(), "prompt": "private", "api_key": "secret"})
        self.assertEqual(event["billing_mode"], "unknown")
        self.assertIsNone(event["input_tokens"])
        self.assertNotIn("prompt", event)
        self.assertNotIn("api_key", event)

    def test_events_are_deduplicated_and_unknown_totals_stay_null(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "usage-ledger.jsonl"
            event = self.base_event()
            self.assertTrue(append_usage_event(path, event))
            self.assertFalse(append_usage_event(path, event))
            self.assertEqual(len(path.read_text().splitlines()), 1)
            self.assertIsNone(summarize_usage(path)["input_tokens"])
            stored = json.loads(path.read_text())
            self.assertEqual(stored["usage_source"], "unknown")

    def test_subscription_cost_is_not_invented(self):
        with self.assertRaisesRegex(ValueError, "not meaningful"):
            normalize_usage_event({
                **self.base_event(), "billing_mode": "subscription", "estimated": True,
                "estimated_usd": 1.25, "price_snapshot_id": "price-1",
            })

    def test_estimated_cost_requires_price_snapshot(self):
        with self.assertRaisesRegex(ValueError, "price_snapshot_id"):
            normalize_usage_event({
                **self.base_event(), "billing_mode": "api", "estimated": True,
                "estimated_usd": 1.25,
            })

    def test_summary_separates_boundaries_from_model_usage(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "usage-ledger.jsonl"
            append_usage_event(path, {**self.base_event(), "event_kind": "stage_boundary"})
            append_usage_event(path, {**self.base_event(), "run_id": "r2", "event_kind": "model_usage", "input_tokens": 10})
            summary = summarize_usage(path)
            self.assertEqual(summary["stage_boundaries"], 1)
            self.assertEqual(summary["model_usage_events"], 1)
            self.assertEqual(summary["input_tokens"], 10)


if __name__ == "__main__":
    unittest.main()
