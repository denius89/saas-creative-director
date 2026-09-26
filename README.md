# SaaS Creative Director / Креативный директор для SaaS

Система креативного препродакшена для SaaS-видео с опорой на проверяемые источники. Она превращает бриф, материалы продукта, исследование рынка и референсы в согласованную стратегию, нарратив, storyboard и редактируемые wireframes в Figma.

Русский — язык по умолчанию для общения и пользовательских материалов. Английская терминология сохранена там, где она привычна в индустрии.

It deliberately does **not** generate a final video. The system removes repetitive research and production planning while leaving interpretation, taste, final illustration, and motion craft to people.

## Что входит в V0.6

- one deterministic project orchestrator with three human approval gates;
- a claim/evidence model that separates confirmed facts, supported interpretations, and hypotheses;
- ten composable Claude Skills for intake through production review;
- schemas and validation for every handoff;
- competitor and reference intelligence structures;
- strategy, narrative, visual direction, and storyboard contracts;
- a Figma import manifest plus a small plugin scaffold for native, editable frames;
- an end-to-end example, quality rubric, and automated tests.
- русскоязычный сценарий запуска без Python, терминала, npm и ручного редактирования JSON;
- готовый Figma-плагин, который не нужно собирать самостоятельно.

## Самый простой запуск

Пользователю не нужны Python, терминал или программирование:

1. Скачать репозиторий как ZIP.
2. Открыть распакованную папку в Claude Code.
3. Перетащить материалы клиента в `INBOX`.
4. Написать: `Начни новый проект. Материалы в INBOX. Веди меня по шагам на русском языке.`

Подробная нетехническая инструкция: [`START_HERE.md`](START_HERE.md). Готовый текст для знакомого: [`docs/QUICK_TEST_FOR_FRIEND.md`](docs/QUICK_TEST_FOR_FRIEND.md).

Для разработчиков и автоматических проверок CLI остаётся доступным как необязательный слой:

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
