# AccuWeather PR #98: local audit corrections

The September 16, 2026 corrections address all 13 findings from the GUI audit:
mobile header/flash and form layouts, menu/homepage destinations, radar legend,
overall AQI scale, forecast consistency, task wording, rubrics, deterministic
answer/state checks, navigation order, asset resolution and review documentation.

Task 8 now explicitly requests the selected alert types; task 17 explicitly asks
for the maximum temperature as well as its first hour and precipitation chance.
The verifier preserves exact database delta and catalog checks while rejecting
wrong units, city/value swaps, contradictions and false confirmations.

Validation completed locally:

- 20 fresh tasks completed through mouse/keyboard/scroll actions; all pass the
  official deterministic evaluator. 180 steps and 20 decoded GIFs are retained.
- 111 copied-evidence controls match expectations: 21 accepted, 90 rejected.
- 301 verifier tests and 5 asset pin tests pass, with no skips.
- Independent seed builds are byte identical within the local SQLite runtime;
  populated startup is a no-op and the forecast consistency checks pass.
- Full Docker build passes; all 29 sites are healthy and their homepages respond.
  AccuWeather runtime/seed hashes match after reset and restart. Forty files in
  the final image match the working checkout. The owned test container is stopped.

The build uses a scoped immutable asset pin for AccuWeather from HF PR #66
(`0a73c1c1ac2e47513389a8a1a67601f75c8c4150`), retaining the existing global pin for
the other sites. A later integration can consolidate this after validating the
merged dataset revision. No publication is part of these local corrections.

Local evidence: `.assets/reviews/pr98-fixes/REPORT.md`, `manifest.json`,
`task-00/` through `task-19/`, `controls/`, and build/reset logs. The original
`.assets/reviews/pr98-gui-audit/` is preserved. Preview: http://localhost:41024/;
report/GIF gallery: http://localhost:41199/. Preview account state is preserved.

Weather is synthetic and radar remains illustrative. Answer matching supports
documented prose/labels and tested paraphrases; it is not a general language
reasoner. The secondary LLM judge was not run because its API/model configuration
is absent. These checks are regression evidence, not a statistical grading error rate.
