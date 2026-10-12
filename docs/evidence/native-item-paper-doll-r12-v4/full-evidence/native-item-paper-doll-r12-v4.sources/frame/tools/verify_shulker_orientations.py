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

from PIL import Image, ImageChops, ImageDraw, ImageFilter
from shulker_pixels import central_object, native_proxy_comparison
from visual_environment import SETUP_DAYLIGHT, RESTORE_DAYLIGHT

ROOT = Path(__file__).resolve().parents[1]


def reference_offset(configured):
    # The native block actor batch disappeared from the upper detached camera.
    return (configured[0], -abs(configured[1]), configured[2])


def matching_camera(actual, pose, tolerance=.02):
    expected = (pose['rotation'][0], pose['rotation'][1] + 180., 0.)
    return (all(abs(left - right) < tolerance for left, right in zip(actual['position'], pose['position']))
            and all(abs((left - right + 180.) % 360. - 180.) < tolerance
                    for left, right in zip(actual['rotation'], expected)))


def wait_camera_pose(check, pose):
    settled = [0]

    def stable(actual):
        settled[0] = settled[0] + 1 if matching_camera(actual, pose) else 0
        return settled[0] >= 2

    return check.wait('native camera interpolation settles twice', stable,
                      lambda: check.run('cam=b.factory.CreateCamera(b.level)\n'
                                        '_result=json.dumps({"position":cam.GetPosition(),'
                                        '"rotation":cam.GetCameraRotation()})'))

LOAD = '''from copy import deepcopy
from modern_projection.projection.model import Document
from modern_projection.projection.world_capture import merge_palette
from modern_projection.projection.cell import rebase,foreground,background,actor_data,make_cell
from modern_projection.projection.visible_actor import compose_actor,render_actor
from modern_projection.projection.nbt_spatial import rebase as rebase_nbt
from modern_projection.projection.debug_blueprints import build,VISUAL_CASES
source=%r
facing=%d
case=VISUAL_CASES['shulker_orientations']
focus=case['focus']
doc=Document(case['size'],name='Shulker orientation pixel check')
if source=='native':
 data=deepcopy(sys._p0_shulker_face_palettes[facing])
 observation=sys._p0_shulker_face_entities[facing]
 world_origin=tuple(observation['pos'][i]-focus[i] for i in range(3))
 merge_palette(doc,data,focus,(1,1,1),world_origin)
 value=doc.get(focus)
 if observation.get('entity_nbt'):
  actor=compose_actor(render_actor(actor_data(value)),rebase_nbt(observation['entity_nbt'],tuple(-v for v in world_origin)))
  doc.blocks[focus]=make_cell(foreground(value),background(value),actor)
else:
 blueprint=build(case['fixture'])
 source_pos=case['cells'][facing]
 doc.blocks[focus]=rebase(blueprint.get(source_pos),tuple(focus[i]-source_pos[i] for i in range(3)))
sys._blueprint_qa_identity='orientation.'+source+'.'+str(facing)
s._loaded(doc)
s.camera_pivot=tuple(v+.5 for v in focus)
s.camera_view(*case['camera']['editor'])
sys._shulker_qa_document=doc
_result=json.dumps({'identity':sys._blueprint_qa_identity,'size':doc.size,
 'blocks':len(doc.blocks),'focus':focus,'front':foreground(doc.get(focus)),
 'facing':static_proxy(foreground(doc.get(focus)),actor_data(doc.get(focus)))[0]})
'''

IDENTITY = '''from modern_projection.projection.entity_render import static_proxy
from modern_projection.projection.cell import foreground,actor_data
doc=s.editor.document
focus=%r
_result=json.dumps({'identity':sys._blueprint_qa_identity,'size':doc.size,
 'blocks':len(doc.blocks),'front':foreground(doc.get(focus)),
 'expected_document':doc is getattr(sys,'_shulker_qa_document',None),
 'facing':static_proxy(foreground(doc.get(focus)),actor_data(doc.get(focus)))[0]})
'''


def masked_frame(path, crop, output):
    with Image.open(path) as source:
        frame = source.convert('RGB').crop(crop)
    result, unused_mask, record = central_object(frame)
    result.save(output)
    record.update(crop=crop, image=str(output.resolve()))
    return result, record


