"""Capture public liquid controls in a sealed, explicitly changed native context.

Run only through the owned live-check harness. This captures diagnostic pixels,
not geometry acceptance; the selected shell is not part of the public source.
"""
import argparse
import copy
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys
import time
import uuid

from PIL import Image, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.cell import AIR, background, decode, encode, foreground
from projection.debug_liquid_blueprints import VISUAL_CASE, source_document

CASES = ('water_depth_0_foreground', 'lava_depth_0_foreground')
CONTROLS = ('supported_positive', 'supported_negative', 'liquid_only', 'empty')
BOUNDARY_GUARD = 3


def wire(value):
    return json.dumps(value, ensure_ascii=True, separators=(',', ':'))


def fixture_plan(case, cell_origin, platform, shell_block='glass'):
    if case not in CASES:
        raise ValueError('Only the two source foreground cases are supported')
    if shell_block not in ('glass', 'barrier'):
        raise ValueError('Only glass or barrier diagnostic shells are supported')
    origin = tuple(cell_origin)
    focus = VISUAL_CASE['focus']
    document_origin = tuple(origin[i] - focus[i] for i in range(3))
    shell, cavity = [], []
    for offset in itertools.product(range(-1, 2), range(-2, 3), range(-1, 2)):
        pos = tuple(origin[i] + offset[i] for i in range(3))
        if abs(offset[0]) == 1 or abs(offset[2]) == 1 or abs(offset[1]) == 2:
            shell.append(pos)
        else:
            cavity.append(pos)
    reserved = {tuple(origin[i] + offset[i] for i in range(3))
                for offset in itertools.product(range(-2, 3), range(-3, 4), range(-2, 3))}
    reserved.update((platform[0], platform[1] + y, platform[2]) for y in range(4))
    controls = {}
    for control in CONTROLS:
        document = source_document(case, isolated=True, control=control)
        cells = [(tuple(document_origin[i] + pos[i] for i in range(3)), encode(value))
                 for pos, value in sorted(document.blocks.items())]
        if not set(pos for pos, value in cells).issubset(cavity):
            raise ValueError('Public source does not fit the declared sealed cavity')
        controls[control] = {'document_origin': document_origin, 'cells': cells,
                             'isolated_cells': [(pos, encode(value))
                                                for pos, value in sorted(document.blocks.items())]}
    row = next(item for item in VISUAL_CASE['cases'] if item['id'] == case)
    return {'case': case, 'cell_origin': origin, 'document_origin': document_origin,
            'original_keep': row['keep'], 'isolated_keep': focus,
            'shell': sorted(shell), 'cavity': sorted(cavity), 'reserved': sorted(reserved),
            'platform': tuple(platform), 'controls': controls,
            'shell_value': ('minecraft:' + shell_block, 0), 'context_changed': True,
            'public_controls_eligible': False}


def native_cells(snapshot, positions):
    if snapshot.get('valid') is not True:
        return None
    rows = snapshot.get('cells', [])
    result = {}
    for row in rows:
        pos = tuple(row['pos'])
        if pos in result:
            return None
        result[pos] = (tuple(row['foreground']), tuple(row['background']), bool(row.get('actor')))
    selected = set(map(tuple, positions))
    if not selected.issubset(result):
        return None
    return {pos: result[pos] for pos in selected}


def expected_native(cells, positions):
    result = {tuple(pos): (AIR, AIR, False) for pos in positions}
    for pos, encoded in cells:
        value = decode(encoded)
        result[tuple(pos)] = (foreground(value), background(value), False)
    return result


def matches(snapshot, cells, positions):
    return native_cells(snapshot, positions) == expected_native(cells, positions)


def native_changes(before, after, positions):
    first, second = native_cells(before, positions), native_cells(after, positions)
    if first is None or second is None:
        return {'observable': False, 'unchanged': False, 'changes': [],
                'reason': 'invalid_or_incomplete_native_snapshot'}
    return {'observable': True, 'unchanged': first == second,
            'changes': [{'pos': pos, 'before': first[pos], 'after': second[pos]}
                        for pos in sorted(first) if first[pos] != second[pos]]}


