"""Compare connected world blocks and bounded projections at identical poses.

Run in an owned disposable managed world through run_live_check.py. Reserve
confirmed air, write explicit snapshots through WorldAdapter, verify native
client replication, and restore world/camera/editor/observers in finally.
"""
import argparse
import hashlib
import json
import os
import time
from pathlib import Path

from PIL import Image, ImageDraw

import verify_context_batch_visuals as bounded
from context_test_environment import run, SETUP, RESTORE as RESTORE_ENVIRONMENT
from verify_debug_blueprints import BlueprintCheck, Client, INSTALL_PROBE, RESTORE, write_json
from verify_debug_visuals import SAVE_VISUAL, camera_restore_code

native = bounded.native
CELL_HEIGHT = 1.6
CASES = tuple(bounded.METADATA['cells']) + tuple(
    family + '_cross_chunk' for family in bounded.METADATA['cross_chunk_cells'])

CAPTURE_OPTIONS = '''view=b.factory.CreatePlayerView(b.level)
option=api.GetMinecraftEnum().OptionId.RENDER_CLOUDS
assert not hasattr(sys,'_neighbor_visual_options_saved')
saved=view.GetToggleOption(option)
assert saved in (0,1), saved
sys._neighbor_visual_options_saved=saved
assert view.SetToggleOption(option,False)
assert view.GetToggleOption(option)==0
_result=json.dumps({'clouds_before':saved,'clouds_during_capture':0})
'''

RESTORE_OPTIONS = '''view=b.factory.CreatePlayerView(b.level)
option=api.GetMinecraftEnum().OptionId.RENDER_CLOUDS
saved=sys._neighbor_visual_options_saved
assert view.SetToggleOption(option,bool(saved))
assert view.GetToggleOption(option)==saved
del sys._neighbor_visual_options_saved
_result=True
'''

RESERVE = '''import mod.server.extraServerApi as api
import sys,json
from modern_projection.server_system import WorldAdapter
from modern_projection.projection.cell import AIR
player=api.GetPlayerList()[0]
adapter=WorldAdapter(player)
source=%r
supports=%r
cells=supports+source
reserved=set(tuple(pos[i]+offset[i] for i in range(3)) for pos,value in cells
             for offset in ((0,0,0),(-1,0,0),(1,0,0),(0,-1,0),(0,1,0),(0,0,-1),(0,0,1)))
assert not hasattr(sys,'_neighbor_world_saved')
for pos in reserved:assert adapter.read(pos)==AIR, (pos,adapter.read(pos))
sys._neighbor_world_saved={'player':player,'cells':cells,'reserved':reserved}
for pos,value in cells:assert adapter.write(pos,tuple(value)), (pos,value)
actual=[(pos,adapter.read(pos)) for pos,value in cells]
for (pos,value),(actual_pos,observed) in zip(cells,actual):
 assert observed is not None and observed[0]==value[0], (pos,value,observed)
_result=json.dumps({'cells':len(cells),'reserved':len(reserved),'verified':True,'actual':actual})
'''

CLEAR = '''import mod.server.extraServerApi as api
import sys
from modern_projection.server_system import WorldAdapter
from modern_projection.projection.cell import AIR
saved=sys._neighbor_world_saved
adapter=WorldAdapter(saved['player'])
player_foot=saved.get('player_foot')
if player_foot is not None:
 assert api.GetEngineCompFactory().CreatePos(saved['player']).SetFootPos(tuple(player_foot))
for pos,value in reversed(saved['cells']):
 if adapter.read(pos)!=AIR:assert adapter.write(pos,AIR), pos
for pos in saved['reserved']:
 if adapter.read(pos)!=AIR:assert adapter.write(pos,AIR),pos
for pos in saved['reserved']:assert adapter.read(pos)==AIR, (pos,adapter.read(pos))
del sys._neighbor_world_saved
_result=json.dumps({'restored':True,'player_foot':player_foot})
'''

CLEAR_SOURCE = '''import sys
from modern_projection.server_system import WorldAdapter
from modern_projection.projection.cell import AIR
saved=sys._neighbor_world_saved
adapter=WorldAdapter(saved['player'])
cells=%r
for pos,value in cells:
 if adapter.read(pos)!=AIR:assert adapter.write(pos,AIR), pos
for pos,value in cells:assert adapter.read(pos)==AIR,(pos,adapter.read(pos))
_result=True
'''

