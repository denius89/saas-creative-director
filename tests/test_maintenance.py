import tempfile
import unittest
from pathlib import Path

from saas_creative_director.maintenance import copy_managed, semver


class MaintenanceTests(unittest.TestCase):
    def test_semver(self):
        self.assertEqual(semver("v1.2.3"), (1, 2, 3))
        with self.assertRaises(ValueError):
            semver("latest")

    def test_update_copy_preserves_user_data(self):
        with tempfile.TemporaryDirectory() as name:
            base = Path(name)
            source = base / "release"
            target = base / "install"
            (source / "core").mkdir(parents=True)
            (source / "core" / "VERSION").write_text("0.5.1\n")
            (target / "core").mkdir(parents=True)
            (target / "core" / "VERSION").write_text("0.5.0\n")
            (target / "projects" / "client").mkdir(parents=True)
            private = target / "projects" / "client" / "brief.txt"
            private.write_text("keep me")
            copy_managed(source, target)
            self.assertEqual((target / "core" / "VERSION").read_text(), "0.5.1\n")
            self.assertEqual(private.read_text(), "keep me")


if __name__ == "__main__":
    unittest.main()