def capture_native_gate(before, after, plan, requested, platform_present=True):
    shell = [(pos, encode(plan['shell_value'])) for pos in plan['shell']]
    context = shell + ([(plan['platform'], encode(('minecraft:stone', 0)))]
                       if platform_present else [])
    expected = context + requested
    sides = {}
    for side in ('server', 'client'):
        sides[side] = {'before_matches_requested_context': matches(before[side], expected, plan['reserved']),
                       'after_matches_requested_context': matches(after[side], expected, plan['reserved']),
                       'cavity_changes': native_changes(before[side], after[side], plan['cavity']),
                       'reservation_changes': native_changes(before[side], after[side], plan['reserved'])}
    passed = all(row['before_matches_requested_context'] and row['after_matches_requested_context']
                 and row['reservation_changes']['unchanged'] for row in sides.values())
    return {'declared_context_state_passed': passed, 'sides': sides,
            'public_controls_eligible': False, 'native_geometry_accepted': False}


def validate_png(record, session, expected_size=None):
    path = Path(record['path'])
    capture = record.get('capture', {})
    if not (record.get('background_only') is True and capture.get('ok') is True
            and capture.get('reliable') is True and capture.get('background_only') is True
            and capture.get('background_safe') is True
            and capture.get('backend') == 'Windows.Graphics.Capture'):
        raise ValueError('An owner-bound reliable background WGC capture is required')
    for key in ('owner', 'game_pid', 'game_identity'):
        if str(capture.get(key)) != str(session[key]):
            raise ValueError('Native capture session mismatch: ' + key)
    if Path(capture.get('session_file', '')).resolve() != Path(session['session_file']).resolve():
        raise ValueError('Native capture session file mismatch')
    if capture.get('window', {}).get('pid') != session['game_pid']:
        raise ValueError('Native capture window PID mismatch')
    frame = capture.get('frame', {})
    if (not frame.get('ok') or frame.get('frame_qpc_100ns', -1) < frame.get('request_qpc_100ns', 0)):
        raise ValueError('Native capture frame is not fresh')
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if (record.get('sha256') != digest or capture.get('sha256') != digest
            or record.get('bytes') != len(payload) or capture.get('bytes') != len(payload)):
        raise ValueError('Native PNG fingerprint changed')
    with Image.open(path) as image:
        size = image.size
        variance = ImageStat.Stat(image.convert('RGB')).var
        if image.format != 'PNG' or max(variance) <= 1.:
            raise ValueError('Native PNG is invalid or blank')
        if tuple(record.get('size', ())) != size or (frame.get('width'), frame.get('height')) != size:
            raise ValueError('Native PNG dimensions differ from the capture record')
        if expected_size is not None and tuple(expected_size) != size:
            raise ValueError('Native viewport changed between controls')
    return {'reliable': True, 'sha256': digest, 'size': size, 'variance': variance}


def fixed_viewport(record, pose):
    stable = pose['stable']
    observations = [record[key] for key in ('camera_before', 'camera_after')]
    for item in [stable] + observations:
        if 'fov' not in item:
            raise ValueError('Native camera state is missing the actual Camera.GetFov observation')
        fov = item['fov']
        if (not isinstance(fov, (int, float)) or isinstance(fov, bool)
                or not math.isfinite(fov) or not 0 < fov < 180):
            raise ValueError('Native camera FOV observation is invalid')
    if any(tuple(item['screen']) != tuple(stable['screen']) or
           abs(item['fov'] - stable['fov']) >= .01 for item in observations):
        raise ValueError('Native viewport or reported FOV changed between controls')
    return {'passed': True, 'screen': stable['screen'], 'reported_fov': stable['fov']}


