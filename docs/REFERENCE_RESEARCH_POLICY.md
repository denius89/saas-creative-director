# Reference Research Policy

## Objective

Reference research must find the strongest ways to visually explain a specific value story or product mechanism. “Beautiful SaaS videos” is not a research question. Start from the approved strategy: what must the viewer understand, believe, or notice, and what causal mechanism must be made visible?

## Source tiers

1. **Tier A — curated benchmarks.** Start with the maintained studios in `knowledge/references/curated-sources.yaml`. They establish a quality bar and useful search vocabulary; they are never sufficient alone.
2. **Tier B — direct competitors.** Study how the client's category frames the same buyer, pain, proof, and product mechanism. Store commercial/message observations in competitor intelligence; store scene mechanics here only when visually relevant.
3. **Tier C — category and adjacent-category references.** Find strong work with similar information density, buying context, or product interaction.
4. **Tier D — cross-industry exploration.** Find a matching visual mechanism even when the product category differs: convergence, comparison, transformation, orchestration, detection, simulation, or cause/result.

A normal research pass samples A plus at least two other tiers. Explain any exception.

## Reference library versus pattern library

`reference-library` records concrete works: canonical URL, studio, project, scene timestamps/screenshots, metadata, observed mechanics, inspection method/date, and confidence. It may say “unknown.”

`pattern-library` records abstract mechanisms: the communication problem, how the pattern works, when it helps, when it fails, provenance reference IDs, confidence, and a non-copy rule. A named visual identity, color system, illustration style, or unique shot sequence is not a reusable pattern.

## Analysis protocol

1. State the target value story/product mechanism in one sentence.
2. Build candidates across tiers and record provenance before analysis.
3. Watch the work, not just its thumbnail or portfolio copy. Sample opening, mechanism reveal, proof, and ending; use additional timestamps where the visual logic changes.
4. Record industry, project/video type, narrative structure, composition, hierarchy/focal point, UI and illustration use, motion, transitions, pacing, text density, strengths, weaknesses, reusable principles, and risks.
5. Distinguish observation from interpretation. Do not infer motion, pacing, or scene order from still imagery.
6. Rank relevance to the communication problem separately from craft quality.
7. Abstract principles only after identifying what information relationship they clarify.

## Provenance

Every record needs its canonical work URL, studio/source ID, inspection date, inspection method (`video`, `browser_visual`, `page_metadata`, or `screenshot`), and confidence. Timestamp annotations use `MM:SS–MM:SS`. Screenshots record the source URL and timestamp; do not rehost copyrighted frames in the repository unless permission allows it.

If a page changes or disappears, preserve the last known canonical URL and mark availability. Do not invent missing metadata.

## Inaccessible and dynamic sites

Try the canonical page first. If ordinary retrieval fails (for example, a 403 or script-only portfolio), use visual browser inspection. Read the visible page, open the work from the site's own navigation, and record `browser_visual` as the method. Never bypass a paywall, login, CAPTCHA, robots restriction, or browser security warning. If the video still cannot be inspected, retain metadata only, set analysis fields to `null`, and mark the item `queued` or `blocked` with low confidence.

## Inspiration versus copying

Allowed abstraction describes relationships: “keep action and result visible together,” “preserve an object across a state transition,” or “use progressive disclosure for a dense workflow.”

Do not copy a studio's colors, illustration language, proprietary UI treatment, character design, signature transition, audio identity, exact wording, or sequence of scenes. Do not use “make it like Studio X” as direction. Combine principles from multiple sources and adapt them to the client's evidence, brand, and product mechanics.

## Competitor research boundary

Competitor intelligence asks what the market claims, proves, omits, and positions. Visual reference research asks how a communication problem is solved on screen. A competitor can appear in both datasets, but the observations and conclusions remain separate. Competitor messaging is never evidence about the client's users, and a competitor's visual style is never a production brief.

## Acceptance criteria

- Tier A is represented but not dominant by default.
- At least one candidate directly matches the product mechanism.
- Every analyzed scene has provenance and an honest confidence level.
- Concrete references and abstract patterns are separate artifacts.
- Reusable principles explain why they work and when not to use them.
- Non-copy risks are explicit.

