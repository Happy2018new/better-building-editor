"""Focused editor and world-projection screenshots in one owned game.

Run through run_live_check.py. Only local client actors and cameras are changed;
the real world, player position and persistent building library are untouched.
"""
import argparse
import json
import time
from pathlib import Path

from PIL import Image, ImageChops
from verify_debug_blueprints import (BlueprintCheck, Client, INSTALL_PROBE, RESTORE,
                                     ROOT, write_json)

CASES = {
    'water': ('test.layers.water', (3, 1, 6)),
    'snow': ('test.layers.snow', (3, 1, 9)),
    'chest': ('test.connections.context', (26, 1, 5)),
    'shulker': ('test.entities.classic', (33, 1, 21)),
    'stairs': ('test.connections.context', (3, 1, 23)),
}

SAVE_VISUAL = '''cam=b.factory.CreateCamera(b.level)
sys._blueprint_visual_saved={'origin':s.origin,'opacity':s.opacity,
 'missing':s.projection_missing,'outline':s.projection_outline,
 'camera_pos':cam.GetPosition(),'camera_rot':cam.GetCameraRotation(),
 'pitch_lock':cam.IsModCameraLockPitch(),'yaw_lock':cam.IsModCameraLockYaw(),
 'player':b.player_position.GetFootPos()}
_result=True
'''

PROJECTION_STATUS = '''work=b.projection_work
model=b.projection_mesh[1] if b.projection_mesh else None
parts=b.context_models.get(model,())
scales=[b.factory.CreateActorRender(b.entity).GetActorBlockGeometryScale(name) for name,origin,context in parts] if b.entity else []
_result=json.dumps({'active':s.projection_active,'actor':b.entity,
 'actors':len(b.projection_entities)+int(bool(b.entity)),
 'preparing':bool(b.preparing_entity),'ready':work is None or work.ready,
 'error':work.error if work is not None else None,'message':s.editor.message,
 'mesh':b.projection_mesh,'origin':s.origin,
 'scale':scales[0] if scales and all(scale is not None for scale in scales) else None,
 'part_scales':scales,'parts':parts,
 'camera':b.factory.CreateCamera(b.level).GetPosition(),
 'rotation':b.factory.CreateCamera(b.level).GetCameraRotation(),
 'player':b.player_position.GetFootPos()})
'''

PROJECTION_SOURCE = '''from modern_projection.projection.bridge import coordinate
work=b.projection_work
doc=s.editor.document
model=b.projection_mesh[1] if b.projection_mesh else None
parts=b.context_models.get(model,())
_result=json.dumps({'editor_id':id(s.editor),'document_id':id(doc),'fixture':sys._blueprint_qa_identity,
 'nonce':sys._blueprint_qa_nonce,'serial':b.projection_serial,
 'work_current':work is not None and work.serial==b.projection_serial and work.ready and
  work.model==model and work.document.size==doc.size and work.document.blocks==doc.blocks,
 'path':'incremental','cache_model':model,'model':model,
 'cache_current':model is not None and work is not None and model==work.shader.names[work.shader.bank]
  and bool(parts) and all(name in work.shader.parts[work.shader.bank] for name,origin,context in parts),
 'origin_current':b.projection_mesh is not None and
  tuple(b.projection_mesh[2])==tuple(coordinate(s.origin)) and work is not None and
  tuple(work.origin)==tuple(coordinate(s.origin)),
 'missing':s.projection_missing,'parts':parts})
'''


def projection_source_matches(actual, expected):
    fields = ('editor_id', 'document_id', 'fixture', 'nonce', 'serial', 'model', 'path')
    return (all(actual.get(field) == expected.get(field) for field in fields) and
            actual.get('work_current') and actual.get('cache_current') and actual.get('origin_current'))


def camera_restore_code(detached):
    code = '''saved=sys._blueprint_visual_saved
cam=b.factory.CreateCamera(b.level)
cam.ResetCameraPos()
cam.UnDepartCamera()
'''
    if detached:
        code += '''cam.DepartCamera()
assert cam.SetCameraPos(saved['camera_pos'])
'''
    return code + '''assert cam.SetCameraRotation(saved['camera_rot'])
cam.LockModCameraPitch(saved['pitch_lock'])
cam.LockModCameraYaw(saved['yaw_lock'])
_result=True
'''


