"""Branding integration smoke tests; test logos are NEVER shipped as actual logos."""
import importlib.util
from pathlib import Path

from PIL import Image


def test_branding_source_wires_correct_roles():
    root = Path(__file__).resolve().parents[2]
    html = (root / 'backend/app/pwa/index.html').read_text(encoding='utf-8')
    dart = (root / 'mobile/lib/branding.dart').read_text(encoding='utf-8')
    pubspec = (root / 'mobile/pubspec.yaml').read_text(encoding='utf-8')
    for i in (1, 2):
        assert f'branding/logo-{i}.png' in html
        assert f'assets/branding/logo_{i}.png' in dart
    assert 'app_icon.png' not in dart
    assert 'flutter_launcher_icons' in pubspec
    assert 'image_path: "assets/branding/app_icon.png"' in pubspec
    assert 'apple-touch-icon.png' in html


def test_branding_installer_with_temporary_test_images(tmp_path):
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location('apply_branding', root / 'scripts/apply_branding.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    mock = tmp_path / 'mock'
    mock.mkdir()
    for i, color in enumerate(((10, 20, 40, 255), (10, 70, 20, 255), (60, 20, 30, 255)), 1):
        Image.new('RGBA', (450, 240), color).save(mock / f'{i}.png')
    project = tmp_path / 'project'
    module.ROOT = project
    module.MOBILE = project / 'mobile/assets/branding'
    module.PWA = project / 'backend/app/pwa'
    module.PWA.mkdir(parents=True)
    (module.PWA / 'sw.js').write_text("const CACHE='thd-static-v2-branding';")
    (project / 'docs').mkdir()
    info = module.install(*(mock / f'{i}.png' for i in (1, 2, 3)))
    assert info['logos_embedded']
    for p in (module.MOBILE / 'logo_1.png', module.MOBILE / 'logo_2.png', module.MOBILE / 'app_icon.png',
              module.PWA / 'branding/logo-1.png', module.PWA / 'branding/logo-2.png'):
        assert p.exists()
    with Image.open(module.PWA / 'icons/icon-192.png') as icon:
        assert icon.size == (192, 192)
        assert icon.getpixel((0, 0)) == (255, 255, 255, 255)
    with Image.open(module.PWA / 'icons/icon-512.png') as icon:
        assert icon.size == (512, 512)
    assert 'thd-static-brand-' in (module.PWA / 'sw.js').read_text()
