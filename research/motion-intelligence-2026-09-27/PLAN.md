# Motion Intelligence Layer — исследование и план MVP

> Актуализация: порядок работ и первоначальный scope уточнены в [MASTER_PLAN.md](MASTER_PLAN.md). Для разработки использовать [START_DEVELOPMENT_5_6.md](START_DEVELOPMENT_5_6.md).
Дата: 27 сентября 2026. База: локальный SaaS Creative Director 0.6.0; текущие данные и Figma manifest используют schema 0.5. Статус: проектирование, не реализованный релиз.

**Решение:** добавить Motion Intelligence как связку проверенных визуальных знаний, выбора визуального механизма, структурированной композиции и проверки результата. Одного нового prompt или каталога «модных роликов» недостаточно. Первым вертикальным срезом должен стать путь «размеченная сцена → абстрактный паттерн → состояния storyboard → нативная композиция Figma → визуальная проверка».

Продукт остаётся системой pre-production: клиентские данные → доказательная стратегия → creative direction → storyboard/composition → редактируемые Figma wireframes → handoff. Финальная анимация, иллюстрационный craft и видеорендер не входят в MVP.

## Метод и границы исследования

Восстановлены все страницы предыдущего разговора; проверены существующие skills, схемы, orchestrator, validator, renderer/importer, примеры, evals и updater. Три исследовательских направления работали параллельно: студии/визуальный язык; retrieval/данные/evals; инструменты/Figma. Это организация разового исследования, а не предлагаемая архитектура продукта.

Обозначения: **CONFIRMED** — непосредственно проверяемый факт в коде или первичном источнике; **SUPPORTED** — интерпретация с поддерживающими наблюдениями; **HYPOTHESIS** — предположение, требующее проверки. Предложения по объёму библиотеки, срокам и порогам ниже — проектные решения, не эмпирические нормы рынка.

Исследование страниц и документации не равно просмотру полного видео. Работы без подтверждённого просмотра остаются кандидатами; им нельзя присваивать наблюдённые motion/timing характеристики. Дата посещения портфолио не является датой выпуска ролика. Полный gold-корпус и blind A/B в рамках этой задачи не созданы и не проведены.

## A. Почему storyboard кажется устаревшим

### Подтверждённые ограничения реализации

| Наблюдение в 0.6.0 | Последствие | Что менять |
|---|---|---|
| `core/skills/visual-direction/SKILL.md` задаёт перечень общих требований, но не контракт выбора по доказательствам и сценам | «hero UI / split / before-after» легко становятся универсальными шаблонами | Motion direction с условиями применимости, альтернативами, происхождением и проверяемым результатом |
| В `storyboard.schema.json` motion — массив строк, transition — строка, objects почти не типизированы | Нельзя проверить, какой объект меняется, что сохраняется и как возникает результат | Состояния, события, object IDs, начальный/конечный кадр и связи сцен |
| `figma.py` переносит `composition_pattern` как метаданные, не реализует его; теряет часть семантики объектов | Правильное режиссёрское решение может не дойти до canvas | Типизированный layout manifest и библиотека компоновки |
| `figma-plugin/src/code.ts` рисует каждый нетекстовый объект прямоугольником; одинаковые fallback bounds, фиксированная позиция copy; tokens не используются | Разные механизмы превращаются в одинаковые плейсхолдеры | Нативные группы, текст, UI subcomponents, crop, hierarchy; запрет молчаливой подмены |
| Background layer не получает bounds и попадает под общие fallback dimensions | Фоновый прямоугольник не соответствует размеру сцены | Явный background contract и визуальный regression fixture |
| Повторный import создаёт новые frames | Потеря управляемой итерации с дизайнером | Стабильные ID, revision conflict policy, безопасный reimport |
| `validation.py` проверяет некоторые поля и evidence links, но не исполняет JSON Schemas, не проверяет тайминг/reference/pattern links | Наличие схем в репозитории создаёт более сильное впечатление гарантий, чем реальная проверка | Stage-aware schema + semantic validation |
| `advance` не проверяет готовность артефактов; approve не связан с revision артефактов | Старое согласование может пережить существенную переработку | Digest утверждаемого пакета, invalidation downstream |
| Evals проверяют главным образом наличие полей, количество записей и суммарный тайминг | PASS не означает качественный storyboard или пригодность для production | Retrieval benchmark, визуальные пары, тест редактирования и blind review |

Проверены исходные файлы, а не работа импортера в живом Figma. Поэтому дефекты передачи данных — CONFIRMED по коду; их вклад в конкретный отзыв «выглядит старо» — HYPOTHESIS до сравнения исходных пользовательских результатов.

### Диагноз процесса

Хороший verbal script отвечает, что сказать. Storyboard дополнительно должен решить: что зритель увидит; какой объект несёт смысл; какое изменение доказывает ценность; сколько информации видно одновременно; куда перемещается внимание; что связывает соседние планы. Пропуск этих решений вынуждает модель достраивать привычную композицию «заголовок + карточка + декоративный переход».

В проекте уже есть reference/pattern libraries и non-copy policy. Недостающее звено — переход от списка источников к **наблюдённому механизму конкретной сцены**, затем к реализуемой структуре и проверке изображения. Нельзя диагностировать всё как исключительно knowledge gap: часть разрыва находится в renderer и evals.

Отдельный риск — сравнивать нейтральный wireframe с законченным студийным роликом. MVP должен проверять современность композиционной логики, ясность UI, последовательность и rhythm intent. Он не обещает финальное ощущение premium без типографического, цветового, звукового и анимационного craft.

## B. Рекомендуемая архитектура

