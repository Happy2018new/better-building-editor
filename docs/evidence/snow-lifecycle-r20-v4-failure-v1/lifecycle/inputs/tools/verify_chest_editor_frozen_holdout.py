"""Frozen native-world chest controls versus the ordinary product Scene viewport.

An independent unit cube fixes registration before any chest frames. The
original chest thresholds apply to its registered bounds without chest fitting.
"""
import argparse
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

from PIL import Image, ImageChops

import verify_copper_chest_render as native
import verify_chest_top_public_visuals as public
from shulker_pixels import _prepared_pair
from verify_camera_projection import largest_component
from verify_debug_blueprints import Client, INSTALL_PROBE, RESTORE, STATUS, write_json
from verify_debug_visuals import SAVE_VISUAL, PROJECTION_STATUS, camera_restore_code
from verify_hanging_sign_front_holdout import record_file
from verify_missing_neighbor_visuals import maximum, camera_matches
from verify_native_entity_appearances import execute
from verify_neighbor_world_visuals import CAPTURE_OPTIONS, RESTORE_OPTIONS
from verify_shulker_orientations import viewport_crop
from verify_sign_visuals import (SignCheck, SAVE_HUD, RESTORE_HUD, capture_editor,
                                 editor_pose_matches, restore_editor_overlays)
from visual_environment import SETUP_DAYLIGHT, RESTORE_DAYLIGHT

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.debug_blueprints import VISUAL_CASES, material

LOAD_EDITOR = '''from modern_projection.projection.model import Document
from modern_projection.projection.cell import foreground
from modern_projection.projection.debug_blueprints import VISUAL_CASES
identity,empty=%r,%r
source=sys._copper_native_document
doc=Document(source.size,{} if empty else source.blocks.copy(),name='Chest editor '+identity)
points=tuple(source.blocks)
center=tuple((min(pos[i] for pos in points)+max(pos[i] for pos in points)+1.)/2. for i in range(3))
sys._blueprint_qa_identity='chest.editor.'+identity+('.empty' if empty else '.shown')
sys._blueprint_qa_nonce+=1
sys._blueprint_qa_expected={'metadata':{'name':doc.name,'size':doc.size,'blocks':len(doc.blocks)},
 'previous_document_id':id(s.editor.document),'editor_id':None}
s._loaded(doc)
s.grid=False
s.camera_pivot=center
s.camera_pan=(0.,0.)
s.camera_focus_request=None
s.camera_view(*VISUAL_CASES['chest_top']['camera']['editor'])
s.focused=s.box_anchor=None
s.emit()
owner.open_workspace()
_result=json.dumps({'metadata':{'name':doc.name,'size':doc.size,'blocks':len(doc.blocks)},
 'editor_id':id(s.editor),'document_id':id(doc),'center':center,'document':doc.to_data()})
'''

EDITOR_STATE = '''_result=json.dumps({'pose':s.camera_pose,'pivot':s.camera_pivot,
 'pan':s.camera_pan,'grid':s.grid,'document':s.editor.document.to_data(),
 'editor_id':id(s.editor),'document_id':id(s.editor.document)})'''

HIDE_EDITOR_GEOMETRY = '''host=navigator.top._host
def chest_diag_walk(fiber):
 yield fiber
 for child in fiber.child_fibers:
  for descendant in chest_diag_walk(child):yield descendant
overlays=[]
for fiber in chest_diag_walk(host._root_fiber):
 if fiber.key in ('surface0','surface1'):
  mapped=next((child for child in chest_diag_walk(fiber) if child.native_path),None)
  assert mapped is not None,fiber.key
  control=host.GetBaseUIControl(mapped.native_path)
  overlays.append({'key':fiber.key,'path':mapped.native_path,'before':control.GetVisible()})
assert overlays and any(row['before'] for row in overlays),overlays
for row in overlays:
 control=host.GetBaseUIControl(row['path'])
 control.SetVisible(False)
 row['after']=control.GetVisible()
 assert not row['after'],row
_result=json.dumps({'overlays':overlays,'scope':'Existing ordinary Scene PreviewTile surfaces only'})
'''

CUBE = '''import json,sys
import mod.server.extraServerApi as api
saved=sys._copper_native_probe
info=api.GetEngineCompFactory().CreateBlockInfo(saved['player'])
target=tuple(saved['target'])
for pos in saved['reserved']:
 if pos[1]==target[1]-1:assert info.SetBlockNew(tuple(pos),{'name':'minecraft:air','aux':0},0,saved['dimension'],False,False)
assert info.SetBlockNew(target,{'name':'minecraft:stone','aux':0},0,saved['dimension'],False,False)
saved['cells']=[target]
_result=json.dumps({'cells':[target],'name':'minecraft:stone'})
'''

