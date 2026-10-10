"""Pixel contracts for connected native projections with one occupied neighbor.

Run with run_live_check.py in a managed game instance. Client occupancy reads
are replaced temporarily; no world blocks, server data or player position are
changed. Baseline, dynamic hiding and initial regeneration use the same camera.
"""
import argparse
import json
import math
import os
import time
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageStat

from camera_projection import project_box_corners
from verify_debug_blueprints import BlueprintCheck, Client, INSTALL_PROBE, RESTORE, write_json
from verify_debug_visuals import SAVE_VISUAL, camera_restore_code

FIXTURE = 'test.connections.context'
VISUAL_CASES = {
    'stairs': ((3, 1, 23), (4, 1, 23)),
    'rail': ((3, 1, 3), (4, 1, 3)),
    'wall': ((7, 1, 17), (7, 1, 16)),
    'fence': ((17, 1, 17), (18, 1, 17)),
    'pane': ((17, 1, 20), (17, 1, 21)),
    'iron_bars': ((22, 1, 20), (22, 1, 21)),
    'chest_keep_sub': ((27, 1, 5), (26, 1, 5)),
    'chest_keep_main': ((26, 1, 5), (27, 1, 5)),
    'copper_chest_keep_sub': ((27, 1, 10), (26, 1, 10)),
    'copper_chest_keep_main': ((26, 1, 10), (27, 1, 10)),
}
VIEWS = ('top', 'side', 'under')

INSTALL_OBSERVER = '''import modern_projection.projection.occupancy as occupancy_module
assert not hasattr(sys,'_neighbor_qa_saved'), 'A previous neighbor probe needs cleanup'
sys._neighbor_qa_saved=occupancy_module.ProjectionOccupancy
sys._neighbor_qa_occupied=set()
sys._neighbor_qa_owner=owner
class BlueprintNeighborOccupancy(occupancy_module.ProjectionOccupancy):
 def __init__(self,*args,**kwargs):
  sys._neighbor_qa_saved.__init__(self,*args,**kwargs)
  self.bulk=None
  self.bulk_job=None
 def read(self,pos,initial=False):
  self.reads+=1
  return self.observe(self.index(pos),2 if pos in sys._neighbor_qa_occupied else 1,initial)
occupancy_module.ProjectionOccupancy=BlueprintNeighborOccupancy
_result=True
'''

RESTORE_OBSERVER = '''import modern_projection.projection.occupancy as occupancy_module
occupancy_module.ProjectionOccupancy=sys._neighbor_qa_saved
del sys._neighbor_qa_saved
del sys._neighbor_qa_occupied
for field in ('document','history','source','editor','origin','owner','camera'):
 name='_neighbor_qa_'+field
 if hasattr(sys,name):delattr(sys,name)
_result=True
'''

PROJECTION_STATE = '''t=b.projection_occupancy
work=b.projection_work
ids=list(b.projection_entities.values())+([b.entity] if b.entity else [])
_result=json.dumps({'active':s.projection_active,'actors':ids,'preparing':bool(b.preparing_entity),
 'ready':work is None or work.ready,'error':work.error if work is not None else None,
 'failed':t.failed if t is not None else None,'model':b.projection_mesh,
 'builds':t.builds if t is not None else 0,'commits':t.commits if t is not None else 0,
 'building':t is not None and t.build is not None,
 'pending':t is not None and (t.pending_model is not None or t.attaching),
 'changed':len(t.changed) if t is not None else 0,
 'state':t.state[t.index(%r)] if t is not None else None,
 'target_tracked':%r in t.targets if t is not None else False,
 'has_occupancy':t is not None,
 'document_preserved':s.editor.document.blocks==sys._neighbor_qa_document,
 'occupancy_document_preserved':t.document.blocks==sys._neighbor_qa_document if t is not None else False,
 'history_preserved':(len(s.editor.undo_stack),len(s.editor.redo_stack))==sys._neighbor_qa_history,
 'source_reference_preserved':owner is sys._neighbor_qa_owner and s.editor is sys._neighbor_qa_editor and
  s.editor.document is sys._neighbor_qa_source and tuple(s.origin)==sys._neighbor_qa_origin,
 'fixture_preserved':sys._blueprint_qa_identity==%r,
 'projection_serial':b.projection_serial,
 'player':b.player_position.GetFootPos()})
'''

