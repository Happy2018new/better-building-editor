"""Pixel acceptance for six shulker orientations at one position and camera.

Run through the owned instance's run_live_check.py. Native palettes can be
prepared with p0_shulker_orientations_* or --setup-native. A successful native
Combine call or different facing fields never counts as a visual pass.
"""
import argparse
import base64
import json
import sys
import time
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parents[1]

LOAD = '''from copy import deepcopy
from modern_projection.projection.model import Document
from modern_projection.projection.world_capture import merge_palette
from modern_projection.projection.cell import rebase
from modern_projection.projection.debug_blueprints import build,VISUAL_CASES
source=%r
facing=%d
case=VISUAL_CASES['shulker_orientations']
focus=case['focus']
doc=Document(case['size'],name='Shulker orientation pixel check')
if source=='native':
 data=deepcopy(sys._p0_shulker_face_palettes[facing])
 merge_palette(doc,data,focus,(1,1,1),tuple(-v for v in focus))
else:
 blueprint=build(case['fixture'])
 source_pos=case['cells'][facing]
 doc.blocks[focus]=rebase(blueprint.get(source_pos),tuple(focus[i]-source_pos[i] for i in range(3)))
sys._blueprint_qa_identity='orientation.'+source+'.'+str(facing)
s._loaded(doc)
s.camera_pivot=tuple(v+.5 for v in focus)
s.camera_view(*case['camera']['editor'])
_result=True
'''


def purple_mask(image):
    pixels = image.convert('RGB')
    red, green, blue = pixels.split()
    first = ImageChops.subtract(red, green).point(lambda value: 255 if value > 14 else 0)
    second = ImageChops.subtract(blue, green).point(lambda value: 255 if value > 14 else 0)
    brightness = ImageChops.lighter(red, blue).point(lambda value: 255 if value > 40 else 0)
    return ImageChops.multiply(ImageChops.multiply(first, second), brightness)


def masked_frame(path, crop, output):
    with Image.open(path) as source:
        frame = source.convert('RGB').crop(crop)
    mask = purple_mask(frame)
    count = mask.histogram()[255]
    if count < 150:
        raise AssertionError('Shulker model is missing or too small: %d purple pixels in %s' % (count, path))
    result = Image.new('RGB', frame.size, 'black')
    result.paste(frame, mask=mask)
    result.save(output)
    return result, {'purple_pixels': count, 'crop': crop, 'image': str(output.resolve())}


def pixel_comparison(frames, minimum=150, threshold=24):
    if len(frames) != 6 or len({frame.size for frame in frames}) != 1:
        raise AssertionError('Six identically sized images are required')
    rows = []
    for left in range(6):
        for right in range(left + 1, 6):
            delta = ImageChops.difference(frames[left], frames[right])
            channels = delta.split()
            maximum = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2])
            changed = sum(maximum.histogram()[threshold + 1:])
            rows.append({'left': left, 'right': right, 'changed_pixels': changed})
    return {'passed': any(row['changed_pixels'] >= minimum for row in rows),
            'minimum_changed_pixels': minimum, 'channel_threshold': threshold,
            'pairs': rows,
            'scope': 'Rejects six visually identical poses; does not prove each direction is semantically correct.'}


def contact_sheet(frames, labels, output):
    width, height = frames[0].size
    sheet = Image.new('RGB', (width * 3, (height + 24) * 2), 'white')
    draw = ImageDraw.Draw(sheet)
    for index, frame in enumerate(frames):
        x, y = index % 3 * width, index // 3 * (height + 24)
        sheet.paste(frame, (x, y))
        draw.text((x + 4, y + height + 4), labels[index], fill='black')
    sheet.save(output)


def viewport_crop(check, screenshot):
    from verify_debug_blueprints import walk
    tree = check.command('dump_tree')['tree']
    scene = next(node for node in walk(tree) if node.get('type') == 'Scene')
    box = next((node['layout'] for node in walk(scene) if node.get('layout')), None)
    root = next((node['layout'] for node in walk(tree) if node.get('layout')), None)
    if not box or not root or not root.get('width') or not root.get('height'):
        raise AssertionError('Actual viewport layout is unavailable; refusing to compare whole UI screenshots')
    width, height = screenshot['size']
    sx, sy = width / root['width'], height / root['height']
    return (int((box['x'] - root.get('x', 0)) * sx),
            int((box['y'] - root.get('y', 0)) * sy),
            int((box['x'] - root.get('x', 0) + box['width']) * sx),
            int((box['y'] - root.get('y', 0) + box['height']) * sy))


