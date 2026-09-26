# Maintainer release process

1. Update `core/VERSION`, `core/COMPATIBILITY.json`, `pyproject.toml`, and `CHANGELOG.md` with the same SemVer.
2. Add a migration guide for every minor or major release that changes persisted project behavior.
3. Run tests, skill validation, example validation, and the health check.
4. Tag `vX.Y.Z` and push the tag.
5. The GitHub workflow builds `scd-core-vX.Y.Z.tar.gz`, attaches its SHA-256 checksum, and publishes the changelog excerpt as a GitHub Release.

The release asset contains managed product files only. It intentionally excludes local config, overrides, custom knowledge, projects, `.git`, and `.scd` backups.

