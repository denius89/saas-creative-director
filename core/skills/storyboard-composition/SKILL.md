---
name: storyboard-composition
description: Turn an approved SaaS narrative and visual grammar into a timed, evidence-linked storyboard and editable Figma wireframe manifest. Use for scene composition, hierarchy, UI placement, attention, motion notes, transitions, and production annotations.
---

# Storyboard composition

Write `artifacts/storyboard.json` against `core/schemas/storyboard.schema.json`. Every scene must have one purpose and one dominant message, duration, composition pattern, positioned objects, copy/VO, attention sequence, motion, transition, sources, locked decisions, and creative freedom.

Check that total scene duration equals `total_duration_seconds`, proof appears where a claim is made, attention order is physically possible, and transitions preserve continuity. Avoid ornamental scenes with no narrative job.

Then run `scd figma-manifest <project> --output <project>/artifacts/figma-manifest.json`. Use the Figma scaffold or official Figma tooling to create native frames and layers. The manifest is an interchange format, not the final deliverable.
