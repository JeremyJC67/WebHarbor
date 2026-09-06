# walmart_careers — site notes

Mirror of https://careers.walmart.com. Port **40019** (index 19 in `websyn_start.sh`, the 20th and last site);
alt-port test container maps it to **41019**.

## Layout

| file | role |
|---|---|
| `app.py` | models, routes, scored search, deterministic SVG maps, bootstrap |
| `catalog_source.py` | the source catalog: areas, categories, 44 stores, 37 hourly + 29 salaried title families with explicit placements, hub copy, trending job ids |
| `seed_data.py` | turns the catalog into SQLite; `build_seed_database()` is the freezer |
| `_content.py` | static chrome strings only: headings, boilerplate prose, design constants, US/PR map outlines |
| `templates/` | 19 Jinja2 templates + `_job_card.html` macro |
| `static/` | `css/`, `js/`, `icons/`, `fonts/` in git; `images/` HF-managed |
| `scripts_dev/` | local-only helpers and build-time invariants; gitignored and dockerignored |

Everything a handler renders about a job, a store or a hub comes from SQLAlchemy.
`_content.py` holds no per-record content: hub name/blurb/image live on `Store`,
and the trending flag lives on `Job.is_trending`.

## Rebuilding the seed DB

```bash
cd sites/walmart_careers
PYTHONHASHSEED=0 python seed_data.py     # writes instance_seed/walmart_careers.db
```

Run it twice and compare md5s — the build is byte-reproducible.

`build_seed_database()` also runs the build-time invariant checks, which fail the
build if a catalog edit breaks a volume invariant (jobs per category/store/state/
shift) or a benchmark task's near-miss set. Those checks live in
`scripts_dev/assert_distractors.py`, which the freezer loads by path *only if the
file exists* — it is git-ignored and docker-ignored, so it never reaches the shipped
tree, and a checkout without it builds the identical database and prints a note that
the checks were skipped. Nothing in `seed_data.py` or `app.py` encodes what a task
is looking for. The checks never run at import, bootstrap or `/reset` time.

## Determinism rules that must hold

- one RNG: `random.Random(20260905)` in `seed_data.py`, nothing else
- `MIRROR_REFERENCE_DATE` instead of `date.today()`; no `utcnow()`/`now()` anywhere on the
  import or bootstrap path (runtime writes may use `now()` — `/reset` wipes them)
- the four werkzeug password hashes are hard-coded (werkzeug salts randomly)
- `seed_database()` and `seed_benchmark_users()` are each gated as a whole

## Local dev helpers (`scripts_dev/`, never shipped)

```bash
python scripts_dev/serve.py 5017            # run with Jinja auto-reload on
python scripts_dev/walkthrough.py <base_url> [<control-plane reset url>]
python scripts_dev/leak_audit.py  <base_url>     # writes leak_audit.md
python scripts_dev/robustness.py  <base_url>
python scripts_dev/shots.py       <base_url> <out_dir>   # 1440px screenshots
```

`assert_distractors.py` is not run directly — the freezer imports it by path.

`assert_distractors.py`, `walkthrough.py`, `leak_audit.py`, `robustness.py` and
`VERIFICATION.md` hold the ground-truth answers, which is exactly why `scripts_dev/`
is in both `.gitignore` and `.dockerignore`.

## Assets

Brand chrome (`static/icons/`, `static/fonts/`) is committed; photography
(`static/images/`) is HF-managed. Everything was pulled from the live site:
`cms.careers.walmart.com/content/dam/careers/...`, `careers.walmart.com/assets/svgs/...`,
and the `EverydaySansUI` / `LivingDesign` font files from `i5.walmartimages.com`.
`scripts_dev/harvest_assets.py` records the exact URL → filename mapping and re-downloads
them; images are then downscaled to 1600px wide (16 MB total).

## Things that are deliberately not mirrored

Google Maps (replaced by a deterministic server-rendered SVG cluster map on `/results`
and an SVG pin card on the detail page), the LLM search assistant (replaced by ordinary
query params with token-overlap scoring), Workday/OIDC login (local email + password),
the OTP apply flow (two-step local form), and the Future roles / Content tabs (explicit
empty-state panels).
