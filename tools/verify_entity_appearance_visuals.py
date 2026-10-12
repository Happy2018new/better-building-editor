"""Independent native/editor/projection appearance checks linked to built-in cases."""
import argparse
import base64
import json
import hashlib
import math
import os
from pathlib import Path
import sys
import time

from PIL import Image, ImageChops, ImageFilter
from verify_debug_blueprints import Client, INSTALL_PROBE, RESTORE, write_json
from verify_debug_visuals import (SAVE_VISUAL, PROJECTION_SOURCE, PROJECTION_STATUS,
                                 camera_restore_code, projection_source_matches, world_closeup)
from verify_native_entity_appearances import execute, replicated_palettes
from verify_shulker_orientations import matching_camera, opacity_comparison, viewport_crop, wait_camera_pose
from verify_sign_visuals import SignCheck, SAVE_HUD, RESTORE_HUD, center_editor, capture_editor, world_sample
from verify_snow_plant_visibility import changed, count, world_cell_roi
from visual_environment import SETUP_DAYLIGHT, RESTORE_DAYLIGHT

ROOT = Path(__file__).resolve().parents[1]
LOAD = '''from copy import deepcopy
from modern_projection.projection.model import Document
from modern_projection.projection.world_capture import merge_palette,restore_omitted_palette_cells
from modern_projection.projection.cell import rebase,foreground,background,actor_data,make_cell
from modern_projection.projection.visible_actor import compose_actor,render_actor
from modern_projection.projection.nbt_spatial import rebase as rebase_nbt
from modern_projection.projection.debug_blueprints import build,VISUAL_CASES
from modern_projection.projection.debug_appearance_blueprints import CASE_POSITIONS
from modern_projection.projection.block_groups import group_partner
case=VISUAL_CASES['entity_appearances']
identity,source=%r,%r
focus=case['focus']
doc=Document(case['isolated_size'],name='Entity appearance '+identity)
index=next(i for i,row in enumerate(sys._p0_entity_appearance_entities) if row['case']==identity)
row=sys._p0_entity_appearance_entities[index]
public_source=None
if identity.startswith('bed_'):
 blueprint=build(case['fixture'])
 target=CASE_POSITIONS[identity]
 first=foreground(blueprint.get(target))
 relationship=group_partner(first)
 assert relationship is not None,('Public bed has no partner',identity,first)
 partner=tuple(target[axis]+relationship[0][axis] for axis in range(3))
 assert foreground(blueprint.get(partner))==relationship[1],('Public bed partner changed',identity)
 public_source={'target':target,'cells':[
  {'pos':point,'foreground':foreground(blueprint.get(point))} for point in (target,partner)]}
if source=='native':
 origin=tuple(row['pos'][axis]-focus[axis] for axis in range(3))
 lo=tuple(row['palette_origin'])
 size=tuple(max(point[axis] for point in row['cells'])-lo[axis]+1 for axis in range(3))
 destination=tuple(lo[axis]-origin[axis] for axis in range(3))
 merge_palette(doc,deepcopy(sys._p0_entity_appearance_palettes[index]),destination,size,origin)
 restore_omitted_palette_cells(doc,sys._p0_entity_appearance_palettes[index],destination,size,origin,
                              b.factory.CreateBlockInfo(b.level).GetBlock)
 for cell in row['cell_nbt']:
  pos=tuple(cell['pos'][axis]-origin[axis] for axis in range(3))
  value=doc.get(pos)
  actor=compose_actor(render_actor(actor_data(value)),rebase_nbt(cell['nbt'],tuple(-v for v in origin)))
  doc.blocks[pos]=make_cell(foreground(value),background(value),actor)
else:
 blueprint=build(case['fixture'])
 target=CASE_POSITIONS[identity]
 delta=tuple(focus[axis]-target[axis] for axis in range(3))
 origin=tuple(row['pos'][axis]-target[axis] for axis in range(3))
 points=([cell['pos'] for cell in public_source['cells']] if public_source is not None else
         [tuple(cell[axis]-origin[axis] for axis in range(3)) for cell in row['cells']])
 for point in points:
  pos=tuple(point[axis]+delta[axis] for axis in range(3))
  doc.blocks[pos]=rebase(blueprint.get(point),delta)
sys._blueprint_qa_identity='entity.'+source+'.'+identity
sys._blueprint_qa_nonce+=1
sys._blueprint_qa_expected={'metadata':{'name':doc.name,'size':doc.size,'blocks':len(doc.blocks)},
 'previous_document_id':id(s.editor.document),'editor_id':None}
s._loaded(doc)
if public_source is None:s.camera_pivot=tuple(v+.5 for v in focus)
s.camera_view(*case['isolated_camera']['editor'])
s.emit()
_result=json.dumps({'identity':sys._blueprint_qa_identity,'editor_id':id(s.editor),
 'document_id':id(doc),'metadata':{'name':doc.name,'size':doc.size,'blocks':len(doc.blocks)},
 'public_source':public_source})
'''


