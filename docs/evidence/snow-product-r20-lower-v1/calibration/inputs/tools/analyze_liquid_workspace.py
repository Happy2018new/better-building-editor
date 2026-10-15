"""Replay frozen Workspace controls without accepting production liquid gates."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


def foreground_policy_failures(row):
    """Authorize only explicit schema-3 receipts; preserve legacy background gates."""
    problems = []
    if type(row.get('schema')) is not int or row['schema'] != 3:
        return ['foreground_policy/schema']
    if row.get('foreground_policy') != 'allow_user_foreground':
        problems.append('foreground_policy')
    for key, expected in (('window_coordinate_units', 'physical_pixels'), ('dpi_awareness', 'per_monitor_v2')):
        if row.get(key) != expected:
            problems.append(key)
    for key, expected in (('user_foreground_allowed', True), ('agent_activation_allowed', False),
                          ('activation_fallback', False), ('noactivation_requested', True),
                          ('guarded_no_activation', True), ('background_only', False)):
        if row.get(key) is not expected:
            problems.append(key)
    window = row.get('window')
    game_pid = row.get('game_pid')
    if (not isinstance(window, dict) or type(window.get('hwnd')) is not int or window['hwnd'] <= 0
            or type(game_pid) is not int or game_pid <= 0 or type(window.get('pid')) is not int
            or window['pid'] != game_pid
            or window.get('minimized') is not False
            or type(window.get('width')) is not int or window['width'] <= 1
            or type(window.get('height')) is not int or window['height'] <= 1
            or row.get('width') != window['width'] or row.get('height') != window['height']):
        return problems + ['window']
    for phase in ('before', 'after'):
        guard = row.get('guard_' + phase)
        snapshot = row.get('foreground_' + phase)
        if not isinstance(guard, dict) or not isinstance(snapshot, dict):
            problems.append('guard_' + phase)
            continue
        guard_foreground = guard.get('foreground')
        if (type(snapshot.get('pid')) is not int or snapshot['pid'] < 0
                or type(snapshot.get('hwnd')) is not int or snapshot['hwnd'] < 0
                or bool(snapshot['hwnd']) != bool(snapshot['pid'])
                or not isinstance(guard_foreground, dict)
                or any(type(guard_foreground.get(key)) is not int
                       or guard_foreground[key] != snapshot[key] for key in ('hwnd', 'pid'))):
            problems.append('foreground_' + phase)
        if guard.get('background_safe') is not (snapshot.get('pid') != game_pid):
            problems.append('guard_' + phase + '/background_safe')
        windows = guard.get('windows')
        if (guard.get('window_noactivate') is not True or not isinstance(windows, list) or not windows
                or any(not isinstance(item, dict) or type(item.get('hwnd')) is not int
                       or item['hwnd'] <= 0 or type(item.get('pid')) is not int or item['pid'] != game_pid
                       or item.get('noactivate') is not True or item.get('minimized') is not False
                       or type(item.get('width')) is not int or item['width'] <= 1
                       or type(item.get('height')) is not int or item['height'] <= 1 for item in windows)
                or not any(isinstance(item, dict) and item.get('hwnd') == window['hwnd'] for item in windows)):
            problems.append('guard_' + phase + '/windows')
        elif any(item['width'] != window['width'] or item['height'] != window['height']
                 for item in windows if item['hwnd'] == window['hwnd']):
            problems.append('guard_' + phase + '/dimensions')
        elif snapshot.get('pid') == game_pid and not any(item['hwnd'] == snapshot.get('hwnd') for item in windows):
            problems.append('foreground_' + phase + '/window')
    after = row.get('guard_after')
    if (not isinstance(after, dict) or type(row.get('background_safe')) is not bool
            or row['background_safe'] is not after.get('background_safe')):
        problems.append('background_safe')
    if row.get('foreground_unchanged') is not (row.get('foreground_before') == row.get('foreground_after')):
        problems.append('foreground_unchanged')
    return problems


def capture_failures(captures, binding):
    failures = []
    if not captures:
        return ['No captures']
    for label, row in captures.items():
        problems = []
        for key in ('ok', 'reliable', 'native_resolution'):
            if row.get(key) is not True:
                problems.append(key)
        if row.get('schema') == 3:
            problems.extend(foreground_policy_failures(row))
        else:
            for key in ('background_only', 'background_safe'):
                if row.get(key) is not True:
                    problems.append(key)
            if any(key in row for key in ('foreground_policy', 'user_foreground_allowed',
                                         'guarded_no_activation', 'agent_activation_allowed')):
                problems.append('foreground_policy/schema')
            if 'schema' in row and (type(row['schema']) is not int or row['schema'] not in (1, 2)):
                problems.append('schema')
        for key in ('owner', 'game_pid', 'game_identity', 'session_file'):
            if row.get(key) != binding.get(key):
                problems.append('binding/'+key)
        frame = row.get('frame', {})
        if row.get('backend') != 'Windows.Graphics.Capture' or frame.get('backend') != row.get('backend'):
            problems.append('backend')
        if frame.get('frame_qpc_100ns', -1) < frame.get('request_qpc_100ns', 0):
            problems.append('freshness')
        if not row.get('variance') or max(row['variance']) <= 1.:
            problems.append('blank')
        path = Path(row['path'])
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != row.get('sha256'):
            problems.append('sha256')
        else:
            with Image.open(path) as image:
                if image.format != 'PNG' or image.size != (row.get('width'), row.get('height')):
                    problems.append('encoding/size')
        if problems:
            failures.append({'capture':label, 'failures':problems})
    return failures


def rgb(path):
    with Image.open(path) as image:
        return np.asarray(image.convert('RGB'), dtype=np.int16)


def select_roi(shape, roi, crosshair=False):
    height, width = shape[:2]
    selected = np.zeros((height, width), dtype=bool)
    x0,y0,x1,y1 = roi
    selected[y0:y1,x0:x1] = True
    if crosshair:
        selected[height//2-20:height//2+20,width//2-20:width//2+20] = False
    return selected


def difference_mask(image, background, selected, threshold=12):
    return (np.max(np.abs(image-background), axis=2) > threshold) & selected


def mask_row(mask):
    ys, xs = np.nonzero(mask)
    return {'pixels':int(mask.sum()),
            'bounds':[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)] if len(xs) else None}


def compare_masks(first, second):
    union = int(np.count_nonzero(first|second))
    intersection = int(np.count_nonzero(first&second))
    a, b = mask_row(first), mask_row(second)
    edges = max(abs(x-y) for x,y in zip(a['bounds'],b['bounds'])) if a['bounds'] and b['bounds'] else None
    return {'first':a, 'second':b, 'iou':intersection/float(union) if union else None,
            'max_edge_error':edges}


def changed_pixels(first, second, mask):
    values = np.max(np.abs(first-second),axis=2)[mask]
    return {'pixels':int(values.size), 'pixels_gt2':int(np.count_nonzero(values>2)),
            'maximum_delta':int(values.max()) if values.size else None}


def opacity_row(low, high):
    def alphas(row):
        return [group['group'][3][3][3] for group in row['liquid_groups']]
    low_ids = [group['id'] for group in low['liquid_groups']]
    high_ids = [group['id'] for group in high['liquid_groups']]
    return {'body_low':low['body_uniforms']['4'][3], 'body_high':high['body_uniforms']['4'][3],
            'liquid_low':alphas(low), 'liquid_high':alphas(high), 'ids_low':low_ids, 'ids_high':high_ids,
            'body_updated':low['body_uniforms']['4'][3]==.4 and high['body_uniforms']['4'][3]==.8,
            'liquid_updated':bool(low_ids and high_ids) and all(value==.4 for value in alphas(low))
                             and all(value==.8 for value in alphas(high)),
            'ids_retained':low_ids==high_ids}


def transparency_control(positive, no_water, liquid_only, empty, rois):
    evidence = {}
    for name in ('submerged_body', 'behind_block'):
        selected = select_roi(positive.shape, rois[name])
        body = difference_mask(no_water, empty, selected)
        water = difference_mask(liquid_only, empty, selected)
        eligible = body & water
        contribution = difference_mask(positive, liquid_only, eligible)
        status = ('NOT_TESTED' if not eligible.any() else
                  'OBSERVED' if contribution.any() else 'FAIL')
        evidence[name] = {'roi':rois[name], 'eligible_pixels':int(eligible.sum()),
                          'body_contribution_pixels':int(contribution.sum()), 'status':status}
    statuses = [row['status'] for row in evidence.values()]
    return {'status':'FAIL' if 'FAIL' in statuses else
                    'NOT_TESTED' if 'NOT_TESTED' in statuses else 'OBSERVED',
            'controls':evidence, 'native_alpha_accepted':False,
            'scope':'Independent declared submerged/behind ROIs require body contribution against liquid-only controls; detecting contribution does not accept native alpha or sorting'}


def analyze(path, scene_roi=None, scene_body_exclusions=()):
    source = json.loads(path.read_bytes())
    captures = source['captures']
    failures = capture_failures(captures, source['session_binding'])
    images = {label:rgb(row['path']) for label,row in captures.items()}
    width, height = next(iter(captures.values()))['width'], next(iter(captures.values()))['height']
    scene_roi = scene_roi or (round(width*.237),round(height*.322),round(width*.773),round(height*.761))
    selected_scene = select_roi((height,width),scene_roi)
    selected_body = selected_scene.copy()
    for exclusion in scene_body_exclusions:
        selected_body &= ~select_roi((height,width),exclusion)
    output = {'schema':1, 'source':str(path.resolve()), 'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
              'analyzer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'completed':source['completed'], 'restored':source['restored'], 'cleanup_errors':source['cleanup_errors'],
              'capture_count':len(captures), 'capture_failures':failures, 'captures_verified':not failures,
              'foreground_unchanged_count':sum(row.get('foreground_unchanged') is True for row in captures.values()),
              'thresholds':{'rgb_delta':12, 'temporal_delta':2, 'crosshair_half_extent':20},
              'scene_roi':scene_roi, 'scene_body_exclusions':scene_body_exclusions,
              'scene_body_scope':'Body measurements exclude explicit UI regions and may omit coincident model samples; water measurements retain the complete Scene ROI',
              'cases':{}, 'measurements':source['measurements'],
              'opacity_patch_commit':source.get('opacity_patch',{}).get('commit'),
              'native_shape_accepted':False, 'native_uv_accepted':False, 'native_alpha_accepted':False,
              'production_editor_accepted':False, 'production_world_accepted':False, 'production_memory_accepted':False,
              'native_transparency_controls':{'status':'NOT_TESTED', 'native_alpha_accepted':False,
                  'reason':'Workspace fixture has no declared independent submerged-body and behind-block ROIs with all four aligned controls'},
              'scope':'Public-owner and pixel observations for supplied cases; reference biome/animation differ, native gates remain disabled'}
    for identity, scene_rows in source['scene'].items():
        row = output['cases'][identity] = {'scene_biomes':{}, 'world_biomes':{}, 'native_reference_gates':{},
                                          'native_silhouette':{}, 'scene_view_controls':{}}
        for biome, state in scene_rows['biomes'].items():
            ready = state['ready']
            row['scene_biomes'][biome] = {'document_biome':ready['biome'],
                                         'liquid_uniform4':[group['uniforms'][3] for group in ready['liquid_groups']]}
        if identity in source['world']:
            # Fixed camera envelopes include the fixture, excluding the separate
            # player platform and changing creatures in the surrounding world.
            fractions = (.4425,.4615,.5645,.619) if identity == 'pool' else (.469,.462,.53,.558)
            world_roi = tuple(round(value*(width if axis%2 == 0 else height)) for axis,value in enumerate(fractions))
            selected_world = select_roi((height,width),world_roi,True)
            row['world_roi'] = world_roi
            world = source['world'][identity]
            row['opacity'] = opacity_row(world['opacity']['0.4'],world['opacity']['0.8'])
            row['missing'] = {'empty_groups':len(world['missing_empty_world']['ready']['liquid_groups']),
                              'occupied_groups':len(world['missing_occupied']['ready']['liquid_groups']),
                              'restored_groups':len(world['missing_restored']['ready']['liquid_groups']),
                              'occupied_keep':world['missing_occupied']['ready']['occupancy']['rendered_keep'],
                              'restored_keep':world['missing_restored']['ready']['occupancy']['rendered_keep']}
            for biome,state in world['biomes'].items():
                row['world_biomes'][biome] = {'document_biome':state['biome'],
                                             'liquid_uniform4':[group['group'][3][3] for group in state['liquid_groups']]}
            for control in ('supported_positive','supported_negative','liquid_only','empty'):
                gates = source['native'][identity][control]['gates']
                row['native_reference_gates'][control] = all(gate['unchanged'] and gate['before_matches']
                                                               and gate['after_matches'] for gate in gates.values())
            native_mask = difference_mask(images['native_'+identity+'_liquid_only'], images['native_'+identity+'_empty'], selected_world)
            candidate_mask = difference_mask(images['world_'+identity+'_full_liquid_only'], images['world_'+identity+'_full_empty'], selected_world)
            row['native_silhouette'] = compare_masks(native_mask,candidate_mask)
            row['native_silhouette']['scope'] = 'Independent liquid-only masks exclude support and the player platform; differential alpha may affect threshold edges'
            water_interior = Image.fromarray((candidate_mask*255).astype(np.uint8)).filter(ImageFilter.MinFilter(3))
            interior = np.asarray(water_interior)>0
            row['opacity']['pixels'] = changed_pixels(images['world_'+identity+'_opacity_0_4'],images['world_'+identity+'_opacity_0_8'],interior)
            row['missing']['pixels'] = changed_pixels(images['world_'+identity+'_missing_occupied'], images['world_'+identity+'_missing_restored'],interior)
        for phase, controls in scene_rows.get('view_controls',{}).items():
            positive = images['scene_'+identity+'_'+phase+'_supported_positive']
            negative = images['scene_'+identity+'_'+phase+'_supported_negative']
            empty = images['scene_'+identity+'_'+phase+'_empty']
            water = difference_mask(positive,negative,selected_scene)
            body_raw = difference_mask(negative,empty,selected_scene)
            body = difference_mask(negative,empty,selected_body)
            row['scene_view_controls'][phase] = {'water':mask_row(water), 'body':mask_row(body),
                'body_raw':mask_row(body_raw), 'body_excluded_pixels':int(np.count_nonzero(body_raw & ~selected_body)),
                'camera_depth':controls['supported_positive']['ready']['camera_depth'],
                'camera_pan':controls['supported_positive']['ready']['camera_pan'],
                'depth_plane':controls['supported_positive']['ready']['depth_plane'],
                'liquid_control_requests':controls['supported_positive']['ready'].get('liquid_control_requests')}
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--scene-roi',type=int,nargs=4,metavar=('X0','Y0','X1','Y1'))
    parser.add_argument('--scene-body-exclude',type=int,nargs=4,action='append',default=[],
                        metavar=('X0','Y0','X1','Y1'),help='Explicit UI annotation bounds excluded only from body measurements')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh analysis output')
    report = analyze(args.input,args.scene_roi,args.scene_body_exclude)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='ascii')
    print(json.dumps({'completed':report['completed'],'restored':report['restored'],
                      'captures_verified':report['captures_verified'],'capture_count':report['capture_count']}))
    return 0 if report['completed'] and report['restored'] and report['captures_verified'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
