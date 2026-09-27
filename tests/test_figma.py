import copy
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from jsonschema import Draft202012Validator

from saas_creative_director.figma import FigmaManifestError, build_manifest, preflight_manifest


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "ledgerly"


def flatten(nodes):
    for node in nodes:
        yield node
        yield from flatten(node.get("children", []))


def example_manifest(storyboard=None, visual=None):
    storyboard = storyboard or json.loads((EXAMPLE / "artifacts" / "storyboard.json").read_text())
    visual = visual or json.loads((EXAMPLE / "artifacts" / "visual-direction.json").read_text())
    with TemporaryDirectory() as directory:
        project_root = Path(directory)
        (project_root / "artifacts").mkdir()
        (project_root / "project.json").write_text(json.dumps({"name": "Example product"}))
        (project_root / "artifacts" / "storyboard.json").write_text(json.dumps(storyboard))
        (project_root / "artifacts" / "visual-direction.json").write_text(json.dumps(visual))
        return build_manifest(project_root)


def v1_storyboard(recipe="focus-detail"):
    source = json.loads((EXAMPLE / "artifacts" / "storyboard.json").read_text())
    scene = copy.deepcopy(source["scenes"][1])
    scene.update({
        "semantic_id": "scene/S02", "revision": "S02-r1", "pattern_version": "1.0",
        "recipe": recipe, "recipe_version": "1.0",
        "states": [{"id": "ready", "at_seconds": 0, "object_ids": ["S02/hero"], "description": "Ready state"}],
        "events": [{"id": "resolve", "at_seconds": 2, "type": "state-change", "object_ids": ["S02/hero"], "from_state_id": "ready", "to_state_id": "ready", "description": "Resolve visibly"}],
        "transition_anchors": [{"id": "out", "edge": "out", "at_seconds": scene["duration_seconds"], "object_id": "S02/hero", "state_id": "ready", "description": "Carry result"}],
    })
    scene["objects"][0]["semantic_id"] = "S02/hero"
    return {"schema_version": "1.0", "revision": "storyboard-r1", "title": "V1", "total_duration_seconds": scene["duration_seconds"], "scenes": [scene]}


