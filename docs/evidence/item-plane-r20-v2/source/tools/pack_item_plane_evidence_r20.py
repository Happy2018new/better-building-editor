"""Retain owner-bound item-plane captures with sanitized replayable reports."""
import argparse
import copy
import hashlib
import importlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True) + '\n', encoding='ascii')


def sanitize(value, secret):
    if isinstance(value, dict):
        return {key: sanitize(data, secret) for key, data in value.items() if key.lower() != 'token'}
    if isinstance(value, list):
        return [sanitize(data, secret) for data in value]
    if secret and isinstance(value, str):
        return value.replace(secret, '[REDACTED]')
    return value


def retain_captures(value, destination, secret, retained):
    if isinstance(value, dict):
        path = value.get('path')
        if isinstance(path, str) and path.lower().endswith('.png') and 'sha256' in value:
            source = Path(value['path'])
            assert digest(source) == value['sha256'], 'Changed capture: ' + str(source)
            target = destination / 'captures' / source.name
            if source in retained:
                assert target == retained[source]
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                receipt = sanitize(json.loads(source.with_suffix('.capture.json').read_bytes()), secret)
                receipt['path'] = str(target.resolve())
                save(target.with_suffix('.capture.json'), receipt)
                retained[source] = target
            value['path'] = str(target.resolve())
        for child in value.values():
            retain_captures(child, destination, secret, retained)
    elif isinstance(value, list):
        for child in value:
            retain_captures(child, destination, secret, retained)


def retain_analysis_sources(output):
    # Freeze the analyzer's actual import closure, including generated registry data.
    importlib.import_module('analyze_visible_items_r16')
    importlib.import_module('analyze_item_sprite_sides')
    importlib.import_module('analyze_item_dense_motion_r17')
    paths = {Path(module.__file__).resolve() for module in tuple(sys.modules.values())
             if getattr(module, '__file__', None)
             and Path(module.__file__).resolve().is_relative_to(ROOT)}
    paths.update(ROOT / relative for relative in (
        'tools/generate_item_icon_catalog.py', 'tools/run_visible_items_r16.py',
        'tools/item_sprite_native_reference.py', 'tools/pack_item_plane_evidence_r20.py',
        'tools/verify_item_plane_evidence_r20.py',
        'tools/data/item_icon_catalog_nemc_3.10.0.420447.json',
        'behavior_pack/modern_projection/projection/item_icon_data.py',
        'resource_pack/models/modern_projection/item_icons/cf75a6e96b2d3e06_mesh.json',
        'resource_pack/textures/models/modern_projection/item_icons/cf75a6e96b2d3e06.png',
        'resource_pack/shaders/glsl/modern_projection_item_icon.vertex',
        'resource_pack/shaders/glsl/modern_projection_item_icon_world.vertex',
        'resource_pack/shaders/glsl/modern_projection_item_icon.fragment'))
    for path in sorted(paths):
        target = output / 'source' / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    shutil.copy2(ROOT / 'tools/verify_item_plane_evidence_r20.py', output / 'verify_package.py')


def compact_evidence(specification, output, glint=False):
    label, path = specification.split('=', 1)
    if not label or any(character not in 'abcdefghijklmnopqrstuvwxyz0123456789-_' for character in label):
        raise ValueError('Compact labels must be simple directory names')
    source = Path(path).resolve()
    raw = json.loads(source.read_bytes())
    if not raw['completed'] or raw['cleanup_errors'] or not raw['source_unchanged']:
        raise ValueError('Compact evidence did not complete restoration')
    destination = output / ('glint' if glint else 'compact') / label
    destination.mkdir(parents=True, exist_ok=False)
    analysis = source.parent.with_name(source.parent.name + '-analysis')
    retained = [analysis / 'analysis.json']
    if glint:
        dense = source.parent.with_name(source.parent.name + '-dense-analysis')
        retained.extend(dense / name for name in ('analysis.json', 'editor.gif', 'world.gif',
            'world_missing.gif', 'native.gif', 'editor.png', 'world.png', 'world_missing.png', 'native.png'))
    else:
        retained.append(analysis / 'contact-sheet.png')
    for index, original in enumerate(retained):
        target = destination / ('sparse-analysis.json' if glint and index == 0 else original.name)
        shutil.copy2(original, target)
    provenance = {'scope': 'Compact review only; original PNGs and receipts remain in ignored local runtime',
        'original_report': str(source), 'original_report_sha256': digest(source),
        'source_snapshot_sha256': raw['launch_sources_sha256'],
        'completed': raw['completed'], 'source_unchanged': raw['source_unchanged'],
        'cleanup_errors': raw['cleanup_errors'], 'production_qualified': False,
        'original_analysis_sha256': {str(original): digest(original) for original in retained}}
    save(destination / 'provenance.json', provenance)
    return provenance


