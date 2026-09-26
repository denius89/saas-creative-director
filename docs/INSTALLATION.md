# Installation

## Requirements

- macOS or Linux;
- Python 3.11 or newer;
- Git;
- Claude Code for the guided skill workflow;
- Figma Desktop plus the development plugin only when creating wireframes.

## Recommended installation

```bash
git clone https://github.com/denius89/saas-creative-director.git
cd saas-creative-director
./scd install
```

`install` is idempotent. It creates `config/local.json` only when absent, creates protected directories, records installed state in `.scd/state.json`, and runs the health check. It never modifies an existing local config, override, custom-knowledge file, or project.

For CLI autocomplete or use outside the repository, optionally install the Python entry point:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

The repository-local `./scd` command remains the canonical maintenance command because it can repair an environment without relying on an installed package.

## Configure updates

If the clone has a GitHub `origin`, no update configuration is required. Otherwise copy the `owner/repository` name into `github_repository` in `config/local.json`.

## Verify

```bash
./scd health-check
./scripts/test.sh
./scd validate examples/ledgerly
```

All health-check lines should report `PASS`.

## Data boundary

| Path | Owner | Updated automatically? |
|---|---|---|
| `core/` | product | yes |
| `.claude/skills/` | product adapters | yes |
| `docs/`, `evals/`, `figma-plugin/`, `examples/` | product | yes |
| `config/` | user | no |
| `overrides/` | user | no |
| `knowledge/custom/` | user | no |
| `projects/` | user/client | no |

Never put client data in `core/` or `examples/`. Never customize `core/skills/*/SKILL.md`; use the matching file in `overrides/`.
