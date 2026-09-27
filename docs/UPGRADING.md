# Upgrading and rollback

For a plain-language Russian workflow, see [`docs/ru/UPDATING.md`](ru/UPDATING.md). The commands below are the maintainer interface used by Claude when requested.

## Normal update

```bash
./scd update
```

The updater resolves the exact versioned `.tar.gz` and checksum assets from the latest GitHub Release. It requires an exact file manifest, checks every file hash and compatibility rule, creates a transaction backup, and replaces only the paths declared in `core/release-policy.json`. A lock prevents concurrent maintenance. If activation or the health check fails, the transaction restores its backup automatically.

The published 0.6 updater used a hard-coded inventory and cannot copy newly introduced top-level knowledge directories during its first pass. The candidate carries those directories inside the already-managed `core` tree; the new `scd` launcher materializes them once, without overwriting an existing destination, before the next command. This bootstrap is covered by the 0.6 migration test and requires no manual file copying.

For an offline or pre-release package:

```bash
./scd update --from /absolute/path/to/scd-core-v0.7.0.tar.gz
```

A checked-out release directory is also accepted by `--from`, but it must contain the same complete verified manifest as a built release.

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

The successful update message also prints its transaction ID. Restore the backup created for that operation with:

```bash
./scd rollback --transaction TRANSACTION_ID
```

Rollback itself makes a backup of the current core first. It restores managed product files only, leaving projects, local settings, knowledge, and overrides untouched.

A manifest-free backup produced by the published 0.6 updater is accepted only from the same installation's `.scd/backups` directory, only with the original `vVERSION-UTC.tar.gz` filename, and only through version 0.6.0. It is unpacked with current size/type/path limits and checked against the old allowlist. Its old `INBOX` copy is deliberately ignored, so the live client materials are preserved. A manifest-free archive copied from elsewhere is rejected.

## Failed health check

Do not continue client work after a failed update. The updater first attempts automatic recovery from the transaction backup. Run `./scd health-check` again and inspect `.scd/transactions/` before choosing a manual rollback. The updater never deletes its pre-update backup after failure.

The release manifest and its sibling checksum detect missing, extra, or corrupted files. They do not independently prove who published the release. The trust boundary is the configured GitHub repository over HTTPS; pin and review that repository before using automatic updates.
