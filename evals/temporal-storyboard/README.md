# Temporal storyboard regression

This regression tests a demonstrated failure mode: a sound causal idea becomes a presentation-like board that displays its consecutive states simultaneously.

Use `causal-saved-alert.json` as an input brief, not as a production storyboard schema. Generate the candidate with the same product facts and eight-second duration. Review the storyboard contact sheet first, then its timed animatic without showing the fixture's expected panel descriptions to the reviewer.

Pass when every required causal boundary is visually inspectable, semantic object continuity survives the selected-item transformation, the result follows its cause, and the sequence is understandable without long notes. The candidate may combine adjacent panels when the causal boundary remains unambiguous; six panels are a golden example, not a universal quota.

Fail on any blocking failure in the fixture. Record major failures separately. A static contact sheet can establish composition and continuity but cannot pass the timing requirement.

For a negative control, deliberately place the promise, item hero, saved card, notification controls, save button, and saved result in one large dashboard. Visual QA must report `ANTI-009` as a blocker. For an over-segmentation control, add separate panels for pointer travel, hover, press, release, and decorative glow without new information; Visual QA must report `ANTI-010` as a major finding.