def positive_pixel_controls(paths, liquid_mask, support_mask, threshold, minimum):
    if not 0 <= threshold < 255 or minimum <= 0:
        raise ValueError('Pixel thresholds must be nonnegative and minimum pixels positive')
    frames = {}
    for control in CONTROLS:
        with Image.open(paths[control]) as image:
            frames[control] = image.convert('RGB')
    if any(frame.size != liquid_mask.size for frame in frames.values()) or support_mask.size != liquid_mask.size:
        raise ValueError('Control PNGs and fixed masks must share one native viewport')
    signals, results = {}, {}
    for label, positive, negative, mask in (
            ('liquid_only_vs_empty', 'liquid_only', 'empty', liquid_mask),
            ('supported_vs_support_only', 'supported_positive', 'supported_negative', liquid_mask),
            ('support_only_vs_empty', 'supported_negative', 'empty', support_mask)):
        signal = ImageChops.difference(frames[positive], frames[negative])
        maximum = ImageChops.lighter(ImageChops.lighter(*signal.split()[:2]), signal.split()[2])
        presence = ImageChops.multiply(maximum.point(lambda value: 255 if value > threshold else 0), mask)
        pixels = presence.histogram()[255]
        results[label] = {'positive': positive, 'negative': negative, 'pixels': pixels,
                          'minimum_pixels': minimum, 'threshold': threshold,
                          'valid_positive_signal': pixels >= minimum}
        signals[label] = signal
    results['independent_liquid_signals_passed'] = all(
        results[label]['valid_positive_signal'] for label in ('liquid_only_vs_empty', 'supported_vs_support_only'))
    results.update(support_pixels_can_satisfy_gate=False, native_geometry_accepted=False,
                   public_controls_eligible=False)
    return results, signals


# The raw palette is retained before normalization, including common/extra states.
SNAPSHOT_FUNCTION = '''import json,sys
from modern_projection.projection.cell import AIR,freeze
from modern_projection.projection.world_capture import native_palette_layers
def _liquid_snapshot(palette,positions):
 result={'valid':False,'cells':[],'raw_palette':None}
 if palette is None:
  result['reason']='native_palette_none'
  return result
 source=palette.SerializeBlockPalette()
 result['raw_palette']=freeze(source)
 low=tuple(min(pos[i] for pos in positions) for i in range(3))
 high=tuple(max(pos[i] for pos in positions) for i in range(3))
 size=tuple(high[i]-low[i]+1 for i in range(3))
 result.update(low=low,high=high,size=size)
 try:
  fronts,backs=native_palette_layers(source,size)
 except (ValueError,TypeError) as error:
  result['reason']='native_palette_layers: '+str(error)
  return result
 actors=set(index for entries in source.get('actor',{}).values() for index in entries)
 valid=True
 for pos in positions:
  local=tuple(pos[i]-low[i] for i in range(3))
  index=(local[1]*size[0]+local[0])*size[2]+local[2]
  front,back=fronts.get(index,AIR),backs.get(index,AIR)
  valid=valid and front[0]!='minecraft:unknown' and back[0]!='minecraft:unknown'
  result['cells'].append({'pos':pos,'foreground':front,'background':back,'actor':index in actors})
 result['valid']=valid
 return result
def _liquid_matches(snapshot,positions,front):
 selected=set(tuple(pos) for pos in positions)
 rows=[row for row in snapshot['cells'] if tuple(row['pos']) in selected]
 return (snapshot['valid'] and len(rows)==len(selected) and
  all(tuple(row['foreground'])==tuple(front) and tuple(row['background'])==AIR and not row['actor'] for row in rows))
'''

SERVER_HEADER = '''import mod.server.extraServerApi as api
from modern_projection.server_system import WorldAdapter
from modern_projection.projection.cell import encode,decode
adapter=WorldAdapter(api.GetPlayerList()[0])
def _liquid_server_snapshot(positions):
 low=tuple(min(pos[i] for pos in positions) for i in range(3))
 high=tuple(max(pos[i] for pos in positions) for i in range(3))
 palette=adapter.palette_block.GetBlockPaletteBetweenPos(adapter.dimension,low,high,False)
 result=_liquid_snapshot(palette,positions)
 values=[]
 for pos in positions:
  observed=adapter.read(tuple(pos))
  values.append({'pos':pos,'value':encode(observed) if observed is not None else None})
 result.update(adapter_values=values,dimension=adapter.dimension,runtime=api.GetMinecraftVersion())
 result['valid']=result['valid'] and all(row['value'] is not None for row in values)
 return result
'''


