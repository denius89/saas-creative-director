<p align="center">
  <a href="../../README.md">English</a> ·
  <a href="../../START_HERE.md">Начать без терминала</a> ·
  <a href="../../examples/ledgerly/README.md">Пример Ledgerly</a>
</p>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="../assets/readme/hero-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="../assets/readme/hero-light.svg">
  <img alt="SaaS Creative Director превращает факты о продукте в стратегию, motion direction, storyboard и редактируемые Figma-wireframes" src="../assets/readme/hero-light.svg">
</picture>

# SaaS Creative Director

**От фактов о продукте — к storyboard, готовому к производству.**

Система креативного препродакшена для SaaS-видео превращает бриф, материалы продукта, исследование рынка и визуальные референсы в согласованное креативное направление, таймированный storyboard, редактируемые Figma-wireframes и понятную передачу в продакшен.

Система готовит решения и материалы. Команда сохраняет контроль над вкусом, ремеслом и финальным роликом.

> **Статус Preview:** контракты, проверки, безопасное обновление, пример проекта и детерминированный Figma-импортёр покрыты автоматическими тестами. Живая проверка Figma canvas и первый слепой тест визуальной современности остаются критериями стабильного релиза.

## Что получает команда

| Результат | Что это даёт |
|---|---|
| **Стратегия на основе источников** | Подтверждённые факты, поддержанные интерпретации и гипотезы не смешиваются. |
| **Актуальное motion direction** | Датированная база знаний, визуальные паттерны и условные anti-pattern проверки помогают избежать устаревшей подачи. |
| **Референсы для конкретной сцены** | Референс подбирается под коммуникационный механизм без копирования стиля студии. |
| **Таймированный storyboard** | У каждой сцены есть задача, сообщение, состояния, события, переходы и связь с доказательствами. |
| **Редактируемые Figma-wireframes** | Локальный импортёр создаёт native-слои, стабильные IDs, видимые комментарии и безопасные новые ревизии. |
| **Передача в продакшен** | Visual QA показывает blockers, отсутствующие assets, зафиксированные решения и зоны творческой свободы. |

## Как устроен процесс

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="../assets/readme/pipeline-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="../assets/readme/pipeline-light.svg">
  <img alt="Пять этапов от материалов продукта до production handoff и три обязательных человеческих согласования" src="../assets/readme/pipeline-light.svg">
</picture>

Один оркестратор подключает нужные skills по этапам. Человек утверждает стратегию, креативное направление и готовность к продакшену. После паузы работа продолжается с сохранённого checkpoint, не повторяя весь проект.

## Посмотреть готовый пример

**Ledgerly** — вымышленный SaaS-проект без клиентских данных. Можно последовательно открыть реальные артефакты:

- [video strategy](../../examples/ledgerly/artifacts/video-strategy.json);
- [narrative](../../examples/ledgerly/artifacts/narrative.json);
- [motion direction](../../examples/ledgerly/artifacts/motion-direction.json);
- [storyboard](../../examples/ledgerly/artifacts/storyboard.json);
- [Figma manifest](../../examples/ledgerly/artifacts/figma-manifest.json);
- [Visual QA](../../examples/ledgerly/reviews/visual-qa.json) и [production review](../../examples/ledgerly/reviews/production-review.md).

Иллюстрации на странице объясняют проверенный процесс и не выдаются за скриншоты живой Figma. Настоящие canvas exports будут добавлены после прохождения [чек-листа живой проверки](../FIGMA_LIVE_VERIFICATION.md).

## Начать за пять минут

1. Скачайте репозиторий как ZIP и распакуйте его.
2. Откройте папку в Claude Code.
3. Перенесите brief, PDF, скриншоты и заметки клиента в `INBOX/`.
4. Напишите Claude:

   > Начни новый проект. Материалы клиента лежат в INBOX. Веди меня по одному решению за раз на русском языке.

Python, терминал, npm и ручное редактирование JSON для обычной работы не нужны. Полная инструкция находится в [START_HERE.md](../../START_HERE.md), а готовый сценарий теста — в [инструкции для знакомого](../QUICK_TEST_FOR_FRIEND.md).

## Контроль и безопасность

- Значимые утверждения связаны с evidence IDs, а гипотеза не превращается в факт без основания.
- Три согласования привязаны к конкретным ревизиям материалов.
- Система использует компактные context packets, кеширование и точечные исправления вместо постоянного повторного анализа.
- Usage credits, API-биллинг и автопополнение не включаются системой.
- `INBOX`, клиентские проекты, локальные настройки и собственная база знаний не входят в обновления продукта.

Подробности: [обработка данных](../DATA_HANDLING.md), [безопасность](../SECURITY.md), [расход Claude и кредиты](CLAUDE_CREDITS.md), [безопасное обновление](UPDATING.md).

## Figma

Готовый локальный импортёр создаёт native frames, текст, UI-карточки, строки, connectors и видимые handoff-комментарии. Он проверяет входные данные, запоминает результат операции, обнаруживает ручные визуальные изменения и не перезаписывает изменённый board незаметно.

Это редактируемый production wireframe, а не финальная иллюстрация или анимация. Установка описана в [русской инструкции по Figma-плагину](../../figma-plugin/README_RU.md).

## Документация

- [Быстрый старт](../../START_HERE.md)
- [Первый реальный проект](ONBOARDING.md)
- [Пример Ledgerly](../../examples/ledgerly/README.md)
- [Motion Intelligence](../MOTION_INTELLIGENCE.md)
- [Архитектура](../ARCHITECTURE.md)
- [Обновление и откат](UPDATING.md)
- [Расход Claude и кредиты](CLAUDE_CREDITS.md)
- [Changelog](../../CHANGELOG.md)

## Граница продукта

SaaS Creative Director заканчивает работу на согласованном creative direction, storyboard, редактируемых Figma-wireframes, Visual QA и production handoff. Финальная иллюстрация, анимация, звук, compositing и режиссёрский вкус остаются частью производства.

Лицензия: [MIT](../../LICENSE).
