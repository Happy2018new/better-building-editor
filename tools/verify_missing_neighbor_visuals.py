"""Pixel contracts for connected native projections with one occupied neighbor.

Run with run_live_check.py in the parent's owned game. Client occupancy reads
are replaced temporarily; no world blocks, server data or player position are
changed. Baseline, dynamic hiding and initial regeneration use the same camera.
"""
import argparse
import json
import math
import time
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageStat

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

INSTALL_OBSERVER = '''import modern_projection.projection.occupancy as occupancy_module
assert not hasattr(sys,'_neighbor_qa_saved'), 'A previous neighbor probe needs cleanup'
sys._neighbor_qa_saved=occupancy_module.ProjectionOccupancy
sys._neighbor_qa_occupied=set()
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
if hasattr(sys,'_neighbor_qa_document'):del sys._neighbor_qa_document
if hasattr(sys,'_neighbor_qa_history'):del sys._neighbor_qa_history
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
 'document_preserved':s.editor.document.blocks==sys._neighbor_qa_document,
 'occupancy_document_preserved':t.document.blocks==sys._neighbor_qa_document if t is not None else False,
 'history_preserved':(len(s.editor.undo_stack),len(s.editor.redo_stack))==sys._neighbor_qa_history,
 'player':b.player_position.GetFootPos()})
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


def roi_masks(projection, size, keep, occupied):
    scale = (size[0] / projection['screen'][0], size[1] / projection['screen'][1])
    masks, polygons = {}, {}
    for row in projection['cells']:
        pos = tuple(row['pos'])
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
    return remaining, hidden, {'keep': polygons[keep], 'occupied': polygons[occupied],
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
    artifacts = {}
    for label, value, roi in (('baseline_remaining', baseline, keep_roi),
                            ('actual_remaining', actual, keep_roi),
                            ('baseline_hidden', baseline, hidden_roi),
                            ('actual_hidden', actual, hidden_roi)):
        path = prefix.with_name(prefix.name + '_' + label + '.png')
        box = roi.getbbox()
        if box is None:
            raise AssertionError('Empty acceptance ROI: ' + label)
        masked = ImageChops.multiply(value, Image.merge('RGB', (roi, roi, roi)))
        masked.crop(box).save(path)
        artifacts[label] = str(path.resolve())
    delta_path = prefix.with_name(prefix.name + '_signal_delta.png')
    ImageChops.difference(baseline, actual).save(delta_path)
    artifacts['signal_delta'] = str(delta_path.resolve())
    return {'passed': remaining_passed and hidden_passed, 'valid_baseline': valid,
            'remaining_passed': remaining_passed, 'hidden_passed': hidden_passed,
            'remaining_shape': shape, 'remaining_edges': edges, 'remaining_color_error': color,
            'hidden_baseline_pixels': hidden_before, 'hidden_actual_pixels': hidden_after,
            'hidden_residual': residual, 'threshold': threshold, 'minimum_baseline_pixels': min_pixels,
            'limits': {'shape_recall': .93, 'shape_precision': .93, 'edge_recall': .75,
                       'edge_precision': .75, 'color_channel_error': 20, 'hidden_residual': .05},
            'artifacts': artifacts}


def capture_signal(check, label):
    actors = check.run('_result=json.dumps(list(b.projection_entities.values())+([b.entity] if b.entity else []))')
    assert actors, 'No projection actors to capture'
    time.sleep(.35)
    shown = check.capture(label + '_shown')
    try:
        check.run('for entity in %r:\n assert b.factory.CreateActorRender(entity).SetNotRenderAtAll(True)\n_result=True' % actors)
        time.sleep(.25)
        hidden = check.capture(label + '_actor_hidden')
    finally:
        check.run('for entity in %r:\n assert b.factory.CreateActorRender(entity).SetNotRenderAtAll(False)\n_result=True' % actors)
    return signal(shown['path'], hidden['path']), {'shown': shown, 'actor_hidden': hidden, 'actors': actors}


def projection_ready(check, occupied, minimum_commit=None):
    def ready(state):
        if state['error'] or state['failed']:
            raise AssertionError(state)
        settled = (state['active'] and state['ready'] and state['actors'] and state['model'] and
                   not state['preparing'] and not state['building'] and not state['pending'] and
                   state['changed'] == 0 and state['target_tracked'])
        return settled and (minimum_commit is None or state['commits'] >= minimum_commit)
    state = check.wait('neighbor projection', ready,
                       lambda: check.run(PROJECTION_STATE % (occupied, occupied)))
    assert state['document_preserved'] and state['occupancy_document_preserved'] and state['history_preserved'], state
    return state


def prepare_case(check, label, keep, occupied, offset, opacity):
    check.run('owner.open_workspace()\n_result=True')
    check.wait('workspace opens', lambda nav: nav['open'] and not nav['transition'], check.navigation)
    original = check.fixture(FIXTURE)
    cropped = check.run('''from modern_projection.projection.cell import AIR
keep=%r
neighbor=%r
doc=s.editor.document
assert doc.get(keep)!=AIR and doc.get(neighbor)!=AIR
for pos in tuple(doc.blocks):
 if pos[1]==0 or not (min(keep[0],neighbor[0])-3<=pos[0]<=max(keep[0],neighbor[0])+3 and
                     min(keep[2],neighbor[2])-3<=pos[2]<=max(keep[2],neighbor[2])+3):
  del doc.blocks[pos]
