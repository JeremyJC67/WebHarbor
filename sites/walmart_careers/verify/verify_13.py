#!/usr/bin/env python3
"""Verify Walmart Careers--13: Carol signs in and applies to the Tacoma Pharmacy Technician posting with the task phone; reports the confirmation number (stateful).

Deterministic only: no LLM calls. Ground truth is hardcoded below and never
appears in tasks.jsonl.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from verify_lib import (  # noqa: E402
    Judge,
    application_rows,
    check_signed_in_as,
    check_trajectory_identity,
    check_visited_job_detail,
    check_visited_path,
    contains_confirmation_number,
    digits_only,
    fail_closed,
    final_answer,
    load_run,
    new_application_rows,
    parse_args,
    resolve_snapshots,
)


TASK_ID = "Walmart Careers--13"
EMAIL = "carol.d@test.com"
USER_ID = 3
JOB_ID = "CP-4137-10959"
PHONE_DIGITS = "2535550142"


def run_checks(judge: Judge, trajectory: dict, initial_db: str, after_db: str) -> None:
    check_trajectory_identity(judge, trajectory, TASK_ID)
    answer = final_answer(trajectory)
    check_signed_in_as(judge, trajectory, EMAIL)
    check_visited_job_detail(judge, trajectory, JOB_ID)
    check_visited_path(judge, trajectory, "visited_apply_page", f"/jobs/{JOB_ID}/apply")
    check_visited_path(judge, trajectory, "visited_apply_submitted_page", f"/jobs/{JOB_ID}/apply/submitted")
    judge.check(
        "initial_has_no_carol_application_for_target",
        not application_rows(initial_db, job_id=JOB_ID, email=EMAIL),
        f"job_id={JOB_ID}, email={EMAIL}",
    )
    new_rows = new_application_rows(initial_db, after_db)
    judge.check(
        "exactly_one_new_application",
        len(new_rows) == 1,
        f"new_rows={new_rows!r}",
    )
    row = new_rows[0] if len(new_rows) == 1 else {}
    judge.check(
        "new_application_is_for_target_posting",
        row.get("job_id") == JOB_ID,
        f"expected_job_id={JOB_ID!r}, row={row!r}",
    )
    judge.check(
        "new_application_belongs_to_carol",
        row.get("user_id") == USER_ID and str(row.get("email") or "").casefold() == EMAIL,
        f"expected_user_id={USER_ID}, expected_email={EMAIL!r}, row={row!r}",
    )
    judge.check(
        "new_application_has_task_phone",
        digits_only(row.get("phone")) == PHONE_DIGITS,
        f"expected_phone_digits={PHONE_DIGITS!r}, row_phone={row.get('phone')!r}",
    )
    confirmation = str(row.get("confirmation_no") or "")
    judge.check(
        "answer_has_matching_confirmation_number",
        bool(confirmation) and contains_confirmation_number(answer, confirmation),
        f"row_confirmation_no={confirmation!r}, answer={answer!r}",
    )


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