def opacity_comparison(shown, translucent, hidden, crop, object_mask=None):
    with Image.open(shown) as full, Image.open(translucent) as half, Image.open(hidden) as empty:
        frames = [source.convert('RGB').crop(crop) for source in (full, half, empty)]
    if object_mask is None:
        unused, mask, record = central_object(frames[0])
    else:
        if object_mask.size != frames[0].size:
            raise AssertionError('Opacity mask dimensions differ from the measured crop')
        mask, record = object_mask, {'bbox': object_mask.getbbox()}
    eligible = list(mask.filter(ImageFilter.MinFilter(5)).tobytes())
    full_signal, half_signal = [], []
    for channel in range(3):
        values = [frame.split()[channel].tobytes() for frame in frames]
        for opaque, faded, background, use in zip(*values, eligible):
            if use:
                full_signal.append(opaque - background)
                half_signal.append(faded - background)
    energy = sum(value * value for value in full_signal)
    if len(full_signal) < 450 or energy <= 100:
        raise AssertionError('The opacity probe lacks an opaque object signal')
    gain = sum(left * right for left, right in zip(full_signal, half_signal)) / float(energy)
    residual = (sum((right - .5 * left) ** 2 for left, right in zip(full_signal, half_signal)) / energy) ** .5
    return {'requested_opacity': .5, 'measured_contrast_gain': gain,
            'half_blend_relative_residual': residual, 'samples': len(full_signal),
            'object_bbox': record['bbox'], 'passed': .35 <= gain <= .65 and residual <= .15,
            'limits': {'contrast_gain': [.35, .65], 'half_blend_relative_residual': .15}}


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
    time.sleep(.25)
    rows['supports_removed'] = server_run(client, '''import json,sys
import mod.server.extraServerApi as api
saved=sys._p0_shulker_faces
info=api.GetEngineCompFactory().CreateBlockInfo(api.GetLevelId())
for row in saved['rows']:
 info.SetBlockNew(tuple(row['support']),{'name':'minecraft:air','aux':0},0,saved['dimension'],True,True)
_result=json.dumps([info.GetBlockNew(tuple(row['support']),saved['dimension']) for row in saved['rows']])
''')
    check.run('sys._p0_shulker_face_positions=%r\n_result=True' % rows['rows'])
    code = (ROOT / 'tools/p0_shulker_orientations_read.py').read_text(encoding='utf8')
    time.sleep(.5)
    return check.run(code)


def verify_native_fixtures(client):
    return server_run(client, '''import json
import sys
import mod.server.extraServerApi as api
from modern_projection.projection.nbt_spatial import root_payload,scalar
saved=sys._p0_shulker_faces
info=api.GetEngineCompFactory().CreateBlockInfo(api.GetLevelId())
for row in saved['rows']:
 assert info.GetBlockNew(tuple(row['support']),saved['dimension'])['name']=='minecraft:air',row
 assert info.GetBlockNew(tuple(row['pos']),saved['dimension'])['name']=='minecraft:purple_shulker_box',row
 current=info.GetBlockEntityData(saved['dimension'],tuple(row['pos']))
 assert scalar(root_payload(current),'facing')==row['server_facing'],row
_result=json.dumps({'supports_removed':True,'native_faces_unchanged':True})
''')


