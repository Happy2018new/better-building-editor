"""Freeze offline holdout inputs and exact commands without starting a game."""
import ast
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DESTINATION = HERE / 'holdout-prepare-v1'
SPEC = importlib.util.spec_from_file_location('lectern_holdout', HERE / 'probe_holdout.py')
HOST = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HOST)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if DESTINATION.exists():
        raise ValueError('Choose a fresh frozen preparation directory')
    prelaunch = json.loads((HERE / 'prelaunch-v1.json').read_bytes())
    project = Path(prelaunch['project'])
    sources = HOST.BASE.snapshot_sources(project)
    if sources != prelaunch['source_sha256']:
        raise ValueError('The sealed business candidate changed')
    config = json.loads((project / '.mcdev.json').read_bytes())
    if any(config.get(key) is not False for key in ('auto_hot_reload_mods', 'auto_hot_reload_ui',
                                                   'auto_hot_reload_shaders', 'auto_hot_reload_materials')):
        raise ValueError('All four hot reload settings must remain false')
    candidate = project / 'behavior_pack/modern_projection/projection/lectern_body.py'
    flags = [node for node in ast.parse(candidate.read_text(encoding='ascii')).body
             if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and
                target.id == 'CANDIDATE_ENABLED' for target in node.targets)]
    if len(flags) != 1 or ast.literal_eval(flags[0].value) is not False:
        raise ValueError('The isolated source gate must remain closed')
    capture = ROOT / '.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/.runtime/native_wgc/build/Release/native_wgc_capture.exe'
    mcdk = ROOT / '.runtime/mcdk-retry-r11/build-ipc-framing-r11/tools/mcdk/mcdk.exe'
    guard = ROOT / 'docs/evidence/background-focus-r13-v1/inputs/native_focus_guard.dll'
    if sha(capture) != HOST.BASE.SINGLE_FRAME_SHA256:
        raise ValueError('The single-frame native capture helper changed')
    mcdk_sha = 'b8eb8959f97a4348006837bb7897d1e5cb957855d1746145974d8f37c00be9f9'
    guard_sha = '04b073e1aea6fe16a70573e64c6aac31940431409ac90c79f250e02f35a3ec93'
    if sha(mcdk) != mcdk_sha or sha(guard) != guard_sha:
        raise ValueError('The previously exercised noactivation launch inputs changed')
    owner = 'book-r20-holdout-r21-v1'
    checks = HOST.check_templates()
    from probe_product_water import snapshot_digest
    paths = {Path('host') / name: HERE / name for name in (
        'probe_runtime.py', 'probe_runtime_v2.py', 'probe_runtime_v3.py',
        'probe_holdout.py', 'prepare_holdout.py')}
    paths.update({Path('dependencies') / name: ROOT / 'tools' / name for name in (
        'probe_liquid_pose_channel.py', 'probe_product_water.py', 'capture_native_window.py',
        'verify_debug_blueprints.py', 'context_test_environment.py', 'verify_biome_shader.py',
        'watch_intrinsic_glint_exit_r21.py')})
    DESTINATION.mkdir()
    files = {}
    for relative, source in paths.items():
        target = DESTINATION / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        files[relative.as_posix()] = dict(sha256=sha(target), bytes=target.stat().st_size)
    record = dict(schema=1, created_at=datetime.now(timezone.utc).isoformat(),
        stage='offline_prepared_single_lectern_cardinal_holdout', project=str(project),
        intended_owner=owner, process_started=False, runtime_executed=False,
        root_mc_slot_assigned=False, product_qualified=False, tests=checks,
        source_sha256=sources, source_digest=snapshot_digest(sources),
        config_sha256=sha(project / '.mcdev.json'), host_sha256=sha(HERE / 'probe_holdout.py'),
        source_gate_enabled=False, native_capture_helper=dict(path=str(capture), sha256=sha(capture)),
        files=files, environment={'MCDEV_ALLOW_USER_FOREGROUND': '1'},
        launch_command=['python', '-X', 'utf8', str(ROOT / '.agents/skills/pyreact-debugging/scripts/instances.py'),
            'start', '--project', str(project), '--owner', owner, '--mcdk', str(mcdk),
            '--noactivate-dll', str(guard), '--noactivate-sha256', guard_sha,
            '--noactivate-mcdk-sha256', mcdk_sha, '--wait', '180'],
        capture_command=['python', '-X', 'utf8', str(HERE / 'probe_holdout.py'), '--session', '<assigned-session.json>',
            '--owner', owner, '--project', str(project), '--output', str(HERE / 'runtime-holdout-v1'),
            '--capture-exe', str(capture)],
        invariants=['Four real unpowered cardinal source states, one isolated target per case.',
            'The only lectern neighbor is its cyan lower support; native receipt count must be exactly one.',
            'Hidden lectern target emits no body or book while its cyan support remains.',
            'Cyan-only uses two native cyan cells; hiding the upper cell must leave only the lower support.',
            'Book body-only phase must contain no custom book and no native book duplicate.',
            'One fixed oblique camera; this is four block directions, not four cameras.',
            'No native book pixel parity or powered appearance claim.',
            'Root must assign MC/WGC; recheck real process identities and retain exact exit handles before sampling.'])
    (DESTINATION / 'manifest.json').write_text(json.dumps(record, indent=2) + '\n', encoding='ascii')
    print(json.dumps(dict(directory=str(DESTINATION), manifest_sha256=sha(DESTINATION / 'manifest.json'),
        host_sha256=record['host_sha256'], files=len(files), source_digest=record['source_digest'],
        planned_captures=checks['planned_captures'], compiled_templates=checks['compiled_templates'])))


if __name__ == '__main__':
    main()
