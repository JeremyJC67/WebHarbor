#!/usr/bin/env python3
"""Verify Walmart Careers--1: Staff, Software Engineer (Sunnyvale): quote Option 2 of Minimum Qualifications (read-only).

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
    check_trajectory_identity,
    check_visited_job_detail,
    contains_all,
    contains_any,
    fail_closed,
    final_answer,
    load_run,
    parse_args,
    resolve_snapshots,
)


TASK_ID = "Walmart Careers--1"
JOB_ID = "R-2468347"
OPTION_2_YEARS = "7 years"
OPTION_2_CORE = "operating search or ML-serving systems in production"
OPTION_1_MARKERS = ("5 years", "bachelor")


def run_checks(judge: Judge, trajectory: dict, initial_db: str, after_db: str) -> None:
    check_trajectory_identity(judge, trajectory, TASK_ID)
    answer = final_answer(trajectory)
    check_visited_job_detail(judge, trajectory, JOB_ID)
    judge.check(
        "answer_quotes_option_2",
        contains_all(answer, [OPTION_2_YEARS, OPTION_2_CORE]),
        f"expected_fragments={[OPTION_2_YEARS, OPTION_2_CORE]!r}, answer={answer!r}",
    )
    quoted_option_1 = contains_any(answer, OPTION_1_MARKERS) and not contains_all(answer, [OPTION_2_YEARS])
    judge.check(
        "answer_is_not_option_1",
        not quoted_option_1,
        f"option_1_markers={OPTION_1_MARKERS!r}, answer={answer!r}",
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
