"""Shared fixtures for the walmart_careers verifier tests.

Synthetic SQLite snapshots (same table shapes as instance_seed/walmart_careers.db,
only the columns the verifiers read are populated) and a hand-written trajectory
writer in the agent_demo/agent.py format. No docker, no LLM.
"""
from __future__ import annotations

import copy
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

VERIFY_DIR = Path(__file__).resolve().parents[1]
BASE = "http://localhost:41019"
PASSWORD = "TestPass123!"

SCHEMA = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY, email TEXT NOT NULL UNIQUE, username TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL DEFAULT '', first_name TEXT NOT NULL DEFAULT '',
    last_name TEXT NOT NULL DEFAULT '', phone TEXT NOT NULL DEFAULT '',
    city TEXT NOT NULL DEFAULT '', state TEXT NOT NULL DEFAULT '',
    password_hash TEXT NOT NULL DEFAULT 'x', created_at TEXT NOT NULL DEFAULT '2026-08-01 00:00:00'
);
CREATE TABLE stores (id INTEGER PRIMARY KEY, store_number TEXT NOT NULL, street TEXT NOT NULL DEFAULT '');
CREATE TABLE jobs (job_id TEXT PRIMARY KEY, title TEXT NOT NULL DEFAULT '', store_id INTEGER NOT NULL DEFAULT 1);
CREATE TABLE saved_jobs (
    id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, job_id TEXT NOT NULL,
    saved_at TEXT NOT NULL DEFAULT '2026-08-01 00:00:00', UNIQUE (user_id, job_id)
);
CREATE TABLE applications (
    id INTEGER PRIMARY KEY, job_id TEXT NOT NULL, user_id INTEGER, email TEXT NOT NULL,
    first_name TEXT NOT NULL DEFAULT '', last_name TEXT NOT NULL DEFAULT '', phone TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'Submitted', confirmation_no TEXT NOT NULL UNIQUE,
    submitted_at TEXT NOT NULL DEFAULT '2026-08-01 00:00:00'
);
"""

# Same ids/emails/relations as the frozen seed (values are synthetic).
SEED_USERS = [
    dict(id=1, email="alice.j@test.com", username="alice.j", first_name="Alice", last_name="Johnson",
         phone="479-555-0134", city="Bentonville", state="AR"),
    dict(id=2, email="bob.c@test.com", username="bob.c", first_name="Bob", last_name="Chen",
         phone="206-555-0178", city="Seattle", state="WA"),
    dict(id=3, email="carol.d@test.com", username="carol.d", first_name="Carol", last_name="Davis",
         phone="253-555-0119", city="Tacoma", state="WA"),
    dict(id=4, email="david.k@test.com", username="david.k", first_name="David", last_name="Kim",
         phone="214-555-0166", city="Dallas", state="TX"),
]
SEED_SAVED = [
    (1, 1, "CP-9046-10913"), (2, 1, "CP-2503-11505"), (3, 1, "CP-5991-12522"),
    (4, 1, "CP-6088-12101"), (5, 1, "R-2423457"), (6, 1, "CP-4137-10533"),
    (7, 2, "CP-5991-11940"), (8, 2, "CP-6038-12357"), (9, 2, "R-2420377"),
    (10, 3, "CP-4137-10959"), (11, 3, "CP-6318-12289"),
    (12, 4, "CP-4750-11130"), (13, 4, "R-2429348"),
]
SEED_APPLICATIONS = [
    dict(id=1, job_id="CP-144-11515", user_id=1, email="alice.j@test.com", phone="479-555-0134", confirmation_no="WMC-000001"),
    dict(id=2, job_id="CP-6014-11937", user_id=2, email="bob.c@test.com", phone="206-555-0178", confirmation_no="WMC-000002"),
    dict(id=3, job_id="CP-2073-12751", user_id=3, email="carol.d@test.com", phone="253-555-0119", confirmation_no="WMC-000003"),
    dict(id=4, job_id="R-2434655", user_id=4, email="david.k@test.com", phone="214-555-0166", confirmation_no="WMC-000004"),
]


class State:
    """Mutable copy of the seeded users / saved_jobs / applications tables."""

    def __init__(self) -> None:
        self.users = copy.deepcopy(SEED_USERS)
        self.saved = list(SEED_SAVED)
        self.applications = copy.deepcopy(SEED_APPLICATIONS)

    # -- mutators -----------------------------------------------------------
    def add_user(self, email: str, **fields: Any) -> int:
        new_id = max(u["id"] for u in self.users) + 1
        self.users.append(dict(id=new_id, email=email, username=email.split("@")[0],
                               first_name="New", last_name="Candidate", phone="", city="", state="", **fields))
        return new_id

    def set_profile(self, user_id: int, **fields: Any) -> None:
        for user in self.users:
            if user["id"] == user_id:
                user.update(fields)
                return
        raise KeyError(user_id)

    def add_saved(self, user_id: int, job_id: str) -> None:
        new_id = max(row[0] for row in self.saved) + 1
        self.saved.append((new_id, user_id, job_id))

    def remove_saved(self, user_id: int, job_id: str) -> None:
        before = len(self.saved)
        self.saved = [row for row in self.saved if not (row[1] == user_id and row[2] == job_id)]
        assert len(self.saved) == before - 1, f"no saved row {user_id}/{job_id}"

    def add_application(self, job_id: str, user_id: int | None, email: str, phone: str) -> str:
        new_id = max(a["id"] for a in self.applications) + 1
        confirmation = f"WMC-{new_id:06d}"
        self.applications.append(dict(id=new_id, job_id=job_id, user_id=user_id, email=email,
                                      phone=phone, confirmation_no=confirmation))
        return confirmation

    # -- persistence --------------------------------------------------------
    def write(self, path: Path) -> Path:
        connection = sqlite3.connect(path)
        try:
            connection.executescript(SCHEMA)
            for user in self.users:
                connection.execute(
                    "INSERT INTO users(id, email, username, display_name, first_name, last_name, phone, city, state) "
                    "VALUES (:id, :email, :username, :first_name || ' ' || :last_name, :first_name, :last_name, :phone, :city, :state)",
                    user,
                )
            connection.executemany("INSERT INTO saved_jobs(id, user_id, job_id) VALUES (?, ?, ?)", self.saved)
            for application in self.applications:
                connection.execute(
                    "INSERT INTO applications(id, job_id, user_id, email, first_name, last_name, phone, confirmation_no) "
                    "VALUES (:id, :job_id, :user_id, :email, 'F', 'L', :phone, :confirmation_no)",
                    application,
                )
            connection.commit()
        finally:
            connection.close()
        return path


def step(path: str, action: str = "click", text: str | None = None) -> dict[str, Any]:
    """One trajectory step in the agent.py shape; ``path`` is relative to BASE."""
    params: dict[str, Any] = {"text": text} if text is not None else {}
    url = path if path.startswith("http") else f"{BASE}{path}"
    return {"url": url, "action": action, "params": params}


def login_steps(email: str) -> list[dict[str, Any]]:
    return [
        step("/login", "input", email),
        step("/login", "input", PASSWORD),
        step("/login", "click"),
    ]


def only_paths(steps: list[dict[str, Any]], *allowed: str) -> list[dict[str, Any]]:
    """Keep the steps whose URL path is one of ``allowed`` (shortcut trajectories)."""
    from urllib.parse import urlparse

    def path_of(item: dict[str, Any]) -> str:
        return urlparse(item["url"]).path.rstrip("/") or "/"

    return [item for item in steps if path_of(item) in allowed]


def write_run(run_dir: Path, task_id: str, steps: list[dict[str, Any]], answer: str) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    numbered = []
    for index, item in enumerate(steps):
        numbered.append({"step": index, **item, "screenshot_before": f"step_{index:03d}.png",
                         "screenshot_after": f"step_{index + 1:03d}.png"})
    trajectory = {
        "task": "synthetic", "task_id": task_id, "start_url": f"{BASE}/", "model": "unit-test",
        "max_steps": 15, "steps": numbered, "terminated": True,
        "termination_reason": "agent_done" if answer else "max_steps",
        "final_answer": answer if answer else None,
    }
    (run_dir / "trajectory.json").write_text(json.dumps(trajectory, indent=2), encoding="utf-8")


class VerifierTestCase(unittest.TestCase):
    """Base class: ``self.N`` selects verify_N.py."""

    N = -1

    @property
    def task_id(self) -> str:
        return f"Walmart Careers--{self.N}"

    def verdict(
        self,
        steps: list[dict[str, Any]],
        answer: str,
        initial: State | None = None,
        after: State | None = None,
        task_id: str | None = None,
        snapshots_in_run_dir: bool = False,
    ) -> dict[str, Any]:
        initial = initial or State()
        after = after or State()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_dir = root / "run"
            write_run(run_dir, task_id or self.task_id, steps, answer)
            if snapshots_in_run_dir:
                initial.write(run_dir / "initial.db")
                after.write(run_dir / "after.db")
                command = [sys.executable, str(VERIFY_DIR / f"verify_{self.N}.py"), "--run_dir", str(run_dir)]
            else:
                command = [
                    sys.executable, str(VERIFY_DIR / f"verify_{self.N}.py"), "--run_dir", str(run_dir),
                    "--initial_db", str(initial.write(root / "initial.db")),
                    "--after_db", str(after.write(root / "after.db")),
                ]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertTrue(result.stdout.strip(), f"verifier printed nothing; stderr={result.stderr}")
            verdict = json.loads(result.stdout)
            verdict["returncode"] = result.returncode
            return verdict

    def assertPasses(self, verdict: dict[str, Any]) -> None:
        self.assertTrue(verdict["pass"], verdict["evidence"])
        self.assertEqual(verdict["returncode"], 0)
        self.assertEqual(verdict["reason"], "all checks passed")

    def assertFailsOn(self, verdict: dict[str, Any], reason: str) -> None:
        self.assertFalse(verdict["pass"], verdict["evidence"])
        self.assertEqual(verdict["returncode"], 1)
        self.assertEqual(verdict["reason"], reason, verdict["evidence"])
