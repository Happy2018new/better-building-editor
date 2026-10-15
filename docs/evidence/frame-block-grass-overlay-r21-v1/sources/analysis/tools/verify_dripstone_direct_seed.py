"""Diagnose native world mesh versus live and deserialized palette meshes.

The same supported cells, anchor transform and camera are used for every
path. This preserves failures without fitting image translations or changing
production geometry. Run only through the owned run_live_check.py runner.
"""
import argparse
import hashlib
import importlib.util
import itertools
import json
import os
from pathlib import Path
import time
import uuid

from PIL import Image, ImageChops, ImageDraw

import verify_neighbor_world_visuals as world
from context_test_environment import run, SETUP, RESTORE as RESTORE_ENVIRONMENT
from verify_debug_blueprints import Client, INSTALL_PROBE, RESTORE, write_json
from verify_debug_visuals import SAVE_VISUAL, camera_restore_code
from verify_dripstone_native_boxes import SERVER_BOXES, CLIENT_BOXES, verify_scene_boxes
from verify_neighbor_native_png import restore_owned_window
from release_owned_game_focus import main as release_focus

native = world.native
ROOT = Path(__file__).resolve().parents[1]
PATHS = ('direct_world', 'direct_palette', 'captured_palette', 'roundtrip')
ROOT_CELL = (6, -37, 6)
STATIC_ROOT = (6, 86, 6)


STATIC_CAPABILITY = '''from modern_projection.projection.model import Document
from modern_projection.projection.debug_blueprints import material
from modern_projection.projection.geometry_palette import prepare_palette
from modern_projection.projection.bridge import _native_palette
from modern_projection.projection.cell import freeze
import uuid
cells=%r
supports=%r
positions=[pos for pos,value in cells+supports]
low=tuple(min(pos[i] for pos in positions) for i in range(3))
high=tuple(max(pos[i] for pos in positions) for i in range(3))
doc=Document(tuple(high[i]-low[i]+1 for i in range(3)))
for pos,value in cells+supports:
 doc.blocks[tuple(pos[i]-low[i] for i in range(3))]=tuple(value)
sources=[('public_fixture',doc.palette_data())]
for control in ('stone','glass','pale_moss_carpet','dandelion','fern'):
 document=Document((1,1,1))
 document.blocks[(0,0,0)]=material(control)
 sources.append((control,document.palette_data()))
block=b.factory.CreateBlock(b.level)
geometry=b.factory.CreateBlockGeometry(b.level)
rows=[]
for kind,raw in sources:
 row={'kind':kind,'raw':freeze(raw),'prepared':freeze(prepare_palette(raw)),'variants':[]}
 for variant,data in (('raw',raw),('prepared',prepare_palette(raw))):
  palette=block.GetBlankBlockPalette()
  assert palette is not None
  accepted=palette.DeserializeBlockPalette(_native_palette(data))
  item={'variant':variant,'deserialized':accepted,'results':[]}
  if accepted:
   item['roundtrip']=freeze(palette.SerializeBlockPalette())
   for mode in (0,1):
    name='static_capability_'+uuid.uuid4().hex
    returned=geometry.CombineBlockPaletteToGeometry(palette,name,mode)
    item['results'].append({'unsupported_mode':mode,'requested_name':name,'returned':returned})
  row['variants'].append(item)
 rows.append(row)
direct=[]
for mode in (0,1):
 name='static_list_'+uuid.uuid4().hex
 palette=geometry.CombineBlockFromPosListToGeometry(positions,name,mode,False)
 direct.append({'unsupported_mode':mode,'requested_name':name,'returned_palette':palette is not None,
                'palette':freeze(palette.SerializeBlockPalette()) if palette is not None else None})
_result=json.dumps({'rows':rows,'direct_world_list':direct,'runtime':api.GetMinecraftVersion(),
 'limits':'Native API return values only; four-path pixel checks establish visibility.'})
'''


def static_fixture_plan(identity):
    from projection.debug_blueprints import build
    from projection.debug_connection_blueprints import VISUAL_CASE
    from projection.cell import foreground
    row = next(item for item in VISUAL_CASE['cases'] if item['id'] == identity)
    document = build(VISUAL_CASE['fixture'])
    low = tuple(min(pos[i] for pos in row['cells']) for i in range(3))
    origin = tuple(STATIC_ROOT[i] - low[i] for i in range(3))

    def translated(pos):
        return tuple(origin[i] + pos[i] for i in range(3))

    cells = [(translated(pos), foreground(document.get(pos))) for pos in row['cells']]
    root = max(pos for pos, value in cells)
    supports = [((root[0], root[1] + 1, root[2]), ('minecraft:stone', 0))]
    return cells, supports, translated(row['keep']), translated(row['occupied'])


