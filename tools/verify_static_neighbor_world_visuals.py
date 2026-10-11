"""Compare fixed public gate and chorus cells with native world controls."""
import verify_neighbor_world_visuals as world
import hashlib
import json
from pathlib import Path
import shutil
from projection.debug_connection_blueprints import VISUAL_CASE

native = world.native
rows = dict((row['id'], row) for row in VISUAL_CASE['cases'])
native.FIXTURE = VISUAL_CASE['fixture']
native.VIEWS = ('side',)
native.VISUAL_CASES = dict((identity, (row['keep'], row['occupied'])) for identity, row in rows.items())
world.CASES = tuple(rows)
world.CELL_HEIGHT = VISUAL_CASE['cell_hull_height']
native.CELL_ROIS = native.CELL_ROIS.replace('(0.,1.6)', '(0.,1.)')
native.CROP_FIXTURE = '''from modern_projection.projection.cell import AIR
keep=%r
neighbor=%r
cases=%r
row=next(value for value in cases if value['keep']==keep and value['occupied']==neighbor)
doc=s.editor.document
allowed=set(row['cells'])
for pos in tuple(doc.blocks):
 if pos not in allowed:doc.blocks[pos]=AIR
sys._neighbor_qa_document=doc.blocks.copy()
sys._neighbor_qa_history=(len(s.editor.undo_stack),len(s.editor.redo_stack))
sys._neighbor_qa_editor=s.editor
sys._neighbor_qa_source=doc
sys._neighbor_qa_occupied.clear()
foot=b.player_origin()
center=tuple((keep[i]+neighbor[i]+1.)/2. for i in range(3))
s.origin=tuple(int(foot[i]+(6,24,6)[i]-center[i]) for i in range(3))
sys._neighbor_qa_origin=tuple(s.origin)
s.opacity=%r
s.projection_missing=True
s.projection_outline=False
b.project()
_result=json.dumps({'size':doc.size,'cells':len(doc.blocks),'source':'public fixed static connection case'})
'''.replace('cases=%r', 'cases=' + repr(VISUAL_CASE['cases']))


def offset(keep, occupied, view, override=None):
    if override is not None:
        return tuple(override)
    row = next(row for row in rows.values() if row['keep'] == keep and row['occupied'] == occupied)
    assert row['camera']['view'] == view, row
    return row['camera']['offset']


def supports(cells):
    if cells[0][1][0] == 'minecraft:pale_hanging_moss':
        root = max((pos for pos, value in cells), key=lambda pos: pos[1])
        return [((root[0], root[1] + 1, root[2]), ('minecraft:stone', 0))]
    lowest = min(pos[1] for pos, value in cells)
    return [((pos[0], pos[1] - 1, pos[2]),
             ('minecraft:end_stone' if value[0] == 'minecraft:chorus_plant' else 'minecraft:stone', 0))
            for pos, value in cells if pos[1] == lowest]


native.view_offset = offset
world.native_supports = supports

_world_case = world.world_case


def native_state_comparison(source, replication):
    origin = source['origin']
    requested = [(tuple(origin[i] + pos[i] for i in range(3)), tuple(value))
                 for pos, value in source['cells']]
    observed = [(tuple(pos), tuple(value)) for pos, value in replication['cells']]
    expected, actual = dict(requested), dict(observed)
    missing = sorted(set(expected) - set(actual))
    unexpected = sorted(set(actual) - set(expected))
    changes = [dict(position=pos, requested=expected[pos], actual=actual[pos])
               for pos in sorted(set(expected) & set(actual)) if expected[pos] != actual[pos]]
    unique = len(expected) == len(requested) and len(actual) == len(observed)
    return {'passed': bool(expected) and unique and not missing and not unexpected and not changes,
            'requested_cells': len(requested), 'observed_cells': len(observed),
            'unique_positions': unique, 'missing': missing, 'unexpected': unexpected,
            'changes': changes,
            'scope': 'Original public blueprint name/aux must match native readback before state replacement.'}