def require_bed_calibration(calibration, runtime=None):
    assert calibration is not None and calibration.get('completed') and calibration.get('passed'), \
        'Bed comparison requires a completed, passed native cube camera calibration'
    session = os.environ.get('MCDEV_SESSION_FILE')
    assert session and calibration.get('session_file') and \
        Path(calibration['session_file']).resolve() == Path(session).resolve(), 'Calibration belongs to another instance'
    if runtime is not None:
        assert calibration['runtime_minecraft_version'] == runtime['version'], 'Calibration game version changed'
        assert abs(calibration['reported_fov'] - runtime['fov']) < .01, 'Camera FOV changed since calibration'
        assert abs(calibration['screen_aspect'] - runtime['screen'][0] / runtime['screen'][1]) < .01, \
            'Viewport aspect changed since calibration'


def source_cells_at(public_source, anchor):
    target = public_source['target']
    assert len(public_source['cells']) == 2, 'Public bed must contain both source cells'
    return [tuple(anchor[axis] + cell['pos'][axis] - target[axis] for axis in range(3))
            for cell in public_source['cells']]


def camera_read(check):
    return check.run('cam=b.factory.CreateCamera(b.level)\n'
                     '_result=json.dumps({"position":cam.GetPosition(),"rotation":cam.GetCameraRotation(),'
                     '"source_origin":b.projection_mesh[2] if b.projection_mesh else None})')


def require_camera(actual, expected):
    assert len(actual['position']) == len(actual['rotation']) == 3 and matching_camera(actual, expected), \
        ('Bed capture camera does not match the declared pose', expected, actual)


def require_source_registration(actual, binding, contract):
    if binding['projection']:
        assert actual['source_origin'] is not None and tuple(actual['source_origin']) == tuple(contract['origin']), \
            ('Bed projection source origin changed during capture', contract['origin'], actual['source_origin'])


def bed_world_roi(check, size, cells, pose, calibration):
    runtime = check.run('cam=b.factory.CreateCamera(b.level)\n'
                        '_result=json.dumps({"fov":cam.GetFov(),'
                        '"screen":b.factory.CreateGame(b.level).GetScreenSize(),'
                        '"version":api.GetMinecraftVersion()})')
    require_bed_calibration(calibration, runtime)
    crop = (0, 0, size[0], size[1])
    mask = Image.new('L', size)
    projected = []
    for cell in cells:
        part, evidence = world_cell_roi(check, crop, size, cell, pose, calibration)
        mask = ImageChops.lighter(mask, part)
        projected.append(evidence)
    assert mask.getbbox() is not None, 'Public bed source cells have no screen region'
    return mask, {'cells': cells, 'cell_projection': projected, 'bounds': mask.getbbox(),
                  'scope': 'Full envelopes of both public blueprint source cells at the actual camera'}


def capture_bound_world(check, label, binding, capture):
    require_bed_calibration(binding['calibration'])
    contract = check.run('''anchor,offset,projection,cells=%r,%r,%r,%r
origin=tuple(b.projection_mesh[2]) if projection else (0,0,0)
requested_origin=tuple(s.origin) if projection else (0,0,0)
target=tuple(origin[i]+anchor[i]+.5 for i in range(3))
position=tuple(target[i]+offset[i] for i in range(3))
rotation=api.GetRotFromDir(tuple(target[i]-position[i] for i in range(3)))
_result=json.dumps({'expected':{'target':target,'position':position,
 'rotation':(rotation[0],rotation[1],0.)},'origin':origin,'requested_origin':requested_origin,
 'source_cells':[tuple(origin[i]+point[i] for i in range(3)) for point in cells]})
''' % (tuple(binding['anchor']), tuple(binding['offset']), binding['projection'], binding['cells']))
    expected = contract['expected']
    contract['settled'] = wait_camera_pose(check, expected)
    contract['before'] = camera_read(check)
    require_camera(contract['before'], expected)
    require_source_registration(contract['before'], binding, contract)
    shot = capture()
    contract['after'] = camera_read(check)
    require_camera(contract['after'], expected)
    require_source_registration(contract['after'], binding, contract)
    roi, source = bed_world_roi(check, shot['size'], contract['source_cells'], expected, binding['calibration'])
    contract['after_roi'] = camera_read(check)
    require_camera(contract['after_roi'], expected)
    require_source_registration(contract['after_roi'], binding, contract)
    path = Path(shot['path']).with_name(Path(shot['path']).stem + '_source_roi.png')
    roi.save(path)
    shot['source_roi'] = dict(source, path=str(path.resolve()))
    shot['camera_binding'] = contract
    return shot


