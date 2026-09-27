# Motion Intelligence: что подтверждают источники

Проверено 27 сентября 2026. Этот документ дополняет [план A–J](PLAN.md). Ниже разделены опубликованные процессы студий, собственно визуальные наблюдения, исследовательские данные и наши проектные выводы.

## 1. Современный язык 2025–2026: что можно утверждать

Нет достаточных оснований свести contemporary SaaS motion к одному стилю. В изученных первичных источниках сосуществуют product UI, data transformation, выразительная типографика, dark treatments, glass, 2D/3D и filmed/founder launch formats. Это подтверждает разнообразие подходов в доступных портфолио; не устанавливает их распространённость на всём рынке или дату каждой работы.

Практическая рекомендация — выбирать визуальный язык по задаче:

| Контекст | Рекомендуемая грамматика для проверки | Что нельзя принять за универсальный тренд |
|---|---|---|
| Feature/product demo | Показать узнаваемый UI, действие и изменение результата; усиливать читаемость выбранной части | Обязательные 70% экранного времени с UI |
| AI workflow | Input → действие системы → проверяемый output → human control/exception | Неоновые поля и «магия» как доказательство возможностей |
| Devtools/infrastructure | Схема объектов, потоков и состояний, затем точка контакта с продуктом | Требование показывать dashboard, которого у продукта нет |
| Launch/brand | Контраст ритма, type accents, продуктовый hero, footage при необходимости | Запрет типографики, 3D или эмоциональной метафоры |
| Dense data UI | Context/detail, selective disclosure, held proof, semantic continuity | Скриншот всего экрана без адаптации к времени просмотра |

Это synthesis/recommendation, а не измеренная taxonomy трендов. Для каждой рекомендации production system должна сохранять применимость, source observations, counterexamples и дату review.

### Проверка прежнего ADVIDS аргумента

