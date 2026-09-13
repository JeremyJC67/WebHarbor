# UC Berkeley mirror

Offline Flask mirror of `https://www.berkeley.edu/`. In the 29-site registry it is site index 28 and runs on container port `40028`. Every college, department, programme, faculty member, research centre, article, event and account is deterministic synthetic benchmark data; only the page chrome mirrors upstream.

## Runtime

```bash
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python Flask==3.1.0 Flask-SQLAlchemy==3.1.1 Flask-Login==0.6.3 \
  Flask-WTF==1.2.2 Flask-Bcrypt==1.0.1 email-validator==2.2.0   # the shared pins; no site-specific deps
cd sites/berkeley && PYTHONHASHSEED=0 ../../.venv/bin/python seed_data.py      # writes instance_seed/berkeley.db
PORT=40028 ../../.venv/bin/python app.py
```

There is no Hugging Face archive for this site: `.build-generated-seed` marks it, `./scripts/fetch_assets.sh berkeley` skips it, and the Docker build regenerates `instance_seed/berkeley.db` from the tracked `seed_data.py` (`cd /opt/WebSyn/berkeley && rm -rf instance instance_seed && PYTHONHASHSEED=0 python seed_data.py && rm -rf instance`). The seed is byte-reproducible — md5 `3001bcf4bcec169f4192c08609160ab6`, identical under `PYTHONHASHSEED=0` and `=1` — because the four benchmark password hashes are precomputed bcrypt strings, every `created_at` is the frozen clock, and `User.email`/`User.username` carry `unique=True` without `index=True` (SQLAlchemy emits named indexes in set-iteration order, which moved SQLite root pages between runs).

## Frozen benchmark clock

`app.py` defines `BENCHMARK_NOW = datetime(2026, 5, 12)` and uses it everywhere a date is compared or stamped (the `/events` upcoming/past/today filters, the homepage "Upcoming events" block, and the `created_at` / `published_date` column defaults via `utcnow()`). No request or seed path calls `datetime.utcnow()`, so the rendered site is identical on any run date; against the seeded calendar `/events` admits 52 of 64 rows, 15 of them Lecture. Reseeding with a different `now` means re-pinning the verifier contract in `verify/verify_lib.py` (schema hash, counts, catalog fingerprint).

## Imagery

The mirror ships **no images by design**: `static/css/` and `static/js/` hold only `.gitkeep`, `templates/base.html` carries a single inline stylesheet, and the logo is a CSS circle. `.requires-images` is absent, so `check_assets.sh` treats the empty `static/images/` as expected rather than a gap. This is a deliberate visual-fidelity compromise for a text-and-listing site: every task is graded on rendered text, tables and links.

## Seeded rows

| Model | Rows | Model | Rows |
|---|---|---|---|
| colleges | 14 | departments | 30 |
| programmes | 83 (25 PhD / 21 BA / 16 BS / 16 MS / MBA, JD, MEng, MD, MPH ×1; 17 GRE-required, 1 online) | faculty | 82 (19 EECS) |
| research centres | 25 | news articles | 121 (7 Athletics) |
| events | 64 (19 Lecture / 14 Career / …) | users | 4 |

Benchmark accounts: `alice`, `bob`, `carol`, `dave` `@berkeley.edu`, password `test1234` (public by design; the hashes are hardcoded in `seed_data.py`). The `bookmarks` table starts empty, so the two stateful tasks bind their insert/delete ordering to the row ids the app assigns.

## Routes

`/`, `/news` (search + category + pagination), `/news/<slug>`, `/academics`, `/programs` (search, college and degree filters, pagination), `/programs/<slug>`, `/events` (category + upcoming/past/today), `/events/<id>`, `/research`, `/research/<slug>`, `/departments`, `/departments/<slug>`, `/admissions`, `/about`, `/search` (programmes / news / events / faculty / centres), `/faculty` (name, interest and department filters), `/faculty/<slug>`, `/login`, `/register`, `/logout` (POST-only, CSRF-protected: a prefetching GET gets 405), `/account` (bookmarks), `/bookmark/add` (POST), `/bookmark/remove` (POST), `/_health`.

Article detail, programme detail, event detail, faculty profiles and centre pages are pure reads: no GET path writes the database, so a read-only benchmark task's after-state always equals its initial snapshot. `sites/berkeley/tests/` holds the runnable checks: registry/seed integration, the answer-leak sweep (`test_answer_leaks.py`) and the app-robustness suite (`test_app_robustness.py`).

## Grading contract

`sites/berkeley/verify/` holds the deterministic verifiers (one per `tasks.jsonl` row), the shared `verify_lib.py`/`ground_truth.py`, and `TASK_REVIEW.md` with the per-row ACCEPT/DROP/ADDED record. See `verify/README.md` for the snapshot contract and how to run them.
