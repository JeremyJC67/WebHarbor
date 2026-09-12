#!/usr/bin/env python3
"""Reject unsafe or out-of-contract WebHarbor asset archive members.

An archive member is in contract when it lives inside one of the managed roots
(`instance_seed`, `static/images`, `static/external_cache`) under the site's own
root directory. A directory entry that is a bare ancestor of a managed root
(`kaggle/static`, on the way to `static/images`) carries no content of its own
and is accepted; files outside the managed roots are never accepted.
"""
from __future__ import annotations

import argparse
import tarfile
from pathlib import Path, PurePosixPath

ALLOWED_ROOTS = {"instance_seed", "static/images", "static/external_cache"}


def is_managed_member(relative: str, is_dir: bool) -> bool:
    """True when `relative` (the member path below the site root) is managed."""
    if not relative:
        return True  # the site root directory entry itself
    for root in ALLOWED_ROOTS:
        if relative == root or relative.startswith(root + "/"):
            return True
    if is_dir:
        # Ancestor directory entry such as `static` or `static/images/avatars`.
        return any(root.startswith(relative + "/") for root in ALLOWED_ROOTS)
    return False


def validate(archive: Path, expected_site: str) -> int:
    count = 0
    with tarfile.open(archive, "r:gz") as bundle:
        for member in bundle:
            path = PurePosixPath(member.name)
            parts = path.parts
            if not parts or path.is_absolute() or ".." in parts:
                raise ValueError(f"unsafe archive path: {member.name!r}")
            if any(part.startswith("._") for part in parts):
                continue
            if parts[0] != expected_site:
                raise ValueError(f"unexpected site root in archive: {member.name!r}")
            if not (member.isfile() or member.isdir()):
                raise ValueError(f"unsafe archive member type: {member.name!r}")
            relative = "/".join(parts[1:])
            if not is_managed_member(relative, member.isdir()):
                raise ValueError(f"unexpected managed path: {member.name!r}")
            count += 1
    if count == 0:
        raise ValueError("asset archive contains no managed members")
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("site")
    args = parser.parse_args()
    count = validate(args.archive, args.site)
    print(f"[fetch] validated {count} managed members for {args.site}")


if __name__ == "__main__":
    main()
