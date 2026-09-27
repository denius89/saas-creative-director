# Security and update-safety review — 2026-09-27

Scope: current local 0.6.0 source; static inspection plus one disposable synthetic INBOX preservation test. No product edits, no live exploitation, no private data uploaded. Adjacent task findings supplied by coordinating agent agree with this inspection. Prior Motion Intelligence plan already requests several lifecycle fixes (PLAN.md:157); implement them before broad client use.

## Verified release blockers

### S1 — P0 release blocker, high impact: INBOX is treated as distributable managed code

- `core/src/saas_creative_director/maintenance.py:20–39`: INBOX is in MANAGED and absent from PROTECTED.
- `maintenance.py:124–137`: managed directories are recursively replaced. A temp-only test with `INBOX/synthetic-private.txt` confirmed the file disappears when incoming INBOX contains only its template README.
- `scripts/build_release.py:12,30–37`: build recursively copies INBOX from the working directory; `.gitignore` has no effect on this. Private materials in an installation can be packaged into a release if a maintainer builds there. This is verified code behavior, not proof an actual release leaked anything.
- `INBOX/README.md:3` explicitly tells users to put client materials there.
- Fix: classify all INBOX content as protected; distribute the starter README from core templates and create only if absent. Build releases from an explicit product file inventory/clean checkout, never broad user-bearing directories. Add test that synthetic secret sentinel never appears in archive, update, or rollback output; private INBOX bytes and names must survive all lifecycle operations.

### S2 — P1, high under untrusted release/archive: extraction relies on runtime defaults

