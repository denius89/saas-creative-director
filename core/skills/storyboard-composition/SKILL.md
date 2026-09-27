---
name: storyboard-composition
description: Turn an approved SaaS narrative and visual grammar into a timed, evidence-linked storyboard and editable Figma wireframe manifest. Use for scene composition, hierarchy, UI placement, attention, motion notes, transitions, and production annotations.
---

# Storyboard composition

Write `artifacts/storyboard.json` against `core/schemas/storyboard.schema.json`. Treat each top-level scene as a narrative beat, not automatically as one finished picture. Every scene must have one purpose and one dominant message, duration, a versioned pattern/recipe, stable semantic object IDs, positioned objects, copy/VO, attention sequence, meaningful states, motion events, transition anchors, sources, locked decisions, and creative freedom.

For a causal product beat, add the minimum storyboard panels needed to read setup, action, transformation, and result. A panel is a representative drawing; a production keyframe is a timed property value and is outside this storyboard contract. Preserve semantic object identity across panels while allowing its visible instance, bounds, crop, content state, and emphasis to change. Use each panel's transition from the previous panel to distinguish a cut or dissolve from a continuous transform or camera move. Do not create a panel for every cursor move or decorative microinteraction.

Never collapse consecutive states into one infographic merely because they fit on the canvas. A result must not be visible before the action that causes it. Side-by-side states are allowed only when simultaneous comparison or summary is the communication job. If the active schema or renderer cannot express the required sequence as distinct editable panels, record a handoff blocker instead of substituting a composite frame.

Check that total scene duration equals `total_duration_seconds`, panel timing is monotonic and bounded, proof appears where a claim is made, event times are within their scene, referenced objects exist, attention order is physically possible, results follow their triggers, and transition anchors resolve across adjacent scenes. Avoid ornamental scenes with no narrative job and avoid over-segmenting a state change that one panel plus a motion note communicates clearly.

Then create `<project>/artifacts/figma-manifest.json` with the deterministic compiler. Do not hand-author repetitive per-node geometry or executable plugin code. Use the prebuilt Figma importer for the MVP; an available official Figma transport may consume the same manifest later. Reimport changed scenes only, keep raster assets explicitly labelled, and run `visual-qa` on the rendered contact sheet/readback. For timing or pacing claims, also review a timed animatic; a static Figma strip cannot verify them. The manifest is an interchange format, not the final deliverable.
