"""Keep a fixed native AABB holdout without duplicating its terrain snapshots."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry
from verify_dripstone_native_boxes import holdout_samples, matrix, verify_scene_boxes


def pack(report, session, manifest, raw_sha256):
    if (report.get('schema') != 1 or not report.get('completed') or
            not report.get('restored') or report.get('error') or
            not report.get('background_only') or not report.get('preserve_terrain')):
        raise ValueError('A completed, restored background holdout is required')
    if (Path(report['session_file']).resolve() != Path(session['session_file']).resolve() or
            report['owner'] != session['owner'] or Path(session['project']).resolve() != ROOT):
        raise ValueError('The report and project must belong to the recorded session')
    version = manifest['game_version'].removeprefix('NEMC ')
    if (Path(session['game_executable']).parent.name != version or
            manifest['game_version'] != block_registry.source_version() or
            manifest['source_sha256'].lower() != block_registry.fingerprint().lower()):
        raise ValueError('The installed game and block registry version do not match')
    cells, supports, samples = matrix(holdout_samples())
    if (report['samples'] != json.loads(json.dumps(samples)) or
            report['cells'] != json.loads(json.dumps(cells)) or
            report['supports'] != json.loads(json.dumps(supports))):
        raise ValueError('Native observations must use the unchanged 92-pair holdout')
    cleanup, setup = report['cleanup'], report['world_setup']
    count = setup['reserved'] + setup['guard']
    if (cleanup.get('errors') or cleanup.get('snapshot_retained_for_retry') or
            cleanup.get('verified_cells') != count or not setup.get('all_preflight_reads_before_write')):
        raise ValueError('Every saved terrain cell must be restored and verified')
    server, client = report['server'], report['client']
    if server['runtime'] != client['runtime']:
        raise ValueError('Client and server runtime versions differ')
    verified = verify_scene_boxes(server, client, dict(cells + supports))
    records = []
    for row in server['rows']:
        value = (row['value']['name'], row['value']['aux'])
        states = row['states']
        if states != block_registry.states(value):
            raise ValueError('Native state does not match the dump: ' + repr(row['pos']))
        records.append({'pos': row['pos'], 'material': list(value),
                        'states': states, 'box': row['clip']})
    return {'schema_version': 1, 'game_version': manifest['game_version'],
            'palette_sha256': manifest['source_sha256'].lower(),
            'runtime_minecraft_version': server['runtime'], 'seed': report['seed'],
            'raw_report_sha256': raw_sha256,
            'probe_source_sha256': report['probe_source_sha256'],
            'session': {key: session[key] for key in ('id', 'owner', 'game_identity', 'game_executable')},
            'completed': True, 'restored': True, 'verified_terrain_cells': count,
            'sampling_plan': report['sampling_plan'], 'native_palette_header': client['native_palette_header'],
            'scene_verification': verified, 'pair_count': len(holdout_samples()), 'records': records,
            'native_geometry_accepted': False, 'visual_accuracy_accepted': False,
            'scope': 'Native server/client clip and collision boxes at fixed signed coordinates. '
                     'No fitted displacement, production offset rule or pixel acceptance.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('session', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output exists; preserve evidence and choose a new path')
    raw = args.report.read_bytes()
    manifest = json.loads((ROOT / 'tools/data/block_registry_manifest.json').read_text(encoding='utf8'))
    session = json.loads(args.session.read_text(encoding='utf8'))
    result = pack(json.loads(raw), session, manifest, hashlib.sha256(raw).hexdigest())
    args.output.write_text(json.dumps(result, ensure_ascii=True, sort_keys=True, indent=2) + '\n', encoding='ascii')
    print(json.dumps({'pairs': result['pair_count'], 'rows': len(result['records']),
                      'restored_terrain_cells': result['verified_terrain_cells'],
                      'raw_report_sha256': result['raw_report_sha256'],
                      'visual_accuracy_accepted': result['visual_accuracy_accepted']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
