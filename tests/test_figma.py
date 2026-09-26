import json
import unittest
from pathlib import Path

from saas_creative_director.figma import build_manifest


class FigmaManifestTests(unittest.TestCase):
    def test_example_creates_editable_scene_layers(self):
        root = Path(__file__).resolve().parents[1] / "examples" / "ledgerly"
        manifest = build_manifest(root)
        self.assertEqual(len(manifest["scenes"]), 4)
        self.assertEqual(manifest["document_pages"][3], "04 Storyboard")
        self.assertTrue(all(scene["layers"] for scene in manifest["scenes"]))
        self.assertTrue(all(scene["annotations"]["locked"] for scene in manifest["scenes"]))


if __name__ == "__main__":
    unittest.main()