class AppearanceCheck(SignCheck):
    world_binding = None

    def capture(self, label, tree=None):
        capture = lambda: SignCheck.capture(self, label, tree)
        if self.world_binding is None:
            return capture()
        return capture_bound_world(self, label, self.world_binding, capture)


def capture_bed_editor(check, label, camera):
    grid = check.run('_result=s.grid')
    try:
        check.run('s.grid=False\ns.emit()\n_result=True')
        return capture_editor(check, label, camera)
    finally:
        check.run('s.grid=%r\ns.emit()\n_result=True' % grid)


def bed_comparison(reference, reference_mask, actual, actual_mask, reference_roi, actual_roi):
    result = comparison(reference, reference_mask, actual, actual_mask)
    presence = {'reference_pixels': count(ImageChops.multiply(reference_mask, reference_roi)),
                'actual_pixels': count(ImageChops.multiply(actual_mask, actual_roi)), 'minimum_pixels': 100}
    presence['passed'] = presence['reference_pixels'] >= 100 and presence['actual_pixels'] >= 100
    result.update(source_presence=presence, comparison_scope='Full client frame; no observed geometry crop')
    result['passed'] = result['passed'] and presence['passed']
    return result


def bed_world_capture(check, label, case, offset):
    result = world_sample(check, label, case['focus'], offset, 1., case['projection_height'], mesh_origin=True)
    final = check.run(PROJECTION_STATUS)
    source = check.run(PROJECTION_SOURCE)
    assert not source['missing'] and projection_source_matches(source, source), source
    assert all(row.get('result') and not row.get('error') and
               row.get('editor_id') == source['editor_id'] and
               row.get('document_id') == source['document_id'] for row in result['native_calls']), result['native_calls']
    saved_player = check.run('_result=json.dumps(sys._blueprint_visual_saved["player"])')
    assert final['player'] == saved_player, (saved_player, final['player'])
    result.update(final=final, source=source,
                  native_evidence='current_source_submission' if result['native_calls'] else 'current_source_cached_geometry')
    return result


def pixels(shown, hidden, crop):
    first = Image.open(shown).convert('RGB')
    second = Image.open(hidden).convert('RGB')
    assert first.size == second.size, 'Appearance visibility capture dimensions changed'
    return first.crop(crop), changed(first.crop(crop), second.crop(crop), 25)


def comparison(reference, reference_mask, actual, actual_mask):
    if reference.size != actual.size:
        raise AssertionError('Appearance camera dimensions changed')
    total, observed = count(reference_mask), count(actual_mask)
    intersection = ImageChops.multiply(reference_mask, actual_mask)
    recall = count(ImageChops.multiply(reference_mask, actual_mask.filter(ImageFilter.MaxFilter(5)))) / max(1, total)
    precision = count(ImageChops.multiply(actual_mask, reference_mask.filter(ImageFilter.MaxFilter(5)))) / max(1, observed)
    interior = intersection.filter(ImageFilter.MinFilter(5))
    difference = changed(reference, actual, 55)
    agreement = 1. - count(ImageChops.multiply(interior, difference)) / max(1, count(interior))
    return {'passed': total >= 100 and observed >= 100 and recall >= .85 and precision >= .85 and agreement >= .65,
            'reference_pixels': total, 'actual_pixels': observed, 'recall': recall,
            'precision': precision, 'interior_color_agreement': agreement,
            'edge_tolerance_pixels': 2, 'color_threshold': 55}


def texture_comparison(reference, reference_mask, actual, actual_mask):
    interior = ImageChops.multiply(reference_mask, actual_mask).filter(ImageFilter.MinFilter(5))
    eligible = list(interior.tobytes())
    features = []
    for frame in (reference, actual):
        low = frame.filter(ImageFilter.BoxBlur(3))
        features.append([value - smooth for channel, blurred in zip(frame.split(), low.split())
                         for value, smooth, use in zip(channel.tobytes(), blurred.tobytes(), eligible) if use])
    energy = [sum(value * value for value in row) for row in features]
    cosine = None
    if all(value > 100 for value in energy):
        cosine = sum(left * right for left, right in zip(*features)) / math.sqrt(energy[0] * energy[1])
    return {'passed': len(features[0]) >= 450 and cosine is not None and cosine >= .45,
            'texture_cosine': cosine, 'minimum_texture_cosine': .45,
            'texture_samples': len(features[0]), 'texture_energy': energy,
            'scope': 'Local texture contrast at the identical native/projection camera'}


def restore_native_player(client):
    return execute(client, '''import sys
import mod.server.extraServerApi as api
saved=getattr(sys,'_p0_entity_appearances',{})
point=saved.get('qa_player_foot')
if point is not None:
 assert api.GetEngineCompFactory().CreatePos(saved['player']).SetFootPos(tuple(point))
 del saved['qa_player_foot']
_result=True
''')


