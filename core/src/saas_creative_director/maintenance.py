from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.parse
import urllib.request
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Iterator


INSTALLER_VERSION = "0.6.0"
MANIFEST_PATH = "core/release-manifest.json"
POLICY_PATH = "core/release-policy.json"
LEGACY_BACKUP_NAME = re.compile(r"v(?P<version>\d+\.\d+\.\d+)-(?P<stamp>\d{8}T\d{6}Z)\.tar\.gz")
LEGACY_MANAGED = (
    "core",
    ".claude/skills",
    "CLAUDE.md",
    "README.md",
    "START_HERE.md",
    "CHANGELOG.md",
    "LICENSE",
    "docs",
    "figma-plugin",
    "evals",
    "examples",
    "INBOX",
    "knowledge/references",
    "knowledge/patterns",
    "pyproject.toml",
    "scd",
    "scripts/test.sh",
)
LEGACY_BOOTSTRAP_DEFAULTS = {
    "core/defaults/managed/knowledge/current-motion": "knowledge/current-motion",
    "core/defaults/managed/knowledge/anti-patterns": "knowledge/anti-patterns",
}
_IGNORED_BUILD_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".cache",
    ".DS_Store",
    "node_modules",
    "build",
}
_IGNORED_BUILD_SUFFIXES = {".pyc", ".pyo"}


def root_dir() -> Path:
    return Path(__file__).resolve().parents[3]


