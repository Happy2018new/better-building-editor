"""Run the frozen two-capture route with canonical commit checks at boundaries."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from census_intrinsic_glint_ui_r21 import commit_at_boundary
import probe_portal_reference_r19 as probe

control = ROOT / '.runtime/portal-native-control-r20-v9'
ready = json.loads((control / 'ready-summary.json').read_bytes())
assert ready['state'] == 'ready' and ready['owner'] == 'portal-r20-native-v9'
memory_log = {'metric': 'CommitLimit-CommitTotal', 'threshold_bytes': 6 * 1024 ** 3,
              'physical_memory_is_a_gate': False, 'boundaries': [],
              'canonical_source_sha256': hashlib.sha256((ROOT / 'tools/census_intrinsic_glint_ui_r21.py').read_bytes()).hexdigest(),
              'guard_host_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'frozen_probe_sha256': hashlib.sha256((ROOT / 'tools/probe_portal_reference_r19.py').read_bytes()).hexdigest()}


def boundary(name, require=True):
    row = dict(commit_at_boundary(), boundary=name)
    row['commit_gate_passed'] = row['commit_available_bytes'] >= memory_log['threshold_bytes']
    memory_log['boundaries'].append(row)
    (control / 'runtime-memory-boundaries.json').write_text(json.dumps(memory_log, indent=2)+'\n', encoding='ascii', newline='\n')
    if require and not row['commit_gate_passed']:
        raise RuntimeError('Available commit fell below the authorized 6 GiB gate at ' + name)


original_capture = probe.capture


def guarded_capture(session, owner, path, backend):
    boundary('before_' + path.stem)
    result = original_capture(session, owner, path, backend)
    boundary('after_' + path.stem)
    return result


boundary('before_pair')
probe.capture = guarded_capture
sys.argv = [str(ROOT / 'tools/probe_portal_reference_r19.py'),
            '--project', str(ROOT / '.runtime/projects/portal-r20-native-v9'),
            '--session', ready['session_file'], '--owner', ready['owner'],
            '--output', str(ROOT / '.runtime/portal-coordinate-readback-r20-v9'),
            '--native-adapter', '--adapter-prefix', 'r19_native_portal_',
            '--families', 'end_gateway', '--views', 'front', '--near-player', '--record-absent']
try:
    probe.main()
finally:
    boundary('after_pair_cleanup', require=False)