def pack(captures, output, compact=(), glint=()):
    output.mkdir(parents=True, exist_ok=False)
    summary = {'schema': 1, 'production_qualified': False, 'captures': {},
        'scope': 'Frozen flat-item front-plane candidate; individual poses retain independent gates',
        'owner_boundary': {'frame_layout_0': 'Uses the mesh front plane',
            'shelf_layout_1_3': 'Existing shader overrides point.z with 0.3125',
            'campfire_layout_4_7': 'Existing shader overrides point.z with 0.05',
            'lectern': 'No flat-item plan; handled by the independently gated book owner'}}
    for specification in captures:
        label, path = specification.split('=', 1)
        if not label or any(character not in 'abcdefghijklmnopqrstuvwxyz0123456789-_' for character in label):
            raise ValueError('Capture labels must be simple directory names')
        source = Path(path)
        raw = json.loads(source.read_bytes())
        if not raw['completed'] or raw['cleanup_errors'] or not raw['source_unchanged']:
            raise ValueError('Only completed, restored, stable-source reports can enter this package')
        destination = output / label
        report = sanitize(copy.deepcopy(raw), raw['session'].get('token'))
        retained = {}
        retain_captures(report, destination, raw['session'].get('token'), retained)
        report_path = destination / 'report.json'
        save(report_path, report)
        command = [sys.executable, '-X', 'utf8', str(ROOT / 'tools/analyze_visible_items_r16.py'),
                   str(report_path), str(destination / 'analysis'), '--world-plain-only']
        result = subprocess.run(command, cwd=str(ROOT), check=True, capture_output=True,
                                text=True, encoding='utf8')
        (destination / 'analysis.stdout.txt').write_text(result.stdout, encoding='utf8')
        analysis = json.loads((destination / 'analysis/analysis.json').read_bytes())
        if not analysis['evidence_valid']:
            raise ValueError('Rebased evidence failed validity: ' + label)
        summary['captures'][label] = {'original_report_sha256': digest(source),
            'retained_report_sha256': digest(report_path), 'retained_images': len(retained),
            'source_snapshot_sha256': raw['launch_sources_sha256'],
            'resource_contract': raw['resource_contract'],
            'view_configuration': raw['view_configuration'],
            'requested_cases': analysis['requested_cases'],
            'completed_cases': analysis['completed_cases'],
            'all_bodies_passed': analysis['all_bodies_passed'],
            'all_native_bodies_passed': analysis['all_native_bodies_passed'],
            'all_native_edges_passed': analysis['all_native_edges_passed'],
            'static_pose_accepted': analysis['static_pose_accepted']}
    summary['compact'] = {row.split('=', 1)[0]: compact_evidence(row, output) for row in compact}
    summary['glint'] = {row.split('=', 1)[0]: compact_evidence(row, output, True) for row in glint}
    retain_analysis_sources(output)
    save(output / 'summary.json', summary)
    files = {path.relative_to(output).as_posix(): {'sha256': digest(path), 'bytes': path.stat().st_size}
             for path in sorted(output.rglob('*')) if path.is_file()}
    save(output / 'manifest.json', {'schema': 1, 'production_qualified': False,
                                  'original_package_root': str(output.resolve()), 'files': files})
    print(json.dumps({'files': len(files), 'bytes': sum(row['bytes'] for row in files.values()),
        'poses': sum(len(row['completed_cases']) for row in summary['captures'].values()),
        'all_static_poses_accepted': all(row['static_pose_accepted'] for row in summary['captures'].values()),
        'production_qualified': False}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', action='append', required=True, help='label=absolute-report-path')
    parser.add_argument('--compact', action='append', default=[], help='label=report-path; adjacent -analysis folder required')
    parser.add_argument('--glint', action='append', default=[], help='label=report-path; adjacent sparse/dense analysis required')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    pack(args.capture, args.output.resolve(), args.compact, args.glint)
