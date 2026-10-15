"""Record a cold candidate source snapshot without launching any process."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PROJECT = ROOT / '.runtime/projects/book-r20'
sys.path.insert(0, str(ROOT / 'tools'))
from probe_product_water import snapshot_sources, snapshot_digest


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    destination = HERE / 'prelaunch-v1.json'
    if destination.exists():
        raise ValueError('Use a fresh prelaunch record')
    config = json.loads((PROJECT / '.mcdev.json').read_bytes())
    keys = ('auto_hot_reload_mods', 'auto_hot_reload_ui',
            'auto_hot_reload_shaders', 'auto_hot_reload_materials')
    if any(config.get(key) is not False for key in keys):
        raise ValueError('All hot reload settings must remain false')
    candidate = PROJECT / 'behavior_pack/modern_projection/projection/lectern_body.py'
    flags = [node for node in ast.parse(candidate.read_text(encoding='ascii')).body
             if isinstance(node, ast.Assign) and any(
                 isinstance(target, ast.Name) and target.id == 'CANDIDATE_ENABLED'
                 for target in node.targets)]
    if len(flags) != 1 or ast.literal_eval(flags[0].value) is not False:
        raise ValueError('The isolated source candidate must default to closed')
    sources = snapshot_sources(PROJECT)
    report = dict(schema=1, project=str(PROJECT), created_at=time.time(),
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        intended_owner='book-r20-candidate-r21-v1',
        process_started=False, runtime_host_executed=False, product_qualified=False,
        candidate_enabled_in_source=False, runtime_candidate_assignment_expected=True,
        config_sha256=sha(PROJECT / '.mcdev.json'),
        source_sha256=sources, source_digest=snapshot_digest(sources),
        host_sha256=sha(HERE / 'probe_runtime.py'),
        offline_evidence_manifest_sha256=sha(HERE / 'offline-snapshot-v1/manifest.json'),
        gate='Wait for explicit root MC-slot scheduling; preflight is not a launch authorization.')
    destination.write_text(json.dumps(report, indent=2), encoding='ascii')
    print(json.dumps(dict(path=str(destination), sources=len(sources), source_digest=report['source_digest'],
                         prelaunch_sha256=sha(destination))))


if __name__ == '__main__':
    main()
