# Figma storyboard workflow

The Figma importer turns the compact `figma-manifest.json` contract into native, editable storyboard boards. Coordinates and repeated UI structures are compiled locally; the plugin does not call a model, download fonts, fetch assets, or use the network.

For a causal scene, the storyboard output is a set of distinct panel frames grouped by narrative beat. It must not combine setup, action, transformation, and result into one simultaneous dashboard. Shared semantic object IDs preserve continuity across panel instances even when position, scale, crop, or product state changes. Each panel identifies its transition from the previous panel. Scene-level purpose, voiceover, evidence, and locked/free decisions remain shared handoff data rather than duplicated notes on every panel.

## Generate and import

1. Generate a manifest with `./scd figma-manifest <project> --output <project>/artifacts/figma-manifest.json`.
2. In Figma Desktop, import `figma-plugin/manifest.json` as a development plugin.
3. Run **SaaS Creative Director Importer** and select the generated JSON file.
4. Review the visible handoff cards beside every scene and open the compact import report.

Storyboard 1.1 panel-sequence scenes compile their declared panels and object presentations. Storyboard 1.0 single-frame scenes select one of three versioned deterministic compositions explicitly: source convergence, horizontal flow, or focus/detail. Legacy 0.5 scenes keep the earlier composition-pattern inference path and are labelled `legacy-inferred` in the manifest. Unsupported explicit recipes or recipe versions fail before any canvas write. The output uses native text, frames, rows, pills, and connectors. Screenshot and image inputs are labelled `RASTER` and reported as missing replacement assets; unsupported object types get a visible `UNSUPPORTED` placeholder.

The scene contract carries states, timed events, transition anchors, and normalized production-object semantics into the content hash, manifest, visible handoff rail, and compact readback. Changing a recipe, motion event, transition anchor, or production object therefore creates a new scene revision instead of silently reusing an outdated board.

The renderer accepts only a bounded token subset: named color roles, base spacing/corner/stroke values, and four type-scale roles. Missing roles receive neutral defaults. Unknown visual-direction fields such as free-form palette labels never become executable renderer input. Approved color, spacing, and type values are applied to native nodes and are part of each scene hash.

## Safe reimport behavior

Scene and node semantic IDs are stable for the same storyboard content. The operation ID and content hashes are deterministic.

- Reimporting the same operation creates no duplicates.
- A new operation reuses scenes whose scene revision and content hash did not change.
- After a successful import, the target page stores a compact operation receipt mapping every scene to its complete board. Exact retries validate this receipt, including boards reused from an older operation.
- A missing or corrupt receipt is reconstructed only when every manifest scene has an exact, complete board; partial drafts are never promoted by reconstruction.
- A changed scene creates a new draft beside its prior revision.
- Existing boards are fingerprinted. Manual changes are preserved and reported; the plugin does not merge over them.
- An interrupted operation is reported as an incomplete draft on retry instead of being repeated blindly.
- If a bounded write fails, nodes and empty pages created by that attempt are removed where the plugin runtime permits.

The default mode deliberately avoids automatic merging of arbitrary designer edits. Delete an unwanted draft manually only after checking it does not contain work that must be retained.

## Preflight and limits

The Python compiler and plugin both validate the complete manifest before canvas writes. The plugin also resolves and loads a local font before writing. Its report records the requested font, actual font, and fallback status.

Current hard limits are 2 MB per manifest, 48 scenes, 2,500 nodes total, 200 nodes per scene, 4,000 characters per text value, 100,000 text characters total, 12 pages, and 8,192 px per canvas dimension. Node types are allowlisted. Executable JavaScript, SVG payloads, external references, and network asset URLs are not accepted by this contract.

The compact readback contains receipt status, scene IDs, scene revisions and hashes, recipe/pattern versions, state/event/anchor IDs, production-object IDs, created/reused state, board node IDs, object counts, missing raster assets, text-overflow findings, font fallback, and warnings. It does not return the full Figma document tree.

## Production boundary

These boards are editable production wireframes and static motion-direction artifacts. A contact sheet can verify hierarchy, causal order, object continuity, and editability. It does not prove easing, timing feel, audio synchronization, or final animation quality. Those require an animatic or rendered video review and a human production approval.