def verify_static_values(server, client, expected):
    for side, result in (('server', server), ('client', client)):
        observed = {}
        for row in result['rows']:
            pos = tuple(row['pos'])
            assert pos not in observed, ('duplicate native cell', side, pos)
            value = row['value']
            observed[pos] = ((value['name'], value['aux']) if side == 'server' else tuple(value))
        assert observed == expected, (side, expected, observed)
    return {'original_names_and_aux_equal': True,
            'limits': 'Plant collision boxes are raw diagnostic fields.'}


GENERATE = '''positions=%r
prefix=%r
low=tuple(min(pos[i] for pos in positions) for i in range(3))
high=tuple(max(pos[i] for pos in positions) for i in range(3))
assert not hasattr(sys,'_dripstone_direct_seed')
geometry=b.factory.CreateBlockGeometry(b.level)
names=dict((key,prefix+'_'+key) for key in %r)
direct=geometry.CombineBlockFromPosListToGeometry(positions,names['direct_world'],0,False)
assert direct is not None,'Direct native world Combine failed'
assert geometry.CombineBlockPaletteToGeometry(direct,names['direct_palette'],0)==names['direct_palette']
captured=b.factory.CreateBlock(b.level).GetBlockPaletteBetweenPos(low,high,False)
assert captured is not None
raw=captured.SerializeBlockPalette()
assert geometry.CombineBlockPaletteToGeometry(captured,names['captured_palette'],0)==names['captured_palette']
copy=b.factory.CreateBlock(b.level).GetBlankBlockPalette()
assert copy is not None and copy.DeserializeBlockPalette(raw)
assert geometry.CombineBlockPaletteToGeometry(copy,names['roundtrip'],0)==names['roundtrip']
def tagged(value):
 if isinstance(value,dict):return {'type':'dict','items':[[tagged(k),tagged(v)] for k,v in sorted(value.items(),key=lambda item:repr(item[0]))]}
 if isinstance(value,(tuple,list)):return {'type':'tuple' if isinstance(value,tuple) else 'list','items':[tagged(v) for v in value]}
 if isinstance(value,str):return {'type':'bytes','value':value.decode('utf8')}
 if isinstance(value,unicode):return {'type':'unicode','value':value}
 if value is None or isinstance(value,(bool,int,long,float)):return {'type':type(value).__name__,'value':value}
 raise TypeError('Unsupported native palette type: '+repr(type(value)))
entity=b.system.CreateClientEntityByTypeStr(b'modern_projection:anchor',low,(0.,0.))
assert entity
sys._dripstone_direct_seed={'entity':entity,'names':names,'attached':None,'origin':low}
_result=json.dumps({'names':names,'actor':entity,'origin':low,'low':low,'high':high,
 'volume':raw.get('volume'),'offset':(-.5,0.,-.5),'rotation':(0.,180.,0.),
 'uniform4':(19487.,0.,0.,0.),'runtime':api.GetMinecraftVersion(),
 'direct_palette':tagged(direct.SerializeBlockPalette()),'captured_palette':tagged(raw),
 'roundtrip_palette':tagged(copy.SerializeBlockPalette()),
 'roundtrip_equal':copy.SerializeBlockPalette()==raw})
'''

ATTACH = '''saved=sys._dripstone_direct_seed
render=b.factory.CreateActorRender(saved['entity'])
if saved['attached'] is not None:
 assert render.DeleteActorBlockGeometry(saved['attached'])
 saved['attached']=None
key=%r
name=saved['names'][key]
assert render.AddActorBlockGeometry(name,(-.5,0.,-.5),(0.,180.,0.))
saved['attached']=name
assert render.EnableActorBlockGeometryTransparent(name,True)
assert render.SetActorBlockGeometryTransparency(name,1.)
assert render.SetEntityExtraUniforms(4,(19487.,0.,0.,0.))
assert render.SetNotRenderAtAll(False)
assert tuple(render.GetActorBlockGeometryScale(name) or ())==(1.,1.,1.)
_result=json.dumps({'actor':saved['entity'],'model':name,
 'position':b.factory.CreatePos(saved['entity']).GetPos(),
 'scale':render.GetActorBlockGeometryScale(name),'offset':(-.5,0.,-.5),'rotation':(0.,180.,0.)})
'''

