"""Observe native dripstone boxes independently of screenshot alignment."""
import argparse
import json
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


def matrix():
    cells, supports, samples = {}, {}, []
    for identity, root in SAMPLES:
        positions = (root, (root[0], root[1] + 1, root[2]))
        for pos, aux in zip(positions, (4, 12)):
            cells[pos] = ('minecraft:pointed_dripstone', aux)
            samples.append({'case': identity, 'pos': pos, 'expected_aux': aux})
        for y in (root[1] - 1, root[1] + 2):
            supports[(root[0], y, root[2])] = ('minecraft:stone', 0)
    assert not set(cells).intersection(supports)
    return sorted(cells.items()), sorted(supports.items()), samples


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
    args = parser.parse_args()
    from _session import load_session
    report = {'schema': 1, 'completed': False, 'restored': False,
              'session_file': os.environ.get('MCDEV_SESSION_FILE'),
              'owner': os.environ.get('MCDEV_OWNER'),
              'method': 'Documented native GetBlockClip/GetBlockCollision at independent coordinates',
              'limits': 'Diagnostic raw boxes only; no fitted image offsets or production rule.'}
    cells, supports, samples = matrix()
    report.update(samples=samples, cells=cells, supports=supports)
    try:
        report['owned_window_activation'] = restore_owned_window(load_session(live=True))
        with Client(timeout=30) as client:
            check = BlueprintCheck(client, args.output, 90)
            try:
                report['world_setup'] = run(client, world.RESERVE % (cells, supports))
                report['near_player'] = run(client, world.NEAR_PLAYER % (cells,))
                report['near_player']['client'] = world.player_ready(check, report['near_player']['after'])
                report['replication'] = world.replication(check, cells + supports, False)
                positions = [pos for pos, value in cells + supports]
                report['server'] = run(client, SERVER_BOXES % (positions,))
                report['client'] = check.run(CLIENT_BOXES % (positions,))
                expected = dict(cells + supports)
                for row in report['server']['rows']:
                    value = row['value']
                    assert (value['name'], value['aux']) == expected[tuple(row['pos'])], row
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
