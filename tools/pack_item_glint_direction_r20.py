"""Freeze source-bound glint measurements, lossless pixels and replay dependencies."""
import argparse
import copy
import importlib
import json
from pathlib import Path
import shutil
import sys

from pack_item_plane_evidence_r20 import digest, sanitize, save

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ('tools/data/item_icon_catalog_nemc_3.10.0.420447.json',
          'tools/generate_item_icon_catalog.py',
          'behavior_pack/modern_projection/projection/item_icon_data.py',
          'resource_pack/shaders/glsl/modern_projection_item_icon.vertex',
          'resource_pack/shaders/glsl/modern_projection_item_icon_world.vertex',
          'resource_pack/shaders/glsl/modern_projection_item_icon.fragment',
          'resource_pack/textures/models/modern_projection/item_icons/enchanted_glint.png',
          'resource_pack/textures/models/modern_projection/item_icons/cf75a6e96b2d3e06.png')


def copy_file(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def pack(cases, output):
    output.mkdir(parents=True, exist_ok=False)
    summary = {'schema': 1, 'production_qualified': False, 'captures': {},
               'scope': 'Both glint phase velocities and red/green dynamic additive amplitude; frame only'}
    for label, report_path, sparse_path, direction_path, assets_path in cases:
        if not label or any(char not in 'abcdefghijklmnopqrstuvwxyz0123456789-_' for char in label):
            raise ValueError('Capture label must be a simple directory name')
        source, sparse_source, direction, assets = map(Path, (report_path, sparse_path, direction_path, assets_path))
        report = json.loads(source.read_bytes())
        sparse = json.loads(sparse_source.read_bytes())
        analysis = json.loads((direction / 'analysis.json').read_bytes())
        if (not report['completed'] or report['cleanup_errors'] or not report['source_unchanged']
                or analysis['source_sha256'] != digest(source) or sparse['source_sha256'] != digest(source)
                or analysis['analyzer_sha256'] != digest(ROOT / 'tools/analyze_item_glint_direction_r20.py')):
            raise ValueError('Glint evidence must complete restoration with bound analyses')
        target = output / label
        target.mkdir()
        secret = report['session'].get('token')
        save(target / 'source-report.json', sanitize(copy.deepcopy(report), secret))
        save(target / 'sparse-analysis.json', sanitize(sparse, secret))
        shutil.copytree(direction, target / 'direction')
        for relative in ASSETS:
            path = assets / relative
            if relative in report['launch_sources'] and digest(path) != report['launch_sources'][relative]:
                raise ValueError('Asset differs from launch snapshot: ' + relative)
            copy_file(path, target / 'assets' / relative)
        for route in analysis['routes']:
            burst = report['closeup']['motion_bursts'][route]
            receipt_path = Path(burst['receipt'])
            if digest(receipt_path) != burst['sha256']:
                raise ValueError('Dense source receipt changed')
            receipt = json.loads(receipt_path.read_bytes())
            if sanitize(receipt, secret) != receipt:
                raise ValueError('Dense receipt unexpectedly contains private session data')
            copy_file(receipt_path, target / 'receipts' / (route + '-dense.json'))
            for index, frame in enumerate(row for row in receipt['frames'] if row['png'] is not None):
                raw = Path(frame['receipt']['path'])
                if digest(raw) != frame['receipt']['sha256']:
                    raise ValueError('Dense frame receipt changed')
                parsed = json.loads(raw.read_bytes())
                if sanitize(parsed, secret) != parsed:
                    raise ValueError('Frame receipt unexpectedly contains private session data')
                copy_file(raw, target / 'receipts' / route / ('%04d.json' % (index + 1)))
            rows = report['closeup']['native_reference']['captures'] if route == 'native' else report['closeup']['captures']
            row = next(row for row in rows if row['label'] == route + '_0')
            screenshot = Path(row['capture']['path'])
            if digest(screenshot) != row['capture']['sha256']:
                raise ValueError('Sparse screenshot changed')
            copy_file(screenshot, target / 'review' / (route + '.png'))
        save(target / 'provenance.json', {'original_report_sha256': digest(source),
            'source_snapshot_sha256': report['launch_sources_sha256'],
            'completed': report['completed'], 'cleanup_errors': report['cleanup_errors'],
            'source_unchanged': report['source_unchanged'],
            'direction_analyzer_sha256': analysis['analyzer_sha256'],
            'sanitization': 'Session token omitted; all pixel bytes are unchanged'})
        summary['captures'][label] = {'direction_and_speed_accepted': analysis['direction_and_speed_accepted'],
                                    'brightness_accepted': analysis['brightness_accepted'],
                                    'base_evidence_valid': analysis['base_evidence_valid']}
    importlib.import_module('analyze_item_glint_direction_r20')
    closure = {Path(module.__file__).resolve() for module in tuple(sys.modules.values())
               if getattr(module, '__file__', None)
               and Path(module.__file__).resolve().is_relative_to(ROOT)}
    closure.update(ROOT / name for name in ('tools/verify_item_glint_direction_r20.py',
        'tools/pack_item_glint_direction_r20.py', 'tests/test_item_glint_direction.py'))
    for path in sorted(closure):
        copy_file(path, output / 'source' / path.relative_to(ROOT))
    copy_file(ROOT / 'tools/verify_item_glint_direction_r20.py', output / 'verify_package.py')
    save(output / 'summary.json', summary)
    files = {path.relative_to(output).as_posix(): {'sha256': digest(path), 'bytes': path.stat().st_size}
             for path in sorted(output.rglob('*')) if path.is_file()}
    save(output / 'manifest.json', {'schema': 1, 'production_qualified': False, 'files': files})
    print(json.dumps({'files': len(files), 'bytes': sum(row['bytes'] for row in files.values()),
                      'captures': summary['captures'], 'production_qualified': False}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', nargs=5, action='append', required=True,
                        metavar=('LABEL', 'REPORT', 'SPARSE', 'DIRECTION', 'ASSETS'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    pack(args.case, args.output.resolve())
