# Start here

SaaS Creative Director is a versioned pre-production workspace, not a prompt bundle. It researches and plans an evidence-backed SaaS video through editable Figma wireframes. It stops before final illustration, animation, and video generation.

## Install

```bash
git clone <your-github-repository-url> saas-creative-director
cd saas-creative-director
./scd install
```

The installer checks Python and creates protected local areas. Then create a project:

```bash
./scd init projects/acme --name "Acme"
```

Put the client brief, screenshots, exports, and notes into `projects/acme/inputs/`. Open the repository in Claude Code and say:

> Start the SaaS Creative Director workflow for `projects/acme`. Run status, use the skill for the current stage, cite every strategic claim through the evidence registry, validate the artifacts, and stop at each approval gate.

## Update and recover

```bash
./scd update
./scd health-check
./scd rollback
```

An update replaces only the allowlisted product files. It does not replace `config/`, `overrides/`, `knowledge/custom/`, or `projects/`. A backup is created before every update and rollback.

Read [`docs/INSTALLATION.md`](docs/INSTALLATION.md) for first setup and [`docs/UPGRADING.md`](docs/UPGRADING.md) before changing major versions.