Один orchestrator, компонуемые skills и детерминированные операции. Отдельная модель для каждого этапа не требуется. Этот выбор согласуется с рекомендацией Anthropic начинать с простых компонуемых workflow; конкретная архитектура ниже — наше проектное решение. [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)

```text
client input → product intelligence → JTBD / pain / value
→ competitor intelligence → video strategy → [G1 strategy]
→ reference research + current-motion snapshot
→ narrative directions
→ motion-design-director + provisional scene retrieval
→ 2–3 representative composition frames → [G2 creative direction]
→ final scene-level retrieval → storyboard / states / continuity
→ visual-QA preflight → editable Figma
→ rendered readback + production review → [G3 production] → handoff
```

JTBD остаётся частью product intelligence; current-motion — знания, а не отдельный автономный агент. Reference research может возвращаться к поиску после появления scene briefs. Не фиксировать retrieval только до narrative: потребность в референсе уточняется по конкретному механизму.

### Три gates, но более содержательные

- **G1:** цель, формат, аудитория, core message, proof, scope. Одобрение стратегии открывает исследование и creative development.
- **G2:** narrative + visual grammar + 2–3 репрезентативных composition frames + motion intent + ограничения ассетов. Перенести существующий creative gate с конца одного только narrative. Человек утверждает визуальное решение, которое уже можно увидеть. Preview может быть в отдельной draft-странице Figma; это не финальная production export.
- **G3:** storyboard, rendered Figma, readback QA, asset exceptions, handoff. Нет блокирующих ошибок; final craft явно отмечен как работа человека.

Записывать `approved_by`, время, комментарий, набор artifact IDs/revisions и digest. Изменение стратегии инвалидирует G1 и downstream; смена narrative/pattern/UI mechanism — G2 и downstream; исправление подписи без смены смысла требует только локальной QA. Политику существенности оформить явно. Историческое согласование не удалять; помечать superseded. При изменениях после утверждения запросить только необходимое повторное решение.

### Семь частей Motion Intelligence

1. **Current-motion knowledge:** датированные наблюдения о конкретных выборках и контекстах; не «закон стиля 2026».
2. **Reference library:** реальные работы и проверенные временные отрезки; metadata отдельно от visual observations.
3. **Pattern library:** абстрактные решения информационных задач с условиями, вариантами и ограничениями.
4. **Anti-pattern library:** диагностические правила о несоответствии функции, а не запреты эстетики.
5. **Scene retrieval:** объяснимый поиск подходящих механизмов; допускает «подходящего референса нет».
6. **Motion-design-director:** преобразует стратегию, narrative, product truth и найденные паттерны в ограниченную визуальную грамматику.
7. **Visual QA + Figma mapping:** проверяет, что реальная композиция соответствует замыслу и остаётся редактируемой.

### Разделение исследований

Competitor intelligence хранит positioning, claims, proof, objections и market gaps. Visual reference research хранит композицию, причинность, motion и production mechanics. Один URL может использоваться в обеих системах через общий Source ID, но заключения и evidence records различны. Успешность чужого ролика не доказывает боль пользователей нашего клиента; красивый кадр не доказывает conversion uplift.

## C. Точный scope MVP и backlog

Целевой расширенный MVP: product demo, feature announcement и короткий launch/explainer; основной формат 16:9, 20–60 секунд, 6–10 сцен как тестовый диапазон, а не ограничение всех проектов. Добавить один concept-led кейс для invisible infrastructure, чтобы product-led не превратился в догму.

| В MVP | Критерий объёма / результата |
|---|---|
| Motion direction skill и расширение существующих skills | 1 orchestrator; не добавлять постоянный multi-agent runtime |
| Curated corpus | Не менее 16 просмотренных работ, 48 размеченных сцен; все четыре Tier A представлены, также минимум два источника вне Tier A |
| Качество корпуса | Минимум 12 работ с подтверждённой публикацией в 2025–2026; недатированные — отдельная evergreen/category группа; 16 сцен независимо размечены вторым человеком |
| Pattern library | 12–16 паттернов; минимум 8 composition recipes имеют рабочее отображение в Figma; новый паттерн может иметь статус experimental |
| Anti-pattern library | 10 условных проверок; обоснованный override и явное исключение |
| Retrieval | Фильтры + полнотекстовый поиск по человеческим аннотациям + объяснимое ранжирование + diversity; без обязательного vector DB |
| Storyboard | Структурированные сцены, native objects, action/result states, timing и continuity; 2–3 ключевых состояния для сцен с существенной трансформацией |
| Figma | Plugin fallback как базовый adapter; MCP adapter через capability check; editable native nodes; screenshots только как явно растровые ассеты |
| QA | Structural checks, contact sheet, transition-state strips, Figma screenshot/readback и human production review |
| Evals | 24 brief cases, 60 retrieval queries, pilot blind A/B на 12 briefs, отдельные failure fixtures |
| Update safety | Version pinning, read compatibility с 0.5, explicit migration, checksum verification, rollback rehearsal |

Числа — минимальный стартовый объём для проверки гипотезы. Нельзя добирать квоту непроверенными сценами. Если доступен только metadata, stage остаётся incomplete/degraded с видимой причиной. Уменьшение корпуса допускается как явно обозначенный pilot, но не как прошедший release criterion.

**После MVP:** multimodal embeddings и ANN при доказанной потребности; scene-boundary automation; active learning; большие команды и multi-tenant storage; автоматическая адаптация 9:16/1:1; богатые дизайн-системы; Weave workflows; автоматический animatic, VO/audio timing, AE/Remotion export; learning-to-rank; лицензируемая библиотека медиа; библиотека полноценного art direction. Финальная генерация видео — отдельное продуктовое решение, не подразумеваемое продолжение этой задачи.

