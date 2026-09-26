from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


INSTALLER_VERSION = "0.6.0"
PROTECTED = ("config", "overrides", "knowledge/custom", "projects")
MANAGED = (
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


def root_dir() -> Path:
    return Path(__file__).resolve().parents[3]


def semver(value: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:[-+].*)?", value.strip())
    if not match:
        raise ValueError(f"Invalid semantic version: {value}")
    return tuple(int(part) for part in match.groups())


def version_at(root: Path) -> str:
    return (root / "core" / "VERSION").read_text(encoding="utf-8").strip()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def initialize(root: Path) -> int:
    for path in PROTECTED:
        (root / path).mkdir(parents=True, exist_ok=True)
    (root / ".scd" / "backups").mkdir(parents=True, exist_ok=True)
    local = root / "config" / "local.json"
    if not local.exists():
        shutil.copy2(root / "config" / "local.example.json", local)
    write_state(root, previous=None)
    print(f"Installed SaaS Creative Director {version_at(root)}")
    return health_check(root)


def write_state(root: Path, previous: str | None) -> None:
    write_json(root / ".scd" / "state.json", {
        "installed_version": version_at(root),
        "previous_version": previous,
        "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    })


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_release(source: Path) -> None:
    compatibility = read_json(source / "core" / "COMPATIBILITY.json")
    candidate = version_at(source)
    if compatibility.get("release") != candidate:
        raise ValueError("VERSION and COMPATIBILITY.json disagree")
    if sys.version_info < tuple(int(x) for x in compatibility["minimum_python"].split(".")):
        raise ValueError(f"Python {compatibility['minimum_python']}+ is required")
    if semver(INSTALLER_VERSION) < semver(compatibility["minimum_installer"]):
        raise ValueError("This release needs a newer bootstrap installer")
    manifest = source / "core" / "release-manifest.json"
    if manifest.exists():
        for relative, expected in read_json(manifest).get("files", {}).items():
            path = source / relative
            if not path.is_file() or sha256(path) != expected:
                raise ValueError(f"Release integrity check failed: {relative}")


def backup(root: Path) -> Path:
    version = version_at(root)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = root / ".scd" / "backups" / f"v{version}-{stamp}.tar.gz"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(destination, "w:gz") as archive:
        for relative in MANAGED:
            path = root / relative
            if path.exists():
                archive.add(path, arcname=relative, recursive=True)
    return destination


def copy_managed(source: Path, root: Path) -> None:
    for relative in MANAGED:
        incoming = source / relative
        if not incoming.exists():
            continue
        target = root / relative
        if incoming.is_dir():
            temporary = target.with_name(target.name + ".incoming")
            if temporary.exists():
                shutil.rmtree(temporary)
            shutil.copytree(incoming, temporary)
            if target.exists():
                shutil.rmtree(target)
            temporary.replace(target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_suffix(target.suffix + ".incoming")
            shutil.copy2(incoming, temporary)
            temporary.replace(target)
    executable = root / "scd"
    if executable.exists():
        executable.chmod(executable.stat().st_mode | 0o111)


def locate_release(unpacked: Path) -> Path:
    if (unpacked / "core" / "VERSION").is_file():
        return unpacked
    matches = list(unpacked.glob("*/core/VERSION"))
    if len(matches) != 1:
        raise ValueError("Archive must contain one repository root with core/VERSION")
    return matches[0].parents[1]


def safe_extract(archive_path: Path, destination: Path) -> None:
    with tarfile.open(archive_path, "r:gz") as archive:
        base = destination.resolve()
        for member in archive.getmembers():
            target = (destination / member.name).resolve()
            if base != target and base not in target.parents:
                raise ValueError("Unsafe path in release archive")
        archive.extractall(destination)


def github_repo(root: Path) -> str:
    local = root / "config" / "local.json"
    if local.exists() and read_json(local).get("github_repository"):
        return read_json(local)["github_repository"]
    result = subprocess.run(["git", "remote", "get-url", "origin"], cwd=root, text=True, capture_output=True)
    if result.returncode:
        raise ValueError("Set github_repository in config/local.json or pass --from PATH")
    url = result.stdout.strip().removesuffix(".git")
    match = re.search(r"github\.com[/:]([^/]+/[^/]+)$", url)
    if not match:
        raise ValueError("Origin is not a GitHub repository")
    return match.group(1)


def download_latest(root: Path, destination: Path) -> Path:
    repository = github_repo(root)
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repository}/releases/latest",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "saas-creative-director-updater"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        release = json.load(response)
    assets = [a for a in release.get("assets", []) if a["name"].endswith(".tar.gz")]
    if not assets:
        raise ValueError("Latest GitHub Release has no .tar.gz core asset")
    output = destination / assets[0]["name"]
    urllib.request.urlretrieve(assets[0]["browser_download_url"], output)
    return output


def update(root: Path, source_arg: str | None, allow_major: bool) -> int:
    current = version_at(root)
    with tempfile.TemporaryDirectory(prefix="scd-update-") as temp_name:
        temp = Path(temp_name)
        if source_arg:
            supplied = Path(source_arg).expanduser().resolve()
            if supplied.is_dir():
                source = supplied
            else:
                unpacked = temp / "release"
                unpacked.mkdir()
                safe_extract(supplied, unpacked)
                source = locate_release(unpacked)
        else:
            archive = download_latest(root, temp)
            unpacked = temp / "release"
            unpacked.mkdir()
            safe_extract(archive, unpacked)
            source = locate_release(unpacked)
        verify_release(source)
        candidate = version_at(source)
        if semver(candidate)[0] != semver(current)[0] and not allow_major:
            raise ValueError("Major upgrade requires --allow-major and its migration guide")
        if semver(candidate) < semver(current):
            raise ValueError("Refusing downgrade; use rollback for a previous installed version")
        archive = backup(root)
        copy_managed(source, root)
        write_state(root, previous=current)
        print(f"Updated {current} → {candidate}; backup: {archive}")
    return health_check(root)


def rollback(root: Path, archive_arg: str | None) -> int:
    backups = sorted((root / ".scd" / "backups").glob("*.tar.gz"))
    archive = Path(archive_arg).expanduser().resolve() if archive_arg else (backups[-1] if backups else None)
    if archive is None or not archive.is_file():
        raise ValueError("No rollback backup found")
    before = version_at(root)
    with tempfile.TemporaryDirectory(prefix="scd-rollback-") as temp_name:
        unpacked = Path(temp_name)
        safe_extract(archive, unpacked)
        source = locate_release(unpacked)
        verify_release(source)
        backup(root)
        copy_managed(source, root)
    write_state(root, previous=before)
    print(f"Rolled back {before} → {version_at(root)}")
    return health_check(root)


def health_check(root: Path) -> int:
    checks: list[tuple[str, bool, str]] = []
    try:
        version = version_at(root)
        semver(version)
        checks.append(("version", True, version))
    except Exception as exc:
        checks.append(("version", False, str(exc)))
    checks.append(("python", sys.version_info >= (3, 11), sys.version.split()[0]))
    for relative in PROTECTED:
        path = root / relative
        checks.append((relative, path.is_dir() and os.access(path, os.W_OK), "present and writable"))
    skill_count = len(list((root / "core" / "skills").glob("*/SKILL.md")))
    adapter_count = len(list((root / ".claude" / "skills").glob("*/SKILL.md")))
    checks.append(("skill adapters", skill_count > 0 and skill_count == adapter_count, f"{adapter_count}/{skill_count}"))
    protected_in_managed = set(PROTECTED).intersection(MANAGED)
    checks.append(("update boundary", not protected_in_managed, "protected paths excluded from update allowlist"))
    for name, passed, detail in checks:
        print(f"{'PASS' if passed else 'FAIL'} {name}: {detail}")
    return 0 if all(item[1] for item in checks) else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scd", description="Install and safely update SaaS Creative Director")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("install")
    update_parser = commands.add_parser("update")
    update_parser.add_argument("--from", dest="source")
    update_parser.add_argument("--allow-major", action="store_true")
    rollback_parser = commands.add_parser("rollback")
    rollback_parser.add_argument("--backup")
    commands.add_parser("health-check")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = root_dir()
    try:
        if args.command == "install":
            return initialize(root)
        if args.command == "update":
            return update(root, args.source, args.allow_major)
        if args.command == "rollback":
            return rollback(root, args.backup)
        return health_check(root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