def _normal_relative(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ValueError(f"Invalid relative path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise ValueError(f"Invalid relative path: {value!r}")
    normalized = path.as_posix()
    if normalized != value.rstrip("/"):
        raise ValueError(f"Path is not normalized: {value!r}")
    return normalized


def _overlaps(left: str, right: str) -> bool:
    return left == right or left.startswith(right + "/") or right.startswith(left + "/")


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def load_release_policy(root: Path) -> dict:
    policy = read_json(root / POLICY_PATH)
    if policy.get("schema_version") != 1:
        raise ValueError("Unsupported release policy schema")
    managed = policy.get("managed_paths")
    protected = policy.get("protected_paths")
    defaults = policy.get("factory_defaults")
    limits = policy.get("archive_limits")
    if not isinstance(managed, list) or not managed or not isinstance(protected, list):
        raise ValueError("Release policy must define managed_paths and protected_paths")
    if not isinstance(defaults, dict) or not isinstance(limits, dict):
        raise ValueError("Release policy must define factory_defaults and archive_limits")
    managed = [_normal_relative(item) for item in managed]
    protected = [_normal_relative(item) for item in protected]
    if len(set(managed)) != len(managed) or len(set(protected)) != len(protected):
        raise ValueError("Release policy contains duplicate paths")
    for managed_path in managed:
        for protected_path in protected:
            if _overlaps(managed_path, protected_path):
                raise ValueError(f"Managed and protected paths overlap: {managed_path}, {protected_path}")
    normalized_defaults: dict[str, str] = {}
    for source, destination in defaults.items():
        source = _normal_relative(source)
        destination = _normal_relative(destination)
        if not any(source == item or source.startswith(item + "/") for item in managed):
            raise ValueError(f"Factory default is outside managed paths: {source}")
        if not any(destination == item or destination.startswith(item + "/") for item in protected):
            raise ValueError(f"Factory destination is outside protected paths: {destination}")
        normalized_defaults[source] = destination
    required_limits = (
        "maximum_archive_bytes",
        "maximum_files",
        "maximum_file_bytes",
        "maximum_expanded_bytes",
    )
    if any(not isinstance(limits.get(name), int) or limits[name] <= 0 for name in required_limits):
        raise ValueError("Release policy archive limits must be positive integers")
    result = dict(policy)
    result["managed_paths"] = managed
    result["protected_paths"] = protected
    result["factory_defaults"] = normalized_defaults
    return result


_DEFAULT_POLICY = load_release_policy(root_dir())
MANAGED = tuple(_DEFAULT_POLICY["managed_paths"])
PROTECTED = tuple(_DEFAULT_POLICY["protected_paths"])


def semver(value: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:[-+].*)?", value.strip())
    if not match:
        raise ValueError(f"Invalid semantic version: {value}")
    return tuple(int(part) for part in match.groups())


def version_at(root: Path) -> str:
    return (root / "core" / "VERSION").read_text(encoding="utf-8").strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _path_is_managed(relative: str, managed: list[str] | tuple[str, ...]) -> bool:
    return any(relative == item or relative.startswith(item + "/") for item in managed)


def _directory_is_managed_or_parent(relative: str, managed: list[str] | tuple[str, ...]) -> bool:
    return _path_is_managed(relative, managed) or any(item.startswith(relative + "/") for item in managed)


def _walk_regular_files(root: Path) -> tuple[set[str], set[str]]:
    files: set[str] = set()
    directories: set[str] = set()
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"Release root must be a real directory: {root}")
    for current, dirnames, filenames in os.walk(root, followlinks=False):
        current_path = Path(current)
        relative_current = current_path.relative_to(root)
        for name in list(dirnames):
            path = current_path / name
            if path.is_symlink():
                raise ValueError(f"Links are not allowed in a release: {path.relative_to(root)}")
            mode = path.stat(follow_symlinks=False).st_mode
            if not stat.S_ISDIR(mode):
                raise ValueError(f"Special path is not allowed in a release: {path.relative_to(root)}")
            directories.add(path.relative_to(root).as_posix())
        for name in filenames:
            path = current_path / name
            mode = path.stat(follow_symlinks=False).st_mode
            relative = path.relative_to(root).as_posix()
            if not stat.S_ISREG(mode):
                raise ValueError(f"Only regular files are allowed in a release: {relative}")
            files.add(relative)
        if relative_current != Path("."):
            directories.add(relative_current.as_posix())
    return files, directories


def _release_asset_name(version: str) -> str:
    semver(version)
    return f"scd-core-v{version}.tar.gz"


def create_release_manifest(stage: Path) -> dict:
    policy = load_release_policy(stage)
    files, directories = _walk_regular_files(stage)
    files.discard(MANIFEST_PATH)
    for relative in files:
        if not _path_is_managed(relative, policy["managed_paths"]):
            raise ValueError(f"Release contains a path outside its inventory: {relative}")
    for relative in directories:
        if relative != "." and not _directory_is_managed_or_parent(relative, policy["managed_paths"]):
            raise ValueError(f"Release contains a directory outside its inventory: {relative}")
    version = version_at(stage)
    manifest = {
        "schema_version": 1,
        "version": version,
        "release_asset": _release_asset_name(version),
        "managed_paths": policy["managed_paths"],
        "files": {relative: sha256(stage / relative) for relative in sorted(files)},
    }
    if not manifest["files"]:
        raise ValueError("Release inventory is empty")
    write_json(stage / MANIFEST_PATH, manifest)
    return manifest


def verify_release(source: Path, expected_asset_name: str | None = None) -> None:
    policy = load_release_policy(source)
    for key in ("managed_paths", "protected_paths", "factory_defaults"):
        if policy[key] != _DEFAULT_POLICY[key]:
            raise ValueError(f"Release changes {key}; install a compatible bootstrap updater first")
    compatibility = read_json(source / "core" / "COMPATIBILITY.json")
    candidate = version_at(source)
    if compatibility.get("release") != candidate:
        raise ValueError("VERSION and COMPATIBILITY.json disagree")
    minimum_python = compatibility.get("minimum_python")
    minimum_installer = compatibility.get("minimum_installer")
    if not isinstance(minimum_python, str) or not isinstance(minimum_installer, str):
        raise ValueError("Compatibility metadata is incomplete")
    if sys.version_info < tuple(int(x) for x in minimum_python.split(".")):
        raise ValueError(f"Python {minimum_python}+ is required")
    if semver(INSTALLER_VERSION) < semver(minimum_installer):
        raise ValueError("This release needs a newer bootstrap installer")

    manifest_path = source / MANIFEST_PATH
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise ValueError("Release manifest is required")
    if manifest_path.stat().st_size > 5 * 1024 * 1024:
        raise ValueError("Release manifest is too large")
    manifest = read_json(manifest_path)
    expected_release_asset = _release_asset_name(candidate)
    if manifest.get("schema_version") != 1:
        raise ValueError("Unsupported release manifest schema")
    if manifest.get("version") != candidate:
        raise ValueError("Release manifest version disagrees with VERSION")
    if manifest.get("release_asset") != expected_release_asset:
        raise ValueError("Release manifest has an unexpected asset identity")
    if expected_asset_name is not None and expected_asset_name != expected_release_asset:
        raise ValueError("Downloaded asset name does not match the verified release")
    if manifest.get("managed_paths") != policy["managed_paths"]:
        raise ValueError("Release manifest and release policy inventories disagree")
    expected_files = manifest.get("files")
    if not isinstance(expected_files, dict) or not expected_files:
        raise ValueError("Release manifest must contain a non-empty file inventory")

    normalized_files: dict[str, str] = {}
    for relative, expected_digest in expected_files.items():
        relative = _normal_relative(relative)
        if relative == MANIFEST_PATH or not _path_is_managed(relative, policy["managed_paths"]):
            raise ValueError(f"Manifest path is outside the managed inventory: {relative}")
        if not isinstance(expected_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_digest):
            raise ValueError(f"Invalid digest in release manifest: {relative}")
        if relative in normalized_files:
            raise ValueError(f"Duplicate path in release manifest: {relative}")
        normalized_files[relative] = expected_digest

    actual_files, actual_directories = _walk_regular_files(source)
    actual_files.discard(MANIFEST_PATH)
    if actual_files != set(normalized_files):
        missing = sorted(set(normalized_files) - actual_files)
        extra = sorted(actual_files - set(normalized_files))
        raise ValueError(f"Release inventory mismatch; missing={missing[:3]}, extra={extra[:3]}")
    for relative in actual_files:
        if not _path_is_managed(relative, policy["managed_paths"]):
            raise ValueError(f"Release contains an unmanaged path: {relative}")
    for relative in actual_directories:
        if relative != "." and not _directory_is_managed_or_parent(relative, policy["managed_paths"]):
            raise ValueError(f"Release contains an unmanaged directory: {relative}")
    for relative in policy["managed_paths"]:
        if not (source / relative).exists():
            raise ValueError(f"Required managed path is missing: {relative}")
    for relative, expected_digest in normalized_files.items():
        if sha256(source / relative) != expected_digest:
            raise ValueError(f"Release integrity check failed: {relative}")


def _excluded_from_build(relative: str) -> bool:
    path = PurePosixPath(relative)
    return (
        relative == MANIFEST_PATH
        or any(part in _IGNORED_BUILD_NAMES for part in path.parts)
        or any(part.endswith(".egg-info") for part in path.parts)
        or path.suffix in _IGNORED_BUILD_SUFFIXES
    )


def _copy_product_path(source_root: Path, destination_root: Path, relative: str) -> None:
    source = source_root / relative
    destination = destination_root / relative
    if source.is_symlink():
        raise ValueError(f"Release sources may not be links: {relative}")
    if source.is_file():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        return
    if not source.is_dir():
        raise ValueError(f"Required release source is missing: {relative}")
    for current, dirnames, filenames in os.walk(source, followlinks=False):
        current_path = Path(current)
        current_relative = current_path.relative_to(source_root).as_posix()
        if _excluded_from_build(current_relative):
            dirnames[:] = []
            continue
        if current_path.is_symlink():
            raise ValueError(f"Release sources may not contain links: {current_relative}")
        (destination_root / current_relative).mkdir(parents=True, exist_ok=True)
        kept_directories: list[str] = []
        for name in dirnames:
            child = current_path / name
            child_relative = child.relative_to(source_root).as_posix()
            if _excluded_from_build(child_relative):
                continue
            if child.is_symlink():
                raise ValueError(f"Release sources may not contain links: {child_relative}")
            kept_directories.append(name)
        dirnames[:] = kept_directories
        for name in filenames:
            child = current_path / name
            child_relative = child.relative_to(source_root).as_posix()
            if _excluded_from_build(child_relative):
                continue
            if child.is_symlink():
                raise ValueError(f"Release sources may not contain links: {child_relative}")
            mode = child.stat(follow_symlinks=False).st_mode
            if not stat.S_ISREG(mode):
                raise ValueError(f"Release sources must be regular files: {child_relative}")
            target = destination_root / child_relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(child, target)


def stage_release(source_root: Path, stage: Path) -> None:
    policy = load_release_policy(source_root)
    for relative in policy["managed_paths"]:
        _copy_product_path(source_root, stage, relative)
    create_release_manifest(stage)
    verify_release(stage)


def _archive_stage(stage: Path, archive: Path) -> None:
    archive.parent.mkdir(parents=True, exist_ok=True)
    if archive.exists():
        raise FileExistsError(f"Refusing to overwrite release archive: {archive}")
    with tarfile.open(archive, "x:gz") as handle:
        handle.add(stage, arcname=stage.name, recursive=True)


def build_release_archive(source_root: Path, output_dir: Path) -> tuple[Path, Path]:
    version = version_at(source_root)
    archive_name = _release_asset_name(version)
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="scd-release-") as temp_name:
        stage = Path(temp_name) / f"saas-creative-director-{version}"
        stage.mkdir()
        stage_release(source_root, stage)
        archive = output_dir / archive_name
        _archive_stage(stage, archive)
    checksum = output_dir / f"{archive_name}.sha256"
    if checksum.exists():
        raise FileExistsError(f"Refusing to overwrite checksum: {checksum}")
    checksum.write_text(f"{sha256(archive)}  {archive.name}\n", encoding="utf-8")
    return archive, checksum