def projection_pixels(shown, hidden, output):
    with Image.open(shown).convert('RGB') as first, Image.open(hidden).convert('RGB') as second:
        if first.size != second.size:
            raise AssertionError('Window size changed between visibility captures')
        delta = ImageChops.difference(first, second)
        channels = delta.split()
        maximum = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2])
        width, height = first.size
        crop = (width // 5, height // 5, width * 4 // 5, height * 4 // 5)
        histogram = maximum.crop(crop).histogram()
        pixels = sum(histogram[13:])
        delta.save(output)
        return {'changed_pixels': pixels, 'threshold': 12, 'crop': crop,
                'image': str(output.resolve())}


def editor_closeup(check, label, focus, zoom):
    check.run('s.focused=%r\ns.locate_selected()\n_result=True' % (tuple(focus),))
    check.wait('focus consumed', lambda state: state['request'] is None and state['pivot'] is not None,
               lambda: check.run('_result=json.dumps({"request":s.camera_focus_request,'
                                 '"pivot":s.camera_pivot})'))
    check.run('s.camera_view(35.,25.,%r)\n_result=True' % zoom)
    pose = check.wait('closeup zoom', lambda state: abs(state['pose'][2] - zoom) < .01,
                      lambda: check.run('_result=json.dumps({"pose":s.camera_pose,'
                                        '"pivot":s.camera_pivot,"focus":s.focused})'))
    time.sleep(.3)
    tree = check.command('dump_tree')['tree']
    pose['screenshot'] = check.capture(label + '_editor_closeup', tree)
    pose['cell'] = check.run('from modern_projection.projection.cell import foreground,background,actor_data\n'
                             'value=s.editor.document.get(%r)\n'
                             '_result=json.dumps({"front":foreground(value),"back":background(value),'
                             '"actor":actor_data(value)})' % (tuple(focus),))
    return pose


def world_closeup(check, label, focus, offset, opacity, projection_height=8):
    before = check.run('_result=len(sys._blueprint_qa_records)')
    check.run('''focus=%r
foot=b.player_origin()
s.origin=(foot[0]+6-focus[0],foot[1]+%r-focus[1],foot[2]+6-focus[2])
s.opacity=%r
s.projection_missing=False
s.projection_outline=False
b.project()
_result=True''' % (tuple(focus), projection_height, opacity))

    def ready(state):
        if state['error']:
            raise AssertionError(state)
        return (state['active'] and state['ready'] and not state['preparing'] and
                state['actors'] == 1 and state['mesh'] and state['scale'] is not None)

    state = check.wait('world projection', ready, lambda: check.run(PROJECTION_STATUS))
    if check.navigation()['open']:
        check.run('navigator.pop()\n_result=True')
        check.wait('close workspace for world',
                   lambda nav: not nav['open'] and not nav['transition'], check.navigation)
    pose = check.run('''focus=%r
offset=%r
target=tuple(s.origin[i]+focus[i]+.5 for i in range(3))
position=tuple(target[i]+offset[i] for i in range(3))
rotation=api.GetRotFromDir(tuple(target[i]-position[i] for i in range(3)))
cam=b.factory.CreateCamera(b.level)
cam.DepartCamera()
cam.LockModCameraPitch(True)
cam.LockModCameraYaw(True)
assert cam.SetCameraPos(position)
assert cam.SetCameraRotation((rotation[0],rotation[1]+180.,0.))
_result=json.dumps({'target':target,'position':position,'rotation':rotation})''' %
                     (tuple(focus), tuple(offset)))
    time.sleep(.7)
    shown = check.capture(label + '_world_closeup')
    try:
        check.run('assert b.factory.CreateActorRender(b.entity).SetNotRenderAtAll(True)\n_result=True')
        time.sleep(.3)
        hidden = check.capture(label + '_world_hidden')
    finally:
        check.run('assert b.factory.CreateActorRender(b.entity).SetNotRenderAtAll(False)\n_result=True')
    delta_path = check.output.parent / (check.output.stem + '_' + label + '_projection_delta.png')
    delta = projection_pixels(shown['path'], hidden['path'], delta_path)
    assert delta['changed_pixels'] > 150, delta
    final = check.run(PROJECTION_STATUS)
    saved_player = check.run('_result=json.dumps(sys._blueprint_visual_saved["player"])')
    assert final['player'] == saved_player, (saved_player, final['player'])
    calls = check.run('_result=json.dumps(sys._blueprint_qa_records[%d:])' % before)
    source = check.run(PROJECTION_SOURCE)
    assert not source['missing'] and projection_source_matches(source, source), source
    assert all(row.get('result') and not row.get('error') and
               row.get('editor_id') == source['editor_id'] and
               row.get('document_id') == source['document_id'] for row in calls), calls
    state.update(pose=pose, final=final, screenshot=shown, hidden_screenshot=hidden,
                 pixel_difference=delta, native_calls=calls, source=source,
                 native_evidence='current_source_submission' if calls else 'current_source_cached_geometry')
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--case', action='append', choices=tuple(CASES), help='Repeat to select closeups')
    parser.add_argument('--fixture', help='Custom stable fixture identity; requires --focus X Y Z')
    parser.add_argument('--focus', type=int, nargs=3, metavar=('X', 'Y', 'Z'))
    parser.add_argument('--zoom', type=float, default=4, help='Editor closeup zoom')
    parser.add_argument('--offset', type=float, nargs=3, default=(-3.5, 3., -5.), metavar=('X', 'Y', 'Z'),
                        help='World camera offset from the selected cell center')
    parser.add_argument('--opacity', type=float, default=.85)
    parser.add_argument('--timeout', type=float, default=90)
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--native-resolution', action='store_true',
                        help='Use an owner-bound background native-window capture')
    parser.add_argument('--capture-helper', type=Path,
                        default=ROOT/'tools/capture_native_window.py')
    parser.add_argument('--restore-detached', action='store_true',
                        help='Restore an originally detached camera instead of player-follow mode')
    args = parser.parse_args()
    if bool(args.fixture) != bool(args.focus):
        parser.error('--fixture and --focus must be provided together')
    if args.zoom < .25 or args.timeout <= 0 or not 0 < args.opacity <= 1:
        parser.error('Invalid zoom, timeout or opacity')
    cases = [('custom', args.fixture, tuple(args.focus))] if args.fixture else [
        (label,) + CASES[label] for label in (args.case or ('water', 'snow', 'chest', 'shulker'))]
    evidence = {'schema': 1, 'cases': [], 'completed': False,
                'camera_restore_mode': 'detached' if args.restore_detached else 'player_follow',
                'visual_acceptance': 'Actor differences prove visibility; inspect closeups for individual block shapes.'}
    installed = visual_saved = False
    try:
        with Client(timeout=30) as client:
            if args.native_resolution:
                from verify_sign_visuals import SignCheck
                check = SignCheck(client, args.output, args.timeout, native_resolution=True,
                                  background_only=True, native_capture_helper=args.capture_helper)
            else:
                check = BlueprintCheck(client, args.output, args.timeout)
            check.run(INSTALL_PROBE)
            installed = True
            try:
                check.run(SAVE_VISUAL)
                visual_saved = True
                if args.refresh:
                    check.refresh()
                check.page()
                for label, identity, focus in cases:
                    check.run('owner.open_workspace()\n_result=True')
                    check.wait('workspace opens', lambda nav: nav['open'] and not nav['transition'],
                               check.navigation)
                    baseline = check.fixture(identity)
                    if label == 'shulker':
                        focus = tuple(check.run(
                            'from modern_projection.projection.cell import foreground\n'
                            '_result=json.dumps(next(pos for pos,value in s.editor.document.blocks.items() '
                            'if foreground(value)[0]=="minecraft:purple_shulker_box"))'))
                    editor = editor_closeup(check, label, focus, args.zoom)
                    world = world_closeup(check, label, focus, args.offset, args.opacity)
                    evidence['cases'].append({'case': label, 'fixture': identity, 'focus': focus,
                                              'baseline': baseline, 'editor': editor, 'world': world})
                    write_json(args.output, evidence)
                    print(json.dumps({'case': label, 'editor': editor['screenshot']['path'],
                                      'world': world['screenshot']['path'],
                                      'projection_pixels': world['pixel_difference']['changed_pixels']}), flush=True)
                    check.run('b.stop_projection()\n_result=True')
                    check.run(camera_restore_code(args.restore_detached))
                evidence['completed'] = True
            finally:
                if visual_saved:
                    check.run('b.stop_projection()\n_result=True')
                    check.run(camera_restore_code(args.restore_detached))
                    check.run('saved=sys._blueprint_visual_saved\n'
                              's.origin=saved["origin"]\ns.opacity=saved["opacity"]\n'
                              's.projection_missing=saved["missing"]\n'
                              's.projection_outline=saved["outline"]\n'
                              'del sys._blueprint_visual_saved\n_result=True')
                if installed:
                    was_open = check.run('_result=sys._blueprint_qa_saved["workspace"]')
                    check.run(RESTORE)
                    if was_open:
                        check.run('owner.open_workspace()\n_result=True')
                        check.wait('restore workspace', lambda nav: nav['open'] and not nav['transition'],
                                   check.navigation)
                    elif check.navigation()['open']:
                        check.run('navigator.pop()\n_result=True')
                        check.wait('restore closed workspace',
                                   lambda nav: not nav['open'] and not nav['transition'], check.navigation)
                    evidence['restored'] = True
    except Exception as error:
        evidence['error'] = '%s: %s' % (type(error).__name__, error)
        raise
    finally:
        write_json(args.output, evidence)
    print(json.dumps({'evidence': str(args.output.resolve()), 'cases': len(evidence['cases']),
                      'completed': evidence['completed'], 'restored': evidence.get('restored')}))


if __name__ == '__main__':
    main()
