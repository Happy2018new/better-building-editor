"""Verify real editor snow commands with native pixels and an in-memory library."""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]

MEMORY_LIBRARY = '''import copy
assert not hasattr(sys,'_snow_lifecycle_saved')
sys._snow_lifecycle_saved={'bridge':s.bridge,'library':s.library,'serial':s.library_serial}
class SnowLifecycleLibrary(object):
 def __init__(self,target):self.target=target;self.data=None;self.preferences=None
 def __getattr__(self,name):return getattr(self.target,name)
 def save_library(self,data):self.data=copy.deepcopy(data);return True
 def load_library(self):return copy.deepcopy(self.data)
 def save_preferences(self,data):self.preferences=copy.deepcopy(data);return True
s.bridge=SnowLifecycleLibrary(s.bridge)
s.library=[]
s.library_serial=0
_result=True
'''

RESTORE_LIBRARY = '''saved=sys._snow_lifecycle_saved
s.bridge=saved['bridge']
s.library=saved['library']
s.library_serial=saved['serial']
del sys._snow_lifecycle_saved
_result=True
'''

BIND_SOURCE = '''from modern_projection.projection.cell import encode
doc=s.editor.document
metadata={'name':doc.name,'size':doc.size,'blocks':len(doc.blocks)}
sys._blueprint_qa_expected={'metadata':metadata,'previous_document_id':None,
 'editor_id':id(s.editor),'document_id':id(doc)}
_result=json.dumps({'metadata':metadata,'editor_id':id(s.editor),'document_id':id(doc),
 'cells':[(pos,encode(value)) for pos,value in sorted(doc.blocks.items())],
 'edit_layer':s.editor.edit_layer,'history':len(s.editor.undo_stack),'future':len(s.editor.redo_stack)})
'''

STEPS = (
    ('strict_front_erase', 'plant', "s.set_editor('edit_layer',0)\ns.choose_mode('erase')\nassert s.point_action(focus)==1"),
    ('strict_front_undo', 'covered', 'assert s.action(s.editor.undo)'),
    ('strict_front_redo', 'plant', 'assert s.action(s.editor.redo)'),
    ('strict_front_restore', 'covered', 'assert s.action(s.editor.undo)'),
    ('strict_back_erase', 'snow', "s.set_editor('edit_layer',1)\ns.choose_mode('erase')\nassert s.point_action(focus)==1"),
    ('strict_back_undo', 'covered', 'assert s.action(s.editor.undo)'),
    ('auto_remove_snow', 'plant', "s.set_editor('edit_layer',2)\ns.choose_mode('erase')\nassert s.point_action(focus)==1"),
    ('auto_add_snow', 'covered', "s.editor.material=snow_material\ns.choose_mode('place')\nassert s.placement_target(focus,(0,1,0))==(focus,None)\nassert s.point_action(focus,(0,1,0))==1"),
    ('saved_library_load', 'covered', "sys._snow_lifecycle_saved['camera']=(s.camera_pose,s.camera_pivot,s.camera_pan)\ns.action(s.save)\nassert len(s.library)==1 and s.bridge.data is not None\ns._loaded(Document(s.editor.document.size))\ns.load(s.library[0]['id'])"),
)


