"""Compare native snow and plant visibility at one fixed editor/world position."""
import argparse
import base64
import json
import time
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter
from verify_debug_blueprints import (BlueprintCheck, Client, INSTALL_PROBE, RESTORE,
                                     write_json)
from verify_debug_visuals import SAVE_VISUAL, PROJECTION_STATUS, camera_restore_code
from verify_missing_neighbor_visuals import camera_matches
from verify_shulker_orientations import viewport_crop

ROOT = Path(__file__).resolve().parents[1]
PROJECTION_SOURCE = '''import zlib
from modern_projection.projection.bridge import _stable_palette
from modern_projection.projection.geometry_palette import prepare_palette
work=b.projection_work
doc=s.editor.document
data=prepare_palette(doc.palette_data())
fingerprint=zlib.compress(repr(_stable_palette((doc.size,data))).encode('utf8'),1)
model=b.projection_mesh[1] if b.projection_mesh else None
_result=json.dumps({'editor_id':id(s.editor),'document_id':id(doc),'fixture':sys._blueprint_qa_identity,
 'nonce':sys._blueprint_qa_nonce,'serial':b.projection_serial,
 'work_current':work is not None and work.serial==b.projection_serial and work.ready and
  work.model==model and work.document.size==doc.size and work.document.blocks==doc.blocks,
 'cache_model':b.models.get(fingerprint),'model':model,
 'cache_current':model is not None and b.models.get(fingerprint)==model,
 'origin_current':work is not None and tuple(work.origin)==tuple(s.origin),
 'fingerprint_bytes':len(fingerprint)})
'''


def projection_source_matches(actual, expected):
    fields = ('editor_id', 'document_id', 'fixture', 'nonce', 'serial', 'model')
    return (all(actual.get(field) == expected.get(field) for field in fields) and
            actual.get('work_current') and actual.get('cache_current') and actual.get('origin_current'))


LOAD = '''from modern_projection.projection.model import Document
from modern_projection.projection.cell import _covered_snow,foreground,background,rebase
from modern_projection.projection.debug_blueprints import build,VISUAL_CASES
from modern_projection.projection import block_registry as registry
from modern_projection.projection.render_layout import SCHEMA_VERSION as render_layout_version
plant=%r
height=%d
kind=%r
case=VISUAL_CASES['snow_plant_visibility']
focus=case['focus']
row=next(row for row in case['cells'] if row['plant']==plant)
source_pos=row['standalone'] if kind in ('plant','blank') else next(pos for h,pos in row['covered'] if h==height)
source=build(case['fixture'])
value=source.get(source_pos)
if kind=='snow':value=_covered_snow(foreground(value),False)
doc=Document(case['size'],name='Snow plant visibility check')
if kind!='blank':doc.blocks[focus]=rebase(value,tuple(focus[i]-source_pos[i] for i in range(3)))
sys._blueprint_qa_identity='snow.visibility.'+plant+'.'+kind+'.'+str(height)
sys._blueprint_qa_nonce+=1
sys._blueprint_qa_expected={'metadata':{'name':doc.name,'size':doc.size,'blocks':len(doc.blocks)},
 'previous_document_id':id(s.editor.document),'editor_id':None}
s._loaded(doc)
s.camera_pivot=tuple(v+.5 for v in focus)
s.camera_view(*case['camera']['editor'])
s.emit()
_result=json.dumps({'fixture':case['fixture'],'fixture_schema':case['schema'],
 'source_position':source_pos,'focus':focus,'registry_version':registry.source_version(),
 'registry_fingerprint':registry.fingerprint(),'render_layout_version':render_layout_version,
 'runtime_minecraft_version':api.GetMinecraftVersion() if hasattr(api,'GetMinecraftVersion') else None,
 'front':foreground(doc.get(focus)),'back':background(doc.get(focus)),
 'metadata':{'name':doc.name,'size':doc.size,'blocks':len(doc.blocks)},
 'editor_id':id(s.editor),'document_id':id(doc)})
'''


def green_mask(frame):
    red, green, blue = frame.convert('RGB').split()
    first = ImageChops.subtract(green, red).point(lambda value: 255 if value > 7 else 0)
    second = ImageChops.subtract(green, blue).point(lambda value: 255 if value > 7 else 0)
    brightness = green.point(lambda value: 255 if value > 25 else 0)
    return ImageChops.multiply(ImageChops.multiply(first, second), brightness)


def maximum(frame):
    red, green, blue = frame.split()
    return ImageChops.lighter(ImageChops.lighter(red, green), blue)


def count(mask):
    return mask.histogram()[255]


