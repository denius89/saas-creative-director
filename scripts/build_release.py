from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "core" / "src"))
    from saas_creative_director.maintenance import build_release_archive

    output_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else root / "dist"
    archive, _checksum = build_release_archive(root, output_dir)
    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
