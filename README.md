# SaaS Creative Director

An evidence-backed creative pre-production system for SaaS video. It turns a client brief, product material, market research, and references into an approved strategy, narrative, storyboard, and editable Figma wireframe specification.

It deliberately does **not** generate a final video. The system removes repetitive research and production planning while leaving interpretation, taste, final illustration, and motion craft to people.

## What ships in V0.5

- one deterministic project orchestrator with three human approval gates;
- a claim/evidence model that separates confirmed facts, supported interpretations, and hypotheses;
- nine composable Claude Skills for intake through production review;
- schemas and validation for every handoff;
- competitor and reference intelligence structures;
- strategy, narrative, visual direction, and storyboard contracts;
- a Figma import manifest plus a small plugin scaffold for native, editable frames;
- an end-to-end example, quality rubric, and automated tests.

## Quick start

Requires Python 3.11+. No runtime packages are required.

```bash
./scd install
./scd init projects/my-client --name "My Client"
./scd status projects/my-client
./scd validate projects/my-client
```

Open the repository in Claude Code and use the prompt in [`docs/ONBOARDING.md`](docs/ONBOARDING.md). Claude reads [`CLAUDE.md`](CLAUDE.md) and loads only the skill needed for the current stage.

To try the complete sample:

```bash
./scd validate examples/ledgerly
./scd status examples/ledgerly
./scd figma-manifest examples/ledgerly --output /tmp/ledgerly-figma.json
./scripts/test.sh
```

## Workflow

```text
intake → product intelligence → competitor intelligence → video strategy
                                                        ↓ gate 1
reference research → narrative + creative directions → visual direction
                                                        ↓ gate 2
storyboard + composition → Figma wireframes → production review
                                                        ↓ gate 3
illustrator / motion handoff
```

Gates are intentional. The AI advises and prepares; a person approves strategy, creative direction, and production readiness.

## Repository map

```text
core/skills/          immutable, versioned Claude Skills
.claude/skills/       discovery adapters composing core + overrides
core/src/             deterministic orchestration and validation
core/schemas/         JSON contracts between stages
figma-plugin/          editable-frame import scaffold
evals/                 quality rubric and fixture checks
examples/ledgerly/     complete fictional project
docs/                  onboarding, architecture, and version history
projects/              local client workspaces (sensitive files ignored)
config/                protected local settings
overrides/             protected skill customizations
knowledge/custom/      protected organization knowledge
knowledge/references/  managed curated source and benchmark structure
knowledge/patterns/    managed abstract visual-pattern library
```

## Safety and product boundaries

- Every externally meaningful claim must cite evidence IDs.
- `HYPOTHESIS` is never silently promoted to fact.
- Competitor patterns are inputs to reasoning, not templates to copy.
- Research records a reusable principle and a copying risk.
- Tier A studios are seeds, not the whole search; project research must extend into relevant Tier B–D sources.
- Generated Figma frames are production wireframes, not final art.
- Client inputs and generated artifacts are ignored by default to reduce accidental publishing.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the data flow and [`docs/ONBOARDING.md`](docs/ONBOARDING.md) for the first real project.

For lifecycle management, begin with [`START_HERE.md`](START_HERE.md). SemVer-tagged GitHub Releases are installed with `./scd update`; a verified backup and rollback point are created first.
