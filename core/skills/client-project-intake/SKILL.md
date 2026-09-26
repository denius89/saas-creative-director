---
name: client-project-intake
description: Normalize a new SaaS video client's brief, website, docs, screenshots, Figma, and optional code into a source registry, evidence base, project context, and material open questions. Use at the start of a client project or when major new inputs arrive.
---

# Client project intake

Read `CLAUDE.md`, `project.json`, and every supplied input. Create or update:

- `artifacts/source-registry.json` using `core/schemas/source-registry.schema.json`;
- `artifacts/evidence.json` using `core/schemas/evidence.schema.json`;
- `artifacts/project-context.md` with business goal, audience, channel, constraints, deliverables, and known approvals;
- `artifacts/open-questions.md` with only questions that could change strategy or make a claim unsafe.

Register a source before citing it. Split compound claims. A direct client/product source can support `CONFIRMED`; multiple independent indirect signals can support `SUPPORTED`; interpretation stays `HYPOTHESIS`.

Do not infer customer pains merely from features. Note conflicts between sources instead of resolving them silently. Finish by summarizing source coverage, critical gaps, and whether product intelligence can begin.
