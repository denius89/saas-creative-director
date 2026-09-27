# Motion Intelligence Layer

The Motion Intelligence Layer turns an approved narrative into a current, evidence-backed visual grammar before the full storyboard is expanded. It is part of pre-production: it produces direction, composition, editable Figma wireframes, QA, and handoff data. It does not generate the final video.

## Runtime path

1. `creative-reference-research` retrieves concrete, inspected work separately from competitor research.
2. `motion-design-director` selects two treatments, explains trade-offs, and creates representative frames.
3. A human approves the narrative revision, direction revision, and representative frames.
4. `storyboard-composition` expands scenes with stable semantic objects, states, events, and transition anchors.
5. The deterministic compiler maps approved recipes and tokens to a typed Figma manifest.
6. The local Figma importer creates editable nodes and returns a compact readback report.
7. `visual-qa` checks rendered output and readback, then localizes repairs to affected scenes.

The normal client workflow uses one orchestrator and composable skills. It does not launch a standing group of agents. Model work chooses meaning; deterministic code handles repeated geometry, IDs, node names, and import bookkeeping.

## Knowledge layers

- `knowledge/references/`: concrete works with source, inspection method, timestamped observations, confidence, freshness, and non-copy guidance.
- `knowledge/patterns/`: abstract mechanisms that solve communication problems. Patterns never contain a source's brand assets or signature sequence.
- `knowledge/anti-patterns/`: conditional failure detectors. A trigger requires visible evidence and may be overridden with a documented reason.
- `knowledge/current-motion/`: dated synthesis records. These are hypotheses supported by inspected samples, not universal trend laws.
- `knowledge/custom/`: user-owned additions. Product updates never replace or publish this directory.

Project-private references stay inside the project. Promotion to shared knowledge is an explicit curation step that removes client material and preserves provenance.

## Freshness and confidence

Every current-motion or reference record carries `observed_at`, `review_after`, `source_ids`, `inspection_method`, `confidence`, and `status`. A stale record remains searchable but cannot be presented as current evidence until reviewed. Portfolio copy and thumbnails do not support claims about pacing or transitions; those fields remain unknown until the work is watched.

Suggested review intervals are shorter for tool capabilities and fast-moving surface treatments, and longer for durable information-design principles. Changing a synthesis does not silently alter an approved project. `motion-direction.json` stores a knowledge snapshot with current-motion IDs, versions, observation/review dates and status, plus the exact pattern and anti-pattern library versions used by its approved revision.

## Scene retrieval

Retrieval starts from the scene's communication mechanism, audience state, product fidelity, asset availability, channel, duration, and transition need. It returns at most three candidates by default:

1. a concrete inspected scene or work;
2. a reusable pattern derived from more than one observation when possible;
3. an anti-pattern or constraint relevant to the proposed treatment.

Industry and visual similarity are secondary. A reference is useful because it solves a comparable communication problem, not because it looks fashionable. The output includes adaptation rationale and a non-copy boundary.

## Human approval and revision binding

Approvals store the digest of the exact upstream artifacts reviewed. If an approved narrative or direction changes, downstream approval becomes stale. Figma import creates a new draft for a new approved storyboard revision unless an idempotent retry or a safe machine-owned update is explicitly selected.

## Usage controls

The standard preset expands two directions, inspects up to six new works, retrieves three candidates per distinct mechanism, performs one full storyboard pass, and allows two targeted correction cycles. These are operation quotas, not a guaranteed Claude token cap. Unknown subscription token counts remain unknown.

The product never enables Usage credits, auto-reload, an API key, or a different model. See [Claude usage and billing](USAGE_AND_BILLING.md).

## Release boundary

Core skills, schemas, compiler recipes, and public curated knowledge are versioned product files. `INBOX/`, `projects/`, `config/`, `overrides/`, `knowledge/custom/`, caches, logs, backups, and exports are protected user data. Schema and pattern changes require changelog entries and migrations when existing project data is affected.
