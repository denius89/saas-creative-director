# Figma live verification record

Status: **pending a Figma Desktop canvas with plugin write access**.

The compiler tests and TypeScript build verify the contract and implementation, but they do not substitute for inspecting the actual canvas. Complete this checklist in a disposable test file before treating the vertical slice as visually accepted.

## Canvas checklist

- Import the Ledgerly example and confirm the source-convergence, horizontal-flow, and focus/detail boards are visibly distinct.
- Confirm headline, UI labels, rows, pills, frames, and connectors are native selectable objects.
- Confirm every scene has a visible notes rail with purpose, VO/copy, duration, recipe/pattern versions, states/events, transition anchors, production objects, sources, locked decisions, and creative freedom.
- Change an approved accent color and headline size, regenerate, and confirm the new draft uses those tokens while unexpected token keys are rejected or ignored by the compiler contract.
- Import `tests/fixtures/figma/FIGMA_EDGE_CASE_STORYBOARD.json` through a temporary project manifest and verify Russian copy wrapping, the visible `RASTER` label, and the `UNSUPPORTED` placeholder.
- Edit a headline, move a row, and rename a generated layer. Reimport the identical manifest and confirm there are no duplicates and all edits remain.
- Change one scene in the storyboard, regenerate, and import. Confirm only that scene gets a neighboring draft revision while unchanged scene boards are reused.
- Repeat that mixed import and confirm its page receipt is validated: zero new boards, with both changed and previously reused scenes reported as reused.
- Simulate a missing requested font and confirm the UI reports the local fallback.
- Inspect the compact report for scene IDs, revisions/hashes, node IDs, object counts, missing assets, overflow, and warnings.
- Trigger an invalid or oversized manifest and confirm no final board is left behind.

Record the tested Figma Desktop version, operating system, date, screenshots/contact sheet, defects, and reviewer decision here or in the release evidence before changing this status.