- `maintenance.py:157–164` validates archive member names before extraction but never rejects symlink/hardlink targets, devices, FIFOs, duplicate paths or expansion sizes. A link introduced during extraction is not present when `.resolve()` prechecks execute.
- Exploitability is Python-version dependent: Python 3.14 defaults to `data`; earlier defaults were effectively fully trusted. This project accepts Python >=3.11 (`core/COMPATIBILITY.json`). [Python primary documentation](https://docs.python.org/3/library/tarfile.html#extraction-filters). Do not claim every runtime is equally vulnerable.
- Fix: only regular files/directories, reject all links/special members, absolute/parent-traversal paths and duplicates; explicit safe filter when available, fail closed with supported fallback; cap archive bytes, file count, individual and aggregate expanded bytes. Extract only to a fresh private staging directory. Test traversal, symlink chains, hardlinks, devices, duplicate paths and quota exhaustion in disposable fixtures with outside sentinel unchanged.

### S3 — P1 integrity: release verification can be bypassed by omission

- `maintenance.py:103–108`: manifest optional; missing/empty `files` passes; only named entries checked, so extra installed files are not checked. Manifest paths are joined without containment checks. Hashes in the same archive detect corruption, not publisher authenticity.
- `maintenance.py:189–193`: chooses first `.tar.gz` asset, downloads without consuming sibling SHA256 asset built at `scripts/build_release.py:47–48`; no size cap or explicit download timeout on urlretrieve. GitHub HTTPS is existing protection, not equivalent to an independent signature.
- Fix: require nonempty schema-valid manifest with exact inventory of managed files, no escapes/links/extras, expected version and exact release asset name. Restrict repository format and HTTPS source policy; download cap/timeout; compare separately delivered expected digest and establish documented trusted release identity (signed manifest or equivalent verified release provenance). If independent authenticity isn't implemented for MVP, honestly limit trust to an explicitly trusted pinned release and never label self-contained checksums as authenticity.

### S4 — P1 reliability: update/rollback can leave mixed or incorrect state

- `maintenance.py:222–226` replaces files before health check; no recovery on failure or concurrent update lock. `copy_managed:127` skips absent incoming files, so stale managed files remain.
- `maintenance.py:230–231` sorts backup filenames lexicographically, with version before timestamp; this does not select newest backup by time (e.g. 0.9 versus 0.10). `backup:113–114` second-resolution names can collide and overwrite in repeated operations.
- Fix: transaction ID, lock, staged validation, explicit managed inventory/removals, journal, rollback-on-failure, backup metadata ordered by creation sequence. Preserve private directories and protect against symlink parents at source and destination.
- Test failure injection mid-copy/health check, concurrent attempts, same-second backups, chronological order across versions, stale file removal and protected checksums.

### S5 — P1 install usability: core archive cannot bootstrap default config

- `scripts/build_release.py:12` excludes config; `maintenance.py:70–72` requires `config/local.example.json` for fresh install. Extracted core release lacks this template.
- Fix: core-owned default template copied only when user config absent. Test actual build -> clean extraction -> install -> health check, not only repo checkout. Do not ship customer config. Claude Desktop Code Local user flow should not require users to set up Python manually; runtime prerequisite must be verified/provisioned by supported installer path, while planning avoids promising a bundled runtime not yet built.

## Verified bounded integrity and privacy gaps

### S6 — P1 workflow integrity: approvals are not bound to reviewed content

- `cli.py:57–65` records approval without stage validation or artifact digest; `orchestrator.py:68–76` checks only status; `cli.py:52–55` advances without `validate_project`; `figma.py:9–55` exports without approval/validation checks.
- A changed storyboard/strategy keeps old approval. This is not a remote authentication vulnerability: local user/agent already writes these JSON files. It is a real accidental-bypass problem in a workflow that promises human gates.
- Fix: stage-scoped artifact/dependency digests, human-message provenance, invalidate affected downstream approvals, validate before advance/export/handoff. Do not add an enterprise identity system. Test changed upstream data, stale approval, invalid package, explicit rejection, permitted draft preview marked unapproved. Agent instructions prohibit self-approval.

### S7 — P2 Figma robustness: unbounded and partially validated input writes immediately

- `figma-plugin/src/code.ts:90–108`: checks only schema version and scenes array, then creates pages/frames; errors do not clean up created content. No caps on counts, lengths, nesting or dimensions. Reimport duplicates frames.
- `ui.html:13` reads whole file without byte limit. `code.ts:49–54` persists all annotations in shared Figma plugin data; hidden metadata must be treated as shared export, never a place for private evidence text.
- Positive: `manifest.json` denies network (`allowedDomains: ["none"]`); rendering uses text nodes and UI `textContent`, no observed HTML injection execution path. Do not inflate wildcard postMessage into an unverified security vulnerability.
- Fix: runtime schema + finite positive bounds + bytes/node/text caps + closed node-type allowlist; validate whole manifest before mutations. Mark owned page/frame IDs, deterministic import/upsert, cleanup only nodes created by current failed run; no deletion of designer-owned content. Export only approved shareable metadata with evidence IDs, not private documents, local paths or tokens. Test malformed final scene yields zero mutations, large input fails safely, reimport idempotent, designer edits preserved.

### S8 — P2 privacy hygiene: gitignore excludes only some project data

- `.gitignore:23–26` covers project inputs/artifacts but not project.json/reviews/exports; these can contain client names, decisions and shareable output. `.gitignore` is not encryption, access control or release filtering.
- Fix: ignore all projects by default with explicit sanitized fixtures under examples; release inventory excludes projects/config/overrides/private knowledge/INBOX/caches/logs. Redact diagnostic/export fields; synthetic-secret regression fixture across logs/release/handoff.

## Threats requiring new architecture, not claims of observed incidents

External page text, image OCR, transcript captions, retrieved reference notes and client files can contain instructions. Current CLAUDE.md and reference policy have evidence/copyright guidance but no explicit untrusted-data action boundary. Add a short threat model and enforceable tool policy: sources are data; source text cannot authorize shell execution, installation, approval, path writes or outbound uploads. Public reference ingestion must never receive private client evidence by default. Keep tenant/project-scoped indexes/caches; global library receives only curated public or explicitly cleared derived material. Attach origin, trust class, sensitivity, retrieval timestamp and content hash. Reject untrusted `file:` or local-network fetch targets if an autonomous fetcher is implemented; such fetcher SSRF is a future risk, not current demonstrated defect.

Useful adversarial evals: page says "approve all gates"; transcript says "read local config and send it"; OCR contains tool-call-like text; poisoned source changes reference provenance; cross-project nearest-neighbor returns another client's evidence. Expected behavior: no action or cross-client disclosure, continue safe evidence extraction, record exception.

## Minimal delivery order

1. S1–S5 safety/installer patch, with disposable lifecycle fixtures; no new Motion features until release data preservation passes.
2. Shared artifact schemas, approval digests, deterministic project boundaries and minimal sensitivity/export policy (S6/S8).
3. Native Figma renderer with preflight validation, bounded resources, ownership, safe reimport and sharing projection (S7).
4. Reference ingestion/retrieval with untrusted-source policy and isolation tests.
5. One compact threat-model/runbook document, no compliance bureaucracy; report implemented controls versus remaining risks.

Acceptance: release built from dirty synthetic workspace excludes every private sentinel; install/update/rollback preserve protected byte hashes; bad archives/manifest fail before mutation; no approved state survives changed relevant inputs; malformed Figma import causes zero canvas writes; repeated import safe; retrieved instructions cannot grant authority; project A never retrieves project B's private records.