BACKGROUND = '''import json,sys
import mod.server.extraServerApi as api
saved=sys._copper_native_probe
info=api.GetEngineCompFactory().CreateBlockInfo(saved['player'])
target=tuple(saved['target'])
config,value=%r,%r
cells=[(target[0]+x,target[1]+config['offset_y'],target[2]+z)
 for x in range(-config['radius'],config['radius']+1)
 for z in range(-config['radius'],config['radius']+1)]
for pos in cells:assert info.GetBlockNew(pos,saved['dimension'])['name']=='minecraft:air',(pos,info.GetBlockNew(pos,saved['dimension']))
saved['reserved'].extend(cells)
for pos in cells:assert info.SetBlockNew(pos,{'name':value[0],'aux':value[1]},0,saved['dimension'],False,False)
_result=json.dumps({'cells':cells,'material':value,'confirmed_air_before':True})
'''


def extract(shown, empty, crop, output):
    with Image.open(shown).convert('RGB') as image, Image.open(empty).convert('RGB') as background:
        assert image.size == background.size, 'Frame dimensions changed'
        signal = maximum(ImageChops.difference(image, background)).crop(crop)
        selected = image.crop(crop)
    mask = largest_component(signal.point(lambda value: 255 if value > 25 else 0))
    bounds, pixels = mask.getbbox(), mask.histogram()[255]
    assert bounds is not None and pixels >= 1000, 'No chest/cube contributes 1000 pixels: %r' % pixels
    result = Image.new('RGB', selected.size)
    result.paste(selected, mask=mask)
    result.save(output)
    mask.save(output.with_name(output.stem + '_mask.png'))
    resize = getattr(Image, 'Resampling', Image)
    record = {'bbox': bounds, 'world_bounds': [value + crop[axis % 2] for axis, value in enumerate(bounds)],
              'pixels': pixels, 'crop': crop, 'signal': str(output.resolve())}
    return result.crop(bounds).resize((64, 64), resize.BILINEAR), mask.crop(bounds).resize((64, 64), resize.NEAREST), record


def registration(native_cube, editor_cube):
    first, second = native_cube['world_bounds'], editor_cube['world_bounds']
    ratios = [(second[i+2]-second[i]) / float(first[i+2]-first[i]) for i in range(2)]
    scale = sum(ratios) / 2.
    assert max(abs(value / scale-1.) for value in ratios) <= .02, 'Unit cube registration has anisotropic scale'
    centers = [[(box[i]+box[i+2])/2. for i in range(2)] for box in (first, second)]
    return {'scale': scale, 'axis_ratios': ratios, 'native_center': centers[0], 'editor_center': centers[1],
            'native_cube': native_cube, 'editor_cube': editor_cube,
            'contract': 'Uniform scale and centers fixed only by independent stone cube before chest frames'}


def compare(reference, editor, transform):
    first = reference[2]
    bounds = first['world_bounds']
    registered = [(bounds[i]-transform['native_center'][i % 2])*transform['scale']+
                  transform['editor_center'][i % 2] for i in range(4)]
    registered_record = dict(first, bbox=registered, world_bounds=registered)
    result = _prepared_pair((reference[0], reference[1], registered_record), editor)
    result['alignment'] = native.world_alignment(registered_record, editor[2])
    result['registration'] = transform
    result['passed'] = (result['shape_iou'] >= .82 and result['texture_cosine'] is not None and
                        result['texture_cosine'] >= .45 and result['scale_relative_error'] <= .2 and
                        result['alignment']['passed'])
    return result


def close_editor(check):
    if check.navigation()['open']:
        check.run('navigator.pop()\n_result=True')
        check.wait('workspace closed', lambda value: not value['open'] and not value['transition'], check.navigation)


def native_pose(check, cells, config):
    code = native.CAPTURE.replace('(-3.5,-3.,-5.)', repr(tuple(config['camera']['world_offset'])))
    pose = check.run(code % (cells,))
    position = tuple(pose['position'])
    execute(check.client, public.PLAYER_AT_CAMERA % (position, (pose['rotation'][0], pose['rotation'][1]-180.)))
    check.wait('player replicated at native camera',
               lambda value: all(abs(value[i]-position[i]) < .02 for i in range(3)),
               lambda: check.run('_result=b.player_position.GetFootPos()'))
    time.sleep(.5)
    check.run('cam=b.factory.CreateCamera(b.level)\ncam.DepartCamera()\n'
              'cam.LockModCameraPitch(True)\ncam.LockModCameraYaw(True)\n'
              'assert cam.SetCameraPos(%r)\nassert cam.SetCameraRotation(%r)\n_result=True' %
              (position, tuple(pose['rotation'])))
    check.wait('declared native camera', lambda value: camera_matches(value, pose), lambda: check.run(native.CAMERA))
    time.sleep(.5)
    return pose


