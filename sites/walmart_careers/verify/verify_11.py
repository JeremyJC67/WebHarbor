#!/usr/bin/env python3
"""Verify Walmart Careers--11: Alice signs in, searches Yard Driver, saves the Williamsburg posting (stateful).

Deterministic only: no LLM calls. Ground truth is hardcoded below and never
appears in tasks.jsonl.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from verify_lib import (  # noqa: E402
    Judge,
    check_results_visited,
    check_signed_in_as,
    check_tables_unchanged,
    check_trajectory_identity,
    check_visited_job_detail,
    fail_closed,
    final_answer,
    load_run,
    parse_args,
    resolve_snapshots,
    saved_job_ids,
)


TASK_ID = "Walmart Careers--11"
EMAIL = "alice.j@test.com"
JOB_ID = "CP-6088-10659"


def run_checks(judge: Judge, trajectory: dict, initial_db: str, after_db: str) -> None:
    check_trajectory_identity(judge, trajectory, TASK_ID)
    answer = final_answer(trajectory)
    check_signed_in_as(judge, trajectory, EMAIL)
    check_results_visited(judge, trajectory, "visited_results_yard_driver_search", {"q": "yard"})
    check_visited_job_detail(judge, trajectory, JOB_ID)
    before = saved_job_ids(initial_db, EMAIL)
    after = saved_job_ids(after_db, EMAIL)
    judge.check(
        "initial_target_not_saved",
        before is not None and JOB_ID not in before,
        f"email={EMAIL}, job_id={JOB_ID}, initial_saved={sorted(before or set())!r}",
    )
    judge.check(
        "target_saved_for_alice",
        after is not None and JOB_ID in after,
        f"email={EMAIL}, job_id={JOB_ID}, after_saved={sorted(after or set())!r}",
    )
    judge.check(
        "alice_saved_roles_changed_only_by_target",
        before is not None and after == before | {JOB_ID},
        f"initial_saved={sorted(before or set())!r}, after_saved={sorted(after or set())!r}",
    )
    check_tables_unchanged(judge, initial_db, after_db, ("users", "applications"))


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