CROP_FIXTURE = '''from modern_projection.projection.cell import AIR
keep=%r
neighbor=%r
doc=s.editor.document
assert doc.get(keep)!=AIR and doc.get(neighbor)!=AIR
for pos in tuple(doc.blocks):
 if pos[1]==0 or not (min(keep[0],neighbor[0])-3<=pos[0]<=max(keep[0],neighbor[0])+3 and
                     min(keep[2],neighbor[2])-3<=pos[2]<=max(keep[2],neighbor[2])+3):
  doc.blocks[pos]=AIR
sys._neighbor_qa_document=doc.blocks.copy()
sys._neighbor_qa_history=(len(s.editor.undo_stack),len(s.editor.redo_stack))
sys._neighbor_qa_editor=s.editor
sys._neighbor_qa_source=doc
sys._neighbor_qa_occupied.clear()
foot=b.player_origin()
center=tuple((keep[i]+neighbor[i]+1.)/2. for i in range(3))
s.origin=tuple(int(foot[i]+(6,8,6)[i]-center[i]) for i in range(3))
sys._neighbor_qa_origin=tuple(s.origin)
s.opacity=%r
s.projection_missing=True
s.projection_outline=False
b.project()
_result=json.dumps({'size':doc.size,'cells':len(doc.blocks),'source':'built-in fixture; platform and remote categories cropped'})
'''

SET_CAMERA = '''keep=%r
neighbor=%r
offset=%r
assert tuple(s.origin)==sys._neighbor_qa_origin
target=tuple(s.origin[i]+(keep[i]+neighbor[i]+1.)/2. for i in range(3))
position=tuple(target[i]+offset[i] for i in range(3))
direction=api.GetRotFromDir(tuple(target[i]-position[i] for i in range(3)))
rotation=(direction[0],direction[1]+180.,0.)
cam=b.factory.CreateCamera(b.level)
cam.DepartCamera()
cam.LockModCameraPitch(True)
cam.LockModCameraYaw(True)
assert cam.SetCameraPos(position)
assert cam.SetCameraRotation(rotation)
sys._neighbor_qa_camera={'position':position,'rotation':rotation,'target':target}
_result=json.dumps(sys._neighbor_qa_camera)
'''

CAMERA_STATE = '''cam=b.factory.CreateCamera(b.level)
_result=json.dumps({'position':cam.GetPosition(),'rotation':cam.GetCameraRotation(),
 'screen':b.factory.CreateGame(b.level).GetScreenSize()})
'''

CELL_ROIS = '''cam=b.factory.CreateCamera(b.level)
game=b.factory.CreateGame(b.level)
target=sys._neighbor_qa_camera['target']
position=cam.GetPosition()
assert hasattr(cam,'GetFov'), 'NEMC 3.9 Camera.GetFov is required for fallback projection'
fov=cam.GetFov()
cells=[]
for pos in s.editor.document.blocks:
 world_points=[]
 for dx in (.03,.97):
  for dy in (0.,1.6):
   for dz in (.03,.97):
    world=tuple(s.origin[i]+pos[i]+(dx,dy,dz)[i] for i in range(3))
    world_points.append(world)
 points=[]
 if hasattr(cam,'WorldToScreenPoint'):
  points=[cam.WorldToScreenPoint(*world) for world in world_points]
 cells.append({'pos':pos,'world_points':world_points,'native_points':points})
_result=json.dumps({'cells':cells,'screen':game.GetScreenSize(),'position':position,
 'rotation':cam.GetCameraRotation(),'target':target,'fov':fov,
 'runtime_minecraft_version':api.GetMinecraftVersion(),
 'projection_method':'native' if hasattr(cam,'WorldToScreenPoint') else 'analytic_vertical_fov'})
'''


