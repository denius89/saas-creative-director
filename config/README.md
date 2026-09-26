# Configuration

Run `./scd install` to create `config/local.json`. That file is ignored by Git and is never touched by updates. Keep machine-, team-, and user-specific settings there.

`local.example.json` documents supported fields and may change with core releases. When a release adds a setting, merge it into your local file only if needed; migrations never replace local configuration.

