import io
import json
import shutil
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from saas_creative_director.maintenance import (
    MANIFEST_PATH,
    LEGACY_MANAGED,
    bootstrap_managed_defaults,
    build_release_archive,
    create_release_manifest,
    health_check,
    initialize,
    load_release_policy,
    locate_release,
    operation_lock,
    rollback,
    safe_extract,
    semver,
    stage_release,
    update,
    verify_release,
)


REPOSITORY = Path(__file__).resolve().parents[1]
PRIVATE_SENTINEL = b"synthetic-private-client-secret-8db1f5"


def release_tree(parent: Path, name: str = "release") -> Path:
    result = parent / name
    result.mkdir()
    stage_release(REPOSITORY, result)
    return result


def add_tar_file(archive: tarfile.TarFile, name: str, content: bytes = b"x") -> None:
    member = tarfile.TarInfo(name)
    member.size = len(content)
    archive.addfile(member, io.BytesIO(content))


class MaintenanceTests(unittest.TestCase):
    def test_semver(self):
        self.assertEqual(semver("v1.2.3"), (1, 2, 3))
        with self.assertRaises(ValueError):
            semver("latest")

    def test_policy_keeps_every_user_tree_outside_managed_inventory(self):
        policy = load_release_policy(REPOSITORY)
        self.assertEqual(
            set(policy["protected_paths"]),
            {"INBOX", "projects", "config", "overrides", "knowledge/custom"},
        )
        for protected in policy["protected_paths"]:
            self.assertFalse(
                any(
                    protected == managed
                    or protected.startswith(managed + "/")
                    or managed.startswith(protected + "/")
                    for managed in policy["managed_paths"]
                )
            )

    def test_factory_config_uses_official_github_repository(self):
        factory = json.loads((REPOSITORY / "core" / "defaults" / "config" / "local.json").read_text())
        example = json.loads((REPOSITORY / "config" / "local.example.json").read_text())
        self.assertEqual(factory["github_repository"], "denius89/saas-creative-director")
        self.assertEqual(example["github_repository"], "denius89/saas-creative-director")

    def test_legacy_bootstrap_payload_matches_managed_knowledge(self):
        for relative in ("knowledge/current-motion", "knowledge/anti-patterns"):
            canonical = REPOSITORY / relative
            payload = REPOSITORY / "core" / "defaults" / "managed" / relative
            canonical_files = {
                path.relative_to(canonical).as_posix(): path.read_bytes()
                for path in canonical.rglob("*")
                if path.is_file()
            }
            payload_files = {
                path.relative_to(payload).as_posix(): path.read_bytes()
                for path in payload.rglob("*")
                if path.is_file()
            }
            self.assertEqual(payload_files, canonical_files)

    def test_legacy_bootstrap_atomically_completes_compatible_partial_tree(self):
        with tempfile.TemporaryDirectory() as name:
            installed = release_tree(Path(name), "installed")
            destination = installed / "knowledge" / "current-motion"
            missing = destination / "2026-h2.json"
            missing.unlink()

            self.assertTrue(bootstrap_managed_defaults(installed))
            self.assertEqual(
                missing.read_bytes(),
                (installed / "core" / "defaults" / "managed" / "knowledge" / "current-motion" / "2026-h2.json").read_bytes(),
            )
            self.assertFalse(bootstrap_managed_defaults(installed))

    def test_legacy_bootstrap_rejects_conflicting_existing_tree(self):
        with tempfile.TemporaryDirectory() as name:
            installed = release_tree(Path(name), "installed")
            destination_file = installed / "knowledge" / "anti-patterns" / "README.md"
            destination_file.write_text("local conflict\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "changed files: README.md"):
                bootstrap_managed_defaults(installed)
            self.assertEqual(destination_file.read_text(encoding="utf-8"), "local conflict\n")

    def test_health_check_rejects_incomplete_bootstrap_destination(self):
        with tempfile.TemporaryDirectory() as name:
            installed = release_tree(Path(name), "installed")
            for relative in ("INBOX", "projects", "config", "overrides", "knowledge/custom"):
                (installed / relative).mkdir(parents=True, exist_ok=True)
            (installed / "knowledge" / "current-motion" / "2026-h2.json").unlink()

            self.assertEqual(health_check(installed), 1)

    def test_release_excludes_private_and_unmanaged_canaries(self):
        with tempfile.TemporaryDirectory() as name:
            base = Path(name)
            source = release_tree(base)
            private_paths = (
                "INBOX/customer/brief.txt",
                "projects/acme/project.json",
                "config/local.json",
                "overrides/private.md",
                "knowledge/custom/private.md",
                "private-build-note.txt",
            )
            for relative in private_paths:
                path = source / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(PRIVATE_SENTINEL)
            dependency_bin = source / "figma-plugin" / "node_modules" / ".bin"
            dependency_bin.mkdir(parents=True)
            (dependency_bin / "tsserver").symlink_to(source / "figma-plugin" / "package.json")
            archive, checksum = build_release_archive(source, base / "dist")
            self.assertTrue(checksum.is_file())
            unpacked = base / "unpacked"
            unpacked.mkdir()
            safe_extract(archive, unpacked)
            built = locate_release(unpacked)
            verify_release(built, expected_asset_name=archive.name)
            names = {path.relative_to(built).as_posix() for path in built.rglob("*")}
            self.assertFalse(any(name == "INBOX" or name.startswith("INBOX/") for name in names))
            self.assertFalse(any(name == "projects" or name.startswith("projects/") for name in names))
            self.assertFalse(any(name == "config" or name.startswith("config/") for name in names))
            self.assertFalse(any(name == "overrides" or name.startswith("overrides/") for name in names))
            self.assertNotIn("knowledge/custom/private.md", names)
            self.assertNotIn("private-build-note.txt", names)
            self.assertFalse(any("node_modules" in Path(name).parts for name in names))
            for path in built.rglob("*"):
                if path.is_file():
                    self.assertNotIn(PRIVATE_SENTINEL, path.read_bytes())

    def test_release_builder_still_rejects_links_in_included_sources(self):
        with tempfile.TemporaryDirectory() as name:
            base = Path(name)
            source = release_tree(base)
            (source / "core" / "unsafe-link").symlink_to(source / "README.md")
            with self.assertRaisesRegex(ValueError, "may not contain links"):
                build_release_archive(source, base / "dist")

    def test_manifest_is_required_exact_and_hash_checked(self):
        with tempfile.TemporaryDirectory() as name:
            base = Path(name)
            source = release_tree(base)
            verify_release(source)
            (source / "core" / "unexpected.txt").write_text("extra", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "inventory mismatch"):
                verify_release(source)
            (source / "core" / "unexpected.txt").unlink()
            (source / MANIFEST_PATH).unlink()
            with self.assertRaisesRegex(ValueError, "manifest is required"):
                verify_release(source)
            create_release_manifest(source)
            (source / "README.md").write_text("tampered", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "integrity check failed"):
                verify_release(source)

    def test_safe_extract_rejects_traversal_links_specials_and_duplicates(self):
        cases = {}
        with tempfile.TemporaryDirectory() as name:
            base = Path(name)
            traversal = base / "traversal.tar.gz"
            with tarfile.open(traversal, "w:gz") as archive:
                add_tar_file(archive, "../outside.txt", b"overwrite")
            cases["traversal"] = traversal

            symlink = base / "symlink.tar.gz"
            with tarfile.open(symlink, "w:gz") as archive:
                member = tarfile.TarInfo("release/link")
                member.type = tarfile.SYMTYPE
                member.linkname = "../../outside.txt"
                archive.addfile(member)
            cases["symlink"] = symlink

            hardlink = base / "hardlink.tar.gz"
            with tarfile.open(hardlink, "w:gz") as archive:
                member = tarfile.TarInfo("release/link")
                member.type = tarfile.LNKTYPE
                member.linkname = "release/file"
                archive.addfile(member)
            cases["hardlink"] = hardlink

            fifo = base / "fifo.tar.gz"
            with tarfile.open(fifo, "w:gz") as archive:
                member = tarfile.TarInfo("release/pipe")
                member.type = tarfile.FIFOTYPE
                archive.addfile(member)
            cases["fifo"] = fifo

            duplicate = base / "duplicate.tar.gz"
            with tarfile.open(duplicate, "w:gz") as archive:
                add_tar_file(archive, "release/file", b"one")
                add_tar_file(archive, "release/file", b"two")
            cases["duplicate"] = duplicate

            outside = base / "outside.txt"
            outside.write_bytes(PRIVATE_SENTINEL)
            for label, archive in cases.items():
                destination = base / f"extract-{label}"
                destination.mkdir()
                with self.subTest(label=label), self.assertRaises(ValueError):
                    safe_extract(archive, destination)
                self.assertEqual(outside.read_bytes(), PRIVATE_SENTINEL)
                self.assertEqual(list(destination.iterdir()), [])

    def test_safe_extract_enforces_expansion_limits(self):
        with tempfile.TemporaryDirectory() as name:
            base = Path(name)
            archive_path = base / "large.tar.gz"
            with tarfile.open(archive_path, "w:gz") as archive:
                add_tar_file(archive, "release/file", b"12345")
            destination = base / "extract"
            destination.mkdir()
            limits = {
                "maximum_archive_bytes": 1024 * 1024,
                "maximum_files": 10,
                "maximum_file_bytes": 4,
                "maximum_expanded_bytes": 10,
            }
            with self.assertRaisesRegex(ValueError, "file size limit"):
                safe_extract(archive_path, destination, limits)
            self.assertEqual(list(destination.iterdir()), [])

    def test_built_release_bootstraps_factory_defaults_on_clean_install(self):
        with tempfile.TemporaryDirectory() as name:
            base = Path(name)
            archive, _ = build_release_archive(REPOSITORY, base / "dist")
            unpacked = base / "install"
            unpacked.mkdir()
            safe_extract(archive, unpacked)
            installed = locate_release(unpacked)
            self.assertFalse((installed / "config").exists())
            self.assertFalse((installed / "INBOX").exists())
            self.assertEqual(initialize(installed), 0)
            self.assertTrue((installed / "config" / "local.json").is_file())
            self.assertTrue((installed / "INBOX" / "README.md").is_file())

    def test_update_and_transaction_rollback_preserve_all_private_canaries(self):
        with tempfile.TemporaryDirectory() as name:
            base = Path(name)
            archive, _ = build_release_archive(REPOSITORY, base / "dist")
            unpacked = base / "install"
            unpacked.mkdir()
            safe_extract(archive, unpacked)
            installed = locate_release(unpacked)
            self.assertEqual(initialize(installed), 0)
            canaries = {}
            for relative in (
                "INBOX/customer/brief.bin",
                "projects/acme/project.json",
                "config/local.json",
                "overrides/private.md",
                "knowledge/custom/private.md",
            ):
                path = installed / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(PRIVATE_SENTINEL + relative.encode())
                canaries[relative] = path.read_bytes()
            stale = installed / "core" / "stale-managed-file.txt"
            stale.write_text("old managed file", encoding="utf-8")

            self.assertEqual(update(installed, str(archive), allow_major=False), 0)
            self.assertFalse(stale.exists())
            for relative, expected in canaries.items():
                self.assertEqual((installed / relative).read_bytes(), expected)
            transaction_id = json.loads((installed / ".scd" / "state.json").read_text())["transaction_id"]

            self.assertEqual(rollback(installed, None, transaction_id), 0)
            self.assertTrue(stale.is_file())
            for relative, expected in canaries.items():
                self.assertEqual((installed / relative).read_bytes(), expected)

    def test_published_0_6_policy_bootstraps_new_knowledge_and_rolls_back_local_legacy_backup(self):
        with tempfile.TemporaryDirectory() as name:
            base = Path(name)
            candidate = release_tree(base, "candidate")
            installed = base / "installed"
            shutil.copytree(candidate, installed)

            # Represent the published 0.6 tree before the candidate arrived: it
            # had no release policy/required manifest and treated INBOX as a
            # managed path. Keep only facts the migration needs to recognize.
            (installed / MANIFEST_PATH).unlink()
            (installed / "core" / "release-policy.json").unlink()
            shutil.rmtree(installed / "core" / "defaults")
            shutil.rmtree(installed / "knowledge" / "current-motion")
            shutil.rmtree(installed / "knowledge" / "anti-patterns")
            (installed / "README.md").write_text("legacy product marker\n", encoding="utf-8")
            legacy_private = installed / "INBOX" / "customer" / "brief.bin"
            legacy_private.parent.mkdir(parents=True)
            legacy_private.write_bytes(b"legacy-private-value")
            for relative in ("projects", "config", "overrides", "knowledge/custom"):
                (installed / relative).mkdir(parents=True, exist_ok=True)
            local_config = installed / "config" / "local.json"
            local_config.write_bytes(PRIVATE_SENTINEL + b"-config")
            legacy_dependency = installed / "figma-plugin" / "node_modules" / ".bin"
            legacy_dependency.mkdir(parents=True)
            (legacy_dependency / "tsc").symlink_to(installed / "figma-plugin" / "package.json")

            backups = installed / ".scd" / "backups"
            backups.mkdir(parents=True)
            legacy_backup = backups / "v0.6.0-20260927T120000Z.tar.gz"
            with tarfile.open(legacy_backup, "w:gz") as archive:
                for relative in LEGACY_MANAGED:
                    path = installed / relative
                    if path.exists():
                        archive.add(path, arcname=relative, recursive=True)

            # Emulate the exact hard-coded 0.6 copy pass: candidate core and
            # launcher arrive, while the two newly managed directories do not.
            for relative in LEGACY_MANAGED:
                incoming = candidate / relative
                if not incoming.exists():
                    continue
                target = installed / relative
                if target.is_dir():
                    shutil.rmtree(target)
                elif target.exists():
                    target.unlink()
                if incoming.is_dir():
                    shutil.copytree(incoming, target)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(incoming, target)
            self.assertFalse((installed / "knowledge" / "current-motion").exists())
            self.assertFalse((installed / "knowledge" / "anti-patterns").exists())

            self.assertTrue(bootstrap_managed_defaults(installed))
            self.assertTrue((installed / "knowledge" / "current-motion" / "2026-h2.json").is_file())
            self.assertTrue((installed / "knowledge" / "anti-patterns" / "generic-ai-storyboard.json").is_file())
            self.assertFalse(bootstrap_managed_defaults(installed))

            # Change the live private value after the old backup was created.
            # A safe rollback must never restore the backup's old INBOX copy.
            current_private = PRIVATE_SENTINEL + b"-current-inbox"
            legacy_private.write_bytes(current_private)
            self.assertEqual(rollback(installed, str(legacy_backup)), 0)
            self.assertEqual((installed / "README.md").read_text(), "legacy product marker\n")
            self.assertEqual(legacy_private.read_bytes(), current_private)
            self.assertEqual(local_config.read_bytes(), PRIVATE_SENTINEL + b"-config")
            self.assertFalse((installed / "knowledge" / "current-motion").exists())
            self.assertFalse((installed / "knowledge" / "anti-patterns").exists())

    def test_external_manifest_free_legacy_backup_is_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            base = Path(name)
            archive, _ = build_release_archive(REPOSITORY, base / "dist")
            unpacked = base / "install"
            unpacked.mkdir()
            safe_extract(archive, unpacked)
            installed = locate_release(unpacked)
            self.assertEqual(initialize(installed), 0)
            external = base / "v0.6.0-20260927T120000Z.tar.gz"
            with tarfile.open(external, "w:gz") as output:
                add_tar_file(output, "core/VERSION", b"0.6.0\n")
            with self.assertRaisesRegex(ValueError, "only from this installation"):
                rollback(installed, str(external))

    def test_failed_health_check_restores_previous_managed_tree(self):
        with tempfile.TemporaryDirectory() as name:
            base = Path(name)
            archive, _ = build_release_archive(REPOSITORY, base / "dist")
            unpacked = base / "install"
            unpacked.mkdir()
            safe_extract(archive, unpacked)
            installed = locate_release(unpacked)
            self.assertEqual(initialize(installed), 0)
            original_readme = (installed / "README.md").read_bytes()
            private = installed / "INBOX" / "private.bin"
            private.write_bytes(PRIVATE_SENTINEL)

            candidate = release_tree(base, "candidate")
            (candidate / "README.md").write_text("candidate content", encoding="utf-8")
            create_release_manifest(candidate)
            with mock.patch("saas_creative_director.maintenance.health_check", return_value=1):
                with self.assertRaisesRegex(RuntimeError, "health check failed"):
                    update(installed, str(candidate), allow_major=False)
            self.assertEqual((installed / "README.md").read_bytes(), original_readme)
            self.assertEqual(private.read_bytes(), PRIVATE_SENTINEL)
            journals = [json.loads(path.read_text()) for path in (installed / ".scd" / "transactions").glob("*.json")]
            self.assertIn("rolled_back", {journal["status"] for journal in journals})

    def test_live_lock_rejects_concurrent_maintenance(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            with operation_lock(root, "first"):
                with self.assertRaisesRegex(ValueError, "Another maintenance operation"):
                    with operation_lock(root, "second"):
                        self.fail("second lock must not be acquired")


if __name__ == "__main__":
    unittest.main()
