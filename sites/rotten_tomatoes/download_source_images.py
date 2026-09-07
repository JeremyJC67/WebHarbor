"""Download only exact catalog image URLs; never scrape or guess a person photo."""
import argparse
from collections import Counter
# Re-downloads record a new hash: source bytes and Pillow versions can change.
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.request import Request, urlopen

from PIL import Image
from seed_data import BASE_DIR, CATALOG_PATH, load_catalog


def download_images(catalog, kind, output_dir):
    if kind not in ('people', 'posters'):
        raise ValueError('Unsupported image kind')
    records = catalog['persons'] if kind == 'people' else catalog['movies']
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for item in records:
        slug = item['slug']
        prefix = 'photo' if kind == 'people' else 'poster'
        # A verified manifest URL, when included in the catalog, is used literally.
        # Otherwise use the exact observed src. Do not rewrite signed CDN URLs.
        url = item.get(prefix + '_download_url') or item.get(prefix + '_url')
        result = {'slug': slug, 'source_url': url}
        if not url:
            results.append({**result, 'status': 'NOT_VERIFIED', 'reason': 'No source image URL'})
            continue
        temporary = None
        try:
            if not re.fullmatch(r'[A-Za-z0-9_-]+', slug):
                raise ValueError('Invalid catalog slug')
            request = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urlopen(request, timeout=25) as response:
                raw = response.read()
                final_url = response.url
            with Image.open(BytesIO(raw)) as image:
                image.load()
                with tempfile.NamedTemporaryFile(dir=output_dir, suffix='.jpg', delete=False) as handle:
                    temporary = Path(handle.name)
                image.convert('RGB').save(temporary, 'JPEG', quality=90, optimize=True, progressive=True)
            target = output_dir / (slug + '.jpg')
            os.replace(temporary, target)
            temporary = None
            results.append({**result, 'status': 'SUCCESS', 'final_url': final_url,
                            'path': str(target), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()})
        except Exception as error:
            # An old file may be retained, but is never counted as a successful fetch.
            results.append({**result, 'status': 'FAILED', 'error': str(error)})
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    return {'kind': kind, 'counts': dict(Counter(row['status'] for row in results)), 'results': results}


def main(kind):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', type=Path, default=CATALOG_PATH)
    parser.add_argument('--output-dir', type=Path, default=BASE_DIR / 'static' / 'images' / kind)
    options = parser.parse_args()
    report = download_images(load_catalog(options.catalog), kind, options.output_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report['counts'].get('FAILED') else 0
