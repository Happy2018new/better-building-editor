"""Freeze completed native item captures, offline score and owner visual review."""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from run_native_item_paper_doll import ARTIFACTS, SESSION, EVIDENCE_PREFIX, load_probe
from session_pack_stage import digest


def write_fresh(path, report):
    with path.open('x', encoding='ascii') as target:
        json.dump(report, target, ensure_ascii=True, indent=2)
        target.write('\n')


def main():
    prefix = EVIDENCE_PREFIX
    paths = [ARTIFACTS / (prefix + suffix) for suffix in
             ('.orchestration.json', '.runtime.json', '.post-restoration-health.json', '.sources.index.json')]
    original_hashes = {str(path): digest(path) for path in paths}
    orchestration, runtime, health, sources = [json.loads(path.read_bytes()) for path in paths]
    assert orchestration['completed'] and orchestration['restored']
    assert runtime['completed'] and runtime['restored'] and not runtime['errors'] and not runtime['cleanup_errors']
    assert health['passed'] and health['timer_cleanup_verified']
    assert orchestration['protected_sources_and_configs_unchanged']
    assert not orchestration['shader_or_pack_mutation_attempted']
    assert not orchestration['world_or_inventory_mutation_attempted']
    probe, _ = load_probe()
    frames = [(label, index, frame) for label in probe.STATES
              for index, frame in enumerate(runtime['states'][label]['frames'])]
    assert len(frames) == 15
    assert all(len(runtime['states'][label]['frames']) == 3 for label in probe.STATES)
    assert all(runtime['states'][label]['state'] == 'captured' for label in probe.STATES)
    score = probe.score_probe(runtime)
    write_fresh(ARTIFACTS / (prefix + '.offline-score.json'), {
        'schema': 1, 'scope': 'Offline score from exact reviewed probe; no SDK calls',
        'runtime_sha256': digest(paths[1]), 'scores': score,
    })
    maximum_marker_error = max(value for _, _, frame in frames
                               for marker in frame['marker_mapping']['markers']
                               for value in marker['center_errors'] + marker['edge_errors'])
    assert maximum_marker_error <= 1.
    assert all(frame['marker_mapping']['passed'] and
               frame['marker_mapping']['calibration'] == runtime['frozen_marker_calibration']
               for _, _, frame in frames)
    assert all(frame['marker_mapping']['legacy_api_uniform_mapping']['passed'] is False
               for _, _, frame in frames)
    attachments = runtime['owned attachments']['attachments']
    assert len(attachments) == 3
    assert all(row['state'] == 'removed' and row['remove_result'] is True and row['item_nonmutation'] is True
               for row in attachments)
    observed_pngs = [{'control': label, 'frame': index, 'path': frame['capture']['path'],
                      'sha256': frame['capture']['sha256'], 'bytes': frame['capture']['bytes']}
                     for label, index, frame in frames]
    for row in observed_pngs:
        assert digest(Path(row['path'])) == row['sha256']
    write_fresh(ARTIFACTS / (prefix + '.visual-review.json'), {
        'schema': 1, 'reviewer': 'frame-r11-background', 'created_at': datetime.now(timezone.utc).isoformat(),
        'scope': 'Owner opened all 15 original native PNGs after restoration and health verification',
        'original_native_pngs_inspected': observed_pngs,
        'native_bound_item_ui_inclusion_proven': True,
        'enchantment_correlated_temporal_appearance_observed': True,
        'production_rendering_accepted': False, 'editor_frame_content_accepted': False,
        'enchantment_glint_accepted': False,
        'observations': [
            'The diamond sword is visible across the head and right side in every plain frame.',
            'Both empty triplets show the same native player without the attached sword.',
            'Flag-only and actual typed-enchantment frames show changing blue-purple sheen over the item.',
            'All frames show four opaque corner markers and the same large native player framing.',
            'The visible sword overlaps the head and includes fragmented-looking edges; portions extend past the paper-doll crop.',
        ],
        'limitations': [
            'This proves only attached-item inclusion on this isolated entity-ID UI surface.',
            'It does not establish production frame-body shared depth, clipping, transparency or block-context behavior.',
            'Temporal appearance does not establish GLINT defines, material identity, texture inputs or shader time.',
            'The marker mapping passed separately; the original one-pixel API-only uniform mapping still failed.',
        ],
    })
    raw_errors = [row for row in orchestration['requests']
                  if isinstance(row.get('response'), dict) and row['response'].get('isError') is True]
    assert not raw_errors
    write_fresh(ARTIFACTS / (prefix + '.result-supplement.json'), {
        'schema': 1, 'created_at': datetime.now(timezone.utc).isoformat(),
        'completed': True, 'restored': True, 'native_frames_captured': len(frames),
        'raw_rpc_entries': len(orchestration['requests']), 'raw_rpc_isError_entries': len(raw_errors),
        'native_elapsed_seconds': orchestration['native_elapsed_seconds'],
        'maximum_marker_edge_or_center_error_physical_pixels': maximum_marker_error,
        'frozen_marker_calibration': runtime['frozen_marker_calibration'],
        'legacy_api_uniform_mapping_passed': False,
        'owned_attachment_rows': attachments,
        'original_artifact_sha256': original_hashes,
        'post_restoration_health_passed': health['passed'],
        'post_restoration_client_clocks': [health['client_before']['now'], health['client_after']['now']],
        'post_restoration_server_timer_callbacks': health['timer_stop']['callbacks'],
        'native_bound_item_ui_inclusion_proven': True,
        'enchantment_correlated_temporal_appearance_observed': True,
        'production_rendering_accepted': False, 'editor_frame_content_accepted': False,
        'enchantment_glint_accepted': False,
    })
    shutil.copyfile(SESSION / 'mcdk.log', ARTIFACTS / (prefix + '.post-restoration.mcdk.log'))
    preservation_source = ARTIFACTS / (prefix + '.' + digest(Path(__file__))[:12] + '.preservation-source.py')
    assert not preservation_source.exists()
    shutil.copyfile(Path(__file__), preservation_source)
    files = set(path for path in ARTIFACTS.iterdir() if path.is_file() and path.name.startswith(prefix + '.'))
    for row in sources['files']:
        path = Path(sources['directory']) / row['path']
        assert digest(path) == row['sha256'] and path.stat().st_size == row['bytes']
        files.add(path)
    index = ARTIFACTS / (prefix + '.artifact-index.json')
    write_fresh(index, {'schema': 1, 'files': [
        {'path': str(path), 'bytes': path.stat().st_size, 'sha256': digest(path)} for path in sorted(files)]})
    for row in json.loads(index.read_bytes())['files']:
        path = Path(row['path'])
        assert digest(path) == row['sha256'] and path.stat().st_size == row['bytes']
    assert all(digest(Path(path)) == sha for path, sha in original_hashes.items())
    print(json.dumps({'artifacts_verified': len(files), 'index_sha256': digest(index),
                      'score': score, 'maximum_marker_error_pixels': maximum_marker_error}))


if __name__ == '__main__':
    main()