VISIBILITY = '''saved=sys._dripstone_direct_seed
assert saved['attached'] is not None
assert b.factory.CreateActorRender(saved['entity']).SetNotRenderAtAll(%r)
_result=True
'''

CLEANUP = '''if hasattr(sys,'_dripstone_direct_seed'):
 b.system.DestroyClientEntity(sys._dripstone_direct_seed['entity'])
 del sys._dripstone_direct_seed
_result=True
'''

CAMERA = '''root=%r
target=(root[0]+.5,root[1]+1.,root[2]+.5)
position=(target[0],target[1],target[2]-9.)
direction=api.GetRotFromDir(tuple(target[i]-position[i] for i in range(3)))
rotation=(direction[0],direction[1]+180.,0.)
cam=b.factory.CreateCamera(b.level)
cam.DepartCamera();cam.LockModCameraPitch(True);cam.LockModCameraYaw(True)
assert cam.SetCameraPos(position) and cam.SetCameraRotation(rotation)
_result=json.dumps({'position':position,'rotation':rotation,'target':target})
'''

ROIS = '''positions=%r
target=%r
cam=b.factory.CreateCamera(b.level)
points=[]
for pos in positions:
 corners=[tuple(pos[i]+offset[i] for i in range(3))
  for offset in ((x,y,z) for x in (0.,1.) for y in (0.,1.) for z in (0.,1.))]
 points.append({'pos':pos,'world_points':corners,
  'native_points':[cam.WorldToScreenPoint(*point) for point in corners] if hasattr(cam,'WorldToScreenPoint') else []})
_result=json.dumps({'cells':points,'position':cam.GetPosition(),'rotation':cam.GetCameraRotation(),
 'target':target,'fov':cam.GetFov(),'screen':b.factory.CreateGame(b.level).GetScreenSize(),
 'runtime_minecraft_version':api.GetMinecraftVersion(),
 'projection_method':'native' if hasattr(cam,'WorldToScreenPoint') else 'analytic_vertical_fov'})
'''


def fingerprint(path):
    payload = path.read_bytes()
    return {'path': str(path.resolve()), 'sha256': hashlib.sha256(payload).hexdigest(),
            'bytes': len(payload)}


def validate_calibration(calibration, session):
    assert session is not None, 'A validated managed instance is required'
    assert calibration.get('completed') is True and calibration.get('passed') is True, \
        'The camera calibration must be completed and passed'
    assert calibration.get('session_file'), 'Camera calibration has no session provenance'
    assert Path(calibration['session_file']).resolve() == Path(session['session_file']).resolve(), \
        'Camera calibration belongs to a different instance/session'
    assert Path(session['project']).resolve() == ROOT, 'Managed instance belongs to a different project'
    checked = {'completed': True, 'passed': True, 'session_file': session['session_file']}
    for key, target in (('session_id', 'id'), ('instance_id', 'id'), ('owner', 'owner'),
                        ('game_pid', 'game_pid'), ('game_identity', 'game_identity'),
                        ('mcdk_pid', 'mcdk_pid'), ('mcdk_identity', 'mcdk_identity')):
        if key in calibration:
            assert str(calibration[key]) == str(session[target]), 'Camera calibration mismatch: ' + key
            checked[key] = calibration[key]
    if 'restored' in calibration:
        assert calibration['restored'] is True, 'Camera calibration did not restore its instance'
        checked['restored'] = True
    return checked


def capture(check, label, expected):
    before = check.run(native.CAMERA_STATE)
    assert native.camera_matches(before, expected), before
    result = check.capture(label)
    after = check.run(native.CAMERA_STATE)
    assert native.camera_matches(after, expected), after
    assert before['screen'] == after['screen'], (before, after)
    result.update(camera_before=before, camera_after=after)
    return result


