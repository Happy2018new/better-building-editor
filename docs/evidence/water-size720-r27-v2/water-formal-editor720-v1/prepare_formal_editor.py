"""Prepare one non-trace editor cell; preparation never launches Minecraft."""
import ast
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import sys

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
OLD = WORK.with_name('water-size720-v3')
OWNER = 'water-r27-final41-formal-editor720-v1'
CONTRACT = ROOT / '.runtime/round-20261021/water-startup-protocol-v2/host-contract-v1.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    with (WORK/name).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def main():
    assert not (WORK/'final-source-binding-v1.json').exists()
    patches = []
    names = ('candidate_bootstrap.py', 'bootstrap_payload.py', 'guard_policy.py', 'modal_guard.py',
        'launch_r25.py', 'start_assert_watch.py', 'watch_handles.py', 'run_candidate_bootstrap.py',
        'retire_bootstrap_marker.py', 'resize_adapter.py', 'resize_background.py',
        'run_size_group.py', 'run_diagnostic.py')
    for name in names:
        raw = (OLD/name).read_bytes()
        revised = raw
        if name != 'candidate_bootstrap.py':
            revised = revised.replace(b'water-r27-final41-size720-v3', OWNER.encode())
            revised = revised.replace(b'prelaunch-host-binding-r27-direct.json', b'prelaunch-host-binding-r27.json')
            revised = revised.replace(b'diagnostic-east-editor-size720-v1', b'formal-east-editor-size720-v1')
        if name == 'run_diagnostic.py':
            revised = revised.replace(b'trace-lifetime-v2', b'water-startup-protocol-v2')
            revised = revised.replace(b"'diagnostic_only': True, 'qualification_evidence': False,", 
                b"'diagnostic_only': False, 'qualification_evidence': True, 'sampling_protocol_check_only': True, 'formal_A_accepted': False, 'world_A_accepted': False,")
            revised = revised.replace(b'# Explicit new acquisition protocol; frozen product source remains unchanged.',
                b'# Reviewed non-trace fixed-startup protocol; frozen product source remains unchanged.')
        if name == 'run_size_group.py':
            revised = revised.replace(b'final41-size720-diagnostic', b'final41-formal-editor-single-cell')
            revised = revised.replace(b"if name in ('launch', 'bootstrap', 'G', 'F-editor'):",
                b"if name in ('launch', 'bootstrap', 'resize', 'A', 'G', 'F-editor'):")
            revised = revised.replace(b'No new experiment after 14:55', b'No new experiment after local 07:30')
        (WORK/name).write_bytes(revised)
        if revised != raw:
            patches.extend(difflib.unified_diff(raw.decode('utf-8').splitlines(True),
                revised.decode('utf-8').splitlines(True), fromfile='v3/'+name, tofile='formal-editor/'+name))
    binding = json.loads((OLD/'final-source-binding-v1.json').read_bytes())
    binding.update(owner=OWNER, bootstrap_receipt_marker='_water_r27_formal_editor_bootstrap_v1',
        guard_deadline_utc='2026-10-21T23:45:00+00:00', new_source_bytes_created=False,
        previous_host_binding_sha256=sha(OLD/'prelaunch-host-binding-r27-direct.json'))
    write('final-source-binding-v1.json', binding)
    (WORK/'product-v2-launch-inputs.json').write_bytes((OLD/'product-v2-launch-inputs.json').read_bytes())
    stage = dict(schema=1, round='R27', owner=OWNER, source_contract_sha256=binding['source_contract_sha256'],
        sampling_protocol_check_only=True, formal_A_accepted=False, world_A_accepted=False,
        single_variable_from_v3='lifetime trace helper replaced by reviewed non-trace fixed-startup-v2 helper',
        native_client_area=[1280,720], preparation_ms=1500, measurement_ms=3200, gap_limit_ms=150,
        total_buffer_limit_bytes=536870912, minimum_available_commit_bytes=6442450944,
        maximum_process_handles=250000, maximum_adjacent_handle_growth=10000,
        cases=['flow_east'], routes=['editor'], complete_A_still_requires_15_cells=True,
        world_camera_not_required_for_editor=True, final_merged_source_not_qualified=True,
        no_long_step_after_utc='2026-10-21T23:30:00+00:00', cleanup_deadline_utc=binding['guard_deadline_utc'],
        OS_process_suspension_allowed=False, manual_closures_added=0)
    write('stage-r25.json', stage)
    contract = json.loads(CONTRACT.read_bytes())
    for path, expected in contract['sources'].items():
        assert sha(Path(path)) == expected, path
    assert sha(Path(contract['binary']['path'])) == contract['binary']['sha256']
    project = Path(binding['project'])
    for key in ('source_sha256', 'auxiliary_sha256'):
        for path, expected in binding[key].items():
            assert sha(project/path) == expected, path
    assert sha(Path(binding['archive']['path'])) == binding['archive']['sha256']
    assert sha(WORK/'candidate_bootstrap.py') == binding['bootstrap_sha256']
    assert sha(project/binding['qualification_path']) == binding['qualification_sha256']
    for path in WORK.glob('*.py'):
        ast.parse(path.read_bytes(), filename=str(path))
    sys.path.insert(0, str(WORK))
    from bootstrap_payload import dispatch_code
    payload = dispatch_code((WORK/'candidate_bootstrap.py').read_text('utf-8'), binding)
    (WORK/'dispatched-payload.py').write_text(payload, encoding='utf-8')
    py2 = subprocess.run(['D:/Program/Python27/python.exe', '-B', '-c',
        'import sys;compile(open(sys.argv[1],"rb").read(),sys.argv[1],"exec")',
        str(WORK/'dispatched-payload.py')], capture_output=True, text=True)
    py2.check_returncode()
    previous = json.loads((OLD/'prelaunch-host-binding-r27-direct.json').read_bytes())
    external = {name:sha(ROOT/name) for name in previous['external_host_sha256']}
    write('prelaunch-host-binding-r27.json', dict(schema=1,
        source_binding_sha256=sha(WORK/'final-source-binding-v1.json'),
        host_sha256={path.name:sha(path) for path in WORK.glob('*.py')} |
            {name:sha(WORK/name) for name in ('product-v2-launch-inputs.json','stage-r25.json')},
        external_host_sha256=external, startup_contract_sha256=sha(CONTRACT),
        startup_contract_path=str(CONTRACT), startup_binary=contract['binary'],
        MC_started=False, frozen_at_utc=datetime.now(timezone.utc).isoformat()))
    (WORK/'v3-to-nontrace-editor.patch').write_text(''.join(patches), encoding='utf-8')
    write('prelaunch-review-v1.json', dict(schema=1, passed=True, MC_started=False,
        owner=OWNER, source_files=len(binding['source_sha256']), auxiliary_files=len(binding['auxiliary_sha256']),
        source_unchanged=True, original_core_sha256=sha(WORK/'candidate_bootstrap.py'),
        source_contract_sha256=binding['source_contract_sha256'],
        binding_sha256=sha(WORK/'prelaunch-host-binding-r27.json'),
        python2_compile_exit=py2.returncode, sampling_protocol_check_only=True,
        formal_A_accepted=False, world_A_accepted=False, production_admission_performed=False,
        manual_closures_added=0))
    print(json.dumps(dict(passed=True, MC_started=False, owner=OWNER,
        review_sha256=sha(WORK/'prelaunch-review-v1.json'),
        binding_sha256=sha(WORK/'prelaunch-host-binding-r27.json'))))


if __name__ == '__main__':
    main()
