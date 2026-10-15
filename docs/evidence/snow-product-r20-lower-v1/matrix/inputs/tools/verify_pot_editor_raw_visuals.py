"""Compare raw native palette and public fixture in the same real PaperDoll.

This is an orthographic editor check. It does not compare editor pixels to the
perspective world camera. Native palette objects are submitted directly,
without the document or production palette preparation path.
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from verify_debug_blueprints import Client, INSTALL_PROBE, RESTORE, write_json
from verify_debug_visuals import SAVE_VISUAL, camera_restore_code
from verify_native_entity_appearances import execute, replicated_palettes
from verify_native_pot_fields import SETUP, WRITE, READ, CLEANUP, SHERDS
from verify_pot_visuals import NEAR_PLAYER, RESTORE_PLAYER, maximum, largest_component
from verify_sign_visuals import SignCheck
from verify_shulker_orientations import viewport_crop
from visual_environment import SETUP_DAYLIGHT, RESTORE_DAYLIGHT

LOAD = '''from modern_projection.projection.debug_blueprints import build,VISUAL_CASES
from modern_projection.projection.cell import rebase
from modern_projection.projection.model import Document
case=VISUAL_CASES['pot_artwork']
identity,zoom=%r,%r
row=next(row for row in case['cases'] if row['id']==identity)
focus=(1,0,1)
doc=Document((3,3,3),name='Raw native editor control '+identity)
doc.blocks[focus]=rebase(build(case['fixture']).get(row['position']),tuple(focus[i]-row['position'][i] for i in range(3)))
s._loaded(doc)
s.editor._restore_selection(s.editor._selection_state(()))
s.touch_mode=True
s.box_anchor=s.focused=None
s.camera_view(case['camera']['editor'][0],case['camera']['editor'][1],zoom)
s.grid=False
sys._blueprint_qa_identity=case['fixture']+'.'+identity
sys._blueprint_qa_nonce+=1
metadata={'name':doc.name,'size':doc.size,'blocks':len(doc.blocks)}
sys._blueprint_qa_expected={'metadata':metadata,'editor_id':id(s.editor),'document_id':id(doc),'previous_document_id':None}
s.emit()
_result=json.dumps({'metadata':metadata,'editor_id':id(s.editor),'document_id':id(doc),'focus':focus})
'''

CONTROLS = '''from modern_projection.pyreact.debug import _type_name
host=navigator.top._host
def diag_walk(fiber):
 yield fiber
 for child in fiber.child_fibers:
  for descendant in diag_walk(child):yield descendant
fibers=list(diag_walk(host._root_fiber))
tile=next(fiber for fiber in fibers if _type_name(fiber)=='PreviewTile')
registry=tile.props['registry']
assert len(registry)==1,registry.keys()
key=tile.props['identity']
dolls,surfaces,preview=registry[key]
part=s.tiles.parts[key]
assert preview.ready(part['name']) and preview.pending is None
front=preview.front
control=dolls[front].current
overlay=[]
for fiber in fibers:
 if fiber.key in ('edge','cursor'):
  mapped=next((child for child in diag_walk(fiber) if child.native_path),None)
  assert mapped is not None,fiber.key
  original=host.GetBaseUIControl(mapped.native_path)
  overlay.append({'key':fiber.key,'path':mapped.native_path,'before':original.GetVisible()})
  original.SetVisible(False)
  overlay[-1]['after']=original.GetVisible()
assert set(row['key'] for row in overlay)==set(('edge','cursor')),overlay
_result=json.dumps({'key':key,'part_origin':part['origin'],'part_size':part['size'],
 'production_model':part['name'],'model_pose':preview.poses[front],
 'front':front,'control_position':control.GetPosition(),'control_size':control.GetSize(),
 'control_visible':control.GetVisible(),'overlays':overlay,
 'camera_pose':s.camera_pose,'camera_pivot':s.camera_pivot,'camera_pan':s.camera_pan,
 'scene_size':s.scene_size,'scene_origin':s.scene_origin,'scene_scale':s.scene_scale,
 'native_calls':len(sys._blueprint_qa_records)})
'''

RAW = '''target,focus,model_name=%r,%r,%r
world_origin=tuple(target[i]-focus[i] for i in range(3))
lo=tuple(world_origin[i]+part['origin'][i] for i in range(3))
hi=tuple(lo[i]+part['size'][i]-1 for i in range(3))
raw=api.GetEngineCompFactory().CreateBlock(b.level).GetBlockPaletteBetweenPos(lo,hi,False)
assert raw is not None
data=raw.SerializeBlockPalette()
assert tuple(data['volume'])==tuple(part['size'])
assert set(name[0] for name in data.get('common',{}))<=set(('minecraft:air','minecraft:decorated_pot'))
assert len(data.get('actor',{}).get('minecraft:decorated_pot',{}))==1,data.get('actor',{})
raw_geometry=sys._blueprint_qa_saved['factory'].CreateBlockGeometry(b.level)
returned=raw_geometry.CombineBlockPaletteToGeometry(raw,model_name,0)
assert returned==model_name,returned
pose=preview.poses[front]
original_native_dolls=preview.native_dolls
diag_raw_resubmissions=[]
class RawReferenceDollCallProbe(object):
 def __init__(self,target):self.target=target
 def __getattr__(self,name):return getattr(self.target,name)
 def RenderBlockGeometryModel(self,params):
  diag_raw_resubmissions.append(dict(params))
  return self.target.RenderBlockGeometryModel(params)
preview.native_dolls=tuple(RawReferenceDollCallProbe(doll) for doll in original_native_dolls)
assert control.asNeteasePaperDoll().RenderBlockGeometryModel({'block_geometry_model_name':returned,
 'scale':pose[0],'init_rot_x':pose[1],'init_rot_y':0.,'init_rot_z':pose[2]})
sys._pot_editor_diag_model_names.append(returned)
_result=json.dumps({'model':returned,'volume':data['volume'],'capture_lo':lo,'capture_hi':hi,
 'raw_palette_repr':repr(data),'actor':repr(data.get('actor',{})),
 'direct_raw_palette_object':True,'production_document_prepare_used':False,
 'render_params':{'block_geometry_model_name':returned,'scale':pose[0],'init_rot_x':pose[1],'init_rot_y':0.,'init_rot_z':pose[2]},
 'control_position':control.GetPosition(),'control_size':control.GetSize(),
 'native_calls':len(sys._blueprint_qa_records)})
'''


def frames(shown, raw, hidden, crop, output):
    if len({tuple(item['size']) for item in (shown, raw, hidden)}) != 1:
        raise AssertionError('Reference and production native viewport dimensions differ')
    width, height = shown['size']
    if not (0 <= crop[0] < crop[2] <= width and 0 <= crop[1] < crop[3] <= height):
        raise AssertionError('Actual viewport crop leaves the native client frame')
    with Image.open(shown['path']) as image:
        first = image.convert('RGB').crop(crop)
    with Image.open(raw['path']) as image:
        second = image.convert('RGB').crop(crop)
    with Image.open(hidden['path']) as image:
        blank = image.convert('RGB').crop(crop)
    masks = [largest_component(maximum(ImageChops.difference(frame, blank)).point(lambda value: 255 if value > 25 else 0)) for frame in (first, second)]
    bounds = [mask.getbbox() for mask in masks]
    signal_counts = [mask.histogram()[255] for mask in masks]
    delta = maximum(ImageChops.difference(first, second))
    changed = sum(delta.histogram()[26:])
    intersection = ImageChops.multiply(*masks).histogram()[255]
    union = ImageChops.lighter(*masks).histogram()[255]
    dimensions = first.size
    margins = [[box[0], box[1], dimensions[0] - box[2], dimensions[1] - box[3]] if box else None for box in bounds]
    framing = all(row is not None and min(row) >= 8 for row in margins)
    positive = signal_counts[1] >= 1000 and bounds[1] is not None
    agreement = positive and changed <= 100
    for label, frame, mask in zip(('production', 'raw_native'), (first, second), masks):
        signal = Image.new('RGB', dimensions)
        signal.paste(frame, mask=mask)
        signal.save(output / (label + '_signal.png'))
    delta.save(output / 'actual_viewport_difference.png')
    return {'raw_positive_control': positive, 'signal_pixels': signal_counts, 'bounds': bounds,
            'viewport': crop, 'margin_pixels': margins, 'framing_passed': framing,
            'changed_pixels_over_25': changed, 'shape_iou': intersection / float(max(1, union)),
            'pixel_agreement_passed': agreement, 'passed': agreement and framing,
            'limits': {'minimum_native_signal_pixels': 1000, 'maximum_changed_pixels': 100, 'minimum_viewport_margin_pixels': 8},
            'scope': 'Identical full real viewport, camera, control and native pose. Raw palette captured and submitted directly. No bbox normalization.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--direction', type=int, action='append', choices=range(4))
    parser.add_argument('--native-entity-definition', type=Path,
                        help='Optional installed vanilla pot definition for geometry provenance')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    report = {'schema': 1, 'completed': False, 'restored': False, 'passed': False, 'cases': [],
              'scope': 'Independent raw native palette rendering in the same actual orthographic PaperDoll as the public production fixture.',
              'declared_zooms': [2.8, 2.0], 'focus': [1, 0, 1],
              'focus_reason': 'Lowest document layer excludes the real native support below the captured palette; model coordinates come from exact palette volume and current production tile.',
              'geometry_homography': {'available': False, 'reason': 'Installed vanilla pot definition provides textures only; no verified native body vertex/UV export or proxy contract.'},
              'preserved_failure': 'pot-background-native-editor-world-r6-v8-four-directions/report.json'}
    if args.native_entity_definition:
        payload = args.native_entity_definition.read_bytes()
        definition = json.loads(payload.decode('utf-8-sig'))
        description = definition['minecraft:client_entity']['description']
        report['geometry_homography']['native_definition'] = {
            'path': str(args.native_entity_definition.resolve()),
            'sha256': hashlib.sha256(payload).hexdigest(),
            'identifier': description['identifier'], 'description_keys': sorted(description),
            'geometry': description.get('geometry'), 'texture_count': len(description.get('textures', {}))}
    installed = visual = daylight = native = hud = False
    with Client(timeout=30) as client:
        check = SignCheck(client, args.output / 'report.json', 45, native_resolution=True)
        try:
            report['workspace_before'] = check.navigation()['open']
            check.run(INSTALL_PROBE)
            installed = True
            check.run(SAVE_VISUAL + 'sys._blueprint_visual_saved["grid"]=s.grid\nsys._blueprint_visual_saved["touch_mode"]=s.touch_mode\nsys._pot_editor_diag_model_names=[]\n_result=True')
            visual = True
            execute(client, SETUP_DAYLIGHT)
            daylight = True
            report['hud'] = check.run('view=b.factory.CreatePlayerView(b.level)\noption=api.GetMinecraftEnum().OptionId.HIDE_HUD\nsys._pot_editor_diag_hud_saved=view.GetToggleOption(option)\nassert sys._pot_editor_diag_hud_saved in (0,1)\nassert view.SetToggleOption(option,True)\nassert view.GetToggleOption(option)==1\n_result=json.dumps({"before":sys._pot_editor_diag_hud_saved,"during":1})')
            hud = True
            report['native_setup'] = execute(client, SETUP)
            native = True
            target = tuple(report['native_setup']['target'])
            near = execute(client, NEAR_PLAYER % ((2.5, .3, 3.5),))
            check.wait('native player nearby', lambda foot: all(abs(a-b) < .1 for a, b in zip(foot, near['expected'])), lambda: check.run('_result=json.dumps(b.player_position.GetFootPos())'))
            report['near_player'] = near
            check.run('owner.open_workspace()\n_result=True')
            check.wait('workspace opens', lambda row: row['open'] and not row['transition'], check.navigation)
            for direction in args.direction or range(4):
                native_data = execute(client, WRITE % (direction, SHERDS))
                replication = replicated_palettes(client, READ % (target, direction, SHERDS))
                for zoom in report['declared_zooms']:
                    label = 'direction_%d_zoom_%s' % (direction, str(zoom).replace('.', '_'))
                    case_output = args.output / label
                    case_output.mkdir(exist_ok=True)
                    row = {'id': label, 'native_data': native_data, 'replication': replication}
                    report['cases'].append(row)
                    state = check.run(LOAD % ('direction_' + str(direction), zoom))
                    row['production_state'] = check.editor_preview(label, state['metadata'], state['editor_id'], state['document_id'])
                    check.run('s.focused=%r\ns.locate_selected()\n_result=True' % ((1, 0, 1),))
                    row['focus_consumed'] = check.wait('declared voxel center focus consumed',
                        lambda value: value['request'] is None and value['pivot'] == [1.5, .5, 1.5],
                        lambda: check.run('_result=json.dumps({"request":s.camera_focus_request,"pivot":s.camera_pivot})'))
                    check.run('s.camera_view(35.,10.,%r)\n_result=True' % zoom)
                    check.wait('declared editor zoom settles', lambda pose: abs(pose[2] - zoom) < .001,
                               lambda: check.run('_result=json.dumps(s.camera_pose)'))
                    time.sleep(.4)
                    row['controls'] = check.run(CONTROLS)
                    shown = check.capture(label + '_production')
                    crop = viewport_crop(check, shown)
                    model_name = 'r6_raw_pot_%d_zoom_%d' % (direction, round(zoom * 10))
                    row['raw_submission'] = check.run(RAW % (target, (1, 0, 1), model_name))
                    row['raw_submission']['raw_palette_repr_sha256'] = hashlib.sha256(row['raw_submission']['raw_palette_repr'].encode('utf8')).hexdigest()
                    time.sleep(.4)
                    row['raw_stability'] = check.run('_result=json.dumps({"native_calls":len(sys._blueprint_qa_records),"model_pose":preview.poses[front],"production_model":part["name"],"front":preview.front,"control_visible":control.GetVisible(),"production_resubmissions":diag_raw_resubmissions})')
                    assert row['raw_stability']['native_calls'] == row['raw_submission']['native_calls'], row['raw_stability']
                    assert not row['raw_stability']['production_resubmissions'], row['raw_stability']
                    raw = check.capture(label + '_raw_native')
                    check.run('assert not diag_raw_resubmissions,diag_raw_resubmissions\npreview.native_dolls=original_native_dolls\n_result=True')
                    check.run('surfaces[front].current.SetVisible(False)\n_result=True')
                    time.sleep(.25)
                    hidden = check.capture(label + '_hidden')
                    check.run('surfaces[front].current.SetVisible(True)\n_result=True')
                    row.update(production=shown, raw_native=raw, hidden=hidden, crop=crop,
                               comparison=frames(shown, raw, hidden, crop, case_output))
                    write_json(args.output / 'report.json', report)
            report['completed'] = True
            report['original_zoom_framing_passed'] = all(row['comparison']['framing_passed'] for row in report['cases'] if row['id'].endswith('2_8'))
            report['additional_zoom_2_0_reference_passed'] = all(row['comparison']['passed'] for row in report['cases'] if row['id'].endswith('2_0'))
            report['passed'] = all(row['comparison']['passed'] for row in report['cases'])
        finally:
            errors = []
            actions = []
            if native:
                actions.extend((('player', lambda: execute(client, RESTORE_PLAYER)), ('native', lambda: execute(client, CLEANUP))))
            if daylight:
                actions.append(('daylight', lambda: execute(client, RESTORE_DAYLIGHT)))
            if hud:
                actions.append(('hud', lambda: check.run('view=b.factory.CreatePlayerView(b.level)\nassert view.SetToggleOption(api.GetMinecraftEnum().OptionId.HIDE_HUD,bool(sys._pot_editor_diag_hud_saved))\nassert view.GetToggleOption(api.GetMinecraftEnum().OptionId.HIDE_HUD)==sys._pot_editor_diag_hud_saved\ndel sys._pot_editor_diag_hud_saved\n_result=True')))
            if visual:
                actions.extend((('raw_doll_probe', lambda: check.run('if "original_native_dolls" in globals():preview.native_dolls=original_native_dolls\n_result=True')),
                                ('projection', lambda: check.run('b.stop_projection()\n_result=True')),
                                ('camera', lambda: check.run(camera_restore_code(False))),
                                ('fields', lambda: check.run('saved=sys._blueprint_visual_saved\ns.grid=saved["grid"]\ns.touch_mode=saved["touch_mode"]\ns.origin=saved["origin"]\ns.opacity=saved["opacity"]\ns.projection_missing=saved["missing"]\ns.projection_outline=saved["outline"]\ndel sys._blueprint_visual_saved\ndel sys._pot_editor_diag_model_names\n_result=True'))))
            if installed:
                actions.append(('editor', lambda: check.run(RESTORE)))
            actions.append(('workspace', lambda: check.run('owner.open_workspace()\n_result=True' if report.get('workspace_before') else 'if navigator.contains("modern_projection_workspace"):navigator.pop()\n_result=True')))
            for name, action in actions:
                try:
                    result = action()
                    report['cleanup_' + name] = result
                    if name == 'native' and not result.get('restored'):
                        errors.append('native fixture remains')
                except Exception as error:
                    errors.append(name + ': ' + str(error))
            report['cleanup_errors'] = errors
            report['restored'] = not errors
            report['passed'] = report['passed'] and report['restored']
            write_json(args.output / 'report.json', report)
    print(json.dumps({'completed': report['completed'], 'restored': report['restored'], 'passed': report['passed'],
                      'original_zoom_framing_passed': report.get('original_zoom_framing_passed'),
                      'additional_zoom_2_0_reference_passed': report.get('additional_zoom_2_0_reference_passed'),
                      'cases': [{'id': row['id'], 'comparison': row.get('comparison')} for row in report['cases']]}))
    return 0 if report['completed'] and report['restored'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