def compare(first, second, mask, threshold, minimum):
    empty = Image.new('L', mask.size)
    result = native.compare_complete(first, second, (mask, empty), threshold, minimum // 2)
    result.update(threshold=threshold, minimum_pixels=minimum, translation=(0, 0))
    return result


def execute(check, args, report):
    if args.static_case:
        cells, supports, lower, upper = static_fixture_plan(args.static_case)
        root = min(pos for pos, value in cells)
        region = 'static'
        report['public_fixture'] = {'identity': 'test.connections.static', 'case': args.static_case,
                                    'fixed_root': STATIC_ROOT, 'keep': lower, 'occupied': upper}
    else:
        root = lower = ROOT_CELL
        upper = (lower[0], lower[1] + 1, lower[2])
        cells = [(lower, ('minecraft:pointed_dripstone', 4)),
                 (upper, ('minecraft:pointed_dripstone', 12))]
        supports = [((lower[0], lower[1] - 1, lower[2]), ('minecraft:stone', 0)),
                    ((upper[0], upper[1] + 1, upper[2]), ('minecraft:stone', 0))]
        region = 'dripstone'
    all_cells = supports + cells
    positions = [pos for pos, value in all_cells]
    report.update(cells=cells, supports=supports)
    report['world_setup'] = run(check.client, world.RESERVE % (cells, supports))
    report['near_player'] = run(check.client, world.NEAR_PLAYER % (cells,))
    world.player_ready(check, report['near_player']['after'])
    report['replication'] = world.replication(check, all_cells, False)
    report['native_aabb'] = {'server': run(check.client, SERVER_BOXES % (positions,)),
                             'client': check.run(CLIENT_BOXES % (positions,))}
    expected = dict(all_cells)
    if args.static_case:
        report['native_aabb']['verification'] = verify_static_values(
            report['native_aabb']['server'], report['native_aabb']['client'], expected)
        report['native_capability'] = check.run(STATIC_CAPABILITY % (cells, supports))
    else:
        report['native_aabb']['verification'] = verify_scene_boxes(
            report['native_aabb']['server'], report['native_aabb']['client'], expected)
    report['generation'] = check.run(GENERATE % (positions, 'seed_diag_' + uuid.uuid4().hex, PATHS))
    expected_volume = ([1, 1, 6] if args.static_case else [1, 1, 4])
    assert report['generation']['volume'] == expected_volume, report['generation']['volume']
    time.sleep(.3)
    pose = check.run(CAMERA % (root,))
    time.sleep(.35)
    shown = capture(check, 'world', pose)
    run(check.client, world.CLEAR_SOURCE % (all_cells,))
    report['cleared'] = world.replication(check, all_cells, True)
    time.sleep(.35)
    hidden = capture(check, 'world_empty', pose)
    baseline = native.signal(shown['path'], hidden['path'])
    projection = check.run(ROIS % ([lower, upper], tuple(pose['target'])))
    masks = native.roi_masks(projection, baseline.size, lower, upper, args.calibration)
    dripstone_mask = ImageChops.lighter(masks[0], masks[1])
    support_mask, support_hulls = world.support_roi(projection, baseline.size, supports)
    report['camera'] = pose
    report['world'] = {'shown': shown, 'hidden': hidden, region + '_roi': masks[2],
                       'support_hulls': support_hulls}
    signals = {}
    report['paths'] = {}
    for key in PATHS:
        item = {'attachment': check.run(ATTACH % key)}
        time.sleep(.35)
        item['shown'] = capture(check, key + '_shown', pose)
        check.run(VISIBILITY % True)
        time.sleep(.35)
        item['hidden'] = capture(check, key + '_hidden', pose)
        actual = native.signal(item['shown']['path'], item['hidden']['path'])
        signals[key] = actual
        item['world_' + region] = compare(baseline, actual, dripstone_mask, args.threshold, args.min_pixels * 2)
        item['world_supports'] = compare(baseline, actual, support_mask, args.threshold, args.min_pixels * 2)
        path = args.output.with_name(args.output.stem + '_' + key + '_signal.png')
        actual.save(path)
        item['signal'] = fingerprint(path)
        report['paths'][key] = item
        write_json(args.output, report)
    report['pairwise'] = {}
    for first, second in itertools.combinations(PATHS, 2):
        report['pairwise'][first + '_vs_' + second] = {
            region: compare(signals[first], signals[second], dripstone_mask, args.threshold, args.min_pixels * 2),
            'supports': compare(signals[first], signals[second], support_mask, args.threshold, args.min_pixels * 2)}
    report['completed'] = True
    report['all_paths_match_world'] = all(
        item['world_' + region]['passed'] and item['world_supports']['passed']
        for item in report['paths'].values())
    report['pairwise_equal_under_contract'] = all(
        item[region]['passed'] and item['supports']['passed'] for item in report['pairwise'].values())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--capture-helper', type=Path, required=True)
    parser.add_argument('--camera-calibration', type=Path, required=True)
    parser.add_argument('--static-case', choices=('hanging_moss', 'hanging_moss_cross_chunk'),
                        help='Use the original public static fixture states and top support')
    parser.add_argument('--threshold', type=int, default=16)
    parser.add_argument('--min-pixels', type=int, default=80)
    parser.add_argument('--background-only', action='store_true', default=True,
                        help='Preserve desktop focus and refuse blank background capture fallback')
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.calibration = json.loads(args.camera_calibration.read_text(encoding='utf8'))
    helper = args.capture_helper.resolve(strict=True)
    spec = importlib.util.spec_from_file_location('direct_seed_capture', helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report = {'schema': 1, 'completed': False, 'restored': False,
              'background_only': args.background_only,
              'session_file': os.environ.get('MCDEV_SESSION_FILE'), 'owner': os.environ.get('MCDEV_OWNER'),
              'method': 'Native world/list Combine, returned palette, captured palette and Deserialize roundtrip',
              'limits': 'Diagnostic only; fixed origin/offset/rotation; no pixel fitting or production correction',
              'helper': fingerprint(helper), 'calibration': fingerprint(args.camera_calibration),
              'probe_source': fingerprint(Path(__file__)),
              'native_aabb_reference': (None if args.static_case else
                                        fingerprint(ROOT / 'tools/data/native_dripstone_boxes_r5.json')),
              'resources': [fingerprint(ROOT / path) for path in (
                  'resource_pack/shaders/glsl/modern_projection_biome_blocks.vertex',
                  'resource_pack/shaders/glsl/modern_projection_biome_blocks.fragment',
                  'resource_pack/materials/terrain.material',
                  'behavior_pack/entities/modern_projection_anchor.json',
                  'resource_pack/entity/modern_projection_anchor.entity.json')
                  if (ROOT / path).is_file()]}
    try:
        from _session import load_session
        session = load_session(live=True)
        report['calibration_validation'] = validate_calibration(args.calibration, session)
        with Client(timeout=30) as client:
            report['activation'] = restore_owned_window(session, args.background_only)
            arguments = {'native_resolution': True}
            if args.background_only:
                arguments['background_only'] = True
            check = module.SignCheck(client, args.output, 90, **arguments)
            environment = installed = visual = options = False
            try:
                report['environment_before'] = run(client, SETUP)
                environment = True
                check.run(INSTALL_PROBE)
                installed = True
                check.run(SAVE_VISUAL)
                visual = True
                report['capture_options'] = check.run(world.CAPTURE_OPTIONS)
                options = True
                if check.navigation()['open']:
                    check.run('navigator.pop()\n_result=True')
                    check.wait('close workspace', lambda value: not value['open'] and not value['transition'], check.navigation)
                report['seed'] = run(client, 'import mod.server.extraServerApi as api\n'
                    '_result=api.GetEngineCompFactory().CreateGame(api.GetLevelId()).GetSeed()')
                execute(check, args, report)
            finally:
                errors = []
                cleanup = [('actor', CLEANUP)]
                if visual:
                    cleanup.append(('camera', camera_restore_code(False)))
                    cleanup.append(('visual', 'del sys._blueprint_visual_saved\n_result=True'))
                if installed:
                    cleanup.append(('probe', 'workspace_before=sys._blueprint_qa_saved["workspace"]\n' +
                                    RESTORE + '\nif workspace_before:owner.open_workspace()\n_result=True'))
                if options:
                    cleanup.append(('options', world.RESTORE_OPTIONS))
                for label, code in cleanup:
                    try:
                        check.run(code)
                    except Exception as error:
                        errors.append('%s: %s' % (label, error))
                try:
                    report['world_cleanup'] = world.clear_world(client)
                    if report['world_cleanup']['player_foot'] is not None:
                        world.player_ready(check, report['world_cleanup']['player_foot'])
                except Exception as error:
                    errors.append('world: %s' % error)
                if environment:
                    try:
                        run(client, RESTORE_ENVIRONMENT)
                    except Exception as error:
                        errors.append('environment: %s' % error)
                report['cleanup_errors'] = errors
                report['restored'] = not errors
    except Exception as error:
        report['error'] = '%s: %s' % (type(error).__name__, error)
        raise
    finally:
        try:
            report['focus_release'] = ({'background_only': True, 'focus_unchanged': True}
                                       if args.background_only else release_focus())
        except Exception as error:
            report['focus_release'] = {'error': '%s: %s' % (type(error).__name__, error)}
        write_json(args.output, report)
    print(json.dumps({'completed': report['completed'], 'restored': report['restored'],
                      'all_paths_match_world': report.get('all_paths_match_world'),
                      'pairwise_equal_under_contract': report.get('pairwise_equal_under_contract')}))
    return 0 if report['completed'] and report['restored'] and 'error' not in report['focus_release'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
