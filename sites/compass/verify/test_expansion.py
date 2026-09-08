"""Synthetic verifier regressions; these are not browser execution evidence."""
import copy
import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_lib as v


def database(path, extras=()):
    with sqlite3.connect(path) as db:
        for table in v.TABLES | set(extras):
            pk = "slug TEXT" if table == "neighborhood_guides" else "id INTEGER"
            db.execute(f'CREATE TABLE "{table}" ({pk} PRIMARY KEY, value TEXT)')
        if "neighborhood_guides" in extras:
            db.execute("INSERT INTO neighborhood_guides VALUES ('nyc', 'original')")
    return path


@pytest.mark.parametrize("extras", [(), ("neighborhood_guides",), ("neighborhood_guides", "seller_inquiries")])
def test_supported_snapshot_generations(tmp_path, extras):
    state = v.snapshot(database(tmp_path / "seed.db", extras))
    assert set(state) == v.TABLES | set(extras)
    if extras:
        assert state["neighborhood_guides"]["nyc"]["value"] == "original"


def test_unknown_table_is_not_silently_ignored(tmp_path):
    with pytest.raises(ValueError):
        v.snapshot(database(tmp_path / "seed.db", ("unexpected",)))


@pytest.mark.parametrize("table", ["seller_inquiries", "neighborhood_guides"])
@pytest.mark.parametrize("mutation", ["insert", "drop"])
def test_old_tasks_protect_current_tables(table, mutation):
    before = {name: {} for name in v.TABLES | {"seller_inquiries", "neighborhood_guides"}}
    after = copy.deepcopy(before)
    if mutation == "insert":
        after[table][1] = {"id": 1}
    else:
        del after[table]
    judge = v.Checks(0)
    v.state_checks(judge, {}, before, after)
    assert not judge.result()["pass"]


def fixture(task):
    before = {name: {} for name in v.TABLES | {"seller_inquiries", "neighborhood_guides"}}
    before["users"] = {
        1: {"id": 1, "email": "alice.j@test.com", "name": "Alice Johnson", "phone": "(415) 555-0144"},
        2: {"id": 2, "email": "bob.smith@test.com"},
        3: {"id": 3, "email": "carol.lee@test.com"},
    }
    before["tours"] = {4: {"id": 4, "user_id": 3, "listing_id": 84, "requested_date": "2026-06-14", "status": "requested"},
                       5: {"id": 5, "user_id": 3, "listing_id": 92, "requested_date": "2026-06-16", "status": "confirmed"},
                       7: {"id": 7, "user_id": 4, "listing_id": 238, "requested_date": "2026-06-17", "status": "confirmed"}}
    before["collections"][2] = {"id": 2, "user_id": 2, "name": "Bob — NY shortlist", "listing_ids_json": "[16, 18, 9]", "share_token": "keep-token"}
    before["listings"] = {16: {"id": 16, "price": 775000, "sqft": None}, 18: {"id": 18, "price": 1125000, "sqft": 1217}, 9: {"id": 9, "price": 1495000, "sqft": 1200}}
    before["neighborhood_guides"]["nyc"] = {"slug": "nyc", "directory_json": "unchanged"}
    after = copy.deepcopy(before)
    paths = ["/account"]
    if task == 18:
        after["tours"][5]["status"] = "cancelled"
        answer = "170 NW 44th St; built 2026; cancelled."
        paths += ["/tours", v.detail_path(92), "/tours"]
    elif task == 19:
        after["collections"][2]["listing_ids_json"] = "[16, 18]"
        answer = "Removed 130 Prospect Pl, Unit 1; built 1930."
        paths += ["/collections/2", v.detail_path(9), "/collections/2"]
    else:
        after["seller_inquiries"][1] = {"id": 1, "reference": "a0b1c2d3e4f567890123abcd", "name": "Alice Johnson", "email": "alice.j@test.com", "phone": "(415) 555-0144", "zip_code": "94107", "created_at": "2026-09-08 12:00:00"}
        answer = "Reference: a0b1c2d3e4f567890123abcd. Alice Johnson; alice.j@test.com; (415) 555-0144; ZIP 94107."
        paths += ["/sell/#lead-form"]
    trajectory = {"task_id": f"Compass--{task}", "start_url": "http://localhost:57021/", "final_answer": answer,
                  "steps": [{"url": "http://127.0.0.1:57021" + path, "action": "click"} for path in paths]}
    return trajectory, before, after


