# Figma, storyboard/previs and implementation notes
Research date: 2026-09-27. No canvas writes and no implementation performed. Sources were live official docs plus read-only inspection of the existing repository and installed Figma skill. Product recommendations below are proposed decisions, not vendor claims.

## Most consequential finding: existing renderer destroys visual intent
Confirmed from local code, independent of any hypothesis about model taste:
- `core/src/saas_creative_director/figma.py:15` constructs only background, copy and generic objects. It exports composition_pattern as a string and tokens at manifest level; it does not compile a composition recipe. Object content, reference IDs, native UI source and asset identity are lost.
- `figma-plugin/src/code.ts:18` does not include tokens in its Manifest type. Lines 32–38 hardcode Inter Regular and ink; lines 47–48 hardcode background and no layout; 63–80 collapse every non-text type into a gray rectangle with dashed outline and identical fallback bounds. Pattern name is merely a label/plugin-data field. The background created without bounds becomes a 640×420 rectangle at (240,280), although the frame fill hides the issue visually. Empty intended copy becomes literal “Copy”. Every scene looks structurally similar regardless of reference selection.
- Import at lines 105–108 always creates frames. Re-import duplicates/overlaps instead of reconciling; no node-ID report or screenshot/readback acceptance.
- `tests/test_figma.py` checks scene count, page name, nonempty layers and locked annotations. It cannot detect pattern collapse, clipping, missing tokens or editability defects.
- `figma-plugin/manifest.json` disallows all network access. Asset retrieval cannot simply be added as external fetch without an explicit design change. Prefer user-supplied local bytes through UI or already-imported Figma assets.
- `core/schemas/storyboard.schema.json` leaves objects untyped and motion/transition as prose; it cannot validate semantic continuity or generate real entry/exit states.

Diagnosis implication: adding a knowledge base without changing the scene contract and renderer will preserve the same visual sameness. Fix intent preservation first and measure both composition decisions and rendered results.

