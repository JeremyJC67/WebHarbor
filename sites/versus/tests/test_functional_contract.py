"""Regression contract for the Versus mirror.

Each test pins a defect found during review, so a later change that reintroduces
it fails here instead of in a benchmark run.

Run from the repo root:
    docker run --rm -v "$PWD:/repo:ro" -w /repo wh-review025-deps:latest \
        python3 -m unittest discover -s sites/versus/tests -v
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path, PurePosixPath

SITE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SITE_DIR.parents[1]
TASKS = SITE_DIR / "tasks.jsonl"
SITE_NAME = "versus"


def load_tasks():
    return [json.loads(line) for line in TASKS.read_text().splitlines() if line.strip()]


def build_seed(dest: Path) -> Path:
    """Generate the seed DB the way the Dockerfile does, into an isolated copy."""
    work = dest / SITE_NAME
    shutil.copytree(SITE_DIR, work)
    for sub in ("instance", "instance_seed"):
        shutil.rmtree(work / sub, ignore_errors=True)
    subprocess.run([sys.executable, "-c", "from app import app"],
                   cwd=work, check=True, capture_output=True)
    return work / "instance" / f"{SITE_NAME}.db"


class SeedDeterminism(unittest.TestCase):
    """F9: two builds of the same commit must ship byte-identical seed data."""

    def test_seed_is_byte_reproducible(self):
        digests = []
        for _ in range(2):
            with tempfile.TemporaryDirectory() as tmp:
                db = build_seed(Path(tmp))
                digests.append(hashlib.sha256(db.read_bytes()).hexdigest())
        self.assertEqual(
            digests[0], digests[1],
            "seed DB differs between builds; a random salt or other nondeterminism "
            "leaked into instance_seed, so its hash cannot be pinned",
        )


class RegistryConsistency(unittest.TestCase):
    def _sites_from_control_server(self):
        text = (REPO_ROOT / "control_server.py").read_text()
        block = re.search(r"^SITES = \[(.*?)\]", text, re.S | re.M).group(1)
        return re.findall(r"'([a-z0-9_]+)'", block)

    def _sites_from_start_script(self):
        text = (REPO_ROOT / "websyn_start.sh").read_text()
        block = re.search(r"^SITES=\((.*?)\)", text, re.S | re.M).group(1)
        return block.split()

    def test_site_registered_identically_in_both_registries(self):
        control = self._sites_from_control_server()
        start = self._sites_from_start_script()
        self.assertEqual(control, start, "control_server and websyn_start site order differ")
        self.assertIn(SITE_NAME, control)

    def test_task_urls_match_the_registered_port(self):
        port = 40000 + self._sites_from_control_server().index(SITE_NAME)
        for task in load_tasks():
            self.assertEqual(
                f"http://localhost:{port}/", task["web"],
                f"{task['id']} points at {task['web']} but the site is registered on {port}",
            )

    def test_dockerfile_exposes_the_registered_port(self):
        text = (REPO_ROOT / "Dockerfile").read_text()
        upper = int(re.search(r"EXPOSE 8101 40000-(\d+)", text).group(1))
        port = 40000 + self._sites_from_control_server().index(SITE_NAME)
        self.assertGreaterEqual(upper, port)


class TaskContract(unittest.TestCase):
    def test_every_task_has_a_verifier_and_rubric(self):
        for task in load_tasks():
            self.assertTrue(task.get("verifier_path"), f"{task['id']} has no verifier_path")
            self.assertTrue((REPO_ROOT / task["verifier_path"]).exists(),
                            f"{task['id']}: {task['verifier_path']} does not exist")
            self.assertTrue(task.get("judge_rubric"), f"{task['id']} has no judge_rubric")

    def test_task_file_carries_no_answer_key(self):
        allowed = {"web_name", "id", "ques", "web", "upstream_url",
                   "verifier_path", "judge_rubric"}
        for task in load_tasks():
            extra = set(task) - allowed
            self.assertFalse(extra, f"{task['id']} carries unexpected keys {extra}")
            self.assertNotIn("answer", task)

    def test_task_ids_are_contiguous_and_unique(self):
        ids = [t["id"] for t in load_tasks()]
        self.assertEqual(len(ids), len(set(ids)), "duplicate task ids")
        self.assertEqual(ids, [f"Versus--{i}" for i in range(len(ids))])

    def test_task_count_is_in_the_review_guide_range(self):
        self.assertGreaterEqual(len(load_tasks()), 15)
        self.assertLessEqual(len(load_tasks()), 20)


class StatefulTasksStartUnsatisfied(unittest.TestCase):
    """T1: a task that asks the agent to create state must not already be satisfied."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.db = build_seed(Path(cls._tmp.name))

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def saved_pairs(self, email):
        con = sqlite3.connect(self.db)
        try:
            rows = con.execute(
                "SELECT l.slug, r.slug FROM saved_comparison sc "
                "JOIN user u ON u.id = sc.user_id "
                "JOIN product l ON l.id = sc.left_id "
                "JOIN product r ON r.id = sc.right_id WHERE u.email = ?",
                (email,)).fetchall()
        finally:
            con.close()
        return {frozenset(pair) for pair in rows}

    def test_save_tasks_target_a_pair_not_already_saved(self):
        existing = self.saved_pairs("alice.j@test.com")
        slugs = {p[0] for p in sqlite3.connect(self.db).execute(
            "SELECT slug FROM product")}
        for task in load_tasks():
            ques = task["ques"].lower()
            if "save" not in ques:
                continue
            mentioned = frozenset(s for s in slugs
                                  if s.replace("-", " ") in ques.replace("-", " "))
            if len(mentioned) != 2:
                continue
            self.assertNotIn(
                mentioned, existing,
                f"{task['id']} asks to save a comparison Alice already has at seed "
                f"state, so the after-state is identical whether or not the agent acts",
            )


