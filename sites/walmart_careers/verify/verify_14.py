#!/usr/bin/env python3
"""Verify Walmart Careers--14: Register a new account, then save the eCom Warehouse Worker posting at #9046 Marcy (stateful).

Deterministic only: no LLM calls. Ground truth is hardcoded below and never
appears in tasks.jsonl.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from verify_lib import (  # noqa: E402
    Judge,
    check_tables_unchanged,
    check_trajectory_identity,
    check_visited_job_detail,
    check_visited_path,
    fail_closed,
    final_answer,
    load_run,
    new_user_ids,
    parse_args,
    resolve_snapshots,
    saved_job_ids_by_user_id,
    user_ids,
)


TASK_ID = "Walmart Careers--14"
JOB_ID = "CP-9046-11274"


def run_checks(judge: Judge, trajectory: dict, initial_db: str, after_db: str) -> None:
    check_trajectory_identity(judge, trajectory, TASK_ID)
    answer = final_answer(trajectory)
    check_visited_path(judge, trajectory, "visited_register_page", "/register")
    check_visited_job_detail(judge, trajectory, JOB_ID)
    fresh = new_user_ids(initial_db, after_db)
    judge.check("new_user_registered", bool(fresh), f"new_user_ids={sorted(fresh)!r}")
    savers = sorted(uid for uid in fresh if JOB_ID in saved_job_ids_by_user_id(after_db, uid))
    judge.check(
        "target_saved_by_new_user",
        bool(savers),
        f"job_id={JOB_ID}, new_user_ids={sorted(fresh)!r}, new_users_with_target={savers!r}",
    )
    seeded_gainers = sorted(
        uid
        for uid in user_ids(initial_db)
        if JOB_ID in saved_job_ids_by_user_id(after_db, uid)
        and JOB_ID not in saved_job_ids_by_user_id(initial_db, uid)
    )
    judge.check(
        "no_seeded_user_gained_target",
        not seeded_gainers,
        f"seeded_users_that_gained_target={seeded_gainers!r}",
    )
    check_tables_unchanged(judge, initial_db, after_db, ("applications",))


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
