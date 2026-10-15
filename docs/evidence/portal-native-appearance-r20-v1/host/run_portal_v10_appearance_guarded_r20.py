"""Acquire independent finite-face starfield runs under canonical commit gates."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from census_intrinsic_glint_ui_r21 import commit_at_boundary
from probe_product_water import snapshot_sources
import probe_portal_reference_r19 as probe

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--families', nargs='+', choices=('end_gateway', 'end_portal'),
                    default=('end_gateway', 'end_portal'))
parser.add_argument('--views', nargs='+', choices=('front', 'oblique'),
                    default=('front', 'oblique'))
args = parser.parse_args()
assert len(args.families) == len(set(args.families))
assert len(args.views) == len(set(args.views))
project = ROOT / '.runtime/projects/portal-r20-native-v10'
control = ROOT / '.runtime/portal-native-control-r20-v10'
ready = json.loads((control / 'ready-summary.json').read_bytes())
assert ready['state'] == 'ready' and ready['owner'] == 'portal-r20-native-v10'
frozen = json.loads((control / 'launch-inputs.json').read_bytes())['files']
assert snapshot_sources(project) == frozen
assert hashlib.sha256((ROOT / 'tools/probe_portal_reference_r19.py').read_bytes()).hexdigest() == frozen['tools/probe_portal_reference_r19.py']
assert hashlib.sha256((ROOT / 'tools/census_intrinsic_glint_ui_r21.py').read_bytes()).hexdigest() == frozen['tools/census_intrinsic_glint_ui_r21.py']
memory_log = {'metric': 'CommitLimit-CommitTotal', 'threshold_bytes': 6 * 1024 ** 3,
              'physical_memory_is_a_gate': False, 'families': args.families,
              'views': args.views, 'boundaries': [],
              'canonical_source_sha256': frozen['tools/census_intrinsic_glint_ui_r21.py'],
              'guard_host_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'frozen_probe_sha256': frozen['tools/probe_portal_reference_r19.py']}
memory_path = control / ('runtime-memory-boundaries-' + '-'.join(args.families) +
                         '-' + '-'.join(args.views) + '.json')
assert not memory_path.exists(), 'Never overwrite an observed capture run'


def boundary(name, require=True):
    row = dict(commit_at_boundary(), boundary=name)
    row['commit_gate_passed'] = row['commit_available_bytes'] >= memory_log['threshold_bytes']
    memory_log['boundaries'].append(row)
    memory_path.write_text(json.dumps(memory_log, indent=2)+'\n', encoding='ascii', newline='\n')
    if require and not row['commit_gate_passed']:
        raise RuntimeError('Available commit fell below 6 GiB at ' + name)


original_capture = probe.capture


def guarded_capture(session, owner, path, backend):
    boundary('before_' + path.stem)
    result = original_capture(session, owner, path, backend)
    boundary('after_' + path.stem)
    return result


probe.capture = guarded_capture
for family in args.families:
    boundary('before_' + family)
    suffix = '' if args.views == ['front', 'oblique'] or args.views == ('front', 'oblique') else '-' + '-'.join(args.views)
    output = ROOT / ('.runtime/portal-appearance-r20-v10-' + family + suffix)
    assert not output.exists(), 'Capture output must be fresh'
    sys.argv = [str(ROOT / 'tools/probe_portal_reference_r19.py'),
                '--project', str(project), '--session', ready['session_file'], '--owner', ready['owner'],
                '--output', str(output), '--native-adapter', '--adapter-prefix', 'r19_native_portal_',
                '--families', family, '--views'] + list(args.views) + [
                '--near-player', '--end-portal-front-elevation', '2.2']
    try:
        probe.main()
    finally:
        boundary('after_' + family + '_cleanup', require=False)
    report = json.loads((output / 'report.json').read_bytes())
    assert report['completed'] and report['restored'] and report['project_source_unchanged']
    assert report['all_surfaces_visible'], 'A true starfield surface failed its visibility gate'
    assert len(report['captures']) == 2 * len(args.views), 'Unexpected appearance capture count'
