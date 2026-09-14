#!/usr/bin/env python3
"""Versus--20: area of the most populous city."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_lib as V


def body(j, traj, initial, after):
    rows = V.products(initial, "cities")
    if not rows:
        return j.fail("seed data missing", "no cities in initial_db")
    target = V.unique_extreme(rows, "spec_1_value", largest=True)
    if target is None:
        return j.fail("ambiguous ground truth", "no unique largest population")
    expected = target["spec_2_value"]

    ans = V.terminal_state_is_sound(j, traj)
    j.check("opened the fact-bearing page for the target city",
            V.opened_detail_or_compare(traj, target["slug"]),
            f"slug={target['slug']} steps={V.step_urls(traj)[-6:]}")
    j.check("answer names the most populous city",
            V.mentions_product(ans, target["name"]), f"expected={target['name']!r}")
    j.check("answer states its area",
            V.mentions_number(ans, expected, tol=1.0), f"expected={expected}")
    ok, why = V.llm_text_match(ans, f"{target['name']} — {expected} km2",
                               "area of the most populous city")
    j.check("anchored LLM agreement", ok, why, llm=True)


if __name__ == "__main__":
    V.run("Versus--20", body)
