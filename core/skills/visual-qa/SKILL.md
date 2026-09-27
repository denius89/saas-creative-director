---
name: visual-qa
description: Inspect rendered storyboard contact sheets, state strips, and Figma readback for hierarchy, product truth, continuity, conditional anti-patterns, editability, and handoff blockers. Use after representative frames and after final Figma import.
---

# Visual QA

Read the approved storyboard and motion-direction revisions, the compact renderer report, and rendered contact sheet. When a scene contains causal or timed action, also inspect its state strip or animatic. Inspect detail crops only for scenes with legibility or fidelity concerns. Do not load the complete Figma document tree.

Create `reviews/visual-qa.json` with localized findings: artifact revision, scene/object, criterion, observed evidence, severity, suggested repair, inspector, and status. Check:

- one readable focal hierarchy and realistic attention order;
- product facts, UI states, claims, and disclosed simplifications;
- temporal readability: setup, action, transformation, and result appear in causal order rather than simultaneously;
- panel transitions, persistent-object identity, and the absence of premature result states;
- panel economy: enough drawings to explain the mechanism without turning every microinteraction into a panel;
- scene-to-scene escalation, variation for a reason, holds, and transition anchors;
- conditional anti-pattern triggers and approved exceptions;
- text overflow, missing fonts/assets, raster versus native editability;
- stable IDs, readback agreement, duplicate-free import, and human-edit conflicts.

Treat a causal process flattened into one presentation-like board as a blocker when production would have to invent the order. An intentional comparison or summary is not a failure when it is labelled and does not replace the causal sequence. Static frames can support composition and continuity findings; report timing, rhythm, or hold quality as unverified unless a timed animatic was reviewed.

Do one normal repair pass and at most two targeted Figma correction cycles. Re-render only changed scenes and genuine adjacency dependencies. Unresolved issues become explicit blockers; do not keep self-critiquing, weaken evidence requirements, or approve the production gate.