def server_code(body):
    return SNAPSHOT_FUNCTION + SERVER_HEADER + body


def snapshot_code(positions, server=False):
    positions = sorted(set(map(tuple, positions)))
    if server:
        return server_code('positions=json.loads(%r)\n_result=json.dumps(_liquid_server_snapshot(positions))\n' % wire(positions))
    return SNAPSHOT_FUNCTION + '''positions=json.loads(%r)
low=tuple(min(pos[i] for pos in positions) for i in range(3))
high=tuple(max(pos[i] for pos in positions) for i in range(3))
palette=b.factory.CreateBlock(b.level).GetBlockPaletteBetweenPos(low,high,False)
result=_liquid_snapshot(palette,positions)
info=b.factory.CreateBlockInfo(b.level)
reads=[{'pos':pos,'value':info.GetBlock(tuple(pos))} for pos in positions]
result['block_reads']=reads
result['valid']=result['valid'] and all(row['value'] and row['value'][0]!='minecraft:unknown' for row in reads)
result['runtime']=api.GetMinecraftVersion()
_result=json.dumps(result)
''' % wire(positions)


RESERVE = '''plan,token=json.loads(%r),%r
assert not hasattr(sys,'_neighbor_world_saved'),'Existing world reservation must be preserved'
positions=plan['reserved']
before=_liquid_server_snapshot(positions)
reserved=_liquid_matches(before,positions,AIR) and all(decode(row['value'])==AIR for row in before['adapter_values'])
if reserved:
 sys._neighbor_world_saved={'player':adapter.player,'cells':[],'reserved':set(map(tuple,positions)),
  'pure_liquid_plan':plan,'pure_liquid_token':token,'shell_verified':False}
_result=json.dumps({'reserved':reserved,'before':before})
'''

WRITE_SHELL = '''saved=sys._neighbor_world_saved
assert saved['pure_liquid_token']==%r
plan=saved['pure_liquid_plan']
saved['shell_verified']=False
writes=[{'pos':pos,'written':bool(adapter.write(tuple(pos),tuple(plan['shell_value'])))} for pos in plan['shell']]
after=_liquid_server_snapshot(plan['reserved'])
verified=all(row['written'] for row in writes) and _liquid_matches(after,plan['shell'],plan['shell_value'])
saved['shell_verified']=verified
_result=json.dumps({'verified':verified,'writes':writes,'after':after})
'''

WRITE_CONTROL = '''saved=sys._neighbor_world_saved
assert saved['pure_liquid_token']==%r
plan=saved['pure_liquid_plan']
before=_liquid_server_snapshot(plan['reserved'])
assert saved['shell_verified'] and _liquid_matches(before,plan['shell'],plan['shell_value']),'Shell gate failed before liquid seed'
cells=json.loads(%r)
writes=[{'pos':pos,'written':bool(adapter.write(tuple(pos),decode(value),tuple(plan['document_origin'])))} for pos,value in cells]
after=_liquid_server_snapshot(plan['reserved'])
_result=json.dumps({'writes':writes,'before':before,'after':after})
'''

CLEAR_POSITIONS = '''saved=sys._neighbor_world_saved
assert saved['pure_liquid_token']==%r
positions=json.loads(%r)
assert set(map(tuple,positions)).issubset(saved['reserved'])
before=_liquid_server_snapshot(positions)
writes=[{'pos':pos,'written':bool(adapter.write(tuple(pos),AIR))} for pos in positions]
after=_liquid_server_snapshot(positions)
_result=json.dumps({'writes':writes,'before':before,'after':after})
'''

