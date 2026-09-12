# Y Combinator verifiers

One deterministic verifier per accepted task, invoked through
`agent_demo/eval_judge.py --verifier True`. Ground truth lives here, never in
`tasks.jsonl`.

## Input contract

Each verifier grades a frozen run signature:

| Input | Source |
|---|---|
| `trajectory.json` | `<run_dir>/trajectory.json` — `task_id`, `start_url`, `steps[]`, `final_answer`, `terminated`, `termination_reason` |
| step screenshots | `<run_dir>/screenshots/<name>.png`, referenced by each step's `screenshot_before` / `screenshot_after` |
| initial state | `--initial_db`, or `docker cp` from `<container>:/opt/WebSyn/y_combinator/instance_seed/y_combinator.db` |
| after state | `--after_db`, or `docker cp` from `<container>:/opt/WebSyn/y_combinator/instance/y_combinator.db` |

```bash
python3 sites/y_combinator/verify/verify_9.py \
    --run_dir runs/yc-9 \
    --initial_db runs/yc-9/initial_state/y_combinator.db \
    --after_db  runs/yc-9/after_state/y_combinator.db
```

Prints `{task_id, pass, reason, evidence[]}` and exits 0 on PASS, 1 on FAIL.
Pass the snapshots explicitly when grading a frozen run: the container's live
database is whatever the last run left behind, not that run's after state.

## How grading works

`verify_lib.expected(task, before)` **derives** each answer from the frozen
initial snapshot rather than hard-coding it, so a verifier fails loudly with
`valid_inputs` if it is graded against a seed the task was not written for.
Every extreme ("largest team", "most upvotes") is required to be unambiguous in
that snapshot, so a task cannot silently become unanswerable.

Four groups of checks run for every task:

- **package** — task identity, non-empty step list, every recorded URL on the
  run's own loopback origin, a non-empty final answer, a completed run, and a
  readable PNG for each referenced step screenshot.
- **state** — the table set is unchanged, every table the task is not allowed to
  touch is byte-identical, and for the three stateful tasks the expected row is
  present, bound to the right account and object, with nothing else disturbed.
- **navigation** — the pages that actually carry the answer were opened. Only
  pages the task requires are checked; no route, click count or ordering beyond
  the task's own wording is imposed.
- **answer** — the requested facts appear in the final answer, matched case- and
  punctuation-insensitively, with number grouping and million/thousand notation
  accepted. A fact that appears only inside a negation does not count.

Tasks 8, 9 and 10 are the stateful ones (library bookmark, launch upvote,
registration plus newsletter). Every other task must leave the database
byte-identical.

## Requirements

`Pillow` (screenshot validation) and, for task 10 only, `bcrypt` to confirm the
registered password. Both ship in the WebHarbor image.