sys._neighbor_qa_document=doc.blocks.copy()
sys._neighbor_qa_history=(len(s.editor.undo_stack),len(s.editor.redo_stack))
sys._neighbor_qa_occupied.clear()
foot=b.player_origin()
center=tuple((keep[i]+neighbor[i]+1.)/2. for i in range(3))
s.origin=tuple(int(foot[i]+(6,8,6)[i]-center[i]) for i in range(3))
s.opacity=%r
s.projection_missing=True
s.projection_outline=False
b.project()
_result=json.dumps({'size':doc.size,'cells':len(doc.blocks),'source':'built-in fixture; platform and remote categories cropped'})
''' % (keep, occupied, opacity))
    state = projection_ready(check, occupied)
    assert state['state'] == 1, state
    check.run('navigator.pop()\n_result=True')
    check.wait('close workspace for world', lambda nav: not nav['open'] and not nav['transition'], check.navigation)
    pose = check.run('''keep=%r
neighbor=%r
offset=%r
target=tuple(s.origin[i]+(keep[i]+neighbor[i]+1.)/2. for i in range(3))
position=tuple(target[i]+offset[i] for i in range(3))
rotation=api.GetRotFromDir(tuple(target[i]-position[i] for i in range(3)))
cam=b.factory.CreateCamera(b.level)
cam.DepartCamera()
cam.LockModCameraPitch(True)
cam.LockModCameraYaw(True)
assert cam.SetCameraPos(position)
assert cam.SetCameraRotation((rotation[0],rotation[1]+180.,0.))
_result=json.dumps({'target':target,'position':position,'rotation':rotation})
''' % (keep, occupied, tuple(offset)))
    time.sleep(.7)
    rois = check.run('''cam=b.factory.CreateCamera(b.level)
cells=[]
for pos in s.editor.document.blocks:
 if pos[1]!=%d:continue
 points=[]
 for dx in (.03,.97):
  for dy in (0.,1.6):
   for dz in (.03,.97):
    world=tuple(s.origin[i]+pos[i]+(dx,dy,dz)[i] for i in range(3))
    points.append(cam.WorldToScreenPoint(*world))
 cells.append({'pos':pos,'points':points})
_result=json.dumps({'cells':cells,'screen':b.factory.CreateGame(b.level).GetScreenSize()})
''' % keep[1])
    baseline_signal, capture = capture_signal(check, label + '_baseline')
    remaining_roi, hidden_roi, roi_record = roi_masks(rois, baseline_signal.size, keep, occupied)
    return baseline_signal, (remaining_roi, hidden_roi), {
        'fixture': original, 'cropped_document': cropped, 'projection': state,
        'camera': pose, 'capture': capture, 'roi': roi_record}


def case(check, label, keep, occupied, args):
    baseline, masks, before = prepare_case(check, label, keep, occupied, args.offset, args.opacity)
    check.run('sys._neighbor_qa_occupied.add(%r)\nb.projection_occupancy.read(%r)\n_result=True' % (occupied, occupied))
    dynamic = projection_ready(check, occupied, before['projection']['commits'] + 1)
    assert dynamic['state'] == 2, dynamic
    actual, capture = capture_signal(check, label + '_dynamic')
    prefix = args.output.parent / (args.output.stem + '_' + label + '_dynamic')
    dynamic_pixels = compare_pixels(baseline, actual, masks, prefix, args.min_pixels, args.threshold)
    dynamic.update(capture=capture, pixels=dynamic_pixels)
    check.run('b.project()\n_result=True')
    initial = projection_ready(check, occupied)
    assert initial['state'] == 2, initial
    actual, capture = capture_signal(check, label + '_initial')
    prefix = args.output.parent / (args.output.stem + '_' + label + '_initial')
    initial_pixels = compare_pixels(baseline, actual, masks, prefix, args.min_pixels, args.threshold)
    initial.update(capture=capture, pixels=initial_pixels)
    saved_player = check.run('_result=json.dumps(sys._blueprint_visual_saved["player"])')
    assert initial['player'] == saved_player and dynamic['player'] == saved_player, (saved_player, initial, dynamic)
    return {'case': label, 'keep': keep, 'occupied': occupied, 'passed': dynamic_pixels['passed'] and initial_pixels['passed'],
            'baseline': before, 'dynamic': dynamic, 'initial': initial}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--case', action='append', choices=tuple(VISUAL_CASES))
    parser.add_argument('--offset', type=float, nargs=3, default=(0., 6., .15), metavar=('X', 'Y', 'Z'))
    parser.add_argument('--opacity', type=float, default=.85)
    parser.add_argument('--timeout', type=float, default=90)
    parser.add_argument('--min-pixels', type=int, default=80)
    parser.add_argument('--threshold', type=int, default=16)
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--restore-detached', action='store_true')
    args = parser.parse_args()
    if args.timeout <= 0 or args.min_pixels <= 0 or not 0 < args.opacity <= 1 or not 0 <= args.threshold < 255:
        parser.error('Invalid timeout, pixel minimum, opacity or threshold')
    if math.sqrt(sum(value * value for value in args.offset)) < 3:
        parser.error('Use a camera offset at least three blocks from the target')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    evidence = {'schema': 1, 'fixture': FIXTURE, 'cases': [], 'completed': False, 'passed': False,
                'occupancy_source': 'temporary client observation replacement; no world writes',
                'baseline': 'native complete palette in missing mode with all observations air',
                'visual_contract': 'remaining pixels match baseline; occupied-cell actor pixels disappear',
                'limitations': ['Focused overhead view; side and underside faces need separate views.',
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
                                      'dynamic': result['dynamic']['pixels'],
                                      'initial': result['initial']['pixels']}), flush=True)
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