MARKER = '''saved=getattr(sys,'_neighbor_world_saved',None)
owned=saved is not None and saved.get('pure_liquid_token')==%r
_result=json.dumps({'owned':owned,'player_foot':saved.get('player_foot') if owned else None})
'''

RESTORE_PLAYER = '''saved=sys._neighbor_world_saved
assert saved['pure_liquid_token']==%r
point=saved.get('player_foot')
if point is not None:assert api.GetEngineCompFactory().CreatePos(saved['player']).SetFootPos(tuple(point))
_result=json.dumps({'player_foot':point})
'''

DELETE_MARKER = '''assert sys._neighbor_world_saved['pure_liquid_token']==%r
del sys._neighbor_world_saved
_result=True
'''

CAMERA = '''target,offset=%r,%r
position=tuple(target[i]+offset[i] for i in range(3))
direction=api.GetRotFromDir(tuple(target[i]-position[i] for i in range(3)))
rotation=(direction[0],direction[1]+180.,0.)
cam=b.factory.CreateCamera(b.level)
cam.DepartCamera();cam.LockModCameraPitch(True);cam.LockModCameraYaw(True)
assert cam.SetCameraPos(position) and cam.SetCameraRotation(rotation)
_result=json.dumps({'position':position,'rotation':rotation,'target':target})
'''


class NativeHarness:
    def __init__(self, direct, wet, check, args, report, token):
        from _session import load_session
        self.direct, self.wet, self.check, self.args = direct, wet, check, args
        self.report, self.token = report, token
        self.session = load_session(live=True)
        report['session_binding'] = {key: self.session[key] for key in
                                     ('session_file', 'owner', 'game_pid', 'game_identity', 'id')}

    def checkpoint(self):
        self.direct.write_json(self.args.output, self.report)

    def server(self, source):
        return self.direct.run(self.check.client, source)

    def snapshot(self, positions):
        return {'server': self.server(snapshot_code(positions, True)),
                'client': self.check.run(snapshot_code(positions))}

    def reserve(self, plan):
        return self.server(server_code(RESERVE % (wire(plan), self.token)))

    def shell(self):
        return self.server(server_code(WRITE_SHELL % self.token))

    def clear(self, positions):
        return self.server(server_code(CLEAR_POSITIONS % (self.token, wire(positions))))

    def write(self, cells):
        return self.server(server_code(WRITE_CONTROL % (self.token, wire(cells))))

    def settle(self):
        time.sleep(self.args.settle_seconds)

    def frame(self, label, pose):
        return self.direct.capture(self.check, label, pose)

    def marker(self):
        return self.server('import sys,json\n' + MARKER % self.token)

    def restore_player(self):
        return self.server(server_code(RESTORE_PLAYER % self.token))

    def delete_marker(self):
        return self.server('import sys\n' + DELETE_MARKER % self.token)


def clear_cavity(harness, plan, row):
    row['clear_cavity'] = harness.clear(plan['cavity'])
    harness.checkpoint()
    harness.settle()
    row['cavity_after_clear'] = harness.snapshot(plan['reserved'])
    harness.checkpoint()
    if not all(matches(row['cavity_after_clear'][side], [], plan['cavity']) for side in ('server', 'client')):
        raise RuntimeError('Native cavity did not clear in both layers; containment retained')


