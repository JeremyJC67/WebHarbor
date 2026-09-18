#!/usr/bin/env bash
# Pull per-site asset tarballs from the Hugging Face dataset and extract
# them into sites/.
#
# The dataset stores assets as <site>.tar.gz (one tarball per site) to
# dodge the small-file tax that previously made `hf download` stall on
# 4000+ tiny image files. Each tarball extracts back to
# sites/<site>/{instance_seed,static/images,static/external_cache}.
#
# Usage:
#   ./scripts/fetch_assets.sh                 # fetch all sites at pinned rev
#   ./scripts/fetch_assets.sh google_search   # fetch one site only
#   ASSETS_REVISION=abc123 ./scripts/fetch_assets.sh   # override pin
#
# Requires:
#   - hf CLI  (pip install -U "huggingface_hub[cli]")
#   - (optional) HF auth if the dataset becomes gated: hf auth login  (or set HF_TOKEN env)
set -euo pipefail
cd "$(dirname "$0")/.."

REPO=$(awk '/^repo:/ {print $2}' .assets-revision)
REVISION="${ASSETS_REVISION:-$(awk '/^revision:/ {print $2}' .assets-revision)}"
ONLY_SITE="${1:-}"
CACHE_DIR="sites/.cache/tarballs/$REVISION"

if ! command -v hf >/dev/null 2>&1; then
    echo "fetch_assets: 'hf' CLI not found. Install with: pip install -U \"huggingface_hub[cli]\"" >&2
    exit 1
fi

mkdir -p "$CACHE_DIR"
echo "[fetch] huggingface.co/datasets/$REPO @ $REVISION -> sites/"

if [[ -n "$ONLY_SITE" ]]; then
    INCLUDES=("$ONLY_SITE.tar.gz")
    echo "[fetch] scope: $ONLY_SITE only"
else
    # Request exactly the archives this checkout registers. The dataset may also
    # hold archives for sites whose code has not merged yet; downloading them
    # would waste bandwidth and make the inventory below ambiguous.
    INCLUDES=()
    for site_dir in sites/*/; do
        [[ -d "$site_dir" ]] || continue
        INCLUDES+=("$(basename "$site_dir").tar.gz")
    done
    echo "[fetch] scope: ${#INCLUDES[@]} registered site(s)"
fi

# Optional site pins allow a reviewed contributor bundle to be fetched while
# its central HF publication is pending. An explicit global revision override
# intentionally bypasses both scoped repository and revision settings.
TARBALLS=()
for archive in "${INCLUDES[@]}"; do
    site=${archive%.tar.gz}
    [[ "$site" =~ ^[a-z0-9_]+$ && -d "sites/$site" ]] || { echo "Unknown site: $site" >&2; exit 1; }
    asset_repo="$REPO"
    asset_revision="$REVISION"
    destination="$CACHE_DIR"
    if [[ -z "${ASSETS_REVISION:-}" ]]; then
        scoped_revision=$(awk -v key="site.$site:" '$1 == key {print $2}' .assets-revision)
        scoped_repo=$(awk -v key="site.$site.repo:" '$1 == key {print $2}' .assets-revision)
        if [[ -n "$scoped_revision" ]]; then
            [[ "$scoped_revision" =~ ^[0-9a-f]{40}$ ]] || { echo "Non-immutable scoped revision for $site" >&2; exit 1; }
            asset_revision="$scoped_revision"
            asset_repo="${scoped_repo:-$REPO}"
            destination="sites/.cache/tarballs/scoped/$site/$asset_revision"
        elif [[ -n "$scoped_repo" ]]; then
            echo "Scoped repository needs an immutable revision: $site" >&2; exit 1
        fi
    fi
    hf download "$asset_repo" "$archive" --repo-type dataset --revision "$asset_revision" --local-dir "$destination"
    tarball="$destination/$archive"
    [[ -f "$tarball" ]] || { echo "Missing required archive: $tarball" >&2; exit 1; }
    expected_sha=$(awk -v key="site.$site.sha256:" '$1 == key {print $2}' .assets-revision)
    if [[ -n "$expected_sha" && -z "${ASSETS_REVISION:-}" ]]; then
        [[ "$expected_sha" =~ ^[0-9a-f]{64}$ ]] || { echo "Invalid archive hash: $site" >&2; exit 1; }
        actual_sha=$(sha256sum "$tarball" | cut -d' ' -f1)
        [[ "$actual_sha" == "$expected_sha" ]] || { echo "Archive hash mismatch: $site" >&2; exit 1; }
    fi
    TARBALLS+=("$tarball")
done
extracted=0
for tarball in "${TARBALLS[@]}"; do
    site=$(basename "$tarball" .tar.gz)
    if [[ -n "$ONLY_SITE" && "$site" != "$ONLY_SITE" ]]; then continue; fi
    python3 scripts/validate_asset_archive.py "$tarball" "$site"
    echo "[fetch] extracting $site"
    python3 scripts/extract_asset_archive.py "$tarball" sites "$site"
    # An archive can outlive the code that used it: a site may stop shipping a
    # managed root, or stop generating per-record art. asset_inventory.json is
    # the declared contract for what the site actually serves, and the build
    # validates it, so prune managed files the contract does not declare instead
    # of leaving stale members to fail the inventory gate.
    python3 scripts/sync_assets_to_inventory.py "sites/$site"
    migrator="sites/$site/migrate_seed.py"
    database="sites/$site/instance_seed/$site.db"
    if [[ -f "sites/$site/.build-generated-seed" ]]; then
        rm -rf "sites/$site/instance_seed"
    elif [[ -f "$migrator" && -f "$database" ]]; then
        echo "[fetch] applying tracked $site seed migration"
        PYTHONHASHSEED=0 python3 "$migrator" "$database"
    fi
    extracted=$((extracted + 1))
done

if [[ -n "$ONLY_SITE" && $extracted -ne 1 ]]; then
    echo "fetch_assets: did not extract requested site $ONLY_SITE" >&2
    exit 1
fi
echo "[fetch] done — $extracted site(s) extracted into sites/"