def hull(points):
    ordered = sorted(set(tuple(point) for point in points))
    if len(ordered) <= 2:
        return ordered

    def cross(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    low, high = [], []
    for point in ordered:
        while len(low) >= 2 and cross(low[-2], low[-1], point) <= 0:
            low.pop()
        low.append(point)
    for point in reversed(ordered):
        while len(high) >= 2 and cross(high[-2], high[-1], point) <= 0:
            high.pop()
        high.append(point)
    return low[:-1] + high[:-1]


def maximum(image):
    red, green, blue = image.split()
    return ImageChops.lighter(ImageChops.lighter(red, green), blue)


def count(mask):
    return mask.histogram()[255]


def signal(shown, hidden):
    with Image.open(shown).convert('RGB') as first, Image.open(hidden).convert('RGB') as second:
        if first.size != second.size:
            raise AssertionError('The viewport changed during a visibility capture')
        return ImageChops.difference(first, second)


def roi_masks(projection, size, keep, occupied, calibration=None):
    effective_fov = projection['fov']
    if calibration is not None and projection['projection_method'] != 'native':
        assert calibration.get('passed') and calibration.get('completed'), calibration
        assert calibration['session_file'] == os.environ.get('MCDEV_SESSION_FILE'), calibration
        assert calibration['runtime_minecraft_version'] == projection['runtime_minecraft_version'], calibration
        assert abs(calibration['reported_fov'] - projection['fov']) < .01, calibration
        assert abs(calibration['screen_aspect'] - projection['screen'][0] / projection['screen'][1]) < .01, calibration
        effective_fov = calibration['vertical_fov']
    if projection['projection_method'] == 'native':
        for row in projection['cells']:
            row['points'] = row.pop('native_points')
    else:
        for row in projection['cells']:
            row['points'] = project_box_corners(row['world_points'], projection['position'],
                                                projection['target'], projection['screen'],
                                                effective_fov, projection['rotation'][2])
            del row['world_points']
    projection['projection_details'] = {
        'method': projection['projection_method'],
        'fov_degrees': projection['fov'],
        'effective_vertical_fov': effective_fov,
        'calibration': calibration,
        'fov_convention': 'vertical' if projection['projection_method'] != 'native' else 'native engine',
        'position': projection['position'], 'target': projection['target'],
        'rotation': projection['rotation'], 'screen': projection['screen']}
    scale = (size[0] / projection['screen'][0], size[1] / projection['screen'][1])
    masks, polygons = {}, {}
    for row in projection['cells']:
        pos = tuple(row['pos'])
        if not row['points']:
            assert pos not in (keep, occupied), 'A target cell lies behind the camera: %r' % (pos,)
            masks[pos] = Image.new('L', size)
            continue
        if pos in (keep, occupied) and not all(point['isInScreen'] for point in row['points']):
            raise AssertionError('A native cell ROI lies outside the viewport: %r' % row)
        polygon = hull((point['screenX'] * scale[0], point['screenY'] * scale[1])
                       for point in row['points'])
        mask = Image.new('L', size)
        ImageDraw.Draw(mask).polygon(polygon, fill=255)
        masks[pos], polygons[pos] = mask, polygon
    remaining = ImageChops.subtract(masks[keep], masks[occupied])
    hidden = masks[occupied].copy()
    for pos, mask in masks.items():
        if pos != occupied:
            hidden = ImageChops.subtract(hidden, mask)
    return remaining, hidden, {'projection': projection['projection_details'],
                               'keep': polygons[keep], 'occupied': polygons[occupied],
                               'remaining_area': count(remaining), 'hidden_area': count(hidden),
                               'viewport_scale': scale}


def binary(image, threshold):
    return image.point(lambda value: 255 if value > threshold else 0)


def feature_overlap(first, second):
    first_count, second_count = count(first), count(second)
    recall = count(ImageChops.multiply(first, second.filter(ImageFilter.MaxFilter(3)))) / max(1, first_count)
    precision = count(ImageChops.multiply(second, first.filter(ImageFilter.MaxFilter(3)))) / max(1, second_count)
    union = count(ImageChops.lighter(first, second))
    return {'baseline_pixels': first_count, 'actual_pixels': second_count,
            'recall_1px': recall, 'precision_1px': precision,
            'iou': count(ImageChops.multiply(first, second)) / max(1, union)}


def compare_pixels(baseline, actual, masks, prefix, min_pixels, threshold):
    keep_roi, hidden_roi = masks
    baseline_presence, actual_presence = (binary(maximum(value), threshold)
                                         for value in (baseline, actual))
    full_keep = ImageChops.multiply(baseline_presence, keep_roi)
    now_keep = ImageChops.multiply(actual_presence, keep_roi)
    full_hidden = ImageChops.multiply(baseline_presence, hidden_roi)
    now_hidden = ImageChops.multiply(actual_presence, hidden_roi)
    shape = feature_overlap(full_keep, now_keep)
    edge_inputs = []
    for value in (baseline, actual):
        edges = binary(value.convert('L').filter(ImageFilter.FIND_EDGES), 18)
        edge_inputs.append(ImageChops.multiply(edges, keep_roi))
    edges = feature_overlap(*edge_inputs)
    shared = ImageChops.multiply(full_keep, now_keep)
    color = (ImageStat.Stat(ImageChops.difference(baseline, actual), mask=shared).mean
             if count(shared) else [255., 255., 255.])
    hidden_before, hidden_after = count(full_hidden), count(now_hidden)
    residual = hidden_after / max(1, hidden_before)
    valid = (shape['baseline_pixels'] >= min_pixels and hidden_before >= min_pixels and
             edges['baseline_pixels'] >= max(20, min_pixels // 4))
    remaining_passed = (valid and shape['recall_1px'] >= .93 and shape['precision_1px'] >= .93 and
                        edges['recall_1px'] >= .75 and edges['precision_1px'] >= .75 and max(color) <= 20)
    hidden_passed = valid and residual <= .05
    failures = []
    if not valid:
        failures.append('insufficient_observable_native_baseline')
    else:
        if not remaining_passed:
            failures.append('remaining_native_pixels_changed')
        if not hidden_passed:
            failures.append('occupied_cell_native_pixels_remain')
    artifacts = {}
    for label, value, roi in (('baseline_remaining', baseline, keep_roi),
                            ('actual_remaining', actual, keep_roi),
                            ('baseline_hidden', baseline, hidden_roi),
                            ('actual_hidden', actual, hidden_roi)):
        path = prefix.with_name(prefix.name + '_' + label + '.png')
        box = roi.getbbox() or (0, 0, value.width, value.height)
        masked = ImageChops.multiply(value, Image.merge('RGB', (roi, roi, roi)))
        masked.crop(box).save(path)
        artifacts[label] = str(path.resolve())
    delta_path = prefix.with_name(prefix.name + '_signal_delta.png')
    ImageChops.difference(baseline, actual).save(delta_path)
    artifacts['signal_delta'] = str(delta_path.resolve())
    return {'passed': remaining_passed and hidden_passed, 'valid_baseline': valid, 'failures': failures,
            'remaining_passed': remaining_passed, 'hidden_passed': hidden_passed,
            'remaining_shape': shape, 'remaining_edges': edges, 'remaining_color_error': color,
            'hidden_baseline_pixels': hidden_before, 'hidden_actual_pixels': hidden_after,
            'hidden_residual': residual, 'threshold': threshold, 'minimum_baseline_pixels': min_pixels,
            'limits': {'shape_recall': .93, 'shape_precision': .93, 'edge_recall': .75,
                       'edge_precision': .75, 'color_channel_error': 20, 'hidden_residual': .05},
            'artifacts': artifacts}


def compare_complete(baseline, actual, masks, threshold, min_pixels):
    """Require the all-air context mesh to match the complete native mesh."""
    roi = ImageChops.lighter(*masks)
    first, second = (ImageChops.multiply(binary(maximum(value), threshold), roi)
                     for value in (baseline, actual))
    overlap = feature_overlap(first, second)
    shared = ImageChops.multiply(first, second)
    color = (ImageStat.Stat(ImageChops.difference(baseline, actual), mask=shared).mean
             if count(shared) else [255., 255., 255.])
    valid = overlap['baseline_pixels'] >= min_pixels * 2
    return {'passed': valid and overlap['recall_1px'] >= .93 and
            overlap['precision_1px'] >= .93 and max(color) <= 20,
            'valid_baseline': valid, 'shape': overlap, 'color_error': color,
            'limits': {'shape_recall': .93, 'shape_precision': .93, 'color_channel_error': 20}}


def camera_matches(actual, expected):
    position = all(abs(actual['position'][i] - expected['position'][i]) < .02 for i in range(3))
    rotation = all(abs((actual['rotation'][i] - expected['rotation'][i] + 180.) % 360. - 180.) < .2
                   for i in range(3))
    return position and rotation


def source_state(check, occupied):
    state = check.run(PROJECTION_STATE % (occupied, occupied, FIXTURE))
    fields = ('document_preserved', 'history_preserved',
              'source_reference_preserved', 'fixture_preserved')
    assert all(state[field] for field in fields), state
    assert not state['has_occupancy'] or state['occupancy_document_preserved'], state
    return state


def capture_signal(check, label, occupied):
    time.sleep(.35)
    before = source_state(check, occupied)
    camera_before = check.run(CAMERA_STATE)
    expected_camera = check.run('_result=json.dumps(sys._neighbor_qa_camera)')
    assert camera_matches(camera_before, expected_camera), (camera_before, expected_camera)
    actors = before['actors']
    assert actors, 'No projection actors to capture'
    shown = check.capture(label + '_shown')
    try:
        check.run('for entity in %r:\n assert b.factory.CreateActorRender(entity).SetNotRenderAtAll(True)\n_result=True' % actors)
        time.sleep(.25)
        hidden = check.capture(label + '_actor_hidden')
    finally:
        check.run('for entity in %r:\n assert b.factory.CreateActorRender(entity).SetNotRenderAtAll(False)\n_result=True' % actors)
    after = source_state(check, occupied)
    camera_after = check.run(CAMERA_STATE)
    assert camera_matches(camera_after, expected_camera), (camera_after, expected_camera)
    assert camera_before['screen'] == camera_after['screen'], (camera_before, camera_after)
    assert (before['projection_serial'], before['actors'], before['model']) == (
        after['projection_serial'], after['actors'], after['model']), (before, after)
    return signal(shown['path'], hidden['path']), {
        'shown': shown, 'actor_hidden': hidden, 'actors': actors,
        'source_before': before, 'source_after': after,
        'camera_before': camera_before, 'camera_after': camera_after}


def projection_ready(check, occupied, minimum_commit=None):
    def ready(state):
        if state['error'] or state['failed']:
            raise AssertionError(state)
        settled = (state['active'] and state['ready'] and state['has_occupancy'] and state['actors'] and state['model'] and
                   not state['preparing'] and not state['building'] and not state['pending'] and
                   state['changed'] == 0 and state['target_tracked'])
        return settled and (minimum_commit is None or state['commits'] >= minimum_commit)
    state = check.wait('neighbor projection', ready,
                       lambda: source_state(check, occupied))
    return state


def prepare_case(check, keep, occupied, opacity):
    check.run('owner.open_workspace()\n_result=True')
    check.wait('workspace opens', lambda nav: nav['open'] and not nav['transition'], check.navigation)
    original = check.fixture(FIXTURE)
    cropped = check.run(CROP_FIXTURE % (keep, occupied, opacity))
    state = projection_ready(check, occupied)
    assert state['state'] == 1, state
    check.run('navigator.pop()\n_result=True')
    check.wait('close workspace for world', lambda nav: not nav['open'] and not nav['transition'], check.navigation)
    return {'fixture': original, 'cropped_document': cropped, 'projection': state}


def view_offset(keep, occupied, view, override=None):
    if override is not None:
        return tuple(override)
    if view == 'top':
        return (0., 6., .15)
    if view == 'under':
        return (0., -6., .15)
    dx, dz = occupied[0] - keep[0], occupied[2] - keep[2]
    length = math.sqrt(dx * dx + dz * dz)
    assert length, 'A side view requires horizontally separated neighboring cells'
    return (6. * dz / length, 2.4, -6. * dx / length)


def select_view(check, keep, occupied, view, override=None):
    pose = check.run(SET_CAMERA % (keep, occupied, view_offset(keep, occupied, view, override)))
    stable = check.wait('camera ' + view, lambda value: camera_matches(value, pose),
                        lambda: check.run(CAMERA_STATE))
    # Native camera interpolation and the projection-follow transform run on
    # different ticks. The capture also checks stability across both images.
    time.sleep(.35)
    pose.update(view=view, stable=stable)
    return pose


def case(check, label, keep, occupied, args):
    before = prepare_case(check, keep, occupied, args.opacity)
    baselines, masks = {}, {}
    before['views'] = {}
    for view in args.view or VIEWS:
        pose = select_view(check, keep, occupied, view, args.offset)
        baseline, capture = capture_signal(check, label + '_' + view + '_baseline', occupied)
        rois = check.run(CELL_ROIS)
        keep_roi, hidden_roi, roi_record = roi_masks(rois, baseline.size, keep, occupied, args.camera_calibration)
        baselines[view], masks[view] = baseline, (keep_roi, hidden_roi)
        before['views'][view] = {'camera': pose, 'capture': capture, 'roi': roi_record}
    if args.normal_oracle:
        check.run('s.projection_missing=False\nb.project()\n_result=True')
        check.wait('complete native projection', lambda state: state['active'] and
                   state['ready'] and state['actors'] and state['model'] and not
                   state['has_occupancy'] and not state['preparing'],
                   lambda: source_state(check, occupied))
        before['normal_oracle'] = {}
        for view in baselines:
            pose = select_view(check, keep, occupied, view, args.offset)
            native, capture = capture_signal(check, label + '_' + view + '_native_complete', occupied)
            comparison = compare_complete(native, baselines[view], masks[view],
                                          args.threshold, args.min_pixels)
            before['normal_oracle'][view] = {'camera': pose, 'capture': capture,
                                            'context_matches_complete': comparison}
            baselines[view] = native
        check.run('s.projection_missing=True\nb.project()\n_result=True')
        before['projection'] = projection_ready(check, occupied)
        assert before['projection']['state'] == 1, before['projection']
    check.run('sys._neighbor_qa_occupied.add(%r)\nb.projection_occupancy.read(%r)\n_result=True' % (occupied, occupied))
    dynamic = projection_ready(check, occupied, before['projection']['commits'] + 1)
    assert dynamic['state'] == 2, dynamic
    dynamic['views'] = {}
    for view, baseline in baselines.items():
        pose = select_view(check, keep, occupied, view, args.offset)
        actual, capture = capture_signal(check, label + '_' + view + '_dynamic', occupied)
        prefix = args.output.parent / (args.output.stem + '_' + label + '_' + view + '_dynamic')
        pixels = compare_pixels(baseline, actual, masks[view], prefix, args.min_pixels, args.threshold)
        dynamic['views'][view] = {'camera': pose, 'capture': capture, 'pixels': pixels}
    check.run('b.project()\n_result=True')
    initial = projection_ready(check, occupied)
    assert initial['state'] == 2, initial
    initial['views'] = {}
    for view, baseline in baselines.items():
        pose = select_view(check, keep, occupied, view, args.offset)
        actual, capture = capture_signal(check, label + '_' + view + '_initial', occupied)
        prefix = args.output.parent / (args.output.stem + '_' + label + '_' + view + '_initial')
        pixels = compare_pixels(baseline, actual, masks[view], prefix, args.min_pixels, args.threshold)
        initial['views'][view] = {'camera': pose, 'capture': capture, 'pixels': pixels}
    saved_player = check.run('_result=json.dumps(sys._blueprint_visual_saved["player"])')
    assert initial['player'] == saved_player and dynamic['player'] == saved_player, (saved_player, initial, dynamic)
    passed = all(row['pixels']['passed'] for stage in (dynamic, initial) for row in stage['views'].values())
    if args.normal_oracle:
        passed = passed and all(row['context_matches_complete']['passed']
                                for row in before['normal_oracle'].values())
    return {'case': label, 'keep': keep, 'occupied': occupied, 'passed': passed,
            'baseline': before, 'dynamic': dynamic, 'initial': initial}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--case', action='append', choices=tuple(VISUAL_CASES))
    parser.add_argument('--view', action='append', choices=VIEWS,
                        help='Repeat to select views; defaults to top, side and under')
    parser.add_argument('--offset', type=float, nargs=3, metavar=('X', 'Y', 'Z'),
                        help='Custom camera offset; requires exactly one --view')
    parser.add_argument('--opacity', type=float, default=.85)
    parser.add_argument('--timeout', type=float, default=90)
    parser.add_argument('--min-pixels', type=int, default=80)
    parser.add_argument('--threshold', type=int, default=16)
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--restore-detached', action='store_true')
    parser.add_argument('--camera-calibration', type=Path,
                        help='Passed native-cube FOV calibration evidence JSON')
    parser.add_argument('--normal-oracle', action='store_true',
                        help='Use the complete native projection as the independent pixel baseline')
    args = parser.parse_args()
    if args.camera_calibration is not None:
        args.camera_calibration = json.loads(args.camera_calibration.read_text(encoding='utf8'))
    if args.timeout <= 0 or args.min_pixels <= 0 or not 0 < args.opacity <= 1 or not 0 <= args.threshold < 255:
        parser.error('Invalid timeout, pixel minimum, opacity or threshold')
    if args.offset is not None and len(args.view or ()) != 1:
        parser.error('A custom --offset requires exactly one --view')
    if args.offset is not None and math.sqrt(sum(value * value for value in args.offset)) < 3:
        parser.error('Use a camera offset at least three blocks from the target')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    evidence = {'schema': 2, 'fixture': FIXTURE, 'cases': [], 'completed': False, 'passed': False,
                'views': args.view or VIEWS,
                'occupancy_source': 'temporary client observation replacement; no world writes',
                'baseline': ('complete native projection; context all-air independently compared'
                             if args.normal_oracle else
                             'native complete palette in missing mode with all observations air'),
                'visual_contract': 'remaining pixels match baseline; occupied-cell actor pixels disappear',
                'limitations': ['Selected views require observable remaining and occupied native surfaces.',
                                'Invisible or occluded baseline surfaces fail validity; they do not establish a rendering regression.',
                                'Pixel tolerances are explicit. Insufficient visible baseline pixels fail.']}
    installed = visual_saved = observer_installed = False
    try:
        with Client(timeout=30) as client:
            check = BlueprintCheck(client, args.output, args.timeout)
            check.run(INSTALL_PROBE)
            installed = True
            try:
                check.run(SAVE_VISUAL)
                visual_saved = True
                if args.refresh:
                    check.refresh()
                check.run(INSTALL_OBSERVER)
                observer_installed = True
                check.page()
                for label in args.case or tuple(VISUAL_CASES):
                    result = case(check, label, *VISUAL_CASES[label], args)
                    evidence['cases'].append(result)
                    write_json(args.output, evidence)
                    print(json.dumps({'case': label, 'passed': result['passed'],
                                      'dynamic': dict((view, row['pixels']) for view, row in result['dynamic']['views'].items()),
                                      'initial': dict((view, row['pixels']) for view, row in result['initial']['views'].items())}), flush=True)
                    check.run('b.stop_projection()\n_result=True')
                    check.run(camera_restore_code(args.restore_detached))
                evidence['completed'] = True
                evidence['passed'] = all(row['passed'] for row in evidence['cases'])
            finally:
                if visual_saved:
                    check.run('b.stop_projection()\n_result=True')
                    check.run(camera_restore_code(args.restore_detached))
                    check.run('saved=sys._blueprint_visual_saved\n'
                              's.origin=saved["origin"]\ns.opacity=saved["opacity"]\n'
                              's.projection_missing=saved["missing"]\ns.projection_outline=saved["outline"]\n'
                              'del sys._blueprint_visual_saved\n_result=True')
                if observer_installed:
                    check.run(RESTORE_OBSERVER)
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
    print(json.dumps({'evidence': str(args.output.resolve()), 'cases': len(evidence['cases']),
                      'completed': evidence['completed'], 'passed': evidence['passed'],
                      'restored': evidence.get('restored')}))
    return 0 if evidence['completed'] and evidence['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