def snow_control_checks(crop, camera_state, focus, height, observed):
    from PIL import Image, ImageChops, ImageDraw, ImageFilter
    from verify_snow_plant_visibility import OrbitCamera, convex_hull, count, editor_snow_geometry
    from verify_centered_snow_profiles import shape_metrics

    hull, unused = editor_snow_geometry(crop, camera_state, focus, height)
    width, pixels_high = hull.size
    camera = OrbitCamera(*camera_state['pose'])
    camera.pivot = tuple(camera_state['pivot']) if camera_state['pivot'] is not None else None
    camera.pan = tuple(camera_state['pan'])
    size = tuple(camera_state['size'])
    unit = min(width, pixels_high) * camera.zoom * .72 / max(size)
    project = camera.projector(size, width, pixels_high, unit)
    top = Image.new('L', hull.size)
    ImageDraw.Draw(top).polygon(convex_hull(project((focus[0] + x, focus[1] + (height + 1) / 8., focus[2] + z))
        for x in (0., 1.) for z in (0., 1.)), fill=255)
    # White top texels can match the editor background. Opaque side faces remain observable.
    sides = ImageChops.subtract(hull, top)
    expected_count = count(sides)
    side_recall = count(ImageChops.multiply(sides, observed.filter(ImageFilter.MaxFilter(7)))) / max(1, expected_count)
    full = shape_metrics(hull, observed)
    return {'passed': expected_count >= 80 and full['observed_pixels'] >= 80
            and full['precision'] >= .98 and side_recall >= .90,
            'expected_visible_side_pixels': expected_count, 'side_recall': side_recall,
            'full_hull_diagnostic': full, 'minimum_side_recall': .90,
            'minimum_hull_precision': .98, 'full_hull_recall_required': False,
            'method': 'Independent affine snow sides and complete hull; white top contrast is not guaranteed'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('output', type=Path)
    parser.add_argument('--plant', default='blue_orchid')
    parser.add_argument('--height', type=int, choices=range(8), default=0)
    parser.add_argument('--timeout', type=float, default=45.)
    parser.add_argument('--max-handles', type=int, default=215000)
    parser.add_argument('--minimum-commit-gib', type=float, default=6.)
    args = parser.parse_args()
    sys.path.insert(0, str(args.project.resolve(strict=True) / 'tools'))
    sys.path.insert(0, str(args.project.resolve() / '.agents/skills/pyreact-debugging/scripts'))
    from _session import load_session
    from verify_debug_blueprints import Client, INSTALL_PROBE, RESTORE, write_json
    from verify_sign_visuals import SignCheck
    from verify_centered_snow_profiles import shape_metrics, save_mask
    from verify_snow_plant_visibility import (LOAD, capture_frame, cross_assets,
        editor_cross_above_snow, editor_snow_geometry, compare_controls)
    from verify_shulker_orientations import viewport_crop
    from verify_neighbor_world_visuals import CAPTURE_OPTIONS, RESTORE_OPTIONS
    from native_draw_response import (INSTALL, REMOVE, capture_response, frame_count, ui_preflight)
    from check_native_dialogs import assertion_dialogs
    from probe_liquid_workspace import transport
    from census_intrinsic_glint_ui_r21 import commit_at_boundary

    session = load_session(live=True)
    assert Path(session['project']).resolve() == args.project.resolve()
    assets = cross_assets(session, args.plant)
    if assets is None:
        raise ValueError('Snow lifecycle plant has no declared centered source')
    model, texture, asset_record = assets
    report = {'schema': 1, 'completed': False, 'passed': False, 'controls': {}, 'steps': [],
              'owner': session['owner'], 'game_pid': session['game_pid'],
              'game_identity': session['game_identity'], 'plant': args.plant, 'height': args.height,
              'persistent_library_writes': False, 'qualification_changed': False,
              'assets': asset_record, 'declared_editor_pan': [0., -.12],
              'minimum_available_commit_gib': args.minimum_commit_gib, 'resource_checks': []}
    started = time.monotonic()

    class GuardedCheck(SignCheck):
        def resource_gate(self, phase):
            sample = dict(commit_at_boundary(), phase=phase)
            report['resource_checks'].append(sample)
            if sample['commit_available_bytes'] < args.minimum_commit_gib * 1024 ** 3:
                write_json(args.output, report)
                raise RuntimeError('Snow lifecycle available system commit gate reached; restore')

        def run(self, code):
            if not getattr(self, 'resource_restore_mode', False):
                self.resource_gate('before_native_call')
            return super().run(code)

        def capture(self, label, tree=None):
            self.resource_gate('before_capture:' + label)
            if time.monotonic() - started > 900.:
                raise RuntimeError('Snow lifecycle time budget reached; restore')
            dialogs = [row for row in assertion_dialogs() if row['pid'] == session['game_pid']]
            if dialogs:
                raise RuntimeError('Owned native assertion blocks snow lifecycle: ' + repr(dialogs))
            metrics = transport.metrics(session['session_file'], session['owner'])
            if metrics['handles'] >= args.max_handles:
                raise RuntimeError('Snow lifecycle native handle budget reached; restore')
            return super().capture(label, tree)

    with Client(timeout=30) as client:
        check = GuardedCheck(client, args.output, args.timeout, native_resolution=True, background_only=True)
        installed = library_saved = options_saved = frames_installed = False
        original_open = None
        try:
            check.run(INSTALL_PROBE)
            installed = True
            original_open = check.run('_result=sys._blueprint_qa_saved["workspace"]')
            check.run(MEMORY_LIBRARY)
            library_saved = True
            report['capture_options'] = check.run(CAPTURE_OPTIONS)
            options_saved = True
            check.run(INSTALL)
            frames_installed = True
            check.require_native_response = True
            check.run('owner.open_workspace()\n_result=True')
            check.wait('open snow lifecycle editor', lambda nav: nav['open'] and not nav['transition'], check.navigation)
            blank = crop = None
            masks, controls = {}, {}
            for kind in ('blank', 'plant', 'snow', 'covered'):
                before = frame_count(check)
                source = check.run((LOAD % (args.plant, args.height, kind)) +
                                   '\ns.camera_pan=(0.,-.12)\ns.emit()')
                state = check.editor_preview(kind + ' control', source['metadata'], source['editor_id'], source['document_id'])
                camera = check.run('_result=json.dumps({"pose":s.camera_pose,"pan":s.camera_pan,'
                                   '"pivot":s.camera_pivot,"size":s.scene_size})')
                expected = None
                if kind == 'plant':
                    expected = editor_cross_above_snow(crop, camera, source['focus'], -1, model, texture)
                elif kind == 'snow':
                    expected = editor_snow_geometry(crop, camera, source['focus'], args.height)[0]
                if kind == 'blank':
                    picture = check.capture('control_blank')
                    crop = viewport_crop(check, picture)
                    report['editor_crop'] = crop
                    blank = picture
                    report['native_draw_preflight'] = ui_preflight(check)
                    response = None
                    comparison = {'passed': True, 'expected_empty': True}
                else:
                    def validate_control(record):
                        frame = capture_frame(record['path'], crop, blank['path'])
                        if kind == 'covered':
                            return compare_controls(controls['plant'], controls['snow'], frame, args.height)
                        if kind == 'snow':
                            return snow_control_checks(crop, camera, source['focus'], args.height, frame['object'])
                        return shape_metrics(expected, frame['object'])

                    picture, response = capture_response(check, 'control_' + kind, blank, crop, before,
                                                          validate=validate_control)
                    frame = capture_frame(picture['path'], crop, blank['path'])
                    masks[kind] = frame['object']
                    if kind == 'plant':
                        frame['above_snow'] = {args.height: editor_cross_above_snow(
                            crop, camera, source['focus'], args.height, model, texture)}
                    elif kind == 'snow':
                        frame['geometry'] = expected
                    controls[kind] = frame
                    comparison = validate_control(picture)
                report['controls'][kind] = {'source': source, 'state': state,
                    'camera_state': camera, 'screenshot': picture, 'native_response': response,
                    'checks': comparison, 'passed': comparison['passed']}
                if expected is not None:
                    report['controls'][kind]['expected_alpha'] = save_mask(expected, args.output, 'control_' + kind)
                write_json(args.output, report)
            check.run('from modern_projection.projection.model import Document\n'
                      'from modern_projection.projection.cell import foreground\n'
                      'focus=tuple(%r)\nsnow_material=foreground(s.editor.document.get(focus))\n'
                      's.editor.select_box(focus,focus)\n_result=True' % (source['focus'],))
            for label, expected, code in STEPS:
                report['active_step'] = {'label': label, 'expected_control': expected,
                                         'phase': 'before_frame_count', 'command': code}
                write_json(args.output, report)
                before = frame_count(check)
                report['active_step'].update(phase='before_mutation', render_frames_before=before)
                write_json(args.output, report)
                check.run('sys._blueprint_qa_nonce+=1\n' + code + '\n_result=True')
                report['active_step']['phase'] = 'mutation_completed'
                write_json(args.output, report)
                if label == 'saved_library_load':
                    check.wait('complete snow lifecycle library load', bool,
                               lambda: check.run('_result=s.io_job is None'))
                    check.run("pose,pivot,pan=sys._snow_lifecycle_saved['camera']\n"
                              's.camera_pivot=pivot\ns.camera_pan=pan\ns.camera_view(*pose)\n_result=True')
                    check.wait('restore snow library camera',
                        lambda value: all(abs(a - b) < .01 for a, b in zip(value['expected'], value['actual'])),
                        lambda: check.run("_result=json.dumps({'expected':sys._snow_lifecycle_saved['camera'][0],"
                                          "'actual':s.camera_pose})"))
                result = check.run(BIND_SOURCE)
                state = check.editor_preview(label, result['metadata'], result['editor_id'], result['document_id'])

                def validate(record):
                    frame = capture_frame(record['path'], crop, blank['path'])
                    return shape_metrics(masks[expected], frame['object'])

                picture, response = capture_response(check, label, blank, crop, before, validate=validate)
                frame = capture_frame(picture['path'], crop, blank['path'])
                comparison = shape_metrics(masks[expected], frame['object'])
                report['steps'].append({'label': label, 'expected_control': expected, 'source': result,
                    'state': state, 'screenshot': picture, 'native_response': response,
                    'mask': save_mask(frame['object'], args.output, label), 'checks': comparison,
                    'passed': comparison['passed']})
                report['active_step'] = None
                write_json(args.output, report)
            report['completed'] = True
        finally:
            check.resource_restore_mode = True
            prior = sys.exc_info()
            if prior[0] is not None:
                report['error'] = prior[0].__name__ + ': ' + str(prior[1])
            actions = []
            if frames_installed:
                actions.append(('render_observer', lambda: check.run(REMOVE)))
            if options_saved:
                actions.append(('capture_options', lambda: check.run(RESTORE_OPTIONS)))
            if library_saved:
                actions.append(('library_bridge', lambda: check.run(RESTORE_LIBRARY)))
            if installed:
                actions.append(('workspace', lambda: check.run(RESTORE)))
            errors = []
            for name, callback in actions:
                try:
                    callback()
                except Exception as error:
                    errors.append(name + ': ' + str(error))
            if installed and not errors:
                try:
                    if original_open:
                        check.run('owner.open_workspace()\n_result=True')
                    elif check.navigation()['open']:
                        check.run('navigator.pop()\n_result=True')
                    check.wait('restore snow lifecycle navigation',
                        lambda nav: nav['open'] == original_open and not nav['transition'], check.navigation)
                except Exception as error:
                    errors.append('navigation: ' + str(error))
            report.update(cleanup_errors=errors, restored=not errors,
                          elapsed_seconds=time.monotonic() - started)
            report['passed'] = (report['completed'] and report['restored']
                and all(row['passed'] for row in report['controls'].values())
                and all(row['passed'] for row in report['steps']))
            write_json(args.output, report)
    print(json.dumps({key: report[key] for key in ('completed', 'passed', 'restored', 'elapsed_seconds')}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