## Capability distinctions (do not repeat obsolete assumptions)
As of this check, official Figma MCP documentation lists remote `use_figma` for creating/editing/inspecting nodes, `create_new_file`, `upload_assets`, design-system lookup and screenshots. `generate_figma_design` imports live web interfaces; it is not itself a scene planner. `get_motion_context` extracts animated node/keyframe information, not arbitrary timing from a reference movie. These are official MCP capabilities, also exposed by this installed Codex Figma connector; they must not be described as universally Codex-only. Availability still depends on client/tool exposure. [Official tool index](https://developers.figma.com/docs/figma-mcp-server/tools-and-prompts/).

The general REST file API provides structured node inspection; do not design arbitrary scene-node creation around a nonexistent generic REST node-write endpoint. [REST overview](https://developers.figma.com/docs/rest-api/), [file endpoints](https://developers.figma.com/docs/rest-api/file-endpoints/).

Authentication, supported clients, seat, plan and file access matter. MCP read calls have rate limits; some writes are exempt. Run capability discovery and identity/permission checks in the actual implementation environment, cache per-run reads and never hardcode present limits as architectural constants. [Access and limits](https://developers.figma.com/docs/figma-mcp-server/rate-limits-access/).

Use one scene model and two transports: the existing deterministic Figma importer as portable baseline; a capability-gated MCP adapter as optional convenience. Do not make all customers adopt an agent-specific runtime. Never emit code using installed MCP convenience methods as though every method existed in the regular plugin runtime.

## Installed figma-use constraints relevant to adapter design
Read `/Users/denisfedko/.codex/plugins/cache/openai-curated-remote/figma/13.0.0/skills/figma-use/SKILL.md` as local integration documentation. Its hosted execution is not identical to a conventional plugin: return structured IDs; no top-level IIFE/closePlugin; page context resets; switch once per call; await promises; honor safeToRetryWithoutCanvasRead on failure. Its helpers such as query/set/createAutoLayout must remain inside that adapter unless supported by the target plugin typings. Standard plugin can retain ordinary runtime APIs.

All text creation and mutation needs available fonts loaded first. Font load does not download arbitrary internet fonts. [Official font API](https://developers.figma.com/docs/plugins/api/properties/figma-loadfontasync/). Preflight real font family/style, explicit approved fallback; record substitutions rather than silently styling every brand in Inter. Text wrapping needs width/height/reflow validation, including longer localized copy.

Use auto-layout for structurally related UI groups; absolute layout is appropriate for the shot canvas and intentional floating elements. Images stay raster: editable image crop/container is not editable inner UI. Preserve this distinction in handoff and editability metrics. Components can be reused when accessible, with provenance and stable keys. Do not imply a bitmap is a native reconstruction.

## Storyboard/previs workflows worth learning from
| Product | Verified capability | Lesson for our product | MVP integration decision |
|---|---|---|---|
| Boords | Timed boards, audio, frame comments, attributed versions and approvals, exports | A board is a versioned sequence with review state, not a contact sheet | Borrow data/workflow principles; no dependency |
| Toon Boom Storyboard Pro | Drawing/layout, timeline, camera movements and sound | Capture action over time; one pretty still cannot validate a transition | Motion specs and boundary states now; native timeline integration later |
| Wonder Unit Storyboarder | Fast sketch boards, dialogue/action/timing metadata, external artwork editing and exports | Low fidelity can communicate intent without implying final design | Inspiration for compact annotations and optional animatic; no integration |
| Figma Weave | Reusable node workflows encoding style references and sequence logic; generated frames and editing | Reuse a coherent direction across the sequence | Optional visual exploration later; native Figma scene nodes remain contract |

Sources: [Boords](https://boords.com/about), [Boords concepts](https://boords.com/docs/concepts), [Toon Boom](https://shop.toonboom.com/en/products/storyboard-pro), [Storyboarder](https://wonderunit.com/storyboarder/), [Figma Weave](https://www.figma.com/solutions/ai-storyboard-generator-weave/). These are product capability claims, not proof their generation quality solves modern SaaS design. Storyboarder public product page is old; do not describe its release cadence as current. Weave does not prove generated raster panels become native UI layers.

## Proposed MVP scene/pattern-to-Figma contract
Introduce versioned `scene-graph.schema.json` and `figma-manifest.schema.json`, rather than adding unvalidated prompt text. Keep motion meaning separate from transport:
- root: schema_version, project_id, storyboard_revision, knowledge_snapshot_id, pattern_pack_version, renderer_version, source_artifact_hash, canvas/aspect_ratio, token_refs, asset_registry, scenes.
- scene: stable scene_id, beat_id, purpose/message/evidence_ids, pattern_id/version, reference_fragment_ids, adaptation_rationale, duration, state_frames[], transition_contract, limitations.
- state_frame: state_id, time_ms, entry/hero/exit role, camera_crop, node tree. MVP requires hero plus entry/exit only when needed to communicate causal change; avoid tripling every trivial scene.
- node: stable semantic_id, parent_id, native kind (frame/text/vector/rectangle/image/component_instance), semantic_role, bounds or layout constraints, z-order, token refs, content, component_key or asset_id, crop, clipping, editability class, source provenance, ownership.
- motion_spec: object_id, property, from/to states, time interval, easing family, attention purpose; validate target exists and time is within scene. Timing is a pre-production proposal, not measured reference evidence unless actually timecoded.
- transition_contract: incoming/outgoing anchor identity, camera/scale relationship, continuity constraints, direction and rationale.
- asset registry: source type (user screenshot/native UI/licensed/generated/placeholder), checksum, permission scope, crop, native_ref when available. Explicit placeholders carry missing-asset status, never pass as authentic UI.
- pattern recipe: allowed semantic slots, minimum required product data, composition constraints, density range, focal hierarchy, typography scale, states, layout variants for supported ratios, compatible transitions, contraindications, supported renderer capabilities. Patterns specify grammar, not a studio's signature palette/illustration.

Start with 6–8 deterministic, materially distinct recipes: anchored UI detail; before/after same object; input→operation→verified result; progressive disclosure; relationship/network focus; evidence/result proof; typographic bridge; optional split-context comparison. Recipe names are proposals; choose final set against the curated cases. Require deliberate hierarchy and purpose, not random variety.

## Import and handoff contract
- Preflight schema, asset resolution, renderer capability, font availability, provenance and approval revision. Fail on unsupported required native type, do not silently downgrade to gray rectangle.
- Deterministic semantic IDs map to node IDs. Upsert only nodes owned by generator and only within designated project/revision container. Detect human edits via previous generated hash/property snapshot. Preserve or report conflict, never overwrite silently. Duplicate-as-new-revision is explicit mode.
- Stage import in a new scoped container, produce a write report (created/updated/skipped/conflicts, all IDs), then mark complete. Handle partial execution by reading actual canvas before retry. Keep old approved revision until new QA passes.
- `figma-export-report.json`: actual bounds, node kinds, font substitutions, unresolved assets, native-text count, fully rasterized UI areas, node map and file URL; attach to handoff.
- Readback QA validates structure and semantic roles; screenshot QA validates composition and legibility. Exporter unit tests alone cannot validate the canvas.
- Human approval is tied to artifact hash/revision. A renderer change invalidates rendered-board approval even if script text unchanged.

## Thin feasibility spike (planned, not executed)
1–2 implementation days, after scene schema/fixtures: 3 scenes with different recipes using one native UI component, one screenshot-crop scene and one proof/comparison; long copy variant; entry/hero/exit on one scene. Import via existing plugin, then optional MCP adapter if exposed.
Acceptance: native text and vectors remain editable; screenshot explicitly labeled raster; semantic IDs/readback matches graph; all three recipes visibly distinct; token changes propagate; no accidental overlap/clipping at declared delivery size; second identical import creates zero duplicates; missing fonts/assets fail with actionable report; simulated partial import and human edit survive retry; screenshots inspected. Approval evidence must distinguish “specified”, “unit-tested” and “verified in actual Figma”.

## Concrete file delta proposal
Modify `core/src/saas_creative_director/figma.py` into validated graph→manifest compiler; `figma-plugin/src/code.ts` into version-dispatching importer with native nodes, tokens, assets, reconciliation/readback; plugin UI for preflight/report; extend storyboard schema; update tests/test_figma.py to assert semantic preservation and pattern diversity (not merely layer existence).
Add `core/schemas/scene-graph.schema.json`, `core/schemas/figma-manifest.schema.json`, `core/schemas/figma-export-report.schema.json`; `core/src/saas_creative_director/composition.py`; `core/renderers/patterns/` recipe definitions or existing pattern library recipe extension; `tests/fixtures/figma/`; `docs/FIGMA_CAPABILITIES.md`, `docs/FIGMA_QA.md`; later optional `core/src/saas_creative_director/adapters/figma_mcp.py`. Do not build both adapters before proving the common scene contract.

## Claude Skills packaging notes
Official Claude Code skills live in personal `~/.claude/skills/` or repository `.claude/skills/`, or namespaced plugin skills. Personal files are not automatically available in Cowork/cloud; account-enabled skills or committed project skills have different distribution paths. Skills load supporting content on demand, which fits core instructions plus external pattern/reference records. Naming collisions have precedence rules, so installation docs must detect existing skills rather than overwrite silently. [Official skills documentation](https://code.claude.com/docs/en/skills).

Recommendation: maintain one canonical `core/skills/` source and an installer/distribution manifest, not multiple edited copies. Installer dry-run reports target platform/location, collisions, package version/checksum and dependencies. Release upgrade modifies vendor-managed core only, snapshots prior release and resolved config, migrates a copy, runs schema/eval smoke checks, then activates atomically. Rollback restores code plus matching compatible schemas/knowledge snapshot; never deletes user projects/custom knowledge. Version core, knowledge pack, graph/manifest schema and renderer separately with explicit compatibility matrix. Ship pinned fixture sets for reproducibility; update docs must not claim Claude has an automatic rollback primitive for arbitrary skill bundles. These are repository responsibilities.