def editor_shot(check, label, identity, empty, config):
    source = check.run(LOAD_EDITOR % (identity, empty))
    check.wait('ordinary workspace opens', lambda value: value['open'] and not value['transition'], check.navigation)
    check.editor_preview(label, source['metadata'], source['editor_id'], source['document_id'])
    check.wait('declared editor camera', lambda value: editor_pose_matches(value, config['camera']['editor']),
               lambda: check.run('_result=s.camera_pose'))
    time.sleep(.4)
    before = check.run(EDITOR_STATE)
    shot = capture_editor(check, label, {'declared_view': config['camera']})
    after = check.run(EDITOR_STATE)
    assert before == after, ('Actual editor state changed during capture', before, after)
    assert before['document'] == source['document']
    shot.update(editor_before=before, editor_after=after, source=source, crop=viewport_crop(check, shot))
    return shot


def editor_background(check, label, shown, config):
    before = check.run(EDITOR_STATE)
    assert before == shown['editor_after'], 'Blank control source changed'
    controls = check.run(HIDE_EDITOR_GEOMETRY)
    try:
        time.sleep(.2)
        shot = capture_editor(check, label, {'declared_view': config['camera']})
    finally:
        restored = restore_editor_overlays(check, controls)
    after = check.run(EDITOR_STATE)
    assert before == after, 'Blank control changed the actual editor source or camera'
    shot.update(editor_before=before, editor_after=after, source=shown['source'],
                crop=viewport_crop(check, shot), hidden_geometry=controls,
                restored_geometry=restored, document_preserved=True)
    return shot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--case-limit', type=int, choices=(1, 2, 3), default=3)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a new holdout directory')
    config = VISUAL_CASES['chest_top']
    helper = Path(os.environ['MCDEV_NATIVE_CAPTURE_HELPER']).resolve(strict=True)
    executable = Path(os.environ['MCDEV_NATIVE_CAPTURE_EXE']).resolve(strict=True)
    args.output.mkdir(parents=True)
    production = [record_file(path) for folder in ('behavior_pack', 'resource_pack')
                  for path in sorted((ROOT/folder).rglob('*')) if path.is_file()]
    tool_paths = sorted((ROOT/'tools').glob('*.py')) + sorted((ROOT/'tools/native_wgc').glob('*'))
    tool_paths += sorted((ROOT/'.agents/skills/pyreact-debugging/scripts').glob('*.py')) + [helper, executable]
    frozen = {'schema': 1, 'production': production,
              'tools': [record_file(path) for path in tool_paths if path.is_file()], 'config': config,
              'checked_out_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'limits': {'minimum_native_pixels': 1000, 'shape_iou': .82, 'texture_cosine': .45,
                         'scale_relative_error': .2, 'center_distance_pixels': 3, 'boundary_rms_pixels': 4}}
    write_json(args.output/'frozen_source.json', frozen)
    report = {'schema': 1, 'scope': 'True native world chest versus ordinary product editor Scene viewport; independent stone cube registration',
              'completed': False, 'passed': False, 'restored': False, 'cases': [], 'config': config,
              'session_file': os.environ.get('MCDEV_SESSION_FILE'), 'limits': frozen['limits']}
    flags = set()
    try:
        with Client(timeout=30) as client:
            check = SignCheck(client, args.output/'report.json', 60, native_resolution=True, background_only=True,
                              native_capture_helper=helper)
            try:
                report['options'] = check.run(CAPTURE_OPTIONS); flags.add('options')
                report['hud'] = check.run(SAVE_HUD); flags.add('hud')
                report['daylight'] = execute(client, SETUP_DAYLIGHT); flags.add('daylight')
                report['player'] = execute(client, public.SAVE_PLAYER); flags.add('player')
                check.run(INSTALL_PROBE); flags.add('probe')
                check.run(SAVE_VISUAL); flags.add('visual')
                report['grid'] = check.run('_result=s.grid')
                assert not check.navigation()['open'], 'Preflight requires a closed workspace'
                encoded = base64.b64encode((ROOT/'behavior_pack/modern_projection/projection/debug_blueprints.py').read_bytes()).decode('ascii')
                check.run('import base64\nimport modern_projection.projection.debug_blueprints as module\n'
                          'eval(compile(base64.b64decode(%r),%r,"exec"),module.__dict__)\n_result=True' %
                          (encoded, str(ROOT/'behavior_pack/modern_projection/projection/debug_blueprints.py')))
                report['runtime_config'] = check.run('from modern_projection.projection.debug_blueprints import VISUAL_CASES\n_result=json.dumps(VISUAL_CASES["chest_top"])')
                assert json.loads(json.dumps(config)) == report['runtime_config']
                setup = native.SETUP.replace('int(math.floor(foot[1]))+16', 'int(math.floor(foot[1]))+%d' % config['target_height_offset'])
                report['native_setup'] = native.server_run(client, setup); flags.add('world')
                report['native_background'] = native.server_run(client, BACKGROUND %
                    (config['native_background'], material(config['native_background']['material'])))
                time.sleep(1.)
                cube = report['calibration'] = {'placement': native.server_run(client, CUBE)}
                time.sleep(.5)
                cube['pose'] = native_pose(check, cube['placement']['cells'], config)
                cube['native'] = public.capture_at(check, 'cube_native', cube['pose'])
                native.server_run(client, native.CLEAR); time.sleep(.5)
                cube['empty'] = public.capture_at(check, 'cube_empty', cube['pose'])
                cube['editor'] = editor_shot(check, 'cube_editor', 'stone', False, config)
                cube['editor_empty'] = editor_background(check, 'cube_editor_empty', cube['editor'], config)
                crop = (int(cube['native']['size'][0]*.25), int(cube['native']['size'][1]*.2),
                        int(cube['native']['size'][0]*.75), int(cube['native']['size'][1]*.8))
                reference = extract(cube['native']['path'], cube['empty']['path'], crop, args.output/'cube_native_signal.png')
                editor = extract(cube['editor']['path'], cube['editor_empty']['path'], cube['editor']['crop'], args.output/'cube_editor_signal.png')
                transform = report['registration'] = registration(reference[2], editor[2])
                write_json(args.output/'registration_before_chests.json', transform)
                close_editor(check)
                for index, case in enumerate(config['cases'][:args.case_limit]):
                    row = dict(case); report['cases'].append(row)
                    row['placement'] = native.server_run(client, native.PLACE % (case['name'], case['direction'], case['paired']))
                    time.sleep(2.)
                    row['pose'] = native_pose(check, row['placement']['cells'], config)
                    row['public_source'] = check.run(public.LOAD_PUBLIC % (case['fixture'], case['cells']))
                    row['native'] = public.capture_at(check, str(index)+'_native', row['pose'])
                    native.server_run(client, native.CLEAR); time.sleep(.5)
                    row['empty'] = public.capture_at(check, str(index)+'_empty', row['pose'])
                    row['editor'] = editor_shot(check, str(index)+'_editor', case['id'], False, config)
                    row['editor_empty'] = editor_background(check, str(index)+'_editor_empty', row['editor'], config)
                    reference = extract(row['native']['path'], row['empty']['path'], crop, args.output/(str(index)+'_native_signal.png'))
                    editor = extract(row['editor']['path'], row['editor_empty']['path'], row['editor']['crop'], args.output/(str(index)+'_editor_signal.png'))
                    row.update(native_signal=reference[2], editor_signal=editor[2], comparison=compare(reference, editor, transform))
                    write_json(args.output/'report.json', report)
                    print(json.dumps({'case': case['id'], 'comparison': row['comparison']}), flush=True)
                    close_editor(check)
                report['completed'] = True
                report['passed'] = all(row['comparison']['passed'] for row in report['cases'])
            finally:
                if 'visual' in flags:
                    check.run('b.stop_projection()\n_result=True')
                    close_editor(check)
                    check.run(camera_restore_code(False))
                    check.run('saved=sys._blueprint_visual_saved\ns.origin=saved["origin"]\ns.opacity=saved["opacity"]\n'
                              's.projection_missing=saved["missing"]\ns.projection_outline=saved["outline"]\n'
                              'del sys._blueprint_visual_saved\ns.grid=%r\n_result=True' % report['grid'])
                if 'probe' in flags:
                    check.run(RESTORE)
                if 'world' in flags:
                    report['world_restored'] = native.server_run(client, native.CLEANUP)
                check.run('''for name in ('_copper_native_document','_copper_native_origin','_chest_top_public_snapshot'):
 if hasattr(sys,name):delattr(sys,name)
_result=True''')
                if 'player' in flags: report['player_restored'] = execute(client, public.RESTORE_PLAYER)
                if 'hud' in flags: report['hud_restored'] = check.run(RESTORE_HUD)
                if 'options' in flags: report['options_restored'] = check.run(RESTORE_OPTIONS)
                if 'daylight' in flags: report['daylight_restored'] = execute(client, RESTORE_DAYLIGHT)
                report['restored'] = True
    except Exception as error:
        report['error'] = '%s: %s' % (type(error).__name__, error)
        raise
    finally:
        unchanged = all(hashlib.sha256(Path(row['path']).read_bytes()).hexdigest() == row['sha256']
                        for row in production + frozen['tools'])
        write_json(args.output/'frozen_source_after.json', {'production_and_tools_unchanged': unchanged})
        write_json(args.output/'report.json', report)
    print(json.dumps({'completed': report['completed'], 'passed': report['passed'], 'restored': report['restored']}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
