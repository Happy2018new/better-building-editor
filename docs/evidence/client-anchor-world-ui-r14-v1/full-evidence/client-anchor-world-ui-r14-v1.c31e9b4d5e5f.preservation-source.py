"""Preserve exact paired world/UI evidence after cleanup, health and visual review."""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from run_client_anchor_world_ui import ROOT, SESSION, ARTIFACTS, EVIDENCE_PREFIX, load_probe
from session_pack_stage import digest


def write_fresh(path, value):
    with path.open('x', encoding='ascii') as output:
        json.dump(value, output, ensure_ascii=True, indent=2)
        output.write('\n')


def main():
    prefix = EVIDENCE_PREFIX
    paths = [ARTIFACTS / (prefix + suffix) for suffix in
             ('.supervision.json', '.orchestration.json', '.runtime.json',
              '.health-supervision.json', '.post-restoration-health.json', '.sources.index.json',
              '.visual-review.json')]
    before = {str(path): digest(path) for path in paths}
    supervision, owner, runtime, health_supervision, health, sources, review = [json.loads(path.read_bytes()) for path in paths]
    assert supervision['attempts'] == 1 and supervision['completed'] and not supervision['timed_out']
    assert runtime['restored'] and owner['restored'] and not runtime['cleanup_errors'] and not owner['cleanup_errors']
    assert health['passed'] and health['timer_cleanup_verified'] and not health_supervision['timed_out']
    assert owner['protected_sources_and_configs_unchanged']
    assert not any(owner[key] for key in ('shader_or_pack_mutation_attempted',
                   'world_or_inventory_mutation_attempted', 'player_position_mutation_attempted'))
    probe, _ = load_probe()
    score = probe.score_probe(runtime) if runtime['completed'] else {
        'classification': 'incomplete_matrix', 'reason': runtime['errors'],
        'production_rendering_accepted': False, 'editor_frame_content_accepted': False,
        'enchantment_glint_accepted': False}
    frames = [(label, index, frame) for label in probe.STATES if label in runtime['states']
              for index, frame in enumerate(runtime['states'][label]['frames'])]
    original_pngs = [{'control': label, 'frame': index, 'path': frame['capture']['path'],
                     'sha256': frame['capture']['sha256'], 'bytes': frame['capture']['bytes']}
                    for label, index, frame in frames]
    assert review['original_native_pngs_inspected'] == original_pngs
    assert not any(review[key] for key in ('production_rendering_accepted', 'editor_frame_content_accepted',
                                         'enchantment_glint_accepted'))
    for row in original_pngs:
        assert digest(Path(row['path'])) == row['sha256'] and Path(row['path']).stat().st_size == row['bytes']
    raw_errors = [row for row in owner['requests'] if isinstance(row.get('response'), dict) and row['response'].get('isError')]
    write_fresh(ARTIFACTS / (prefix + '.offline-score.json'),
                {'schema': 1, 'scope': 'Exact reviewed paired-probe offline score; no SDK calls',
                 'runtime_sha256': digest(paths[2]), 'scores': score})
    write_fresh(ARTIFACTS / (prefix + '.result-supplement.json'),
                {'schema': 1, 'created_at': datetime.now(timezone.utc).isoformat(),
                 'completed': runtime['completed'], 'restored': runtime['restored'],
                 'native_frames_captured': len(frames), 'raw_rpc_entries': len(owner['requests']),
                 'raw_rpc_isError_entries': len(raw_errors), 'http_entries_including_delete': len(owner['network_requests']),
                 'native_elapsed_seconds': owner['native_elapsed_seconds'], 'scores': score,
                 'errors': runtime['errors'], 'cleanup_errors': runtime['cleanup_errors'],
                 'initial': runtime.get('initial'), 'actor_absence': runtime.get('actor_absence'),
                 'restored_state': runtime.get('restore'), 'original_artifact_sha256': before,
                 'post_restoration_health_passed': health['passed'],
                 'client_clocks': [health['client_before']['now'], health['client_after']['now']],
                 'server_clocks': [health['server_before']['now'], health['server_after']['now']],
                 'server_callbacks': health['timer_stop']['callbacks'],
                 'production_rendering_accepted': False, 'editor_frame_content_accepted': False,
                 'enchantment_glint_accepted': False})
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
    print(json.dumps({'artifacts_verified': len(files), 'index_sha256': digest(index), 'scores': score}))


if __name__ == '__main__':
    main()
