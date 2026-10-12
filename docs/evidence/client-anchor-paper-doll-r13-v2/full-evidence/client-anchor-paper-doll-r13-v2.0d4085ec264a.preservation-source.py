"""Preserve the single R13 gated result, original PNGs and full exact provenance."""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from run_client_anchor_paper_doll import ROOT, SESSION, ARTIFACTS, EVIDENCE_PREFIX, load_probe
from session_pack_stage import digest


def write_fresh(path, value):
    with path.open('x', encoding='ascii') as output:
        json.dump(value, output, ensure_ascii=True, indent=2)
        output.write('\n')


def main():
    prefix = EVIDENCE_PREFIX
    files = [ARTIFACTS / (prefix + suffix) for suffix in
             ('.supervision.json', '.orchestration.json', '.runtime.json',
              '.health-supervision.json', '.post-restoration-health.json', '.sources.index.json')]
    before = {str(path): digest(path) for path in files}
    supervision, owner, runtime, health_supervision, health, sources = [json.loads(path.read_bytes()) for path in files]
    assert supervision['completed'] and not supervision['timed_out'] and supervision['attempts'] == 1
    assert runtime['restored'] and owner['restored'] and not runtime['cleanup_errors'] and not owner['cleanup_errors']
    assert not runtime['completed'] and set(runtime['states']) == {'empty', 'plain'}
    assert health['passed'] and health['timer_cleanup_verified'] and not health_supervision['timed_out']
    assert owner['protected_sources_and_configs_unchanged']
    assert not any(owner[key] for key in ('shader_or_pack_mutation_attempted',
                   'world_or_inventory_mutation_attempted', 'player_position_mutation_attempted'))
    probe, _ = load_probe()
    score, ordinary = probe.score_probe(runtime), probe.ordinary_gate(runtime)
    assert ordinary == runtime['ordinary_gate'] and ordinary['stable_plain_pixels'] == 0
    assert ordinary['marker_gate_passed'] and not ordinary['body_dispatch_allowed']
    frames = [(label, index, frame) for label in ('empty', 'plain')
              for index, frame in enumerate(runtime['states'][label]['frames'])]
    assert len(frames) == 4
    maximum_marker_error = max(value for _, _, frame in frames for marker in frame['marker_mapping']['markers']
                               for value in marker['center_errors'] + marker['edge_errors'])
    assert maximum_marker_error <= 1.
    assert all(frame['marker_mapping']['passed'] and
               frame['marker_mapping']['calibration'] == runtime['frozen_marker_calibration'] and
               frame['marker_mapping']['legacy_api_uniform_mapping']['passed'] is False for _, _, frame in frames)
    attachments = runtime['restore']['attachments']
    assert len(attachments) == 1 and attachments[0]['id'] == 0
    assert all(row['state'] == 'removed' and row['remove_result'] is True and row['item_nonmutation'] for row in attachments)
    assert runtime['cleanup_destroy']['observed_actor_kind'] == 'modern_projection:anchor'
    assert runtime['actor_absence']['kind'] is None and runtime['actor_absence']['absent']
    assert runtime['restore']['body'] is None
    raw_errors = [row for row in owner['requests'] if isinstance(row.get('response'), dict) and row['response'].get('isError')]
    assert len(owner['requests']) == 46 and not raw_errors
    observed_pngs = [{'control': label, 'frame': index, 'path': frame['capture']['path'],
                     'sha256': frame['capture']['sha256'], 'bytes': frame['capture']['bytes']}
                    for label, index, frame in frames]
    for row in observed_pngs:
        assert digest(Path(row['path'])) == row['sha256'] and Path(row['path']).stat().st_size == row['bytes']
    write_fresh(ARTIFACTS / (prefix + '.offline-score.json'),
                {'schema': 1, 'scope': 'Offline exact reviewed probe score and pre-body ordinary gate',
                 'runtime_sha256': digest(files[2]), 'scores': score, 'ordinary_gate': ordinary})
    write_fresh(ARTIFACTS / (prefix + '.visual-review.json'),
                {'schema': 1, 'created_at': datetime.now(timezone.utc).isoformat(), 'reviewer': 'frame-r11-background',
                 'scope': 'Owner opened all four original PNGs after restoration and fresh health',
                 'original_native_pngs_inspected': observed_pngs,
                 'observations': ['All four captures show the same light opaque UI background and four colored corner markers.',
                                  'Neither empty nor plain captures show a visible anchor or diamond sword.',
                                  'Small transient diagnostic text at the top is outside the frozen lower-90-percent score region.'],
                 'ordinary_item_on_client_actor_proven': False, 'shared_body_depth_proven': False,
                 'production_rendering_accepted': False, 'editor_frame_content_accepted': False,
                 'enchantment_glint_accepted': False,
                 'limitations': ['This single transparent anchor, root bind, unit item scale and .35 UI scale was not visibly included.',
                                 'No world-rendered attachment comparison was captured.',
                                 'Stone-body geometry, shared depth, occlusion, clipping and glint were never dispatched or proven.']})
    write_fresh(ARTIFACTS / (prefix + '.result-supplement.json'),
                {'schema': 1, 'created_at': datetime.now(timezone.utc).isoformat(),
                 'completed': False, 'restored': True, 'native_frames_captured': 4,
                 'native_elapsed_seconds': owner['native_elapsed_seconds'],
                 'raw_rpc_entries': len(owner['requests']), 'raw_rpc_isError_entries': len(raw_errors),
                 'http_entries_including_delete': len(owner['network_requests']),
                 'ordinary_gate': ordinary, 'body_dispatch_attempted': False,
                 'maximum_marker_edge_or_center_error_physical_pixels': maximum_marker_error,
                 'legacy_api_uniform_mapping_passed': False,
                 'frozen_marker_calibration': runtime['frozen_marker_calibration'],
                 'owned_actor': runtime['initial']['actor'], 'root_bone_readback': runtime['actor_ready']['bone'],
                 'attachment': attachments[0], 'actor_absence': runtime['actor_absence'],
                 'post_restoration_health_passed': health['passed'],
                 'client_clocks': [health['client_before']['now'], health['client_after']['now']],
                 'server_clocks': [health['server_before']['now'], health['server_after']['now']],
                 'server_callbacks': health['timer_stop']['callbacks'],
                 'original_artifact_sha256': before,
                 'ordinary_item_on_client_actor_proven': False, 'shared_body_depth_proven': False,
                 'production_rendering_accepted': False, 'editor_frame_content_accepted': False,
                 'enchantment_glint_accepted': False})
    for name in ('check_client_anchor_health.py', 'test_check_client_anchor_health.py'):
        source = ROOT / '.runtime/frame-baseline-plan-r11' / name
        destination = ARTIFACTS / (prefix + '.' + digest(source)[:12] + '.' + name)
        assert not destination.exists()
        shutil.copyfile(source, destination)
    shutil.copyfile(SESSION / 'mcdk.log', ARTIFACTS / (prefix + '.post-restoration.mcdk.log'))
    source = Path(__file__)
    shutil.copyfile(source, ARTIFACTS / (prefix + '.' + digest(source)[:12] + '.preservation-source.py'))
    files = set(path for path in ARTIFACTS.iterdir() if path.is_file() and path.name.startswith(prefix + '.'))
    for row in sources['files']:
        path = Path(sources['directory']) / row['path']
        assert digest(path) == row['sha256'] and path.stat().st_size == row['bytes']
        files.add(path)
    index = ARTIFACTS / (prefix + '.artifact-index.json')
    write_fresh(index, {'schema': 1, 'files': [
        {'path': str(path), 'bytes': path.stat().st_size, 'sha256': digest(path)} for path in sorted(files)]})
    for row in json.loads(index.read_bytes())['files']:
        assert digest(Path(row['path'])) == row['sha256']
    assert all(digest(Path(path)) == expected for path, expected in before.items())
    print(json.dumps({'artifacts_verified': len(files), 'index_sha256': digest(index),
                      'maximum_marker_error_pixels': maximum_marker_error, 'ordinary_gate': ordinary}))


if __name__ == '__main__':
    main()