def capture_control(harness, plan, control, row, pose, expected_size):
    requested = plan['controls'][control]['cells']
    row.update(control=control, requested=plan['controls'][control], completed=False,
               corners=[{'corner': corner, 'status': 'unobservable',
                         'reason': 'no_reliable_corner_assignment_in_changed_context'}
                        for corner in ((0, 0), (1, 0), (1, 1), (0, 1))])
    harness.checkpoint()
    try:
        clear_cavity(harness, plan, row)
        row['write'] = harness.write(requested)
        harness.checkpoint()
        if not all(item['written'] for item in row['write']['writes']):
            raise RuntimeError('Native control write failed; requested values were not retried')
        harness.settle()
        row['native_before_capture'] = harness.snapshot(plan['reserved'])
        harness.checkpoint()
        try:
            row['capture'] = harness.frame(plan['case'] + '_' + control, pose)
            harness.checkpoint()
            row['fixed_viewport'] = fixed_viewport(row['capture'], pose)
            row['png_validation'] = validate_png(row['capture'], harness.session, expected_size)
        except Exception as error:
            row['capture_error'] = '%s: %s' % (type(error).__name__, error)
            raise
        finally:
            row['native_after_capture'] = harness.snapshot(plan['reserved'])
            row['native_gate'] = capture_native_gate(row['native_before_capture'], row['native_after_capture'],
                                                    plan, requested)
            harness.checkpoint()
        row['completed'] = True
    except Exception as error:
        row['error'] = '%s: %s' % (type(error).__name__, error)
        label = plan['case'] + '_' + control
        candidate = harness.args.output.with_name(harness.args.output.stem + '_' + label + '_native.png')
        row['failed_capture_artifacts'] = [str(path.resolve()) for path in
                                           (candidate, candidate.with_suffix('.capture.json'),
                                            candidate.with_suffix('.capture_error.json')) if path.exists()]
        raise
    finally:
        harness.checkpoint()


def cleanup_containment(harness, plan, report):
    cleanup = {'restored': False, 'containment_retained': True, 'steps': [], 'player_foot': None}
    owned = player_restored = False
    report['contained_cleanup'] = cleanup
    harness.checkpoint()
    try:
        marker = harness.marker()
        cleanup['ownership'] = marker
        owned = marker['owned']
        if not marker['owned']:
            cleanup.update(restored=True, containment_retained=False, no_owned_reservation=True)
            return cleanup
        cleanup['player_foot'] = marker['player_foot']
        # Clear every nonshell reserved cell while the walls still contain ticks.
        nonshell = sorted(set(map(tuple, plan['reserved'])) - set(map(tuple, plan['shell'])))
        cleanup['steps'].append({'clear_nonshell': harness.clear(nonshell)})
        harness.checkpoint()
        for label in ('nonshell_first', 'nonshell_second'):
            harness.settle()
            sample = harness.snapshot(plan['reserved'])
            cleanup['steps'].append({label: sample})
            harness.checkpoint()
            if not all(matches(sample[side], [], nonshell) for side in ('server', 'client')):
                raise RuntimeError('Native foreground/background residue; shell removal refused')
        cleanup['steps'].append({'clear_shell': harness.clear(plan['shell'])})
        cleanup['containment_retained'] = False
        harness.checkpoint()
        for label in ('reservation_first', 'reservation_second'):
            harness.settle()
            sample = harness.snapshot(plan['reserved'])
            cleanup['steps'].append({label: sample})
            harness.checkpoint()
            if not all(matches(sample[side], [], plan['reserved']) for side in ('server', 'client')):
                raise RuntimeError('Native reservation restoration could not be verified')
        cleanup['steps'].append({'player_restore': harness.restore_player()})
        player_restored = True
        harness.delete_marker()
        cleanup['restored'] = True
        return cleanup
    except Exception as error:
        cleanup['error'] = '%s: %s' % (type(error).__name__, error)
        raise
    finally:
        if owned and not player_restored:
            try:
                cleanup['steps'].append({'recovery_player_restore': harness.restore_player()})
            except Exception as error:
                cleanup['recovery_player_error'] = '%s: %s' % (type(error).__name__, error)
        harness.checkpoint()


