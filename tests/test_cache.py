import tempfile
import unittest
from pathlib import Path

from saas_creative_director.cache import ArtifactCache, make_cache_key


class CacheTests(unittest.TestCase):
    def test_cache_is_project_scoped_and_dependency_bound(self):
        with tempfile.TemporaryDirectory() as name:
            base = Path(name) / "cache"
            key = make_cache_key({"source": "digest"}, {"schema": "1"})
            first = ArtifactCache(base, "project-a")
            second = ArtifactCache(base, "project-b")
            first.put(key, {"result": 1}, {"source": "old"})
            self.assertEqual(first.get(key, {"source": "old"}), {"result": 1})
            self.assertIsNone(first.get(key, {"source": "new"}))
            self.assertIsNone(second.get(key, {"source": "old"}))

    def test_targeted_invalidation(self):
        with tempfile.TemporaryDirectory() as name:
            cache = ArtifactCache(Path(name), "project")
            first = make_cache_key({"id": 1})
            second = make_cache_key({"id": 2})
            cache.put(first, 1, {"storyboard": "a"})
            cache.put(second, 2, {"strategy": "b"})
            self.assertEqual(cache.invalidate({"storyboard"}), 1)
            self.assertIsNone(cache.get(first, {"storyboard": "a"}))
            self.assertEqual(cache.get(second, {"strategy": "b"}), 2)


if __name__ == "__main__":
    unittest.main()