def result(task, trajectory, before, after):
    from verify_expansion import check
    judge = v.Checks(task)
    check(judge, trajectory, before, after)
    return judge.result()


@pytest.mark.parametrize("task", [18, 19, 20])
def test_completed_outcome(task):
    args = fixture(task)
    assert result(task, *args)["pass"], result(task, *args)


@pytest.mark.parametrize("task", [18, 19, 20])
@pytest.mark.parametrize("attack", ["noop", "wrong_answer", "no_navigation", "other_user", "extra_write", "guide_write", "schema_drop"])
def test_failed_outcomes(task, attack):
    t, before, after = fixture(task)
    if attack == "noop": after = copy.deepcopy(before)
    elif attack == "wrong_answer": t["final_answer"] = "All done!"
    elif attack == "no_navigation": t["steps"] = [{"url": t["start_url"], "action": "done"}]
    elif attack == "other_user":
        if task == 18: after["tours"][5]["user_id"] = 2
        elif task == 19: after["collections"][2]["user_id"] = 3
        else: after["seller_inquiries"][1]["email"] = "bob.smith@test.com"
    elif attack == "extra_write": after["saved_homes"][99] = {"id": 99, "user_id": 1, "listing_id": 9}
    elif attack == "guide_write": after["neighborhood_guides"]["nyc"]["directory_json"] = "changed"
    else: del after["seller_inquiries"]
    assert not result(task, t, before, after)["pass"]


def test_cancel_wrong_tour_or_wrong_status():
    for change in ("other_tour", "requested", "delete", "negated_answer"):
        t, before, after = fixture(18)
        if change == "other_tour":
            after["tours"][5]["status"] = "confirmed"
            after["tours"][4]["status"] = "cancelled"
        elif change == "delete": del after["tours"][5]
        elif change == "negated_answer": t["final_answer"] = "170 Northwest 44th Street; built 2026; not cancelled."
        else: after["tours"][5]["status"] = change
        assert not result(18, t, before, after)["pass"]


@pytest.mark.parametrize("members", [[18], [16, 9], [16, 18, 18], []])
def test_collection_preserves_every_other_member(members):
    t, before, after = fixture(19)
    after["collections"][2]["listing_ids_json"] = json.dumps(members)
    assert not result(19, t, before, after)["pass"]


def test_collection_accepts_equivalent_member_order_and_address():
    t, before, after = fixture(19)
    after["collections"][2]["listing_ids_json"] = "[18,16]"
    t["final_answer"] = "130 Prospect Place #1, built in 1930."
    t["steps"].reverse()  # No unrequested route order is imposed.
    assert result(19, t, before, after)["pass"]


@pytest.mark.parametrize("field,value", [("name", "Bob Smith"), ("phone", "4155550199"), ("zip_code", "10001"), ("reference", "wrong-reference")])
def test_sell_wrong_contact_or_reference(field, value):
    t, before, after = fixture(20)
    after["seller_inquiries"][1][field] = value
    assert not result(20, t, before, after)["pass"]


def test_sell_duplicate_or_profile_change():
    for change in ("duplicate", "profile"):
        t, before, after = fixture(20)
        if change == "duplicate": after["seller_inquiries"][2] = dict(after["seller_inquiries"][1], id=2, reference="second-reference")
        else: after["users"][1]["phone"] = "4155550199"
        assert not result(20, t, before, after)["pass"]


def test_sell_accepts_phone_format_and_reference_from_this_run():
    t, before, after = fixture(20)
    after["seller_inquiries"][1]["phone"] = "+1 415-555-0144"
    after["seller_inquiries"][1]["reference"] = "ffeeddccbbaa112233445566"
    t["final_answer"] = "ffeeddccbbaa112233445566 — Alice Johnson, alice.j@test.com, +1 415 555 0144; 94107."
    assert result(20, t, before, after)["pass"]
