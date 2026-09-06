# walmart_careers — site notes

Mirror of https://careers.walmart.com. Port **40017** (index 17 in `websyn_start.sh`);
alt-port test container maps it to **41017**.

## Layout

| file | role |
|---|---|
| `app.py` | models, routes, scored search, deterministic SVG maps, bootstrap |
| `catalog_source.py` | the source catalog: areas, categories, 44 stores, 37 hourly + 29 salaried title families with explicit placements |
| `seed_data.py` | turns the catalog into SQLite; `build_seed_database()` is the freezer |
| `_content.py` | CMS-style prose, design constants, US/PR map outlines |
| `templates/` | 18 Jinja2 templates + `_job_card.html` macro |
| `scripts_dev/` | local-only helpers (asset harvest, smoke test); gitignored and dockerignored |

## Rebuilding the seed DB

```bash
cd sites/walmart_careers
PYTHONHASHSEED=0 python seed_data.py     # writes instance_seed/walmart_careers.db
```

Run it twice and compare md5s — the build is byte-reproducible. `build_seed_database()`
also runs `_assert_distractors()`, which fails the build if a catalog edit breaks a
volume invariant (jobs per category/store/state/shift) or a task's near-miss set.
`_assert_distractors()` never runs at import or at `/reset` time.

## Determinism rules that must hold

- one RNG: `random.Random(20260905)` in `seed_data.py`, nothing else
- `MIRROR_REFERENCE_DATE` instead of `date.today()`; no `utcnow()`/`now()` anywhere on the
  import or bootstrap path (runtime writes may use `now()` — `/reset` wipes them)
- the four werkzeug password hashes are hard-coded (werkzeug salts randomly)
- `seed_database()` and `seed_benchmark_users()` are each gated as a whole

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
