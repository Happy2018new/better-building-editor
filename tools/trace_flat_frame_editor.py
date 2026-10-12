"""Record one editor frame overlay submission without changing world blocks."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

from flat_frame_item_visual_checks import SWITCH, content_mask
from verify_debug_blueprints import Client, INSTALL_PROBE, RESTORE, write_json
from verify_sign_visuals import SignCheck
from verify_shulker_orientations import viewport_crop
from verify_snow_plant_visibility import count

ROOT = Path(__file__).resolve().parents[1]
LOAD = '''from modern_projection.projection.debug_blueprints import build,VISUAL_CASES
from modern_projection.projection.debug_appearance_blueprints import CASE_POSITIONS
from modern_projection.projection.model import Document
from modern_projection.projection.cell import rebase
case=VISUAL_CASES['entity_appearances']
doc=Document(case['isolated_size'],name='Frame editor submission diagnostic')
target=CASE_POSITIONS['frame_filled']
delta=tuple(case['focus'][axis]-target[axis] for axis in range(3))
doc.blocks[tuple(case['focus'])]=rebase(build(case['fixture']).get(target),delta)
sys._blueprint_qa_identity='entity.synthetic.frame_editor_submission'
sys._blueprint_qa_nonce+=1
metadata={'name':doc.name,'size':doc.size,'blocks':len(doc.blocks)}
sys._blueprint_qa_expected={'metadata':metadata,
 'previous_document_id':id(s.editor.document),'editor_id':None}
s._loaded(doc)
s.camera_pivot=tuple(v+.5 for v in case['focus'])
s.camera_view(*case['isolated_camera']['editor'])
s.emit()
_result=json.dumps({'metadata':metadata,'editor_id':id(s.editor),
 'document_id':id(doc),'document':doc.to_data(),'case':case})
'''
SAVE = '''from copy import deepcopy
from modern_projection.projection import static_frame_item_data
assert not hasattr(sys,'_frame_editor_profiles_saved')
assert not any(profile['accepted'] for profile in static_frame_item_data.FRAME_ITEMS.values())
sys._frame_editor_profiles_saved=deepcopy(static_frame_item_data.FRAME_ITEMS)
_result=True
'''
RESTORE_PROFILES = '''from modern_projection.projection import static_frame_item_data
static_frame_item_data.FRAME_ITEMS=sys._frame_editor_profiles_saved
del sys._frame_editor_profiles_saved
if hasattr(sys,'_frame_editor_control'):del sys._frame_editor_control
if hasattr(sys,'_frame_editor_transforms'):del sys._frame_editor_transforms
assert not any(profile['accepted'] for profile in static_frame_item_data.FRAME_ITEMS.values())
_result=True
'''
INSTALL_CONTROLS = '''from copy import deepcopy
sys._frame_editor_control='combined'
sys._frame_editor_transforms=[]
class FrameEditorNativeControl(object):
 def __init__(self,target,level):self.target=target;self.level=level
 def __getattr__(self,name):return getattr(self.target,name)
 def CombineBlockPaletteToGeometry(self,palette,name,mode=0):
  control=sys._frame_editor_control
  if control in ('item_only','blank','positive'):
   original=palette.SerializeBlockPalette()
   data=deepcopy(original)
   frames=('minecraft:frame','minecraft:glow_frame')
   for layer in ('common','states'):
    data[layer]=dict((key,value) for key,value in data.get(layer,{}).items() if key[0] not in frames)
   data['actor']=dict((key,value) for key,value in data.get('actor',{}).items() if key not in frames)
   items=[(key,list(indices)) for key,indices in data['common'].items()
          if key[0].startswith('modern_projection:preview_item_')]
   assert len(items)==1 and len(items[0][1])==1,items
   if control in ('blank','positive'):
    for key,indices in items:
     del data['common'][key]
     data['states'].pop(key,None)
     replacement=('minecraft:air' if control=='blank' else 'modern_projection:preview_shulker_blue_0',0)
     data['common'][replacement]=indices
   assert data['volume']==original['volume']
   palette=b.factory.CreateBlock(self.level).GetBlankBlockPalette()
   assert palette is not None and palette.DeserializeBlockPalette(data)
   sys._frame_editor_transforms.append({'nonce':sys._blueprint_qa_nonce,'control':control,
    'volume':data['volume'],'original_items':[{'material':key,'indices':indices} for key,indices in items],
    'removed_frame_indices':[index for key,indices in original.get('common',{}).items()
                             if key[0] in frames for index in indices],
    'submitted':[{'material':key,'indices':list(indices)} for key,indices in data['common'].items()],
    'remaining_actor_names':sorted(data.get('actor',{}))})
  return self.target.CombineBlockPaletteToGeometry(palette,name,mode)
class FrameEditorFactoryControl(object):
 def __init__(self,target):self.target=target
 def __getattr__(self,name):return getattr(self.target,name)
 def CreateBlockGeometry(self,level):
  return FrameEditorNativeControl(self.target.CreateBlockGeometry(level),level)
b.factory=FrameEditorFactoryControl(b.factory)
_result=True
'''


def frame_submission(state):
    records = state['native_calls']
    items = [entry for row in records for entry in row.get('frame_materials', ())
             if entry['material'][0].startswith('modern_projection:preview_item_')]
    return {'item_cells': sum(len(entry['indices']) for entry in items),
            'item_materials': items,
            'submitted_materials': [entry for row in records for entry in row.get('submitted_materials', ())],
            'native_call_count': len(records),
            'layouts': [row.get('render_layout') for row in state['parts']]}


def pixel_trace(shown, baseline, crop):
    unused, mask = content_mask(shown, baseline, crop, threshold=25)
    box = mask.getbbox()
    return {'pixels': count(mask), 'bbox': None if box is None else
            [box[0] + crop[0], box[1] + crop[1], box[2] + crop[0], box[3] + crop[1]],
            'crop': list(crop), 'threshold': 25}


def score_existing(path):
    evidence = json.loads(path.read_text(encoding='utf8'))
    controls = evidence['controls']
    captures = {}
    for name, control in controls.items():
        shot = control['capture']
        original = Path(shot['path'])
        capture = original if original.is_file() else path.parent / original.name
        if hashlib.sha256(capture.read_bytes()).hexdigest() != shot['sha256']:
            raise ValueError('Capture SHA-256 mismatch: %s' % capture)
        captures[name] = capture
    crop = evidence['crop']
    blank = captures['blank']
    body = captures['body']
    body_signal = pixel_trace(body, blank, crop)
    roi = body_signal['bbox']
    assert roi is not None, 'Body ROI is unavailable'
    return {'schema': 1, 'source_report': str(path.resolve()),
            'source_report_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'scorer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'production_rendering_accepted': False, 'body_roi_from_body_vs_blank': body_signal,
            'controls': {key: {'whole_viewport': pixel_trace(captures[key], blank, crop),
                               'body_roi': pixel_trace(captures[key], blank, roi),
                               'capture_sha256': controls[key]['capture']['sha256']}
                         for key in ('combined', 'item_only', 'positive')},
            'combined_vs_body': {key: pixel_trace(captures[key], body, crop)
                                 for key in ('combined', 'combined_repeat')}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--score-report', type=Path, help='Score an existing report offline without game access')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh report')
    if args.score_report:
        scored = score_existing(args.score_report)
        write_json(args.output, scored)
        print(json.dumps(scored))
        return 0
    helper = os.environ.get('MCDEV_NATIVE_CAPTURE_HELPER')
    if not helper or Path(helper).resolve() != ROOT / 'tools/capture_native_window.py':
        parser.error('Owner-bound background WGC helper is required')
    evidence = {'schema': 1, 'completed': False, 'passed': False,
                'production_rendering_accepted': False,
                'scope': 'Editor only: actual submitted palette and ready state; no world or shader changes',
                'session_file': os.environ.get('MCDEV_SESSION_FILE'),
                'source_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in (Path(__file__), ROOT / 'tools/verify_debug_blueprints.py',
                                 ROOT / 'tools/flat_frame_item_visual_checks.py',
                                 ROOT / 'behavior_pack/modern_projection/projection/static_frame_item.py',
                                 ROOT / 'behavior_pack/modern_projection/projection/static_frame_item_data.py',
                                 ROOT / 'behavior_pack/modern_projection/projection/geometry_palette.py',
                                 ROOT / 'behavior_pack/modern_projection/projection/bridge.py',
                                 ROOT / 'behavior_pack/modern_projection/projection/tiles.py',
                                 ROOT / 'behavior_pack/modern_projection/projection/scene.py',
                                 ROOT / 'behavior_pack/modern_projection/projection/preview_depth.py',
                                 ROOT / 'resource_pack/materials/entity.material',
                                 ROOT / 'resource_pack/materials/terrain.material',
                                 ROOT / 'resource_pack/shaders/glsl/modern_projection_biome_blocks.vertex',
                                 ROOT / 'behavior_pack/netease_blocks/preview_shulker_blue_0.json',
                                 ROOT / 'resource_pack/models/netease_block/preview_shulker_blue_0.json',
                                 ROOT / 'resource_pack/models/netease_block/preview_item_minecraft_diamond_sword_0_f2_r0.json')},
                'controls': {}}
    installed = saved = False
    try:
        with Client(timeout=20) as client:
            check = SignCheck(client, args.output, 30, native_resolution=True, background_only=True)
            try:
                check.run(INSTALL_PROBE)
                installed = True
                check.run(SAVE)
                saved = True
                check.run(INSTALL_CONTROLS)
                check.run('owner.open_workspace()\n_result=True')
                check.wait('editor opened', lambda nav: nav['open'] and not nav['transition'], check.navigation)
                document = None
                for label, enabled in (('combined', True), ('body', False), ('combined_repeat', True),
                                       ('item_only', True), ('blank', True), ('positive', True)):
                    check.run("sys._frame_editor_control=%r\n_result=True" % label)
                    check.run(SWITCH % enabled)
                    loaded = check.run(LOAD)
                    if document is None:
                        document = loaded['document']
                    assert loaded['document'] == document, 'Control changed frame content'
                    state = check.editor_preview(label, loaded['metadata'], loaded['editor_id'], loaded['document_id'])
                    evidence['controls'][label] = {'loaded': loaded, 'ready': state,
                                                  'submission': frame_submission(state),
                        'palette_control': check.run('_result=json.dumps([row for row in sys._frame_editor_transforms '
                                                     "if row['nonce']==sys._blueprint_qa_nonce])")}
                    write_json(args.output, evidence)
                    time.sleep(.3)
                    shot = check.capture('frame_editor_' + label)
                    evidence['controls'][label]['capture'] = shot
                    write_json(args.output, evidence)
                shown, body, repeat = (evidence['controls'][key] for key in ('combined', 'body', 'combined_repeat'))
                crop = viewport_crop(check, repeat['capture'])
                evidence['crop'] = crop
                for key in ('combined', 'combined_repeat'):
                    unused, mask = content_mask(evidence['controls'][key]['capture']['path'], body['capture']['path'], crop)
                    evidence['controls'][key]['item_pixels'] = count(mask)
                for key in ('item_only', 'positive'):
                    unused, mask = content_mask(evidence['controls'][key]['capture']['path'],
                                               evidence['controls']['blank']['capture']['path'], crop)
                    evidence['controls'][key]['geometry_pixels'] = count(mask)
                evidence['positive_control_visible'] = evidence['controls']['positive']['geometry_pixels'] >= 80
                evidence['item_only_visible'] = evidence['controls']['item_only']['geometry_pixels'] >= 80
                evidence['document_nonmutation'] = check.run('_result=json.dumps(s.editor.document.to_data())') == document
                evidence['completed'] = True
                evidence['passed'] = (body['submission']['item_cells'] == 0 and
                    all(evidence['controls'][key]['submission']['item_cells'] == 1 and
                        evidence['controls'][key]['item_pixels'] >= 80 for key in ('combined', 'combined_repeat')) and
                    evidence['document_nonmutation'])
            finally:
                errors = []
                was_open = None
                if installed:
                    try:
                        was_open = check.run('_result=sys._blueprint_qa_saved["workspace"]')
                    except Exception as error:
                        errors.append('read workspace baseline: ' + str(error))
                for label, code in ((('profiles', RESTORE_PROFILES),) if saved else ()) + \
                                   ((('workspace', RESTORE),) if installed else ()):
                    try:
                        check.run(code)
                    except Exception as error:
                        errors.append(label + ': ' + str(error))
                if installed and not errors:
                    try:
                        if was_open:
                            check.run('owner.open_workspace()\n_result=True')
                            check.wait('workspace restored', lambda nav: nav['open'] and not nav['transition'], check.navigation)
                        elif check.navigation()['open']:
                            check.run('navigator.pop()\n_result=True')
                            check.wait('workspace closed', lambda nav: not nav['open'] and not nav['transition'], check.navigation)
                    except Exception as error:
                        errors.append('close workspace: ' + str(error))
                evidence['cleanup_errors'] = errors
                evidence['restored'] = installed and saved and not errors
                evidence['passed'] = evidence['passed'] and evidence['restored']
    except Exception as error:
        evidence['error'] = '%s: %s' % (type(error).__name__, error)
        raise
    finally:
        write_json(args.output, evidence)
    print(json.dumps({'completed': evidence['completed'], 'passed': evidence['passed'],
                      'restored': evidence['restored']}))
    return 0 if evidence['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
