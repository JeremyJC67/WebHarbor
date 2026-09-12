#!/usr/bin/env python3
"""Verifier for B&H Photo--1: report the effective megapixels of the body-only EOS 90D.

Ground truth is read from the shipped seed database at verify time, so the
answer key lives here and never in the agent-facing task file.
"""
from verify_lib import (Judge, changed_tables_excluding, check_common, contains_any,
                        final_answer, load_run, normalize_text, only_allowed_tables_changed,
                        parse_args, resolve_db, row_dicts, visited_path)

TASK_ID = 'B&H Photo--1'
SLUG = 'canon-eos-90d-dslr-camera-body-only'
SPEC_LABEL = 'Sensor Resolution'


def spec_value(db_path):
    rows = row_dicts(db_path, """
        SELECT s.value FROM product_specs s
        JOIN product_spec_groups g ON g.id = s.group_id
        JOIN products p ON p.id = g.product_id
        WHERE p.slug = ? AND s.name = ?
    """, (SLUG, SPEC_LABEL))
    return rows[0]['value'] if rows else ''


def main():
    args = parse_args()
    trajectory = load_run(args.run_dir)
    judge = Judge(TASK_ID)
    answer = final_answer(trajectory)
    check_common(judge, trajectory, TASK_ID)

    initial = resolve_db(args.initial_db, args.container, 'instance_seed')
    after = resolve_db(args.after_db, args.container, 'instance')
    judge.check('databases_readable', bool(initial and after), f'initial={initial} after={after}')
    value = spec_value(initial) if initial else ''
    judge.check('ground_truth_readable', bool(value), f'spec={value!r}')

    judge.check('opened_product_page', visited_path(trajectory, '/product/' + SLUG),
                f'slug={SLUG}')
    # value reads "Actual: 34.4 Megapixel | Effective: 32.5 Megapixel (6960 x 4640)"
    import re
    effective = re.search(r'Effective:\s*([\d.]+)', value)
    actual = re.search(r'Actual:\s*([\d.]+)', value)
    judge.check('ground_truth_has_effective', bool(effective), f'spec={value!r}')
    if effective:
        judge.check('answer_gives_effective_megapixels',
                    effective.group(1) in normalize_text(answer),
                    f'expected={effective.group(1)} answer={answer!r}')
    if actual and effective:
        stated_actual_only = actual.group(1) in normalize_text(answer) and effective.group(1) not in normalize_text(answer)
        judge.check('answer_not_actual_megapixels_only', not stated_actual_only,
                    f'actual={actual.group(1)} answer={answer!r}')
    judge.check('did_not_use_the_kit_page',
                not visited_path(trajectory, '/product/canon-eos-90d-dslr-camera-with-18-135mm-lens')
                or visited_path(trajectory, '/product/' + SLUG),
                'body-only page required')
    if initial and after:
        judge.check('no_state_written',
                    only_allowed_tables_changed(initial, after, ['search_logs']),
                    f'changed={sorted(changed_tables_excluding(initial, after, ["search_logs"]))}')
    judge.emit()


if __name__ == '__main__':
    main()