NEAR_PLAYER = '''import sys,json
import mod.server.extraServerApi as api
from modern_projection.server_system import WorldAdapter
from modern_projection.projection.cell import AIR
saved=sys._neighbor_world_saved
adapter=WorldAdapter(saved['player'])
position=api.GetEngineCompFactory().CreatePos(saved['player'])
assert 'player_foot' not in saved
saved['player_foot']=position.GetFootPos()
source=%r
lo=tuple(min(pos[i] for pos,value in source) for i in range(3))
platform=(lo[0]-4,lo[1]-1,lo[2]-4)
assert adapter.read(platform)==AIR,(platform,adapter.read(platform))
saved['reserved'].add(platform)
assert adapter.write(platform,('minecraft:stone',0))
point=(platform[0]+.5,platform[1]+1.,platform[2]+.5)
assert position.SetFootPos(point)
_result=json.dumps({'before':saved['player_foot'],'after':point,'platform':platform})
'''

WRITE_SUPPORTS = '''import sys
from modern_projection.server_system import WorldAdapter
saved=sys._neighbor_world_saved
adapter=WorldAdapter(saved['player'])
cells=%r
for pos,value in cells:assert adapter.write(pos,tuple(value)),(pos,value)
_result=True
'''

SUPPORT_CONTEXT = '''supports=%r
origin=tuple(s.origin)
cells=[]
for world,value in supports:
 pos=tuple(world[i]-origin[i] for i in range(3))
 assert all(0<=pos[i]<s.editor.document.size[i] for i in range(3)),pos
 s.editor.document.blocks[pos]=tuple(value)
 sys._neighbor_qa_occupied.add(pos)
 cells.append((pos,value))
sys._neighbor_qa_document=s.editor.document.blocks.copy()
_result=json.dumps({'cells':cells,'rendered':False,'native_context':True})
'''

REPLICATION = '''from modern_projection.projection.model import Document
from modern_projection.projection.world_capture import merge_palette
from modern_projection.projection.cell import foreground
from modern_projection.projection.block_registry import canonical
cells=%r
empty=%r
lo=tuple(min(pos[i] for pos,value in cells) for i in range(3))
hi=tuple(max(pos[i] for pos,value in cells) for i in range(3))
size=tuple(hi[i]-lo[i]+1 for i in range(3))
palette=b.factory.CreateBlock(b.level).GetBlockPaletteBetweenPos(lo,hi,False)
matches=False
actual=[]
if palette is not None:
 doc=Document(size)
 merge_palette(doc,palette.SerializeBlockPalette(),(0,0,0),size,lo)
 actual=[(tuple(pos[i]+lo[i] for i in range(3)),foreground(value)) for pos,value in doc.blocks.items()]
 expected=[] if empty else [(tuple(pos),canonical(tuple(value))) for pos,value in cells]
 matches=sorted((pos,value[0]) for pos,value in actual)==sorted((pos,value[0]) for pos,value in expected)
_result=json.dumps({'matches':matches,'cells':actual})
'''


def replication(check, cells, empty):
    return check.wait('client world palette replication', lambda value: value['matches'],
                      lambda: check.run(REPLICATION % (cells, empty)))


def camera_capture(check, label, keep, occupied, view):
    pose = native.select_view(check, keep, occupied, view, None)
    time.sleep(.35)
    return pose, check.capture(label)


