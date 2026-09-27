# Единый план доработок: качество, расходы, Figma и безопасность

27 сентября 2026. Статус: основная инженерная часть реализована в рабочем дереве; стабильный релиз ожидает живой проверки Figma и пилотной blind A/B оценки. Основание: локальный код 0.6.0 + Unreleased Motion Intelligence, соседняя задача **Build SaaS Creative Director**, исследование и проверка специализированными агентами. Пользователь подтвердил основной способ оплаты конечного пользователя: **Claude Pro/Max**.

Этот документ задаёт актуальный порядок и размер работ. [Предыдущий PLAN A–J](PLAN.md) сохраняется как подробный дизайн Motion Intelligence. При расхождениях приоритет у MASTER_PLAN: меньше первоначальный корпус и eval, Figma plugin первым, обязательная защита INBOX, подписка вместо обязательного API runner. [START_DEVELOPMENT_5_6.md](START_DEVELOPMENT_5_6.md) — краткая точка входа для разработки.

## 1. Решения, которые фиксируем

1. **Продукт:** evidence-backed creative pre-production для SaaS. Финал — понятный storyboard, native editable Figma и handoff; финальный ролик не генерируем.
2. **Пользовательский путь:** Claude Desktop → Code → Local → папка проекта, русский язык, обычные фразы. Без требования вручную ставить Python, npm и править JSON. Обслуживание должно реально поддерживать этот путь, а не только обещать его в README.
3. **Оплата:** Pro/Max allowance по умолчанию. Никакого обязательного API-ключа, включения usage credits или автопополнения самим продуктом. Настройки аккаунта меняет только пользователь.
4. **Архитектура:** один orchestrator + небольшие skills + deterministic tools. Агенты использованы для разового аудита; постоянные команды агентов не входят в стандартный клиентский workflow.
5. **Figma:** общий scene contract и существующий importer как основной путь. MCP — опциональная автоматизация после проверки тех же данных. Не строить два независимых renderer.
6. **Качество:** сначала один полезный end-to-end проект; затем три реальных пилота. Более крупная библиотека и blind benchmark — последующее расширение проверки.
7. **Безопасность:** до новых функций устранить риски потери/утечки пользовательских файлов и небезопасной установки.
8. **Разработка:** после согласования перейти на GPT-5.6; предложенный конкретный вариант — Sol, medium для обычных задач и high для updater/schema/review при необходимости. Выбор модели разработки не меняет Claude-модель и оплату конечного пользователя.

