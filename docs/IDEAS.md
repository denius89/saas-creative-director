# Product ideas

Ideas in this file are intentionally not part of the current skill contract. Move an item into implementation only after its interaction design and token cost have been reviewed.

## Guided designer mode

**Status:** proposed

Give a non-technical designer a calm, step-by-step experience while the main orchestrator handles project state and technical work in the background.

Proposed behavior:

- greet once when a new project starts and explain the expected outcome in two sentences;
- on later sessions, resume from the saved stage without repeating the introduction;
- show only the current stage, what the skill will do, one decision needed from the designer, and the next milestone;
- ask one question at a time, except when two choices cannot be decided independently;
- offer two or three creative options with a recommendation and a short tradeoff at approval gates;
- hide commands, JSON, repository structure, schemas, and token-management details during ordinary use;
- perform routine research, file updates, validation, and checkpointing without asking the designer to operate developer tools;
- explain results by meaning before naming artifacts;
- use a compact progress line instead of repeating the full workflow on every turn;
- when the included Claude allowance is exhausted, save a checkpoint and provide one plain-language resume instruction.

Example turn:

> **Сейчас:** определяем направление ролика.  
> **Я сделаю:** соберу три направления из утверждённой стратегии и проверенных референсов.  
> **От вас:** выбрать одно направление; я отмечу рекомендуемый вариант и его компромисс.  
> **Дальше:** сценарная структура и storyboard.

Before implementation, validate the behavior with four scenarios: a new project, a resumed project, a creative choice at a gate, and a usage-limit checkpoint. Prefer prompt-level behavior over new schema fields unless testing shows that the existing project stage and artifacts cannot reliably prevent repeated greetings.
