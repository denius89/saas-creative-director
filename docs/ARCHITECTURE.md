# Architecture

## Product boundary

The system ends at evidence-backed creative direction, storyboard, and editable production wireframes. It does not render a final film. Human creators retain strategy approval, creative selection, illustration language, animation craft, and final polish.

## One orchestrator, composable skills

`project.json` is the state machine. The Python CLI advances stages and enforces gates; Claude applies judgment through one stage-specific skill. Skills do not behave as independent agents.

```text
client inputs
    ↓
source registry → evidence registry
    ↓                    ↓
product intelligence → competitor intelligence
    ↓
video strategy ── strategy gate
    ↓
reference intelligence → narrative directions ── creative gate
    ↓
visual grammar → timed storyboard → Figma manifest → editable frames
    ↓
production review ── production gate → handoff
```

## Evidence model

- `CONFIRMED`: direct primary evidence supports the exact claim.
- `SUPPORTED`: multiple indirect or secondary signals support an interpretation.
- `HYPOTHESIS`: a strategically useful inference awaiting validation.

Artifacts reference `EV-*` IDs instead of copying provenance ad hoc. The validator rejects unknown evidence links and confirmed records without a registered source.

## Lifecycle boundary

Managed paths are an explicit allowlist in `maintenance.py`. User-owned paths are separate by construction:

```text
managed:    core/ .claude/skills/ docs/ figma-plugin/ evals/ examples/
protected:  config/ overrides/ knowledge/custom/ projects/
```

An updater stages a release, verifies compatibility and checksums, backs up managed paths, then swaps only those paths. No update routine recursively copies the repository root.

## Figma contract

The storyboard is the semantic source. `figma-manifest` maps it to six pages and editable layers with stable names, annotations, evidence links, timing, locked decisions, and creative freedom. The development plugin creates native Figma nodes; visual designers can replace placeholder layers without losing structure.

