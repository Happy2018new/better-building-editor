"""Read the three immutable v5 images and lifecycle evidence without game calls."""
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
CONTROL = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'tools'))
from prepare_shelf_render_palette_r21 import verify
from shelf_render_palette_candidate_r21 import SOURCE, PROXY


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    destination = CONTROL/'review.json'
    if destination.exists():
        raise ValueError('Keep the original review receipt')
    freeze = CONTROL/'frozen.json'
    frozen = verify(freeze)
    captures = CONTROL/'captures/south-full-palette'
    acquisition = json.loads((captures/'report.json').read_bytes())
    if not all(acquisition[key] for key in ('completed', 'restored', 'source_unchanged')) or acquisition['cleanup_errors']:
        raise ValueError('The acquisition did not complete and restore')
    if acquisition['frozen_manifest_sha256'] != sha(freeze):
        raise ValueError('The acquisition is not bound to this amendment')
    labels = ('native', 'proxy_support', 'proxy_support_color')
    if set(acquisition['captures']) != set(labels):
        raise ValueError('The acquisition must contain exactly its three declared images')
    first = acquisition['captures']['native']['before']
    for row in acquisition['captures'].values():
        if row['before'] != first or row['after'] != first:
            raise ValueError('The comparison camera changed')
    palette = acquisition['palette']
    cyan = ('minecraft:cyan_concrete', 0)
    if (palette['volume'] != [1, 1, 2] or
            ast.literal_eval(palette['source_common']) != {SOURCE: [1], cyan: [0]} or
            ast.literal_eval(palette['common']) != {PROXY: [1], cyan: [0]} or
            ast.literal_eval(palette['actor']) != {} or
            not palette['support_inside_same_combine'] or palette['independent_body_overlay'] or
            not palette['source_unchanged'] or not palette['prepared_unchanged']):
        raise ValueError('The full render-only palette ownership changed')
    air = [{'name': 'minecraft:air', 'aux': 0}] * 2
    if (acquisition['empty_replication']['world'] != air or
            acquisition['empty_replication']['replication']['cells'] != air):
        raise ValueError('Real support/body were not both cleared before attachment')
    images = {name: Image.open(captures/(name+'.png')).convert('RGB') for name in labels}
    if any(image.size != (1994, 1105) for image in images.values()):
        raise ValueError('The reviewed image framing changed')
    regions = {'upper_vertical': (920, 450, 1080, 490),
               'middle_vertical': (920, 500, 1080, 580),
               'lower_vertical': (920, 592, 1080, 630)}
    color_regions = {}
    for name, bounds in regions.items():
        pixels = Counter(images['proxy_support_color'].crop(bounds).getdata())
        expected = (bounds[2]-bounds[0])*(bounds[3]-bounds[1])
        if pixels != {(204, 204, 204): expected}:
            raise ValueError('The observed COLOR region changed: '+name)
        color_regions[name] = {'bounds': bounds, 'pixels': expected, 'rgb': [204, 204, 204]}
    points = [(920, y) for y in (446, 450, 500, 550, 580, 585, 590, 630)]
    points += [(1080, y) for y in (446, 450, 500, 550, 580, 590, 630)]
    points += [(997, y) for y in (439, 470, 530, 600, 650, 750)]
    close_path, exit_path = CONTROL/'launch/normal-close-receipt.json', CONTROL/'launch/exact-exit.json'
    close, exited = json.loads(close_path.read_bytes()), json.loads(exit_path.read_bytes())
    if close['normal_close_calls'] != 1 or close['force'] or not exited['completed']:
        raise ValueError('The single normal-close and exact-exit lifecycle changed')
    session = acquisition['session']
    ready = json.loads((CONTROL/'launch/start-summary.json').read_bytes())
    for kind in ('game', 'mcdk'):
        process = exited['processes'][kind]
        if process['state'] != 'exited' or (
                process['pid'], process['identity']) != (ready[kind+'_pid'], ready[kind+'_identity']):
            raise ValueError('The exact observed process changed')
    registry_path = Path('C:/Users/Happy2018new/.pyreact-debug/instances/'+session['id']+'/session.json')
    registry = json.loads(registry_path.read_bytes())
    if registry['state'] != 'stopped' or registry['ready'] is not False:
        raise ValueError('The exact session was not finalized')
    readback_path = CONTROL/'launch/finalized-session-readback.json'
    if readback_path.exists():
        raise ValueError('Keep the original finalized session readback')
    readback = {key: registry[key] for key in ('id', 'owner', 'state', 'ready', 'game_pid',
                'game_identity', 'mcdk_pid', 'mcdk_identity')}
    readback.update(observed_at=datetime.now(timezone.utc).isoformat(),
                    source_session_sha256=sha(registry_path),
                    source='Selected fields read directly from the finalized session registry; token omitted.')
    readback_path.write_text(json.dumps(readback, indent=2)+'\n', encoding='ascii', newline='\n')
    paths = [captures/(name+'.png') for name in labels]
    paths += [captures/'report.json', close_path, exit_path, freeze, CONTROL/'compile.json',
              CONTROL/'launch/assertion-watch-ready.json', readback_path, CONTROL/'launch/start-summary.json']
    result = {'schema_version': 1, 'reviewed_at': datetime.now(timezone.utc).isoformat(),
        'actual_raw_images_opened_by_shelf_agent': True, 'production_qualified': False,
        'native_neighbor_ao_qualified': False, 'body_lighting_closed': False,
        'scope': 'One south/unpowered oak shelf and cyan support in the same Combine. No other direction, state or packed-context runtime claim.',
        'conclusion': 'Full proxy/support front COLOR stays spatially constant at byte204 in the measured interiors. '
                      'Including support in the same palette did not reproduce the previously observed native vertical COLOR gradient. '
                      'No height fit, scalar compensation or product routing was introduced.',
        'source_and_prepared_unchanged': True, 'same_combine_volume': [1, 1, 2],
        'support_inside_same_combine': True, 'both_real_cells_replicated_air': True,
        'camera_unchanged': True, 'color_regions': color_regions,
        'samples': [dict(point=point, **{name: image.getpixel(point) for name, image in images.items()}) for point in points],
        'resource_commit_minimum_bytes': min(row['commit_available_bytes'] for row in acquisition['resource_samples']),
        'normal_close': {'calls': 1, 'force': False, 'returncode': close['returncode'],
                         'timeout_preserved': 'Game has not closed' in close['stderr']},
        'exact_exits': exited['processes'], 'finalized_registry_readback': {
            'id': registry['id'], 'owner': registry['owner'], 'state': registry['state'], 'ready': registry['ready']},
        'finalize_command_exit_zero': {'value': True, 'provenance': 'Agent transcript attestation; finalization stdout was not separately saved.'},
        'source_files_digest': frozen['files_sha256'],
        'evidence_sha256': {path.relative_to(CONTROL).as_posix(): sha(path) for path in paths}}
    destination.write_text(json.dumps(result, indent=2)+'\n', encoding='ascii', newline='\n')
    print(json.dumps({'reviewed': True, 'color_pixels': sum(row['pixels'] for row in color_regions.values()),
                      'native_neighbor_ao_qualified': False, 'review_sha256': sha(destination)}))


if __name__ == '__main__':
    main()