def review_sheet(report, output):
    rows = [(row, view, frames) for row in report['cases']
            for view, frames in row.get('views', {}).items() if 'context' in frames]
    if not rows:
        return
    sheet = Image.new('RGB', (1920, len(rows) * 320 + 32), '#f4f5f6')
    draw = ImageDraw.Draw(sheet)
    draw.text((8, 8), 'Actual screenshots: world | all-air projection | dynamic occupied | initial occupied', fill='black')
    for index, (row, view, frames) in enumerate(rows):
        captures = (frames['world'], frames['context']['shown'],
                    row['dynamic']['views'][view]['capture']['shown'],
                    row['initial']['views'][view]['capture']['shown'])
        for column, capture in enumerate(captures):
            with Image.open(capture['path']).convert('RGB') as frame:
                frame.thumbnail((480, 266))
                sheet.paste(frame, (column * 480, index * 320 + 60))
        dynamic = row['dynamic']['views'][view]['pixels']
        initial = row['initial']['views'][view]['pixels']
        label = '%s/%s guard=%s: dynamic residual=%.4f, initial residual=%.4f; passed=%s' % (
            row['case'], view, frames['roi']['neighbor_boundary_guard_pixels'],
            dynamic['hidden_residual'], initial['hidden_residual'], row['passed'])
        draw.text((8, index * 320 + 40), label, fill='black')
    path = output.with_name(output.stem + '_review_sheet.png')
    sheet.save(path)
    report['review_sheet'] = {'path': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def replay(args):
    report = json.loads(args.replay.read_text(encoding='utf8'))
    assert report['completed'] and report['restored'], report
    for row in report['cases']:
        keep, occupied = tuple(row['keep']), tuple(row['occupied'])
        origin = row['source']['origin']
        for view, frames in row['views'].items():
            calibration = args.calibration
            details = frames['roi']['projection']
            projection = dict(position=details['position'], rotation=details['rotation'],
                              target=details['target'], fov=details['fov_degrees'],
                              screen=details['screen'], projection_method=details['method'],
                              runtime_minecraft_version=calibration['runtime_minecraft_version'], cells=[])
            for pos, value in row['source']['cells']:
                points = [tuple(origin[i] + pos[i] + offset[i] for i in range(3))
                          for offset in ((x, y, z) for x in (0., 1.)
                                         for y in (0., row.get('cell_height', 1.6)) for z in (0., 1.))]
                projection['cells'].append({'pos': pos, 'world_points': points})
            for capture in (frames['world'], frames['empty']):
                assert hashlib.sha256(Path(capture['path']).read_bytes()).hexdigest() == capture['sha256'], capture
            baseline = native.signal(frames['world']['path'], frames['empty']['path'])
            first, second, record = native.roi_masks(projection, baseline.size, keep, occupied, calibration)
            masks = first, second
            frames['roi'] = record
            if 'support_positive_control' in frames:
                control = frames['support_positive_control']
                for capture in (control['shown'], control['hidden']):
                    assert hashlib.sha256(Path(capture['path']).read_bytes()).hexdigest() == capture['sha256'], capture
                support_signal = native.signal(control['shown']['path'], control['hidden']['path'])
                support_mask, polygons = support_roi(projection, baseline.size, row['native_supports'])
                control['pixels'] = native.count(native.ImageChops.multiply(
                    native.binary(native.maximum(support_signal), args.threshold), support_mask))
                control['cell_hulls'] = polygons
                control['passed'] = control['pixels'] >= args.min_pixels
            context = frames['context']
            for capture in (context['shown'], context['actor_hidden']):
                assert hashlib.sha256(Path(capture['path']).read_bytes()).hexdigest() == capture['sha256'], capture
            complete = native.signal(context['shown']['path'], context['actor_hidden']['path'])
            frames['context_matches_world'] = native.compare_complete(baseline, complete, masks, args.threshold, args.min_pixels)
            for stage in ('dynamic', 'initial'):
                item = row[stage]['views'][view]
                for capture in (item['capture']['shown'], item['capture']['actor_hidden']):
                    assert hashlib.sha256(Path(capture['path']).read_bytes()).hexdigest() == capture['sha256'], capture
                actual = native.signal(item['capture']['shown']['path'], item['capture']['actor_hidden']['path'])
                prefix = args.output.with_name(args.output.stem + '_' + row['case'] + '_' + view + '_' + stage)
                item['pixels'] = native.compare_pixels(baseline, actual, masks, prefix, args.min_pixels, args.threshold)
        row['passed'] = (all(item['context_matches_world']['passed'] and
                             item.get('support_positive_control', {'passed': True})['passed']
                             for item in row['views'].values()) and
                         all(item['pixels']['passed'] for stage in ('dynamic', 'initial')
                             for item in row[stage]['views'].values()))
    report['replay_source'] = {'path': str(args.replay.resolve()),
                               'sha256': hashlib.sha256(args.replay.read_bytes()).hexdigest()}
    report['passed'] = all(row['passed'] for row in report['cases'])
    review_sheet(report, args.output)
    write_json(args.output, report)
    print(json.dumps({'completed': True, 'passed': report['passed'], 'replayed': str(args.replay),
                      'cases': {row['case']: row['passed'] for row in report['cases']}}))
    return 0 if report['passed'] else 1


def clear_world(client):
    return run(client, 'import sys\n_result={"restored":True,"player_foot":None}\n'
               'if hasattr(sys,"_neighbor_world_saved"):\n' +
               '\n'.join(' ' + line for line in CLEAR.splitlines()))


def player_ready(check, point):
    return check.wait('client player position',
                      lambda value: all(abs(value[i] - point[i]) < .2 for i in range(3)),
                      lambda: check.run('_result=json.dumps(b.player_position.GetFootPos())'))


def case(check, label, args, row):
    try:
        return world_case(check, label, args, row)
    finally:
        restored = clear_world(check.client)
        if restored.get('player_foot') is not None:
            player_ready(check, restored['player_foot'])
        row['world_cleanup'] = restored
        row['world_restored'] = True


def native_supports(cells):
    return [(tuple(pos[i] - (i == 1) for i in range(3)), ('minecraft:stone', 0))
            for pos, value in cells if value[0] == 'minecraft:rail']


def support_roi(projection, size, supports):
    details = projection['projection_details']
    assert details['method'] != 'native', 'This support control needs the calibrated NEMC 3.9 camera'
    mask = Image.new('L', size)
    scale = size[0] / details['screen'][0], size[1] / details['screen'][1]
    polygons = []
    for pos, value in supports:
        corners = [tuple(pos[i] + offset[i] for i in range(3))
                   for offset in ((x, y, z) for x in (0., 1.) for y in (0., 1.) for z in (0., 1.))]
        points = native.project_box_corners(corners, details['position'], details['target'],
                                           details['screen'], details['effective_vertical_fov'],
                                           details['rotation'][2])
        polygon = native.hull((point['screenX'] * scale[0], point['screenY'] * scale[1]) for point in points)
        assert polygon, (pos, details)
        ImageDraw.Draw(mask).polygon(polygon, fill=255)
        polygons.append({'position': pos, 'polygon': polygon})
    return mask, polygons


def world_case(check, label, args, row):
    keep, occupied = native.VISUAL_CASES[label]
    before = native.prepare_case(check, keep, occupied, args.opacity)
    source = check.run('from modern_projection.projection.cell import foreground\n'
                       '_result=json.dumps({"origin":s.origin,"cells":'
                       '[(pos,foreground(value)) for pos,value in s.editor.document.blocks.items()]})')
    cells = [(tuple(source['origin'][i] + pos[i] for i in range(3)), tuple(value))
             for pos, value in source['cells']]
    row.update(keep=keep, occupied=occupied, source=source, fixture=before,
               cell_height=CELL_HEIGHT, views={})
    check.run('b.stop_projection()\n_result=True')
    supports = native_supports(cells)
    row['native_supports'] = supports
    world_frames = {}
    row['world_setup'] = run(check.client, RESERVE % (cells, supports))
    row['near_player'] = run(check.client, NEAR_PLAYER % (cells,))
    row['near_player']['client'] = player_ready(check, row['near_player']['after'])
    row['world_replication'] = replication(check, cells, False)
    # Capture persistent wall/rail states after native placement. Rail supports
    # remain in every shown/hidden frame, so subtraction isolates the rails.
    captured = row['world_replication']['cells']
    actual_values = dict((tuple(pos), tuple(value)) for pos, value in captured)
    row['world_state_changes'] = [dict(position=pos, requested=value,
                                     actual=actual_values[pos])
                                 for pos, value in cells
                                 if value != actual_values[pos]]
    check.run('origin=tuple(s.origin)\n'
              'captured=%r\n'
              'for pos,value in captured:\n'
              ' s.editor.document.blocks[tuple(pos[i]-origin[i] for i in range(3))]=tuple(value)\n'
              'sys._neighbor_qa_document=s.editor.document.blocks.copy()\n_result=True' % captured)
    for view in args.view:
        pose, shown = camera_capture(check, label + '_' + view + '_world', keep, occupied, view)
        world_frames[view] = shown
        row['views'][view] = {'camera': pose, 'world': shown}
    run(check.client, CLEAR_SOURCE % (cells,))
    row['world_cleared'] = replication(check, cells, True)
    masks, baselines = {}, {}
    for view, shown in world_frames.items():
        pose, empty = camera_capture(check, label + '_' + view + '_empty', keep, occupied, view)
        baseline = native.signal(shown['path'], empty['path'])
        baseline_path = args.output.with_name(args.output.stem + '_' + label + '_' + view + '_world_signal.png')
        baseline.save(baseline_path)
        projection = check.run(native.CELL_ROIS)
        keep_roi, hidden_roi, roi_record = native.roi_masks(
            projection, baseline.size, keep, occupied, args.calibration)
        baselines[view], masks[view] = baseline, (keep_roi, hidden_roi)
        row['views'][view].update(empty=empty, roi=roi_record, world_signal=str(baseline_path.resolve()))
        if supports:
            run(check.client, CLEAR_SOURCE % (supports,))
            replication(check, supports, True)
            pose, support_hidden = camera_capture(check, label + '_' + view + '_support_hidden', keep, occupied, view)
            control = native.signal(empty['path'], support_hidden['path'])
            mask, polygons = support_roi(projection, baseline.size, supports)
            control_pixels = native.count(native.ImageChops.multiply(
                native.binary(native.maximum(control), args.threshold), mask))
            row['views'][view]['support_positive_control'] = {
                'shown': empty, 'hidden': support_hidden, 'pixels': control_pixels,
                'cell_hulls': polygons,
                'minimum_pixels': args.min_pixels, 'passed': control_pixels >= args.min_pixels}
            run(check.client, WRITE_SUPPORTS % (supports,))
            replication(check, supports, False)
            assert control_pixels >= args.min_pixels, row['views'][view]['support_positive_control']
    # Real supports influence native tessellation even when they are occupied
    # and therefore absent from the missing-only projection's rendered cells.
    row['support_context'] = check.run(SUPPORT_CONTEXT % (supports,))
    check.run('b.project()\n_result=True')
    initial_air = native.projection_ready(check, occupied)
    assert initial_air['state'] == 1, initial_air
    row['context_all_air'] = initial_air
    for view in world_frames:
        native.select_view(check, keep, occupied, view, None)
        context, capture = native.capture_signal(check, label + '_' + view + '_context', occupied)
        comparison = native.compare_complete(baselines[view], context, masks[view],
                                             args.threshold, args.min_pixels)
        row['views'][view].update(context=capture, context_matches_world=comparison)
    check.run('sys._neighbor_qa_occupied.add(%r)\nb.projection_occupancy.read(%r)\n_result=True' %
              (occupied, occupied))
    for stage in ('dynamic', 'initial'):
        if stage == 'initial':
            check.run('b.project()\n_result=True')
        state = native.projection_ready(check, occupied,
                                        initial_air['commits'] + 1 if stage == 'dynamic' else None)
        assert state['state'] == 2, state
        row[stage] = {'projection': state, 'views': {}}
        for view in world_frames:
            native.select_view(check, keep, occupied, view, None)
            actual, capture = native.capture_signal(check, label + '_' + view + '_' + stage, occupied)
            prefix = args.output.with_name(args.output.stem + '_' + label + '_' + view + '_' + stage)
            pixels = native.compare_pixels(baselines[view], actual, masks[view], prefix,
                                           args.min_pixels, args.threshold)
            row[stage]['views'][view] = {'capture': capture, 'pixels': pixels}
    row['passed'] = (all(value['context_matches_world']['passed'] and
                         value.get('support_positive_control', {'passed': True})['passed']
                         for value in row['views'].values()) and
                     all(value['pixels']['passed'] for stage in ('dynamic', 'initial')
                         for value in row[stage]['views'].values()))
    row['completed'] = True
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--case', action='append', choices=CASES)
    parser.add_argument('--view', action='append', choices=native.VIEWS)
    parser.add_argument('--camera-calibration', type=Path, required=True)
    parser.add_argument('--replay', type=Path, help='Reanalyze preserved and hash-checked native captures')
    parser.add_argument('--opacity', type=float, default=1.)
    parser.add_argument('--threshold', type=int, default=16)
    parser.add_argument('--min-pixels', type=int, default=80)
    parser.add_argument('--timeout', type=float, default=90.)
    args = parser.parse_args()
    args.view = args.view or ['side']
    args.calibration = json.loads(args.camera_calibration.read_text(encoding='utf8'))
    if args.replay is not None:
        expected_session = json.loads(args.replay.read_text(encoding='utf8'))['session_file']
        assert expected_session and args.calibration.get('session_file') and \
            Path(args.calibration['session_file']).resolve() == Path(expected_session).resolve(), \
            'Calibration belongs to another instance'
        os.environ['MCDEV_SESSION_FILE'] = expected_session
        return replay(args)
    report = {'schema': 1, 'completed': False, 'passed': False, 'cases': [],
              'session_file': os.environ.get('MCDEV_SESSION_FILE'),
              'owner': os.environ.get('MCDEV_OWNER'),
              'fixture': native.FIXTURE,
              'scope': 'Real world native blocks versus bounded client projection at identical position/camera',
              'occupancy_source': 'Temporary client observation replacement after world baseline is cleared',
              'limits': 'Unchanged missing-neighbor pixel contracts; camera calibrated in this session'}
    installed = visual = observer = environment = options = False
    try:
        with Client(timeout=30) as client:
            check = BlueprintCheck(client, args.output, args.timeout)
            try:
                run(client, SETUP)
                environment = True
                check.run(INSTALL_PROBE)
                installed = True
                check.run(SAVE_VISUAL)
                visual = True
                options = True
                report['capture_options'] = check.run(CAPTURE_OPTIONS)
                check.run(native.INSTALL_OBSERVER)
                observer = True
                check.page()
                for label in args.case or CASES:
                    row = {'case': label, 'completed': False, 'passed': False}
                    report['cases'].append(row)
                    case(check, label, args, row)
                    write_json(args.output, report)
                    print(json.dumps({'case': label, 'passed': row['passed'],
                                      'context': {view: value['context_matches_world']
                                                  for view, value in row['views'].items()},
                                      'dynamic': {view: value['pixels'] for view, value in row['dynamic']['views'].items()}}),
                          flush=True)
                    check.run('b.stop_projection()\n_result=True')
                    check.run(camera_restore_code(False))
                report['completed'] = True
                report['passed'] = all(row['passed'] for row in report['cases'])
            finally:
                errors = []
                cleanup = []
                if visual:
                    cleanup.extend((('projection', 'b.stop_projection()\n_result=True'),
                                    ('camera', camera_restore_code(False)),
                                    ('fields', 'saved=sys._blueprint_visual_saved\n'
                                     's.origin=saved["origin"]\ns.opacity=saved["opacity"]\n'
                                     's.projection_missing=saved["missing"]\ns.projection_outline=saved["outline"]\n'
                                     'del sys._blueprint_visual_saved\n_result=True')))
                if observer:
                    cleanup.append(('observer', native.RESTORE_OBSERVER))
                if installed:
                    cleanup.append(('editor', RESTORE))
                if options:
                    cleanup.append(('options', RESTORE_OPTIONS))
                for label, code in cleanup:
                    try:
                        check.run(code)
                    except Exception as error:
                        errors.append('%s: %s' % (label, error))
                try:
                    clear_world(client)
                except Exception as error:
                    errors.append('world: %s' % error)
                if environment:
                    try:
                        run(client, RESTORE_ENVIRONMENT)
                    except Exception as error:
                        errors.append('environment: %s' % error)
                report['restored'] = not errors
                report['cleanup_errors'] = errors
    except Exception as error:
        report['error'] = '%s: %s' % (type(error).__name__, error)
        raise
    finally:
        if report['completed']:
            review_sheet(report, args.output)
        write_json(args.output, report)
    print(json.dumps({'completed': report['completed'], 'passed': report['passed'],
                      'restored': report['restored'], 'cases': len(report['cases'])}))
    return 0 if report['completed'] and report['passed'] and report['restored'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
