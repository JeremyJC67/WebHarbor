# Drugs.com local benchmark mirror

This directory contains the Drugs.com-style WebHarbor environment. It is registered as the 25th site on container port `40024` and is intended only for deterministic software evaluation. It is not the official Drugs.com service and its fixture records are not medical guidance.

## Runtime data

`app.py` contains the tracked source fixtures and Flask application. `seed_data.py` builds a candidate database without touching the active instance or known-good seed, validates it without network access, and atomically installs it. The seed is accepted only when the `seed_metadata` version is `drugs-com-source-v3`, canonical static table counts match, SQLite integrity and foreign keys pass, and the catalog/schema digests match `seed_manifest.json`; the builder additionally verifies the canonical database byte count and SHA-256.

The seed contains 246 medication records, 105 drug classes, 69 conditions, 379 drug-condition links, 104 pill-description records, 76 drug-drug interactions, 11 explicitly drug-keyed food/alcohol interaction records, 80 simulated news records, 716 simulated review records, 15 saved-medication records, and 12 fixture users. Pill-description rows are rendered as visibly labeled synthetic diagrams and are not real product images or identification evidence. `content_inventory.json` records the provenance status and runtime treatment of every fixture family.

Run a deterministic rebuild with:

```bash
cd sites/drugs_com
PYTHONHASHSEED=0 uv run python seed_data.py
```

## Assets

The original pill descriptors still use explicitly synthetic inline SVGs. Separately, `/official-labels` contains 13 selected DailyMed product-label supplements and 13 authentic packaging-label images. They are not Drugs.com articles or pill photographs. `asset_inventory.json` binds all downloaded files, including archived SPL XML and the build-time catalog. `scripts/recover_dailymed.py` is an explicit recovery tool, never a runtime/build network dependency. HTTP handlers read the `daily_med_label` table.

The replacement HF archive must include `static/images/dailymed/` and `static/external_cache/dailymed/`; the SQLite seed remains build-generated. The old pinned 134-byte HF archive cannot build this revision. Local validation does not imply that this replacement bundle has been published or merged. Before code integration, merge the asset PR, update immutable pins and the repository-wide asset manifest, and validate a fresh download/build.

## Tests

From the repository root with the site dependencies installed:

```bash
pytest -q sites/drugs_com/tests sites/drugs_com/verify
```

The application tests cover routing, validation, authentication, ownership, state mutation, seed integrity and reset behavior. The verifier tests execute every task verifier against positive and adversarial trajectories. Task answers can be ordinary prose, bullets or simple tables; JSON is optional. Bounded deterministic checks bind facts to entities, properties and units and reject tested contradictions. See `verify/README.md` for parsing limits, saved-snapshot priority and trusted preview-origin configuration.
