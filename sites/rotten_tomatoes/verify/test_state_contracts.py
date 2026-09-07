"""Portable regression fixtures for tasks 8, 9, 11 and 14.

Run beside the verifiers: python -m unittest -v test_state_contracts
Requires bcrypt and the public site asset's instance_seed/rotten_tomatoes.db.
ROTTEN_TOMATOES_TEST_SEED may select another copy of that public seed.

All database mutations affect TemporaryDirectory copies. The tiny PNGs and DOM
sidecars are explicitly synthetic parser fixtures, not captured browser evidence
or benchmark acceptance. Expected answers remain in verify/, never in task input.
"""
from copy import deepcopy
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import bcrypt
from contracts import CONTRACTS
import verify_lib
from verify_lib import Snapshot, VerificationError, authenticated, count_answer
from verify_14 import answer_pairs, evaluate as evaluate_information


VERIFY_DIR = Path(verify_lib.__file__).resolve().parent
SEED_PATH = Path(os.environ.get(
    "ROTTEN_TOMATOES_TEST_SEED",
    str(VERIFY_DIR.parent / "instance_seed" / "rotten_tomatoes.db"),
)).resolve()
ORIGIN = "http://fixture.localhost:40019"
# A valid one-pixel PNG for artifact plumbing only. Vision is disabled in tests.
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII="
)
VERDICT_CHECKS = []


def snapshot_copy(source, destination):
    with sqlite3.connect(source.as_uri() + "?mode=ro", uri=True) as src:
        with sqlite3.connect(destination) as dst:
            src.backup(dst)


def nav(name=None, legacy=False):
    if name is None:
        return '- navigation:\n  - link "Sign In":\n    - /url: /login\n'
    logout = ('  - link "Logout":\n    - /url: /logout\n' if legacy
              else '  - button "Logout"\n')
    return ('- navigation:\n  - link "My Account: ' + name + '":\n'
            '    - /url: /account\n' + logout)


def page(title, name=None, body=""):
    return nav(name) + f'- main:\n  - heading "{title}" [level=1]\n' + body


def account(user):
    return page(user["name"], user["name"], '  - paragraph: ' + user["email"] + '\n')


class BrowserFixture:
    """Small native-trajectory builder, independent of any recorder or raw run."""

    def __init__(self, directory, task_number, seed):
        self.directory = directory
        directory.mkdir()
        for filename in ("before.db", "after.db"):
            snapshot_copy(SEED_PATH, directory / filename)
        (directory / "screenshots").mkdir()
        (directory / "observations").mkdir()
        (directory / "SYNTHETIC-FIXTURE.txt").write_text(__doc__)
        self.number = task_number
        self.spec = CONTRACTS[f"RottenTomatoes--{task_number}"]
        self.seed = seed
        self.path, self.dom = "/", page("Movies")
        self.data = {"task_id": self.spec["task_id"], "task": self.spec["prompt"],
                     "start_url": ORIGIN + "/", "steps": [], "final_answer": ""}

    def sql(self, query, params=(), which="after.db"):
        with sqlite3.connect(self.directory / which) as conn:
            conn.execute(query, params)

    def capture(self, number, dom):
        stem = f"step_{number:03}"
        (self.directory / "screenshots" / (stem + ".png")).write_bytes(PNG)
        (self.directory / "observations" / (stem + ".txt")).write_text(dom)
        return stem + ".png"

    def add(self, action, params, path=None, dom=None):
        index = len(self.data["steps"])
        after_path = path if path is not None else self.path
        after_dom = dom if dom is not None else self.dom
        step = {"step": index, "action": action, "params": params,
                "url": ORIGIN + self.path, "url_after": ORIGIN + after_path,
                "screenshot_before": self.capture(index * 2, self.dom),
                "screenshot_after": self.capture(index * 2 + 1, after_dom),
                "action_result": {"is_done": False, "success": None, "error": None}}
        self.data["steps"].append(step)
        self.path, self.dom = after_path, after_dom

    def authenticate(self, user, registration=False):
        route = "/register" if registration else "/login"
        self.add("click", {"name": "Register" if registration else "Sign In"},
                 route, page("Create Account" if registration else "Sign In"))
        if registration:
            self.add("input", {"index": 1, "text": user["name"]})
        self.add("input", {"index": 2, "text": self.spec["email"]})
        self.add("input", {"index": 3, "text": self.spec["password"]})
        if registration:
            self.add("input", {"index": 4, "text": self.spec["password"]})
        self.add("click", {"index": 5}, "/", page("Movies", user["name"]))

    def collection(self, user, table, removed=False):
        movies = {row["id"]: row for row in self.seed.rows["movies"]}
        rows = self.seed.select(table, user_id=user["id"])
        if removed:
            rows = [row for row in rows if movies[row["movie_id"]]["slug"] != "deadpool_and_wolverine"]
        is_ratings = table == "user_ratings"
        body = ""
        for row in rows:
            movie = movies[row["movie_id"]]
            body += f'  - link "{movie["title"]}":\n    - /url: /m/{movie["slug"]}\n'
            body += (f'  - generic: {row["score"]:g}/5\n' if is_ratings
                     else '  - button "Remove"\n')
        dom = page("My Ratings" if is_ratings else "My Watchlist", user["name"], body)
        if removed:
            dom += '- status:\n  - generic: Removed "Deadpool & Wolverine" from your watchlist.\n'
        return dom

    def finish(self, answer):
        self.add("done", {"text": answer, "success": True})
        self.data["final_answer"] = answer
        self.save()

    def save(self):
        (self.directory / "trajectory.json").write_text(json.dumps(self.data, ensure_ascii=False))

    def change_dom(self, transform):
        for filename in (self.directory / "observations").glob("*.txt"):
            filename.write_text(transform(filename.read_text()))

    def answer(self, text):
        self.data["final_answer"] = text
        self.data["steps"][-1]["params"]["text"] = text
        self.save()


class StateContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SEED_PATH.is_file():
            raise FileNotFoundError("Install the public site seed or set ROTTEN_TOMATOES_TEST_SEED")
        cls.seed_hash = hashlib.sha256(SEED_PATH.read_bytes()).hexdigest()
        cls.seed = Snapshot(SEED_PATH)
        cls.new_password_hash = bcrypt.hashpw(b"ReviewPass456!", bcrypt.gensalt(rounds=4)).decode()

    @classmethod
    def tearDownClass(cls):
        if hashlib.sha256(SEED_PATH.read_bytes()).hexdigest() != cls.seed_hash:
            raise AssertionError("The public source seed was modified")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="rt-contract-fixtures-")
        self.base = Path(self.temp.name)
        self.fixture_count = 0

    def tearDown(self):
        self.temp.cleanup()

    def fixture(self, number, relogin=False, reverse_pages=False, enter_save=False):
        self.fixture_count += 1
        f = BrowserFixture(self.base / str(self.fixture_count), number, self.seed)
        if number == 8:
            user = {"id": max(u["id"] for u in self.seed.rows["users"]) + 1,
                    "email": "testreviewer@test.com", "name": "Test Reviewer"}
            f.sql("INSERT INTO users(id,email,name,password_hash,created_at) VALUES(?,?,?,?,?)",
                  (user["id"], user["email"], user["name"], self.new_password_hash, "2026-01-01 00:00:00"))
            f.authenticate(user, registration=True)
            if relogin:
                f.add("click", {"name": "Logout"}, "/", page("Movies"))
                f.authenticate(user)
            f.add("click", {"name": "My Account"}, "/account", account(user))
            f.finish("Registered the requested account and verified its account page.")
        else:
            user = self.seed.one("users", email=f.spec["email"])
            f.authenticate(user)
            if number == 9:
                f.sql("UPDATE users SET name=? WHERE id=?", ("Robert Clark", user["id"]))
                f.add("click", {"name": "My Account"}, "/account", account(user))
                f.add("click", {"name": "Edit Profile"}, "/account/edit", page("Edit Profile", user["name"]))
                f.add("input", {"index": 10, "text": "Robert Clark"})
                f.add("press" if enter_save else "click", {"key": "Enter"} if enter_save else {"index": 11},
                      "/account", account(dict(user, name="Robert Clark")))
                f.finish("The account page now shows Robert Clark.")
            elif number == 11:
                f.sql("DELETE FROM watchlist_items WHERE movie_id=20 AND user_id=?", (user["id"],))
                f.add("click", {"name": "My Watchlist"}, "/user/watchlist", f.collection(user, "watchlist_items"))
                f.add("click", {"name": "Remove", "movie": "Deadpool & Wolverine"},
                      dom=f.collection(user, "watchlist_items", removed=True))
                f.finish("Three movies remain in David's watchlist.")
            elif number == 14:
                tables = ["watchlist_items", "user_ratings"] if reverse_pages else ["user_ratings", "watchlist_items"]
                for table in tables:
                    route = "/user/ratings" if table == "user_ratings" else "/user/watchlist"
                    f.add("click", {"name": "Ratings" if table == "user_ratings" else "My Watchlist"},
                          route, f.collection(user, table))
                f.finish("Oddity — 5/5.")
            else:
                raise ValueError("Only the four retained entrypoints belong in these fixtures")
        return f

    def verdict(self, f, expected, label):
        f.save()
        evaluate = evaluate_information if f.number == 14 else verify_lib.evaluate
        with patch("verify_lib.urlopen", side_effect=AssertionError("Offline fixtures must not call a judge")):
            result = evaluate(f.spec["task_id"], f.directory, no_llm=True)
        VERDICT_CHECKS.append((f.number, label, expected, result["pass"]))
        self.assertEqual(expected, result["pass"], label + ": " + result["reason"])
        return result

    def test_four_positive_contracts(self):
        for number in (8, 9, 11, 14):
            with self.subTest(task=number):
                self.verdict(self.fixture(number), True, "positive")

    def test_state_noop_does_not_pass_with_correct_answer(self):
        for number in (8, 9, 11):
            with self.subTest(task=number):
                f = self.fixture(number)
                shutil.copyfile(f.directory / "before.db", f.directory / "after.db")
                self.verdict(f, False, "no-op with correct answer")

    def test_final_answer_alone_cannot_replace_browser_evidence(self):
        for number in (8, 9, 11, 14):
            with self.subTest(task=number):
                f = self.fixture(number)
                done = deepcopy(f.data["steps"][-1])
                done.update(step=0, url=ORIGIN + "/", url_after=ORIGIN + "/")
                f.data["steps"] = [done]
                self.verdict(f, False, "only answer")

    def test_task_identity_origin_and_browser_action_boundaries(self):
        for number in (8, 9, 11, 14):
            for variant in ("task", "prompt", "origin", "action"):
                with self.subTest(task=number, variant=variant):
                    f = self.fixture(number)
                    if variant == "task": f.data["task_id"] = "RottenTomatoes--999"
                    elif variant == "prompt": f.data["task"] = "Only claim success."
                    elif variant == "origin": f.data["steps"][-1]["url"] = "http://other.localhost/account"
                    else: f.data["steps"][1]["action"] = "database_execute"
                    self.verdict(f, False, variant)

    def test_wrong_email_or_password_input(self):
        for number in (8, 9, 11, 14):
            for field in ("email", "password"):
                with self.subTest(task=number, field=field):
                    f = self.fixture(number)
                    for step in f.data["steps"]:
                        if step["params"].get("text") == f.spec[field]:
                            step["params"]["text"] = "someone-else@test.com" if field == "email" else "WrongPassword!"
                    self.verdict(f, False, "wrong " + field)

    def test_extra_business_writes_are_rejected_for_every_task(self):
        for number in (8, 9, 11, 14):
            with self.subTest(task=number):
                f = self.fixture(number)
                f.sql("UPDATE movies SET synopsis='Unrequested fixture change' WHERE id=1")
                self.verdict(f, False, "extra movie write")

    def test_schema_changes_are_rejected(self):
        f = self.fixture(14)
        f.sql("CREATE TABLE unrequested_table(value TEXT)")
        self.verdict(f, False, "extra schema")

    def test_registration_password_and_existing_account_boundaries(self):
        f = self.fixture(8)
        f.sql("UPDATE users SET password_hash=(SELECT password_hash FROM users WHERE email='bob.c@test.com') WHERE email='testreviewer@test.com'")
        self.verdict(f, False, "registered hash wrong")
        f = self.fixture(8)
        shutil.copyfile(f.directory / "after.db", f.directory / "before.db")
        self.verdict(f, False, "registration already existed")
        f = self.fixture(8)
        f.sql("UPDATE users SET name='Changed other account' WHERE email='alice.j@test.com'")
        self.verdict(f, False, "changed another account")

    def test_rename_is_exact_and_requires_persisted_identity(self):
        f = self.fixture(9)
        f.sql("UPDATE users SET name='Robert Clarks' WHERE email='bob.c@test.com'")
        self.verdict(f, False, "near-match name")
        f = self.fixture(9)
        f.sql("UPDATE users SET name='bob_clark' WHERE email='bob.c@test.com'")
        f.sql("UPDATE users SET name='Robert Clark' WHERE email='alice.j@test.com'")
        self.verdict(f, False, "rename wrong account")
        f = self.fixture(9)
        f.sql("UPDATE users SET email='robert@test.com' WHERE email='bob.c@test.com'")
        self.verdict(f, False, "unrequested email change")

    def test_removal_affects_only_requested_pair(self):
        f = self.fixture(11)
        f.sql("DELETE FROM watchlist_items WHERE user_id=(SELECT id FROM users WHERE email='david.k@test.com')")
        self.verdict(f, False, "extra removals")
        f = self.fixture(11)
        f.sql("UPDATE user_ratings SET score=1 WHERE user_id=(SELECT id FROM users WHERE email='david.k@test.com')")
        self.verdict(f, False, "rating changed during removal")

    def test_legal_paths_and_self_report_independence(self):
        self.verdict(self.fixture(8, relogin=True), True, "same-account re-login")
        self.verdict(self.fixture(9, enter_save=True), True, "Enter saves profile")
        f = self.fixture(8)
        f.data["success_self_report"] = False
        f.data["steps"][-1]["params"]["success"] = False
        self.verdict(f, True, "self-report flag does not decide pass")
        f = self.fixture(8)
        f.change_dom(lambda d: d.replace('  - button "Logout"', '  - link "Logout":\n    - /url: /logout'))
        self.verdict(f, True, "legacy logout link")

    def test_later_other_account_authentication_is_rejected(self):
        f = self.fixture(8, relogin=True)
        in_login = False
        for step in f.data["steps"]:
            in_login = step["url"].endswith("/login")
            if in_login and step["params"].get("text") == f.spec["email"]:
                step["params"]["text"] = "alice.j@test.com"
        self.verdict(f, False, "later identity changed")

    def test_final_ui_confirmation_is_required(self):
        for number in (8, 9):
            with self.subTest(task=number):
                f = self.fixture(number)
                f.change_dom(lambda d: d.replace('heading "' + f.spec["name"] + '"', 'heading "Different account"'))
                self.verdict(f, False, "missing account identity")
        f = self.fixture(11)
        f.change_dom(lambda d: d.replace('Removed "Deadpool & Wolverine" from your watchlist.', 'Unrelated notice'))
        self.verdict(f, False, "missing removal confirmation")

    def test_post_logout_control_requires_matching_navigation_identity(self):
        good = nav("Robert Clark") + '- main:\n  - heading "Movies"\n'
        self.assertTrue(authenticated(good, "Robert Clark"))
        self.assertTrue(authenticated(nav("Robert Clark", legacy=True), "Robert Clark"))
        for bad in (good.replace("Robert Clark", "NotRobert Clark"),
                    good.replace("My Account: Robert Clark", "My Account"),
                    good.replace('button "Logout"', 'paragraph: Logout'),
                    good.replace("My Account: Robert Clark", "My Account").replace('heading "Movies"', 'heading "Robert Clark"')):
            with self.subTest(dom=bad):
                self.assertFalse(authenticated(bad, "Robert Clark"))

    def test_count_answer_uses_current_watchlist_total(self):
        for answer in ("3", "Three movies remain.", "There are three in my watchlist.",
                       "Previously four movies; now three movies remain.", "现在有三部电影。"):
            with self.subTest(answer=answer):
                f = self.fixture(11); f.answer(answer)
                self.verdict(f, True, "legal count wording")
        for answer in ("Four movies remain.", "I rated it 3/5.", "Not three movies.",
                       "Three movies or four movies.", "Previously three movies; now four movies remain."):
            with self.subTest(answer=answer):
                self.assertFalse(count_answer(answer, 3))
        f = self.fixture(11); f.answer("Four movies remain.")
        self.verdict(f, False, "wrong final count")

    def test_r14_fixed_positive_and_negative_matrix(self):
        for label, answer, expected in (
            ("canonical", "Oddity — 5/5.", True),
            ("table", "| Movie | Personal score |\n| --- | --- |\n| Oddity | five stars |", True),
            ("wrong pair", "Oddity — 4/5.", False),
            ("extra movie", "Oddity — 5/5; Barbie — 4/5.", False),
            ("missing score", "Oddity is not in the watchlist.", False),
        ):
            with self.subTest(case=label):
                f = self.fixture(14); f.answer(answer)
                self.verdict(f, expected, label)
        f = self.fixture(14, reverse_pages=True)
        f.answer("Oddity. Its rating is five out of five.")
        self.verdict(f, True, "reverse private page order")
        f = self.fixture(14)
        for step in f.data["steps"]:
            for field in ("url", "url_after"):
                step[field] = step[field].replace("/user/watchlist", "/account")
        self.verdict(f, False, "missing watchlist comparison")
        f = self.fixture(14)
        f.sql("UPDATE user_ratings SET score=1 WHERE user_id=(SELECT id FROM users WHERE email='carol.d@test.com')")
        self.verdict(f, False, "private score changed")
        # The ninth original case (wrong user) is in the four-task credential matrix.

    def test_r14_pair_parser_accepts_equivalence_and_rejects_extra_claims(self):
        expected = {"Oddity": 5}
        for answer in ("Only Oddity (2024): 5/5.", "Oddity：五星。",
                       "Oddity is absent. It received five stars.",
                       "Nosferatu and The Substance are in both lists; Oddity: 5."):
            with self.subTest(answer=answer):
                self.assertEqual(expected, answer_pairs(answer, self.seed.rows["movies"], expected))
        for answer in ("Oddity — 5/5; Oddity — 4/5", "Oddity: 85%", "Oddity: 5/10",
                       "Oddity: 5/5, Made Up Movie: 5/5"):
            with self.subTest(answer=answer):
                with self.assertRaises(VerificationError):
                    answer_pairs(answer, self.seed.rows["movies"], expected)

    def test_missing_snapshot_or_observation_fails_closed(self):
        for label in ("after", "dom", "screenshot"):
            with self.subTest(case=label):
                f = self.fixture(8)
                if label == "after": (f.directory / "after.db").unlink()
                elif label == "dom": shutil.rmtree(f.directory / "observations")
                else: (f.directory / "screenshots" / f.data["steps"][2]["screenshot_after"]).unlink()
                self.verdict(f, False, "missing " + label)

    def test_four_cli_entrypoints_and_initial_snapshot_alias(self):
        for number in (8, 9, 11, 14):
            with self.subTest(task=number):
                f = self.fixture(number)
                (f.directory / "before.db").rename(f.directory / "initial.db")
                command = [sys.executable, str(VERIFY_DIR / f"verify_{number}.py"),
                           "--run_dir", str(f.directory), "--no_llm", "True"]
                result = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(0, result.returncode, result.stderr + result.stdout)
                self.assertTrue(json.loads(result.stdout)["pass"])
                f.answer("Only claimed success.")
                f.data["steps"] = [dict(f.data["steps"][-1], step=0, url=ORIGIN + "/", url_after=ORIGIN + "/")]
                f.save()
                result = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(1, result.returncode, result.stderr + result.stdout)
                self.assertFalse(json.loads(result.stdout)["pass"])


if __name__ == "__main__":
    run = unittest.main(verbosity=2, exit=False)
    print(json.dumps({"unittest_methods": run.result.testsRun,
                      "verdict_cases": len(VERDICT_CHECKS),
                      "positive_verdict_cases": sum(expected for _, _, expected, _ in VERDICT_CHECKS),
                      "negative_verdict_cases": sum(not expected for _, _, expected, _ in VERDICT_CHECKS),
                      "failures": len(run.result.failures), "errors": len(run.result.errors)}))
    sys.exit(0 if run.result.wasSuccessful() else 1)
