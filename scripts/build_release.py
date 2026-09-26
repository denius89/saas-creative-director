from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path


MANAGED = ("core", ".claude/skills", "CLAUDE.md", "README.md", "START_HERE.md", "CHANGELOG.md", "LICENSE", "docs", "figma-plugin", "evals", "examples", "knowledge/references", "knowledge/patterns", "pyproject.toml", "scd", "scripts/test.sh")


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    version = (root / "core" / "VERSION").read_text(encoding="utf-8").strip()
    output_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else root / "dist"
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="scd-release-") as temp_name:
        stage = Path(temp_name) / f"saas-creative-director-{version}"
        for relative in MANAGED:
            source = root / relative
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.is_dir():
                shutil.copytree(source, target)
            else:
                shutil.copy2(source, target)
        files = {}
        for path in sorted(stage.rglob("*")):
            if path.is_file() and path.relative_to(stage).as_posix() != "core/release-manifest.json":
                files[path.relative_to(stage).as_posix()] = digest(path)
        manifest = {"version": version, "files": files}
        (stage / "core" / "release-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        archive = output_dir / f"scd-core-v{version}.tar.gz"
        with tarfile.open(archive, "w:gz") as handle:
            handle.add(stage, arcname=stage.name)
    checksum = output_dir / f"scd-core-v{version}.tar.gz.sha256"
    checksum.write_text(f"{digest(archive)}  {archive.name}\n", encoding="utf-8")
    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
