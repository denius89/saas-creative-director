# Maintainer release process

1. Update `core/VERSION`, `core/COMPATIBILITY.json`, `pyproject.toml`, and `CHANGELOG.md` with the same SemVer.
2. Add a migration guide for every minor or major release that changes persisted project behavior.
3. Run tests, skill validation, example validation, and the health check.
4. Tag `vX.Y.Z` and push the tag.
5. The GitHub workflow builds `scd-core-vX.Y.Z.tar.gz`, attaches its SHA-256 checksum, and publishes the changelog excerpt as a GitHub Release.

The release asset is assembled only from the managed paths in `core/release-policy.json`. The build fails on links or missing managed roots and writes an exact file manifest plus a sibling archive checksum. Inspect the archive inventory before publishing it.

It intentionally excludes the complete `INBOX`, local config, overrides, custom knowledge, projects, `.git`, `.scd`, caches, and other paths outside the policy inventory. Factory `INBOX` and config templates live under `core/defaults/`; installation copies them only when the user-owned destination is absent.

The manifest and sibling checksum provide integrity checks, not an independent publisher signature. Release authenticity currently depends on maintainers protecting the configured GitHub repository, tags, and release publishing access.
