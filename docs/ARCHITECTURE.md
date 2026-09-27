# Architecture

## Product boundary

The system ends at evidence-backed creative direction, storyboard, and editable production wireframes. It does not render a final film. Human creators retain strategy approval, creative selection, illustration language, animation craft, and final polish.

## One orchestrator, composable skills

`project.json` is the state machine. The Python CLI advances stages and enforces gates; Claude applies judgment through one stage-specific skill. Skills do not behave as independent agents.

Each stage boundary materializes a bounded context packet and a checkpoint with artifact digests, gate revisions, next actions, and unresolved items. The context cache is project-scoped and returns a hit only when dependency digests match. These controls reduce repeated reads; their token target is advisory and cannot change account billing or provider limits.

```text
client inputs
    ↓
source registry → evidence registry
    ↓                    ↓
product intelligence → competitor intelligence
    ↓
video strategy ── strategy gate
    ↓
reference intelligence → narrative directions → motion direction + representative frames ── creative gate
    ↓
scene retrieval → timed storyboard → deterministic Figma manifest → editable frames → visual QA
    ↓
production review ── production gate → handoff
```

Motion Direction is required before Creative Direction approval. Rendered Visual QA is required before Production Review; `BLOCKED` QA and unresolved blocker findings cannot receive Production approval. When a reviewed dependency changes, both `project.json` and the gate audit record become stale.

## Evidence model

- `CONFIRMED`: direct primary evidence supports the exact claim.
- `SUPPORTED`: multiple indirect or secondary signals support an interpretation.
- `HYPOTHESIS`: a strategically useful inference awaiting validation.

Artifacts reference `EV-*` IDs instead of copying provenance ad hoc. The validator rejects unknown evidence links and confirmed records without a registered source.

## Lifecycle boundary

Managed paths are an explicit allowlist in `maintenance.py`. User-owned paths are separate by construction:

```text
managed:    core/ .claude/skills/ docs/ figma-plugin/ evals/ examples/ public knowledge/
protected:  INBOX/ config/ overrides/ knowledge/custom/ projects/ caches/logs/backups
```

An updater stages a release, verifies compatibility and checksums, backs up managed paths, then swaps only those paths. No update routine recursively copies the repository root.

## Figma contract

The approved storyboard revision is the semantic source. `figma-manifest` maps its stable scene and object IDs to editable layers, visible annotations, evidence links, timing, transition anchors, locked decisions, and creative freedom. Layout recipes turn semantic scene data into repeated geometry without asking the model to describe every node. The importer creates native Figma nodes, records a compact readback, and must not silently overwrite changed human-owned nodes.

The first supported path is the bundled local plugin. An official Figma transport may consume the same validated manifest later; it does not define a second scene contract. See [`MOTION_INTELLIGENCE.md`](MOTION_INTELLIGENCE.md).