def actual_native_closeup(check, facing, offset):
    if check.navigation()['open']:
        check.run('navigator.pop()\n_result=True')
        check.wait('close editor for native reference',
                   lambda nav: not nav['open'] and not nav['transition'], check.navigation)
    pose = check.run('''b.stop_projection()
source=sys._p0_shulker_face_entities[%d]
offset=%r
pos=tuple(source['pos'])
block=b.factory.CreateBlock(b.level)
palette=block.GetBlockPaletteBetweenPos(pos,pos,False)
assert palette is not None and any(value[0]=='minecraft:purple_shulker_box' for value in palette.SerializeBlockPalette().get('common',{})),source
target=tuple(value+.5 for value in source['pos'])
position=tuple(target[i]+offset[i] for i in range(3))
rotation=api.GetRotFromDir(tuple(target[i]-position[i] for i in range(3)))
cam=b.factory.CreateCamera(b.level)
cam.DepartCamera()
cam.LockModCameraPitch(True)
cam.LockModCameraYaw(True)
assert cam.SetCameraPos(position)
assert cam.SetCameraRotation((rotation[0],rotation[1]+180.,0.))
_result=json.dumps({'target':target,'position':position,'rotation':rotation,
 'server_facing':source['server_facing'],'placement':source['support_face'],
 'reference':'real native world block, no projection actor'})''' % (facing, tuple(offset)))
    pose['settled_camera'] = wait_camera_pose(check, pose)
    time.sleep(.3)
    pose['screenshot'] = check.capture('real_native_facing%d_world' % facing)
    return pose


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--setup-native', action='store_true')
    parser.add_argument('--synthetic-only', action='store_true', help='Check built-in editor poses without projection/native world acceptance')
    parser.add_argument('--timeout', type=float, default=45)
    parser.add_argument('--offset-scale', type=float, default=1.,
                        help='Scale the same native/projection camera offset for closer texture diagnosis')
    parser.add_argument('--opacity-probe', action='store_true',
                        help='Also compare half-transparent projection pixels with the opaque and hidden captures')
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
    evidence = {'schema': 3, 'completed': False, 'sources': {},
                'source': 'Built-in test.transforms.directions blueprint cells',
                'camera_policy': 'One low side offset for all native/proxy pairs; no high-camera or opening-face claim'}
    installed = visual_saved = native_created = daylight_saved = False
    try:
        with Client(timeout=30) as client:
            check = BlueprintCheck(client, args.output, args.timeout)
            try:
                check.run(INSTALL_PROBE)
                installed = True
                check.run(SAVE_VISUAL)
                visual_saved = True
                daylight_saved = True
                evidence['daylight'] = server_run(client, SETUP_DAYLIGHT)
                blueprint_path = ROOT / 'behavior_pack/modern_projection/projection/debug_blueprints.py'
                check.run('import base64\nimport modern_projection.projection.debug_blueprints as refreshed\n'
                          'eval(compile(base64.b64decode(%r),%r,"exec"),refreshed.__dict__)\n'
                          '_result=json.dumps(refreshed.VISUAL_CASES["shulker_orientations"])' %
                          (base64.b64encode(blueprint_path.read_bytes()).decode('ascii'), str(blueprint_path)))
                case = check.run('from modern_projection.projection.debug_blueprints import VISUAL_CASES\n'
                                 '_result=json.dumps(VISUAL_CASES["shulker_orientations"])')
                focus = tuple(case['focus'])
                world_offset = tuple(value * args.offset_scale for value in
                                     reference_offset(case['camera']['world_offset']))
                evidence['reference_camera_offset'] = world_offset
                evidence['blueprint_case'] = case
                if args.setup_native:
                    native_created = True
                    evidence['native_reference'] = native_setup(client, check)
                if not args.synthetic_only:
                    evidence['native_input'] = check.run(
                        'assert hasattr(sys,"_p0_shulker_face_palettes") and '
                        'len(sys._p0_shulker_face_palettes)==6, "Run native palette helpers or --setup-native first"\n'
                        '_result=json.dumps([data.get("actor",{}) for data in sys._p0_shulker_face_palettes])')
                    evidence['native_fixture_readback'] = verify_native_fixtures(client)
                    time.sleep(.3)
                sources = ('synthetic',) if args.synthetic_only else ('native', 'synthetic')
                real_native_frames = []
                for source in sources:
                    rows, editor_frames, world_frames = [], [], []
                    evidence['sources'][source] = {'rows': rows}
                    editor_crop = None
                    for facing in range(6):
                        check.run('owner.open_workspace()\n_result=True')
                        check.wait('open workspace', lambda nav: nav['open'] and not nav['transition'], check.navigation)
                        loaded = check.run('from modern_projection.projection.entity_render import static_proxy\n' + LOAD % (source, facing))
                        expected_identity = 'orientation.%s.%d' % (source, facing)
                        assert loaded['identity'] == expected_identity and loaded['size'] == case['size'] and loaded['blocks'] == 1, loaded
                        actual = check.run(IDENTITY % (focus,))
                        assert actual['expected_document'] and actual['facing'].endswith('_%d' % facing), actual
                        state = check.wait('orientation preview',
                                           lambda value: not value['preview_pending'] and not value['running'] and
                                           not value['dirty'] and not value['mounting'] and value['model_revision_current'] and
                                           all(not row['pending'] for row in value['parts']),
                                           lambda: check.run(STATUS))
                        if state['preview_error']:
                            raise AssertionError(state)
                        actual = check.run(IDENTITY % (focus,))
                        assert actual['identity'] == expected_identity and actual['expected_document'] and actual['size'] == case['size'] and actual['blocks'] == 1, actual
                        time.sleep(.35)
                        label = '%s_facing%d' % (source, facing)
                        editor = check.capture(label + '_editor')
                        if editor_crop is None:
                            editor_crop = viewport_crop(check, editor)
                        frame, pixels = masked_frame(editor['path'], editor_crop,
                                                     args.output.with_name(args.output.stem + '_' + label + '_editor_mask.png'))
                        editor_frames.append(frame)
                        rows.append({'facing': facing, 'editor': editor, 'editor_mask': pixels,
                                     'source': source, 'document_identity': actual})
                        if source == 'native':
                            offset = world_offset
                            world = world_closeup(check, label, focus, offset, 1., case['projection_height'])
                            assert matching_camera({'position': world['final']['camera'],
                                                    'rotation': world['final']['rotation']}, world['pose']), world
                            rows[-1]['world'] = world
                            width, height = world['screenshot']['size']
                            crop = (width // 4, height // 4, width * 3 // 4, height * 3 // 4)
                            frame, world_pixels = masked_frame(world['screenshot']['path'], crop,
                                args.output.with_name(args.output.stem + '_' + label + '_world_mask.png'))
                            world_frames.append(frame)
                            if args.opacity_probe:
                                check.run('assert b.factory.CreateActorRender(b.entity).SetActorBlockGeometryTransparency(b.projection_mesh[1],.5)\n_result=True')
                                try:
                                    time.sleep(.3)
                                    faded = check.capture(label + '_world_opacity_half')
                                    opacity = opacity_comparison(world['screenshot']['path'], faded['path'],
                                                                 world['hidden_screenshot']['path'], crop)
                                    rows[-1]['opacity_probe'] = dict(opacity, screenshot=faded)
                                    assert opacity['passed'], opacity
                                finally:
                                    check.run('assert b.factory.CreateActorRender(b.entity).SetActorBlockGeometryTransparency(b.projection_mesh[1],1.)\n_result=True')
                            real = actual_native_closeup(check, facing, offset)
                            rows[-1]['real_native'] = real
                            try:
                                real_frame, real_pixels = masked_frame(real['screenshot']['path'], crop,
                                    args.output.with_name(args.output.stem + '_real_native_facing%d_mask.png' % facing))
                            except AssertionError as visibility_error:
                                rows[-1]['native_visibility'] = {'observed': False, 'reason': str(visibility_error)}
                                evidence['proxy_comparison_indeterminate'] = True
                                raise AssertionError('Native reference is not visible at the measured camera; '
                                                     'proxy appearance is undetermined: %s' % visibility_error) from visibility_error
                            real_native_frames.append(real_frame)
                            rows[-1].update(world=world, world_mask=world_pixels,
                                            real_native=real, real_native_mask=real_pixels,
                                            matching_camera_offset=offset)
                        write_json(args.output, evidence)
                        check.run('b.stop_projection()\n_result=True')
                        check.run(camera_restore_code(False))
                    record = evidence['sources'][source]
                    views = [('editor', editor_frames)]
                    if world_frames:
                        views.append(('world', world_frames))
                    for label, frames in views:
                        record[label + '_comparison'] = pixel_comparison(frames)
                        sheet = args.output.with_name(args.output.stem + '_' + source + '_' + label + '_six.png')
                        contact_sheet(frames, ['facing %d' % index for index in range(6)], sheet)
                        record[label + '_contact_sheet'] = str(sheet.resolve())
                    if world_frames:
                        evidence['real_native_proxy_comparison'] = native_proxy_comparison(real_native_frames, world_frames)
                        real_sheet = args.output.with_name(args.output.stem + '_real_native_world_six.png')
                        contact_sheet(real_native_frames, ['native facing %d' % index for index in range(6)], real_sheet)
                        evidence['real_native_contact_sheet'] = str(real_sheet.resolve())
                    write_json(args.output, evidence)
                if len(sources) == 2:
                    comparisons = {}
                    for view in ('editor',):
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
                          for view in ('editor', 'world') if view + '_comparison' in record and
                          not record[view + '_comparison']['passed']]
                assert not failed, 'All six shulker poses render identically: ' + ', '.join(failed)
                if not args.synthetic_only:
                    assert evidence['real_native_proxy_comparison']['passed'], 'Native world shape/texture agreement failed; inspect saved matrices and contact sheets'
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
                if daylight_saved:
                    try:
                        evidence['daylight_restored'] = server_run(client, RESTORE_DAYLIGHT)
                    except Exception as cleanup_error:
                        cleanup_errors.append('daylight: %s' % cleanup_error)
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
