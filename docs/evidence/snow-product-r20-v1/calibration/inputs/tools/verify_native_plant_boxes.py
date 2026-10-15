"""Observe native plant boxes at fixed cells without treating boxes as meshes."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from verify_debug_blueprints import BlueprintCheck, Client, write_json
from verify_shulker_orientations import server_run
from verify_snow_plant_visibility import (NATIVE_SETUP, NATIVE_NEAR_PLAYER,
                                         NATIVE_MUTATE, NATIVE_SNOW, NATIVE_CLEANUP)
from _session import load_session

ROOT = Path(__file__).resolve().parents[1]
NAMES = ('short_grass', 'fern', 'poppy', 'torchflower', 'crimson_roots',
         'warped_roots', 'nether_sprouts', 'crimson_fungus', 'warped_fungus')
OFFSETS = ((6, 24, 6), (7, 24, 6), (6, 24, 7), (7, 24, 7),
           (8, 24, 6), (6, 25, 6), (6, 40, 6), (-6, 24, -6))

SERVER_BOXES = '''import json,sys
import mod.server.extraServerApi as api
saved=sys._snow_visibility_native
info=api.GetEngineCompFactory().CreateBlockInfo(saved['player'])
pos=saved['target']
dimension=saved['dimension']
_result=json.dumps({'pos':pos,'front':info.GetBlockNew(pos,dimension),
 'clip':info.GetBlockClip(pos,dimension),'collision':info.GetBlockCollision(pos,dimension)})
'''
CLIENT_BOXES = '''pos=%r
info=b.factory.CreateBlockInfo(b.level)
palette=b.factory.CreateBlock(b.level).GetBlockPaletteBetweenPos(pos,pos,False)
data=palette.SerializeBlockPalette() if palette is not None else {}
_result=json.dumps({'pos':pos,'front':info.GetBlock(pos),'clip':info.GetBlockClip(pos),
 'collision':info.GetBlockCollision(pos),
 'common':[value[0] for value in data.get('common',{})],
 'extra':[value[0] for value in data.get('extra',{})]})
'''
BASIC_INFO = '''import json
import mod.server.extraServerApi as api
info=api.GetEngineCompFactory().CreateBlockInfo(api.GetLevelId())
_result=json.dumps(dict((name,info.GetBlockBasicInfo('minecraft:'+name)) for name in %r))
'''


def source_records():
    paths = ('tools/verify_native_plant_boxes.py', 'tools/verify_snow_plant_visibility.py',
             'behavior_pack/modern_projection/projection/debug_snow_blueprints.py',
             'tools/data/block_registry_manifest.json',
             'tools/data/static_plant_sources_nemc_3.9.0.401155.json')
    return {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in paths}


def replicated(check, target, expected, expected_extra=None):
    def read():
        return check.run(CLIENT_BOXES % (target,))
    def matches(row):
        if not row['front'] or row['front'][0] != expected:
            return False
        return expected_extra is None or row['extra'] == [expected_extra]
    return check.wait('native plant box replication', matches, read)


def cleanup_fixture(client):
    exists = server_run(client, 'import sys\n_result=hasattr(sys,"_snow_visibility_native")')
    return server_run(client, NATIVE_CLEANUP) if exists else [{'clean': True, 'fixture_absent': True}]


def run(output, timeout):
    if output.exists():
        raise ValueError('Native plant box evidence must have a fresh output path')
    session = load_session(live=True)
    if Path(session['project']).resolve() != ROOT:
        raise ValueError('The session belongs to a different project')
    report = {'schema': 1, 'completed': False, 'restored': False,
              'session_file': session['session_file'], 'owner': session['owner'],
              'game_pid': session['game_pid'], 'game_identity': session['game_identity'],
              'plants': NAMES, 'planned_offsets': OFFSETS, 'rows': [], 'cleanups': [],
              'source_sha256': source_records(),
              'native_mesh_accepted': False, 'random_offset_contract_accepted': False,
              'scope': 'Documented raw clip/collision boxes at fixed cells only; no mesh or offset fitting'}
    write_json(output, report)
    pending = False
    cleanup_errors = []
    try:
        with Client(timeout=30) as client:
            check = BlueprintCheck(client, output, timeout)
            exists = server_run(client, 'import sys\n_result=hasattr(sys,"_snow_visibility_native")')
            if exists:
                raise ValueError('Previous native snow fixture needs cleanup')
            report['basic_info'] = server_run(client, BASIC_INFO % (NAMES,))
            foot = check.run('_result=json.dumps(b.player_origin())')
            report['player_origin'] = foot
            targets = [tuple(foot[i]+offset[i] for i in range(3)) for offset in OFFSETS]
            report['targets'] = targets
            write_json(output, report)
            for index, target in enumerate(targets):
                report['active_target'] = target
                write_json(output, report)
                try:
                    pending = True
                    fixture = server_run(client, NATIVE_SETUP % (target,))
                    near_player = server_run(client, NATIVE_NEAR_PLAYER)
                    for plant in NAMES:
                        changed = server_run(client, NATIVE_MUTATE % (plant, 'plant', 0))
                        if changed['front']['name'] != 'minecraft:'+plant:
                            raise ValueError('Dry native plant readback differs: %r' % changed)
                        native_client = replicated(check, target, 'minecraft:'+plant)
                        dry = {'server': server_run(client, SERVER_BOXES), 'client': native_client}
                        snow = server_run(client, NATIVE_SNOW % 0)
                        if (not snow['result'] or snow['front']['name'] != 'minecraft:snow_layer' or
                                snow['states'] != {'height': 0, 'covered_bit': True}):
                            raise ValueError('Native covered h0 readback differs: %r' % snow)
                        native_client = replicated(check, target, 'minecraft:snow_layer',
                                                   'minecraft:'+plant)
                        covered = {'server': server_run(client, SERVER_BOXES), 'client': native_client}
                        report['rows'].append({'target_index': index, 'plant': plant, 'target': target,
                                               'fixture': fixture, 'near_player': near_player,
                                               'dry_mutation': changed, 'h0_mutation': snow,
                                               'dry': dry, 'h0': covered})
                        write_json(output, report)
                        print(json.dumps({'target_index': index, 'plant': plant,
                                          'dry_clip': dry['server']['clip']}), flush=True)
                finally:
                    if pending:
                        cleanup = cleanup_fixture(client)
                        report['cleanups'].append({'target': target, 'results': cleanup})
                        pending = False
                        if not all(row['clean'] for row in cleanup):
                            cleanup_errors.append({'target': target, 'results': cleanup})
                        write_json(output, report)
                    if cleanup_errors:
                        raise ValueError('Native fixture restoration failed')
            report['completed'] = len(report['rows']) == len(targets)*len(NAMES)
    except Exception as error:
        report['error'] = '%s: %s' % (type(error).__name__, error)
        raise
    finally:
        report['restored'] = not pending and not cleanup_errors
        report['cleanup_errors'] = cleanup_errors
        report['source_assets_stable'] = source_records() == report['source_sha256']
        write_json(output, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--timeout', type=float, default=60.)
    args = parser.parse_args()
    report = run(args.output, args.timeout)
    print(json.dumps({key: report[key] for key in
                      ('completed', 'restored', 'source_assets_stable')}))
    return 0 if report['completed'] and report['restored'] and report['source_assets_stable'] else 1


if __name__ == '__main__':
    sys.exit(main())
