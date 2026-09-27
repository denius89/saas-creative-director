# Ledgerly example project

Ledgerly is a fictional SaaS product used to demonstrate the complete pre-production workflow without client data.

## Follow the decisions

1. [Product intelligence](artifacts/product-intelligence.json) establishes the product, audience, JTBD, pains, value, objections, and evidence boundaries.
2. [Competitor intelligence](artifacts/competitor-intelligence.json) stays separate from visual-reference research.
3. [Video strategy](artifacts/video-strategy.json) defines the job of the video and the approved strategic route.
4. [Reference library](artifacts/reference-library.json) and [pattern library](artifacts/pattern-library.json) record provenance and reusable visual principles.
5. [Narrative](artifacts/narrative.json), [motion direction](artifacts/motion-direction.json), and [visual direction](artifacts/visual-direction.json) define the approved creative treatment.
6. [Storyboard](artifacts/storyboard.json) specifies timing, scene purpose, states, events, transitions, objects, evidence, and creative freedom.
7. [Figma manifest](artifacts/figma-manifest.json) is the deterministic import contract for native editable wireframes.
8. [Visual QA](reviews/visual-qa.json) and [production review](reviews/production-review.md) show the handoff checks and remaining limitations.

## Validate the example

```bash
./scd validate examples/ledgerly
./scd status examples/ledgerly
```

The checked-in Figma manifest is validated automatically. It is not evidence that the bundled importer has passed the current live-canvas checklist; that separate verification is tracked in [docs/FIGMA_LIVE_VERIFICATION.md](../../docs/FIGMA_LIVE_VERIFICATION.md).
