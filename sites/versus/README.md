# Versus mirror

Offline Flask mirror of `https://versus.com/` for the WebHarbor benchmark. In the
27-site registry it is site index 26 and runs on container port `40026`.

```bash
docker run -d --rm --name wh-versus -p 8101:8101 -p 40000-40026:40000-40026 webharbor:dev
curl -so /dev/null -w "%{http_code}\n" http://localhost:40026/
curl -X POST http://localhost:8101/reset/versus
```

## Build products, not assets

This site fetches nothing from Hugging Face. Both of its binary-ish artefacts are
regenerated deterministically during the Docker build and gated there:

| Artefact | Generator | Gate |
| --- | --- | --- |
| `static/images/products/*.png` (20 tiles) | `generate_art.py` | `check_generated_assets.py` — coverage, size, SHA-256, PNG decode |
| `instance_seed/versus.db` | `app.py` import side effect | `md5(instance) == md5(instance_seed)` after `/reset/versus` |

Both are byte-identical across builds. The seed's benchmark password hash is a frozen
constant (`BENCHMARK_PASSWORD_HASH`) because `generate_password_hash()` draws a fresh
scrypt salt per call, which made two builds of the same commit differ.

Regenerate locally and refresh the pinned hashes:

```bash
python3 generate_art.py --write-inventory
python3 check_generated_assets.py
```

## What is real and what is not

Product names, brands, release years, list prices and published specifications follow the
manufacturers' figures. The **Versus Score, all user accounts and all saved comparisons
are synthetic benchmark data**; product art is programmatically drawn, not photography.
`/about` and the footer say so on every page. See `NOTICE.md`.

## Catalogue

20 products across 5 categories (smartphones, headphones, cameras, graphics cards,
smartwatches), 4 benchmark accounts sharing the password `TestPass123!`, and 3 saved
comparisons seeded for `alice.j@test.com`.

## Tasks

17 tasks in `tasks.jsonl`, each with a deterministic verifier in `verify/` and a
`judge_rubric`. Ground truth is derived from the passed `initial_db` rather than frozen
in the verifier, so the expected answer moves with the seed. Navigation checks accept
only steps on this site's own origin, with the port derived from `control_server.py`'s
registry.

Every spec value renders only on detail and comparison pages; cards and the ranking list
carry Score, Price and Year. Questions are written so the answer requires a page the list
does not carry.

```bash
python3 -m unittest discover -s tests -v          # 11 regression tests
```