def execute_controls(harness, options, runtime_args, report):
    direct, wet, check = harness.direct, harness.wet, harness.check
    source = tuple(options.cell_origin)
    offset = tuple(VISUAL_CASE['camera']['world_offset'])
    supported = source_document(options.case[0], isolated=True)
    cells = [(tuple(source[i] + pos[i] - VISUAL_CASE['focus'][i] for i in range(3)), encode(value))
             for pos, value in supported.blocks.items()]
    platform = wet.camera_side_platform(cells, offset)
    plan = fixture_plan(options.case[0], source, platform, options.shell_block)
    report.update(schema=1, method='Four native controls in a fixed sealed ' + options.shell_block + ' shell',
                  fixture=VISUAL_CASE['fixture'], context_changed=True, public_controls_eligible=False,
                  native_geometry_accepted=False, native_shape_acceptance='pending', accuracy_accepted=False,
                  registry_version=VISUAL_CASE['registry_version'],
                  registry_fingerprint=VISUAL_CASE['registry_fingerprint'],
                  runner_source=direct.fingerprint(Path(__file__)),
                  public_fixture_source=direct.fingerprint(ROOT / 'behavior_pack/modern_projection/projection/debug_liquid_blueprints.py'),
                  cases=[], containment=plan,
                  limits='Added sealed shell changes the public context. No tick freeze, corner assignment, height rule, camera fit or production geometry.')
    report.pop('native_aabb_reference', None)
    harness.checkpoint()
    report['world_setup'] = harness.reserve(plan)
    harness.checkpoint()
    if not report['world_setup']['reserved']:
        raise RuntimeError('Reservation is not verified native foreground/background air')
    report['shell_setup'] = harness.shell()
    harness.checkpoint()
    if not report['shell_setup']['verified']:
        raise RuntimeError('Incomplete shell prevents liquid seeding')
    report['near_player'] = harness.server(wet.NEAR_PLAYER % (platform,))
    report['near_player']['client'] = direct.world.player_ready(check, report['near_player']['after'])
    target = tuple(source[i] + .5 for i in range(3))
    pose = check.run(CAMERA % (target, offset))
    harness.settle()
    pose['stable'] = check.run(direct.native.CAMERA_STATE)
    actual_player = check.run('_result=json.dumps(b.player_position.GetFootPos())')
    report['player_camera_side'] = wet.player_camera_side(actual_player, pose)
    report['camera'] = pose
    harness.checkpoint()
    if not report['player_camera_side']['passed']:
        raise RuntimeError('Native player is on the opposite camera side')
    expected_size = None
    for case in options.case:
        case_plan = fixture_plan(case, source, platform, options.shell_block)
        row = {'case': case, 'source': case_plan, 'controls': {}, 'completed': False,
               'context_changed': True, 'public_controls_eligible': False, 'native_geometry_accepted': False}
        report['cases'].append(row)
        harness.checkpoint()
        for control in CONTROLS:
            control_row = row['controls'][control] = {}
            capture_control(harness, case_plan, control, control_row, pose, expected_size)
            expected_size = control_row['png_validation']['size']
        below = (source[0], source[1] - 1, source[2])
        above = (source[0], source[1] + 1, source[2])
        projection = check.run(direct.ROIS % ([source, below, above], target))
        upper_projection = copy.deepcopy(projection)
        roi_masks = direct.world.bounded._roi_masks
        remaining, support_mask, roi = roi_masks(
            projection, expected_size, source, below, runtime_args.calibration, boundary_guard=BOUNDARY_GUARD)
        remaining_above, unused_hidden, upper_roi = roi_masks(
            upper_projection, expected_size, source, above, runtime_args.calibration, boundary_guard=BOUNDARY_GUARD)
        liquid_mask = ImageChops.multiply(remaining, remaining_above)
        row['fixed_roi'] = {'source': roi, 'upper_exclusions': upper_roi, 'boundary_guard_pixels': BOUNDARY_GUARD,
                            'liquid_area': liquid_mask.histogram()[255], 'shell_is_declared_context': True}
        paths = {control: row['controls'][control]['capture']['path'] for control in CONTROLS}
        row['pixel_controls'], signals = positive_pixel_controls(
            paths, liquid_mask, support_mask, runtime_args.threshold, runtime_args.min_pixels)
        row['signals'] = {}
        for label, signal in signals.items():
            path = runtime_args.output.with_name(runtime_args.output.stem + '_' + case + '_' + label + '_signal.png')
            signal.save(path)
            row['signals'][label] = direct.fingerprint(path)
        row['declared_context_controls_passed'] = (
            row['pixel_controls']['independent_liquid_signals_passed'] and
            all(item['native_gate']['declared_context_state_passed'] for item in row['controls'].values()))
        row['completed'] = True
        harness.checkpoint()
    report['completed'] = True
    report['declared_context_controls_passed'] = all(row['declared_context_controls_passed'] for row in report['cases'])
    harness.checkpoint()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--case', action='append', choices=CASES,
                        help='Repeat at most once for each source case; default water')
    parser.add_argument('--cell-origin', type=int, nargs=3, required=True,
                        help='Explicit world minimum corner of the source cell; reservation must be air')
    parser.add_argument('--capture-helper', type=Path, required=True)
    parser.add_argument('--camera-calibration', type=Path, required=True)
    parser.add_argument('--shell-block', choices=('glass', 'barrier'), default='glass',
                        help='Diagnostic containment material; both change the public context')
    parser.add_argument('--threshold', type=int, default=16)
    parser.add_argument('--min-pixels', type=int, default=80)
    parser.add_argument('--settle-seconds', type=float, default=.35)
    options = parser.parse_args(argv)
    options.case = options.case or [CASES[0]]
    if len(options.case) > 2 or len(set(options.case)) != len(options.case):
        parser.error('Each of the two source cases can be captured only once')
    if options.output.exists():
        parser.error('Choose a fresh report path')
    if any(options.output.parent.glob(options.output.stem + '_*')):
        parser.error('Choose a report prefix without earlier capture or signal artifacts')
    if options.settle_seconds < .35 or not options.settle_seconds < 10:
        parser.error('Settle seconds must be at least .35 and below 10')
    if not 0 <= options.threshold < 255 or options.min_pixels <= 0:
        parser.error('Invalid pixel threshold or minimum pixels')
    import verify_dripstone_direct_seed as direct
    originals = (direct.world.CASES, direct.native.VIEWS, direct.native.VISUAL_CASES, direct.world.BlueprintCheck)
    import verify_wet_actor_visuals as wet
    direct.world.CASES, direct.native.VIEWS, direct.native.VISUAL_CASES, direct.world.BlueprintCheck = originals
    saved_execute, saved_clear, saved_argv = direct.execute, direct.world.clear_world, sys.argv
    active = {}
    token = uuid.uuid4().hex

    def execute(check, args, report):
        args.settle_seconds = options.settle_seconds
        harness = NativeHarness(direct, wet, check, args, report, token)
        plan = fixture_plan(options.case[0], options.cell_origin,
                            wet.camera_side_platform([(tuple(options.cell_origin), None),
                                                      ((options.cell_origin[0], options.cell_origin[1] - 1,
                                                        options.cell_origin[2]), None)],
                                                     VISUAL_CASE['camera']['world_offset']),
                            options.shell_block)
        active.update(harness=harness, plan=plan, report=report)
        execute_controls(harness, options, args, report)

    def clear_world(client):
        if not active:
            return {'restored': True, 'player_foot': None, 'no_owned_reservation': True}
        result = cleanup_containment(active['harness'], active['plan'], active['report'])
        if not result['restored']:
            raise RuntimeError('Native containment restoration was not verified')
        return result

    try:
        direct.execute, direct.world.clear_world = execute, clear_world
        sys.argv = [str(Path(__file__)), str(options.output), '--capture-helper', str(options.capture_helper),
                    '--camera-calibration', str(options.camera_calibration), '--threshold', str(options.threshold),
                    '--min-pixels', str(options.min_pixels), '--background-only']
        return direct.main()
    finally:
        direct.execute, direct.world.clear_world, sys.argv = saved_execute, saved_clear, saved_argv


if __name__ == '__main__':
    raise SystemExit(main())
