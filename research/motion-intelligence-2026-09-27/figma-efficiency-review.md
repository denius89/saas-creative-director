# Figma efficiency/security re-review — 2026-09-27

Research and planning only. No Figma write, no product code changed. Sources verified live; no real Figma execution was performed. Repository base: `/Users/denisfedko/.codex/.chatgpt-projects/g-p-6ab8253b4c988191a16db7c9b9c5d78b`.

## Decision

Keep the existing local importer as the **default MVP transport**, with a deterministic compiler consuming a compact semantic scene contract. Prove it with three scenes first. Defer the full MCP adapter until that contract and renderer pass actual Figma acceptance. MCP is a convenience/inspection transport, not an extra planner or a second source of truth. This is a cost/portability engineering decision, not a claim that Figma MCP cannot write.

Official Figma documentation confirms remote `use_figma` writes native frames, components, variables and auto-layout. See [Write to canvas](https://developers.figma.com/docs/figma-mcp-server/write-to-canvas/). Current [tool index](https://developers.figma.com/docs/figma-mcp-server/tools-and-prompts/) lists structured inspection, screenshots, asset transfers and writes; `upload_assets` accepts specified raster formats with 10 MB per asset. These capabilities must be discovered in the actual execution client. Assets that are bitmaps remain raster within an editable container; do not count their internal UI as editable.

## Confirmed repository issues

- `core/src/saas_creative_director/figma.py`: exports pattern name but does not compile pattern-specific layout; drops content, native component/asset identity. This is a fidelity defect before any question of model quality.
- `figma-plugin/src/code.ts`: hardcoded Inter and colours, all non-text objects become rectangles, defaults collide, empty text becomes “Copy”; always appends frames, no reconciliation, no scoped ownership, no actual-node report. Font load is repeated per text node instead of cached per unique family/style. It scans page names and creates six pages even if unused.
- `figma-plugin/manifest.json`: network denied, which is a useful default; lacks `documentAccess: "dynamic-page"`. Official [manifest documentation](https://developers.figma.com/docs/plugins/manifest/) says this field is required for new plugins and omission can trigger loading the whole file. Add it and validate actual scoped page operations.
- `figma-plugin/ui.html`: JSON upload checks syntax only; no manifest size/depth/node-count limits, disabled duplicate submission or preflight confirmation/report. It currently uses `textContent` for status, which should remain; never replace with untrusted HTML.
- `tests/test_figma.py`: minimal existence tests cannot detect loss of composition or safe reimport failures.

## Make token saving structural

The model chooses semantic structure and content; deterministic code computes repetitive node coordinates/style fields, serializes manifest and validates it. Do not ask the model to emit full per-node JS anew for each board. Keep reusable renderer code on disk. Do not paste node map, full asset bytes, whole Figma XML, every screenshot or generated manifests back into model context.

Store full reports/files externally; return `{revision, status, counts, blocking_findings, report_path, changed_scene_ids}`. Full node map is necessary for reconciliation but not for model context. Query only designated project container and changed scenes. Cache component/token lookup by file/library revision, not globally forever. Font loads and identical assets are deduplicated within import.

Start with 3 working recipes; expand to 6 only if benchmark coverage demands it. The prior plan's simultaneous 12–16 patterns/8 native recipes, two transports and broad component support is unnecessary before feasibility evidence. Hero frames are default; entry/exit only for causal changes/transition proof, not three full states for every scene. One G2 contact sheet and one G3 final contact sheet; inspect individual crops when legibility or a QA finding needs them. A low-resolution contact sheet alone does not prove text readability.

## Proposed measurable budgets (engineering policy, not vendor limits)

Fixture: 8–12 scenes, one aspect ratio, up to 300 generated semantic/native nodes before explicitly splitting the board.

- Plugin path: **zero model calls to materialize a validated manifest**. Human launches one import. One compact structural report, plus contact sheet; additional calls only for findings.
- Optional MCP path: target 1 capability/target inspection (cached for run), 2–4 bounded write batches, 1 compact structural readback, 1 contact-sheet capture where tooling supports grouping; <=8–10 operations normal path, not a guarantee and not permission to omit checks. Snapshot/capture capabilities may require several calls. Do not count every image as free.
- Report in model context: target <=2,000 text tokens for complete board QA summary; detailed findings in files, on demand.
- Initial scene-batch safety ceiling: <=100 native nodes/write batch, <=1 MB manifest JSON excluding assets. These are tunable project limits established in spike; not Figma API hard limits. Reject oversized/unbounded input before mutation.
- No-change reimport: zero new frames, zero mutations; no-change checkpoint should require no new model reasoning.
- One-scene change: only that scene and genuine transition dependencies compile/import/review; no whole-project rerun. Model image inspection limited to affected scenes plus adjacency strip if needed.
- Repair cap: at most 2 targeted repair cycles per failing scene per run; unresolved problems become explicit findings. Never silently loop or weaken native editability to save quota.
- Record elapsed time, graph/manifest bytes, nodes created/changed/skipped, tool calls, response bytes, images and actual LLM usage (if exposed). Do not equate Figma rate limits with token charges or claim predicted savings as measured.

The official [access documentation](https://developers.figma.com/docs/figma-mcp-server/rate-limits-access/) makes read quotas dependent on plan/seat and notes that some write tools are exempt. It also limits access to supported clients and existing user permissions. Do not hardcode a universal monthly quota or imply all `use_figma` calls are unlimited. Capability/access preflight is required; detect quota failure and preserve the local artifact for later import.

## Safe writes and human edits

Use explicit file/page/container IDs and a project owner marker; never identify the destination solely by a shared page name. Manifest revision/hash must match approval. Each generator node gets a stable semantic ID and last-generated property fingerprint. Before mutation compare current values to last-generated values. Unchanged generator-owned nodes can update; edited nodes create a conflict. Default MVP response to conflict: keep old scene and create a new scoped revision for review, not clever automatic merge. Store the human decision once; do not require repeated approval for authorized writes within that scope.

Preflight schema/enums/finite numeric bounds/tree depth/node count/fonts/assets before writes. Stage a bounded revision container; never delete an approved board until new QA passes. Figma mutations are not promised atomic transactions: partial failure must return incomplete status and recorded IDs, followed by scoped readback before retry. A retry must upsert by semantic ID, not append blindly. Deletion is limited to explicitly identified generator-owned nodes in the allowed revision; never arbitrary page cleanup.

Figma layer names, text, comments, pluginData and imported metadata are untrusted content, not agent instructions. The default renderer accepts typed data, not arbitrary JS, SVG scripts, plugin source or network URLs embedded in the manifest. Any later MCP adapter executes fixed reviewed code templates with validated data; it must not turn a retrieved reference into executable code. Keep OAuth/PAT secrets out of manifests, reports and checked-in files. Do not add a custom credential store when connector authentication already suffices.

Keep `allowedDomains: ["none"]` for MVP importer; accept checked user-selected local asset bytes through UI, with MIME/size/dimension bounds and checksums. Do not base64-bloat model context. If external fetching is later needed, make it a separate allowlisted ingestion step with tenant/permission checks; deny local/private addresses and redirects outside policy. No portfolio videos or client assets embedded into handoff merely because publicly viewable. Track asset provenance and usage rights separately from visual citation. Avoid loading external webpages inside the plugin UI.

## Concrete delivery sequence and files

1. P0: Add benchmark and metrics before redesign: 3 scene fixtures, 1 hand-edited scene, duplicate-import case, oversized manifest/missing asset/partial-failure cases. Capture baseline actual Figma output.
2. P1: `core/schemas/scene-graph.schema.json`, `figma-manifest.schema.json`, `figma-export-report.schema.json`; `core/src/saas_creative_director/composition.py` and update `figma.py` to compile semantic content deterministically. Keep only validated native node kinds needed by three recipes.
3. P2: `figma-plugin/src/code.ts`, `ui.html`, `manifest.json`: dynamic-page, limited import, font cache, native layout/text/image containers, owned revision staging, idempotence, compact report export. Build `dist/code.js` through existing package process, not manual edits.
4. P3: `tests/test_figma.py`, fixture-driven plugin tests and actual Figma sandbox checks. Docs `docs/FIGMA_CAPABILITIES.md`, `FIGMA_QA.md`, `FIGMA_OPERATIONS.md` include both success and quota/partial-failure paths.
5. P4 after evidence: optional `core/src/saas_creative_director/adapters/figma_mcp.py` only if workflow friction warrants it; same graph, renderer expectations and report contract. Do not require a second adapter for MVP quality release.

Acceptance: all 3 scenes visibly distinct; text and intended native objects editable; raster usage explicitly reported; repeated import creates zero duplicates; single-scene change affects only approved scope; hand edits survive; missing fonts/assets fail clearly; failure/retry cannot silently duplicate or overwrite; changed brand token propagates; long copy reflows; graph/readback agree; actual Figma proof is saved. Native usability test: change headline, replace UI asset, alter a row state, locate transition/source notes and identify locked/free decisions. All timing/token savings remain hypotheses until measured against same fixture and same model/version.