## D. Конкретные изменения репозитория

Все пути ниже — **предлагаемые изменения**, не уже созданная реализация. Не трогать `sources/` и пользовательские данные.

| Путь | Изменение |
|---|---|
| `core/skills/motion-design-director/SKILL.md` | Новый основной skill визуальной режиссуры |
| `core/skills/visual-qa/SKILL.md` | Новый skill проверки contact sheet, state strips и Figma readback |
| `core/skills/creative-reference-research/SKILL.md` | От work metadata к validated scene observations; retrieval входит сюда как режим |
| `core/skills/visual-direction/SKILL.md` | Совместимый thin alias/делегирование в motion-design-director, затем deprecation; не два конкурирующих директора |
| `core/skills/saas-narrative-director/SKILL.md` | Scene briefs: viewer change, mechanism, proof need, asset constraints |
| `core/skills/storyboard-composition/SKILL.md` | Состояния, scene graph, rationale выбора паттерна, thumbnail QA |
| `core/skills/production-review/SKILL.md` | Проверка actual Figma, edit test, unresolved risks, handoff completeness |
| `core/skills/saas-creative-director/SKILL.md`, `CLAUDE.md` | Routing и три обновлённых gates; естественный русский интерфейс |
| `.claude/skills/<name>/SKILL.md` | Сгенерированные/проверяемые adapters, без независимых копий логики |
| `core/schemas/` | Новые `motion-direction`, `reference-scene`, `motion-observation`, `anti-pattern`, `retrieval-result`, `visual-qa`, `figma-manifest`, `knowledge-lock`, `project` schemas; расширить существующие reference/pattern/storyboard |
| `core/src/saas_creative_director/orchestrator.py` | Routing, validation-before-advance, gate revision binding, downstream invalidation |
| `core/src/saas_creative_director/validation.py` | Реальное исполнение schemas и междокументных инвариантов; null честно отличать от missing |
| `core/src/saas_creative_director/workspace.py` | Инициализация новых artifact contracts и project schema; старые проекты через adapter |
| `core/src/saas_creative_director/retrieval.py` | Новый deterministic filter/rank/dedup; trace кандидатов и причин отказа |
| `core/src/saas_creative_director/knowledge.py` | Новый resolver versions/layers/freshness; immutable snapshot |
| `core/src/saas_creative_director/layout.py` | Новый compiler pattern recipe → native scene graph |
| `core/src/saas_creative_director/figma.py` | Manifest v0.7, состояния, asset refs, object IDs, annotations, node provenance |
| `core/src/saas_creative_director/cli.py` | validate-stage, retrieve, knowledge-check, migration dry-run/apply, manifest/QA; пользователь вызывает через естественный язык |
| `core/integrations/figma/patterns/*.json` | 8 параметризованных recipes; внутри managed core, не новая непокрытая update-директория |
| `figma-plugin/src/code.ts`, `ui.html`, `dist/code.js` | Renderer native types, schema validation, safe reimport/conflicts, export readback; обновить собранный plugin |
| `knowledge/current-motion/`, `knowledge/references/scenes/`, `knowledge/patterns/`, `knowledge/anti-patterns/` | Версионированное managed knowledge, не client inputs |
| `evals/motion-intelligence/` | Brief fixtures, split manifest, retrieval relevance labels, A/B rubric, reviewer packet, results format |
| `tests/test_validation.py`, `test_orchestrator.py`, `test_figma.py`, новые retrieval/knowledge/layout tests | Контрактные/семантические проверки и failure cases |
| `core/src/saas_creative_director/maintenance.py`, `scripts/build_release.py` | Общий release allowlist, новые knowledge paths, совместимость/rollback; не копировать root рекурсивно |
| `core/COMPATIBILITY.json`, `core/VERSION`, `CHANGELOG.md` | Предлагаемый релиз 0.7.0 после приёмки; данные 0.7 с read adapter для 0.5 |
| `docs/ARCHITECTURE.md`, `REFERENCE_RESEARCH_POLICY.md`, `INSTALLATION.md`, `UPGRADING.md`, `RELEASING.md`, `docs/ru/*` | Синхронизировать реальное поведение; добавить `docs/migrations/0.6-to-0.7.md` |
| `examples/ledgerly/` | Сохранить old baseline отдельно; новый v0.7 пример с настоящими evidence-linked states, без повышения доказательности старых записей |

### Update-safe knowledge architecture

- **core:** workflow, schemas, tooling, recipes и skill logic.
- **managed knowledge:** доставляемые references/patterns/current observations; каждый выпуск immutable, content digest и compatibility range.
- **config:** параметры организации и доступных integrations.
- **overrides:** локальные дополнения поведения, с декларацией совместимости; не ручное редактирование core.
- **knowledge/custom:** собственные references/patterns; отдельный namespace `custom:*`, те же validation rules.
- **projects:** клиентские assets, private evidence, approvals, выбранные snapshots, итоговые artifacts.
- **`.scd/cache`:** производные индексы; их можно перестроить; не источник истины.

Resolver: core defaults → organization config → compatible overrides/custom knowledge → project constraints/approved decisions. Evidence и product-boundary invariants остаются обязательными. При конфликте сообщать конкретные значения и происхождение, не молча выбирать последнюю запись.

`knowledge-lock.json` в проекте фиксирует engine/schema/knowledge/taxonomy/recipe/model/prompt versions, content hashes и дату cutoff. Старый проект читает свой snapshot; обновление библиотеки не меняет утверждённый storyboard. В MVP можно доставлять knowledge вместе с core, сохраняя отдельные версии и project snapshots; отдельный remote package registry не нужен.

