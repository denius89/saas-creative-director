# Motion Intelligence: retrieval, libraries, evidence, and evaluation research

Research date: 2026-09-27. These are implementation proposals unless explicitly described as repository observations or published research. No implementation files were changed.

## Repository-grounded diagnosis

The repository is already v0.6.0, with useful starting structures: `core/schemas/reference-library.schema.json`, `pattern-library.schema.json`, `storyboard.schema.json`, `source-registry.schema.json`, `evidence.schema.json`; `knowledge/patterns/{composition,motion,narrative,transitions}`; `core/skills/creative-reference-research`, `visual-direction`, `storyboard-composition`, and `production-review`. Do not recreate these as competing systems.

The strongest policy already exists in `docs/REFERENCE_RESEARCH_POLICY.md`: mechanism-first search; competitor intelligence distinct from reference analysis; no motion inference from stills; concrete works distinct from abstract principles; unknown allowed; no copying expression. Preserve and enforce it.

Actual gaps:

- Reference schema is mainly work-level. `screenshots_timestamps` is only an unconstrained optional object array; there is no enforced scene/interval identity, observed temporal sequence, adjacency, or field-level evidence.
- Pattern schema has problem/mechanism/use/avoid/provenance/non-copy fields, but no parameterized composition, temporal invariants, editable Figma recipe, or version/freshness.
- Storyboard motion is an array of strings, transitions a string, references optional. A valid storyboard can be syntactically complete without a concrete observed motion reference or executable state change.
- `evals/reference-research/benchmark-index.yaml` lists 24 works, evenly across four Tier A studios. `annotations.json` contains eight provisional annotations, all `gold: false`, with many unobserved motion fields. Existing metadata labels occasionally say “likely” or “expected” inside motion fields: migrate these to explicit hypotheses, not observed pattern tags.
- `evals/run_eval.py` checks presence/counts/timing, including benchmark count 20–30 and at least eight manual annotations. It does not test scene retrieval, modernity, comparative preference, or production editability. `all(...)` can also vacuously pass empty reference arrays; meaningful checks require minimum coverage.
- Existing rubric combines eight dimensions into 14/16. A higher overall score can conceal bad composition or handoff. Add independent quality floors and hard evidence/editability gates.

## Technical evidence and its limits