Отчёт опубликован 12 сентября 2026, обновлён 14 сентября: 100 видео 92 компаний, 900 sampled frames, 1 061 segments; выборка Q1 — 60, апрель–август — 40. Сам источник сообщает об отсутствии viewer data. В таблицах различаются screencast format (22/60 → 25/40) и captured-screen build (11/60 → 12/40). Смешивать их нельзя. Данные не были независимо пересчитаны в этом исследовании: linked dataset не удалось получить. [Оригинальный отчёт ADVIDS](https://advids.co/blog/ui-animation-motion-design-trends)

Выборка поставщика услуг, неслучайный отбор, разные временные окна и отсутствие оценки зрителями не позволяют заключить, что 3D «устарел», light UI повышает конверсию или выбранный подход — стандарт всего SaaS. Отчёт полезен как источник гипотез для curation. Он также не сравнивает 2025 с 2026.

Для датированного расширения seed queue подходит официальный [релиз Notion 3.0 от 18 сентября 2025](https://www.notion.com/blog/introducing-notion-3-0): подтверждена дата страницы и заявленный multi-step agent workflow. Motion grammar видео на основе текста этой страницы не размечалась; дата и claim продукта не заменяют просмотра ролика. При формировании корпуса нужно отдельно фиксировать дату оригинального медиа и возможную замену assets на странице.

**Ограничение:** полноценная timecoded сравнительная выборка 2025/2026 в этой исследовательской задаче не построена. Поэтому итог — обоснованная архитектура для её формирования и использования, а не завершённый эмпирический атлас всех актуальных стилей.

## 2. Tier A: источники, наблюдения и seed cases

| Студия | Что проверено | Кандидаты для библиотеки | Ограничение |
|---|---|---|---|
| Anyway | Опубликованный workflow; Jigcar case description; визуально просмотрены stills Jigcar | Jigcar, Liveflow, Lovable Aesthetic Design / 2.0 / x Google, Synaps, Lindy, incident.io | Проектные даты не подтверждены; motion timing не просмотрен |
| Flash Motion | Стадии работы и portfolio metadata | Bolt Forge Launch, Bolt Slides V2, Bleu, NextSlide, Draftboard, Timeliner | Названия/длительности — данные страницы; не frame-level analysis |
| Timeframe | Запрошенный portfolio дал 403; проверены связанные studio-owned профили | Jockey/TwelveLabs, AI SaaS teaser, product demo launch | Нет доступа к полному первичному portfolio в этой сессии; не выдавать альтернативный одноимённый сайт за оригинальный |
| Skale | Portfolio и ссылки на launch posts | Cognition Devin Voice, BrowserBase, Replit, Adaline, Poke, Wonder, Contra | Формат/claims — описания студии; таймкоды и даты не размечены |

Первичные точки входа: [Anyway](https://www.anywaystudio.com/#our-works-section), [Timeframe](https://timeframe.myportfolio.com/), [Flash Motion](https://flashmotion.io/portfolio), [Skale](https://skale.solutions/portfolio). Tier A задаёт приоритет поиска, не автоматически gold label.

### Anyway: существенный workflow lesson

На сайте discovery и script отделены от style-frame design, storyboard и animation/audio. В Jigcar студия описывает варианты treatment, выбор направления, упрощение/укрупнение интерфейса для видео и согласование продуктовых деталей. [Процесс Anyway](https://www.anywaystudio.com/), [Jigcar case](https://www.anywaystudio.com/case-studies/jigcar)

При визуальном просмотре Jigcar before/after still замечены: исходная светлая плотная таблица и treatment с тёмным полем, укрупнённой метрикой, карточкой автомобиля и зелёными столбцами. На другом still изолирована строка со статусом доставки среди приглушённых соседних строк. Это поддерживает принцип selective emphasis. Это не наблюдение длительности, easing или переходов.

Liveflow описывает glass-inspired treatment, реконструкцию графиков в Figma ради читаемости и узнаваемости интерфейса. Сам кейс — контрпример абсолютному запрету glassmorphism. [Liveflow case, URL написан у студии как lifeflow](https://www.anywaystudio.com/case-studies/lifeflow)

Наш вывод: сохранить product semantics, усилить иерархию под формат просмотра, предложить ограниченное число treatments до полного storyboard. Финальные styling decisions человека остаются отдельным слоем.

### Flash Motion: direction и review до дорогой анимации

Студия публикует цепочку discovery → creative direction → script → detailed Figma storyboard → animation с timestamped review → handoff исходников. У разных проектов в portfolio различаются motion-led/founder-led formats и durations. [Flash Motion process](https://flashmotion.io/), [portfolio](https://flashmotion.io/portfolio)

Наш вывод: direction contract должен включать pace, audio intent и format; Figma storyboard — согласуемый production artifact. Человек должен понимать, что утверждает, прежде чем система размножит решение на весь ролик. Публикуемый процесс не является доказательством эффективности отдельного визуального приёма.

### Timeframe и Skale: не сужать продукт до dashboard video

Связанный [Timeframe LinkedIn](https://www.linkedin.com/company/timeframeoff/) указывает на запрошенный portfolio. [Studio-owned Vimeo teaser](https://vimeo.com/1156796803) описывает сочетание музыки, типографики, 2D/3D и workflows; [Dribbble project](https://dribbble.com/shots/27303490-SaaS-Product-Demo-Launch-Video) — UI/storytelling. Это first-party descriptions; слова premium/modern не являются нашей оценкой качества.

Skale включает на странице filmed/launch work наряду с продуктовой тематикой. [Skale portfolio](https://skale.solutions/portfolio) Поэтому library должна различать жанры и production contexts. View counts и attributed growth на портфолио не использовать как causal quality label.

## 3. Storyboard / previs: какие идеи стоит перенять

| Инструмент | Возможности по официальному источнику | Польза для нашего MVP | Решение |
|---|---|---|---|
| Boords | Timed boards, audio, comments, versions/approvals, exports | Storyboard — версионированная последовательность с review state | Перенять контракт, не интегрировать сервис сейчас |
| Toon Boom Storyboard Pro | Timeline, drawing/layout, camera movement, sound | Изменение состояния и камеры нужно планировать во времени | State strips и motion notes сейчас; integration позже |
| Wonder Unit Storyboarder | Sketch boards, action/dialogue/timing, editing/export | Низкая детализация может точно передавать замысел | Не путать polished image с качеством pre-production |
| Figma Weave | Повторно используемые node workflows, style references, генерация последовательности | Coherence может обеспечиваться pipeline, а не отдельными prompts | Optional exploration; не dependency MVP |
| Figma native canvas | Frames/text/vector/components/layout | Конечный production blueprint можно править | Основной editable output |

Источники: [Boords concepts](https://boords.com/docs/concepts), [Boords overview](https://boords.com/about), [Toon Boom](https://shop.toonboom.com/en/products/storyboard-pro), [Storyboarder](https://wonderunit.com/storyboarder/), [Figma Weave](https://www.figma.com/solutions/ai-storyboard-generator-weave/).

Эти страницы описывают capabilities; инструментальная availability не доказывает качество SaaS storyboard. Storyboarder имеет старую публичную страницу — актуальный темп разработки не проверен. Weave генерация последовательных изображений не означает автоматическое получение нативных редактируемых UI nodes.

## 4. Figma MCP: актуальные возможности и практические пределы

На дату проверки официальный tool index включает `use_figma` для записи/редактирования/инспекции, `create_new_file`, `upload_assets`, design-system tools и screenshots. Поэтому тезис «официальный MCP только читает» уже неверен. Но exposed tools, права и возможности отличаются по клиенту и окружению; перед использованием нужен capability probe. [Figma MCP tools](https://developers.figma.com/docs/figma-mcp-server/tools-and-prompts/)

`generate_figma_design` для переноса веб-интерфейса — не semantic storyboard planner. `get_motion_context` читает motion context Figma nodes, а не извлекает таймкоды из произвольного reference movie. Обычный REST API не следует проектировать как универсальный endpoint создания любых canvas nodes. [Figma REST](https://developers.figma.com/docs/rest-api/), [file endpoints](https://developers.figma.com/docs/rest-api/file-endpoints/)

Предлагаем единый transport-independent scene graph и adapters:

1. **Базовый:** существующий development plugin, дополненный полноценным renderer.
2. **Опциональный:** текущий MCP transport, если нужные tools и права доступны.

Hosted `use_figma` helpers не переносить автоматически в обычный plugin: runtime contracts различаются. Ограничения seats/rate limits проверять в текущем account, не фиксировать случайные числа в core. [Access/rate limits](https://developers.figma.com/docs/figma-mcp-server/rate-limits-access/)

### Mapping и editability

- Native text/vector/frame/component — редактируемые элементы. Screenshot — raster внутри редактируемой рамки; внутренние кнопки не становятся editable.
- Загружать доступные fonts до создания/изменения текста, fallback записывать явно. Проверять long copy и локализацию. [Figma loadFontAsync](https://developers.figma.com/docs/plugins/api/properties/figma-loadfontasync/)
- Auto-layout применять внутри связанных UI groups. Абсолютные coordinates у shot canvas уместны; auto-layout всего киношного кадра не самоцель.
- Scene graph хранит stable object IDs, parent IDs, state IDs, roles, layout/crop/clipping, token refs, asset/component provenance, ownership и editability.
- Recipe задаёт constraints, а не чужую finished composition. Все unsupported primitives приводят к понятному error/explicit placeholder, не к молчаливому прямоугольнику.
- Текущий plugin manifest запрещает network access; asset handling должен использовать согласованный local-bytes/imported-assets путь либо явно пересмотренные network permissions.
- Reimport сопоставляет semantic ID + source revision. Неизменённый import не создаёт дубликатов; конфликт с human-owned layer сохраняет правку и сообщает о конфликте.
- Результат экспорта: node-ID map + screenshots + validation/readback report. Созданные пустые страницы Research/Handoff не означают, что handoff готов: их надо наполнить или явно связать с артефактами.

### Минимальный feasibility spike для следующего этапа

Три сцены: native UI crop, cause/result comparison, single-proof layout. В одной — entry/result/exit; в другой — длинный русский headline. Один native UI component и один raster asset с честной маркировкой. Проверить изменение tokens, missing font/asset report, второй import без duplicates, сохранение ручной правки и восстановление после частичного сбоя. Инспектировать реальный canvas и exported screenshots. Spike запланирован; в этой исследовательской задаче не выполнялся.

## 5. Как не перепутать знание с уверенностью

Публикации студий подтверждают, что студия описывает такой процесс. Просмотр кадра подтверждает композицию. Просмотр video interval подтверждает наблюдённое изменение во времени. Ни то, ни другое отдельно не доказывает рост продаж, «современность» в глазах целевой аудитории или превосходство нашего генератора.

Рабочая цепочка доказательств: проверенный source → ограниченное observation → интерпретация → derived pattern → конкретное решение проекта → rendered output → human evaluation. Только последняя часть показывает, помогает ли Motion Intelligence реальному дизайнеру. Для этого в [PLAN.md](PLAN.md) предусмотрены blind A/B, ablation и production editing tasks.