def changed(first, second, threshold=20):
    return maximum(ImageChops.difference(first, second)).point(lambda value: 255 if value > threshold else 0)


def capture_frame(path, crop, hidden):
    with Image.open(path) as source:
        frame = source.convert('RGB').crop(crop)
    with Image.open(hidden) as source:
        reference = source.convert('RGB').crop(crop)
    return {'image': frame, 'object': changed(frame, reference),
            'green': ImageChops.multiply(green_mask(frame), changed(frame, reference))}


def analyze(frame, crop, output):
    frame['green'].save(output)
    presence_path = output.with_name(output.stem + '_presence.png')
    frame['object'].save(presence_path)
    return {'green_pixels': count(frame['green']), 'bounds': frame['green'].getbbox(),
            'object_pixels': count(frame['object']), 'object_bounds': frame['object'].getbbox(),
            'crop': crop, 'mask': str(output.resolve()), 'presence_mask': str(presence_path.resolve())}


def bands(mask):
    bounds = mask.getbbox()
    if bounds is None:
        return mask.copy(), mask.copy()
    left, top, right, bottom = bounds
    height = bottom - top
    upper, lower = Image.new('L', mask.size), Image.new('L', mask.size)
    ImageDraw.Draw(upper).rectangle((left, top, right - 1, top + max(1, height // 5)), fill=255)
    ImageDraw.Draw(lower).rectangle((left, bottom - max(1, height * 3 // 10), right - 1, bottom - 1), fill=255)
    return ImageChops.multiply(mask, upper), ImageChops.multiply(mask, lower)


def compare_controls(plant, snow, covered, height, minimum=80):
    if len({row['image'].size for row in (plant, snow, covered)}) != 1:
        raise AssertionError('Snow controls must have identical crop dimensions')
    plant_mask, snow_mask = plant['object'], snow['object']
    footprint = plant_mask.filter(ImageFilter.MaxFilter(5))
    difference = ImageChops.multiply(changed(covered['image'], snow['image']),
                                     ImageChops.lighter(covered['object'], snow_mask))
    contribution = ImageChops.multiply(difference, footprint)
    upper, lower = bands(plant_mask)
    # Only require foliage in an upper region that the independent opaque
    # snow control does not cover in this camera. Plant texture bounds vary.
    upper = ImageChops.subtract(upper, snow_mask.filter(ImageFilter.MaxFilter(3)))
    upper_count, lower_count = count(upper), count(lower)
    upper_retained = count(ImageChops.multiply(contribution, upper)) / max(1, upper_count)
    lower_retained = count(ImageChops.multiply(contribution, lower)) / max(1, lower_count)
    covered_lower_by_snow = count(ImageChops.multiply(snow_mask, lower)) / max(1, lower_count)
    outside = ImageChops.multiply(difference, ImageChops.invert(footprint))
    outside_ratio = count(outside) / max(1, count(difference))
    snow_outside = ImageChops.multiply(snow_mask, ImageChops.invert(footprint))
    snow_retained = 1. - count(ImageChops.multiply(outside, snow_outside)) / max(1, count(snow_outside))
    matched = ImageChops.multiply(contribution, plant_mask)
    color_changed = changed(covered['image'], plant['image'], 35)
    color_match = 1. - count(ImageChops.multiply(color_changed, matched)) / max(1, count(matched))
    observability = (count(plant_mask) >= minimum and count(snow_mask) >= minimum and
                     upper_count >= max(8, minimum // 10) and lower_count >= max(12, minimum // 4))
    if height == 5:
        observability = observability and covered_lower_by_snow >= .65
    checks = {
        'observable_controls': observability,
        'plant_contributes_beyond_snow': count(contribution) >= max(20, minimum // 4),
        'upper_foliage_retained': upper_retained >= .65,
        'foliage_stays_at_standalone_position': outside_ratio <= .15,
        'remaining_foliage_matches_standalone': color_match >= .60,
        'snow_stays_at_control_position': snow_retained >= .90,
    }
    if height == 5:
        checks['high_snow_occludes_lower_foliage'] = lower_retained <= .25
    return {'height': height, 'passed': all(checks.values()), 'valid_baseline': observability,
            'checks': checks, 'failures': [key for key, value in checks.items() if not value],
            'plant_pixels': count(plant_mask), 'snow_pixels': count(snow_mask),
            'covered_contribution_pixels': count(contribution), 'upper_pixels': upper_count,
            'lower_pixels': lower_count, 'upper_retained': upper_retained,
            'lower_retained': lower_retained, 'lower_snow_control_coverage': covered_lower_by_snow,
            'outside_standalone_ratio': outside_ratio, 'remaining_color_match': color_match,
            'snow_outside_plant_retained': snow_retained,
            'limits': {'minimum_baseline_pixels': minimum, 'upper_retention': .65,
                       'high_lower_retention': .25, 'high_lower_snow_coverage': .65,
                       'outside_standalone_ratio': .15, 'color_match': .60, 'snow_retention': .90}}


def scope_checks(frames, plants, heights, minimum=80):
    rows = []
    for plant in plants:
        per_height = [compare_controls(frames[(plant, 'plant', 0)], frames[(plant, 'snow', height)],
                                       frames[(plant, 'covered', height)], height, minimum)
                      for height in heights]
        values = dict((row['height'], row) for row in per_height)
        comparative = (0 in values and 5 in values and
                       values[0]['lower_retained'] - values[5]['lower_retained'] >= .20)
        rows.append({'plant': plant, 'heights': per_height, 'height_pair_passed': comparative,
                     'passed': all(row['passed'] for row in per_height) and comparative,
                     'height_pair_contract': 'height 5 removes at least 20% more baseline lower foliage than height 0'})
    return {'passed': bool(rows) and all(row['passed'] for row in rows), 'plants': rows,
            'required_heights_complete': set(heights) == {0, 5},
            'scope': 'Fixed-camera visible upper and occluded lower foliage, snow position and two-height difference; no world writes'}


def projection_capture(check, label, focus, offset):
    native_before = check.run('_result=len(sys._blueprint_qa_records)')
    check.run('''focus=%r
foot=b.player_origin()
s.origin=(foot[0]+6-focus[0],foot[1]+8-focus[1],foot[2]+6-focus[2])
s.opacity=1.
s.projection_missing=False
s.projection_outline=False
b.project()
_result=True
''' % (focus,))

    def ready(state):
        if state['error']:
            raise AssertionError(state)
        return (state['active'] and state['ready'] and not state['preparing'] and
                state['actors'] == 1 and state['mesh'] and state['scale'] is not None)

    state = check.wait('snow native projection', ready, lambda: check.run(PROJECTION_STATUS))
    source = check.run(PROJECTION_SOURCE)
    assert projection_source_matches(source, source), source
    check.run('navigator.pop()\n_result=True')
    check.wait('close workspace for snow projection',
               lambda nav: not nav['open'] and not nav['transition'], check.navigation)
    pose = check.run('''focus=%r
offset=%r
target=tuple(s.origin[i]+focus[i]+.5 for i in range(3))
position=tuple(target[i]+offset[i] for i in range(3))
direction=api.GetRotFromDir(tuple(target[i]-position[i] for i in range(3)))
rotation=(direction[0],direction[1]+180.,0.)
cam=b.factory.CreateCamera(b.level)
cam.DepartCamera()
cam.LockModCameraPitch(True)
cam.LockModCameraYaw(True)
assert cam.SetCameraPos(position)
assert cam.SetCameraRotation(rotation)
_result=json.dumps({'target':target,'position':position,'rotation':rotation})
''' % (focus, offset))
    camera_code = ('cam=b.factory.CreateCamera(b.level)\n_result=json.dumps({'
                   '"position":cam.GetPosition(),"rotation":cam.GetCameraRotation()})')
    check.wait('snow world camera', lambda value: camera_matches(value, pose), lambda: check.run(camera_code))
    time.sleep(.45)
    shown = check.capture(label + '_world_closeup')
    try:
        check.run('assert b.factory.CreateActorRender(b.entity).SetNotRenderAtAll(True)\n_result=True')
        time.sleep(.3)
        hidden = check.capture(label + '_world_hidden')
    finally:
        check.run('assert b.factory.CreateActorRender(b.entity).SetNotRenderAtAll(False)\n_result=True')
    final = check.run(PROJECTION_STATUS)
    actual_camera = check.run(camera_code)
    assert camera_matches(actual_camera, pose), (actual_camera, pose)
    assert state['actor'] == final['actor'] and state['mesh'][:3] == final['mesh'][:3], (state, final)
    saved_player = check.run('_result=json.dumps(sys._blueprint_visual_saved["player"])')
    assert saved_player == final['player'], (saved_player, final['player'])
    calls = check.run('_result=json.dumps(sys._blueprint_qa_records[%d:])' % native_before)
    current_source = check.run(PROJECTION_SOURCE)
    assert projection_source_matches(current_source, source), (source, current_source)
    assert all(row.get('result') and not row.get('error') and
               row.get('editor_id') == source['editor_id'] and
               row.get('document_id') == source['document_id'] and row.get('nonce') == source['nonce']
               for row in calls), calls
    state.update(pose=pose, final=final, camera=actual_camera, screenshot=shown,
                 hidden_screenshot=hidden, native_calls=calls, source=current_source,
                 native_evidence='current_source_submission' if calls else 'current_source_cached_geometry')
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--plant', action='append', choices=('short_grass', 'fern', 'dandelion', 'poppy', 'blue_orchid', 'allium'))
    parser.add_argument('--height', type=int, action='append', choices=(0, 5))
    parser.add_argument('--timeout', type=float, default=60)
    parser.add_argument('--min-pixels', type=int, default=80)
    args = parser.parse_args()
    if args.timeout <= 0 or args.min_pixels <= 0:
        parser.error('Timeout and minimum observable pixels must be positive')
    plants = tuple(dict.fromkeys(args.plant or ('short_grass', 'fern')))
    heights = sorted(set(args.height or (0, 5)))
    frames = {'editor': {}, 'projection': {}}
    evidence = {'schema': 3, 'completed': False, 'passed': False, 'rows': [],
                'scopes': {'editor': {'passed': False}, 'projection': {'passed': False}},
                'scope': 'Independent editor and actual projection assertions with standalone, snow and combined controls at heights 0 and 5.',
                'native_reference': {'captured': False,
                                     'capability_source': 'tools/data/native_snow_overlays_nemc_3.9.0.401155.json',
                                     'plan': 'In the root-owned empty fixture, place each standalone plant, call SetSnowBlock at heights 1 and 6, verify native states 0 and 5, then capture the same side camera. Native capability data is not a visual oracle.'}}
    installed = visual_saved = False
    try:
        with Client(timeout=30) as client:
            check = BlueprintCheck(client, args.output, args.timeout)
            try:
                check.run(INSTALL_PROBE)
                installed = True
                check.run(SAVE_VISUAL)
                visual_saved = True
                check.refresh()
                blueprint_path = ROOT / 'behavior_pack/modern_projection/projection/debug_blueprints.py'
                case = check.run('import base64\nimport modern_projection.projection.debug_blueprints as refreshed\n'
                                 'eval(compile(base64.b64decode(%r),%r,"exec"),refreshed.__dict__)\n'
                                 '_result=json.dumps(refreshed.VISUAL_CASES["snow_plant_visibility"])' %
                                 (base64.b64encode(blueprint_path.read_bytes()).decode('ascii'), str(blueprint_path)))
                focus = tuple(case['focus'])
                evidence['focus'] = focus
                evidence['blueprint_case'] = case
                for plant in plants:
                    cases = [('blank', 0), ('plant', 0)] + [(kind, height)
                            for height in heights for kind in ('snow', 'covered')]
                    editor_crop = None
                    blank_editor = None
                    for kind, height in cases:
                        label = '%s_%s_h%d' % (plant, kind, height)
                        check.run('owner.open_workspace()\n_result=True')
                        check.wait('open workspace', lambda nav: nav['open'] and not nav['transition'], check.navigation)
                        source = check.run(LOAD % (plant, height, kind))
                        state = check.editor_preview('snow visibility preview', source['metadata'],
                                                     source['editor_id'], source['document_id'])
                        if kind != 'blank':
                            assert state['model_name'] and state['parts'] and state['renderer_active'], state
                        camera = check.wait('fixed editor camera',
                                            lambda pose: all(abs(pose[i] - case['camera']['editor'][i]) < .01 for i in range(3)),
                                            lambda: check.run('_result=json.dumps(s.camera_pose)'))
                        time.sleep(.3)
                        editor = check.capture(label + '_editor')
                        actual_crop = viewport_crop(check, editor)
                        if editor_crop is not None:
                            assert actual_crop == editor_crop, (editor_crop, actual_crop)
                        editor_crop = actual_crop
                        if kind == 'blank':
                            blank_editor = editor['path']
                            evidence['rows'].append({'plant': plant, 'kind': kind, 'height': height,
                                                     'source': source, 'editor': editor, 'editor_crop': editor_crop,
                                                     'editor_camera': camera})
                            write_json(args.output, evidence)
                            continue
                        editor_frame = capture_frame(editor['path'], editor_crop, blank_editor)
                        frames['editor'][(plant, kind, height)] = editor_frame
                        pixels = analyze(editor_frame, editor_crop,
                                         args.output.with_name(args.output.stem + '_' + label + '_editor_mask.png'))
                        world = projection_capture(check, label, focus, tuple(case['camera']['world_offset']))
                        width, height_pixels = world['screenshot']['size']
                        crop = (width // 4, height_pixels // 4, width * 3 // 4, height_pixels * 3 // 4)
                        projection_frame = capture_frame(world['screenshot']['path'], crop,
                                                         world['hidden_screenshot']['path'])
                        frames['projection'][(plant, kind, height)] = projection_frame
                        world_pixels = analyze(projection_frame, crop,
                                               args.output.with_name(args.output.stem + '_' + label + '_world_mask.png'))
                        stable_source = check.run('from modern_projection.projection.cell import foreground,background\n'
                                                  '_result=json.dumps({"front":foreground(s.editor.document.get(%r)),'
                                                  '"back":background(s.editor.document.get(%r)),'
                                                  '"runtime":api.GetMinecraftVersion() if hasattr(api,"GetMinecraftVersion") else None})' %
                                                  (focus, focus))
                        assert (stable_source['front'], stable_source['back'], stable_source['runtime']) == (
                            source['front'], source['back'], source['runtime_minecraft_version']), (source, stable_source)
                        evidence['rows'].append({'plant': plant, 'kind': kind, 'height': height, 'source': source,
                                                 'editor': editor, 'editor_pixels': pixels, 'editor_camera': camera,
                                                 'world': world, 'world_pixels': world_pixels})
                        write_json(args.output, evidence)
                        print(json.dumps({'label': label, 'editor': pixels['green_pixels'],
                                          'world': world_pixels['green_pixels']}), flush=True)
                        check.run('b.stop_projection()\n_result=True')
                        check.run(camera_restore_code(False))
                    completed_plants = plants[:plants.index(plant) + 1]
                    for scope, sampled in frames.items():
                        evidence['scopes'][scope] = scope_checks(sampled, completed_plants, heights, args.min_pixels)
                        for result in evidence['scopes'][scope]['plants']:
                            plant_frame = sampled[(result['plant'], 'plant', 0)]
                            for row in result['heights']:
                                snow_frame = sampled[(result['plant'], 'snow', row['height'])]
                                covered_frame = sampled[(result['plant'], 'covered', row['height'])]
                                contribution = ImageChops.multiply(changed(covered_frame['image'], snow_frame['image']),
                                                                    plant_frame['object'].filter(ImageFilter.MaxFilter(5)))
                                path = args.output.with_name(args.output.stem + '_%s_%s_h%d_contribution.png' %
                                                             (scope, result['plant'], row['height']))
                                contribution.save(path)
                                row['contribution_mask'] = str(path.resolve())
                    write_json(args.output, evidence)
                versions = [dict((key, row['source'][key]) for key in (
                    'fixture', 'fixture_schema', 'registry_version', 'registry_fingerprint',
                    'runtime_minecraft_version', 'render_layout_version')) for row in evidence['rows']]
                version_stable = bool(versions) and all(value == versions[0] for value in versions)
                version_present = bool(versions and all(versions[0].values()))
                evidence['runtime_reference'] = versions[0] if versions else None
                evidence['runtime_reference_passed'] = version_stable and version_present
                for scope in evidence['scopes'].values():
                    scope['runtime_reference_passed'] = evidence['runtime_reference_passed']
                    scope['passed'] = scope['passed'] and evidence['runtime_reference_passed']
                evidence['completed'] = True
                evidence['passed'] = all(scope['passed'] for scope in evidence['scopes'].values())
            finally:
                if visual_saved:
                    check.run('b.stop_projection()\n_result=True')
                    check.run(camera_restore_code(False))
                    check.run('saved=sys._blueprint_visual_saved\n'
                              's.origin=saved["origin"]\ns.opacity=saved["opacity"]\n'
                              's.projection_missing=saved["missing"]\ns.projection_outline=saved["outline"]\n'
                              'del sys._blueprint_visual_saved\n_result=True')
                if installed:
                    was_open = check.run('_result=sys._blueprint_qa_saved["workspace"]')
                    check.run(RESTORE)
                    if was_open:
                        check.run('owner.open_workspace()\n_result=True')
                        check.wait('restore workspace', lambda nav: nav['open'] and not nav['transition'], check.navigation)
                    elif check.navigation()['open']:
                        check.run('navigator.pop()\n_result=True')
                        check.wait('restore closed workspace', lambda nav: not nav['open'] and not nav['transition'], check.navigation)
                    evidence['restored'] = True
    except Exception as error:
        evidence['error'] = '%s: %s' % (type(error).__name__, error)
        raise
    finally:
        write_json(args.output, evidence)
    print(json.dumps({'evidence': str(args.output.resolve()), 'completed': evidence['completed'],
                      'passed': evidence['passed'],
                      'editor_passed': evidence['scopes']['editor']['passed'],
                      'projection_passed': evidence['scopes']['projection']['passed']}))
    return 0 if evidence['completed'] and evidence['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