class GeneratedArt(unittest.TestCase):
    """The tiles are synthetic by design, so the contract is byte-stability."""

    def _generate(self, dest: Path):
        work = dest / SITE_NAME
        shutil.copytree(SITE_DIR, work)
        shutil.rmtree(work / "static/images/products", ignore_errors=True)
        subprocess.run([sys.executable, "generate_art.py"],
                       cwd=work, check=True, capture_output=True)
        return work

    def test_art_is_byte_reproducible_and_matches_the_inventory(self):
        inventory = json.loads((SITE_DIR / "generated_asset_inventory.json").read_text())
        self.assertEqual(inventory["schema_version"], 1)
        self.assertTrue(inventory["assets"], "inventory lists no tiles")
        digests = []
        for _ in range(2):
            with tempfile.TemporaryDirectory() as tmp:
                work = self._generate(Path(tmp))
                run = subprocess.run([sys.executable, "check_generated_assets.py"],
                                     cwd=work, capture_output=True, text=True)
                self.assertEqual(run.returncode, 0,
                                 f"asset gate failed on a fresh build:\n{run.stdout}")
                digests.append(sorted(
                    hashlib.sha256((work / row["path"]).read_bytes()).hexdigest()
                    for row in inventory["assets"]))
        self.assertEqual(digests[0], digests[1], "tiles differ between builds")

    def test_gate_rejects_a_tampered_tile(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = self._generate(Path(tmp))
            victim = work / json.loads(
                (SITE_DIR / "generated_asset_inventory.json").read_text())["assets"][0]["path"]
            victim.write_bytes(victim.read_bytes() + b"tamper")
            run = subprocess.run([sys.executable, "check_generated_assets.py"],
                                 cwd=work, capture_output=True, text=True)
            self.assertEqual(run.returncode, 1,
                             "gate passed a tampered tile; its PASS means nothing")

    def test_every_product_has_a_tile(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = build_seed(Path(tmp))
            slugs = {r[0] for r in sqlite3.connect(db).execute("SELECT slug FROM product")}
        listed = {PurePosixPath(row["path"]).stem for row in json.loads(
            (SITE_DIR / "generated_asset_inventory.json").read_text())["assets"]}
        self.assertEqual(slugs, listed, "product catalogue and tile inventory disagree")


class SyntheticDisclosure(unittest.TestCase):
    """The synthetic parts must be stated in the UI, not only in the repo."""

    def test_about_page_and_footer_name_what_is_synthetic(self):
        about = (SITE_DIR / "templates" / "about.html").read_text().lower()
        base = (SITE_DIR / "templates" / "base.html").read_text().lower()
        for token in ("synthetic", "versus score"):
            self.assertIn(token, about, f"/about does not mention {token}")
            self.assertIn(token, base, f"the footer does not mention {token}")
        self.assertIn("not affiliated", about)

    def test_notice_exists_and_covers_imagery_and_data(self):
        notice = (SITE_DIR / "NOTICE.md").read_text().lower()
        for token in ("non-affiliation", "synthetic", "removal", "versus score"):
            self.assertIn(token, notice, f"NOTICE.md does not cover {token}")


class CsrfProtection(unittest.TestCase):
    """F10: 23 of 25 sites on main install CSRFProtect; this one must too."""

    def test_app_installs_csrf_protection(self):
        source = (SITE_DIR / "app.py").read_text()
        self.assertIn("CSRFProtect", source)

    def test_state_changing_forms_carry_a_token(self):
        for template in ("compare.html", "login.html"):
            text = (SITE_DIR / "templates" / template).read_text()
            if "method=\"post\"" not in text.lower():
                continue
            self.assertIn("csrf_token", text,
                          f"{template} posts without a CSRF token field")


if __name__ == "__main__":
    unittest.main()
