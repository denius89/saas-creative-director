# README visual assets

These assets explain the product and do not represent a live Figma canvas capture.

| Asset | Source | Refresh when |
|---|---|---|
| `hero-light.svg`, `hero-dark.svg` | Product thesis and the Ledgerly artifact sequence | The product boundary or primary handoff changes |
| `pipeline-light.svg`, `pipeline-dark.svg` | `core/src/saas_creative_director/orchestrator.py` | Stage or approval-gate order changes |

Rules:

- keep meaningful text outside images in the root README;
- provide light and dark variants plus descriptive alt text;
- use no external scripts, fonts, or image references in SVG;
- do not use client data or imply that a diagram is a product screenshot;
- add real Figma exports only after `docs/FIGMA_LIVE_VERIFICATION.md` passes;
- keep the initial static README image payload below 1.2 MB.
