#!/usr/bin/env python3
"""verify_lib.py — shared deterministic + LLM utilities for Kaggle task verification.

Philosophy: DETERMINISTIC FIRST.
  1. Trajectory navigation check (anti knowledge-shortcut): the agent MUST have
     opened the relevant on-site page; a correct answer with no matching navigation
     is a memory-recall shortcut = FAIL.
  2. Answer check: exact / regex / token-containment / number match against frozen
     ground truth.
  3. DB after-state check (stateful tasks): query the SQLite instance DB directly —
     the strongest deterministic signal (competition_entries, votes, bookmarks,
     follows, discussions/comments, user profile fields).
  4. LLM utilities (text match, screenshot-contains) are used ONLY where exact
     matching is brittle, and are ALWAYS anchored on ground truth: the model
     verifies *presence* of given content, never supplies knowledge. One call each.
     They SKIP (never fail-close) when the LLM is unavailable, so the deterministic
     layer stays authoritative.

Input signature (per task):
  --run_dir DIR      agent trajectory dir: trajectory.json + screenshots/step_NNN.png
  --initial_db PATH  initial-state SQLite DB. Optional: when omitted the verifier fetches
                     <container>:<WEBSYN_DIR>/<site>/instance_seed/<site>.db
  --after_db PATH    after-state SQLite DB. Optional: when omitted the verifier fetches
                     <container>:<WEBSYN_DIR>/<site>/instance/<site>.db
                     (the container is --container, else $WH_CONTAINER, else "wh-review")
  --container NAME   docker container to fetch DBs from (default: $WH_CONTAINER or wh-review)
  --site NAME        site directory inside the container (default: $WH_SITE or kaggle)
  --no_llm           skip LLM-based checks (run deterministic-only)

The documented harness call (`eval_judge.py --run_dir DIR --verifier True`) passes only
--run_dir, so the DB arguments must stay optional and the container fetch is the default
path. An explicit --initial_db/--after_db always wins, which is what the offline negative
sample matrix uses. Every check stays fail-closed: if a DB cannot be obtained, the checks
that need it FAIL, and the process exits 1 with a structured JSON verdict.
Output: JSON {task_id, pass, reason, evidence[]} to stdout; exit 0 on PASS, 1 on FAIL.
"""
import argparse, base64, json, os, re, shutil, sqlite3, subprocess, sys, tempfile, urllib.request
from pathlib import Path

SITE = "kaggle"
WEBSYN_DIR = "/opt/WebSyn"
_DB_CACHE: dict = {}

# ---------------------------------------------------------------- trajectory
def load_run(run_dir):
    d = Path(run_dir)
    traj = json.loads((d / "trajectory.json").read_text())
    traj["_run_dir"] = d
    traj["_shots"] = {p.name: p for p in sorted((d / "screenshots").glob("step_*.png"))}
    return traj

def step_urls(traj):
    return [s.get("url", "") for s in traj.get("steps", [])]

def navigated_to(traj, substr, times=1):
    """Deterministic: at least `times` trajectory steps have a URL containing substr."""
    return sum(1 for u in step_urls(traj) if substr in u) >= times

def navigated_any(traj, substrs):
    return any(navigated_to(traj, s) for s in substrs)

def final_answer(traj):
    return (traj.get("final_answer") or "").strip()

def _shot(traj, name):
    if not name:
        return None
    p = traj["_shots"].get(Path(name).name)
    return p if (p and p.exists()) else None

def shot_after_url(traj, substr):
    for s in traj.get("steps", []):
        if substr in s.get("url", ""):
            p = _shot(traj, s.get("screenshot_after"))
            if p:
                return p
    return None

def last_shot(traj):
    for s in reversed(traj.get("steps", [])):
        p = _shot(traj, s.get("screenshot_after")) or _shot(traj, s.get("screenshot_before"))
        if p:
            return p
    shots = sorted(traj["_shots"].values())
    return shots[-1] if shots else None

