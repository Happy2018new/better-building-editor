"""Preserve eight bound, unnormalized portal appearance captures and exits."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from probe_product_water import snapshot_digest, snapshot_sources
from _session import process_identity


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2)+'\n', encoding='ascii', newline='\n')


package = ROOT / 'docs/evidence/portal-native-appearance-r20-v1'
control = ROOT / '.runtime/portal-native-control-r20-v10'
project = ROOT / '.runtime/projects/portal-r20-native-v10'
assert not package.exists()
frozen = json.loads((control / 'launch-inputs.json').read_bytes())['files']
assert snapshot_sources(project) == frozen
assert snapshot_digest(frozen) == '90abd667504357ed1e7172d22d4e29ad56ba6485f84a7de8de5eedddbb87248e'
ready = json.loads((control / 'ready-summary.json').read_bytes())
session_path = Path(ready['session_file'])
session = json.loads(session_path.read_bytes())
assert session['owner'] == 'portal-r20-native-v10' and session['state'] == 'stopped'
exits = json.loads((control / 'exact-exit-observation.json').read_bytes())
assert exits['completed'] and exits['processes']['game']['exit_code_hex'] == '0xC0000409'
assert exits['processes']['mcdk']['exit_code'] == 0
stopped = {'owner': session['owner'], 'state': session['state'],
           'observed_at_utc': datetime.now(timezone.utc).isoformat(),
           'first_normal_stop_returncode': 1, 'normal_finalize_returncode': 0,
           'finalized_after_exact_identities_exited': True, 'force_used': False,
           'normal_exit_accepted': False, 'session_sha256': sha(session_path), 'processes': {}}
for kind in ('game', 'mcdk'):
    pid, identity = session[kind+'_pid'], session[kind+'_identity']
    current = process_identity(pid)
    assert current != identity
    stopped['processes'][kind] = {'pid': pid, 'identity': identity,
                                'observed_identity': current, 'owned_process_exited': True}

copies = {}
for name in ('analyze_portal_reference_appearance_r20.py', 'probe_portal_reference_r19.py',
             'census_intrinsic_glint_ui_r21.py'):
    assert sha(ROOT / 'tools' / name) == frozen['tools/'+name]
    copies['host/'+name] = project / 'tools' / name
copies['host/watch_intrinsic_glint_exit_r21.py'] = ROOT / 'tools/watch_intrinsic_glint_exit_r21.py'
for name in ('prepare_portal_appearance_r20_v10.py', 'verify_portal_v10_preflight_r20.py',
             'start_portal_v10_observed_r20.py', 'start_portal_prepared_r20.py',
             'run_portal_v10_appearance_guarded_r20.py', 'pack_portal_appearance_r20_v10.py'):
    copies['host/'+name] = ROOT / '.runtime' / name
for name in ('prepared-summary.json', 'preflight-summary.json', 'ready-summary.json',
             'launch-inputs.json', 'exact-exit-observation.json', 'appearance-plan.json',
             'prelaunch-process-identities.json', 'first-pair-review.json'):
    copies['launch/'+name] = control / name
copies['compiled/compile.json'] = ROOT / '.runtime/portal-appearance-compile-r20-v10/compile.json'
copies['frozen/mcdev-config.json'] = project / '.mcdev.json'
for relative in (
    'resource_pack/materials/portal.material', 'resource_pack/materials/entity.material',
    'resource_pack/models/netease_models.json',
    'resource_pack/shaders/glsl/r19_native_portal_world.vertex',
    'resource_pack/shaders/glsl/r19_native_portal_native.fragment',
    'resource_pack/shaders/glsl/r19_native_portal_original.h',
    'resource_pack/models/modern_projection/portal/r19_native_portal_end_gateway_mesh.json',
    'resource_pack/models/modern_projection/portal/r19_native_portal_end_portal_mesh.json',
    'resource_pack/textures/models/modern_projection/portal/r19_native_starfield.png',
    'resource_pack/textures/models/modern_projection/portal/end_portal_colors.png'):
    assert sha(project / relative) == frozen[relative]
    copies['frozen/'+relative] = project / relative

batch_names = ('end_gateway-front', 'end_gateway-oblique', 'end_portal')
reports = []
captures = 0
for name in batch_names:
    folder = ROOT / ('.runtime/portal-appearance-r20-v10-'+name)
    report = json.loads((folder / 'report.json').read_bytes())
    assert all(report[key] for key in ('completed', 'restored', 'source_unchanged',
                                        'project_source_unchanged', 'all_surfaces_visible'))
    assert not report['cleanup_errors']
    assert len(report['captures']) == (4 if name == 'end_portal' else 2)
    captures += len(report['captures'])
    copies['observed/'+name+'/report.json'] = folder / 'report.json'
    reports.append(package / 'observed' / name / 'report.json')
    for key, row in report['captures'].items():
        capture = row['capture']
        assert capture['sha256'] == sha(folder / (key+'.png'))
        for suffix in ('.png', '.capture.json'):
            copies['observed/'+name+'/'+key+suffix] = folder / (key+suffix)
assert captures == 8
copies['observed/absolute-appearance.json'] = control / 'absolute-appearance.json'
boundaries = []
for path in sorted(control.glob('runtime-memory-boundaries-*.json')):
    memory = json.loads(path.read_bytes())
    assert memory['canonical_source_sha256'] == frozen['tools/census_intrinsic_glint_ui_r21.py']
    assert memory['guard_host_sha256'] == sha(ROOT / '.runtime/run_portal_v10_appearance_guarded_r20.py')
    assert all(row['commit_gate_passed'] for row in memory['boundaries'])
    boundaries.extend(memory['boundaries'])
    copies['launch/'+path.name] = path
assert len(boundaries) == 22

package.mkdir(parents=True)
for name, source in copies.items():
    target = package / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
write(package / 'launch/stopped-summary.json', stopped)
analysis = json.loads((control / 'absolute-appearance.json').read_bytes())
pairs = {key: row for report in analysis['reports'] for key, row in report['pairs'].items()}
write(package / 'observed/bounded-summary.json', {
    'source_contract_sha256': snapshot_digest(frozen), 'capture_count': captures,
    'all_eight_actual_images_opened': True, 'first_pair_reviewed_before_remaining_captures': True,
    'all_runs_completed_restored_source_unchanged': True, 'cleanup_errors': [],
    'all_commit_gates_passed': True, 'runtime_boundary_count': len(boundaries),
    'minimum_commit_available_bytes': min(row['commit_available_bytes'] for row in boundaries),
    'physical_memory_is_a_gate': False,
    'candidate_to_native_ratios': {key: row['candidate_to_native_ratios'] for key, row in pairs.items()},
    'native_end_portal_front_gray_smoke_overlaps_measured_surface': True,
    'gray_smoke_is_not_detected_by_magenta_rule': True,
    'particle_pixels_removed': False, 'phase_or_exposure_fit': False,
    'pixel_acceptance': False, 'qualification': False, 'production_resources_changed': False})
readme = '''# Raw native portal appearance, R20 v10

This package preserves eight fresh WGC images from frozen clone SHA
90abd667504357ed1e7172d22d4e29ad56ba6485f84a7de8de5eedddbb87248e.
The candidate retains the measured v9 world-ray correction, native 16-plane
layout, original native starfield fragment, and restored vanilla portal.material.
Actual shader, material, mesh, registry and texture inputs are included.
The source map binds the wider unchanged clone; this is not a complete
standalone runnable world, SDK or imported-host dependency closure.

The gateway front pair was captured, fully restored, opened and analyzed
before any remaining view. Gateway oblique was then captured and restored;
the End portal front and oblique four-image run followed. The private wrapper
adds a view selection and separate memory receipts to permit that review.
Its exact bytes are bound by the launch preflight receipt. The frozen probe,
BP/RP source map and canonical memory function remain unchanged.
Every run completed and restored with unchanged host and project sources;
cleanup errors are empty. All eight actual images were manually opened.

Native references are real native blocks. Gateway measurements use the
interior north face; End portal measurements use the interior top face.
The geometric mask is eroded by 5 pixels and identical for each matched pair.
No phase fitting, exposure fitting, particle deletion or pixel exclusion is
applied inside those finite-face masks. Native beams and exterior particles
are outside the finite-surface comparison, not a qualified candidate effect.

Candidate/native raw mean-luminance, cyan-star and nonblack ratios:

| Pair | Mean Luma | Cyan Coverage | Nonblack Coverage |
| --- | ---: | ---: | ---: |
| Gateway front | 0.933728 | 0.903353 | 0.937122 |
| Gateway oblique | 1.016178 | 1.013051 | 1.005376 |
| End portal front | 0.814418 | 1.122067 | 0.859572 |
| End portal oblique | 1.052021 | 1.100746 | 1.081863 |

The native End portal front image visibly contains gray smoke overlapping
the sampled top face. It remains in the raw brightness and nonblack values.
The magenta contamination count is zero but does not detect gray smoke.
Therefore that front pair cannot isolate pure-starfield brightness equivalence.
Other fresh pairs sample different animation phases; these bounded numbers
do not establish native-equivalent density, brightness or animation.

All four reload flags were false. Canonical available commit is CommitLimit
minus CommitTotal from psapi.GetPerformanceInfo. Prestart available commit was
11680464896 bytes; all 22 runtime boundaries passed 6 GiB, with minimum
8879247360 bytes. Physical available RAM is recorded but is not another gate.
The prelaunch process census found zero valid MC process identities despite
14 stale CIM records. No existing process was terminated or mutated.

The first normal stop returned 1. Immediately retained exact process handles
recorded MC2188 exit 0xC0000409 at 2026-10-16 03:44:47.952 Asia/Shanghai and
MCDK37656 exit 0 at 03:44:48.954. This is not an accepted normal exit, and its
cause is not established by these images. After both exact identities were
absent, normal stop finalized metadata with return code 0 and state stopped.
No force stop was used. All portal exec sessions ended before MC/WGC release.

Offline raw-statistics replay from this package directory:

```powershell
python -B host/analyze_portal_reference_appearance_r20.py --report observed/end_gateway-front/report.json --report observed/end_gateway-oblique/report.json --report observed/end_portal/report.json --output absolute-replay.json
```

Replay bytes were checked against observed/absolute-appearance.json. Raw
session/start/stop responses remain private. The manifest hashes raw bytes,
including native source bytes without text conversion.

No production renderer or profile was changed. Native density/brightness,
animation, opacity, missing blocks, UI, other faces and lifecycle qualification
remain open. No animation or further matrix was run in this allocation.
'''
(package / 'README.md').write_text(readme, encoding='ascii', newline='\n')
(package / '.gitattributes').write_text('* -text\n', encoding='ascii', newline='\n')
replay = ROOT / '.runtime/portal-appearance-replay-r20-v10.json'
assert not replay.exists()
command = [sys.executable, '-B', '-X', 'utf8',
           str(package / 'host/analyze_portal_reference_appearance_r20.py')]
for report in reports:
    command.extend(('--report', str(report)))
command.extend(('--output', str(replay)))
subprocess.run(command, cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
assert replay.read_bytes() == (package / 'observed/absolute-appearance.json').read_bytes()


def inspect(value, path):
    if isinstance(value, dict):
        for key, child in value.items():
            assert key.lower() not in ('token', 'authorization', 'access_token', 'secret',
                                       'mcp_url', 'ipc_token'), (path, key)
            inspect(child, path)
    elif isinstance(value, list):
        for child in value:
            inspect(child, path)


for path in package.rglob('*.json'):
    inspect(json.loads(path.read_bytes()), path)
manifest = {path.relative_to(package).as_posix(): sha(path)
            for path in package.rglob('*') if path.is_file()}
write(package / 'manifest.json', manifest)
print(json.dumps({'files': len(manifest)+1, 'manifest_entries': len(manifest),
                  'bytes': sum(path.stat().st_size for path in package.rglob('*') if path.is_file()),
                  'absolute_decoder_byte_replayed': True, 'credential_key_hits': 0,
                  'qualification': False}))
