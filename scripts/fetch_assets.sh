#!/usr/bin/env bash
# Pull per-site asset tarballs from the Hugging Face dataset and extract
# them into sites/.
#
# The dataset stores assets as <site>.tar.gz (one tarball per site) to
# dodge the small-file tax that previously made `hf download` stall on
# 4000+ tiny image files. Each tarball extracts back to
# sites/<site>/{instance_seed,static/images,static/external_cache}.
#
# "Registered" means the site is listed in control_server.py's SITES registry
# (the same list websyn_start.sh starts and the Dockerfile exposes). The
# dataset is allowed to carry archives for sites that are not registered here
# (their PRs are still open), so coverage is checked by registered site NAME,
# never by archive count.
#
# Usage:
#   ./scripts/fetch_assets.sh                 # fetch every registered site
#   ./scripts/fetch_assets.sh google_search   # fetch one site only
#   ASSETS_REVISION=abc123 ./scripts/fetch_assets.sh   # override the pin
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

# Registered sites, derived from control_server.py so the fetch scope can never
# drift from the runtime registry.
mapfile -t REGISTERED < <(python3 - <<'PY'
import ast
import pathlib
import sys

source = pathlib.Path('control_server.py').read_text()
tree = ast.parse(source)
for node in tree.body:
    if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == 'SITES' for target in node.targets):
        for name in ast.literal_eval(node.value):
            print(name)
        break
else:
    sys.exit('fetch_assets: could not read the SITES registry from control_server.py')
PY
)
if [[ ${#REGISTERED[@]} -eq 0 ]]; then
    echo "fetch_assets: the SITES registry in control_server.py is empty" >&2
    exit 1
fi

mkdir -p "$CACHE_DIR"
echo "[fetch] huggingface.co/datasets/$REPO @ $REVISION -> sites/"

if [[ -n "$ONLY_SITE" ]]; then
    if [[ ! -d "sites/$ONLY_SITE" ]]; then
        echo "fetch_assets: no such site directory: sites/$ONLY_SITE" >&2
        exit 1
    fi
    EXPECTED=("$ONLY_SITE")
    echo "[fetch] scope: $ONLY_SITE only"
else
    EXPECTED=("${REGISTERED[@]}")
    echo "[fetch] scope: ${#EXPECTED[@]} registered sites"
fi

INCLUDE_ARGS=()
for site in "${EXPECTED[@]}"; do
    INCLUDE_ARGS+=(--include "$site.tar.gz")
done

hf download "$REPO" --repo-type dataset --revision "$REVISION" \
    "${INCLUDE_ARGS[@]}" --local-dir "$CACHE_DIR"

shopt -s nullglob
missing=()
for site in "${EXPECTED[@]}"; do
    [[ -f "$CACHE_DIR/$site.tar.gz" ]] || missing+=("$site")
done
if (( ${#missing[@]} > 0 )); then
    echo "fetch_assets: revision $REVISION has no archive for ${#missing[@]} registered site(s): ${missing[*]}" >&2
    for site in "${missing[@]}"; do
        [[ -d "sites/$site" ]] || echo "  registered site without a directory either: sites/$site" >&2
    done
    exit 1
fi

extracted=0
for site in "${EXPECTED[@]}"; do
    tarball="$CACHE_DIR/$site.tar.gz"
    python3 scripts/validate_asset_archive.py "$tarball" "$site"
    echo "[fetch] extracting $site"
    python3 scripts/extract_asset_archive.py "$tarball" sites "$site"
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

echo "[fetch] done — $extracted registered site(s) extracted into sites/"
echo "[fetch] note: the dataset may also carry archives for unregistered sites; they are ignored here."