### Обновление и rollback: важные разрывы текущего кода

Текущий updater действительно отделяет protected directories. Но `copy_managed` заменяет пути последовательно, поэтому операция не является одной атомарной транзакцией всего релиза. Integrity manifest проверяется только при наличии; declared schema bounds не сопоставляются с проектами. Rollback может оставить новые managed paths, отсутствующие в старом архиве, потому что отсутствующие incoming paths пропускаются. Это следует исправить до обещания update-safe Motion Intelligence.

Нужны: обязательный release manifest; staging validation; lock от параллельного обновления; журнал замен и recovery при сбое; removal только прежних managed files, отсутствующих в выбранном релизе; проверка protected checksums; явный отчёт совместимости; smoke test и автоматическое восстановление предыдущего core при неуспехе. Client schemas не мигрировать неявно. Archive extraction не должна принимать path escapes или ссылки за пределы staging. Проверять происхождение релиза отдельно от простого совпадения checksum.

Установка остаётся `./scd install`, обслуживание `./scd update`, `./scd health-check`, `./scd rollback`. Добавить pin конкретного релиза и проектную migration dry-run; точный CLI зафиксировать при реализации. Для обычного пользователя Claude выполняет операции и объясняет результат без требования редактировать JSON.

Документация должна различать Claude Code project skills и переносимый пакет для Claude.ai/Cowork: skill Markdown сам по себе не доставляет локальный Python/Figma importer и не гарантирует те же инструменты. Для MVP поддерживать и тестировать один основной путь — Claude Code + локальный workspace + Figma adapter. [Claude Code Skills](https://code.claude.com/docs/en/skills), [Agent Skills specification](https://agentskills.io/specification)

Semver engine, schema и knowledge — отдельные версии. 0.x не означает «можно молча ломать пользователя»; breaking data changes требуют migration даже до 1.0. После 1.0 соблюдать обычный MAJOR/MINOR/PATCH контракт. [SemVer](https://semver.org/)

## E. Skills и schema contracts

### Skill specs

| Skill | Вход → выход | Обязательное поведение |
|---|---|---|
| `creative-reference-research` | Approved strategy / scene briefs + source registry → references, reference-scenes, retrieval-result | Ищет mechanism-first; сохраняет observation method; не выдаёт описание страницы за просмотр видео; делает подбор по сценам |
| `motion-design-director` | Strategy, narrative, product assets, brand, reviewed knowledge, candidate patterns → `motion-direction.json` + representative composition frames | Предлагает 2 различающихся подхода с trade-offs; выбирает product-/concept-/brand-led/hybrid по задаче; фиксирует causal logic, hierarchy, density, tempo и constraints |
| `saas-narrative-director` | Strategy/evidence/research → narrative + scene briefs | Каждая сцена: viewer state before/after, нужное доказательство, механизм и временной бюджет; не диктовать случайные визуальные украшения |
| `storyboard-composition` | Утверждённое direction + scene retrieval → storyboard + manifest | Компилирует выбранные паттерны в конкретные objects/states; объясняет адаптацию; проверяет continuity и duration |
| `visual-qa` | Rendered contact sheet, state strips, storyboard, product sources, Figma readback → `visual-qa.json` | Проверяет изображение и структуру; выдаёт конкретные локализованные findings; не утверждает результат вместо человека |
| `production-review` | QA, editable Figma, asset register, approvals → handoff + production review | Проверяет реальные задачи редактирования, все исключения и границы ответственности |

`motion-direction.json`: version, strategy/narrative revisions, direction ID, alternatives/rationale, visual mode, product fidelity policy, copy roles, hierarchy, allowed patterns, motion functions, continuity rules, density/pacing envelope, token references, asset gaps, conditional anti-pattern exceptions, evidence/reference IDs, representative-frame IDs, locked/free decisions.

Не фиксировать без причины универсальные «65% UI / 20% illustrations / 15% typography». Если нужны доли, задавать метод подсчёта (например, время primary carrier; роли могут пересекаться) и обоснование под формат. Не превращать квоты разнообразия в требование каждый раз менять композицию.

### Общие правила схем

Каждый документ: `schema_version`, стабильный `id`, `revision`, `created_at`, `updated_at`, `provenance`. JSON Schema проверяет форму; отдельный semantic validator проверяет разрешимость ID, междокументную согласованность, источники и тайминг. Для дат/URL нужен реально включённый format checker. Unknown разрешается только там, где это осмысленно; отсутствие критического asset/state — видимый blocker либо approved conceptual exception.

| Entity | Обязательные поля / инварианты |
|---|---|
| `ReferenceWork` | source ID, canonical URL, studio/client, tier, media locator, publish date nullable + evidence, first seen, access check, visual review, rights policy, status, scene IDs |
| `ReferenceScene` | work ID, start/end ms для просмотренного интервала, keyframe locators, observation records, mechanism/taxonomy tags, before/trigger/after, persistent objects, adjacent scene IDs, inspection limitations |
| `Observation` | field/value, evidence level, inspection method, supporting locator, reviewer, observed_at; temporal claims требуют video/timed sequence |
| `MotionObservation` | claim, scope/cohort, method, supporting/contradicting scene IDs, inference status, review due; «current» требует подтверждённых дат |
| `Pattern` | ID/version, communication problem, preconditions, invariants, free parameters, motion contract, examples/counterexamples, maturity, recipe ID, non-copy boundaries |
| `AntiPattern` | symptom, failure mechanism, applies_when, exceptions, detector type, severity, repair options, source links |
| `RetrievalResult` | query/constraints, snapshot, candidates with dimensions/reasons, selected/rejected, abstention, adaptation rationale |
| `StoryboardScene` | ID, purpose/message, timing, evidence, pattern/version, asset IDs/fidelity, states, attention path, motion events, transition, retrieval decision, locked/free |
| `FigmaManifest` | source storyboard revision/hash, canvas, tokens, asset registry, state frames with node tree, recipes, expected editable semantics, ownership |
| `VisualQA` | artifact revision, rendered evidence, scene/sequence findings, severity, fix, inspector, editability tests, unresolved blockers, status |
| `KnowledgeLock` | engine/schema/pack/taxonomy/recipe versions, content hashes, selected source revisions, cutoff, model/prompt provenance |
| `Project` | stages, artifact revision map, gates with digests, compatibility/pinning, migration history |

Не смешивать **evidence level**, **reviewer confidence**, **pattern maturity** и **benchmark membership**. Нынешнее pattern confidence=`benchmark` вынести в отдельный статус. `CONFIRMED` у наблюдения «на кадре выделена строка» не означает confirmed пользу этого решения для conversion.

### Пример scene contract

Ниже проектируемый пример, не готовая запись gold corpus и не утверждение о реальном UI Ledgerly. `HYPOTHESIS` и fixture IDs намеренно видимы; в production нужны источники клиента и проверенные референсы.

```json
{
  "schema_version": "0.7",
  "id": "S03",
  "revision": 1,
  "purpose": "Показать, что автоматизация сохраняет исключения для проверки",
  "duration_ms": 6000,
  "evidence_level": "HYPOTHESIS",
  "evidence_ids": [],
  "ui_fidelity": "conceptual",
  "pattern": {"id": "PAT-COMPOSITION-001", "version": "1.0.0"},
  "reference_scene_ids": [],
  "retrieval_decision": {
    "status": "no_suitable_match",
    "reason": "Учебный пример; референс пока не инспектирован"
  },
  "objects": [
    {"id": "transaction-table", "kind": "frame", "role": "product-surface"},
    {"id": "exception-row", "kind": "frame", "role": "proof", "parent_id": "transaction-table"}
  ],
  "states": [
    {"id": "entry", "at_ms": 0, "description": "Список содержит обычные и исключительную строки"},
    {"id": "result", "at_ms": 3000, "description": "Обычные строки обработаны; исключительная остаётся видимой"}
  ],
  "motion_events": [
    {"object_id": "exception-row", "from_state": "entry", "to_state": "result", "start_ms": 1000, "end_ms": 3000, "function": "preserve-exception", "primitive": "reframe", "attention_reason": "Не потерять объект, требующий решения человека"}
  ],
  "hold": {"state_id": "result", "start_ms": 3000, "end_ms": 6000},
  "transition_out": {"type": "object-continuity", "anchor_id": "exception-row", "next_scene_id": "S04", "next_anchor_id": "review-detail"},
  "recipe_id": "recipe.context-detail@1.0.0",
  "locked": ["Исключение не исчезает без действия человека"],
  "creative_freedom": ["Материал, акцент, easing в пределах читабельности"],
  "requires_product_confirmation": true
}
```

Реальный manifest дополняет каждое состояние разрешёнными bounds/layout, content, token references, crop и z-order. Объяснительный текст states не заменяет node tree. Сумма duration всех сцен должна совпадать с длительностью ролика; события и holds находятся внутри сцены; transition anchor должен разрешаться в обеих сценах. Неподтверждённый product mechanism блокирует production-ready статус.

## F. Taxonomy, reference library и retrieval

### Оси разметки

| Ось | Начальный vocabulary |
|---|---|
| Communication job | orient, reveal capability, demonstrate mechanism, compare, prove outcome, establish trust, CTA |
| Mechanism | transform, route, aggregate, filter, detect, coordinate, synchronize, retrieve, generate, approve |
| Information relation | one-to-one, one-to-many, many-to-one, many-to-many, before/after, branch |
| UI fidelity | actual-capture, faithful-reconstruction, simplified-truthful, conceptual, unknown |
| Composition | product hero, detail/context, persistent cause/result, shared-baseline comparison, progressive disclosure, spatial pipeline, nested scope, focused work surface |
| Attention | isolate, contrast, pointer/action, reveal, focus transfer |
| Motion function | state change, continuity, causality, hierarchy, feedback, compression, orientation |
| Motion primitive | translate, scale, crop/reframe, opacity, mask, rearrange, number change, connector |
| Transition relation | same object/new state, consequence, detail/context, comparison, scope change, chapter reset |
| Rhythm | burst/hold, staged steps, sustained flow, held proof; измеренные durations отдельно |
| Context | channel, audience, funnel, aspect ratio, language, product maturity, available assets, budget |
| Style attributes | typography/material/depth/color/footage/illustration как описательные теги, не индекс качества |

Контролируемые значения + `other` с пояснением; taxonomy имеет версию. Механизм «many-to-one» может работать для fintech, logistics и devtools. Отрасль полезна как дополнительный контекст, не основной ключ поиска.

### Стартовая pattern library

Сохранить существующие `persistent-cause-result`, `object-continuation`, `state-match`, `mechanism-before-claim`, расширив версии и контракты. Добавить 8 recipes: focused UI crop; context-to-detail; anchored cause/result; before/after on shared baseline; progressive list resolution; routed flow; convergence-to-result; single-proof/result lockup. Дополнить паттернами exception persistence, scope reveal, editorial type beat, modular capability sequence. Не называть общую геометрическую операцию уникальным студийным стилем.

Каждая recipe задаёт anchors, hierarchy, bounds constraints, safe zones, allowed native objects, text roles и варианты плотности. Brand tokens, контент, UI assets и expressive choices приходят из проекта. Recipe должна сохранять композиционный принцип при изменении длины текста, а не быть одним фиксированным кадром 1920×1080.

Для promotion experimental → supported требовать минимум два наблюдённых использования в разных работах и review; разнообразие студий указывать отдельно. Это практическое правило curation, не доказательство универсальной эффективности. Фундаментальные принципы могут иметь отдельное основание, не притворяясь трендом текущего года.

### Как пополнять библиотеку

1. Существующие 24 work candidates использовать как очередь, 8 provisional annotations — как пример честной неопределённости. Не объявлять их gold.
2. Начинать с Anyway, Timeframe, Flash Motion и Skale; добавлять категорийные и cross-industry примеры под реальный механизм.
3. Проверить оригинальный work URL, доступность, автора, дату публикации и допустимость хранения. До выяснения прав хранить ссылки/аннотации, не распространять чужие видео и кадры в release.
4. Просмотреть полную работу для контекста; разметить значимые интервалы и соседние переходы. Screenshot подтверждает layout, но не easing или pacing.
5. Записать observation отдельно от interpretation и business claims. Данные страницы «modern / conversion-focused» не становятся оценкой исследователя.
6. Проверить часть разметки вторым человеком, разрешить расхождения, пометить gold только после этого.
7. Вывести паттерны, зарегистрировать counterexamples, ограничения и recipe compatibility.
8. Выпустить новую knowledge version через review diff + проверки. В существующих проектах ничего не пересобирать молча.

Модель provenance заимствует минимальную цепочку entity → observation activity → reviewer → derived pattern → project decision. Полная RDF-система для этого не нужна. [W3C PROV-DM](https://www.w3.org/TR/prov-dm/)

### Поиск по сценам

Запрос: «показать, что несколько источников превращаются в проверяемый результат, оставляя исключения видимыми», а не «лучший современный fintech ролик».

1. Hard filters: доступное evidence, разрешённое использование, требуемая inspectability, выполнимость UI/production constraints. Сцена только со still может участвовать в composition search, но не в motion-evidence search.
2. Candidate generation: controlled tags + полнотекстовый поиск кратких аннотаций; индекс можно хранить в SQLite FTS или небольшом локальном JSON наборе.
3. Ranking: сначала mechanism и information relation, затем product fidelity, feasibility/timing, composition/attention. Source prestige, recency и craft — отдельные признаки, не замена релевантности.
4. Выдать top-3 с объяснениями, ограничениями и причинами отклонения близких кандидатов. Diversify по работам и студиям; не снижать релевантность ради формальной квоты.
5. Перед использованием перехода проверить прилегающие интервалы. Выбирать паттерн и adaptation rationale, не копировать сцену.
6. При отсутствии подходящего материала вернуть abstention, продолжить поиск либо оформить experimental direction с человеческим решением. Не добавлять случайную ссылку для прохождения validator.

Temporal retrieval — отдельная задача от поиска целого видео; это хорошо иллюстрирует QVHighlights. Его домен не равен SaaS, поэтому переносим принцип работы с интервалами, а не заявляем готовую точность модели. [QVHighlights](https://arxiv.org/abs/2107.09609)

Векторы отложить: image similarity легко находит похожий цвет/объект, но не объясняет причинность. Если baseline теряет релевантные сцены, сначала text embeddings по проверенным аннотациям, затем image reranking; каждое усложнение должно улучшать held-out retrieval eval.

### Anti-pattern library: 10 условных правил

| Симптом | Когда это ошибка | Законное исключение / исправление |
|---|---|---|
| Одинаковая центральная карточка во всех сценах | Разные задачи получают одну иерархию без причины | Стабильность полезна для пошагового обучения; менять scale/attention по смыслу |
| Floating cards / орбиты | Неясно, что является причиной и результатом | Реальная параллельная работа; добавить связи и изменение состояний |
| Полный dashboard | Нужная деталь не читается в размере просмотра | Overview для ориентации; затем осмысленный crop |
| Generic AI glow / мозг / магический шар | Вместо демонстрации реальной функции | Brand metaphor с явной ролью; показать actual input/output |
| Decorative 3D / glass / neon | Мешает чтению, не соответствует бренду или бюджету | Пространственная информация или брендовая функция; уменьшить конкуренцию за внимание |
| Непрерывная высокая скорость | Нет времени прочитать результат/доказательство | Короткий тизер; добавить hold после плотного события |
| Произвольный fade/wipe/zoom | Не поддерживает смысл, пространство или ритм | Намеренная смена главы; использовать continuity anchor там, где важна причинность |
| Всё появляется одновременно | Headline, UI, proof и ornament конкурируют | Сравнение требует simultaneity; иначе progressive disclosure |
| Выдуманные UI controls/results | Зрителю обещается неподтверждённое поведение | Концептуальное UI только с маркировкой и согласованием |
| Узнаваемая копия чужого treatment | Совпадают характерная композиция, материалы и последовательность | Абстрагировать relationship; вернуть client brand; проверить несколько независимых источников |

«Похоже на AI» не является машинно проверяемым критерием. Finding должен указывать кадр/объект, проблему для зрителя, исключения и конкретное исправление.

### Freshness

Раздельно хранить `published_at`, `first_seen_at`, `last_access_checked_at`, `last_visual_reviewed_at`, `review_due_at`, package release. Для трендовых claims — окно наблюдений и дату пересмотра. Начальная политика: ежемесячная проверка доступности; ежеквартальный review current-motion и паттернов; внеплановый review после негативного feedback или изменения продукта. Это предлагаемая политика, а не уже запущенная автоматизация.

Дедлайн review не делает паттерн ложным. Старое сильное решение может быть применимо; свежая дата не делает кадр хорошим. Inaccessible источник остаётся в lineage с историей; свежие утверждения на его основе запрещены без повторной инспекции. Неизвестная дата исключает источник только из dated trend assertions, не из всей библиотеки.

## G. Eval strategy

### Четыре независимых уровня

1. **Evidence/contract correctness:** schema validation, IDs, dates, timings, rights flags, no metadata-only motion inference, no hidden hypotheses, stage/gate enforcement.
2. **Retrieval relevance:** найден ли подходящий механизм, а не эстетически похожая картинка.
3. **Visual quality:** hierarchy, causality, contemporary suitability, coherence и distinctiveness при одинаковой детализации.
4. **Production usability:** нативность, редактируемость, ясность motion intent, передача ассетов и сохранение правок дизайнера.

Не сводить к одному Modernity Score. Существующий общий 14/16 не должен компенсировать провал product truth или редактируемости. Automated graders + human review комбинировать; проверки должны оценивать настоящий итог, не только следование процедуре. [Anthropic: Demystifying evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)

### Benchmark set

24 brief cases: 5 product demos, 5 AI workflow launches, 4 fintech/data, 4 devtools/infrastructure, 3 short performance/feature promos, 3 brand/concept exceptions. Внутри — отсутствующий UI, сложный dense UI, неизвестные dates, недоступный reference, длинный русский copy, identity conflict и неподдержанный asset.

Использовать 12 development и 12 held-out briefs; split по продуктам/работам, не по соседним кадрам одного видео. Corpus sources и eval labels отделить от skill examples. Включить качественные старые и посредственные свежие работы как контроль смещения «новое = хорошее». Новый feedback пополняет regression set, но не переписывает исторические результаты. Заявленные 16 inspected works и 48 scenes — библиотека; 24 briefs и 60 запросов — отдельные eval сущности.

Retrieval: 60 запросов, в том числе 12 no-match/insufficient-evidence; answerable распределены по mechanism families. Разметка 0–3: нерелевантно, поверхностно похоже, применимо, сильное соответствие. Hard negatives: похожая отрасль/палитра, другой механизм. Минимум два разметчика и adjudication для held-out queries. Report nDCG@5, eligible hit@3, Recall@5 по adjudicated pool, abstention precision/recall, diversity и validity. При неполной разметке не называть recall исчерпывающим.

Предлагаемые release floors: 100% валидной provenance; ноль motion assertions из metadata/still-only records; хотя бы один strongly relevant eligible результат в top-3 для ≥80% answerable queries; корректное abstention в ≥10 из 12 no-match cases. Пороги согласовать до просмотра результатов, не подгонять после.

### Blind A/B

Pilot: 12 held-out briefs × 3 независимых специалиста (motion designer, art director, animator). A — текущий baseline; B — Motion Intelligence. Одинаковые brief, product facts, утверждённый script, model/settings и бюджет генерации; одинаковый формат, масштаб и fidelity отображения. Скрыть pipeline labels и ссылки на студии до оценки, случайно менять left/right и порядок, разрешить ties/insufficient evidence.

Оценивать отдельно сцены и sequence по шкале 1–5:

- ясность механизма (1 — невозможно понять, 3 — понятно после объяснения, 5 — очевидная причинная связь);
- hierarchy/readability (1 — конфликт внимания, 3 — рабочая композиция, 5 — ясный фокус и чтение);
- соответствие современному контексту конкретного формата (1 — несоответствие аудитории/каналу, 3 — приемлемо, 5 — убедительный актуальный язык без слепого подражания);
- continuity/motion intent (1 — несвязанные кадры, 3 — переходы понятны, 5 — последовательность усиливает смысл);
- brand/product specificity (1 — подходит любому SaaS, 3 — отражает продукт, 5 — узнаваемо и не копирует benchmark);
- production usability (1 — нужно проектировать заново, 3 — есть доработки, 5 — можно продолжить craft без пересборки смысла).

Анализировать на уровне brief, а не считать 36 оценок независимыми проектами. Публиковать wins/ties/losses, парные различия, расхождения между reviewers и качественные причины. Доверительные интервалы с кластеризацией по brief, если рассчитываются, при n=12 будут широкими. Pilot — направляющий сигнал, не доказательство статистически значимого превосходства.

Проектный go/no-go: минимум 8/12 majority wins без ухудшения clarity и usability, ноль критических factual/editability failures; если результат неоднозначный — исправить причины и расширить выборку по заранее записанному протоколу. Для публичного claims об эффективности нужен отдельный larger confirmation cohort; не обещать заранее достаточную мощность «30 примеров» без расчёта.

После вертикального среза провести ablation: baseline; исправленный renderer с прежним контентом; + motion direction; + retrieval; + visual QA. Это отделит эффект знаний от исправления потери композиции. Если полный вариант медленнее без полезного выигрыша, убрать лишний этап.

Чёткие определения критериев важны для воспроизводимости human evaluation. Bias автоматических judges требует калибровки; VLM помогает искать ошибки, но не единолично утверждает качество. Указанные исследования относятся к NLG/LLM evaluation; применение к визуальной режиссуре — методологическая адаптация. [Howcroft et al.](https://aclanthology.org/2020.inlg-1.23/), [Zheng et al.](https://arxiv.org/abs/2306.05685)

### Production task test

Дать независимому motion designer файл Figma и пять заданий: изменить заголовок; заменить product UI; изменить состояние строки; найти переход и source notes; определить locked/free решения. Измерить завершение, время, число уточнений и объём перестройки. Отдельно проверить повторный import после ручной правки.

Release floor: все пять задач выполнимы без пересборки flattened scene; native text редактируется; hierarchy/grouping осмысленны; assets и limitations обнаружимы; reimport не теряет человеческие изменения и не создаёт дубликаты без выбранного versioning mode. Целевой выигрыш по времени установить после baseline measurement, а не обещать «80% автоматизации» без наблюдений.

Static QA оценивает motion intent. Плавность, ощущение скорости, easing, VO/music synchronization и финальное впечатление оцениваются только на animatic/video; это ограничение обязательно показывать в handoff.

## H. Поэтапный план и зависимости

Оценка ниже — рабочая гипотеза для одного инженера плюс доступного motion designer/куратора. Агент может ускорить написание кода, но не устраняет ручную проверку видео, арт-дирекцию и доступ к Figma. Ориентир 5–7 календарных недель при частичном параллельном выполнении; уточнить после spike. Это не обещание срока.

| Этап | Объём / зависимость | Приёмка |
|---|---|---|
| P0 — baseline, 1–2 дня | Зафиксировать 0.6.0, существующие результаты, renderer limits, 3 контрольных scenes | Baseline packet, source audit, доступен Figma sandbox, нет притворных gold annotations |
| P1 — feasibility slice, 2–3 дня | После P0: один inspected reference → pattern → structured states → 3 разных композиции в Figma | Copy reflow, crop, native hierarchy, object IDs; manifest intent совпадает с canvas; честные asset limitations |
| P2 — contracts/lifecycle, 3–4 дня | После P1: schemas, validator, gate digests, version adapters, snapshot resolver | Некорректный stage не продвигается; old 0.5 читается; ручной approval не переносится на изменённый пакет |
| P3 — curation/retrieval, 5–8 рабочих дней | Может идти с P1/P2: manual inspections, scene taxonomy, patterns, lexical ranking | Целевой corpus; reviewed provenance; retrieval floors; неизвестные даты/движение не выдуманы |
| P4 — director/composition/QA, 4–6 дней | P2 + первый validated corpus из P3 | 2 creative alternatives, representative frames, scene contracts; findings локализованы и исправляемы |
| P5 — Figma adapters/handoff, 4–6 дней | P1/P2; параллельно P4 после стабилизации manifest | 8 recipes, font/asset preflight, safe reimport, readback/screenshots; 5-task usability pass |
| P6 — evaluation/release, 3–5 дней | P3–P5 | Blind pilot, ablation baseline, no blockers, upgrade/rollback rehearsal, русские onboarding/update docs |

**Критический путь:** scene contract → compiler → verified Figma output → visual/handoff evaluation. Curation начинается рано и не ждёт завершения программирования. Не строить сразу десятки паттернов поверх непроверенного renderer.

Зависимости извне: доступные видео и право на хранение ассетов; подтверждённые UI assets клиента; 2 аннотатора для части gold set; 3 reviewers blind pilot; Figma test file и разрешённый write transport. Если этих ресурсов нет, можно завершить engineering preview, но нельзя объявить quality release прошедшим приёмку.

Release package: core/skills + compatible adapters; curated knowledge version; migration guide; changelog; compatibility matrix с фактически испытанными client/tool versions; fixture previews; eval report с limitations; rollback evidence. Обновлять `VERSION` только после этих проверок.

## I. Риски и ограничения

| Риск | Как ограничить |
|---|---|
| Субъективность «современности» | Context-specific rubric, blind comparison, несколько reviewers; никакого одного магического числа |
| Tier A превращается в единственный вкус | Stratified sources, разные formats и historical controls; studio prestige не relevance score |
| Непроверенные маркетинговые claims студий | Записывать как attributed source statements; не как causally established performance |
| Недоступные видео / неизвестные даты | Metadata-only queue, nulls, alternate inspectable works; не восполнять пробелы догадками |
| Копирование treatment | Отделять relationship от expression; multiple-source abstraction, non-copy boundaries, human review |
| Авторские права и приватный UI | Permission/retention fields, links-first distribution, private project storage; публичность страницы не равна праву распространять кадры |
| «Editable» только на бумаге | Native editability classes, Figma readback, реальные editing tasks; raster UI честно маркировать |
| Дизайнер исправил файл, reimport всё затёр | Ownership/revision tracking, conflict report, preserve-human by default, draft version alternative |
| Изменения API/seat/tools | Capability probe, один общий manifest, plugin fallback, versioned compatibility checks |
| Model drift и taste drift | Pin версии/настройки, fixed regression + rolling benchmark, review изменений |
| Рост библиотеки увеличивает шум | Mechanism-first ranking, curated eligibility, measured retrieval; embeddings только по evidence |
| Static frames создают иллюзию motion QA | State strips + time notes; animatic отдельно, отсутствие playback не скрывать |
| Update ломает проекты | Protected paths, immutable project snapshot, non-destructive migration, tested rollback |

## J. Задание на следующую реализацию

Готовый краткий prompt находится в [IMPLEMENTATION_PROMPT.md](IMPLEMENTATION_PROMPT.md). Начинать с P0/P1 и согласованного semantic contract. Не делать одновременно полную библиотеку, новый orchestration runtime и video renderer. В этом исследовательском проходе product code, skills, схемы и Figma canvas не изменялись.

## Исследовательские материалы

Сводка текущего визуального языка, студий, инструментов и актуальных возможностей Figma: [RESEARCH_FINDINGS.md](RESEARCH_FINDINGS.md).

Исходные исследовательские записки: [студии](studios-research.md), [retrieval и evals](retrieval-evals-research.md), [Figma и инструменты](figma-tools-research.md). Они содержат альтернативные предварительные предложения по объёму корпуса; итоговые решения и пороги зафиксированы в этом PLAN.md.
