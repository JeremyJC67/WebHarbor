# Walmart Careers — grading contract

One deterministic verifier per task in `sites/walmart_careers/tasks.jsonl`, plus
the shared helpers in `verify_lib.py`. Each task row points here through
`verifier_path`; the matching `judge_rubric` in that row drives the LLM judge.
The verifiers make **zero LLM calls** — a verdict never depends on a key or a
model, so `eval_judge.py --verifier True` works offline.

## Layout

```
verify_lib.py     shared utilities: trajectory + URL gates, answer matchers,
                  SQLite state diffing, the Judge harness, CLI parsing
verify_0.py …     one per task, ground truth HARDCODED inside
verify_19.py
tests/            unittest suite: synthetic SQLite snapshots + hand-written
                  trajectories, one file per verifier plus the library
```

Ground truth never lives in `tasks.jsonl` — the agent reads that file. Rubrics
name the pages and the kind of fact required, never an answer value.

## Running one

```bash
cd agent_demo
uv run python ../sites/walmart_careers/verify/verify_2.py \
    --run_dir /abs/path/runs/2 \
    [--initial_db <seed.db> --after_db <live.db>] [--container wh-review]
```

Or through the single evaluation entry point (this is how the benchmark runs it):

```bash
uv run python agent_demo/eval_judge.py --run_dir /abs/path/runs/2 --verifier True
```

Output is `{task_id, pass, reason, evidence[]}` on stdout; exit 0 = PASS,
1 = FAIL. `reason` is the **first failing check name** (or
`all checks passed`); `evidence[]` lists every check with `[PASS]`/`[FAIL]`.
Infrastructure problems (missing trajectory, missing snapshots, a query error)
fail closed with `"infra_error": true`.

Pass `--run_dir` as an **absolute path**: `eval_judge.py` re-runs the verifier
with `cwd=agent_demo/`, so a relative run dir would resolve against the wrong
directory.

## Snapshot discovery

Every verifier needs a before/after pair of SQLite databases:

1. `--initial_db` / `--after_db` if given explicitly;
2. otherwise `<run_dir>/initial.db` and `<run_dir>/after.db` if present
   (the run-signature writer and the real-run procedure put them there);
3. otherwise `docker cp` from the container named by `--container`, defaulting
   to `$WH_CONTAINER` or `wh-review`:
   `/opt/WebSyn/walmart_careers/instance_seed/walmart_careers.db` (initial)
   and `/opt/WebSyn/walmart_careers/instance/walmart_careers.db` (after).

If neither snapshot can be obtained the verifier fails closed
(`database_unavailable`). The seed used for review has md5
`b57631080969fe151e1717dbef3dd372`.

## What the verifiers check, in order

1. **Identity** — `task_id` matches and `final_answer` is non-empty
   (`trajectory_task_matches`, `final_answer_nonempty`).
2. **Navigation gates** — every URL the task mandates appears in
   `trajectory_urls` (start_url plus each step's url), on a loopback host with
   **any** port (runs hit 41019 while tasks say 40019). Detail-page gates are
   exact `/jobs/<id>` paths, never `/jobs/<id>/apply`; results gates parse the
   query string (`q`/`searchQuery`/`loc` as substrings, facets as exact
   `getlist` values). Sign-in is `/login` visited plus the last typed email.
   Every requisition-ID task gates on the detail page because result-card
   hrefs expose IDs; the paired fact (street, count, window, chip, degree) is
   detail-only.
3. **Answer match** — tolerant matchers: requisition IDs (case, en/em dashes),
   streets (Rd/Road, SE/Southeast, optional suffix), shift windows (`6 pm`,
   `6:00 PM`, `6:00 p.m.`, `18:00`), counts (bare integer after masking IDs,
   times, money, zips, street and store numbers; word forms), store numbers,
   hashtags, confirmation numbers. Comparison tasks (8, 9, 10, 18) also fail
   when the losing posting is reported instead of the winner.
4. **Database after-state** — stateful tasks diff `initial.db` vs `after.db`:
   set equality on the user's saved roles (an extra or missing save fails),
   exactly one new `applications` row with the right job / user / phone, the
   answer must contain **that row's** `confirmation_no` (never a hardcoded
   string — tasks 13 and 17 both yield `WMC-000005` from a fresh reset), a new
   `users` row for task 14, David's `city`/`state` for task 15.
5. **Read-only invariance** — tasks 0–10, 16 and 18 FAIL on any change to
   `users`, `saved_jobs` or `applications` (`read_only_<table>_unchanged`).

## Validation

### LLM-free matrix

Produced by `scripts_dev/run_signature.py` (Playwright run-signature writer in the
`agent.py` format) and graded through `eval_judge.py --verifier True` against the
container `wh-review` (`-p 8201:8101 -p 41019:40019`). No LLM call anywhere.

| run kind | tasks | expected | result |
|---|---|---|---|
| No-op (homepage only, empty answer, after = seed) | all 20 | FAIL on `final_answer_nonempty` | 20/20 |
| Scripted genuine (real UI path, real DB after-state) | all 20 | PASS | 20/20 |
| Scripted shortcut (right answer, trajectory restricted to `/`, `/results`, `/login`) | 0–10, 13, 15–19 | FAIL on a navigation gate | 17/17 |
| Wrong answer (genuine trajectory, near-miss answer) | 0–10, 13, 15–19 | FAIL on the answer check | 17/17 |
| State mismatch (genuine trajectory + answer, after = seed) | 11–15, 17, 19 | FAIL on the DB check | 7/7 |
| Over-action (extra save, two removals, extra application) | 11, 12, 15, 19 | FAIL on set equality / `applications_unchanged` | 4/4 |
| Read-only write (task 0 that also saves a role) | 0 | FAIL on `read_only_saved_jobs_unchanged` | 1/1 |
| Unit tests | all 20 + lib | green | 223 tests |

```bash
python -m unittest discover sites/walmart_careers/verify/tests
```

### Real agent runs

Two passes of the unchanged `agent_demo/agent.py` (default 15 steps, one attempt per
task, no retries), each run graded by the verifier **and** by the LLM judge
(`gpt-5.4-nano`, rubric-driven). Both passes are graded with the verifiers as
committed after two fixes the runs prompted: a count written as "Open positions: 2."
no longer fails on the trailing period (`verify_lib`), and verifier 5's results gate
also accepts a typed header search naming Hoboken or Technology (`?q=`), not only the
`area` / `loc` filter parameters.

| agent | verifier PASS | judge PASS | agree | diverge |
|---|---|---|---|---|
| gpt-5.4-nano | 8/20 | 3/20 | 15/20 | 5 (all verifier PASS / judge FAIL) |
| gpt-5.4-mini | 13/20 | 3/20 | 8/20 | 12 (11 verifier PASS / judge FAIL, 1 the reverse) |

Every divergent trajectory was read; the deterministic verifier was right in all 17.
The judge, with only the last four screenshots and no database, failed correct runs on
facts it could not see (DB after-state, a below-the-fold hashtag, an earlier detail
page), on requirements outside its rubric, and twice with every rubric checkpoint marked
true; its one PASS against the verifier credited a mandated filter that was never
applied. Every agree-FAIL run is a genuine agent failure (answered from result cards,
wrong posting, out of steps, skipped a mandated filter, guest application instead of a
signed-in one). Full per-task tables and the adjudication are in
`scripts_dev/VERIFICATION.md` §11.
