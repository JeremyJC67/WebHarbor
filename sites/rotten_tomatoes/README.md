# Rotten Tomatoes mirror

A fixed catalog of 147 movies with local demo accounts, watchlists, ratings and reviews. Original contribution: [derenlei, PR #26](https://github.com/aiming-lab/WebHarbor/pull/26).

The site uses port **40019** in the current 20-site image. From the repository root, fetch the immutable asset revision in `.assets-revision`, then run `./scripts/build.sh webharbor:review`. The candidate assets are on [HF PR #55](https://huggingface.co/datasets/ChilleD/WebHarbor/discussions/55), still awaiting maintainer merge.

See the [review report](../../docs/reviews/rotten-tomatoes/README.md) for source provenance, screenshots, reproducible checks and the current unresolved acceptance items. This candidate is not yet ready for approval.

`data/source_catalog.json` is the offline source catalog. Runtime requests read SQLite. `refresh_seed.py --help` documents explicit seed rebuilding into a separate output; it does not silently overwrite an existing populated runtime database. Unknown source facts remain unknown. Demo account data is synthetic benchmark state.

Seven candidate tasks are defined in `tasks.jsonl`. Each has its own entry point under `verify/`. Verifiers require a complete native `trajectory.json` and PNG screenshots, plus frozen `before.db` (or `initial.db`) and `after.db` captured before reset. Synchronous DOM sidecars under `observations/` are supported; without them, the configured vision judge must validate screenshot-anchored claims. Agent statements do not replace observed UI or persisted state. Use the repository's `agent_demo/eval_judge.py` entry point with an absolute `--run_dir` and `--verifier True`.
