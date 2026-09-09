#!/usr/bin/env python3
"""Verify Walmart Careers--5: Full time Technology roles in Hoboken > $200k: requisition ID + Option 1 degree (read-only).

Deterministic only: no LLM calls. Ground truth is hardcoded below and never
appears in tasks.jsonl.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from verify_lib import (  # noqa: E402
    Judge,
    check_read_only,
    check_results_visited,
    check_trajectory_identity,
    check_visited_job_detail,
    contains_all,
    contains_req_id,
    fail_closed,
    final_answer,
    load_run,
    parse_args,
    resolve_snapshots,
)


TASK_ID = "Walmart Careers--5"
JOB_ID = "R-2411489"
DEGREE = "bachelor"


def run_checks(judge: Judge, trajectory: dict, initial_db: str, after_db: str) -> None:
    check_trajectory_identity(judge, trajectory, TASK_ID)
    answer = final_answer(trajectory)
    # Filter UI (area / loc params) or a typed header search naming the place or
    # the career area — a real gpt-5.4-mini run typed "Technology Hoboken, NJ",
    # opened the right posting and answered correctly; the task text says "find",
    # it does not mandate the filter popover.
    check_results_visited(
        judge,
        trajectory,
        "visited_results_technology_or_hoboken",
        {"area": "technology"},
        {"loc": "hoboken"},
        {"q": "hoboken"},
        {"q": "technology"},
    )
    check_visited_job_detail(judge, trajectory, JOB_ID)
    judge.check(
        "answer_has_requisition_id",
        contains_req_id(answer, JOB_ID),
        f"expected={JOB_ID!r}, answer={answer!r}",
    )
    judge.check(
        "answer_names_option_1_degree",
        contains_all(answer, [DEGREE]),
        f"expected_degree={DEGREE!r}, answer={answer!r}",
    )
    check_read_only(judge, initial_db, after_db)


def main() -> None:
    args = parse_args()
    try:
        trajectory = load_run(args.run_dir)
    except (OSError, ValueError) as exc:
        fail_closed(TASK_ID, "trajectory_unavailable", str(exc))
    initial_db, after_db = resolve_snapshots(args, TASK_ID)
    judge = Judge(TASK_ID)
    try:
        run_checks(judge, trajectory, initial_db, after_db)
    except Exception as exc:  # noqa: BLE001 — any verifier error fails closed
        fail_closed(TASK_ID, "verifier_error", f"{type(exc).__name__}: {exc}")
    judge.emit()


if __name__ == "__main__":
    main()
