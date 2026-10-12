"""Bind constant-color native frame route diagnostics to frozen source bytes."""
import argparse
from collections import deque
import hashlib
import json
import os
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

from flat_frame_item_visual_checks import SWITCH, capture_payload
from trace_flat_frame_editor import LOAD, SAVE, RESTORE_PROFILES
from verify_debug_blueprints import Client, INSTALL_PROBE, RESTORE, write_json
from verify_debug_visuals import SAVE_VISUAL, camera_restore_code
from verify_native_entity_appearances import execute
from verify_sign_visuals import SignCheck, load, world_sample
from visual_environment import SETUP_DAYLIGHT, RESTORE_DAYLIGHT

ROOT = Path(__file__).resolve().parents[1]
MARKER_COLORS = {'magenta': (1, 0, 1), 'green': (0, 1, 0),
                 'cyan': (0, 1, 1), 'yellow': (1, 1, 0), 'red': (1, 0, 0)}


def freeze_sources(output):
    paths = [Path(__file__), ROOT / 'tools/trace_flat_frame_editor.py',
             ROOT / 'tools/verify_sign_visuals.py', ROOT / 'tools/flat_frame_item_visual_checks.py']
    paths.extend(sorted((ROOT / 'resource_pack/materials').glob('*')))
    paths.extend(sorted((ROOT / 'resource_pack/shaders/glsl').glob('modern_projection*')))
    paths.extend((ROOT / 'behavior_pack/modern_projection/projection' / name)
                 for name in ('static_frame_item.py', 'static_frame_item_data.py',
                              'geometry_palette.py', 'occupancy_shader.py', 'bridge.py', 'tiles.py'))
    paths.append(ROOT / 'resource_pack/models/netease_block/preview_item_minecraft_diamond_sword_0_f2_r0.json')
    directory = output.with_suffix('.sources')
    directory.mkdir(parents=True, exist_ok=False)
    rows = []
    for path in paths:
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        payload = path.read_bytes()
        frozen = directory / relative
        frozen.parent.mkdir(parents=True, exist_ok=True)
        frozen.write_bytes(payload)
        rows.append({'source': str(relative), 'path': str(frozen.resolve()),
                     'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()})
    return rows


def largest_component(mask):
    pixels = bytearray(mask.tobytes())
    width, height = mask.size
    largest = 0
    for seed, value in enumerate(pixels):
        if not value:
            continue
        queue = deque((seed,))
        pixels[seed] = 0
        size = 0
        while queue:
            index = queue.popleft()
            size += 1
            x, y = index % width, index // width
            neighbors = []
            if x:
                neighbors.append(index - 1)
            if x + 1 < width:
                neighbors.append(index + 1)
            if y:
                neighbors.append(index - width)
            if y + 1 < height:
                neighbors.append(index + width)
            for neighbor in neighbors:
                if pixels[neighbor]:
                    pixels[neighbor] = 0
                    queue.append(neighbor)
        largest = max(largest, size)
    return largest


def marker_pixels(capture, color='magenta', hidden=None):
    expected = MARKER_COLORS[color]
    with Image.open(capture_payload(capture)) as image:
        width, height = image.size
        crop = (width // 3, height // 3, width * 2 // 3, height * 2 // 3)
        colors = image.convert('RGB').crop(crop)
        mask = Image.new('L', colors.size)
        selected = []
        for red, green, blue in colors.getdata():
            marked = all(value >= 240 if high else value <= 32
                         for value, high in zip((red, green, blue), expected))
            selected.append(255 if marked else 0)
        mask.putdata(selected)
        center = (width // 2 - crop[0], height // 2 - crop[1])
        ImageDraw.Draw(mask).rectangle((center[0] - 24, center[1] - 24,
                                       center[0] + 24, center[1] + 24), fill=0)
        if hidden is not None:
            with Image.open(capture_payload(hidden)) as baseline:
                if baseline.size != image.size:
                    raise ValueError('Hidden marker control dimensions changed')
                delta = ImageChops.difference(colors, baseline.convert('RGB').crop(crop))
                red, green, blue = delta.split()
                changed = ImageChops.lighter(ImageChops.lighter(red, green), blue).point(
                    lambda value: 255 if value > 12 else 0)
                mask = ImageChops.multiply(mask, changed)
        pixels = sum(mask.histogram()[1:])
        box = mask.getbbox()
        connected = largest_component(mask)
    return {'crop': crop, 'pixels': pixels, 'color': color,
            'crosshair_excluded_radius': 24, 'bbox_within_crop': box,
            'largest_connected_pixels': connected, 'hidden_actor_control': hidden is not None,
            'positive': connected >= 80}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--sign-control', action='store_true')
    parser.add_argument('--frame-marker', choices=tuple(MARKER_COLORS), default='magenta')
    parser.add_argument('--sign-marker', choices=tuple(MARKER_COLORS), default='green')
    parser.add_argument('--score-report', type=Path, help='Append corrected marker analysis offline')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh report')
    if args.score_report:
        payload = args.score_report.read_bytes()
        original = json.loads(payload)
        rows = {key: row['shown'] for key, row in original['world'].items()}
        if 'sign_control' in original:
            rows['sign_control'] = original['sign_control']['shown']
        evidence = {'schema': 1, 'scope': 'Offline route marker analysis excluding the inverse-color crosshair',
                    'production_rendering_accepted': False,
                    'source_report': str(args.score_report.resolve()),
                    'source_report_sha256': hashlib.sha256(payload).hexdigest(),
                    'tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    'markers': {key: {color: marker_pixels(row['screenshot'], color, row['hidden_screenshot'])
                                      for color in MARKER_COLORS}
                                for key, row in rows.items()}}
        write_json(args.output, evidence)
        print(json.dumps(evidence['markers']))
        return 0
    helper = os.environ.get('MCDEV_NATIVE_CAPTURE_HELPER')
    if not helper or Path(helper).resolve() != ROOT / 'tools/capture_native_window.py':
        parser.error('Owner-bound background WGC helper is required')
    evidence = {'schema': 1, 'completed': False, 'passed': False,
                'production_rendering_accepted': False, 'restored': False,
                'scope': 'Constant-color material-route diagnostic; no world block writes',
                'session_file': os.environ.get('MCDEV_SESSION_FILE'),
                'sources': freeze_sources(args.output), 'world': {},
                'sign_control_requested': args.sign_control, 'expected_frame_marker': args.frame_marker,
                'expected_sign_marker': args.sign_marker}
    installed = profiles_saved = visual_saved = daylight_saved = False
    try:
        with Client(timeout=25) as client:
            check = SignCheck(client, args.output, 60, native_resolution=True, background_only=True)
            try:
                check.run(INSTALL_PROBE)
                installed = True
                check.run(SAVE)
                profiles_saved = True
                check.run(SAVE_VISUAL)
                visual_saved = True
                check.run('sys._blueprint_visual_saved["grid"]=s.grid\n_result=True')
                daylight_saved = True
                evidence['daylight'] = execute(client, SETUP_DAYLIGHT)
                document = None
                for label, enabled in (('body', False), ('combined', True)):
                    check.run(SWITCH % enabled)
                    check.run('owner.open_workspace()\n_result=True')
                    check.wait('workspace opened', lambda nav: nav['open'] and not nav['transition'], check.navigation)
                    loaded = check.run(LOAD)
                    check.editor_preview(label, loaded['metadata'], loaded['editor_id'], loaded['document_id'])
                    if document is None:
                        document = loaded['document']
                    assert loaded['document'] == document, 'Control changed frame content'
                    case = loaded['case']
                    shown = world_sample(check, 'route_' + label, case['focus'],
                                         case['isolated_camera']['world_offset'], 1.,
                                         case['projection_height'], mesh_origin=True)
                    evidence['world'][label] = {'loaded': loaded, 'shown': shown,
                                               'marker': marker_pixels(shown['screenshot'], args.frame_marker,
                                                                       shown['hidden_screenshot']),
                                               'markers': {color: marker_pixels(shown['screenshot'], color,
                                                                                shown['hidden_screenshot'])
                                                           for color in MARKER_COLORS}}
                    write_json(args.output, evidence)
                evidence['document_nonmutation'] = check.run('_result=json.dumps(s.editor.document.to_data())') == document
                if args.sign_control:
                    view = {'id': 'front', 'editor': (0., 0., 3.), 'world_offset': (0., 0., 2.3)}
                    check.run('owner.open_workspace()\n_result=True')
                    check.wait('sign workspace opened', lambda nav: nav['open'] and not nav['transition'], check.navigation)
                    loaded = load(check, 'standing_front_back', True, view)
                    shown = world_sample(check, 'route_sign', (1, 1, 1), view['world_offset'], 1., 20, mesh_origin=True)
                    evidence['sign_control'] = {'loaded': loaded, 'shown': shown,
                                                'marker': marker_pixels(shown['screenshot'], args.sign_marker, shown['hidden_screenshot']),
                                                'native_transparency_marker': marker_pixels(shown['screenshot'], 'magenta',
                                                                                           shown['hidden_screenshot'])}
                    write_json(args.output, evidence)
                evidence['completed'] = True
                evidence['sources_unchanged'] = all(
                    hashlib.sha256((ROOT / row['source']).read_bytes()).hexdigest() == row['sha256']
                    for row in evidence['sources'])
                evidence['passed'] = all(row['marker']['positive'] for row in evidence['world'].values())
                if args.sign_control:
                    evidence['passed'] = evidence['passed'] and evidence['sign_control']['marker']['positive']
            finally:
                actions = []
                if visual_saved:
                    actions.extend((('projection', lambda: check.run('b.stop_projection()\n_result=True')),
                                    ('camera', lambda: check.run(camera_restore_code(False))),
                                    ('visual', lambda: check.run('saved=sys._blueprint_visual_saved\n'
                                      's.origin=saved["origin"]\ns.opacity=saved["opacity"]\n'
                                      's.projection_missing=saved["missing"]\ns.projection_outline=saved["outline"]\n'
                                      's.grid=saved["grid"]\n'
                                      'del sys._blueprint_visual_saved\n_result=True'))))
                if daylight_saved:
                    actions.append(('daylight', lambda: execute(client, RESTORE_DAYLIGHT)))
                if profiles_saved:
                    actions.append(('profiles', lambda: check.run(RESTORE_PROFILES)))
                if installed:
                    def restore_workspace():
                        was_open = check.run('_result=sys._blueprint_qa_saved["workspace"]')
                        check.run(RESTORE)
                        if was_open:
                            check.run('owner.open_workspace()\n_result=True')
                            check.wait('workspace restored', lambda nav: nav['open'] and not nav['transition'], check.navigation)
                        elif check.navigation()['open']:
                            check.run('navigator.pop()\n_result=True')
                            check.wait('workspace closed', lambda nav: not nav['open'] and not nav['transition'], check.navigation)
                    actions.append(('workspace', restore_workspace))
                errors = []
                for label, action in actions:
                    try:
                        action()
                    except Exception as error:
                        errors.append(label + ': ' + str(error))
                evidence['cleanup_errors'] = errors
                evidence['restored'] = installed and profiles_saved and visual_saved and not errors
                evidence['passed'] = (evidence['passed'] and evidence['document_nonmutation'] and
                                      evidence['sources_unchanged'] and evidence['restored'])
    except Exception as error:
        evidence['error'] = '%s: %s' % (type(error).__name__, error)
    finally:
        write_json(args.output, evidence)
    print(json.dumps({key: evidence[key] for key in ('completed', 'passed', 'restored')}))
    return 0 if evidence['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