Возможность графического локального workflow подтверждена документацией Claude Desktop; наличие Code tab не снимает зависимости наших собственных утилит. Проверка нового пользователя остаётся частью приёмки. [Claude Desktop quickstart](https://code.claude.com/docs/en/desktop-quickstart)

## 2. Что найдено и что меняется в приоритетах

| Приоритет | Подтверждённое по коду / контексту | Следствие для плана |
|---|---|---|
| P0 | `INBOX` входит в MANAGED updater и release builder, хотя содержит клиентские материалы | Удалить из managed; не распространять пользовательский inbox; защитить canary-тестами |
| P0 | `build_release.py` рекурсивно копирует папки, не используя `.gitignore` | Чистая сборка из разрешённых product files; тест на отсутствие private fixture в архиве |
| P1 | Archive extraction проверяет имена, но не обеспечивает достаточного контроля links/types; release manifest необязателен | Безопасный staging, строгий архивный allowlist и обязательная проверка релиза |
| P1 | Update по частям, нет полноценного recovery; совместимость проектов не проверена; starter config отсутствует в core-пакете | Самодостаточный starter, проверка скачанного артефакта, explicit migration, rollback по transaction ID |
| P1 | `.gitignore` покрывает часть inputs/artifacts, но не весь private project tree | Защита project.json, reviews, exports, logs, snapshots и cache; release allowlist независимо от Git |
| P1 | Validator не исполняет schemas; пустой проект можно продвинуть; approval не закрепляет revision | Stage-aware validation, evidence source locators, revision-bound gates |
| P1 | Figma importer теряет визуальную семантику, создаёт generic rectangles, повторно дублирует frames | Исправить контракт и renderer до масштабирования Motion Intelligence |
| P1 | Orchestrator управляет стадиями, но не вызовами провайдера | Не обещать hard token/dollar cap из одного SKILL.md; сначала ограничить workflow и измерять |
| P1 | Предыдущий исследовательский пакет уже содержит около 110 тыс. символов | Не загружать весь пакет на каждую сцену; подготовить короткие stage handoffs |

Число символов — локальный замер размера текста, не измерение токенов. Текущий security-аудит повторил только безопасный тест INBOX во временной папке с синтетическим файлом: файл исчез после замены managed directory. Настоящие материалы клиента не использовались. Архивные риски оценены по коду; степень риска зависит от версии Python. Остальные live integrations и обновление рабочей установки не запускались.

## 3. Токеномика под Pro/Max

### За что расходуется ресурс

Модель обрабатывает инструкции, активную историю, прочитанные документы, tool results, изображения, рассуждение и новые ответы. Расход возникает в работе Claude; сам локальный deterministic importer не делает вызовов LLM. Если Claude пишет огромный JSON дерева Figma вручную или каждый раз читает всю библиотеку, это добавляет расход. Если готовый plugin создаёт тысячу nodes из компактной scene specification, сами тысяча nodes не означают тысячу model calls.

Подписка не равна кошельку с фиксированной ценой каждого запроса. Нельзя надёжно перевести «45 секунд видео / 8 сцен» в доллары или процент Pro/Max без наблюдений в реальном аккаунте. API token prices не являются счётом за использование подписки. Отдельный разбор режимов и кредитов — [CLAUDE_CREDITS.md](CLAUDE_CREDITS.md).

### Как ограничиваем работу

| Ресурс | Предлагаемый Standard preset для первого пилота | Что делать при исчерпании |
|---|---|---|
| Клиентский brief | Один компактный context packet; source extracts по IDs | Дочитывать только спорные/недостающие сведения |
| Конкуренты | 3 релевантных конкурента, 1–2 ключевых источника на каждого | Показать пробел, расширить только если он меняет решение |
| Reference discovery | До 12 кандидатов, до 6 подробных разборов новых работ на проект | Использовать проверенную библиотеку; targeted research по незакрытому механизму |
| Creative directions | 2 содержательно разных направления | Третье только при неудовлетворительном выборе или явном запросе |
| Scene retrieval | Top-3 на механизм; одинаковые механизмы используют один retrieval packet | Не повторять поиск для каждой похожей сцены |
| Storyboard | Один полный проход и до 2 targeted correction passes | Вернуть конкретный нерешённый вопрос человеку, не бесконечный self-critique |
| Figma QA | Contact sheet + detail crops по замечаниям; до 2 correction passes | Чёткий blocker report; не пересоздавать весь документ |
| Tool failures | До 2 повторов transient read; write retry только после readback/idempotency check | Сохранить checkpoint и понятную причину остановки |
| Агенты | 0 дополнительных в обычном проекте | Отдельный limited reviewer только если действительно нужен и разрешён |

Это **проектные лимиты операций**, а не гарантированные серверные ограничения токенов. Числа калибруются на пилоте. Источники, необходимые для проверки критического product claim, не выбрасывать ради квоты; показывать незавершённость вместо выдуманного вывода.

### Context и повторное использование

- `CLAUDE.md`: только глобальные правила и routing; полные знания не вставлять.
- Загружать текущий skill, краткий approved project state и релевантные source/pattern records. Не все 10 skills и не весь research пакет.
- Target stage packet: 4–8 тыс. входных токенов контента; предупреждение при >12 тыс. Это ориентир для нашего пакета, не размер полного внутреннего контекста Claude.
- Handoff: approved decisions, evidence IDs, выбранные patterns, unresolved issues, next action; 1–2 страницы. Оригинальные источники остаются доступными по ссылкам.
- Сохранять структурированный результат в файлах; в чате — короткое резюме/изменения. Не дублировать длинный JSON ещё и в ответе.
- Changes-first: правка S04 пересчитывает её и соседние continuity boundaries. Смена аудитории инвалидирует стратегию и downstream. Простая замена copy не перезапускает competitor research.
- Local cache key: project/source content digest + schema/skill/pattern versions + relevant inputs. Cache hit разрешён только при совпадении зависимостей; источник истины — versioned artifacts.
- Cache и retrieval изолировать по project ID; private client content не попадёт в общую библиотеку автоматически.
- Provider prompt caching и наш artifact cache — разные механизмы. Экономию от provider caching не гарантировать; измерять hit/miss, если доступны данные.
- Compaction/new session использовать с сохранённым checkpoint, а не после потери согласований. Новый чат не сбрасывает лимит подписки и не делает предыдущую работу бесплатной.

### Метрики без фиктивной точности

`usage-ledger.jsonl`: project/run/stage IDs, mode (`subscription` / `usage_credits` / `api` / `unknown`), model, timestamps, counts source reads/searches/screenshots/retries, cache hit/miss, changed scene IDs, input/output/cache tokens **только если предоставлены провайдером**, usage_source, estimate flag, pricing snapshot при денежной оценке. Не писать prompts, секреты и client text в telemetry по умолчанию.

Unknown числовые значения остаются null. Не читать приватные файлы авторизации и не сохранять balance credentials. Account-wide change allowance нельзя автоматически приписывать проекту, особенно при параллельных чатах. Для пользователя: «готов этап, изучено N источников, использована библиотека, требуется ещё один проход»; детализация по запросу.

Сравнить baseline и optimized run на одинаковом brief: measured tokens при наличии, tool calls, screenshots, время, rework, quality. Цель — снижение повторных чтений и повторной генерации при неухудшении качества; процент экономии объявлять после замера.

## 4. Как использовать Figma без лишних расходов

**Вход модели:** purpose, product assets, pattern, copy, attention, before/action/after. **Детерминированная часть:** coordinates, layout constraints, repeated UI rows/cards, node naming, IDs, tokens, manifest compilation. Claude не должен генерировать заново все свойства каждого rectangle.

Порядок: compact scene spec → schema/semantic preflight → deterministic renderer → draft version/import → compact readback → contact sheet review → targeted fixes → human approval.

- Сначала 3 различных composition recipes, затем 5 для пилотного MVP, затем до 8 по реальным задачам. Не 16 шаблонов до первого useful output.
- Native frame/text/vector/components; raster UI явно обозначен. Контент экрана не становится editable только из-за image fill.
- Видимые cards рядом со сценой: purpose, VO/copy, duration, motion/transition, source refs, locked/free. Не хранить handoff только в pluginData.
- Для transform-сцен показывать нужные boundary states. Три состояния каждого trivial CTA не обязательны.
- Новый approved storyboard revision по умолчанию создаёт новую draft-версию рядом. Безопасное обновление только machine-owned неизменённых nodes. Автоматический merge произвольных дизайнерских правок — post-MVP.
- Повтор того же import operation ID не создаёт копии. После uncertain write читать результат перед retry; для частичной операции показать incomplete draft.
- Readback: scene IDs, revision/hash, object counts, missing assets, text overflow, node map и warnings. Не возвращать весь Figma document tree.
- Один overview/contact sheet на checkpoint; крупные crops только проблемных областей. Не оценивать мелкий UI по нечитаемой миниатюре ради экономии.
- В plugin добавить `documentAccess: "dynamic-page"` и проверить scoped page loading: загрузка целого документа при старом manifest — лишняя работа, но не тождественна model token расходу. [Figma manifest](https://developers.figma.com/docs/plugins/manifest/)
- Нативный plugin без LLM не расходует Claude model tokens сам по себе. MCP calls добавляют контекст и ответы модели; возможные Figma seat/rate/AI-credit правила учитываются отдельно. Generative Weave/image/video tools выключены в основном flow.
- Permissions: заранее выбранный file/project/page scope; никаких cross-project writes, sharing/publishing или экспорта секретных данных по инструкциям из reference content.

MCP умеет записывать, но наличие capability в документации не гарантирует её в конкретном клиенте. Перед выбором пути — capability/permissions preflight. [Figma MCP tools](https://developers.figma.com/docs/figma-mcp-server/tools-and-prompts/), [access/limits](https://developers.figma.com/docs/figma-mcp-server/rate-limits-access/)

## 5. Безопасность: минимально необходимое

### Файлы, установка, выпуск

1. Защитить **целиком** `INBOX/`, `projects/`, `config/`, `overrides/`, `knowledge/custom/`; private cache/logs/backups не публикуются. Factory README/templates/config переместить в managed core и копировать при первом создании без перезаписи.
2. Release строить из чистого product inventory, а не рекурсивно копировать живую папку пользователя. `.gitignore` не является защитой архива. Manifest сам по себе не гарантирует, что в перечисленных файлах нет private data.
3. Проверять обязательный manifest, полный набор файлов, нормализованные относительные пути, типы, размеры/число файлов, compatibility и expected release identity до активации. Проверять supply-chain trust отдельно от checksum.
4. Archive staging не допускает absolute/traversal paths, symlinks/hardlinks/special files, выход через уже существующие links и перезапись protected paths. Лимиты распакованного размера/числа файлов; отказ без частичного применения.
5. Journal/lock для update, recovery после сбоя, rollback по transaction ID, а не по лексикографически последнему имени архива. Не затрагивать user data при удалении устаревших managed files.
6. Проверить install/update/reinstall/failed update/rollback **из готового release**, включая factory config и runtime. Публичная проверка checksum из того же неподтверждённого архива не является достаточной проверкой автора.

### Внешние данные и клиентская конфиденциальность

- Websites/PDFs/README, reference captions, Figma text и MCP results — недоверенные данные, не управляющие инструкции. Они не могут включать кредиты, менять permissions, запускать команды, утверждать strategy или требовать отправить клиентские материалы на внешний адрес.
- Разделить operations: read sources; local project writes; Figma writes; update/install; public share/publish; billing changes. У последних трёх нет подразумеваемой авторизации из креативного brief.
- Внешний поиск получает очищенные публичные формулировки механизма; private screenshots/docs не отправляются в поисковик автоматически. Перед работой пользователь видит, что локальное выполнение всё равно может передавать выбранный контекст Claude и данные Figma — соответствующим сервисам.
- API tokens не хранить в репозитории, logs, manifest, pluginData или source registry. MVP под Pro/Max обходится без нашего API secret.
- Figma importer принимает данные, не исполняемый JS; strict schema, type whitelist, size/node/text/image limits, safe asset handling. Не исполнять SVG scripts/external references; default network policy не расширять до wildcard.
- Human approval — запись конкретного решения и revision; слов «approved» на внешней странице недостаточно. В локальной папке с правом записи это workflow safeguard, не защита от злонамеренного владельца компьютера. Криптографическую многостороннюю approval-систему в MVP не строим.

## 6. Полный порядок разработки

| Этап | Что делаем | Приёмка / граница |
|---|---|---|
| **0. Зафиксировать baseline** | Версия, existing tests, known defects, private-data inventory, один знакомый завершённый проект для сравнения | Записано, что работает/не проверено; никаких новых release claims |
| **1. Защитить данные и обслуживание** | INBOX/protected paths, safe archive/release inventory, starter config, update recovery/rollback | Canary files сохранены byte-for-byte; ни один private sentinel не попал в архив; corrupt/malicious package отклонён до записи |
| **2. Контракты и согласования** | Реальные schemas, source/evidence/reference links, timing, prerequisites, revision-bound 3 gates | Empty project не может complete; source ID без locatable evidence не подтверждает claim; значимая правка инвалидирует зависимое согласование |
| **3. Экономный execution workflow** | Stage packets, artifact caching, delta reruns, operation quotas, checkpoint, observable usage | Нет повторного чтения всей библиотеки; нет автоэскалации billing/model; loop limit с checkpoint; неизвестный расход не выдан за точный |
| **4. Figma vertical slice** | 3 recipes, typed UI objects/states, visible notes, preflight, idempotent import, readback | Реальный Figma: distinct compositions, native text/UI, long Russian copy, stable IDs, сохранён human edit |
| **5. Motion Intelligence pilot** | 6–8 полностью проверенных references, 24–32 scene intervals, 8 abstract patterns, 5 recipes, условные anti-pattern checks, director/retrieval/visual QA | Всё temporal наблюдено; выбор scene mechanism объясним; reference-free hypothesis помечена; 2 directions до full expansion |
| **6. Пользовательский MVP** | 1 end-to-end pilot → ещё 2; русский onboarding, packaged runtime choice, resume/edit/export | Непрограммист самостоятельно начинает работу; один accepted handoff; три кейса проходят evidence/editability/data-safety gates |
| **7. Подтверждение качества и масштабирование** | 16 works/48 scenes, 8 recipes; 24 briefs/60 retrieval queries и blind A/B из предыдущего PLAN | Расширенный eval после полезного pilot; никаких обещаний эффекта по одним count checks |

Curation можно вести параллельно с этапами 2–4, однако не тратить дорогой глубокий ресерч на десятки работ до доказательства renderer. Технический риск реализации сначала снижает этап 4; реальные токены/лимиты калибруем уже на одном проекте, не на десятках synthetic runs.

Три human gates сохраняются: стратегия; narrative + visual direction + representative frames; verified Figma + handoff. Человек утверждает реальные результаты, а не заполняет форму на каждом шаге.

### Минимальная проверка пользы

На знакомом завершённом проекте скрыть прежний готовый storyboard, дать исходники и сравнить с ручным baseline. Затем проверить incomplete-evidence и complex-workflow проекты. Замерить активное время специалиста, ожидание, rework, долю сохранённых сцен, удобство Figma, изменение после approval и resume. Отдельно сравнить baseline renderer и новый renderer при том же script, чтобы не приписать knowledge то, что исправила геометрия.

Blind pilot на 12 briefs × 3 experts и крупные retrieval tests остаются хорошей следующей ступенью, но не повод блокировать первый полезный внутренний pilot. Public effectiveness claims требуют более сильной проверки; внутренний pilot не называется statistically proven release.

## 7. Изменения файлов поверх прежнего плана

| Файлы | Доработка |
|---|---|
| `maintenance.py`, `scripts/build_release.py`, `.gitignore` | Protected INBOX/projects, один inventory, safe extract/verify/update/rollback; clean release packaging |
| `core/defaults/`, `core/release-policy.json` | Factory templates/config вне пользовательских директорий; строгое описание managed files |
| `tests/test_maintenance.py`, новые release/security fixtures | Canary preservation, malicious archive/path cases, interrupted update/recovery, clean install, no private leakage |
| `validation.py`, `orchestrator.py`, `cli.py`, `workspace.py`, schemas | Contract enforcement, gate digests, migrations, prerequisite/status separation |
| `core/src/saas_creative_director/context.py`, `usage.py` | Bounded context/observable events; не выдавать их за provider-wide billing controller |
| `core/schemas/{execution-policy,usage-event,checkpoint}.schema.json` | Quotas, sources of usage values, resumable work; fields unknown честно null |
| `core/defaults/execution-policy.json`, `config/local.example.json` | Standard preset, subscription preference, no auto billing/model escalation; пользовательские настройки не перезаписывать |
| Skills/adapters/CLAUDE.md | Lazy loading, compact outputs, stop/retry logic, untrusted-input rules, natural-language approvals |
| `figma.py`, `layout.py`, plugin source/UI/dist, manifest schemas | Deterministic recipes, typed nodes, visible notes, import ID/revisions/readback and input limits |
| `docs/{COSTS,SECURITY,FIGMA_WORKFLOW,DATA_HANDLING}.md`, русские quickstart/update guides | Оплата/лимиты, реальная граница безопасности, supported runtime и Figma path |
| `evals/usage/`, `evals/security/`, `evals/handoff/` | Cost-quality regression, injection tests, editing tasks; исторические результаты не переписывать |
| `pyproject.toml`, release workflow, compatibility | Если jsonschema нужен runtime, перенести из dev-only dependency в runtime или упаковать; тестировать поддерживаемую установку |

Перечисленные CLI-команды, схемы, библиотеки и проверки реализованы в рабочем дереве. Названия контрактов нормализованы; перед стабильным выпуском остаются живая проверка Figma и blind A/B пилот.

## 8. Что сознательно откладываем

Собственный API billing runner, vector DB, fully autonomous crawl всех студий, video generation, automatic animatic, сложный merge human edits, multi-user approval server, автоматические recurring background researches, отдельные installers под все платформы сразу и две независимые Figma integrations.

Для no-code обслуживания сначала выбрать и доказать один supported desktop path: готовая упаковка runtime/launcher или проверенная доставка через Claude plugin. Markdown plugin не считается решением runtime автоматически. Критерий — запуск и обновление на чистой машине без ручного управления dependencies, а не название технологии.

## 9. Переход к GPT-5.6

Предлагается GPT-5.6 Sol. Официальный model page определяет `gpt-5.6` alias как Sol; medium — разумная стартовая настройка, а не доказанная самая дешёвая на нашем проекте. High использовать на ограниченных сложных изменениях с измерением времени/повторов. API-цены OpenAI не переводить в расход Claude Pro/Max. [GPT-5.6 Sol](https://developers.openai.com/api/docs/models/gpt-5.6-sol)

Реализацию начинать с этапа 1 отдельными небольшими изменениями. В следующую рабочую сессию передать краткий START_DEVELOPMENT_5_6 + актуальное дерево/изменения, а подробные исследования читать по мере необходимости. Не отправлять весь архив разговора всем агентам.

Разработка выполнена с привлечением специализированных GPT-5.6 Sol агентов и итоговым интеграционным аудитом. Настройки Claude billing и live Figma не менялись; это по-прежнему отдельные пользовательские поверхности.


## 10. Инструкция для друга и публикация в Git

Исследовательский [черновик инструкции](FRIEND_UPDATE_GUIDE_DRAFT.md) перенесён в готовую пользовательскую инструкцию `docs/ru/UPDATING.md`. Она связана с START_HERE, README и release notes и должна публиковаться в том же Git-репозитории вместе с релизом.

Инструкция покрывает проверку версии, changelog, backup, совместимость и migration, безопасное обновление, прежний проект, Figma plugin, ошибку, rollback и конфиденциальный диагностический отчёт. Перед стабильным релизом остаётся добавить tested version и реальные screenshots после проверки на чистой установке и знакомом.

Документы и реализация сохранены локально. Публичный push и стабильный выпуск выполняются после живых проверок.

## Приложения аудита

[Токены и кредиты](token-economics-review.md), [безопасность](security-review.md), [Figma эффективность](figma-efficiency-review.md). Предварительные численные бюджеты в записках — альтернативы; итоговые scope и quotas задаёт MASTER_PLAN.
