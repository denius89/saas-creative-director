# Onboarding a client project

## 1. Initialize

```bash
./scd init projects/client-slug --name "Client Name"
```

Put supplied material in `projects/client-slug/inputs/`. Keep links in the source registry even when a source cannot be copied locally.

## 2. Start Claude

Open the repository in Claude Code and use:

> Start the SaaS Creative Director workflow for `projects/client-slug`. First run `./scd status`. Use the indicated skill, register sources before citing them, preserve CONFIRMED/SUPPORTED/HYPOTHESIS labels, run validation after editing artifacts, and stop at each approval gate. Do not generate a final video.

## 3. Work stage by stage

After a stage artifact is reviewed:

```bash
./scd validate projects/client-slug
./scd advance projects/client-slug
```

At a gate, record an actual human decision:

```bash
./scd approve projects/client-slug strategy --by "Name" --notes "Selected option A"
./scd advance projects/client-slug
```

The other gate names are `creative_direction` and `production`.

## 4. Customize safely

Create `overrides/<skill-name>.md`; do not change `core/skills/`. For example:

```markdown
# Local video strategy defaults

- Default paid-social recommendations to 20–30 seconds unless evidence supports more.
- Include our internal review code beside each strategy option.
```

Put reusable private vocabulary or production conventions in `knowledge/custom/`. Keep client truth inside that client's project.

## 5. Build Figma wireframes

```bash
./scd figma-manifest projects/client-slug --output projects/client-slug/artifacts/figma-manifest.json
```

Build the development plugin in `figma-plugin/`, import it into Figma Desktop, and select the generated manifest. Review native frames against the storyboard before requesting production approval.

## 6. Definition of done

- strategy and creative direction are explicitly approved;
- every external claim links to evidence;
- total timing is valid;
- every frame is editable and named;
- hierarchy, copy, UI, attention, motion, and transition intent are legible;
- locked decisions and creative freedom are distinct;
- blocking production-review findings are closed.

