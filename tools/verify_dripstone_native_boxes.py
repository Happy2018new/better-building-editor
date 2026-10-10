"""Observe native dripstone boxes independently of screenshot alignment."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path

import verify_neighbor_world_visuals as world
from context_test_environment import run
from verify_debug_blueprints import BlueprintCheck, Client, write_json
from verify_neighbor_native_png import restore_owned_window
from release_owned_game_focus import main as release_focus


SAMPLES = (('world_original', (6, -37, 6)),
           ('world_shifted', (7, -37, 8)),
           ('packed_original_lower', (45, 13, 9)),
           ('packed_original_upper', (45, 16, 9)),
           ('packed_source_shift', (25, 13, 25)))


def holdout_samples():
    coordinates = (-33, -32, -31, -17, -16, -15, -1, 0, 1, 15, 16, 17, 31, 32, 33)
    positions = sorted(set([(value, 6) for value in coordinates] +
                           [(6, value) for value in coordinates] +
                           list(zip(coordinates, reversed(coordinates))) + [(6, 6)]))
    return tuple(('holdout_%d_%d_y%d' % (x, z, y), (x, y, z))
                 for x, z in positions for y in (-47, -31))


def matrix(source_samples=SAMPLES):
    cells, supports, samples = {}, {}, []
    for identity, root in source_samples:
        positions = (root, (root[0], root[1] + 1, root[2]))
        for pos, aux in zip(positions, (4, 12)):
            cells[pos] = ('minecraft:pointed_dripstone', aux)
            samples.append({'case': identity, 'pos': pos, 'expected_aux': aux})
        for y in (root[1] - 1, root[1] + 2):
            supports[(root[0], y, root[2])] = ('minecraft:stone', 0)
    assert not set(cells).intersection(supports)
    return sorted(cells.items()), sorted(supports.items()), samples


def verify_scene_boxes(server, client, expected):
    server_rows = dict((tuple(row['pos']), row) for row in server['rows'])
    client_rows = dict((tuple(row['pos']), row) for row in client['rows'])
    assert set(server_rows) == set(client_rows) == set(expected)
    for pos, value in expected.items():
        first, second = server_rows[pos], client_rows[pos]
        for row in (first, second):
            assert (row['value']['name'], row['value']['aux']) == value, row
            for kind in ('clip', 'collision'):
                box = row[kind]
                assert isinstance(box, dict), (pos, kind, box)
                for bound in ('min', 'max'):
                    axes = box.get(bound)
                    assert isinstance(axes, (tuple, list)) and len(axes) == 3, (pos, kind, box)
                    assert all(isinstance(axis, (int, float)) and math.isfinite(axis) for axis in axes), (pos, kind, box)
                assert all(box['min'][axis] < box['max'][axis] for axis in range(3)), (pos, kind, box)
        assert first['clip'] == first['collision'] == second['clip'] == second['collision'], (first, second)
        if value[0] == 'minecraft:stone':
            assert tuple(first['clip']['min']) == pos, first
            assert tuple(first['clip']['max']) == tuple(axis + 1 for axis in pos), first
    return {'all_values_equal': True, 'all_boxes_valid': True,
            'all_box_methods_equal': True, 'stone_unit_boxes': True,
            'cells': len(expected)}


SERVER_BOXES = '''import json
import mod.server.extraServerApi as api
factory=api.GetEngineCompFactory()
level=api.GetLevelId()
dimension=factory.CreateDimension(api.GetPlayerList()[0]).GetEntityDimensionId()
info=factory.CreateBlockInfo(level)
state=factory.CreateBlockState(level)
positions=%r
rows=[{'pos':pos,'value':info.GetBlockNew(pos,dimension),
 'states':state.GetBlockStates(pos,dimension),
 'clip':info.GetBlockClip(pos,dimension),'collision':info.GetBlockCollision(pos,dimension)}
 for pos in positions]
_result=json.dumps({'runtime':api.GetMinecraftVersion(),'dimension':dimension,'rows':rows})
'''

CLIENT_BOXES = '''import json
import mod.client.extraClientApi as api
factory=api.GetEngineCompFactory()
level=api.GetLevelId()
info=factory.CreateBlockInfo(level)
positions=%r
rows=[{'pos':pos,'value':info.GetBlock(pos),'clip':info.GetBlockClip(pos),
 'collision':info.GetBlockCollision(pos)} for pos in positions]
low=tuple(min(pos[i] for pos in positions) for i in range(3))
high=tuple(max(pos[i] for pos in positions) for i in range(3))
palette=factory.CreateBlock(level).GetBlockPaletteBetweenPos(low,high,False)
assert palette is not None
serialized=palette.SerializeBlockPalette()
header=dict((key,value) for key,value in serialized.items()
 if key not in ('common','extra','actor','states','extraStates'))
_result=json.dumps({'runtime':api.GetMinecraftVersion(),'rows':rows,'native_palette_header':header})
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--holdout', action='store_true',
                        help='Independent signed-coordinate, axis and chunk-boundary matrix')
    args = parser.parse_args()
    from _session import load_session
    report = {'schema': 1, 'completed': False, 'restored': False,
              'session_file': os.environ.get('MCDEV_SESSION_FILE'),
              'owner': os.environ.get('MCDEV_OWNER'),
              'method': 'Documented native GetBlockClip/GetBlockCollision at independent coordinates',
              'limits': 'Diagnostic raw boxes only; no fitted image offsets or production rule.'}
    source_path = Path(__file__).resolve()
    report['probe_source_sha256'] = hashlib.sha256(source_path.read_bytes()).hexdigest()
    reference = source_path.parent / 'data/native_dripstone_boxes_r5.json'
    if reference.is_file():
        report['native_aabb_reference'] = {'path': str(reference),
                                         'sha256': hashlib.sha256(reference.read_bytes()).hexdigest()}
    cells, supports, samples = matrix(holdout_samples() if args.holdout else SAMPLES)
    report.update(samples=samples, cells=cells, supports=supports)
    report['sampling_plan'] = ('signed-axis/chunk-boundary holdout; fixed before new native observations'
                               if args.holdout else 'original world/source/packed controls')
    try:
        report['owned_window_activation'] = restore_owned_window(load_session(live=True))
        with Client(timeout=30) as client:
            check = BlueprintCheck(client, args.output, 90)
            try:
                report['world_setup'] = run(client, world.RESERVE % (cells, supports))
                near_cells = ([((0, -47, 0), ('minecraft:air', 0))] if args.holdout else cells)
                report['near_player'] = run(client, world.NEAR_PLAYER % (near_cells,))
                report['near_player']['client'] = world.player_ready(check, report['near_player']['after'])
                report['replication'] = world.replication(check, cells + supports, False)
                positions = [pos for pos, value in cells + supports]
                report['server'] = run(client, SERVER_BOXES % (positions,))
                report['client'] = check.run(CLIENT_BOXES % (positions,))
                report['seed'] = run(client, 'import mod.server.extraServerApi as api\n'
                    '_result=api.GetEngineCompFactory().CreateGame(api.GetLevelId()).GetSeed()')
                expected = dict(cells + supports)
                report['scene_verification'] = verify_scene_boxes(report['server'], report['client'], expected)
                report['all_box_methods_equal'] = report['scene_verification']['all_box_methods_equal']
                report['completed'] = True
            finally:
                report['cleanup'] = world.clear_world(client)
                if report['cleanup']['player_foot'] is not None:
                    world.player_ready(check, report['cleanup']['player_foot'])
                report['restored'] = report['cleanup']['restored']
    except Exception as error:
        report['error'] = '%s: %s' % (type(error).__name__, error)
        raise
    finally:
        try:
            report['owned_focus_release'] = release_focus()
        except Exception as error:
            report['owned_focus_release'] = {'error': '%s: %s' % (type(error).__name__, error)}
        write_json(args.output, report)
    print(json.dumps({'completed': report['completed'], 'restored': report['restored'],
                      'samples': len(samples), 'server': report['server'], 'client': report['client']}))
    return 0 if (report['completed'] and report['restored'] and
                 'error' not in report['owned_focus_release']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
