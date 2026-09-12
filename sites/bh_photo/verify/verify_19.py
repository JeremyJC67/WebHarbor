#!/usr/bin/env python3
"""Verifier for B&H Photo--19: Alice removes one named kit from her cart."""
from verify_lib import (Judge, cart_for, changed_tables_excluding, check_common,
                        final_answer, load_run, login_submitted_as, normalize_text,
                        only_allowed_tables_changed, parse_args, resolve_db, visited_path)

TASK_ID = 'B&H Photo--19'
EMAIL = 'alice.j@test.com'
REMOVE_SLUG = 'apple-13-macbook-air-kit-with-applecare-m4-midnight'
ALLOWED = ['cart_items', 'search_logs']


def main():
    args = parse_args()
    trajectory = load_run(args.run_dir)
    judge = Judge(TASK_ID)
    answer = final_answer(trajectory)
    check_common(judge, trajectory, TASK_ID)

    initial = resolve_db(args.initial_db, args.container, 'instance_seed')
    after = resolve_db(args.after_db, args.container, 'instance')
    judge.check('databases_readable', bool(initial and after), f'initial={initial} after={after}')
    if not (initial and after):
        judge.emit()

    before = {row['slug']: row for row in cart_for(initial, EMAIL)}
    now = {row['slug']: row for row in cart_for(after, EMAIL)}
    judge.check('ground_truth_target_was_in_the_cart', REMOVE_SLUG in before, f'before={sorted(before)}')
    survivors = [slug for slug in before if slug != REMOVE_SLUG]
    judge.check('ground_truth_cart_had_another_line', bool(survivors), f'survivors={survivors}')
    if REMOVE_SLUG not in before or not survivors:
        judge.emit()

    judge.check('signed_in_as_the_named_account', login_submitted_as(trajectory, EMAIL), EMAIL)
    judge.check('opened_the_cart', visited_path(trajectory, '/cart'), '/cart')
    judge.check('target_removed_afterwards', REMOVE_SLUG not in now, f'after={sorted(now)}')
    judge.check('the_other_line_survived', all(slug in now for slug in survivors),
                f'expected={survivors} after={sorted(now)}')
    judge.check('cart_was_not_emptied', bool(now), f'after={sorted(now)}')
    remaining_names = [now[slug]['name'] for slug in survivors if slug in now]
    judge.check('answer_says_what_remains',
                any(normalize_text(name) in normalize_text(answer) for name in remaining_names),
                f'expected one of {remaining_names} answer={answer!r}')
    judge.check('no_unrelated_state_written',
                only_allowed_tables_changed(initial, after, ALLOWED),
                f'changed={sorted(changed_tables_excluding(initial, after, ALLOWED))}')
    judge.emit()


if __name__ == '__main__':
    main()