def appearance_offset(row, configured, wall_camera):
    if not wall_camera or row.get('face') not in (2, 3, 4, 5):
        return tuple(configured)
    # Observe the exposed front; the opposite side is occluded by support.
    x, y, z = configured
    return {2: (x, y, z), 3: (-x, y, -z),
            4: (z, y, -x), 5: (-z, y, x)}[row['face']]


def native_capture(check, row, offset, support_block='minecraft:stone', source_cells=None, clear=True):
    check.run('b.stop_projection()\n_result=True')
    # Native block actors can be culled when the detached camera leaves the
    # player's chunks. Keep the player on an owned platform near the target.
    platform = (row['pos'][0] + int(math.floor(offset[0])), row['pos'][1] - 1,
                row['pos'][2] + int(math.floor(offset[2])))
    nearby = execute(check.client, '''import json,sys
import mod.server.extraServerApi as api
saved=sys._p0_entity_appearances
factory=api.GetEngineCompFactory()
position=factory.CreatePos(saved['player'])
assert 'qa_player_foot' not in saved
saved['qa_player_foot']=position.GetFootPos()
platform=%r
info=factory.CreateBlockInfo(saved['player'])
support=%r
assert info.GetBlockNew(support,saved['dimension'])['name']=='minecraft:stone'
support_write=info.SetBlockNew(support,{'name':%r,'aux':0},0,saved['dimension'],True,False)
support_readback=info.GetBlockNew(support,saved['dimension'])
assert support_readback['name']==%r and support_readback['aux']==0,support_readback
before_platform=info.GetBlockNew(platform,saved['dimension'])
assert before_platform['name']=='minecraft:air' or (platform in [tuple(p) for p in saved['reserved']] and before_platform['name']=='minecraft:stone')
if platform not in [tuple(p) for p in saved['reserved']]:saved['reserved'].append(platform)
platform_write=info.SetBlockNew(platform,{'name':'minecraft:stone','aux':0},0,saved['dimension'],True,False)
assert info.GetBlockNew(platform,saved['dimension'])=={'name':'minecraft:stone','aux':0}
assert position.SetFootPos((platform[0]+.5,platform[1]+1.,platform[2]+.5))
_result=json.dumps({'before':saved['qa_player_foot'],'after':position.GetFootPos(),'platform':platform,'support':support,'support_block':%r,
 'support_write':support_write,'support_readback':support_readback,'platform_write':platform_write})
''' % (platform, tuple(row['support']), support_block, support_block, support_block))
    pose = check.run('''target=%r
offset=%r
center=tuple(v+.5 for v in target)
position=tuple(center[axis]+offset[axis] for axis in range(3))
rotation=api.GetRotFromDir(tuple(center[axis]-position[axis] for axis in range(3)))
cam=b.factory.CreateCamera(b.level)
cam.DepartCamera()
cam.LockModCameraPitch(True)
cam.LockModCameraYaw(True)
assert cam.SetCameraPos(position)
assert cam.SetCameraRotation((rotation[0],rotation[1]+180.,0.))
_result=json.dumps({'position':position,'rotation':rotation,'target':center})
''' % (tuple(row['pos']), tuple(offset)))
    pose['settled'] = wait_camera_pose(check, pose)
    pose['nearby_player'] = nearby
    time.sleep(.35)
    pose['scope'] = 'Independently placed vanilla world block; no projection actor or palette rendering'
    pose['screenshot'] = check.capture(row['case'] + ('_real_native' if clear else '_vanilla_empty'))
    if not clear:
        restore_native_player(check.client)
        return pose
    execute(check.client, '''import json
import mod.server.extraServerApi as api
factory=api.GetEngineCompFactory()
player=api.GetPlayerList()[0]
info=factory.CreateBlockInfo(player)
dimension=factory.CreateDimension(player).GetEntityDimensionId()
cells=%r
for pos in cells:info.SetBlockNew(tuple(pos),{'name':'minecraft:air','aux':0},0,dimension,True,False)
_result=json.dumps([info.GetBlockNew(tuple(pos),dimension) for pos in cells])
''' % (source_cells if source_cells is not None else row['cells'],))
    check.wait('native fixture cells cleared',
               lambda values: all(name == 'minecraft:air' for name in values),
               lambda: check.run('''cells=%r
block=b.factory.CreateBlock(b.level)
names=[]
for pos in cells:
 data=block.GetBlockPaletteBetweenPos(tuple(pos),tuple(pos),False).SerializeBlockPalette()
 names.extend(value[0] for value in data.get('common',{}))
_result=json.dumps(names)
''' % (source_cells if source_cells is not None else row['cells'],)))
    time.sleep(.25)
    pose['hidden_screenshot'] = check.capture(row['case'] + '_real_native_hidden')
    restore_native_player(check.client)
    return pose


