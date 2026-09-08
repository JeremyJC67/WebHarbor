"""Outcome checks for the three additional account workflows."""
import copy
import json
import re
from fractions import Fraction

import verify_lib as v


def phone(value):
    digits = re.sub(r"\D", "", value)
    return digits[1:] if len(digits) == 11 and digits.startswith("1") else digits


def exact_text(text, value):
    return bool(re.search(r"(?<![\w.@+-])" + re.escape(value) + r"(?![\w@+-]|\.[\w])", text, re.I))


def property_answer(judge, trajectory, listing_id):
    listing = v.LISTINGS[listing_id]
    text = trajectory["final_answer"]
    judge.check("answer_target_address", v.address_matches(text, listing))
    judge.check("answer_year", v.scalar(text, listing["year_built"], "year"))
    judge.check("property_details", v.visited(trajectory, v.detail_path(listing_id)))


def check(judge, trajectory, before, after):
    """Compare the complete expected state, allowing only the requested outcome."""
    expected = copy.deepcopy(before)
    task = judge.task
    text = trajectory["final_answer"]
    judge.check("same_table_set", before.keys() == after.keys())
    if task == 18:
        uid = v.user_id(before, "carol.lee@test.com")
        tours = [t for t in before["tours"].values() if t["user_id"] == uid and t["status"] != "cancelled"]
        if not tours:
            judge.check("eligible_tour", False)
            return
        latest = max(t["requested_date"] for t in tours)
        targets = [t for t in tours if t["requested_date"] == latest]
        judge.check("unique_latest_tour", uid is not None and len(targets) == 1)
        target = targets[0]
        expected["tours"][target["id"]]["status"] = "cancelled"
        property_answer(judge, trajectory, target["listing_id"])
        judge.check("tours_confirmation", v.visited(trajectory, "/tours"))
        judge.check("answer_cancelled", bool(re.search(r"\bcancell?ed\b", v.norm(text)))
                    and not re.search(r"\b(?:not|never|isn't|wasn't)\s+cancell?ed\b", v.norm(text)))
    elif task == 19:
        uid = v.user_id(before, "bob.smith@test.com")
        collections = [c for c in before["collections"].values() if c["user_id"] == uid and c["name"] == "Bob — NY shortlist"]
        judge.check("existing_collection", uid is not None and len(collections) == 1)
        if len(collections) != 1:
            return
        collection = collections[0]
        members = json.loads(collection["listing_ids_json"])
        eligible = [before["listings"][key] for key in members if (before["listings"][key]["sqft"] or 0) > 0]
        ratios = {item["id"]: Fraction(item["price"], item["sqft"]) for item in eligible}
        if not ratios:
            judge.check("eligible_members", False)
            return
        targets = [key for key, ratio in ratios.items() if ratio == max(ratios.values())]
        judge.check("unique_highest_ratio", len(targets) == 1)
        target = targets[0]
        remaining = [key for key in members if key != target]
        expected["collections"][collection["id"]]["listing_ids_json"] = json.dumps(remaining)
        # Membership, not JSON whitespace or order, is the requested invariant.
        after = copy.deepcopy(after)
        row = after["collections"].get(collection["id"])
        if row:
            actual = json.loads(row["listing_ids_json"])
            if sorted(actual) == sorted(remaining):
                row["listing_ids_json"] = json.dumps(remaining)
        property_answer(judge, trajectory, target)
        judge.check("collection_confirmation", v.visited(trajectory, f'/collections/{collection["id"]}'))
    elif task == 20:
        uid = v.user_id(before, "alice.j@test.com")
        judge.check("existing_account", uid is not None)
        if uid is None or "seller_inquiries" not in before or "seller_inquiries" not in after:
            judge.check("seller_schema_available", False)
            return
        profile = before["users"][uid]
        new = v.only_new(before, after, "seller_inquiries")
        judge.check("one_seller_inquiry", len(new) == 1)
        if len(new) == 1:
            row = new[0]
            judge.check("profile_contact_and_zip", row["name"] == profile["name"]
                        and row["email"].casefold() == profile["email"].casefold()
                        and phone(row["phone"]) == phone(profile["phone"])
                        and row["zip_code"] == "94107")
            reference = row["reference"]
            judge.check("generated_reference", bool(re.fullmatch(r"[0-9a-f]{24}", reference)))
            judge.check("answer_reference", exact_text(text, reference))
            judge.check("answer_contact_and_zip", v.phrase(text, profile["name"])
                        and exact_text(text, profile["email"])
                        and phone(profile["phone"]) in re.sub(r"\D", "", text)
                        and v.phrase(text, "94107"))
            expected["seller_inquiries"][row["id"]] = row
        judge.check("profile_read", v.visited(trajectory, "/account"))
        judge.check("sell_confirmation", v.visited(trajectory, "/sell"))
    else:
        raise ValueError("Unsupported additional task")
    for table in expected.keys() | after.keys():
        judge.check("exact_state_" + table, expected.get(table) == after.get(table))
