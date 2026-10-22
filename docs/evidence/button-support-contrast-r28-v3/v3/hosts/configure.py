"""Prepare the reviewable config or bind one root-granted live session; no launch."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
V5 = HERE.with_name('transforms-cache-lineage-v5')
OLD = ROOT / '.runtime/round-20261022/transforms-runtime-v1'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prelaunch', action='store_true')
    parser.add_argument('--session', type=Path)
    args = parser.parse_args()
    assert args.prelaunch is (args.session is None)
    from frozen_guard import verify
    manifest = verify()
    manifest_path = HERE / 'source-manifest.json'
    project = Path(manifest['project'])
    assert manifest['source_commit'] == 'b70ce7bf13ad6a4472f2b089ac812c162b174861'
    assert manifest['owner'] == 'r28-button-support-contrast-v3'
    assets = {str((HERE / name).resolve()): digest for name, digest in manifest['evidence_hosts'].items()}
    assets.update(manifest['diagnostic_host_assets'])
    for path in ([V5 / name for name in ('observer_client.py', 'lineage_host.py', 'runtime_adapter.py', 'source_partition_proof.py')]
            + [OLD / name for name in ('public_entry_host.py', 'payloads.py', 'lifecycle_helpers.py')]
            + [project / 'tools' / name for name in ('verify_debug_blueprints.py', 'verify_transform_runtime_r23.py',
                'verify_debug_visuals.py', 'verify_sign_visuals.py', 'transform_missing_r23.py', 'capture_native_window.py')]):
        assets[str(path.resolve())] = sha(path)
    assert all(sha(path) == expected for path, expected in assets.items())
    value = {'source_manifest': str(manifest_path), 'source_manifest_sha256': sha(manifest_path),
        'project': str(project), 'owner': manifest['owner'], 'side': manifest['side'],
        'host_assets': assets, 'plan_sha256': sha(HERE / 'plan.json'),
        'output': str(HERE / 'check'), 'assertion_status': str(HERE / 'assert-watch/status.json'),
        'assertion_host_sha256': manifest['diagnostic_watcher']['sha256'],
        'session_file': str(HERE / 'UNASSIGNED_SESSION.json'), 'experiment_cutoff': 'UNASSIGNED',
        'session_unassigned': True, 'launch_performed': False,
        'pair_plan': json.loads((HERE / 'plan.json').read_bytes())}
    if not args.prelaunch:
        grant = json.loads((HERE / 'root-review-and-slot-v1.json').read_bytes())
        assert grant['passed'] and grant['source_manifest_sha256'] == sha(manifest_path)
        prelaunch = HERE / 'prelaunch-config.json'
        assert sha(prelaunch) == grant['prelaunch_config_sha256']
        assert assets == json.loads(prelaunch.read_bytes())['host_assets']
        assert datetime.now(timezone.utc) < datetime.fromisoformat(grant['cutoff_utc'])
        sys.path.insert(0, str(project / '.agents/skills/pyreact-debugging/scripts'))
        from _session import load_session
        binding = load_session(args.session, manifest['owner'], live=True)
        assert binding['ready'] and Path(binding['project']).resolve() == project.resolve()
        value.update(session_file=str(args.session.resolve()), experiment_cutoff=grant['cutoff_utc'], session_unassigned=False)
    output = HERE / ('prelaunch-config.json' if args.prelaunch else 'live-config.json')
    assert not output.exists() and not Path(value['output']).exists()
    with output.open('x', encoding='utf8') as destination:
        json.dump(value, destination, indent=2)
        destination.write('\n')
    print(json.dumps({'config': str(output), 'sha256': sha(output), 'host_assets': len(assets),
        'session_unassigned': value['session_unassigned'], 'MC_started': False}))


if __name__ == '__main__':
    main()