def static_world_case(check, label, args, record):
    result = _world_case(check, label, args, record)
    result['blueprint_states_match_native'] = native_state_comparison(
        result['source'], result['world_replication'])
    result['passed'] = result['passed'] and result['blueprint_states_match_native']['passed']
    preview = result['fixture']['fixture']
    source = preview['screenshot']
    path = args.output.with_name(args.output.stem + '_' + label + '_editor' + Path(source['path']).suffix)
    shutil.copyfile(source['path'], path)
    result['editor'] = {
        'native_evidence': preview['native_evidence'], 'paper_dolls': preview['paper_dolls'],
        'parts': preview['parts'], 'native_submission_verified': True,
        'capture': dict(source, path=str(path.resolve()), sha256=hashlib.sha256(path.read_bytes()).hexdigest()),
        'image_acceptance': {'passed': None, 'scope': 'Public fixture screenshot and native submission; independent editor image comparison pending.'}}
    keep, occupied = native.VISUAL_CASES[label]
    result['full'] = {'projection': {}, 'views': {}}
    try:
        check.run('b.stop_projection()\ns.projection_missing=False\nb.project()\n_result=True')

        def ready(state):
            assert not state['error'] and not state['failed'], state
            return (state['active'] and state['ready'] and state['actors'] and state['model']
                    and not state['has_occupancy'] and not state['preparing']
                    and not state['building'] and not state['pending'])

        result['full']['projection'] = check.wait('full static projection', ready,
                                                 lambda: native.source_state(check, occupied))
        for view, frames in result['views'].items():
            native.select_view(check, keep, occupied, view, None)
            actual, capture = native.capture_signal(check, label + '_' + view + '_full', occupied)
            baseline = native.signal(frames['world']['path'], frames['empty']['path'])
            projection = check.run(native.CELL_ROIS)
            first, second, roi = native.roi_masks(projection, baseline.size, keep, occupied, args.calibration)
            comparison = native.compare_complete(baseline, actual, (first, second), args.threshold, args.min_pixels)
            result['full']['views'][view] = {'capture': capture, 'roi': roi, 'matches_world': comparison}
        result['passed'] = result['passed'] and all(
            row['matches_world']['passed'] for row in result['full']['views'].values())
        result['mode_scope'] = {'editor': 'Submission verified; independent image acceptance pending.',
                                'full': 'Missing mode disabled; native world image comparison.',
                                'missing': 'All-air, dynamic occupied, and initially occupied image comparisons.'}
    finally:
        check.run('b.stop_projection()\ns.projection_missing=True\n_result=True')
    return result


world.world_case = static_world_case

_replay = world.replay


def static_replay(args):
    _replay(args)
    report = json.loads(args.output.read_text(encoding='utf8'))
    for row in report['cases']:
        row['blueprint_states_match_native'] = native_state_comparison(row['source'], row['world_replication'])
        assert row['editor']['native_submission_verified'], row
        capture = row['editor']['capture']
        assert hashlib.sha256(Path(capture['path']).read_bytes()).hexdigest() == capture['sha256'], capture
        assert not row['full']['projection']['has_occupancy'], row['full']['projection']
        for view, frames in row['full']['views'].items():
            for capture in (frames['capture']['shown'], frames['capture']['actor_hidden']):
                assert hashlib.sha256(Path(capture['path']).read_bytes()).hexdigest() == capture['sha256'], capture
            details = row['views'][view]['roi']['projection']
            projection = dict(position=details['position'], rotation=details['rotation'], target=details['target'],
                              fov=details['fov_degrees'], screen=details['screen'], projection_method=details['method'],
                              runtime_minecraft_version=args.calibration['runtime_minecraft_version'], cells=[])
            for pos, value in row['source']['cells']:
                points = [tuple(row['source']['origin'][i] + pos[i] + offset[i] for i in range(3))
                          for offset in ((x, y, z) for x in (0., 1.) for y in (0., 1.) for z in (0., 1.))]
                projection['cells'].append({'pos': pos, 'world_points': points})
            baseline = native.signal(row['views'][view]['world']['path'], row['views'][view]['empty']['path'])
            actual = native.signal(frames['capture']['shown']['path'], frames['capture']['actor_hidden']['path'])
            first, second, roi = native.roi_masks(projection, baseline.size, tuple(row['keep']),
                                                  tuple(row['occupied']), args.calibration)
            frames.update(roi=roi, matches_world=native.compare_complete(
                baseline, actual, (first, second), args.threshold, args.min_pixels))
        row['passed'] = (row['passed'] and row['blueprint_states_match_native']['passed'] and
                         all(frame['matches_world']['passed'] for frame in row['full']['views'].values()))
    report['passed'] = all(row['passed'] for row in report['cases'])
    world.write_json(args.output, report)
    return 0 if report['passed'] else 1


world.replay = static_replay


if __name__ == '__main__':
    raise SystemExit(world.main())
