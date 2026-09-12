#!/usr/bin/env python3
"""Verifier for Kaggle--0 (read-only).

Find the Getting Started competition about predicting passenger survival on the Titanic
(slug titanic-survival, "Titanic — Machine Learning from Disaster") and report its evaluation
metric. Ground truth: metric == "Classification Accuracy".

Checks: nav the competition detail page | answer names the metric | LLM anchor.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verify_lib import (Judge, contains_any, final_answer, llm_text_match, load_run,
                        navigated_to, parse_args, resolve_db, scalar, tables_unchanged)

SLUG = "titanic-survival"

def main():
    a = parse_args()
    j = Judge('Kaggle--0', a.no_llm)
    t = load_run(a.run_dir); fa = final_answer(t)
    ref = resolve_db(a.initial_db, a.container, "instance_seed") or resolve_db(a.after_db, a.container, "instance")
    # Read-only task: the live DB must be unchanged, otherwise the run is not
    # a read-only visit (a missing DB leaves `changed` as None and fails).
    changed = tables_unchanged(ref, resolve_db(a.after_db, a.container, "instance"))
    j.check("db_read_only", changed == [], f"changed tables={changed!r}")
    gt = scalar(ref, "competitions", "metric", SLUG)  # "Classification Accuracy"
    j.check("nav_competition", navigated_to(t, f"/competitions/{SLUG}"), "opened the Titanic competition page")
    j.check("db_ground_truth", gt is not None, f"metric={gt!r}")
    j.check("answer_metric", contains_any(fa, ["classification accuracy", "accuracy"]), f"final={fa!r}")
    ok, ev = llm_text_match(fa, f"The evaluation metric is {gt}.",
        "What evaluation metric does the Titanic (passenger survival) Getting Started competition use?")
    j.check("answer_llm", ok, ev, llm=True)
    j.emit()

if __name__ == "__main__":
    main()