def server_run(client, code):
    from verify_debug_blueprints import return_value
    response = client.call('execute_code', {'code': code, 'is_client': False, 'direct_return': True})
    if response.get('isError'):
        raise RuntimeError(response)
    value = return_value(response)
    return json.loads(value) if isinstance(value, str) else value


def native_setup(client, check):
    rows = server_run(client, (ROOT / 'tools/p0_shulker_orientations_setup.py').read_text(encoding='utf8'))
    check.run('sys._p0_shulker_face_positions=%r\n_result=True' % rows['rows'])
    code = (ROOT / 'tools/p0_shulker_orientations_read.py').read_text(encoding='utf8')
    time.sleep(.5)
    return check.run(code)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--setup-native', action='store_true')
    parser.add_argument('--synthetic-only', action='store_true', help='Isolate current rendering failure without native reference')
    parser.add_argument('--timeout', type=float, default=45)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        same = [Image.new('RGB', (100, 100), (110, 40, 170)) for unused in range(6)]
        assert not pixel_comparison(same)['passed'], 'Identical orientations falsely passed'
        changed = [frame.copy() for frame in same]
        ImageDraw.Draw(changed[5]).rectangle((10, 10, 30, 30), fill=(180, 60, 210))
        assert pixel_comparison(changed)['passed'], 'A significant visible change was not detected'
        noise = [frame.copy() for frame in same]
        noise[5].putpixel((1, 1), (255, 255, 255))
        assert not pixel_comparison(noise)['passed'], 'Single-pixel noise falsely passed'
        print('Shulker pixel detector: identical/noise rejected, significant change accepted')
        return
    from verify_debug_blueprints import (BlueprintCheck, Client, INSTALL_PROBE, RESTORE,
                                         STATUS, write_json)
    from verify_debug_visuals import SAVE_VISUAL, camera_restore_code, world_closeup
    evidence = {'schema': 1, 'completed': False, 'sources': {},
                'source': 'Built-in test.transforms.directions blueprint cells'}
    installed = visual_saved = native_created = False
    try:
        with Client(timeout=30) as client:
            check = BlueprintCheck(client, args.output, args.timeout)
            try:
                check.run(INSTALL_PROBE)
                installed = True
                check.run(SAVE_VISUAL)
                visual_saved = True
                blueprint_path = ROOT / 'behavior_pack/modern_projection/projection/debug_blueprints.py'
                check.run('import base64\nimport modern_projection.projection.debug_blueprints as refreshed\n'
                          'eval(compile(base64.b64decode(%r),%r,"exec"),refreshed.__dict__)\n'
                          '_result=json.dumps(refreshed.VISUAL_CASES["shulker_orientations"])' %
                          (base64.b64encode(blueprint_path.read_bytes()).decode('ascii'), str(blueprint_path)))
                case = check.run('from modern_projection.projection.debug_blueprints import VISUAL_CASES\n'
                                 '_result=json.dumps(VISUAL_CASES["shulker_orientations"])')
                focus = tuple(case['focus'])
                world_offset = tuple(case['camera']['world_offset'])
                evidence['blueprint_case'] = case
                if args.setup_native:
                    native_created = True
                    evidence['native_reference'] = native_setup(client, check)
                if not args.synthetic_only:
                    evidence['native_input'] = check.run(
                        'assert hasattr(sys,"_p0_shulker_face_palettes") and '
                        'len(sys._p0_shulker_face_palettes)==6, "Run native palette helpers or --setup-native first"\n'
                        '_result=json.dumps([data.get("actor",{}) for data in sys._p0_shulker_face_palettes])')
                sources = ('synthetic',) if args.synthetic_only else ('native', 'synthetic')
                for source in sources:
                    rows, editor_frames, world_frames = [], [], []
                    editor_crop = None
                    for facing in range(6):
                        check.run('owner.open_workspace()\n_result=True')
                        check.wait('open workspace', lambda nav: nav['open'] and not nav['transition'], check.navigation)
                        check.run(LOAD % (source, facing))
                        state = check.wait('orientation preview',
                                           lambda value: not value['preview_pending'] and not value['running'] and
                                           not value['dirty'] and not value['mounting'] and value['model_revision_current'] and
                                           all(not row['pending'] for row in value['parts']),
                                           lambda: check.run(STATUS))
                        if state['preview_error']:
                            raise AssertionError(state)
                        time.sleep(.35)
                        label = '%s_facing%d' % (source, facing)
                        editor = check.capture(label + '_editor')
                        if editor_crop is None:
                            editor_crop = viewport_crop(check, editor)
                        frame, pixels = masked_frame(editor['path'], editor_crop,
                                                     args.output.with_name(args.output.stem + '_' + label + '_editor_mask.png'))
                        editor_frames.append(frame)
                        world = world_closeup(check, label, focus, world_offset, 1.)
                        width, height = world['screenshot']['size']
                        crop = (width // 4, height // 4, width * 3 // 4, height * 3 // 4)
                        frame, world_pixels = masked_frame(world['screenshot']['path'], crop,
                                                           args.output.with_name(args.output.stem + '_' + label + '_world_mask.png'))
                        world_frames.append(frame)
                        rows.append({'facing': facing, 'editor': editor, 'editor_mask': pixels,
                                     'world': world, 'world_mask': world_pixels})
                        evidence['sources'][source] = {'rows': rows}
                        write_json(args.output, evidence)
                        check.run('b.stop_projection()\n_result=True')
                        check.run(camera_restore_code(False))
                    record = evidence['sources'][source]
                    for label, frames in (('editor', editor_frames), ('world', world_frames)):
                        record[label + '_comparison'] = pixel_comparison(frames)
                        sheet = args.output.with_name(args.output.stem + '_' + source + '_' + label + '_six.png')
                        contact_sheet(frames, ['facing %d' % index for index in range(6)], sheet)
                        record[label + '_contact_sheet'] = str(sheet.resolve())
                    write_json(args.output, evidence)
                if len(sources) == 2:
                    comparisons = {}
                    for view in ('editor', 'world'):
                        comparisons[view] = []
                        for facing in range(6):
                            left = evidence['sources']['native']['rows'][facing][view + '_mask']['image']
                            right = evidence['sources']['synthetic']['rows'][facing][view + '_mask']['image']
                            with Image.open(left) as native, Image.open(right) as synthetic:
                                if native.size != synthetic.size:
                                    raise AssertionError('Native and synthetic camera framing differ')
                                delta = ImageChops.difference(native.convert('RGB'), synthetic.convert('RGB'))
                                channels = delta.split()
                                maximum = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2])
                                comparisons[view].append({'facing': facing,
                                                          'changed_pixels': sum(maximum.histogram()[25:])})
                    evidence['native_synthetic_comparison'] = comparisons
                failed = ['%s %s' % (source, view) for source, record in evidence['sources'].items()
                          for view in ('editor', 'world') if not record[view + '_comparison']['passed']]
                assert not failed, 'All six shulker poses render identically: ' + ', '.join(failed)
                evidence['completed'] = True
            finally:
                prior_error = sys.exc_info()[0]
                cleanup_errors = []
                if visual_saved:
                    actions = (
                        ('projection', 'b.stop_projection()\n_result=True'),
                        ('camera', camera_restore_code(False)),
                        ('visual_fields', 'saved=sys._blueprint_visual_saved\ns.origin=saved["origin"]\n'
                         's.opacity=saved["opacity"]\ns.projection_missing=saved["missing"]\n'
                         's.projection_outline=saved["outline"]\ndel sys._blueprint_visual_saved\n_result=True'),
                    )
                    for label, code in actions:
                        try:
                            check.run(code)
                        except Exception as cleanup_error:
                            cleanup_errors.append('%s: %s' % (label, cleanup_error))
                if installed:
                    try:
                        opened = check.run('_result=sys._blueprint_qa_saved["workspace"]')
                        check.run(RESTORE)
                        if opened:
                            check.run('owner.open_workspace()\n_result=True')
                        elif check.navigation()['open']:
                            check.run('navigator.pop()\n_result=True')
                        evidence['restored'] = True
                    except Exception as cleanup_error:
                        cleanup_errors.append('workspace: %s' % cleanup_error)
                if native_created:
                    try:
                        saved = server_run(client, 'import sys\n_result=hasattr(sys,"_p0_shulker_faces")')
                        if saved:
                            server_run(client, (ROOT / 'tools/p0_shulker_orientations_cleanup.py').read_text(encoding='utf8'))
                        evidence['native_cleaned'] = True
                    except Exception as cleanup_error:
                        cleanup_errors.append('native_fixture: %s' % cleanup_error)
                if cleanup_errors:
                    evidence['cleanup_errors'] = cleanup_errors
                    if prior_error is None:
                        raise RuntimeError('Shulker acceptance cleanup failed: ' + '; '.join(cleanup_errors))
    except Exception as error:
        evidence['error'] = '%s: %s' % (type(error).__name__, error)
        raise
    finally:
        write_json(args.output, evidence)
    print(json.dumps({'evidence': str(args.output.resolve()), 'completed': evidence['completed']}))


if __name__ == '__main__':
    main()
