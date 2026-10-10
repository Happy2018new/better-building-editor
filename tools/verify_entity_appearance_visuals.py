"""Independent native/editor/projection appearance checks linked to built-in cases."""
import argparse
import base64
import json
from pathlib import Path
import sys
import time

from PIL import Image, ImageChops, ImageFilter
from verify_debug_blueprints import BlueprintCheck, Client, INSTALL_PROBE, RESTORE, write_json
from verify_debug_visuals import SAVE_VISUAL, camera_restore_code, world_closeup
from verify_native_entity_appearances import execute, replicated_palettes
from verify_shulker_orientations import viewport_crop, wait_camera_pose
from verify_snow_plant_visibility import changed, count
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
case=VISUAL_CASES['entity_appearances']
identity,source=%r,%r
focus=case['focus']
doc=Document(case['isolated_size'],name='Entity appearance '+identity)
index=next(i for i,row in enumerate(sys._p0_entity_appearance_entities) if row['case']==identity)
row=sys._p0_entity_appearance_entities[index]
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
 for cell in row['cells']:
  point=tuple(cell[axis]-origin[axis] for axis in range(3))
  pos=tuple(point[axis]+delta[axis] for axis in range(3))
  doc.blocks[pos]=rebase(blueprint.get(point),delta)
sys._blueprint_qa_identity='entity.'+source+'.'+identity
sys._blueprint_qa_nonce+=1
sys._blueprint_qa_expected={'metadata':{'name':doc.name,'size':doc.size,'blocks':len(doc.blocks)},
 'previous_document_id':id(s.editor.document),'editor_id':None}
s._loaded(doc)
s.camera_pivot=tuple(v+.5 for v in focus)
s.camera_view(*case['isolated_camera']['editor'])
s.emit()
_result=json.dumps({'identity':sys._blueprint_qa_identity,'editor_id':id(s.editor),
 'document_id':id(doc),'metadata':{'name':doc.name,'size':doc.size,'blocks':len(doc.blocks)}})
'''


def pixels(shown, hidden, crop):
    first = Image.open(shown).convert('RGB').crop(crop)
    second = Image.open(hidden).convert('RGB').crop(crop)
    return first, changed(first, second, 25)


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


def native_capture(check, row, offset):
    check.run('b.stop_projection()\n_result=True')
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
    time.sleep(.35)
    pose['screenshot'] = check.capture(row['case'] + '_real_native')
    execute(check.client, '''import json
import mod.server.extraServerApi as api
factory=api.GetEngineCompFactory()
player=api.GetPlayerList()[0]
info=factory.CreateBlockInfo(player)
dimension=factory.CreateDimension(player).GetEntityDimensionId()
cells=%r
for pos in cells:info.SetBlockNew(tuple(pos),{'name':'minecraft:air','aux':0},0,dimension,True,False)
_result=json.dumps([info.GetBlockNew(tuple(pos),dimension) for pos in cells])
''' % (row['cells'],))
    check.wait('native fixture cells cleared',
               lambda values: all(name == 'minecraft:air' for name in values),
               lambda: check.run('''cells=%r
block=b.factory.CreateBlock(b.level)
names=[]
for pos in cells:
 data=block.GetBlockPaletteBetweenPos(tuple(pos),tuple(pos),False).SerializeBlockPalette()
 names.extend(value[0] for value in data.get('common',{}))
_result=json.dumps(names)
''' % (row['cells'],)))
    time.sleep(.25)
    pose['hidden_screenshot'] = check.capture(row['case'] + '_real_native_hidden')
    return pose


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--case', action='append')
    args = parser.parse_args()
    evidence = {'schema': 1, 'completed': False, 'passed': False, 'rows': [],
                'scope': 'Native actual block comparison is independent of native and built-in editor inputs.'}
    installed = saved_visual = native_created = daylight_saved = False
    try:
        with Client(timeout=30) as client:
            check = BlueprintCheck(client, args.output, 60)
            try:
                check.run(INSTALL_PROBE)
                installed = True
                check.run(SAVE_VISUAL)
                saved_visual = True
                daylight_saved = True
                evidence['daylight'] = execute(client, SETUP_DAYLIGHT)
                path = ROOT / 'behavior_pack/modern_projection/projection/debug_blueprints.py'
                case = check.run('import base64\nimport modern_projection.projection.debug_blueprints as refreshed\n'
                                 'eval(compile(base64.b64decode(%r),%r,"exec"),refreshed.__dict__)\n'
                                 '_result=json.dumps(refreshed.VISUAL_CASES["entity_appearances"])' %
                                 (base64.b64encode(path.read_bytes()).decode('ascii'), str(path)))
                evidence['blueprint_case'] = case
                selected = args.case or case['acceptance_cases']
                assert all(name in case['acceptance_cases'] for name in selected), selected
                native_created = True
                setup = execute(client, (ROOT / 'tools/p0_entity_appearance_setup.py').read_text(encoding='utf8'))
                execute(client, 'import sys\nsys._p0_entity_appearance_rows=%r\n_result=True' % setup['rows'], True)
                inputs = replicated_palettes(client, (ROOT / 'tools/p0_entity_appearance_read.py').read_text(encoding='utf8'))
                evidence['native_inputs'] = inputs
                for identity in selected:
                    row = next(row for row in inputs['rows'] if row['case'] == identity)
                    result = {'case': identity, 'scopes': {}}
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
                        shot = check.capture(identity + '_' + source + '_editor')
                        crop = viewport_crop(check, shot)
                        editor_frames[source] = Image.open(shot['path']).convert('RGB').crop(crop)
                        result['scopes'][source + '_editor'] = {'screenshot': shot, 'crop': crop, 'identity': loaded}
                        if source == 'native':
                            projected = world_closeup(check, identity, case['focus'], case['isolated_camera']['world_offset'], 1., case['projection_height'])
                            result['projection'] = projected
                    first, second = editor_frames['native'], editor_frames['synthetic']
                    result['editor_input_agreement'] = {'passed': count(changed(first, second, 35)) <= 100,
                                                        'changed_pixels': count(changed(first, second, 35)),
                                                        'scope': 'Built-in fixture versus freshly captured native input at identical editor camera.'}
                    check.run('navigator.pop()\n_result=True')
                    check.wait('workspace closed', lambda state: not state['open'] and not state['transition'], check.navigation)
                    real = native_capture(check, row, case['isolated_camera']['world_offset'])
                    result['real_native'] = real
                    width, height = projected['screenshot']['size']
                    crop = (width // 3, height // 3, width * 2 // 3, height * 2 // 3)
                    shown, mask = pixels(projected['screenshot']['path'], projected['hidden_screenshot']['path'], crop)
                    native, native_mask = pixels(real['screenshot']['path'], real['hidden_screenshot']['path'], crop)
                    result['native_projection_agreement'] = comparison(native, native_mask, shown, mask)
                    result['passed'] = (result['editor_input_agreement']['passed'] and
                                        result['native_projection_agreement']['passed'])
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
                    actions.append(('native', lambda: execute(client, (ROOT / 'tools/p0_entity_appearance_cleanup.py').read_text(encoding='utf8'))))
                if daylight_saved:
                    actions.append(('daylight', lambda: execute(client, RESTORE_DAYLIGHT)))
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
