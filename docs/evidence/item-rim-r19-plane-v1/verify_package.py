"""Portable hash and paired-pixel replay; no live game or repository imports."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import types

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mask_row(mask):
    y, x = np.nonzero(mask)
    return {'pixels': int(mask.sum()), 'bounds': None if not len(x) else
        [int(x.min()), int(y.min()), int(x.max()) + 1, int(y.max()) + 1]}


def expanded(mask, size=9):
    return np.asarray(Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(size))) > 0


def edge_gate():
    # Run the archived gate unchanged, providing only its three pure primitives.
    modules = {
        'analyze_item_sprite_product': {'expanded': expanded},
        'analyze_item_sprite_closeup': {'NATIVE_BODY_LIMITS': {'minimum_extent_pixels': 48}},
        'analyze_liquid_workspace': {'mask_row': mask_row}}
    for name, attributes in modules.items():
        module = types.ModuleType(name)
        module.__dict__.update(attributes)
        sys.modules[name] = module
    path = ROOT / 'source/current/tools/item_sprite_edge_pixels.py'
    spec = importlib.util.spec_from_file_location('archived_item_sprite_edge_pixels', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.native_edge_measurement


def pixels():
    report = json.loads((ROOT / 'causal/report.json').read_bytes())
    images = {row['label']: np.asarray(Image.open(ROOT / 'causal/captures' /
        Path(row['capture']['path']).name).convert('RGB')) for row in report['captures']}
    region = np.asarray(Image.open(ROOT / 'causal/region.png').convert('L')) > 0

    def difference(shown, hidden):
        return (np.max(np.abs(shown.astype(float) - hidden.astype(float)), axis=2) > 8) & region

    native_hidden = (images['native_hidden_before'].astype(float) + images['native_hidden_after']) / 2.
    stable = np.max(np.abs(images['native_hidden_before'].astype(np.int16) -
        images['native_hidden_after'].astype(np.int16)), axis=2) <= 3
    native = difference(images['native_shown'], native_hidden) & stable
    baseline = difference(images['baseline_shown'], images['baseline_hidden'])
    candidate = difference(images['offset_0.25'], images['baseline_hidden'])
    isolated = difference(images['body_hidden_item_shown'], images['body_hidden_item_hidden'])
    restore = difference(images['baseline_shown'], images['baseline_restored'])
    measure = edge_gate()
    expected = json.loads((ROOT / 'causal/recomputed/analysis.json').read_bytes())
    measured = {'native': mask_row(native), 'baseline': mask_row(baseline), 'offset_0.25': mask_row(candidate),
        'isolated': mask_row(isolated), 'baseline_restore_changed_pixels': int(restore.sum()),
        'offset_native_identical': bool(np.array_equal(candidate, native)),
        'baseline_edges_passed': measure(baseline, native)['passed'],
        'offset_edges_passed': measure(candidate, native)['passed']}
    assert measured['native'] == expected['native']
    for label, mask in (('baseline_shown', baseline), ('offset_0.25', candidate),
        ('body_hidden_item_shown', isolated)):
        assert mask_row(mask) == expected['states'][label]['observed']
        assert measure(mask, native) == expected['states'][label]['native_edges']
    assert measured['baseline_restore_changed_pixels'] == 0
    assert measured['offset_native_identical'] is True
    assert measured['baseline_edges_passed'] is False
    assert measured['offset_edges_passed'] is True
    return measured


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pixels', action='store_true')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'manifest.json').read_bytes())
    for relative, expected in manifest['files'].items():
        path = ROOT / relative
        assert path.is_file(), relative
        assert path.stat().st_size == expected['bytes'], relative
        assert digest(path) == expected['sha256'], relative
    result = {'manifest_entries': len(manifest['files']), 'hashes_valid': True, 'production_qualified': False}
    if args.pixels:
        result['pixels'] = pixels()
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
