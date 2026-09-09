#!/usr/bin/env python3
"""Verify Walmart Careers--19: Bob signs in; Stores and Clubs -> Digital Pickup and Delivery, Full time; fewest positions; save + report ID and street (stateful).

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
    check_visited_path,
    contains_req_id,
    contains_street,
    fail_closed,
    final_answer,
    load_run,
    parse_args,
    resolve_snapshots,
    saved_job_ids,
)


TASK_ID = "Walmart Careers--19"
EMAIL = "bob.c@test.com"
JOB_ID = "CP-1179-11202"
STREET = "1301 SW Wanamaker Rd"
AREA_PATH = "/careers-areas/stores-and-clubs"


def run_checks(judge: Judge, trajectory: dict, initial_db: str, after_db: str) -> None:
    check_trajectory_identity(judge, trajectory, TASK_ID)
    answer = final_answer(trajectory)
    check_signed_in_as(judge, trajectory, EMAIL)
    check_visited_path(judge, trajectory, "visited_stores_and_clubs_area_page", AREA_PATH)
    check_results_visited(
        judge,
        trajectory,
        "visited_digital_pickup_full_time_results",
        {"category": "digital-pickup-and-delivery", "type": "Full time"},
    )
    check_visited_job_detail(judge, trajectory, JOB_ID)
    judge.check(
        "answer_has_requisition_id",
        contains_req_id(answer, JOB_ID),
        f"expected={JOB_ID!r}, answer={answer!r}",
    )
    judge.check(
        "answer_has_street_address",
        contains_street(answer, STREET),
        f"expected={STREET!r}, answer={answer!r}",
    )
    before = saved_job_ids(initial_db, EMAIL)
    after = saved_job_ids(after_db, EMAIL)
    judge.check(
        "target_saved_for_bob",
        after is not None and JOB_ID in after,
        f"email={EMAIL}, job_id={JOB_ID}, after_saved={sorted(after or set())!r}",
    )
    judge.check(
        "bob_saved_roles_changed_only_by_target",
        before is not None and after == before | {JOB_ID},
        f"initial_saved={sorted(before or set())!r}, after_saved={sorted(after or set())!r}",
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
