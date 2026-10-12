"""Replay frozen Workspace controls without accepting production liquid gates."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


def capture_failures(captures, binding):
    failures = []
    if not captures:
        return ['No captures']
    for label, row in captures.items():
        problems = []
        for key in ('ok', 'reliable', 'background_only', 'background_safe', 'native_resolution'):
            if row.get(key) is not True:
                problems.append(key)
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


def analyze(path):
    source = json.loads(path.read_bytes())
    captures = source['captures']
    failures = capture_failures(captures, source['session_binding'])
    images = {label:rgb(row['path']) for label,row in captures.items()}
    width, height = next(iter(captures.values()))['width'], next(iter(captures.values()))['height']
    scene_roi = (round(width*.237),round(height*.322),round(width*.773),round(height*.761))
    selected_scene = select_roi((height,width),scene_roi)
    output = {'schema':1, 'source':str(path.resolve()), 'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
              'analyzer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'completed':source['completed'], 'restored':source['restored'], 'cleanup_errors':source['cleanup_errors'],
              'capture_count':len(captures), 'capture_failures':failures, 'captures_verified':not failures,
              'foreground_unchanged_count':sum(row.get('foreground_unchanged') is True for row in captures.values()),
              'thresholds':{'rgb_delta':12, 'temporal_delta':2, 'crosshair_half_extent':20},
              'scene_roi':scene_roi, 'cases':{}, 'measurements':source['measurements'],
              'opacity_patch_commit':source.get('opacity_patch',{}).get('commit'),
              'native_shape_accepted':False, 'native_uv_accepted':False, 'native_alpha_accepted':False,
              'production_editor_accepted':False, 'production_world_accepted':False, 'production_memory_accepted':False,
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
            body = difference_mask(negative,empty,selected_scene)
            row['scene_view_controls'][phase] = {'water':mask_row(water), 'body':mask_row(body),
                'camera_depth':controls['supported_positive']['ready']['camera_depth'],
                'camera_pan':controls['supported_positive']['ready']['camera_pan'],
                'depth_plane':controls['supported_positive']['ready']['depth_plane']}
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh analysis output')
    report = analyze(args.input)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='ascii')
    print(json.dumps({'completed':report['completed'],'restored':report['restored'],
                      'captures_verified':report['captures_verified'],'capture_count':report['capture_count']}))
    return 0 if report['completed'] and report['restored'] and report['captures_verified'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