def _assert_no_symlink_components(root: Path, relative: str) -> Path:
    if root.is_symlink():
        raise ValueError(f"Installation root may not be a symlink: {root}")
    current = root
    for part in PurePosixPath(relative).parts:
        if part == ".":
            continue
        current = current / part
        if current.is_symlink():
            raise ValueError(f"Refusing to write through a symlink: {current}")
    return current


def _remove_internal_path(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_symlink() or path.is_file():
        path.unlink()
    else:
        shutil.rmtree(path)


def copy_managed(source: Path, root: Path, transaction_id: str | None = None) -> None:
    policy = load_release_policy(source)
    token = transaction_id or uuid.uuid4().hex
    for relative in policy["managed_paths"]:
        incoming = source / relative
        if not incoming.exists() or incoming.is_symlink():
            raise ValueError(f"Managed release path is missing or unsafe: {relative}")
        target = _assert_no_symlink_components(root, relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        _assert_no_symlink_components(root, PurePosixPath(relative).parent.as_posix())
        temporary = target.with_name(f".{target.name}.incoming-{token}")
        previous = target.with_name(f".{target.name}.previous-{token}")
        if temporary.exists() or previous.exists():
            raise ValueError(f"Transaction workspace already exists for {relative}")
        if incoming.is_dir():
            _walk_regular_files(incoming)
            shutil.copytree(incoming, temporary, symlinks=False)
        elif incoming.is_file():
            shutil.copy2(incoming, temporary)
        else:
            raise ValueError(f"Managed release path has an unsupported type: {relative}")
        moved_previous = False
        try:
            if target.exists():
                if target.is_symlink():
                    raise ValueError(f"Refusing to replace a symlink: {relative}")
                os.replace(target, previous)
                moved_previous = True
            os.replace(temporary, target)
        except BaseException:
            if moved_previous and not target.exists() and previous.exists():
                os.replace(previous, target)
            raise
        finally:
            _remove_internal_path(temporary)
        _remove_internal_path(previous)
    executable = root / "scd"
    if executable.exists():
        executable.chmod(executable.stat().st_mode | 0o111)


def _apply_factory_defaults(root: Path) -> None:
    policy = load_release_policy(root)
    for source_relative, destination_relative in policy["factory_defaults"].items():
        source = root / source_relative
        destination = _assert_no_symlink_components(root, destination_relative)
        if destination.exists():
            continue
        if not source.is_file() or source.is_symlink():
            raise ValueError(f"Factory default is missing or unsafe: {source_relative}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
        shutil.copy2(source, temporary)
        try:
            os.replace(temporary, destination)
        finally:
            _remove_internal_path(temporary)


def _bootstrap_tree_state(source: Path, destination: Path, destination_relative: str) -> tuple[bool, str]:
    """Return whether a bootstrap destination is an exact, conflict-free copy."""

    source_files, source_directories = _walk_regular_files(source)
    if not destination.exists():
        return False, "missing"
    if destination.is_symlink() or not destination.is_dir():
        raise ValueError(f"Bootstrap destination must be a real directory: {destination_relative}")
    destination_files, destination_directories = _walk_regular_files(destination)
    unexpected = sorted(
        (destination_files - source_files) | (destination_directories - source_directories)
    )
    conflicting = sorted(
        relative
        for relative in source_files & destination_files
        if sha256(source / relative) != sha256(destination / relative)
    )
    if unexpected or conflicting:
        details: list[str] = []
        if conflicting:
            details.append(f"changed files: {', '.join(conflicting)}")
        if unexpected:
            details.append(f"unexpected paths: {', '.join(unexpected)}")
        raise ValueError(f"Bootstrap destination conflicts with managed payload ({destination_relative}): {'; '.join(details)}")
    missing = sorted(
        (source_files - destination_files) | (source_directories - destination_directories)
    )
    if missing:
        return False, f"incomplete; missing: {', '.join(missing)}"
    return True, "complete"


def bootstrap_managed_defaults(root: Path) -> bool:
    """Install managed payloads omitted by the published 0.6 hard-coded inventory.

    The 0.6 updater still replaces ``core`` and ``scd``.  The candidate therefore
    carries the two new knowledge trees inside ``core`` and materializes them on
    the next launcher invocation. Compatible partial copies are replaced
    atomically; changed or unexpected content is rejected as a conflict.
    """

    changed = False
    policy = load_release_policy(root)
    for source_relative, destination_relative in LEGACY_BOOTSTRAP_DEFAULTS.items():
        if destination_relative not in policy["managed_paths"]:
            raise ValueError(f"Bootstrap destination is not managed: {destination_relative}")
        source = root / source_relative
        destination = _assert_no_symlink_components(root, destination_relative)
        if not source.is_dir() or source.is_symlink():
            raise ValueError(f"Bootstrap payload is missing or unsafe: {source_relative}")
        complete, _ = _bootstrap_tree_state(source, destination, destination_relative)
        if complete:
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.bootstrap")
        previous = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.previous")
        shutil.copytree(source, temporary, symlinks=False)
        moved_previous = False
        try:
            if destination.exists():
                os.replace(destination, previous)
                moved_previous = True
            os.replace(temporary, destination)
        except BaseException:
            if moved_previous and not destination.exists() and previous.exists():
                os.replace(previous, destination)
            raise
        finally:
            _remove_internal_path(temporary)
        _remove_internal_path(previous)
        changed = True
    return changed


def write_state(root: Path, previous: str | None, transaction_id: str | None = None) -> None:
    state = {
        "installed_version": version_at(root),
        "previous_version": previous,
        "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    if transaction_id:
        state["transaction_id"] = transaction_id
    write_json(root / ".scd" / "state.json", state)


def _backup_metadata_path(archive: Path) -> Path:
    return archive.with_suffix(archive.suffix + ".json")


def backup(root: Path, transaction_id: str | None = None, purpose: str = "manual") -> Path:
    transaction_id = transaction_id or uuid.uuid4().hex
    version = version_at(root)
    created_at = datetime.now(timezone.utc)
    stamp = created_at.strftime("%Y%m%dT%H%M%S.%fZ")
    destination = root / ".scd" / "backups" / f"{stamp}-{transaction_id}-v{version}.tar.gz"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="scd-backup-") as temp_name:
        stage = Path(temp_name) / f"saas-creative-director-{version}"
        stage.mkdir()
        stage_release(root, stage)
        _archive_stage(stage, destination)
    write_json(
        _backup_metadata_path(destination),
        {
            "schema_version": 1,
            "transaction_id": transaction_id,
            "created_at": created_at.isoformat(),
            "version": version,
            "purpose": purpose,
            "archive": destination.name,
            "sha256": sha256(destination),
        },
    )
    return destination


def locate_release(unpacked: Path) -> Path:
    if (unpacked / "core" / "VERSION").is_file():
        return unpacked
    children = list(unpacked.iterdir())
    if len(children) != 1 or not children[0].is_dir() or children[0].is_symlink():
        raise ValueError("Archive must contain exactly one repository root")
    candidate = children[0]
    if not (candidate / "core" / "VERSION").is_file():
        raise ValueError("Archive repository root must contain core/VERSION")
    return candidate


def safe_extract(archive_path: Path, destination: Path, limits: dict | None = None) -> None:
    limits = limits or _DEFAULT_POLICY["archive_limits"]
    if archive_path.stat().st_size > limits["maximum_archive_bytes"]:
        raise ValueError("Release archive exceeds the compressed size limit")
    if destination.is_symlink() or any(destination.iterdir()):
        raise ValueError("Release staging directory must be fresh and empty")
    with tarfile.open(archive_path, "r:gz") as archive:
        members = archive.getmembers()
        if len(members) > limits["maximum_files"]:
            raise ValueError("Release archive contains too many entries")
        seen: set[str] = set()
        seen_casefolded: set[str] = set()
        types: dict[str, str] = {}
        expanded = 0
        prepared: list[tuple[tarfile.TarInfo, str]] = []
        for member in members:
            relative = _normal_relative(member.name)
            folded = relative.casefold()
            if relative in seen or folded in seen_casefolded:
                raise ValueError(f"Duplicate path in release archive: {relative}")
            seen.add(relative)
            seen_casefolded.add(folded)
            if member.isdir():
                kind = "directory"
            elif member.isfile():
                kind = "file"
                if member.size < 0 or member.size > limits["maximum_file_bytes"]:
                    raise ValueError(f"Release member exceeds the file size limit: {relative}")
                expanded += member.size
                if expanded > limits["maximum_expanded_bytes"]:
                    raise ValueError("Release archive exceeds the expanded size limit")
            else:
                raise ValueError(f"Links and special files are not allowed: {relative}")
            for parent in PurePosixPath(relative).parents:
                parent_name = parent.as_posix()
                if parent_name != "." and types.get(parent_name) == "file":
                    raise ValueError(f"Archive path descends through a file: {relative}")
            types[relative] = kind
            prepared.append((member, relative))

        for relative, kind in types.items():
            if kind == "file" and any(other.startswith(relative + "/") for other in types):
                raise ValueError(f"Archive path descends through a file: {relative}")

        for member, relative in sorted(prepared, key=lambda item: (0 if item[0].isdir() else 1, len(PurePosixPath(item[1]).parts))):
            target = _assert_no_symlink_components(destination, relative)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=False)
                target.chmod(0o755)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            _assert_no_symlink_components(destination, PurePosixPath(relative).parent.as_posix())
            extracted = archive.extractfile(member)
            if extracted is None:
                raise ValueError(f"Could not read release member: {relative}")
            remaining = member.size
            with target.open("xb") as output:
                while remaining:
                    block = extracted.read(min(1024 * 1024, remaining))
                    if not block:
                        raise ValueError(f"Truncated release member: {relative}")
                    output.write(block)
                    remaining -= len(block)
                if extracted.read(1):
                    raise ValueError(f"Release member is larger than declared: {relative}")
            target.chmod(0o755 if member.mode & 0o111 else 0o644)


def _safe_extract_legacy_backup(archive_path: Path, destination: Path, limits: dict) -> None:
    """Extract rollback data while skipping old private and build-only entries."""

    if archive_path.stat().st_size > limits["maximum_archive_bytes"]:
        raise ValueError("Legacy backup exceeds the compressed size limit")
    if destination.is_symlink() or any(destination.iterdir()):
        raise ValueError("Rollback staging directory must be fresh and empty")
    with tarfile.open(archive_path, "r:gz") as archive:
        members = archive.getmembers()
        if len(members) > limits["maximum_files"]:
            raise ValueError("Legacy backup contains too many entries")
        seen: set[str] = set()
        seen_casefolded: set[str] = set()
        prepared: list[tuple[tarfile.TarInfo, str]] = []
        expanded = 0
        for member in members:
            relative = _normal_relative(member.name)
            folded = relative.casefold()
            if relative in seen or folded in seen_casefolded:
                raise ValueError(f"Duplicate path in legacy backup: {relative}")
            seen.add(relative)
            seen_casefolded.add(folded)
            parts = PurePosixPath(relative).parts
            skipped = (
                (parts and parts[0] == "INBOX")
                or any(part in _IGNORED_BUILD_NAMES for part in parts)
                or any(part.endswith(".egg-info") for part in parts)
                or PurePosixPath(relative).suffix in _IGNORED_BUILD_SUFFIXES
            )
            if member.isfile():
                if member.size < 0 or member.size > limits["maximum_file_bytes"]:
                    raise ValueError(f"Legacy backup member exceeds the file size limit: {relative}")
                expanded += member.size
                if expanded > limits["maximum_expanded_bytes"]:
                    raise ValueError("Legacy backup exceeds the expanded size limit")
            if skipped:
                continue
            if not member.isdir() and not member.isfile():
                raise ValueError(f"Links and special files are not allowed in legacy rollback data: {relative}")
            prepared.append((member, relative))

        for member, relative in sorted(
            prepared,
            key=lambda item: (0 if item[0].isdir() else 1, len(PurePosixPath(item[1]).parts)),
        ):
            target = _assert_no_symlink_components(destination, relative)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                target.chmod(0o755)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            _assert_no_symlink_components(destination, PurePosixPath(relative).parent.as_posix())
            extracted = archive.extractfile(member)
            if extracted is None:
                raise ValueError(f"Could not read legacy backup member: {relative}")
            remaining = member.size
            with target.open("xb") as output:
                while remaining:
                    block = extracted.read(min(1024 * 1024, remaining))
                    if not block:
                        raise ValueError(f"Truncated legacy backup member: {relative}")
                    output.write(block)
                    remaining -= len(block)
            target.chmod(0o755 if member.mode & 0o111 else 0o644)


def github_repo(root: Path) -> str:
    local = root / "config" / "local.json"
    repository = read_json(local).get("github_repository") if local.exists() else ""
    if not repository:
        result = subprocess.run(["git", "remote", "get-url", "origin"], cwd=root, text=True, capture_output=True)
        if result.returncode:
            raise ValueError("Set github_repository in config/local.json or pass --from PATH")
        url = result.stdout.strip().removesuffix(".git")
        match = re.search(r"github\.com[/:]([^/]+/[^/]+)$", url)
        if not match:
            raise ValueError("Origin is not a GitHub repository")
        repository = match.group(1)
    if not isinstance(repository, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("github_repository must have owner/repository format")
    return repository


def _download_bounded(url: str, output: Path, maximum_bytes: int) -> None:
    if urllib.parse.urlparse(url).scheme != "https":
        raise ValueError("Release downloads must use HTTPS")
    request = urllib.request.Request(url, headers={"User-Agent": "saas-creative-director-updater"})
    with urllib.request.urlopen(request, timeout=30) as response, output.open("xb") as handle:
        if urllib.parse.urlparse(response.geturl()).scheme != "https":
            raise ValueError("Release download redirected away from HTTPS")
        declared = response.headers.get("Content-Length")
        if declared and int(declared) > maximum_bytes:
            raise ValueError("Release download exceeds the size limit")
        received = 0
        while True:
            block = response.read(min(1024 * 1024, maximum_bytes - received + 1))
            if not block:
                break
            received += len(block)
            if received > maximum_bytes:
                raise ValueError("Release download exceeds the size limit")
            handle.write(block)


def download_latest(root: Path, destination: Path) -> Path:
    repository = github_repo(root)
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repository}/releases/latest",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "saas-creative-director-updater"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        release = json.load(response)
    tag = release.get("tag_name")
    if not isinstance(tag, str):
        raise ValueError("Latest GitHub Release has no semantic version tag")
    version = tag[1:] if tag.startswith("v") else tag
    semver(version)
    archive_name = _release_asset_name(version)
    checksum_name = f"{archive_name}.sha256"
    assets = {asset.get("name"): asset for asset in release.get("assets", []) if isinstance(asset, dict)}
    if archive_name not in assets or checksum_name not in assets:
        raise ValueError(f"Latest GitHub Release must contain {archive_name} and its checksum")
    limits = load_release_policy(root)["archive_limits"]
    archive = destination / archive_name
    checksum = destination / checksum_name
    _download_bounded(assets[archive_name]["browser_download_url"], archive, limits["maximum_archive_bytes"])
    _download_bounded(assets[checksum_name]["browser_download_url"], checksum, 4096)
    checksum_text = checksum.read_text(encoding="ascii").strip()
    match = re.fullmatch(r"([0-9a-f]{64})  ([^/\\]+)", checksum_text)
    if not match or match.group(2) != archive_name or match.group(1) != sha256(archive):
        raise ValueError("Release checksum verification failed")
    return archive


def _journal_path(root: Path, transaction_id: str) -> Path:
    return root / ".scd" / "transactions" / f"{transaction_id}.json"


def _write_journal(root: Path, journal: dict, phase: str, status: str = "in_progress", **changes: object) -> None:
    journal.update(changes)
    journal["phase"] = phase
    journal["status"] = status
    journal["updated_at"] = datetime.now(timezone.utc).isoformat()
    write_json(_journal_path(root, journal["transaction_id"]), journal)


def _pid_running(pid: object) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


@contextmanager
def operation_lock(root: Path, transaction_id: str) -> Iterator[None]:
    scd_dir = root / ".scd"
    scd_dir.mkdir(parents=True, exist_ok=True)
    lock = scd_dir / "update.lock"
    for _ in range(2):
        try:
            descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            break
        except FileExistsError:
            try:
                existing = read_json(lock)
            except (OSError, ValueError, json.JSONDecodeError):
                existing = {}
            if _pid_running(existing.get("pid")):
                raise ValueError(f"Another maintenance operation is running: {existing.get('transaction_id', 'unknown')}")
            lock.unlink(missing_ok=True)
    else:
        raise ValueError("Could not acquire the maintenance lock")
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump({"transaction_id": transaction_id, "pid": os.getpid()}, handle)
        handle.write("\n")
    try:
        yield
    finally:
        try:
            existing = read_json(lock)
        except (OSError, ValueError, json.JSONDecodeError):
            existing = {}
        if existing.get("transaction_id") == transaction_id:
            lock.unlink(missing_ok=True)


def _legacy_restore_paths(root: Path, archive: Path, source: Path) -> list[str]:
    backup_directory = (root / ".scd" / "backups").resolve()
    resolved_archive = archive.resolve()
    if archive.is_symlink() or not archive.is_file() or resolved_archive.parent != backup_directory:
        raise ValueError("Legacy rollback backups are accepted only from this installation's .scd/backups directory")
    identity = LEGACY_BACKUP_NAME.fullmatch(archive.name)
    if not identity:
        raise ValueError("Legacy rollback backup name does not match the published 0.6 format")
    archive_version = identity.group("version")
    if semver(archive_version) > semver("0.6.0"):
        raise ValueError("Manifest-free backups are supported only through version 0.6.0")
    if version_at(source) != archive_version:
        raise ValueError("Legacy backup filename and core/VERSION disagree")
    compatibility_path = source / "core" / "COMPATIBILITY.json"
    if not compatibility_path.is_file() or compatibility_path.is_symlink():
        raise ValueError("Legacy backup compatibility metadata is missing")
    if read_json(compatibility_path).get("release") != archive_version:
        raise ValueError("Legacy backup compatibility metadata and version disagree")

    files, directories = _walk_regular_files(source)
    for relative in files | directories:
        if relative == ".":
            continue
        if not _directory_is_managed_or_parent(relative, LEGACY_MANAGED):
            raise ValueError(f"Legacy backup contains an unexpected path: {relative}")

    current_policy = load_release_policy(root)
    selected: list[str] = []
    for relative in LEGACY_MANAGED:
        if not (source / relative).exists():
            continue
        if any(_overlaps(relative, protected) for protected in current_policy["protected_paths"]):
            continue
        if not any(relative == managed or relative.startswith(managed + "/") for managed in current_policy["managed_paths"]):
            raise ValueError(f"Legacy backup path is outside the current managed inventory: {relative}")
        selected.append(relative)
    if "core" not in selected or "scd" not in selected:
        raise ValueError("Legacy backup is incomplete")
    return selected


def _copy_legacy_snapshot(source: Path, root: Path, selected: list[str], transaction_id: str) -> None:
    current_policy = load_release_policy(root)
    selected_set = set(selected)
    for relative in selected:
        incoming = source / relative
        if incoming.is_symlink() or not incoming.exists():
            raise ValueError(f"Legacy backup path is missing or unsafe: {relative}")
        target = _assert_no_symlink_components(root, relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.incoming-{transaction_id}")
        previous = target.with_name(f".{target.name}.previous-{transaction_id}")
        if temporary.exists() or previous.exists():
            raise ValueError(f"Transaction workspace already exists for {relative}")
        if incoming.is_dir():
            _walk_regular_files(incoming)
            shutil.copytree(incoming, temporary, symlinks=False)
        elif incoming.is_file():
            shutil.copy2(incoming, temporary)
        else:
            raise ValueError(f"Legacy backup path has an unsupported type: {relative}")
        moved_previous = False
        try:
            if target.exists():
                if target.is_symlink():
                    raise ValueError(f"Refusing to replace a symlink: {relative}")
                os.replace(target, previous)
                moved_previous = True
            os.replace(temporary, target)
        except BaseException:
            if moved_previous and not target.exists() and previous.exists():
                os.replace(previous, target)
            raise
        finally:
            _remove_internal_path(temporary)
        _remove_internal_path(previous)

    # Candidate-only managed paths did not exist in the legacy snapshot. Remove
    # those paths so rollback is an actual product rollback, while every current
    # protected path (including INBOX) remains outside this operation.
    for relative in current_policy["managed_paths"]:
        if any(_overlaps(relative, item) for item in selected_set):
            continue
        target = _assert_no_symlink_components(root, relative)
        _remove_internal_path(target)
    executable = root / "scd"
    if executable.exists():
        executable.chmod(executable.stat().st_mode | 0o111)


def _verified_restore_source(root: Path, archive: Path, unpacked: Path) -> tuple[Path, list[str] | None]:
    metadata_path = _backup_metadata_path(archive)
    if metadata_path.is_file():
        metadata = read_json(metadata_path)
        if metadata.get("sha256") != sha256(archive):
            raise ValueError("Backup checksum verification failed")
    limits = load_release_policy(root)["archive_limits"]
    local_legacy = (
        not metadata_path.exists()
        and not archive.is_symlink()
        and archive.resolve().parent == (root / ".scd" / "backups").resolve()
        and LEGACY_BACKUP_NAME.fullmatch(archive.name) is not None
    )
    if local_legacy:
        _safe_extract_legacy_backup(archive, unpacked, limits)
    else:
        safe_extract(archive, unpacked, limits)
    source = locate_release(unpacked)
    if local_legacy:
        return source, _legacy_restore_paths(root, archive, source)
    try:
        verify_release(source)
        return source, None
    except (OSError, ValueError, json.JSONDecodeError) as release_error:
        try:
            return source, _legacy_restore_paths(root, archive, source)
        except (OSError, ValueError, json.JSONDecodeError) as legacy_error:
            raise ValueError(
                f"Rollback archive is neither a verified release nor an accepted local 0.6 backup: {legacy_error}"
            ) from release_error


def _restore_archive(root: Path, archive: Path, transaction_id: str) -> bool:
    with tempfile.TemporaryDirectory(prefix="scd-restore-") as temp_name:
        source, legacy_paths = _verified_restore_source(root, archive, Path(temp_name))
        if legacy_paths is None:
            copy_managed(source, root, transaction_id=transaction_id)
            return False
        _copy_legacy_snapshot(source, root, legacy_paths, transaction_id)
        return True


def recover_incomplete_transactions(root: Path) -> None:
    directory = root / ".scd" / "transactions"
    if not directory.exists():
        return
    for path in sorted(directory.glob("*.json")):
        journal = read_json(path)
        if journal.get("status") != "in_progress":
            continue
        phase = journal.get("phase")
        transaction_id = journal.get("transaction_id")
        if not isinstance(transaction_id, str):
            raise ValueError(f"Invalid transaction journal: {path}")
        if phase in {"activating", "activated", "verified"}:
            archive_value = journal.get("backup")
            if not isinstance(archive_value, str):
                raise ValueError(f"Transaction has no recovery backup: {transaction_id}")
            archive = Path(archive_value)
            if not archive.is_absolute():
                archive = root / archive
            if not archive.is_file():
                raise ValueError(f"Transaction recovery backup is missing: {transaction_id}")
            _restore_archive(root, archive, f"recovery-{transaction_id}")
            _write_journal(root, journal, "recovered", status="rolled_back")
            print(f"Recovered interrupted maintenance transaction: {transaction_id}")
        else:
            _write_journal(root, journal, "abandoned", status="rolled_back")


def _new_journal(root: Path, transaction_id: str, operation: str) -> dict:
    journal = {
        "schema_version": 1,
        "transaction_id": transaction_id,
        "operation": operation,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_journal(root, journal, "prepared")
    return journal


def initialize(root: Path) -> int:
    transaction_id = uuid.uuid4().hex
    with operation_lock(root, transaction_id):
        recover_incomplete_transactions(root)
        policy = load_release_policy(root)
        for relative in policy["protected_paths"]:
            path = _assert_no_symlink_components(root, relative)
            path.mkdir(parents=True, exist_ok=True)
        (root / ".scd" / "backups").mkdir(parents=True, exist_ok=True)
        (root / ".scd" / "transactions").mkdir(parents=True, exist_ok=True)
        bootstrap_managed_defaults(root)
        _apply_factory_defaults(root)
        write_state(root, previous=None, transaction_id=transaction_id)
        print(f"Installed SaaS Creative Director {version_at(root)}")
        return health_check(root)


def _prepare_source(root: Path, source_arg: str | None, temp: Path) -> tuple[Path, str | None]:
    expected_asset: str | None = None
    if source_arg:
        supplied = Path(source_arg).expanduser().resolve()
        if supplied.is_dir():
            return supplied, None
        archive = supplied
        expected_asset = archive.name if re.fullmatch(r"scd-core-v.+\.tar\.gz", archive.name) else None
    else:
        archive = download_latest(root, temp)
        expected_asset = archive.name
    unpacked = temp / "release"
    unpacked.mkdir()
    safe_extract(archive, unpacked, load_release_policy(root)["archive_limits"])
    return locate_release(unpacked), expected_asset


def update(root: Path, source_arg: str | None, allow_major: bool) -> int:
    transaction_id = uuid.uuid4().hex
    with operation_lock(root, transaction_id):
        recover_incomplete_transactions(root)
        bootstrap_managed_defaults(root)
        current = version_at(root)
        journal = _new_journal(root, transaction_id, "update")
        with tempfile.TemporaryDirectory(prefix="scd-update-") as temp_name:
            temp = Path(temp_name)
            source, expected_asset = _prepare_source(root, source_arg, temp)
            verify_release(source, expected_asset_name=expected_asset)
            candidate = version_at(source)
            if semver(candidate)[0] != semver(current)[0] and not allow_major:
                raise ValueError("Major upgrade requires --allow-major and its migration guide")
            if semver(candidate) < semver(current):
                raise ValueError("Refusing downgrade; use rollback for a previous installed version")
            archive = backup(root, transaction_id=transaction_id, purpose="pre-update")
            _write_journal(root, journal, "backup_created", backup=str(archive), from_version=current, to_version=candidate)
            try:
                _write_journal(root, journal, "activating")
                copy_managed(source, root, transaction_id=transaction_id)
                _write_journal(root, journal, "activated")
                if health_check(root) != 0:
                    raise RuntimeError("Post-update health check failed")
                _write_journal(root, journal, "verified")
                write_state(root, previous=current, transaction_id=transaction_id)
            except BaseException:
                _restore_archive(root, archive, f"failed-{transaction_id}")
                _write_journal(root, journal, "rolled_back", status="rolled_back")
                raise
            _write_journal(root, journal, "completed", status="completed")
            print(f"Updated {current} → {candidate}; transaction: {transaction_id}; backup: {archive}")
            return 0


def _available_backups(root: Path) -> list[tuple[datetime, str, Path]]:
    result: list[tuple[datetime, str, Path]] = []
    for metadata_path in (root / ".scd" / "backups").glob("*.tar.gz.json"):
        metadata = read_json(metadata_path)
        archive = metadata_path.with_suffix("")
        created_at = metadata.get("created_at")
        transaction_id = metadata.get("transaction_id")
        if archive.is_file() and isinstance(created_at, str) and isinstance(transaction_id, str):
            result.append((datetime.fromisoformat(created_at), transaction_id, archive))
    known = {item[2].resolve() for item in result}
    for archive in (root / ".scd" / "backups").glob("v*.tar.gz"):
        identity = LEGACY_BACKUP_NAME.fullmatch(archive.name)
        if archive.is_symlink() or not archive.is_file() or archive.resolve() in known or identity is None:
            continue
        created_at = datetime.strptime(identity.group("stamp"), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        result.append((created_at, f"legacy-{sha256(archive)[:12]}", archive))
    return sorted(result, key=lambda item: item[0])


def rollback(root: Path, archive_arg: str | None, transaction_arg: str | None = None) -> int:
    transaction_id = uuid.uuid4().hex
    with operation_lock(root, transaction_id):
        recover_incomplete_transactions(root)
        bootstrap_managed_defaults(root)
        backups = _available_backups(root)
        if archive_arg and transaction_arg:
            raise ValueError("Choose either --backup or --transaction")
        if archive_arg:
            archive: Path | None = Path(archive_arg).expanduser().resolve()
        elif transaction_arg:
            matches = [item[2] for item in backups if item[1] == transaction_arg]
            archive = matches[-1] if matches else None
        else:
            archive = backups[-1][2] if backups else None
        if archive is None or not archive.is_file():
            raise ValueError("No matching rollback backup found")
        before = version_at(root)
        journal = _new_journal(root, transaction_id, "rollback")
        with tempfile.TemporaryDirectory(prefix="scd-rollback-") as temp_name:
            source, legacy_paths = _verified_restore_source(root, archive, Path(temp_name))
            rollback_version = version_at(source)
            current_backup = backup(root, transaction_id=transaction_id, purpose="pre-rollback")
            _write_journal(
                root,
                journal,
                "backup_created",
                backup=str(current_backup),
                restore_archive=str(archive),
                from_version=before,
                to_version=rollback_version,
            )
            try:
                _write_journal(root, journal, "activating")
                if legacy_paths is None:
                    copy_managed(source, root, transaction_id=transaction_id)
                else:
                    _copy_legacy_snapshot(source, root, legacy_paths, transaction_id)
                _write_journal(root, journal, "activated")
                if health_check(root, allow_legacy=legacy_paths is not None) != 0:
                    raise RuntimeError("Post-rollback health check failed")
                _write_journal(root, journal, "verified")
                write_state(root, previous=before, transaction_id=transaction_id)
            except BaseException:
                _restore_archive(root, current_backup, f"failed-{transaction_id}")
                _write_journal(root, journal, "rolled_back", status="rolled_back")
                raise
            _write_journal(root, journal, "completed", status="completed")
            print(f"Rolled back {before} → {rollback_version}; transaction: {transaction_id}")
            return 0


def health_check(root: Path, allow_legacy: bool = False) -> int:
    checks: list[tuple[str, bool, str]] = []
    try:
        version = version_at(root)
        semver(version)
        checks.append(("version", True, version))
    except Exception as exc:
        checks.append(("version", False, str(exc)))
    checks.append(("python", sys.version_info >= (3, 11), sys.version.split()[0]))
    try:
        policy = load_release_policy(root)
        checks.append(("release policy", True, "valid"))
    except Exception as exc:
        if allow_legacy:
            policy = {
                "managed_paths": [item for item in LEGACY_MANAGED if item != "INBOX"],
                "protected_paths": list(_DEFAULT_POLICY["protected_paths"]),
                "factory_defaults": {},
            }
            checks.append(("release policy", True, "legacy 0.6 compatibility mode"))
        else:
            policy = _DEFAULT_POLICY
            checks.append(("release policy", False, str(exc)))
    for relative in policy["protected_paths"]:
        path = root / relative
        passed = path.is_dir() and not path.is_symlink() and os.access(path, os.W_OK)
        checks.append((relative, passed, "present, writable, and not a link"))
    skill_count = len(list((root / "core" / "skills").glob("*/SKILL.md")))
    adapter_count = len(list((root / ".claude" / "skills").glob("*/SKILL.md")))
    checks.append(("skill adapters", skill_count > 0 and skill_count == adapter_count, f"{adapter_count}/{skill_count}"))
    boundary_ok = not any(
        _overlaps(managed, protected)
        for managed in policy["managed_paths"]
        for protected in policy["protected_paths"]
    )
    checks.append(("update boundary", boundary_ok, "protected paths excluded from update inventory"))
    defaults_ok = all((root / source).is_file() for source in policy["factory_defaults"])
    checks.append(("factory defaults", defaults_ok, "available from managed core"))
    if not allow_legacy:
        for source_relative, destination_relative in LEGACY_BOOTSTRAP_DEFAULTS.items():
            try:
                source = root / source_relative
                if not source.is_dir() or source.is_symlink():
                    raise ValueError(f"Bootstrap payload is missing or unsafe: {source_relative}")
                complete, detail = _bootstrap_tree_state(
                    source,
                    root / destination_relative,
                    destination_relative,
                )
                checks.append((f"managed bootstrap {destination_relative}", complete, detail))
            except (OSError, ValueError) as exc:
                checks.append((f"managed bootstrap {destination_relative}", False, str(exc)))
    for name, passed, detail in checks:
        print(f"{'PASS' if passed else 'FAIL'} {name}: {detail}")
    return 0 if all(item[1] for item in checks) else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scd", description="Install and safely update SaaS Creative Director")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("install")
    commands.add_parser("bootstrap-managed", help=argparse.SUPPRESS)
    update_parser = commands.add_parser("update")
    update_parser.add_argument("--from", dest="source")
    update_parser.add_argument("--allow-major", action="store_true")
    rollback_parser = commands.add_parser("rollback")
    rollback_parser.add_argument("--backup")
    rollback_parser.add_argument("--transaction")
    commands.add_parser("health-check")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = root_dir()
    try:
        if args.command == "install":
            return initialize(root)
        if args.command == "bootstrap-managed":
            bootstrap_managed_defaults(root)
            return 0
        if args.command == "update":
            return update(root, args.source, args.allow_major)
        if args.command == "rollback":
            return rollback(root, args.backup, args.transaction)
        return health_check(root)
    except (OSError, ValueError, RuntimeError, tarfile.TarError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
