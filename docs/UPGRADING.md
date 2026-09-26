# Upgrading and rollback

For a plain-language Russian workflow, see [`docs/ru/UPDATING.md`](ru/UPDATING.md). The commands below are the maintainer interface used by Claude when requested.

## Normal update

```bash
./scd update
```

The updater resolves the latest GitHub Release, downloads its `.tar.gz` asset, verifies its manifest when present, checks Python and installer compatibility, compares semantic versions, creates a timestamped backup, and atomically replaces only managed product paths. It then runs the health check.

For an offline or pre-release package:

```bash
./scd update --from /absolute/path/to/scd-core-v0.6.0.tar.gz
```

A checked-out release directory is also accepted by `--from`.

## Compatibility rules

- Patch releases (`0.5.0 → 0.5.1`) fix compatible behavior or docs.
- Minor releases (`0.5 → 0.6`) may add schemas and optional fields; read the migration guide.
- Major releases require `--allow-major` and an explicit migration guide.
- Downgrades are rejected by `update`; use `rollback` so the matching core backup is restored.
- Project schema compatibility is declared in `core/COMPATIBILITY.json`.

## Migrations

Read `docs/migrations/<from>-to-<to>.md` before minor or major updates. Migrations must be non-destructive by default. A migration may create a new derived artifact or report incompatible project data; it must not rewrite protected data without a separate explicit command and a backup.

## Rollback

The last backup can be restored with:

```bash
./scd rollback
```

Choose a specific backup when necessary:

```bash
./scd rollback --backup /absolute/path/to/.scd/backups/v0.5.0-TIMESTAMP.tar.gz
```

Rollback itself makes a backup of the current core first. It restores managed product files only, leaving projects, local settings, knowledge, and overrides untouched.

## Failed health check

Do not continue client work after a failed update. Run `./scd health-check` again, inspect the failed line, and either correct the environment or run `./scd rollback`. The updater never deletes its pre-update backup after failure.
