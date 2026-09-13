#!/usr/bin/env python3
"""Generate the Versus product tiles.

The mirror ships deliberately synthetic product art rather than photography.
See NOTICE.md for why and for the disposition of that choice. This module is
the single source of those images: it draws one tile per product from the seed
data, deterministically, so two builds of the same commit produce byte-identical
files whose hashes are pinned in generated_asset_inventory.json.

Determinism rules observed here:
  * no RNG, no clock, no locale - every value is derived from the product row
  * Pillow's bundled default font, so no system font can change the output
  * PNG written with fixed compression and no ancillary chunks

Usage:
    python3 generate_art.py [--out static/images/products] [--write-inventory]
"""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SITE = Path(__file__).resolve().parent
OUT_REL = "static/images/products"
SIZE = (480, 360)

# Panel and ink follow the site's dark palette (static/css/main.css).
PANEL = (23, 18, 31)
INK = (245, 243, 247)
MUTED = (162, 155, 176)

# One accent per category, used for the backdrop wash and the device outline.
CATEGORY_ACCENT = {
    "smartphones": (124, 92, 255),
    "headphones": (236, 72, 153),
    "cameras": (56, 189, 248),
    "graphics-cards": (34, 197, 94),
    "smartwatches": (251, 146, 60),
    "cities": (96, 165, 250),
    "universities": (250, 204, 21),
}
DEFAULT_ACCENT = (124, 92, 255)


def _mix(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def _initials(brand, name):
    """Two letters at most, taken from the brand, falling back to the name."""
    source = (brand or "").strip()
    if source in ("", "-", "—"):
        source = (name or "?").strip()
    parts = [p for p in source.replace("-", " ").split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[1][0]).upper()


def _device_box(category):
    """A silhouette that hints at the product class without depicting a product."""
    w, h = SIZE
    cx, cy = w // 2, h // 2 - 10
    shapes = {
        "smartphones": (cx - 46, cy - 86, cx + 46, cy + 86, 18),
        "headphones": (cx - 78, cy - 78, cx + 78, cy + 78, 78),
        "cameras": (cx - 104, cy - 62, cx + 104, cy + 62, 16),
        "graphics-cards": (cx - 122, cy - 46, cx + 122, cy + 46, 10),
        "smartwatches": (cx - 54, cy - 62, cx + 54, cy + 62, 22),
        # Not devices: a skyline block and a pediment stand in for the entity.
        "cities": (cx - 116, cy - 40, cx + 116, cy + 70, 6),
        "universities": (cx - 100, cy - 54, cx + 100, cy + 62, 8),
    }
    return shapes.get(category, (cx - 90, cy - 70, cx + 90, cy + 70, 16))


def draw_tile(slug, name, brand, category):
    accent = CATEGORY_ACCENT.get(category, DEFAULT_ACCENT)
    img = Image.new("RGB", SIZE, PANEL)
    d = ImageDraw.Draw(img)

    # Backdrop wash: horizontal bands from panel toward the category accent.
    for y in range(SIZE[1]):
        t = (y / SIZE[1]) * 0.22
        d.line([(0, y), (SIZE[0], y)], fill=_mix(PANEL, accent, t))

    x0, y0, x1, y1, radius = _device_box(category)
    d.rounded_rectangle((x0, y0, x1, y1), radius=radius,
                        fill=_mix(PANEL, accent, 0.10),
                        outline=_mix(accent, INK, 0.25), width=3)

    # Category-specific detail, still schematic.
    if category == "cameras":
        r = 34
        d.ellipse((x0 + 30, (y0 + y1) // 2 - r, x0 + 30 + 2 * r, (y0 + y1) // 2 + r),
                  outline=_mix(accent, INK, 0.45), width=3)
    elif category == "graphics-cards":
        for i in range(3):
            r = 26
            cx = x0 + 44 + i * 72
            d.ellipse((cx - r, (y0 + y1) // 2 - r, cx + r, (y0 + y1) // 2 + r),
                      outline=_mix(accent, INK, 0.35), width=2)
    elif category == "cities":
        for i, h in enumerate((70, 104, 52, 88, 60)):
            x = x0 + 14 + i * 44
            d.rectangle((x, y1 - h, x + 32, y1 - 4), outline=_mix(accent, INK, 0.4), width=2)
    elif category == "universities":
        d.polygon([(x0 + 6, y0 + 6), (x1 - 6, y0 + 6), ((x0 + x1) // 2, y0 - 26)],
                  outline=_mix(accent, INK, 0.45))
        for i in range(4):
            x = x0 + 30 + i * 48
            d.line([(x, y0 + 14), (x, y1 - 10)], fill=_mix(accent, INK, 0.35), width=3)
    elif category == "headphones":
        d.arc((x0 + 16, y0 + 10, x1 - 16, y1 - 10), start=200, end=340,
              fill=_mix(accent, INK, 0.45), width=6)

    initials = _initials(brand, name)
    font = ImageFont.load_default(size=54)
    box = d.textbbox((0, 0), initials, font=font)
    d.text(((SIZE[0] - (box[2] - box[0])) // 2 - box[0],
            (y0 + y1) // 2 - (box[3] - box[1]) // 2 - box[1]),
           initials, font=font, fill=INK)

    label_font = ImageFont.load_default(size=19)
    label = name if len(name) <= 34 else name[:33] + "…"
    lbox = d.textbbox((0, 0), label, font=label_font)
    d.text(((SIZE[0] - (lbox[2] - lbox[0])) // 2 - lbox[0], SIZE[1] - 44),
           label, font=label_font, fill=MUTED)

    # Deliberate, visible marker that this is synthetic art, not a photograph.
    tag_font = ImageFont.load_default(size=13)
    d.text((14, 14), "SYNTHETIC ART", font=tag_font, fill=_mix(MUTED, accent, 0.5))
    return img


def products():
    """Read the catalogue straight from app.py's seed definition."""
    import app  # noqa: WPS433 - import side effect creates/loads the DB
    with app.app.app_context():
        rows = app.Product.query.join(app.Category).order_by(app.Product.id).all()
        return [(p.slug, p.name, p.brand, p.category.slug) for p in rows]


def write_all(out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for slug, name, brand, category in products():
        path = out_dir / f"{slug}.png"
        draw_tile(slug, name, brand, category).save(
            path, format="PNG", optimize=False, compress_level=6)
        data = path.read_bytes()
        written.append({"path": f"{OUT_REL}/{slug}.png", "bytes": len(data),
                        "sha256": hashlib.sha256(data).hexdigest()})
    return sorted(written, key=lambda r: r["path"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(SITE / OUT_REL))
    ap.add_argument("--write-inventory", action="store_true")
    args = ap.parse_args()

    rows = write_all(Path(args.out))
    print(f"wrote {len(rows)} product tiles to {args.out}")
    if args.write_inventory:
        target = SITE / "generated_asset_inventory.json"
        target.write_text(json.dumps(
            {"schema_version": 1,
             "generator": "sites/versus/generate_art.py",
             "toolchain": "Pillow 11.0.0, Python 3.12, bundled default font",
             "assets": rows}, indent=2) + "\n")
        print(f"wrote {target}")


if __name__ == "__main__":
    main()
