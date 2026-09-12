#!/usr/bin/env python3
"""Verifier for B&H Photo--3: report the processor of the 16-inch ThinkPad T1g Gen 8.

Ground truth is read from the shipped seed database at verify time, so the
answer key lives here and never in the agent-facing task file.
"""
from verify_lib import (Judge, changed_tables_excluding, check_common, contains_any,
                        final_answer, load_run, normalize_text, only_allowed_tables_changed,
                        parse_args, resolve_db, row_dicts, visited_path)

TASK_ID = 'B&H Photo--3'
SLUG = 'lenovo-16-thinkpad-t1g-gen-8-multi-touch-laptop'
SPEC_LABEL = 'Processor'


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
    # value reads "Intel Core Ultra 9 285H" (with a non-breaking space before the model)
    tokens = [token for token in value.replace('\xa0', ' ').split() if token]
    judge.check('ground_truth_readable_tokens', len(tokens) >= 2, f'spec={value!r}')
    normalized_answer = normalize_text(answer).replace('\xa0', ' ')
    judge.check('answer_names_full_processor',
                all(normalize_text(token) in normalized_answer for token in tokens),
                f'expected={value!r} answer={answer!r}')
    judge.check('answer_is_more_than_the_vendor',
                normalized_answer.strip() not in {'intel', 'lenovo'},
                f'answer={answer!r}')
    if initial and after:
        judge.check('no_state_written',
                    only_allowed_tables_changed(initial, after, ['search_logs']),
                    f'changed={sorted(changed_tables_excluding(initial, after, ["search_logs"]))}')
    judge.emit()


if __name__ == '__main__':
    main()