def cleanup_native_fixture(client):
    saved = execute(client, 'import sys\n_result=hasattr(sys,"_p0_entity_appearances")')
    if saved:
        return execute(client, (ROOT / 'tools/p0_entity_appearance_cleanup.py').read_text(encoding='utf8'))
    return {'created': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--case', action='append')
    parser.add_argument('--texture-probe', action='store_true')
    parser.add_argument('--opacity-probe', action='store_true')
    parser.add_argument('--wall-camera', action='store_true', help='Rotate both cameras to the exposed wall face')
    parser.add_argument('--native-resolution', action='store_true', help='Use owned background client captures')
    parser.add_argument('--candidate-flat-items', action='store_true',
                        help='Temporarily enable provisional flat item profiles; production acceptance stays false')
    parser.add_argument('--candidate-depth-delta', type=float,
                        help='Diagnostic logical Z translation in blocks; face2 only, never production acceptance')
    parser.add_argument('--candidate-alpha-ownership', action='store_true',
                        help='Diagnostic body/item geometry visibility controls; existing opacity gates stay unchanged')
    parser.add_argument('--camera-calibration', type=Path,
                        help='Completed native cube camera calibration from this exact instance; required for beds')
    parser.add_argument('--support-block', choices=('minecraft:stone', 'minecraft:magenta_concrete'),
                        default='minecraft:stone', help='Native reference support; contrast prevents a grey-on-grey mask')
    args = parser.parse_args()
    if args.candidate_flat_items and (not args.native_resolution or args.camera_calibration is None):
        parser.error('Candidate item checks require native captures and this instance camera calibration')
    if args.candidate_alpha_ownership and not args.candidate_flat_items:
        parser.error('Alpha ownership controls require candidate item checks')
    if args.candidate_flat_items and (not args.case or
            any(case not in ('frame_filled', 'glow_frame_filled') for case in args.case)):
        parser.error('Candidate item checks require explicit filled frame cases')
    if args.candidate_depth_delta is not None and (not args.candidate_flat_items or
            args.case != ['frame_filled'] or not 0 <= args.candidate_depth_delta <= 1.):
        parser.error('Semantic depth diagnostic requires only candidate frame_filled and a delta in [0,1]')
    if args.candidate_flat_items and args.output.exists():
        parser.error('Choose a fresh item candidate report')
    if args.candidate_flat_items:
        helper = os.environ.get('MCDEV_NATIVE_CAPTURE_HELPER')
        if not helper or Path(helper).resolve() != ROOT / 'tools/capture_native_window.py':
            parser.error('Candidate item checks require the reviewed owner-bound WGC capture helper')
    calibration = (json.loads(args.camera_calibration.read_text(encoding='utf8'))
                   if args.camera_calibration is not None else None)
    evidence = {'schema': 1, 'completed': False, 'passed': False, 'rows': [],
                'scope': 'Native actual block comparison is independent of native and built-in editor inputs.',
                'bed_diagnostic': 'Full client difference masks with fixed public source-cell ROI and bound actual camera',
                'camera_calibration': str(args.camera_calibration) if args.camera_calibration else None}
    evidence['candidate_flat_items'] = args.candidate_flat_items
    evidence['candidate_depth_delta_blocks'] = args.candidate_depth_delta
    evidence['candidate_alpha_ownership'] = args.candidate_alpha_ownership
    evidence['production_rendering_accepted'] = False
    if args.candidate_flat_items:
        from generate_flat_item_proxies import source_path
        evidence['candidate_source_sha256'] = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (Path(__file__), ROOT / 'tools/flat_frame_item_visual_checks.py',
                         ROOT / 'tools/flat_frame_item_visual_contract.md',
                         ROOT / 'tools/generate_flat_item_proxies.py',
                         ROOT / 'behavior_pack/modern_projection/projection/static_frame_item.py',
                         ROOT / 'behavior_pack/modern_projection/projection/static_frame_item_data.py',
                         ROOT / 'behavior_pack/modern_projection/projection/debug_appearance_blueprints.py', source_path())}
    installed = saved_visual = native_created = daylight_saved = hud_saved = candidate_enabled = False
    try:
        with Client(timeout=30) as client:
            check = AppearanceCheck(client, args.output, 60, native_resolution=args.native_resolution,
                                    background_only=True)
            try:
                check.run(INSTALL_PROBE)
                installed = True
                check.run(SAVE_VISUAL)
                saved_visual = True
                if args.candidate_flat_items:
                    runtime = check.run('cam=b.factory.CreateCamera(b.level)\n'
                        '_result=json.dumps({"fov":cam.GetFov(),"screen":b.factory.CreateGame(b.level).GetScreenSize(),'
                        '"version":api.GetMinecraftVersion()})')
                    require_bed_calibration(calibration, runtime)
                    evidence['candidate_runtime'] = runtime
                    evidence['candidate_profiles'] = check.run('''from copy import deepcopy
from modern_projection.projection import static_frame_item_data
assert not hasattr(sys,'_flat_frame_item_profiles_saved')
sys._flat_frame_item_profiles_saved=deepcopy(static_frame_item_data.FRAME_ITEMS)
profiles=[]
for key,profile in static_frame_item_data.FRAME_ITEMS.items():
 profiles.append({'identifier':key[0],'aux':key[1],'production_accepted':profile['accepted']})
 profile['accepted']=True
_result=json.dumps(profiles)
''')
                    candidate_enabled = True
                daylight_saved = True
                evidence['daylight'] = execute(client, SETUP_DAYLIGHT)
                path = ROOT / 'behavior_pack/modern_projection/projection/debug_blueprints.py'
                case = check.run('import base64\nimport modern_projection.projection.debug_blueprints as refreshed\n'
                                 'eval(compile(base64.b64decode(%r),%r,"exec"),refreshed.__dict__)\n'
                                 '_result=json.dumps(refreshed.VISUAL_CASES["entity_appearances"])' %
                                 (base64.b64encode(path.read_bytes()).decode('ascii'), str(path)))
                evidence['blueprint_case'] = case
                selected = args.case or case['acceptance_cases']
                allowed = tuple(case['acceptance_cases']) + (('frame_filled', 'glow_frame_filled')
                                                      if args.candidate_flat_items else ())
                assert all(name in allowed for name in selected), selected
                if any(identity.startswith('bed_') for identity in selected):
                    require_bed_calibration(calibration)
                    evidence['native_hud'] = check.run(SAVE_HUD)
                    hud_saved = True
                setup_code = (ROOT / 'tools/p0_entity_appearance_setup.py').read_text(encoding='utf8')
                native_created = True
                setup = execute(client, 'import sys\nsys._p0_entity_appearance_selected=%r\n' % (tuple(selected),) + setup_code)
                execute(client, 'import sys\nsys._p0_entity_appearance_rows=%r\n_result=True' % setup['rows'], True)
                read_code = (ROOT / 'tools/p0_entity_appearance_read.py').read_text(encoding='utf8')
                evidence['before_fill'] = replicated_palettes(client, read_code)
                if args.candidate_flat_items:
                    if check.navigation()['open']:
                        check.run('navigator.pop()\n_result=True')
                        check.wait('close workspace for empty reference', lambda nav: not nav['open'] and not nav['transition'], check.navigation)
                    evidence['native_empty_frames'] = {}
                    for row in evidence['before_fill']['rows']:
                        if not row.get('fill_item'):
                            continue
                        offset = appearance_offset(row, case['isolated_camera']['world_offset'], args.wall_camera)
                        evidence['native_empty_frames'][row['case']] = native_capture(check, row, offset, args.support_block, clear=False)
                    check.run(camera_restore_code(False))
                filled = execute(client, (ROOT / 'tools/p0_entity_appearance_fill.py').read_text(encoding='utf8'))
                assert all(row['fill_observed'] for row in filled['rows'] if row.get('fill_item')), filled
                evidence['filled'] = filled
                execute(client, 'import sys\nsys._p0_entity_appearance_rows=%r\n_result=True' % filled['rows'], True)
                inputs = replicated_palettes(client, read_code)
                evidence['native_inputs'] = inputs
                for identity in selected:
                    is_bed = identity.startswith('bed_')
                    row = next(row for row in inputs['rows'] if row['case'] == identity)
                    native_anchor = next(row for row in setup['rows'] if row['case'] == identity)['pos']
                    if is_bed:
                        assert tuple(row['pos']) == tuple(native_anchor), 'Native bed source anchor changed since fixed setup'
                    offset = appearance_offset(row, case['isolated_camera']['world_offset'], args.wall_camera)
                    result = {'case': identity, 'scopes': {}, 'world_offset': offset}
                    evidence['rows'].append(result)
                    editor_frames = {}
                    projected = None
                    for source in ('native', 'synthetic'):
                        check.run('owner.open_workspace()\n_result=True')
                        check.wait('workspace opened', lambda state: state['open'] and not state['transition'], check.navigation)
                        loaded = check.run(LOAD % (identity, source))
                        state = check.editor_preview('entity appearance current', loaded['metadata'], loaded['editor_id'], loaded['document_id'])
                        assert not state['preview_error'], state
                        time.sleep(.3)
                        if is_bed:
                            framing = center_editor(check, case['focus'], case['isolated_camera'])
                            shot = capture_bed_editor(check, identity + '_' + source + '_editor', framing)
                            result['public_source'] = loaded['public_source']
                        else:
                            shot = check.capture(identity + '_' + source + '_editor')
                        crop = viewport_crop(check, shot)
                        editor_frames[source] = Image.open(shot['path']).convert('RGB').crop(crop)
                        result['scopes'][source + '_editor'] = {'screenshot': shot, 'crop': crop, 'identity': loaded,
                            'scope': ('Fresh vanilla NBT loaded into candidate palette editor; not a vanilla world reference'
                                      if source == 'native' and args.candidate_flat_items else
                                      'Built-in blueprint loaded into palette editor' if source == 'synthetic' else
                                      'Fresh vanilla NBT loaded into palette editor')}
                        if source == 'synthetic' and args.candidate_flat_items:
                            from flat_frame_item_visual_checks import candidate_scopes
                            result['item_scopes'] = {}
                            candidate_scopes(check, identity, case, offset, LOAD % (identity, source), shot,
                                             result['item_scopes'], lambda: write_json(args.output, evidence),
                                             args.candidate_depth_delta, args.candidate_alpha_ownership)
                        if source == 'native':
                            if is_bed:
                                check.world_binding = {'anchor': case['focus'], 'offset': offset, 'projection': True,
                                    'cells': source_cells_at(loaded['public_source'], case['focus']), 'calibration': calibration}
                            try:
                                projected = (bed_world_capture(check, identity, case, offset) if is_bed else
                                             world_closeup(check, identity, case['focus'], offset, 1., case['projection_height']))
                            finally:
                                check.world_binding = None
                            result['projection'] = projected
                            if args.opacity_probe:
                                width, height = projected['screenshot']['size']
                                probe_crop = ((0, 0, width, height) if is_bed else
                                              (width // 3, height // 3, width * 2 // 3, height * 2 // 3))
                                check.run('assert b.factory.CreateActorRender(b.entity).SetActorBlockGeometryTransparency(b.projection_mesh[1],.5)\n_result=True')
                                try:
                                    if is_bed:
                                        check.world_binding = {'anchor': case['focus'], 'offset': offset, 'projection': True,
                                            'cells': source_cells_at(loaded['public_source'], case['focus']), 'calibration': calibration}
                                    time.sleep(.3)
                                    faded = check.capture(identity + '_opacity_half')
                                    unused_frame, opacity_mask = pixels(projected['screenshot']['path'],
                                                                        projected['hidden_screenshot']['path'], probe_crop)
                                    probe = opacity_comparison(projected['screenshot']['path'], faded['path'],
                                                               projected['hidden_screenshot']['path'], probe_crop, opacity_mask)
                                    result['opacity_probe'] = dict(probe, screenshot=faded)
                                finally:
                                    check.world_binding = None
                                    check.run('assert b.factory.CreateActorRender(b.entity).SetActorBlockGeometryTransparency(b.projection_mesh[1],1.)\n_result=True')
                    first, second = editor_frames['native'], editor_frames['synthetic']
                    result['editor_input_agreement'] = {'passed': count(changed(first, second, 35)) <= 100,
                                                        'changed_pixels': count(changed(first, second, 35)),
                                                        'scope': 'Built-in fixture versus freshly captured native input at identical editor camera.'}
                    check.run('navigator.pop()\n_result=True')
                    check.wait('workspace closed', lambda state: not state['open'] and not state['transition'], check.navigation)
                    native_source_cells = source_cells_at(result['public_source'], native_anchor) if is_bed else None
                    if is_bed:
                        check.world_binding = {'anchor': native_anchor, 'offset': offset, 'projection': False,
                                               'cells': native_source_cells, 'calibration': calibration}
                    try:
                        real = native_capture(check, row, offset, args.support_block, native_source_cells)
                    finally:
                        check.world_binding = None
                    result['real_native'] = real
                    width, height = projected['screenshot']['size']
                    crop = ((0, 0, width, height) if is_bed else
                            (width // 3, height // 3, width * 2 // 3, height * 2 // 3))
                    shown, mask = pixels(projected['screenshot']['path'], projected['hidden_screenshot']['path'], crop)
                    native, native_mask = pixels(real['screenshot']['path'], real['hidden_screenshot']['path'], crop)
                    if is_bed:
                        native_roi = Image.open(real['screenshot']['source_roi']['path']).convert('L')
                        projection_roi = Image.open(projected['screenshot']['source_roi']['path']).convert('L')
                        result['native_projection_agreement'] = bed_comparison(
                            native, native_mask, shown, mask, native_roi, projection_roi)
                        # Preserve the existing >150 visibility gate on the full client frame.
                        visibility_pixels = count(changed(shown,
                            Image.open(projected['hidden_screenshot']['path']).convert('RGB'), 12))
                        result['projection_visibility'] = {'passed': visibility_pixels > 150,
                            'changed_pixels': visibility_pixels, 'threshold': 12, 'minimum_exclusive': 150, 'crop': crop}
                    else:
                        result['native_projection_agreement'] = comparison(native, native_mask, shown, mask)
                    result['native_projection_agreement']['crop'] = crop
                    if args.candidate_flat_items:
                        from flat_frame_item_visual_checks import content_mask
                        empty = evidence['native_empty_frames'][identity]
                        native_item, native_item_mask = content_mask(real['screenshot']['path'], empty['screenshot']['path'], crop)
                        result['item_scopes']['native_reference'] = {'empty': empty, 'filled': real,
                            'item_pixels': count(native_item_mask), 'passed': count(native_item_mask) >= 80}
                        for mode in ('full', 'missing'):
                            scoped = result['item_scopes'][mode]
                            body = result['item_scopes']['world_body']['screenshot']['path']
                            actual_item, actual_item_mask = content_mask(scoped['shown']['screenshot']['path'], body, crop)
                            scoped['native_item_agreement'] = comparison(native_item, native_item_mask, actual_item, actual_item_mask)
                        result['item_scopes']['passed'] = (result['item_scopes']['editor']['passed'] and
                            result['item_scopes']['document_nonmutation'] and
                            result['item_scopes']['native_reference']['passed'] and result['item_scopes']['stop_owners']['passed'] and
                            all(result['item_scopes'][mode]['presence_passed'] for mode in ('full', 'missing')) and
                            all(result['item_scopes'][mode][key]['passed'] for mode in ('full', 'missing')
                                for key in ('alpha02', 'alpha0', 'native_item_agreement')))
                    if args.texture_probe:
                        result['native_projection_texture'] = texture_comparison(native, native_mask, shown, mask)
                    result['passed'] = (result['editor_input_agreement']['passed'] and
                                        result['native_projection_agreement']['passed'] and
                                        result.get('native_projection_texture', {'passed': True})['passed'] and
                                        result.get('projection_visibility', {'passed': True})['passed'] and
                                        result.get('opacity_probe', {'passed': True})['passed'] and
                                        result.get('item_scopes', {'passed': True})['passed'])
                    write_json(args.output, evidence)
                    print(json.dumps({'case': identity, 'passed': result['passed']}), flush=True)
                    check.run(camera_restore_code(False))
                evidence['completed'] = True
                evidence['passed'] = all(row['passed'] for row in evidence['rows'])
            finally:
                errors = []
                actions = []
                if saved_visual:
                    actions.extend((('projection', lambda: check.run('b.stop_projection()\n_result=True')),
                                    ('camera', lambda: check.run(camera_restore_code(False))),
                                    ('visual', lambda: check.run('saved=sys._blueprint_visual_saved\n'
                                      's.origin=saved["origin"]\ns.opacity=saved["opacity"]\n'
                                      's.projection_missing=saved["missing"]\ns.projection_outline=saved["outline"]\n'
                                      'del sys._blueprint_visual_saved\n_result=True'))))
                if native_created:
                    actions.append(('native_player', lambda: restore_native_player(client)))
                    actions.append(('native', lambda: cleanup_native_fixture(client)))
                if daylight_saved:
                    actions.append(('daylight', lambda: execute(client, RESTORE_DAYLIGHT)))
                if hud_saved:
                    actions.append(('native_hud', lambda: check.run(RESTORE_HUD)))
                if candidate_enabled:
                    actions.append(('candidate_profiles', lambda: check.run('''from modern_projection.projection import static_frame_item_data
static_frame_item_data.FRAME_ITEMS=sys._flat_frame_item_profiles_saved
del sys._flat_frame_item_profiles_saved
_result=True
''')))
                if installed:
                    def restore_workspace():
                        was_open=check.run('_result=sys._blueprint_qa_saved["workspace"]')
                        check.run(RESTORE)
                        if was_open:
                            check.run('owner.open_workspace()\n_result=True')
                            check.wait('restored workspace opened',lambda state:state['open'] and not state['transition'],check.navigation)
                        elif check.navigation()['open']:
                            check.run('navigator.pop()\n_result=True')
                            check.wait('restored workspace closed',lambda state:not state['open'] and not state['transition'],check.navigation)
                    actions.append(('workspace',restore_workspace))
                for label, action in actions:
                    try:
                        action()
                    except Exception as error:
                        errors.append(label + ': ' + str(error))
                execute(client, 'import sys\nfor name in ("_p0_entity_appearance_rows","_p0_entity_appearance_palettes",'
                        '"_p0_entity_appearance_entities"):\n if hasattr(sys,name):delattr(sys,name)\n_result=True', True)
                evidence['restored'] = not errors
                if errors:
                    evidence['cleanup_errors'] = errors
                    evidence['completed'] = evidence['passed'] = False
                    raise RuntimeError(errors)
    except Exception as error:
        evidence['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        write_json(args.output, evidence)
    return 0 if evidence['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
