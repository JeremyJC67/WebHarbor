# BabyCenter grading contracts

Run through `agent_demo/eval_judge.py --run_dir ABSOLUTE_RUN --verifier True`.
The run must contain `trajectory.json`, real PNG screenshots, `initial.db` and
`after.db`. The verifier never falls back to mutable live state.

The revised tasks explicitly request a JSON final answer. Field names carry the
entity/age relationship; numeric fields contain numbers, not sentences with
incidental matching digits. Date strings accept ISO and written dates, ranges
accept a two-number array or equivalent `18–22 weeks` notation, and short text
facts accept common equivalent phrasing. Ground truth stays in reviewer-only
`answers.py`, not in the task file. Duplicate JSON keys, extra fields, missing
fields, wrong types, contradictions and wrong facts fail closed.

The verifier checks three independent layers: the answer contract, navigation
to the requested source/filter pages, and the exact database delta. It does not
require a minimum number of steps or force arbitrary ordering between sources.
Clicks can use the bundled agent's numeric `index` payload. Selectors and
reviewer-invented button labels are never required.

State tasks must end on `/account` with the correct email in final browser
observation evidence. The bundled agent writes `observed_text` on each step and
`final_observed_text` / `final_url` at completion. A browser QA recorder can supply
the same final visible text. This is observed UI evidence, not agent reasoning
or its final answer. Registration additionally validates the actual stored
password hash. Every unrelated row and field must remain unchanged.

Short-task revisions add comparisons or saved-item management for IDs
0, 1, 2, 4, 5, 6, 8, 9 and 11. All 15 tasks now use explicit answer fields.
Sourced guides are sparse: account/calculator pages distinguish completed
gestational weeks from the nearest linked checkpoint, as of 2026-05-29.

The seed migration runs at fetch/build time, never during normal HTTP startup.
HF PR #78 remains a release dependency until merged and repinned; the immutable
candidate revision permits local validation but is not a merged release asset.
