"""Replay the original blue-orchid h0 lifecycle from a portable evidence package."""
import argparse
import ast
import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter


def load_definitions(path, names, scope, strip_imports=False):
    tree = ast.parse(path.read_text(encoding='utf-8-sig'))
    nodes = [node for node in tree.body
             if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names]
    if {node.name for node in nodes} != set(names):
        raise ValueError('Pinned replay definitions missing: ' + str(path))
    if strip_imports:
        # Use the same pinned pure helpers without importing their game-facing modules.
        for node in nodes:
            node.body = [child for child in node.body
                         if not isinstance(child, (ast.Import, ast.ImportFrom))]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), scope)


def remap(value, mapping, root):
    if isinstance(value, dict):
        return {key: remap(child, mapping, root) for key, child in value.items()}
    if isinstance(value, list):
        return [remap(child, mapping, root) for child in value]
    return str(root / mapping[value]) if isinstance(value, str) and value in mapping else value


def replay_pixels(root, report):
    inputs = root / 'inputs'
    scope = dict(Image=Image, ImageChops=ImageChops, ImageDraw=ImageDraw,
                 ImageFilter=ImageFilter, math=math, hashlib=hashlib, json=json, Path=Path)
    load_definitions(inputs / 'camera.py', ('clamp', 'OrbitCamera'), scope)
    load_definitions(inputs / 'plant_alpha_geometry.py',
                     ('face_alpha_spans', 'planar_alpha_spans'), scope)
    load_definitions(inputs / 'verify_snow_plant_visibility.py',
                     ('green_mask', 'snow_plant_mask', 'maximum', 'count', 'changed',
                      'capture_frame', 'convex_hull', 'editor_snow_geometry',
                      'editor_cross_above_snow', 'bands', 'compare_controls'), scope,
                     strip_imports=True)
    load_definitions(inputs / 'verify_centered_snow_profiles.py', ('shape_metrics',), scope)
    runner = inputs / 'run_snow_scene_lifecycle_r20.py'
    tree = ast.parse(runner.read_text(encoding='utf-8-sig'))
    steps = [node.value for node in tree.body if isinstance(node, ast.Assign)
             and any(isinstance(target, ast.Name) and target.id == 'STEPS' for target in node.targets)]
    if len(steps) != 1:
        raise ValueError('Pinned lifecycle step declaration missing')
    scope['STEPS'] = ast.literal_eval(steps[0])
    load_definitions(runner, ('snow_control_checks', 'camera_stable'), scope, strip_imports=True)
    load_definitions(inputs / 'native_draw_response.py', ('changed_pixels', 'native_clock'), scope)
    load_definitions(inputs / 'analyze_snow_product_r20.py',
                     ('walk', 'verified_path', 'equal_mask'), scope)
    load_definitions(inputs / 'analyze_snow_lifecycle_r20.py', ('response_checks', 'analyze'), scope)
    result = scope['analyze'](report)
    if not result['workflow_accepted'] or result['production_accepted']:
        raise ValueError('Original minimal lifecycle did not replay as its declared subset')
    captures = {row['screenshot']['path']: row for row in report['capture_observations']}
    if len(captures) != result['capture_count']:
        raise ValueError('Native captures lack unique pre-validation observations')
    for row in captures.values():
        if row['phase'] != 'captured_before_validation' or not row['state']['current_source']:
            raise ValueError('Capture has no current pre-validation source')
        if not scope['camera_stable'](row['camera_state'], (35., 10., 2.8), (0., -.12)):
            raise ValueError('Observed native camera did not converge')
        guard = row['empty_placeholder']
        if guard['product_source_changed'] or guard['matched'] != len(guard['nodes']):
            raise ValueError('Placeholder observation changed')
        if any(node['after'] is not False for node in guard['nodes']):
            raise ValueError('Empty placeholder remained visible at capture')
        capture = row['screenshot']['capture']
        if (capture['foreground_unchanged'] is not True
                or capture['noactivation_requested'] is not True
                or capture['background_safe'] is not True):
            raise ValueError('Capture lacks its original background observation')
    result.update(capture_observations_verified=len(captures),
                  pure_replay_method='Unchanged pinned AST definitions; local helper imports supplied from pinned sources')
    return result