class FigmaManifestTests(unittest.TestCase):
    def test_manifest_is_deterministic_and_matches_strict_schema(self):
        first = example_manifest()
        second = example_manifest()
        self.assertEqual(first, second)
        self.assertEqual(first["schema_version"], "1.0")
        self.assertEqual(first["operation"], second["operation"])
        schema = json.loads((ROOT / "core" / "schemas" / "figma-manifest.schema.json").read_text())
        Draft202012Validator(schema).validate(first)

    def test_legacy_storyboard_keeps_manifest_1_0_shape(self):
        manifest = example_manifest()
        self.assertEqual(manifest["schema_version"], "1.0")
        self.assertTrue(all("sequence_mode" not in scene and "panels" not in scene for scene in manifest["scenes"]))

    def test_temporal_panel_storyboard_compiles_to_manifest_1_1(self):
        storyboard = json.loads((ROOT / "tests" / "fixtures" / "figma" / "TEMPORAL_PANEL_STORYBOARD.json").read_text())
        storyboard_schema = json.loads((ROOT / "core" / "schemas" / "storyboard.schema.json").read_text())
        Draft202012Validator(storyboard_schema).validate(storyboard)
        manifest = example_manifest(storyboard=storyboard)
        manifest_schema = json.loads((ROOT / "core" / "schemas" / "figma-manifest.schema.json").read_text())
        Draft202012Validator(manifest_schema).validate(manifest)
        self.assertEqual(manifest["schema_version"], "1.1")
        scene = manifest["scenes"][0]
        self.assertEqual(scene["sequence_mode"], "panel-sequence")
        self.assertEqual(scene["nodes"], [])
        self.assertEqual([panel["id"] for panel in scene["panels"]], ["P01", "P02", "P03", "P04", "P05", "P06"])
        self.assertEqual(scene["panels"][2]["continuity"], "continuous")
        vehicle_instances = []
        for panel in scene["panels"]:
            for node in flatten(panel["nodes"]):
                if node.get("metadata", {}).get("object_id") == "S03/object/vehicle":
                    vehicle_instances.append(node)
        self.assertEqual(len(vehicle_instances), 3)
        self.assertEqual(len({node["semantic_id"] for node in vehicle_instances}), 3)
        self.assertEqual({node["metadata"]["object_id"] for node in vehicle_instances}, {"S03/object/vehicle"})
        preflight_manifest(manifest)

    def test_three_recipes_have_distinct_deterministic_compositions(self):
        manifest = example_manifest()
        scenes_by_recipe = {}
        for scene in manifest["scenes"]:
            scenes_by_recipe.setdefault(scene["recipe"], scene)
        self.assertEqual(set(scenes_by_recipe), {"source-convergence", "horizontal-flow", "focus-detail"})
        signatures = {
            recipe: tuple((node["type"], node["role"], node["bounds"]["x"], node["bounds"]["y"]) for node in scene["nodes"])
            for recipe, scene in scenes_by_recipe.items()
        }
        self.assertEqual(len({json.dumps(value) for value in signatures.values()}), 3)

    def test_native_nodes_have_unique_stable_semantic_ids_and_visible_annotations(self):
        manifest = example_manifest()
        semantic_ids = []
        node_types = set()
        for scene in manifest["scenes"]:
            scene_nodes = list(flatten(scene["nodes"]))
            semantic_ids.extend(node["semantic_id"] for node in scene_nodes)
            node_types.update(node["type"] for node in scene_nodes)
            self.assertTrue(scene["annotations"]["purpose"])
            self.assertTrue(scene["annotations"]["locked"])
        self.assertEqual(len(semantic_ids), len(set(semantic_ids)))
        self.assertTrue({"text", "ui-card", "ui-row", "pill", "connector"}.issubset(node_types))

    def test_edge_case_fixture_marks_raster_and_unsupported_objects(self):
        fixture = json.loads((ROOT / "tests" / "fixtures" / "figma" / "FIGMA_EDGE_CASE_STORYBOARD.json").read_text())
        with TemporaryDirectory() as directory:
            project_root = Path(directory)
            (project_root / "artifacts").mkdir()
            (project_root / "project.json").write_text(json.dumps({"name": "Edge cases"}))
            (project_root / "artifacts" / "storyboard.json").write_text(json.dumps(fixture, ensure_ascii=False))
            (project_root / "artifacts" / "visual-direction.json").write_text(json.dumps({"tokens": {"font_family": "Inter"}}))
            manifest = build_manifest(project_root)
        nodes = list(flatten(manifest["scenes"][0]["nodes"]))
        raster = next(node for node in nodes if node["type"] == "raster-placeholder")
        unsupported = next(node for node in nodes if node["type"] == "asset-placeholder")
        self.assertIn("RASTER", raster["text"])
        self.assertFalse(raster["metadata"]["editable"])
        self.assertIn("UNSUPPORTED", unsupported["text"])
        self.assertEqual(manifest["scenes"][0]["assets"]["missing"], [raster["semantic_id"]])
        self.assertIn("длинный русский", manifest["scenes"][0]["annotations"]["on_screen_copy"])
        rendered_nodes = json.dumps(manifest["scenes"][0]["nodes"], ensure_ascii=False).casefold()
        for leaked_term in ("ledgerly", "payout", "invoice", "reconciliation"):
            self.assertNotIn(leaked_term, rendered_nodes)

    def test_preflight_rejects_duplicate_ids_before_render(self):
        manifest = example_manifest()
        invalid = copy.deepcopy(manifest)
        invalid["scenes"][0]["nodes"][1]["semantic_id"] = invalid["scenes"][0]["nodes"][0]["semantic_id"]
        with self.assertRaisesRegex(FigmaManifestError, "duplicate"):
            preflight_manifest(invalid)

    def test_preflight_rejects_unknown_types_and_oversized_text(self):
        manifest = example_manifest()
        invalid_type = copy.deepcopy(manifest)
        invalid_type["scenes"][0]["nodes"][0]["type"] = "external-script"
        with self.assertRaisesRegex(FigmaManifestError, "unsupported"):
            preflight_manifest(invalid_type)
        invalid_text = copy.deepcopy(manifest)
        invalid_text["scenes"][0]["nodes"][0]["text"] = "x" * 4_001
        with self.assertRaisesRegex(FigmaManifestError, "4000"):
            preflight_manifest(invalid_text)

    def test_preflight_rejects_non_finite_numbers_in_all_render_contracts(self):
        manifest = example_manifest()

        invalid_node = copy.deepcopy(manifest)
        invalid_node["scenes"][0]["nodes"][0]["bounds"]["x"] = float("nan")
        with self.assertRaisesRegex(FigmaManifestError, "finite number"):
            preflight_manifest(invalid_node)

        invalid_production = copy.deepcopy(manifest)
        invalid_production["scenes"][0]["production_semantics"]["objects"][0]["bounds"]["width"] = float("inf")
        with self.assertRaisesRegex(FigmaManifestError, "finite number"):
            preflight_manifest(invalid_production)

        invalid_timing = copy.deepcopy(manifest)
        invalid_timing["scenes"][0]["states"] = [{"at_seconds": float("nan")}]
        with self.assertRaisesRegex(FigmaManifestError, "finite number"):
            preflight_manifest(invalid_timing)

        invalid_token = copy.deepcopy(manifest)
        invalid_token["tokens"]["spacing"]["base"] = float("inf")
        with self.assertRaisesRegex(FigmaManifestError, "out-of-range"):
            preflight_manifest(invalid_token)

    def test_content_change_produces_new_revision_identity(self):
        manifest = example_manifest()
        storyboard = json.loads((EXAMPLE / "artifacts" / "storyboard.json").read_text())
        storyboard["scenes"][0]["on_screen_copy"] += " Revised."
        changed = example_manifest(storyboard=storyboard)
        self.assertNotEqual(manifest["operation"]["id"], changed["operation"]["id"])
        self.assertNotEqual(manifest["scenes"][0]["content_hash"], changed["scenes"][0]["content_hash"])
        self.assertEqual(manifest["scenes"][1]["content_hash"], changed["scenes"][1]["content_hash"])

    def test_render_context_change_invalidates_rendered_scene_hashes(self):
        manifest = example_manifest()
        visual = json.loads((EXAMPLE / "artifacts" / "visual-direction.json").read_text())
        visual["tokens"]["font_family"] = "Roboto"
        changed = example_manifest(visual=visual)
        self.assertNotEqual(manifest["operation"]["id"], changed["operation"]["id"])
        self.assertTrue(
            all(
                before["content_hash"] != after["content_hash"]
                for before, after in zip(manifest["scenes"], changed["scenes"], strict=True)
            )
        )

    def test_v1_explicit_recipe_overrides_legacy_pattern_inference(self):
        storyboard = v1_storyboard("focus-detail")
        manifest = example_manifest(storyboard=storyboard)
        scene = manifest["scenes"][0]
        self.assertEqual(scene["recipe"], "focus-detail")
        self.assertEqual(scene["recipe_version"], "1.0")
        self.assertEqual(scene["recipe_selection"], "explicit")
        self.assertEqual(scene["states"][0]["id"], "ready")
        self.assertEqual(scene["events"][0]["id"], "resolve")
        self.assertEqual(scene["transition_anchors"][0]["id"], "out")
        self.assertEqual(scene["production_semantics"]["objects"][0]["semantic_id"], "S02/hero")

    def test_recipe_and_motion_contract_changes_invalidate_scene_hash(self):
        storyboard = v1_storyboard("focus-detail")
        first = example_manifest(storyboard=storyboard)
        recipe_changed = copy.deepcopy(storyboard)
        recipe_changed["scenes"][0]["recipe"] = "horizontal-flow"
        second = example_manifest(storyboard=recipe_changed)
        self.assertNotEqual(first["scenes"][0]["content_hash"], second["scenes"][0]["content_hash"])
        self.assertNotEqual(first["scenes"][0]["recipe"], second["scenes"][0]["recipe"])
        motion_changed = copy.deepcopy(storyboard)
        motion_changed["scenes"][0]["events"][0]["description"] = "Resolve with a held proof state"
        third = example_manifest(storyboard=motion_changed)
        self.assertNotEqual(first["scenes"][0]["content_hash"], third["scenes"][0]["content_hash"])

    def test_approved_token_subset_is_normalized_and_changes_hashes(self):
        base = example_manifest()
        visual = json.loads((EXAMPLE / "artifacts" / "visual-direction.json").read_text())
        visual["tokens"]["colors"] = {"accent": "#123456", "canvas": "#FAFAFA"}
        visual["tokens"]["type_scale"] = {"headline": 64}
        changed = example_manifest(visual=visual)
        self.assertEqual(changed["tokens"]["colors"]["accent"], "#123456")
        self.assertEqual(changed["tokens"]["type_scale"]["headline"], 64)
        self.assertEqual(set(changed["tokens"]), {"colors", "spacing", "type_scale"})
        self.assertTrue(all(before["content_hash"] != after["content_hash"] for before, after in zip(base["scenes"], changed["scenes"], strict=True)))


if __name__ == "__main__":
    unittest.main()
