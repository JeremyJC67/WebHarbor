#!/usr/bin/env python3
"""Validate the generated Versus product tiles.

The tiles are byte-stable regenerations of ``generate_art.py`` under the pinned
toolchain. This checker enforces exact coverage (no missing, extra or stale
files), per-file size + SHA-256 equality against ``generated_asset_inventory.json``
and a full PNG decode of every file. It runs in the Docker build, mirroring the
webmd_doctor / compass / walmart_careers asset gates, so art that is missing,
altered or unaccounted for fails the build instead of degrading silently.
"""
import hashlib
import json
import sys
from pathlib import Path, PurePosixPath

from PIL import Image

SITE = Path(__file__).resolve().parent
MANAGED_ROOT = "static/images/products"


def verify():
    manifest = json.loads((SITE / "generated_asset_inventory.json").read_text())
    rows = manifest.get("assets")
    if manifest.get("schema_version") != 1 or not isinstance(rows, list):
        raise ValueError("unsupported generated asset inventory")
    if not rows:
        raise ValueError("inventory lists no assets")

    problems = []
    expected = set()
    for row in rows:
        rel = PurePosixPath(row["path"])
        if rel.is_absolute() or ".." in rel.parts or not str(rel).startswith(MANAGED_ROOT):
            problems.append(f"{rel}: path escapes {MANAGED_ROOT}")
            continue
        expected.add(str(rel))
        path = SITE / rel
        if not path.is_file():
            problems.append(f"{rel}: missing")
            continue
        data = path.read_bytes()
        if len(data) != row["bytes"]:
            problems.append(f"{rel}: {len(data)} bytes, inventory says {row['bytes']}")
        digest = hashlib.sha256(data).hexdigest()
        if digest != row["sha256"]:
            problems.append(f"{rel}: sha256 {digest[:12]}…, inventory says {row['sha256'][:12]}…")
        try:
            with Image.open(path) as im:
                im.load()
                if im.format != "PNG":
                    problems.append(f"{rel}: format {im.format}, expected PNG")
        except Exception as exc:  # noqa: BLE001 - any decode failure is a failure
            problems.append(f"{rel}: does not decode ({type(exc).__name__})")

    root = SITE / MANAGED_ROOT
    if root.is_dir():
        for path in sorted(root.rglob("*")):
            if path.is_file():
                rel = str(path.relative_to(SITE))
                if rel not in expected:
                    problems.append(f"{rel}: present but not in the inventory")

    if problems:
        print(f"Versus generated-asset check FAILED ({len(problems)} problem(s)):")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"Versus generated-asset check OK: {len(expected)} tiles verified")
    return 0


if __name__ == "__main__":
    sys.exit(verify())
