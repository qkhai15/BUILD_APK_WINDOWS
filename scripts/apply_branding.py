#!/usr/bin/env python3
"""Install the three ORIGINAL supplied logos in Flutter and PWA.

Logo 1 and 2: shown inside each UI. Logo 3: launcher / home-screen icon.
Does not redraw, infer, or synthesize the missing logos.
Requires: python -m pip install Pillow
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageOps, UnidentifiedImageError

ROOT = Path(__file__).resolve().parents[1]
MOBILE = ROOT / 'mobile' / 'assets' / 'branding'
PWA = ROOT / 'backend' / 'app' / 'pwa'


def load_verified(path: Path) -> Image.Image:
    if not path.is_file():
        raise ValueError(f'Cannot find actual image: {path}')
    try:
        with Image.open(path) as raw:
            if raw.width < 100 or raw.height < 100:
                raise ValueError(f'Logo must have at least 100px each direction: {path}')
            if raw.width * raw.height > 70_000_000:
                raise ValueError(f'Logo too large: {path}')
            return ImageOps.exif_transpose(raw).convert('RGBA')
    except (OSError, UnidentifiedImageError) as exc:
        raise ValueError(f'Unsupported or corrupt image: {path}') from exc


def keep_original(image: Image.Image, limit: int = 1200) -> Image.Image:
    result = image.copy()
    result.thumbnail((limit, limit), Image.Resampling.LANCZOS)
    return result


def launcher_icon(image: Image.Image, size: int, *, transparent: bool = False) -> Image.Image:
    # Contain the whole original logo (never crop or recolor) and leave safe
    # margins so Android round/adaptive and PWA maskable icons do not clip it.
    result = Image.new('RGBA', (size, size), (0, 0, 0, 0) if transparent else (255, 255, 255, 255))
    inner = image.copy()
    max_size = int(size * .68)
    inner.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    result.alpha_composite(inner, ((size - inner.width) // 2, (size - inner.height) // 2))
    return result


def install(logo1: Path, logo2: Path, app_icon: Path) -> dict:
    # Validate all 3 before writing any assets.
    images = [load_verified(p) for p in (logo1, logo2, app_icon)]
    MOBILE.mkdir(parents=True, exist_ok=True)
    (PWA / 'branding').mkdir(parents=True, exist_ok=True)
    (PWA / 'icons').mkdir(parents=True, exist_ok=True)

    for i, img in enumerate(images[:2], 1):
        normalized = keep_original(img)
        normalized.save(MOBILE / f'logo_{i}.png', optimize=True)
        normalized.save(PWA / 'branding' / f'logo-{i}.png', optimize=True)

    launcher_icon(images[2], 1024).save(MOBILE / 'app_icon.png', optimize=True)
    launcher_icon(images[2], 1024, transparent=True).save(MOBILE / 'app_icon_foreground.png', optimize=True)
    for size in (192, 512):
        launcher_icon(images[2], size).save(PWA / 'icons' / f'icon-{size}.png', optimize=True)
    launcher_icon(images[2], 180).save(PWA / 'icons' / 'apple-touch-icon.png', optimize=True)

    # Avoid stale service-worker icons on installed PWAs after a new logo upload.
    sw_file = PWA / 'sw.js'
    sw = sw_file.read_text(encoding='utf-8')
    digest = hashlib.sha256((MOBILE / 'app_icon.png').read_bytes()).hexdigest()[:12]
    import re
    sw = re.sub(r"const CACHE='thd-static-[^']+';", f"const CACHE='thd-static-brand-{digest}';", sw)
    sw_file.write_text(sw, encoding='utf-8')
    status = {
        'logo_1': 'inside app (PWA + Flutter)',
        'logo_2': 'inside app (PWA + Flutter)',
        'logo_3': 'launcher icon (Android APK + PWA + iOS home screen)',
        'logos_embedded': True,
        'app_icon_sha256_prefix': digest,
    }
    (ROOT / 'docs' / 'BRANDING_STATUS.json').write_text(json.dumps(status, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return status


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--logo-1', type=Path, required=True, help='Original logo #1 PNG/JPG/WEBP')
    parser.add_argument('--logo-2', type=Path, required=True, help='Original logo #2 PNG/JPG/WEBP')
    parser.add_argument('--app-icon', type=Path, required=True, help='Original third logo, OUTSIDE app')
    args = parser.parse_args()
    status = install(args.logo_1, args.logo_2, args.app_icon)
    print(json.dumps(status, ensure_ascii=False, indent=2))
    print('NEXT: build Android APK to apply launcher icon; restart/reinstall PWA if cached icon persists.')


if __name__ == '__main__':
    main()
