# Third-party material in the Versus mirror

This file records the disposition of third-party material this site relies on, so a
reviewer can determine what is included, where it came from, and how to remove it.

## Non-affiliation and trademarks

WebHarbor is an independent research benchmark for web agents. This mirror is not
affiliated with, authorized by, endorsed by or sponsored by Versus Tech, nor by Apple,
Samsung, Google, OnePlus, Sony, Bose, Sennheiser, Canon, Nikon, Fujifilm, NVIDIA, AMD,
Garmin or Fitbit. Product and company names are used only to identify the products being
compared. No license or permission is granted or implied by their presence, and nothing
here should be read as a statement by any of those companies.

The running site makes no request to any external service. This is verified, not
asserted: a Playwright sweep of every route at four viewports recorded zero external
requests.

## Imagery — deliberately synthetic, no third-party media redistributed

**This site redistributes no third-party images, fonts or media of any kind.** The 20
product tiles under `static/images/products/` are drawn programmatically by
`generate_art.py`: a category-derived backdrop, a schematic device outline, the brand
initials and the product name, over the site's own palette. Each tile carries a visible
`SYNTHETIC ART` label. They depict no real product and reproduce no photograph.

Why, stated plainly:

- versus.com began returning CloudFront 403 to this client during the review and
  remained blocked across repeated probes. No attempt was made to work around that.
- Freely licensed photography for these specific models could not be matched reliably.
  A Wikimedia Commons sweep returned a freely licensed candidate for 18 of 20 products,
  but strict model matching showed the hits were largely the wrong item — a OnePlus 8
  for the OnePlus 12, an A7R IV for the A7 IV, a 4070 Ti Super for the 4070 Super, a
  card-slot close-up for the Nikon Z8, earbuds for over-ear headphones. Shipping those
  would inject false product facts into a benchmark whose purpose is factual navigation.
- Generated art is the precedent already merged on `main`: `webmd_doctor` ships
  Pillow-drawn initials avatars and gradient poster panels "instead of photography".

This is a deliberate deviation from the reviewer checklist's "Real images" line, and it
is the maintainers' call whether to accept it. It is recorded here rather than glossed.

Engineering contract, matching the `webmd_doctor` / `compass` / `walmart_careers` gates:

- `generate_art.py` is deterministic — no RNG, no clock, no locale, Pillow's bundled
  default font, fixed PNG compression with no ancillary chunks — so two builds of the
  same commit produce byte-identical tiles.
- `generated_asset_inventory.json` pins every tile's path, byte length and SHA-256.
- `check_generated_assets.py` enforces exact coverage (nothing missing, extra or stale),
  per-file size and SHA-256 equality, and a full PNG decode. It runs in the Docker build,
  so altered or missing art fails the build instead of degrading silently.
- The tiles are build products, not commits: `static/images/` is gitignored, and the
  inventory is what travels in Git.

No task answer depends on reading an image. All 17 verifiers are deterministic and never
open a screenshot; every graded fact is text in the DOM.

## Data

Product names, brands, release years, list prices and published specifications follow the
manufacturers' figures. **The Versus Score is not versus.com's value** — it is synthetic
benchmark data, as are all user accounts and saved comparisons. The distinction is stated
on `/about` and in the site footer on every page.

## Removal

To remove the generated art: delete `static/images/products/`, the two `generate_art.py`
/ `check_generated_assets.py` build steps from the Dockerfile, and the `<img>` references
in `templates/_product_card.html`, `product.html` and `compare.html`. The application,
its routes, its seeded data and all 17 tasks continue to function without them; only the
visual presentation changes.
