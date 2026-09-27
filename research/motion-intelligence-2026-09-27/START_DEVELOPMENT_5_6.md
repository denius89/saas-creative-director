# Старт разработки на GPT-5.6

Продолжи существующий SaaS Creative Director 0.6.0 по `MASTER_PLAN.md` в этой папке. Это новая точка входа; старый `IMPLEMENTATION_PROMPT.md` имеет более широкий scope и не должен автоматически запускать весь прежний план. Рабочая модель, предложенная пользователю: GPT-5.6 Sol. Настройки/модель меняет host; этот файл сам ничего не переключает.

Прочитай AGENTS.md, актуальное состояние Git, затем MASTER_PLAN и только относящиеся к текущему шагу материалы. Не загружай все research notes сразу. Не редактируй `sources/`. Пользователь продукта — непрограммист, Claude Desktop Code Local, подписка Pro/Max, русский интерфейс. Один orchestrator + composable skills. Финал — editable Figma pre-production, не видеоролик.

Первый development milestone — безопасность установки/обновления:

1. Защитить весь INBOX и все user/project folders; вынести заводские шаблоны в core. Проверить release builder на отсутствие private данных.
2. Строгий release inventory/manifest, safe bounded archive extraction, staging/compatibility, update lock/journal/recovery, rollback по transaction ID. Не выдавать self-contained checksum за publisher authenticity.
3. Проверить starter archive: config defaults и исполнимый supported runtime присутствуют; no-code пользователю не нужно вручную ставить Python/npm.
4. Meaningful tests на synthetic canaries, malicious archive fixtures, failures, repeat install/update и rollback. Не трогать настоящие проекты/кредиты/аккаунты для проверки.
5. Подготовить чистый, ограниченный diff и сообщить, что доказано, что осталось. Затем двигаться по этапам MASTER_PLAN, не смешивая все подсистемы в одну правку.

Далее: stage/schema/evidence validation и revision approvals; context packs/cache/checkpoints/ограничение повторов; три working Figma recipes через plugin, native UI/text, видимые notes, preflight/idempotency/readback; небольшая проверенная reference library и motion director/QA; один end-to-end пилот, затем три. Никаких автоматических покупок Usage credits, API-ключей или fan-out агентов по умолчанию. Подписочный процент и bill не выдумывать из оценки токенов.

Figma renderer детерминированный; модель задаёт смысл, не печатает заново весь node JS. Native versus raster editability обозначить. Ручные правки сохранять, conflicts явно показывать; новый draft revision предпочтительнее сложного merge. MCP adapter и vector database отложены.

Обязательная документация на Git: доработать `docs/ru/UPDATING.md` по `FRIEND_UPDATE_GUIDE_DRAFT.md`, связать из START_HERE/README/releases, проверить шаги и вставить реальные screenshots. Документировать проверку версии, backup, update, migration, rollback, Figma plugin и отсутствие изменений billing. Не публиковать обещания ещё не реализованного updater.

Каждый milestone заканчивается tests/реальной проверкой соответствующего результата и compact handoff: changed files, evidence, next action, unresolved risks. Не повторять полные документы в чате. Код/аккаунты/релиз не публиковать автоматически по одной только исследовательской задаче; работать в пределах новой пользовательской команды на разработку.
