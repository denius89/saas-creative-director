---
name: storyboard-composition
description: Turn an approved SaaS narrative and visual grammar into a timed, evidence-linked storyboard and editable Figma wireframe manifest. Use for scene composition, hierarchy, UI placement, attention, motion notes, transitions, and production annotations.
---

# Storyboard composition

Write `artifacts/storyboard.json` against `core/schemas/storyboard.schema.json`. Every scene must have one purpose and one dominant message, duration, a versioned pattern/recipe, stable semantic object IDs, positioned objects, copy/VO, attention sequence, meaningful states, motion events, transition anchors, sources, locked decisions, and creative freedom. Trivial scenes need only a hero state; causal transformations need the boundary states required to understand the change.

Check that total scene duration equals `total_duration_seconds`, proof appears where a claim is made, event times are within their scene, referenced objects exist, attention order is physically possible, and transition anchors resolve across adjacent scenes. Avoid ornamental scenes with no narrative job.

Then create `<project>/artifacts/figma-manifest.json` with the deterministic compiler. Do not hand-author repetitive per-node geometry or executable plugin code. Use the prebuilt Figma importer for the MVP; an available official Figma transport may consume the same manifest later. Import changed scenes only, keep raster assets explicitly labelled, and run `visual-qa` on the rendered contact sheet/readback. The manifest is an interchange format, not the final deliverable.