def verify(root, pixels=False):
    manifest = json.loads((root / 'manifest.json').read_bytes())
    actual = {path.relative_to(root).as_posix() for path in root.rglob('*')
              if path.is_file() and path.name != 'manifest.json' and '__pycache__' not in path.parts}
    if actual != set(manifest['files']):
        raise ValueError('Snow lifecycle package file set differs')
    for relative, record in manifest['files'].items():
        path = (root / relative).resolve(strict=True)
        if not path.is_relative_to(root):
            raise ValueError('Snow lifecycle evidence escapes package')
        if path.stat().st_size != record['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
            raise ValueError('Snow lifecycle evidence bytes changed: ' + relative)
    receipt = json.loads((root / 'lifecycle/receipt.json').read_bytes())
    launch = json.loads((root / 'control/launch-inputs.json').read_bytes())
    report_raw = (root / 'lifecycle/report.json').read_bytes()
    report = json.loads(report_raw)
    if receipt['report_sha256'] != hashlib.sha256(report_raw).hexdigest():
        raise ValueError('Wrapper receipt does not bind the original report')
    if any(receipt[key] is not True for key in ('process_completed', 'completed', 'passed',
                                               'restored', 'source_unchanged', 'host_data_unchanged')):
        raise ValueError('Original wrapper receipt is incomplete or changed')
    if receipt['returncode'] != 0 or receipt['files'] != launch['files']:
        raise ValueError('Wrapper exit or product source inventory differs')
    digest = hashlib.sha256(json.dumps(receipt['files'], sort_keys=True,
                                      separators=(',', ':')).encode('ascii')).hexdigest()
    if digest != receipt['source_contract_sha256'] or digest != manifest['source_contract_sha256']:
        raise ValueError('Product source contract differs')
    audit = json.loads((root / 'control/source-audit.json').read_bytes())
    if audit['files'] != receipt['files'] or not audit['matches_launch_and_receipt']:
        raise ValueError('Post-close source audit differs from original inventory')
    frozen = json.loads((root / 'control/external-host-manifest.json').read_bytes())
    plan = json.loads((root / 'control/frozen-plan.json').read_bytes())
    if hashlib.sha256((root / 'control/external-host-manifest.json').read_bytes()).hexdigest() != plan['external_host_manifest_sha256']:
        raise ValueError('Original frozen external host manifest differs')
    for relative, binding in manifest['input_bindings'].items():
        if hashlib.sha256((root / relative).read_bytes()).hexdigest() != binding['sha256']:
            raise ValueError('Pure replay source differs from frozen input')
        name = Path(relative).name
        original = ('behavior_pack/modern_projection/projection/' + name
                    if name in ('camera.py', 'scene.py', 'ui.py') else 'tools/' + name)
        if binding['sha256'] != (receipt['files'][original] if name in ('camera.py', 'scene.py', 'ui.py')
                                 else frozen['files'][original]):
            raise ValueError('Replay source is not bound by its original source manifest')
    if (report['plant'], report['height']) != ('blue_orchid', 0):
        raise ValueError('Lifecycle subset differs')
    if (not all(report[key] is True for key in ('completed', 'passed', 'restored'))
            or report['cleanup_errors'] or len(report['steps']) != 9
            or report['persistent_library_writes'] or report['qualification_changed']):
        raise ValueError('Original report does not meet the minimal lifecycle contract')
    samples = report['resource_checks']
    if not samples or any(row['commit_available_bytes'] != row['commit_limit_bytes'] - row['commit_total_bytes']
                          or row['commit_available_bytes'] < 6 * 1024 ** 3 for row in samples):
        raise ValueError('Canonical execution-boundary commit gate changed')
    placeholder = report['empty_placeholder_diagnostic']
    if (placeholder['product_source_changed'] or not placeholder['uniform_before_every_capture']
            or not placeholder['cleanup']['restored']):
        raise ValueError('Original placeholder cleanup is incomplete')
    exits = json.loads((root / 'control/process-exits.json').read_bytes())
    for name in ('game', 'mcdk'):
        row = exits['processes'][name]
        if (row['state'] != 'exited' or row['pid'] != receipt['session'][name + '_pid']
                or row['identity'] != receipt['session'][name + '_identity']):
            raise ValueError('Exact process-exit identity differs')
    result = {'verified': True, 'files': len(manifest['files']), 'pixels_replayed': False,
              'subset': {'plant': 'blue_orchid', 'height': 0, 'editing_steps': 9},
              'source_unchanged_evidence': 'lifecycle/receipt.json and control/source-audit.json',
              'source_contract_sha256': digest, 'source_count': len(receipt['files']),
              'resource_sample_count': len(samples),
              'minimum_available_commit_bytes': min(row['commit_available_bytes'] for row in samples),
              'workflow_accepted': False, 'production_accepted': False,
              'full_snow_acceptance': False}
    if pixels:
        replay = replay_pixels(root, remap(report, manifest['original_to_package'], root))
        result.update(pixels_replayed=replay['pixels_replayed'], workflow_accepted=replay['workflow_accepted'],
                      capture_count=replay['capture_count'], replay=replay)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--pixels', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = verify(args.package.resolve(strict=True), args.pixels)
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='ascii')
    print(json.dumps({key: value for key, value in result.items() if key != 'replay'}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
