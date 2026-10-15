"""Retest one shader hypothesis against a restored, owner-bound frame scene."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

from flat_frame_item_visual_checks import alpha_ownership_controls, content_mask
from verify_debug_blueprints import Client, INSTALL_PROBE, RESTORE, write_json
from verify_debug_visuals import SAVE_VISUAL, camera_restore_code
from verify_entity_appearance_visuals import AppearanceCheck, require_bed_calibration
from verify_native_entity_appearances import execute
from verify_shulker_orientations import matching_camera
from verify_sign_visuals import world_sample
from verify_snow_plant_visibility import count
from visual_environment import SETUP_DAYLIGHT, RESTORE_DAYLIGHT

ROOT = Path(__file__).resolve().parents[1]
SHADER = 'modern_projection_biome_blocks.fragment'
LOAD_FRAME = '''from copy import deepcopy
from modern_projection.projection import static_frame_item_data
from modern_projection.projection.debug_blueprints import build,VISUAL_CASES
from modern_projection.projection.debug_appearance_blueprints import CASE_POSITIONS
from modern_projection.projection.model import Document
from modern_projection.projection.cell import rebase
assert not hasattr(sys,'_flat_frame_item_profiles_saved')
sys._flat_frame_item_profiles_saved=deepcopy(static_frame_item_data.FRAME_ITEMS)
assert not any(profile['accepted'] for profile in static_frame_item_data.FRAME_ITEMS.values())
for profile in static_frame_item_data.FRAME_ITEMS.values():profile['accepted']=True
case=VISUAL_CASES['entity_appearances']
doc=Document(case['isolated_size'],name='Entity appearance frame_filled')
target=CASE_POSITIONS['frame_filled']
delta=tuple(case['focus'][axis]-target[axis] for axis in range(3))
doc.blocks[tuple(case['focus'])]=rebase(build(case['fixture']).get(target),delta)
sys._blueprint_qa_identity='entity.synthetic.frame_filled'
sys._blueprint_qa_nonce+=1
sys._blueprint_qa_expected={'metadata':{'name':doc.name,'size':doc.size,'blocks':len(doc.blocks)},
 'previous_document_id':id(s.editor.document),'editor_id':None}
s._loaded(doc)
s.camera_pivot=tuple(v+.5 for v in case['focus'])
s.camera_view(*case['isolated_camera']['editor'])
s.emit()
_result=json.dumps({'case':case,'document':doc.to_data()})
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--prior-report', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh ownership report')
    helper = os.environ.get('MCDEV_NATIVE_CAPTURE_HELPER')
    if not helper or Path(helper).resolve() != ROOT / 'tools/capture_native_window.py':
        parser.error('This diagnostic requires the reviewed owner-bound WGC helper')
    prior = json.loads(args.prior_report.read_text(encoding='utf8'))
    assert prior['completed'] and prior['restored'] and prior['candidate_alpha_ownership']
    assert len(prior['rows']) == 1 and prior['rows'][0]['case'] == 'frame_filled'
    assert prior['candidate_depth_delta_blocks'] is None
    original = prior['rows'][0]['item_scopes']['full']['shown']
    calibration = json.loads(Path(prior['camera_calibration']).read_text(encoding='utf8'))
    evidence = {'schema': 1, 'completed': False, 'passed': False,
                'production_rendering_accepted': False,
                'scope': 'One same-instance shader reload; isolated geometry ownership only',
                'session_file': os.environ.get('MCDEV_SESSION_FILE'),
                'prior_report': str(args.prior_report.resolve()),
                'prior_report_sha256': hashlib.sha256(args.prior_report.read_bytes()).hexdigest(),
                'declared_shader': SHADER,
                'declared_opacities': [1., .2, 0.],
                'declared_owners': ['blank', 'body', 'item'],
                'declared_alpha0_maximum_pixels': 2,
                'source_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in (Path(__file__), ROOT / 'tools/flat_frame_item_visual_checks.py',
                                 ROOT / 'tools/verify_sign_visuals.py',
                                 ROOT / ('resource_pack/shaders/glsl/' + SHADER),
                                 ROOT / 'behavior_pack/modern_projection/projection/occupancy_shader.py')}}
    installed = saved_visual = daylight_saved = False
    try:
        with Client(timeout=30) as client:
            check = AppearanceCheck(client, args.output, 60, native_resolution=True, background_only=True)
            try:
                runtime = check.run('cam=b.factory.CreateCamera(b.level)\n'
                    '_result=json.dumps({"fov":cam.GetFov(),"screen":b.factory.CreateGame(b.level).GetScreenSize(),'
                    '"version":api.GetMinecraftVersion()})')
                require_bed_calibration(calibration, runtime)
                check.run(INSTALL_PROBE)
                installed = True
                check.run(SAVE_VISUAL)
                saved_visual = True
                evidence['shader_reload'] = check.run('_result=api.ReloadOneShader(%r)' % SHADER)
                assert evidence['shader_reload'] is True, 'The declared single shader reload failed'
                daylight_saved = True
                evidence['daylight'] = execute(client, SETUP_DAYLIGHT)
                loaded = check.run(LOAD_FRAME)
                case = loaded['case']
                assert case == prior['blueprint_case'], 'The public frame scene changed'
                evidence['document'] = loaded['document']
                shown = world_sample(check, 'terrain_reload_frame', case['focus'], prior['rows'][0]['world_offset'],
                                     1., case['projection_height'], mesh_origin=True)
                evidence['shown'] = shown
                assert tuple(shown['origin']) == tuple(original['origin']), 'The source origin changed'
                assert matching_camera(shown['pose']['settled'], original['pose']), 'The recorded camera changed'
                evidence['same_scene_registration'] = True
                width, height = shown['screenshot']['size']
                crop = (width // 3, height // 3, width * 2 // 3, height * 2 // 3)
                evidence['crop'] = crop
                evidence['alpha_ownership'] = {}
                record = lambda: write_json(args.output, evidence)
                controls = alpha_ownership_controls(check, 'terrain_reload_frame', shown, crop,
                                                    evidence['alpha_ownership'], record)
                blank = controls['captures']['blank']['0.0']['capture']['path']
                controls['blank_positive_controls'] = {}
                for opacity in (1., .2):
                    check.run('''shader=b.projection_shader
s.opacity=%r
b.update_projection_opacity()
for parts in shader.parts:
 for name in parts:assert shader.render.SetActorBlockGeometryVisible(name,False)
_result=True
''' % opacity)
                    time.sleep(.3)
                    shot = check.capture('terrain_reload_frame_owner_blank_alpha' + str(opacity).replace('.', '_'))
                    unused, mask = content_mask(shot['path'], blank, crop, 12)
                    controls['blank_positive_controls'][str(opacity)] = {'capture': shot,
                                                                        'residual_pixels_gt_12': count(mask)}
                    record()
                evidence['document_nonmutation'] = check.run('_result=json.dumps(s.editor.document.to_data())') == loaded['document']
                check.run('b.stop_projection()\n_result=True')
                owners = check.run('''_result=json.dumps({'actors':len(b.projection_entities)+int(bool(b.entity)),
 'preparing':bool(b.preparing_entity),'shader':b.projection_shader is not None,
 'occupancy':b.projection_occupancy is not None})''')
                evidence['stop_owners'] = dict(owners, passed=not any(owners.values()))
                evidence['completed'] = True
                evidence['passed'] = (controls['blank_residual_pixels_gt_12'] <= 2 and
                    all(row['residual_pixels_gt_12'] <= 2 for row in controls['blank_positive_controls'].values()) and
                    all(controls[owner]['opaque_pixels'] >= 80 and controls[owner]['alpha02']['passed'] and
                        controls[owner]['alpha0_total_residual_pixels_gt_12'] <= 2 for owner in ('body', 'item')) and
                    evidence['document_nonmutation'] and evidence['stop_owners']['passed'])
            finally:
                actions = []
                if saved_visual:
                    actions.extend((('projection', lambda: check.run('b.stop_projection()\n_result=True')),
                                    ('camera', lambda: check.run(camera_restore_code(False))),
                                    ('visual', lambda: check.run('saved=sys._blueprint_visual_saved\n'
                                      's.origin=saved["origin"]\ns.opacity=saved["opacity"]\n'
                                      's.projection_missing=saved["missing"]\ns.projection_outline=saved["outline"]\n'
                                      'del sys._blueprint_visual_saved\n_result=True'))))
                if daylight_saved:
                    actions.append(('daylight', lambda: execute(client, RESTORE_DAYLIGHT)))
                if installed:
                    actions.append(('candidate_profiles', lambda: check.run('''from modern_projection.projection import static_frame_item_data
if hasattr(sys,'_flat_frame_item_profiles_saved'):
 static_frame_item_data.FRAME_ITEMS=sys._flat_frame_item_profiles_saved
 del sys._flat_frame_item_profiles_saved
assert not any(profile['accepted'] for profile in static_frame_item_data.FRAME_ITEMS.values())
_result=True
''')))
                    def restore_workspace():
                        was_open = check.run('_result=sys._blueprint_qa_saved["workspace"]')
                        check.run(RESTORE)
                        if was_open:
                            check.run('owner.open_workspace()\n_result=True')
                            check.wait('restored workspace opened', lambda nav: nav['open'] and not nav['transition'], check.navigation)
                        elif check.navigation()['open']:
                            check.run('navigator.pop()\n_result=True')
                            check.wait('restored workspace closed', lambda nav: not nav['open'] and not nav['transition'], check.navigation)
                    actions.append(('workspace', restore_workspace))
                errors = []
                for label, action in actions:
                    try:
                        action()
                    except Exception as error:
                        errors.append(label + ': ' + str(error))
                evidence['cleanup_errors'] = errors
                evidence['restored'] = installed and not errors
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
