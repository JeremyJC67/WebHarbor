#!/usr/bin/env python3
"""Verify UC Berkeley--27 (re-anchored): both programme durations and the MEng department.

The task now asks for the two exact durations printed on the two detail pages
(MEng vs Computer Science MS), which is deterministic; both detail visits are
gated and the department is accepted by name or by its acronym.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from verify_lib import (  # noqa: E402
    check_params_visited,
    check_read_only,
    check_trajectory_identity,
    check_visited_detail,
    contains_department,
    contains_duration_years,
    fail_closed,
    final_answer,
    Judge,
    load_run,
    parse_args,
    resolve_snapshots,
)
from ground_truth import task_ground_truth  # noqa: E402


TASK_ID = "UC Berkeley--27"


def run_checks(judge: Judge, trajectory: dict, initial_db: str, after_db: str) -> None:
    facts = task_ground_truth(initial_db, 27)
    check_trajectory_identity(judge, trajectory, TASK_ID)
    answer = final_answer(trajectory)
    meng_duration, ms_duration = facts["durations"]

    check_params_visited(
        judge, trajectory, "visited_program_search", "/programs",
        {"q": "master of engineering"}, {"degree": "MEng"},
    )
    check_visited_detail(judge, trajectory, "program", facts["meng"]["slug"])
    check_visited_detail(judge, trajectory, "program", facts["ms"]["slug"])
    judge.check(
        "answer_has_department",
        contains_department(answer, facts["department"]),
        f"expected_department={facts['department']!r}, answer={answer!r}",
    )
    judge.check(
        "answer_has_meng_duration",
        contains_duration_years(answer, meng_duration),
        f"expected_meng_duration={meng_duration!r}, answer={answer!r}",
    )
    judge.check(
        "answer_has_ms_duration",
        contains_duration_years(answer, ms_duration),
        f"expected_ms_duration={ms_duration!r}, answer={answer!r}",
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
    except Exception as exc:  # noqa: BLE001 - any verifier error fails closed
        fail_closed(TASK_ID, "verifier_error", f"{type(exc).__name__}: {exc}")
    judge.emit()


if __name__ == "__main__":
    main()
