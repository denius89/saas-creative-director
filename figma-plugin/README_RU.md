# Импорт wireframes в Figma — без кода и npm

1. Попросите Claude: «Подготовь Figma manifest».
2. В Figma Desktop откройте **Plugins → Development → Import plugin from manifest…**.
3. Выберите файл `figma-plugin/manifest.json` из скачанной папки проекта.
4. Запустите плагин **SaaS Creative Director Importer**.
5. Выберите созданный Claude файл `projects/<клиент>/artifacts/figma-manifest.json`.

Плагин создаст редактируемые страницы, frames, текстовые слои, UI placeholders и annotations. Ничего собирать или устанавливать через терминал не нужно.

Плагин создаёт нейтральные production wireframes, а не финальный дизайн. Стиль иллюстраций, фирменная палитра, texture, lighting и финальный motion остаются творческому специалисту.