1. QVHighlights treats retrieval as query-to-relevant temporal moments, with separate saliency labels, rather than retrieving only a whole video. That is the right conceptual unit here. Its data are predominantly vlog/news, not product motion: neither its trained model nor benchmark performance establishes SaaS retrieval quality. Use the distinction between relevance and saliency, not the dataset as a plug-in gold standard. [QVHighlights, Lei et al.](https://arxiv.org/abs/2107.09609)
2. CLIP connects natural-language concepts to images and documents limitations in abstract/systematic tasks. Image similarity may find palettes or familiar objects; it does not establish why an interface transition communicates a product mechanism. Treat multimodal embeddings as candidate discovery, not an arbiter of causal or temporal relevance. [CLIP research](https://openai.com/index/clip/)
3. Human evaluation needs precisely defined dimensions and a documented protocol to support comparison; diverse labels alone are unreliable. Transfer this methodological lesson to design evals, while acknowledging that the source studies NLG rather than motion design. [Howcroft et al. 2020](https://aclanthology.org/2020.inlg-1.23/), [Belz et al. 2020](https://aclanthology.org/2020.inlg-1.24/)
4. LLM judges exhibit position, verbosity, and self-enhancement biases. A model that generated a storyboard should not be its sole release judge. This is research on text judgments; extension to visual judging is a precaution and a hypothesis to calibrate, not an established SaaS-modernity metric. [Zheng et al.](https://arxiv.org/abs/2306.05685)
5. W3C PROV distinguishes entities, generating activities, responsible agents, and derivation. Adopt the minimal lineage concept as JSON references; full RDF/ontology infrastructure is unnecessary for this MVP. [PROV-DM](https://www.w3.org/TR/prov-dm/)

## Minimum viable corpus and taxonomy

Recommended first release: retain the existing 24 candidate works; fully inspect 12 accessible works and annotate 48–72 useful scene intervals; represent all four Tier A studios where accessible, plus at least four non-seed works. Never fill a quota with fabricated timestamps. If access fails, keep metadata-only and substitute another inspectable work. Build 12–16 abstract patterns and 10–12 conditional anti-patterns. These are planning targets, not empirical optimums.

Two libraries with different jobs:

- Reference library: concrete observed work/scene, source, dates, observation, rights, inspector and uncertainty. Source of evidence.
- Pattern library: derived solution to a communication problem, conditions, variables and constraints. Source of reusable design decisions.

Taxonomy facets should be independent, controlled vocabularies with an `other` plus explanation option:

| Facet | Initial vocabulary/examples |
|---|---|
| Communication job | reveal capability, show mechanism, compare alternatives, prove outcome, establish scope, orient workflow, ask action |
| Mechanism | transform, route, aggregate, filter, detect, coordinate, synchronize, retrieve, compare, generate, approve |
| Input/output relation | one-to-one, one-to-many, many-to-one, many-to-many, before/after, branching |
| UI fidelity | actual captured, faithful reconstruction, simplified truthful, conceptual; unknown |
| Composition | persistent cause/result, detail/context, shared comparison baseline, progressive disclosure, spatial pipeline, nested scope, focused work surface |
| Attention | isolate, contrast, pointer/action, reveal, focus transfer; dominant and secondary targets |
| Motion function | state change, object continuity, causality, hierarchy, feedback, temporal compression, spatial orientation |
| Motion primitive | translate, scale, crop/reframe, opacity, mask reveal, rearrange, number change, path/connector; combinations allowed |
| Transition relation | same object/new state, detail-to-context, consequence, comparison, scope change, chapter reset |
| Rhythm | held proof, burst/hold, progressive step, sustained flow; actual durations where observed |
| Density | visible semantic units, focal regions, copy words; derive low/medium/high only with documented rules |
| Constraints | duration, aspect ratio, mobile readability, actual UI available, allowed simplification, production budget |

Do not encode “modern = gradients/3D/bento/kinetic type.” Those are stylistic attributes with context-dependent usefulness. Maintain brand style as separate project input. Pattern tags should remain useful after fashion changes.

## Data model / schemas

Extend existing schemas with `schema_version`; retain stable IDs, migrations and legacy-read support.

`reference-library` work additions: `studio`, `canonical_work_url`, `media_locator`, `published_at` nullable, `publication_date_basis`, `first_seen_at`, `last_access_checked_at`, `last_visual_reviewed_at`, `availability`, `rights:{linking,capture_allowed,redistribution_allowed,basis}`, `content_fingerprint` optional and only for legally held assets, `source_version`, `scene_ids`. A crawl timestamp is not a release date or visual inspection date. Tier A is a source-priority designation, not proof of quality or contemporary date.

New `reference-scenes.schema.json`: `scene_id`, `reference_id`, `start_ms`, `end_ms`, `keyframes:[{timestamp_ms,locator,rights}]`, `observations:[{field,value,evidence_level,inspection_method,observation_locator,reviewer_id,observed_at}]`, `communication_job`, `mechanism_tags`, `composition_tags`, `ui_fidelity`, `state_before`, `trigger`, `state_after`, `persistent_objects`, `attention_path`, `transition_in`, `transition_out`, `prev_scene_id`, `next_scene_id`, `limitations`, `approved_for_retrieval`. Require video/timed sequence inspection for motion/transition/duration claims. A still may support composition only.

Evidence uses the existing CONFIRMED/SUPPORTED/HYPOTHESIS vocabulary; keep reviewer confidence and benchmark status in separate fields. “Confirmed” means observation in an inspected artifact, not proof it improves business outcomes. Proposed pattern maturity enum: experimental/supported/established; existing `benchmark` confidence should migrate to separate `benchmark_status`, because benchmark membership is not confidence.

`pattern-library` additions: `pattern_version`, `intent`, `required_inputs`, `preconditions`, `communication_invariants`, `composition_parameters`, `motion_contract:{before,trigger,after,continuity,timing_constraints}`, `example_scene_ids`, `counterexample_scene_ids`, `evidence_level`, `maturity`, `last_reviewed_at`, `review_due_at`, `supersedes`, `figma_recipe_id`, `non_copy_boundaries`. Promote to supported from multiple independent observed uses (proposal: two distinct works; record studio diversity), or keep single-source pattern experimental. Keep foundational design principles distinguishable from “observed current practice” trend claims.

New `anti-patterns.schema.json`: `id`, `symptom`, `failure_mechanism`, `applies_when`, `exceptions`, `detection_method`, `severity`, `repair_options`, `example_scene_ids`, `evidence_level`, `reviewed_at`. Anti-patterns are conditional failure tests, never a universal blacklist of visual devices.

New `scene-retrieval.schema.json`: `query_id`, `project_scene_id`, `knowledge_snapshot`, `query:{communication_job,mechanism,ui_fidelity,information_relationship,duration,aspect_ratio,brand_constraints}`, `hard_filters`, `candidates:[{scene_id,relevance_reasons,dimensions,inspection_eligibility,limitations}]`, `selected`, `rejected`, `abstention_reason`, `reviewer`. Log the reason for selection, not only a score.

New `visual-qa.schema.json`: artifact/version, rendered evidence paths, scene findings with severity/criterion/observed evidence/fix, sequence findings, factual fidelity, accessibility/readability, anti-pattern exceptions, editability check results, reviewer, status, blockers. Inspection of JSON is not visual QA.

Extend storyboard per scene: `pattern_ids` + versions, `reference_scene_ids`, `reference_application` explaining abstracted principle, `ui_asset_ids`, `ui_fidelity`, `states` (minimum key states appropriate to mechanism), `motion_contract`, `continuity_objects`, `figma_recipe_id`, `qa_findings`. Allow deliberate reference-free invention with explicit hypothesis and human decision; do not require irrelevant reference padding.

## Retrieval workflow: no vector database needed initially

1. Translate scene purpose into a structured query: viewer must understand X because action Y causes state Z. Do not search only “fintech beautiful video.”
2. Filter by inspectability/evidence requirements, rights/access, mechanism-compatible constraints and unsupported production needs. Unknown publication date does not make timeless principles unusable; it makes recency claims unavailable.
3. Search tags and short semantic descriptions in local JSON/SQLite FTS. Score mechanism fit first, then information relation, UI fidelity, timing/aspect feasibility, attention/composition fit. Craft and publication recency are separate dimensions, not substitutes for relevance.
4. Rerank a small candidate set with an explicit rubric and evidence. Return three plausible intervals and reasons; show one useful counterexample. Prefer diversity across sources without forcing irrelevant choices.
5. Inspect selected interval and adjacent shots before deriving transition grammar. State reuse boundary. Return `no_suitable_match` when appropriate, triggering research or explicit experimental design.
6. Project locks selected source/pattern versions; global corpus updates do not silently change approved work.

Optional later: text embeddings over reviewed scene descriptions; image embeddings for composition candidate recall; temporal video models only if manual segmentation is demonstrably the bottleneck. Benchmark each against tag/lexical baseline. Never introduce vector infra merely because the term RAG sounds relevant.

## Anti-pattern candidates (proposals to test with designers)

- Same centered card composition repeated despite changing communication jobs.
- Floating cards that obscure which action causes which result.
- Decorative 3D/orbits without information or orientation purpose.
- Continuous motion with no readable hold on proof/product outcome.
- Full-dashboard screenshots scaled below meaningful readability.
- Typography moving independently of narrative emphasis, competing with product action.
- Generic abstract “AI glow” standing in for an unshown product mechanism.
- Impossible invented UI states or connectors implying nonexistent automation.
- Every cut is a fade, or every transition is spectacular, without semantic continuity.
- All hierarchy equal: simultaneous reveal of headline, UI, proof and decorative objects.
- Shot-level prettiness with no stable object identity across sequence.
- Trend mimicry incompatible with the client's audience, brand or evidence.

For each, document legitimate exceptions (centered hero can be excellent for one claim; 3D can explain spatial relationships; fades can deliberately separate chapters). “Looks AI” is too vague to be a detector.

## Evaluation design

Separate four tests: ingestion honesty, retrieval usefulness, resulting creative quality, production usability.

Ingestion tests: timestamps valid; IDs resolve; motion labels cannot derive from metadata-only/still inspection; publication dates have evidence; all selected claims have sources; inaccessible work retained as such. Existing eight provisional labels become uncertainty regression fixtures, not gold creative examples.

Reference benchmark: use 24 candidate works as review queue; first gold cohort 12 fully inspected works with two independent reviewers and adjudicated scene annotations. Keep studio/work identity disjoint between tuning and held-out tests, to avoid near-duplicate scenes leaking. Preserve an archive fixed test set and a rolling contemporary set. Dated but excellent and current but generic controls should prevent conflating recency with quality.

Retrieval benchmark proposal: 40 scene-intent queries across 8 mechanism families, with 0–3 relevance judgments and hard negatives (matching colors/category but wrong mechanism). Include no-match queries, inaccessible-only and still-only cases. Report nDCG@5, Recall@5 over adjudicated relevant scenes, eligible-evidence rate, source diversity, no-match precision/recall, and per-family results. With incomplete relevance judgments, report pooled-judgment limitation rather than pretending exhaustive recall. Initial target: at least one strongly relevant eligible result in top 3 for 80% of answerable queries; 100% provenance validity; zero metadata-only motion assertions. Targets are product acceptance proposals to calibrate, not scientific constants.

Blind A/B: freeze same approved brief/product evidence/script/model/settings/budget and compare baseline vs full Motion Intelligence. Render both at equal fidelity/size; strip labels, randomize left/right, balance order. Collect scene preference and full-sequence preference separately. Have at least three independent reviewers (motion designer, design/art director, animator) across a 12-brief pilot. Include ties and “insufficient evidence”; require dimension-specific reasons. Raters do not see pipeline identity or studio inspiration until after rating. Do not change script at the same time, or improvement cannot be attributed to Motion Intelligence.

Dimensions 1–5 with anchors: (a) mechanism clarity, (b) composition/hierarchy, (c) contemporary suitability for audience/context, (d) sequence/continuity and motion intent, (e) brand distinctiveness without imitation, (f) feasible/editable production handoff. Judge modernity as context-appropriate current visual communication, not publication-date guessing. QA can assess motion *intent* from state boards; actual smoothness/feel requires an animatic and is outside static-wireframe claims.

Report preference rates including ties, paired differences, confidence intervals clustered by brief, and inter-rater agreement (ordinal Krippendorff alpha or weighted kappa where appropriate). Small pilot results are directional; do not call 36 correlated votes a large independent sample. Proposed go/no-go: no fidelity/editability blockers, mean clarity and usability do not decline, at least 8 of 12 brief-level majority wins in pilot, and qualitative failure patterns resolved. A later 30+ brief confirmation cohort with prespecified analysis can support a stronger effectiveness claim. If confidence interval is too wide, report inconclusive rather than moving thresholds.

Ablation after pilot: same set with (1) motion director only, (2) + scene retrieval, (3) + visual QA. This identifies whether expensive parts actually help. LLM/VLM checks are advisory, calibrated against expert labels, with swapped-order consistency tests; cannot independently approve release.

Production task test: ask an animator to replace a product screen, change headline, alter one scene state, find transition/asset/evidence notes, and identify locked/free decisions. Record completion, time, questions and rework. Confirm native editable text/objects and sensible grouping, not merely node count. Proposed MVP test: all required edits possible without rebuilding flattened scene, no critical ambiguity in selected handoff scenes. Do not promise the storyboard is animation-ready without this handoff trial.

## Freshness and update-safe architecture

Maintain separate clocks: source available, visual observation reviewed, trend assertion reviewed, pattern last validated, package released. Monthly source/access review and quarterly pattern/trend review are pragmatic starting schedules; adapt to observed change, not claimed industry law. Re-review immediately after user feedback or broken links. “Stale” means review due, not automatically false.

Keep core schemas/skills immutable per release; distributable curated records versioned separately; private/custom knowledge and overrides preserved; projects pin `knowledge.lock.json` with IDs/versions/checksums. Derived indexes/caches rebuildable and disposable. A refresh proposes changes, runs schema/evidence/benchmark checks, produces a diff and human curation decision; never silently overwrites accepted project references. Deprecate and retain lineage instead of deleting IDs. Source deletion doesn't erase already lawful observations; mark current availability and avoid claiming fresh inspection. Document rollback of both code and knowledge snapshots.

## Concrete file work to propose next

Modify existing schemas, `core/src/saas_creative_director/{models,validation,orchestrator,workspace}.py`, the four relevant existing skills, `evals/run_eval.py`, `evals/rubric.md`, reference policy and architecture/update docs. Add `core/skills/motion-design-director/SKILL.md`, `scene-reference-retrieval/SKILL.md`, `visual-qa/SKILL.md`; `core/schemas/{reference-scenes,anti-patterns,scene-retrieval,visual-qa,motion-direction,knowledge-manifest}.schema.json`; `knowledge/current-motion/`, `knowledge/anti-patterns/`, versioned scene annotations; `evals/{scene-retrieval,visual-modernity,handoff}/` with protocol, manifests, ratings, holdout policy, reports. Add schema migration and honest legacy fixture migration. The precise upcoming semver should follow project's compatibility policy, not be guessed here.