# ---------------------------------------------------------------- deterministic answer match
def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip()).casefold()

def answer_equals(final, expected):
    return norm(final) == norm(expected)

def contains_all(final, tokens):
    f = norm(final)
    return all(norm(t) in f for t in tokens)

def contains_any(final, tokens):
    f = norm(final)
    return any(norm(t) in f for t in tokens)

def contains_number(final, n):
    """True if integer n appears as a standalone number (not a digit inside a larger
    number). Avoids '7' matching '17'/'70'/'2027'."""
    return re.search(rf"(?<!\d){int(n)}(?!\d)", final or "") is not None

def contains_score(final, value, tol=0):
    """Match the stored score exactly, allowing only an omitted leading zero."""
    s = ("%f" % float(value)).rstrip("0").rstrip(".")
    variants = {s, s.lstrip("0")}
    return any(re.search(rf"(?<![\d.]){re.escape(v)}(?!\d)", final or "")
               for v in variants if v)

# ---------------------------------------------------------------- DB state
def resolve_db(arg, container, kind):
    """Return a local SQLite path for `kind` in {"instance", "instance_seed"}.

    An explicit path from the CLI wins. Otherwise the DB is copied out of the
    docker container that serves the mirror (`docker cp`), which is the only way
    the production harness can supply it: `eval_judge.py --verifier True` passes
    just --run_dir. Returns None when the DB cannot be obtained, so callers
    fail-closed instead of crashing.
    """
    if arg:
        return arg
    site = os.environ.get("WH_SITE") or SITE
    container = container or os.environ.get("WH_CONTAINER") or "wh-review"
    key = (container, site, kind)
    if key in _DB_CACHE:
        return _DB_CACHE[key]
    source = f"{container}:{WEBSYN_DIR}/{site}/{kind}/{site}.db"
    target = Path(tempfile.mkdtemp(prefix="wh-verify-")) / f"{kind}.db"
    try:
        proc = subprocess.run(["docker", "cp", source, str(target)],
                              capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        _DB_CACHE[key] = None
        return None
    path = str(target) if proc.returncode == 0 and target.exists() else None
    _DB_CACHE[key] = path
    return path


def fetched_db_note(container=None):
    """Human-readable description of where the default DBs come from (evidence text)."""
    site = os.environ.get("WH_SITE") or SITE
    container = container or os.environ.get("WH_CONTAINER") or "wh-review"
    return f"{container}:{WEBSYN_DIR}/{site}/{{instance,instance_seed}}/{site}.db"

def db_query(db_path, sql, params=()):
    """Run a query; return rows, or None if the DB can't be opened/queried
    (corrupt/locked/missing table) so callers fail-closed instead of crashing."""
    if not db_path:
        return None
    try:
        con = sqlite3.connect(db_path)
        try:
            return con.execute(sql, params).fetchall()
        finally:
            con.close()
    except sqlite3.Error:
        return None

# --- lookups ---
def user_id_for(db_path, email):
    rows = db_query(db_path, "SELECT id FROM users WHERE email=?", (email,))
    return rows[0][0] if rows else None

def user_location(db_path, email):
    rows = db_query(db_path, "SELECT location FROM users WHERE email=?", (email,))
    return rows[0][0] if rows else None

def id_by_slug(db_path, table, slug):
    rows = db_query(db_path, f"SELECT id FROM {table} WHERE slug=?", (slug,))
    return rows[0][0] if rows else None

# --- stateful after-state helpers (all return None when DB unavailable) ---
def competition_entry(db_path, email, comp_slug):
    """(team_name,) for the user's entry in the competition, or None if not joined / DB down."""
    rows = db_query(db_path,
        "SELECT ce.team_name FROM competition_entries ce JOIN users u ON u.id=ce.user_id "
        "JOIN competitions c ON c.id=ce.competition_id WHERE u.email=? AND c.slug=?",
        (email, comp_slug))
    if rows is None:
        return None
    return rows[0][0] if rows else None

def vote_exists(db_path, email, entity_type, entity_id):
    rows = db_query(db_path,
        "SELECT 1 FROM votes v JOIN users u ON u.id=v.user_id "
        "WHERE u.email=? AND v.entity_type=? AND v.entity_id=?", (email, entity_type, entity_id))
    return None if rows is None else (len(rows) > 0)

def bookmark_exists(db_path, email, entity_type, entity_id):
    rows = db_query(db_path,
        "SELECT 1 FROM bookmarks b JOIN users u ON u.id=b.user_id "
        "WHERE u.email=? AND b.entity_type=? AND b.entity_id=?", (email, entity_type, entity_id))
    return None if rows is None else (len(rows) > 0)

def follow_exists(db_path, email, target_username):
    rows = db_query(db_path,
        "SELECT 1 FROM follows f JOIN users u ON u.id=f.user_id "
        "WHERE u.email=? AND f.target_username=?", (email, target_username))
    return None if rows is None else (len(rows) > 0)

def discussion_by(db_path, author_username, title_substr):
    """True if a discussion authored by author_username has a title containing title_substr."""
    rows = db_query(db_path,
        "SELECT 1 FROM discussions WHERE author_username=? AND lower(title) LIKE ?",
        (author_username, f"%{title_substr.lower()}%"))
    return None if rows is None else (len(rows) > 0)

def discussion_row(db_path, author_username, title_substr):
    rows = db_query(db_path,
        "SELECT title, forum FROM discussions WHERE author_username=? AND lower(title) LIKE ?",
        (author_username, f"%{title_substr.lower()}%"))
    if rows is None:
        return None
    return rows[0] if rows else None

def comment_by_on(db_path, author_username, discussion_slug):
    """List of comment bodies by author_username on the given discussion, or None."""
    rows = db_query(db_path,
        "SELECT cm.body FROM comments cm JOIN discussions d ON d.id=cm.discussion_id "
        "WHERE cm.author_username=? AND d.slug=?", (author_username, discussion_slug))
    return None if rows is None else [r[0] for r in rows]

def dataset_downloads(db_path, slug):
    rows = db_query(db_path, "SELECT downloads FROM datasets WHERE slug=?", (slug,))
    return rows[0][0] if rows else None

def scalar(db_path, table, column, slug):
    """Generic single-value fetch by slug (ground-truth anchor)."""
    rows = db_query(db_path, f"SELECT {column} FROM {table} WHERE slug=?", (slug,))
    return rows[0][0] if rows else None


def db_tables(db_path):
    """{table: [rows as sorted tuples of strings]} for every user table, or None if unreadable."""
    if not db_path:
        return None
    try:
        con = sqlite3.connect(db_path)
        try:
            tables = [r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
            out = {}
            for table in tables:
                rows = sorted(tuple("" if v is None else str(v) for v in row)
                              for row in con.execute(f'SELECT * FROM "{table}"'))
                out[table] = rows
            return out
        finally:
            con.close()
    except sqlite3.Error:
        return None


def tables_unchanged(init_db, after_db, ignore=()):
    """Tables whose content differs between the two DBs.

    Returns None when either DB is unavailable so callers can fail-closed: a
    read-only task must be able to prove that nothing was written.
    """
    before, after = db_tables(init_db), db_tables(after_db)
    if before is None or after is None:
        return None
    return [table for table in sorted(set(before) | set(after))
            if table not in ignore and before.get(table) != after.get(table)]

# ---------------------------------------------------------------- shared LLM utilities (anchored)
_NO_LLM = False


def _llm_config():
    return (os.environ.get("OPENAI_API_KEY", ""),
            os.environ.get("OPENAI_BASE_URL", ""),
            os.environ.get("JUDGE_MODEL", ""))


def _chat(messages, max_tokens=1024):
    if _NO_LLM:
        return None
    key, base, model = _llm_config()
    if not (key and base and model):
        return None
    payload = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 1.0}
    url = base.rstrip("/")
    if not url.endswith("/chat/completions"):
        url += "/chat/completions"
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {key}"})
    try:
        data = json.loads(urllib.request.urlopen(req, timeout=180).read())
    except Exception:
        return None
    try:
        return data["choices"][0]["message"]["content"]
    except Exception:
        return None

def _verdict(out):
    if out is None:
        return None, "<no reply / LLM unavailable>"
    s = out.strip()
    if not s:
        return None, "<empty reply>"
    return s.upper().startswith("PASS"), s

def llm_text_match(agent_answer, ground_truth, question):
    if _NO_LLM:
        return None, "[skipped: --no_llm]"
    out = _chat([{"role": "user", "content":
        f"You are a STRICT binary grader.\nQuestion: {question}\n"
        f"Ground-truth answer (ANCHOR — judge against THIS, never use your own knowledge): {ground_truth}\n"
        f"Agent's answer: {agent_answer}\n"
        f"Decide PASS or FAIL ignoring case/punctuation/word order/surrounding prose. "
        f"PASS only if the agent's answer is consistent with the ground truth AND actually answers the question. "
        f"Line 1: PASS or FAIL. Line 2: one-sentence reason."}])
    return _verdict(out)

def llm_screenshot_shows(shot_path, must_show, question=""):
    if _NO_LLM:
        return None, "[skipped: --no_llm]"
    b64 = base64.b64encode(Path(shot_path).read_bytes()).decode()
    out = _chat([{"role": "user", "content": [
        {"type": "text", "text":
            f"You are a STRICT binary grader. Only what is VISIBLY rendered in this screenshot counts.\n"
            f"Question the page should answer: {question}\n"
            f"Expected content to verify PRESENCE of: {must_show}\n"
            f"PASS only if the expected content (or a semantically equivalent on-screen answer) is visibly shown. "
            f"Do NOT use prior knowledge — judge only the rendered pixels.\n"
            f"Line 1: PASS or FAIL. Line 2: quote the visible evidence."},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}]}])
    return _verdict(out)

