"""Prepare one patterned banner scale comparison using the unchanged v14 packs."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT / '.runtime/banner-pose-control-r21'
PRIOR = ROOT / '.runtime/banner-pose-control-r21-v2'
AMENDMENT = ROOT / '.runtime/banner-pose-v14b-amendment-r21-v1'
OWNER = 'shield-r20-v16-banner-scale-control'
PROJECT = ROOT / '.runtime/projects/shield-r20-v14-banner-pose-control'
OUTPUT = ROOT / '.runtime/banner-scale-control-r21-v1'
POSES = {'yaw90': {'yaw': 90., 'pitch': 0.}}
RELOADS = ('auto_hot_reload_mods', 'auto_hot_reload_ui',
           'auto_hot_reload_shaders', 'auto_hot_reload_materials')
sys.path.insert(0, str(ROOT / 'tools'))
from probe_product_water import snapshot_sources, snapshot_digest


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def save(path, value):
    with path.open('x', encoding='ascii') as handle:
        handle.write(json.dumps(value, ensure_ascii=True, indent=2) + '\n')


def replace(source, before, after):
    assert source.count(before) == 1, before
    return source.replace(before, after, 1)


def templates():
    host = replace((BASE / 'host.py').read_text(encoding='ascii'),
        '.runtime/banner-pose-control-r21/host.py', '.runtime/banner-scale-control-r21/host.py')
    run = (BASE / 'run.py').read_text(encoding='ascii')
    run = replace(run, "'bind', 'pose', 'inspect'", "'bind', 'scale', 'pose', 'inspect'")
    run = replace(run, "default='zero'", "default='yaw90'")
    run = replace(run, "    os.environ.update(MCDEV_SESSION_FILE=str(args.session),", """    import host
    host.validate()
    ready = host.bound(live=True)
    assert ready['id'] == session['id']
    assert not (host.CONTROL / 'stop-request.json').exists()
    exact = prepare.read(host.CONTROL / 'exact-exit.json')
    assert not exact['completed']
    for key in ('game', 'mcdk'):
        assert exact['processes'][key]['state'] == 'live'
        assert exact['processes'][key]['identity'] == session[key + '_identity']
    if args.action not in ('inspect', 'restore', 'absent'):
        proof = prepare.read(OUTPUT / 'runtime-version-config-check.json')
        assert proof['passed'] and proof['session'] == session['id']
        assert all(proof[key + '_identity'] == session[key + '_identity'] for key in ('game', 'mcdk'))
        host.resources()
    os.environ.update(MCDEV_SESSION_FILE=str(args.session),""")
    client = replace((AMENDMENT / 'client.py').read_text(encoding='ascii'),
        "KEY = '_banner_pose_client_v14b_r21'", "KEY = '_banner_scale_client_r21'")
    assert client.count("== 'zero'") == 3
    client = client.replace("== 'zero'", "== 'yaw90'")
    client = replace(client, "'bindings': {}, 'bind_attempted': False,", 
        "'bindings': {}, 'bind_attempted': False, 'scale_attempted': False,")
    client = replace(client, "'bind_attempted': saved['bind_attempted'], 'bindings': saved['bindings'],",
        "'bind_attempted': saved['bind_attempted'], 'bindings': saved['bindings'],\n"
        "                'scale_attempted': saved['scale_attempted'], 'scale_result': saved.get('scale_result'),")
    scale = """            elif ACTION == 'scale':
                assert saved['dolls'] and saved['pose'] == 'yaw90'
                assert LABELS == ['patterned'] and len(saved['bindings']) == 1
                assert not saved['scale_attempted'], 'Never replay scale mutation'
                saved['scale_attempted'] = True
                actor, identity = saved['actors']['patterned'], saved['bindings']['patterned']
                accepted = factory.CreateItem(level).SetBindItemScale(actor, identity, 1., False)
                saved['scale_result'] = accepted
                assert accepted is True, 'Retain binding for cleanup; no retry'
                _result = json.dumps({'scale': 1., 'old_scale': 1. / 16.,
                    'actor': actor, 'identity': identity, 'returned': accepted,
                    'rebound': False, 'render': render(saved)})
"""
    client = replace(client, "            elif ACTION == 'pose':\n", scale + "            elif ACTION == 'pose':\n")
    server = replace((AMENDMENT / 'server.py').read_text(encoding='ascii'),
        "KEY = '_banner_pose_server_v14b_r21'", "KEY = '_banner_scale_server_r21'")
    precheck = (PRIOR / 'runtime-precheck.py').read_text(encoding='ascii')
    precheck = replace(precheck, "'.runtime/banner-pose-control-r21'", "'.runtime/banner-scale-control-r21'")
    precheck = replace(precheck,
        "SESSION = Path('C:/Users/Happy2018new/.pyreact-debug/instances/5986a112da284ef7b0c5fe4d7b75d48e/session.json')",
        "assert len(sys.argv) == 2\nSESSION = Path(sys.argv[1])")
    precheck = replace(precheck, 'run.validate_inputs()\n',
        'run.validate_inputs()\nimport host\nhost.validate()\nhost.resources()\n')
    result = {'host.py': host, 'run.py': run, 'client.py': client, 'server.py': server,
              'precheck.py': precheck}
    for name, source in result.items():
        compile(source, name, 'exec')
    assert 'GetEntityDimensionId' not in client and 'GetCurrentDimension' in client
    return result


def prepare():
    assert not OUTPUT.exists()
    original = read(PRIOR / 'plan.json')
    assert snapshot_sources(PROJECT) == original['files']
    assert snapshot_digest(original['files']) == original['source_sha256']
    assert all(read(PROJECT / '.mcdev.json')[key] is False for key in RELOADS)
    for name, source in templates().items():
        with (HERE / name).open('x', encoding='ascii', newline='\n') as handle:
            handle.write(source)
    OUTPUT.mkdir()
    inputs = read(AMENDMENT / 'inputs.json')
    inputs['items'] = {'patterned': inputs['items']['patterned']}
    save(OUTPUT / 'inputs.json', inputs)
    import layout
    report = layout.estimate()
    assert report['rows'][0]['inside_screen_conservatively']
    save(OUTPUT / 'layout-estimate.json', report)
    references = [PRIOR / 'plan.json', PRIOR / 'launcher-inputs.json', PRIOR / 'runtime-precheck.py',
        AMENDMENT / 'amendment-inputs.json', AMENDMENT / 'inputs.json',
        AMENDMENT / 'runtime-images/01-unbound-negative.png',
        AMENDMENT / 'runtime-images/03-bound-yaw90.png',
        AMENDMENT / 'runtime-receipts/003-banner-client-mount.json',
        ROOT / 'tools/prepare_item_glint_r13.py',
        BASE / 'host.py', BASE / 'run.py', AMENDMENT / 'client.py', AMENDMENT / 'server.py',
        ROOT / 'tools/capture_native_window.py',
        ROOT / '.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/.runtime/native_wgc/build/Release/native_wgc_capture.exe']
    save(OUTPUT / 'plan.json', {'schema': 1, 'owner': OWNER, 'project': str(PROJECT),
        'source_sha256': original['source_sha256'], 'files': original['files'],
        'config_sha256': sha(PROJECT / '.mcdev.json'),
        'host_sha256': {path.name: sha(path) for path in HERE.glob('*.py')},
        'reference_sha256': {str(path): sha(path) for path in references},
        'artifact_sha256': {name: sha(OUTPUT / name) for name in ('inputs.json', 'layout-estimate.json')},
        'host_models': original['host_models'], 'phases': {'banner': ['patterned']}, 'poses': POSES,
        'source_packs_reused_unchanged': True, 'server_actor_budget_per_phase': 1,
        'render_entity_scale': 1.4, 'attachment_rotation': [0., 0., 0.],
        'initial_attachment_scale': 1. / 16., 'only_scale_update': 1.,
        'scale_setter': 'ItemCompClient.SetBindItemScale(entityId,itemModelId,scale,isClientEntity)',
        'scale_setter_attempts': 1, 'no_rebind': True, 'left_slot_unchanged': True,
        'maximum_images': 3, 'automatic_start': False, 'automatic_replay': False,
        'maximum_active_mc': 2, 'minimum_free_commit_gib': 6, 'handle_boundary': 210000,
        'prepared_only': True, 'runtime_started': False, 'production_qualified': False,
        'banner_shape_accepted': False, 'banner_thickness_accepted': False,
        'shared_scene_depth_accepted': False, 'normal_lifecycle_accepted': False})
    verify()


def verify(emit=True):
    plan = read(OUTPUT / 'plan.json')
    assert plan['owner'] == OWNER and not plan['production_qualified']
    assert snapshot_sources(PROJECT) == plan['files']
    assert snapshot_digest(plan['files']) == plan['source_sha256']
    assert sha(PROJECT / '.mcdev.json') == plan['config_sha256']
    for name, digest in plan['host_sha256'].items():
        assert sha(HERE / name) == digest, name
    for path, digest in plan['reference_sha256'].items():
        assert sha(Path(path)) == digest, path
    for name, digest in plan['artifact_sha256'].items():
        assert sha(OUTPUT / name) == digest, name
    for name, source in templates().items():
        assert (HERE / name).read_text(encoding='ascii') == source, name
    if emit:
        print(json.dumps({'verified': True, 'source_sha256': plan['source_sha256'],
                          'templates_exact': True, 'runtime_started': False}))
    return plan


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'verify'))
    {'prepare': prepare, 'verify': verify}[parser.parse_args().action]()
