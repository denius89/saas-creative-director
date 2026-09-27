# Token economics / Claude credits review — 2026-09-27

Research/planning only. No account inspection, billing changes or product implementation performed. Main UX remains Claude Desktop → Code → Local; no user-operated Python/terminal requirement.

## Confirmed repository gap

`core/src/saas_creative_director/orchestrator.py` is a stage router, not an LLM execution engine. `config/local.example.json` contains no spending/context/retry policy. Existing Motion Intelligence PLAN has derived-index cache but no usage architecture. `CLAUDE.md` requires reading whole evidence/source artifacts for claims; unrestricted growth here will inflate context. Main orchestrator initially reads relevant INBOX/custom knowledge but relevance selection is underspecified.

A skill cannot guarantee a dollar or token ceiling. Adding `max_tokens: 10000` to arbitrary skill frontmatter does not create enforcement. The cheapest reliable MVP is structured local artifacts + bounded on-demand reads + deterministic operations; hard provider controls belong to a separately implemented runner/provider or account settings.

## Official billing facts, with scope

1. **Included subscription usage:** Pro/Max usage within allowance is not an API invoice. Claude Code's displayed session dollar total is locally computed from token counts/prices, not the authoritative bill; Claude Console is authoritative for API billing. `/usage` distinguishes plan limits from session estimates. Do not convert a token estimate into “X% of your Max credits.” The provider's allowance formula is not established by these docs. [Claude Code costs](https://code.claude.com/docs/en/costs).
2. **Additional subscription usage credits** (formerly described as extra usage): Pro/Max can enable pay-as-you-go continuation beyond included usage, funded separately and charged at standard API rates. Controls in Claude Settings → Usage include a monthly spending limit, prepaid funds, and optional auto-reload. Auto-reload is a purchase trigger, not a per-project budget. An enabled continuation policy is not something our skill should silently turn on. [Paid-plan usage credits](https://support.claude.com/en/articles/12429409-manage-usage-credits-for-paid-claude-plans).
3. **Console/API credits:** Most Console organizations prepay; invoicing arrangements also exist. Credits pay for API/Playground/Claude Code using that Console account. API balance exhaustion stops access; optional auto-reload buys credits. A successful request may still be charged if the client disconnects/times out, so retry is not automatically free. [API billing](https://support.claude.com/en/articles/8977456-how-do-i-pay-for-my-claude-api-usage). A Claude subscription does not itself include API/Console access. [Separate subscription/API billing](https://support.claude.com/en/articles/9876003-i-have-a-paid-claude-subscription-pro-max-team-or-enterprise-plans-why-do-i-have-to-pay-separately-to-use-the-claude-api-and-console).
4. **Authentication matters:** Claude Code docs warn that an `ANTHROPIC_API_KEY` environment variable takes priority over subscription authentication, causing API charges even when signed into Claude. `/status` reports the active authentication mode. Our diagnostic should report only presence/mode, never display a key. [Auth/billing choice](https://support.claude.com/en/articles/12304248-manage-api-key-environment-variables-in-claude-code).
5. **Desktop specifics:** Code's usage ring exposes context and plan usage. Local runs tools on the machine but sends model context to the configured provider; “Local” does not mean local inference or free inference. Desktop environment inheritance differs from terminal; verify active configuration, do not assume the shell defines Desktop billing. [Desktop docs](https://code.claude.com/docs/en/desktop).
6. **Hard limits:** `--max-budget-usd` and `--max-turns` are print-mode controls, not promises available to an ordinary interactive Desktop skill. The dollar cap includes subagents but resumed runs do not count prior runs' restored totals. Persistent project aggregation therefore requires our own ledger. Version-detect controls before using them. [CLI reference](https://code.claude.com/docs/en/cli-reference).
7. **Subagents:** each has its own context; preloaded skills inject their full body. `maxTurns` is a genuine supported subagent field, and partial completion can be resumed. Returning only a compact result reduces parent-context size; it does not erase subagent consumption. [Subagent docs](https://code.claude.com/docs/en/sub-agents).

Do not reuse this research task's parallel research pattern as the product's default runtime. Default remains one orchestrator. Do not purchase credits, enable auto-reload, change authentication, or claim user balances are known.

## Proposed inexpensive default profile (design hypotheses, to calibrate)

Separate three cost pools: initial shared library curation; one client project's production; software development/evals. Do not rebuild the 48-scene reference library per client.

| Stage | Selected context target excluding host overhead | Work bound |
|---|---:|---|
| Intake / product truth | 8–12k text tokens | one extraction pass, one targeted gap pass |
| Competitor research | 8–12k | 3 relevant competitors, max 2 source pages each initially |
| Strategy | 6–10k | 2 short options; expand chosen direction |
| Reference retrieval | 4–8k | local shortlist first; max 3 candidates/scene; no-match allowed |
| Narrative + motion direction | 8–12k | 2 rough directions, only selected one detailed |
| Storyboard | 8–16k | 2–3 scenes per batch; shared continuity summary |
| Visual QA | 4–8k text + budgeted images | contact sheet, inspect suspect crops; one correction pass |
| Figma / handoff | 4–8k | deterministic manifest; write changed scenes; bounded readback |

These are pack targets, not provider context-window limits. Images, tool schemas, conversation history and model-specific tokenization add overhead. Source text exceeding pack bounds is not silently truncated: selector preserves required claims/evidence spans, then reports omitted sections and a safe follow-up path. Missing critical proof remains unresolved.

Default loop limits: no automatic subagents; at most one directed retrieval expansion per scene group; max two tool retries for transient failures with backoff; at most one content-repair pass per stage; max two Figma QA repair cycles after initial import. Then save a checkpoint and identify the specific unresolved issue. Do not stop mid-write; finish/rollback current bounded mutation safely. Respect explicitly expanded scope without endlessly reasking.

Avoid hardcoding a provider model into skills. Configure roles `extraction`, `creative`, `visual_review`, `escalation`; choose lowest-cost measured quality-passing option. Stronger reasoning only for unresolved creative/strategic issues. No automatic expensive model escalation. Development on GPT-5.6 is separate from the eventual user's Claude runtime.

## Context and cache architecture

Proposed deterministic `context-pack` builder takes stage, project revision and selected scene IDs. It emits a manifest of exact artifact IDs/hashes, evidence excerpts and open questions. Suggested persistent resume capsule ≤2k tokens: stage, locked decisions, gate revisions, next actions, pointers, unresolved risks. Full raw sources and screenshots remain on disk; they are selected, not replayed on every step. Human-visible deliverables can be detailed without repeating all their content in every model response.

Keep three separate mechanisms:

- **Provider prompt cache:** repeated identical prefix, controlled by host/provider. API cache uses exact prefix match; stable instructions first, changing scene/task data last. Cache writes cost more than normal input; hits discount input and do not eliminate output cost. TTL support, minimum cache size and multipliers vary by model/provider; never promise a universal 90% project saving. [Prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching).
- **Local artifact cache:** immutable extracted evidence, annotations and retrieval results keyed by input hashes + schema/skill/index versions + relevant settings + privacy scope. No model call when a valid deterministic result already exists.
- **Stage checkpoints:** approved artifacts and provenance survive host compaction/session restart. Resume loads selected artifacts rather than the original long chat.

Invalidate only affected descendants. New source revision invalidates its extracted evidence, affected claims and dependent scenes; pattern recipe update invalidates the mapped scenes; price update invalidates cost estimate only; token palette update affects layout/readback, not competitor research. Pin corpus/recipe versions per project. Cache keys include project/tenant scope for client material. Public approved reference data may be shared; client extractions may not. Cache invalidation must not erase review history.

## Usage records and enforcement levels

Suggested records: `project_id`, `run_id`, `stage`, `scene_ids`, `attempt`, `host`, `provider`, `model`, `billing_mode`, `usage_origin`, `input_uncached`, `cache_write_5m`, `cache_write_1h`, `cache_read`, `output`, `tool_calls`, `image_count`, `elapsed_ms`, `price_snapshot_id`, `estimated_usd`, `metered_usd_if_available`, `unattributed_usage`, `coverage`. Unknown values are null, never zero. Distinguish provider-reported counts, host-reported estimates, heuristic pack estimates. Avoid logging prompts, private source content, tool args, API keys or screenshots in the usage ledger. Official OTel supports metrics with content logging off. [Monitoring](https://code.claude.com/docs/en/monitoring-usage).

Interactive Desktop MVP: advisory stage quotas and loop caps, visible checkpoint status, optional supported usage import; no fabricated exact bill or live remaining credit balance. Host/account spending controls remain outside skill authority.

Optional future managed runner: atomic persistent project ledger across restarts, reserve maximum estimated next-call cost, enforce turn/output/tool budgets, reconcile actual usage, and refuse a new chargeable call when reservation cannot fit. Unknown usage after timeout remains reserved until reconciled. Concurrent calls reserve before launch. Host cap may overshoot by an in-flight request; do not advertise invoice-perfect control. Account spend limit is an outer backstop. This runner must not become a requirement for nontechnical Desktop MVP use.

## Hypothetical API scenarios, not measured project quotes

For a transparent stable example use Claude Sonnet 4.6 official rates retrieved 2026-09-27: input $3/M, output $15/M, 5-minute cache write $3.75/M, cache read $0.30/M. [Pricing](https://platform.claude.com/docs/en/about-claude/pricing). This is an illustration, not a recommendation that it is cheapest/current-best.

`USD = (uncached*3 + write5m*3.75 + read*0.30 + output*15)/1e6 + separately metered tools`

| Hypothetical workflow | Uncached / cache write / cache read / output | Model-only estimate |
|---|---|---:|
| Bounded project with existing corpus | 100k / 40k / 400k / 25k | $0.945 |
| One targeted scene revision | 20k / 0 / 100k / 5k | $0.165 |
| Repeated broad uncached context | 1,000k / 0 / 0 / 80k | $4.20 |
| Same latter workload entirely on example Opus 4.6 $5/$25 | 1,000k / 0 / 0 / 80k | $7.00 |

Scenarios assume all provider-billed image/reasoning/tool-token overhead is already included in totals; real overhead may be much larger. Exclude web/tool fees, taxes, discounts, residency premiums, Figma plan costs, library curation and human review. Not a measured efficiency claim, not “number of projects on Max.” No conversion to subscription credits. Ratios will change with caching/model/tokenizer and actual project work. The user needs a pilot measurement before a commercial per-project price promise.

## Exact proposed file deltas

- Update `CLAUDE.md`: stage-specific selection rather than repeatedly loading complete source/evidence registries; progress capsule; no automatic agent fan-out; billing mode unknown unless verified.
- Update `core/skills/saas-creative-director/SKILL.md`: economic-default routing; reuse/affected-stage restart; bounded repair; cost-state disclosure in natural language; never alter billing.
- Update reference, storyboard and QA skills: local-first retrieval limits, scene batching, image selection, explicit no-match / unresolved result.
- Extend `config/local.example.json` with advisory profile, stage pack limits, retries/repair, retrieval top-k, image limits, default billing mode unknown, nullable dollar target; retain local overrides/update safety.
- New `core/schemas/context-pack.schema.json`, `core/schemas/usage-event.schema.json`, `core/schemas/execution-policy.schema.json`; annotate advisory vs enforced fields explicitly.
- New `core/src/saas_creative_director/context.py`, `cache.py`, `usage.py` for deterministic pack selection, hash-based artifact cache and optional metric ingestion; extend `cli.py` with callable helpers but no user CLI requirement.
- New `docs/USAGE_AND_BILLING.md`, `docs/CONTEXT_AND_CACHE.md`, Russian usage guide: Desktop usage ring, plan credits vs API, auth diagnostic without secrets, advisory limits, optional developer runner.
- Generated runtime files: `projects/<id>/artifacts/context-packs/`, `projects/<id>/reviews/usage-summary.json`, `.scd/cache/<scope>/`; configurable TTL/deletion, ignored private data.
- Tests `test_context.py`, `test_cache.py`, `test_usage.py`: preservation of evidence links under pack limits, isolation, invalidation, unknown usage semantics, deduplicated events. Future runner tests for concurrent reservations, restart persistence, timeout spend uncertainty.
- New `evals/economics/`: fixed 12-brief pilot; aggregate actual request input including cache reads, output, image/tool calls, retry causes, latency, and accepted deliverable rate. Compare quality at same scope.

## Acceptance and priorities

P0: state truthful accounting scope and default workflow bounds; Desktop docs and auth/billing-mode checklist (do not inspect secret values); no billing mutation.
P1: pack builder, checkpoint, deterministic retrieval/rendering, local cache and delta invalidation. 12-brief pilot records count provenance/coverage and visual quality jointly.
P2: supported host usage ingestion, dashboard summary in Russian, economics regression. A reasonable hypothesis target is ≥30% less uncached input versus existing pipeline on matched briefs with no significant quality degradation; label as target, not established saving.
Post-MVP: dedicated provider runner/gateway caps only if needed. Do not build billing SaaS or a giant telemetry stack before proving pre-production value.

## Confirmed user setup: Pro/Max subscription (parent update)

Make subscription mode primary and record `billing_mode: subscription` only as user-reported until host verifies it. No API key, Console account, runner or prepaid API purchase is required for this MVP. API examples above are secondary explanatory estimates only. Current official help article calls additional paid allowance **Usage credits**; older materials may call it **Extra usage**. Explain both labels for recognition. Included subscription allowance remains distinct. Product default policy: use included allowance; no automatic opt-in to paid continuation, no auto-reload change. If allowance is exhausted and paid continuation is not enabled/authorized, save checkpoint and resume after provider reset. Do not imply our plugin can enforce the account setting across other tasks or devices. User can see actual plan state via Desktop usage ring and Settings → Usage; do not fabricate percentage from our ledger.