# ---------------------------------------------------------------- judge harness + CLI
class Judge:
    def __init__(self, task_id, no_llm=False):
        global _NO_LLM
        _NO_LLM = bool(no_llm)
        self.task_id = task_id
        self.no_llm = no_llm
        self.ok = True
        self.reason = ""
        self.evidence = []

    def check(self, name, cond, evidence="", llm=False):
        if llm and (self.no_llm or cond is None):
            why = "--no_llm" if self.no_llm else "LLM unavailable"
            self.evidence.append(f"[SKIP] {name} ({why}): {evidence}")
            return True
        if cond:
            self.evidence.append(f"[PASS] {name}: {evidence}")
        else:
            self.ok = False
            if not self.reason:
                self.reason = name
            self.evidence.append(f"[FAIL] {name}: {evidence}")
        return bool(cond)

    def emit(self):
        print(json.dumps({"task_id": self.task_id, "pass": self.ok,
                          "reason": self.reason, "evidence": self.evidence}, indent=2))
        sys.exit(0 if self.ok else 1)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_dir", required=True)
    # Optional: eval_judge.py --verifier True invokes the verifier with --run_dir only,
    # so the DBs default to a fetch from the mirror container (see resolve_db).
    parser.add_argument("--initial_db", default=None)
    parser.add_argument("--after_db", default=None)
    parser.add_argument("--container", default=None)
    parser.add_argument("--site", default=None)
    parser.add_argument("--no_llm", action="store_true")
    args = parser.parse_args()
    if args.site:
        os.environ["WH_SITE"] = args.site
    if args.container:
        os.environ["WH_CONTAINER"] = args.container
    return args
