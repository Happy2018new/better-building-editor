"""Frozen authentic-shield comparison; first two captures require visual review."""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
ROUND = 'v7-authentic'
OWNER = 'shield-r20-' + ROUND
PROJECT = ROOT / ('.runtime/projects/shield-r20-' + ROUND)
CONTROL = ROOT / ('.runtime/shield-r20-control-' + ROUND)
OUTPUT = ROOT / '.runtime/shield-authentic-r21-v1'
SCRIPTS = ROOT / '.agents/skills/pyreact-debugging/scripts'
WGC = ROOT / '.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/.runtime/native_wgc/build/Release/native_wgc_capture.exe'
sys.path[:0] = [str(SCRIPTS), str(ROOT / 'tools')]
from _session import load_session, process_identity
from mcdk import Client, return_value
from probe_product_water import snapshot_sources, snapshot_digest
from census_intrinsic_glint_ui_r21 import commit_at_boundary
from capture_native_window import capture

RELOADS = ('auto_hot_reload_mods', 'auto_hot_reload_ui',
           'auto_hot_reload_shaders', 'auto_hot_reload_materials')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def save(name, value):
    with (OUTPUT / name).open('x', encoding='ascii') as handle:
        handle.write(json.dumps(value, ensure_ascii=True, indent=2) + '\n')
    return value


def census():
    result = subprocess.run(['powershell.exe', '-NoProfile', '-Command',
        '@(Get-CimInstance Win32_Process -Filter "Name=\'Minecraft.Windows.exe\'" | '
        'Select-Object ProcessId,HandleCount) | ConvertTo-Json -Compress'],
        capture_output=True, encoding='utf-8-sig', check=True, timeout=20,
        creationflags=subprocess.CREATE_NO_WINDOW)
    rows = json.loads(result.stdout or '[]')
    if not isinstance(rows, list):
        rows = [rows]
    for row in rows:
        row['identity'] = process_identity(row['ProcessId'])
    return [row for row in rows if row['identity'] is not None]


def resource_guard(label, launch=False):
    games, commit = census(), commit_at_boundary()
    save(label + '-resources.json', {'label': label, 'games': games, 'commit': commit,
        'launch': launch, 'at': datetime.now(timezone.utc).isoformat()})
    assert len(games) <= (1 if launch else 2), 'Global MC limit'
    assert commit['commit_available_bytes'] >= 6 * 1024 ** 3, 'Free commit below 6 GiB'
    if not launch:
        session = bound()
        own = [row for row in games if row['ProcessId'] == session['game_pid']
               and row['identity'] == session['game_identity']]
        assert len(own) == 1 and own[0]['HandleCount'] < 210000, 'Owned handle boundary'


def prepare():
    assert not any(path.exists() for path in (OUTPUT, PROJECT, CONTROL))
    OUTPUT.mkdir()
    source = ROOT / 'docs/evidence/shield-native-crafter-r21-v1/records/authentic-shield.json'
    raw = read(source)
    assert raw['native_crafting_output_acquired'] and not raw['native_nbt_injection']
    authentic = copy.deepcopy(raw['item'])
    assert authentic['newItemName'] == 'minecraft:shield' and authentic['newAuxValue'] == 0
    assert authentic['userData']['Base'] == {'__type__': 3, '__value__': 4}
    assert authentic['userData']['Damage'] == {'__type__': 3, '__value__': 0}
    save('inputs.json', {'items': {
        'plain': {'newItemName': 'minecraft:shield', 'newAuxValue': 0, 'count': 1,
                  'durability': 336, 'enchantData': []},
        'authentic': authentic,
        'sword': {'newItemName': 'minecraft:diamond_sword', 'newAuxValue': 0, 'count': 1}},
        'authentic_source': str(source.relative_to(ROOT)).replace('\\', '/'),
        'authentic_source_sha256': sha(source), 'authentic_raw': raw,
        'userdata_copied_exactly': True, 'production_qualified': False})
    result = subprocess.run([sys.executable, '-B', '-X', 'utf8',
        str(ROOT / '.runtime/prepare_shield_r20.py'), '--round', ROUND,
        '--native-discovery', '--prepare-only'], cwd=ROOT, capture_output=True,
        encoding='utf8', check=True, timeout=120)
    save('clone-prepare.json', json.loads(result.stdout))
    config = read(PROJECT / '.mcdev.json')
    assert all(config[key] is False for key in RELOADS)
    model_name = 'modern_projection_item_icon_d19ff5bff710ac9e'
    model_files = [path for path in (PROJECT / 'resource_pack').rglob('*.json')
                   if model_name.encode('ascii') in path.read_bytes()]
    assert model_files, 'Known host model registration absent'
    files = [Path(__file__), HERE / 'client.py', HERE / 'server.py',
        ROOT / '.runtime/prepare_shield_r20.py', ROOT / '.runtime/shield_instances_native_discovery_r20.py',
        ROOT / '.runtime/shield_stop_owned_r20.py', ROOT / '.runtime/shield_lifecycle_read_r20.py',
        ROOT / 'tools/watch_intrinsic_glint_exit_r21.py', ROOT / 'tools/capture_native_window.py',
        ROOT / 'tools/diagnose_window_dpi.py', ROOT / 'tools/census_intrinsic_glint_ui_r21.py',
        ROOT / 'tools/probe_product_water.py', WGC, OUTPUT / 'inputs.json', source]
    files += [SCRIPTS / name for name in ('instances.py', '_session.py', '_window.py', 'mcdk.py')]
    files += sorted(path for path in (ROOT / 'tools/native_wgc').iterdir() if path.is_file())
    frozen = read(CONTROL / 'launch-inputs.json')
    save('plan.json', {'schema': 1, 'owner': OWNER, 'prepared_only': True,
        'source_contract_sha256': frozen['source_contract_sha256'],
        'config_sha256': sha(PROJECT / '.mcdev.json'),
        'host_files_sha256': {str(path.relative_to(ROOT)).replace('\\', '/'): sha(path) for path in files},
        'known_host_model_files': {str(path.relative_to(PROJECT)).replace('\\', '/'): sha(path)
                                   for path in model_files},
        'maximum_active_mc': 2, 'minimum_free_commit_gib': 6, 'handle_boundary': 210000,
        'all_four_reload_flags_false': True, 'desktop_input': False,
        'item_payload_mutation': False, 'native_frame_cells': 4, 'air_guard_cells': 96,
        'first_two_review_required': True, 'native_positive_required': True,
        'image_budget': 9, 'workspace_candidate_only': True, 'production_qualified': False,
        'cases': ['native_ui_unbound_negative', 'native_ui_bound_front', 'bound_oblique',
                  'bound_back', 'bound_side', 'actual_frame_front', 'actual_frame_oblique',
                  'workspace_candidate_front', 'workspace_candidate_oblique']})
    print(json.dumps({'prepared_only': True, 'started': False, 'owner': OWNER,
        'source_contract_sha256': frozen['source_contract_sha256'], 'plan': str(OUTPUT / 'plan.json')}))


def validate():
    plan = read(OUTPUT / 'plan.json')
    assert plan['owner'] == OWNER and not plan['production_qualified']
    for relative, expected in plan['host_files_sha256'].items():
        assert sha(ROOT / relative) == expected, 'Frozen host changed: ' + relative
    sources = snapshot_sources(PROJECT)
    frozen = read(CONTROL / 'launch-inputs.json')
    assert sources == frozen['files'] and snapshot_digest(sources) == plan['source_contract_sha256']
    assert sha(PROJECT / '.mcdev.json') == plan['config_sha256']
    assert all(read(PROJECT / '.mcdev.json')[key] is False for key in RELOADS)
    inputs = read(OUTPUT / 'inputs.json')
    assert inputs['items']['authentic'] == inputs['authentic_raw']['item']
    return plan


def bound(live=True):
    ready = read(CONTROL / 'ready-summary.json')
    session = load_session(ready['session_file'], OWNER)
    assert Path(session['project']).resolve() == PROJECT.resolve()
    for key in ('owner', 'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity'):
        assert ready[key] == session[key], 'Owned identity changed: ' + key
    if live:
        for kind in ('game', 'mcdk'):
            assert process_identity(session[kind + '_pid']) == session[kind + '_identity']
    return session


def launch():
    validate()
    assert not (CONTROL / 'start.stdout.json').exists()
    resource_guard('prelaunch', launch=True)
    result = subprocess.run([sys.executable, '-B', '-X', 'utf8',
        str(ROOT / '.runtime/prepare_shield_r20.py'), '--round', ROUND,
        '--native-discovery', '--launch-prepared'], cwd=ROOT, capture_output=True,
        encoding='utf8', timeout=320)
    save('launch-host-result.json', {'returncode': result.returncode,
        'stdout': result.stdout, 'stderr': result.stderr})
    assert result.returncode == 0, 'Inspect exact startup receipt before any retry'
    session = bound()
    print(json.dumps({key: session[key] for key in ('owner', 'session_file', 'game_pid',
        'game_identity', 'mcdk_pid', 'mcdk_identity')}))


class Probe:
    def __init__(self):
        self.inputs = read(OUTPUT / 'inputs.json')
        self.actors = read(OUTPUT / 'actors.json') if (OUTPUT / 'actors.json').exists() else {}
        self.sequence = max([int(path.name.split('-', 1)[0])
            for path in OUTPUT.glob('[0-9][0-9]-*.json')] + [0])

    def call(self, action, client=True, config=None):
        session = bound()
        os.environ.update(MCDEV_SESSION_FILE=session['session_file'], MCDEV_OWNER=OWNER,
                          MCDEV_ALLOW_USER_FOREGROUND='1')
        code_path = HERE / ('client.py' if client else 'server.py')
        code = 'ACTION = %r\nINPUTS = %r\nACTORS = %r\nCONFIG = %r\n' % (
            action, self.inputs, self.actors, config or {}) + code_path.read_text(encoding='utf8')
        self.sequence += 1
        label = '%02d-%s-%s' % (self.sequence, 'client' if client else 'server', action)
        record = {'code_sha256': hashlib.sha256(code.encode('utf8')).hexdigest(), 'code': code}
        try:
            with Client(timeout=30) as connection:
                raw = connection.call('execute_code', {'code': code, 'is_client': client, 'direct_return': True})
                value = return_value(raw)
            if isinstance(value, str):
                value = json.loads(value)
            record['result'] = value
        except BaseException as exc:
            record['error'] = {'type': type(exc).__name__, 'message': str(exc)}
            raise
        finally:
            save(label + '.json', record)
        assert isinstance(value, dict), label
        return value

    def image(self, name):
        time.sleep(.8)
        session = bound()
        os.environ['MCDEV_ALLOW_USER_FOREGROUND'] = '1'
        receipt = capture(session['session_file'], OWNER, OUTPUT / (name + '.png'), WGC)
        assert receipt['ok'] and receipt['reliable']
        return {'image': name + '.png', 'sha256': receipt['sha256']}

    def restore(self, label):
        errors = []
        for client in (True, False):
            try:
                self.call('restore', client=client)
            except Exception as exc:
                errors.append({'client': client, 'type': type(exc).__name__, 'message': str(exc)})
        save(label + '-restoration.json', {'success': not errors, 'errors': errors})
        save(label + '-source-final.json', {'unchanged': snapshot_sources(PROJECT)
             == read(CONTROL / 'launch-inputs.json')['files']})
        assert not errors, errors


def first():
    validate()
    assert not (OUTPUT / 'first-started.json').exists()
    resource_guard('before-first')
    save('first-started.json', {'at': datetime.now(timezone.utc).isoformat()})
    probe = Probe()
    try:
        row = probe.call('journal', client=False)
        probe.actors = row['actors']
        save('actors.json', row['actors'])
        save('origin.json', row['origin'])
        time.sleep(.6)
        probe.call('journal')
        probe.call('mount_native')
        first_image = probe.image('01-native-ui-unbound')
        probe.call('bind')
        second_image = probe.image('02-native-ui-bound-front')
        save('first-complete.json', {'images': [first_image, second_image],
            'visual_review_pending': True, 'positive_accepted': False})
    except BaseException:
        probe.restore('first-failure')
        raise
    print(json.dumps({'first_two_complete': True, 'review_required': True,
        'scene_temporarily_retained': True, 'owner': OWNER}))


def remaining(accepted):
    validate()
    assert accepted, 'First two native positives must be visually reviewed'
    assert read(OUTPUT / 'first-complete.json')['visual_review_pending']
    assert not (OUTPUT / 'remaining-started.json').exists()
    resource_guard('before-remaining')
    save('remaining-started.json', {'at': datetime.now(timezone.utc).isoformat(),
        'first_two_visually_reviewed': True, 'native_positive_accepted': True})
    probe, images = Probe(), []
    try:
        for name, yaw, pitch in (('03-bound-oblique', 45., 15.),
                                  ('04-bound-back', 180., 0.), ('05-bound-side', 90., 0.)):
            probe.call('pose', config={'yaw': yaw, 'pitch': pitch})
            images.append(probe.image(name))
        probe.call('frames', client=False)
        origin = read(OUTPUT / 'origin.json')
        for name, oblique in (('06-actual-frame-front', False), ('07-actual-frame-oblique', True)):
            probe.call('world', config={'origin': origin, 'oblique': oblique})
            images.append(probe.image(name))
        probe.call('editor_open')
        time.sleep(1.)
        probe.call('mount_editor', config={'yaw': 0., 'pitch': 0.})
        images.append(probe.image('08-workspace-candidate-front'))
        probe.call('pose', config={'yaw': 45., 'pitch': 15.})
        images.append(probe.image('09-workspace-candidate-oblique'))
        save('remaining-complete.json', {'images': images, 'production_qualified': False,
            'workspace_common_depth_tested': False})
    finally:
        probe.restore('remaining')
    print(json.dumps({'remaining_images': len(images), 'restored': True, 'production_qualified': False}))


def stop():
    session = bound(live=False)
    attempts = sorted(OUTPUT.glob('stop-[0-9][0-9].json'))
    if attempts:
        assert all(process_identity(session[kind + '_pid']) is None for kind in ('game', 'mcdk')), \
            'An earlier normal stop was sent; do not resend while live'
    index = len(attempts) + 1
    result = subprocess.run([sys.executable, '-B', '-X', 'utf8',
        str(ROOT / '.runtime/shield_stop_owned_r20.py'), '--session', session['session_file'],
        '--owner', OWNER, '--normal-only'], cwd=ROOT, capture_output=True, encoding='utf8', timeout=60)
    save('stop-%02d.json' % index, {'returncode': result.returncode, 'stdout': result.stdout,
        'stderr': result.stderr, 'forced': False})
    observed = subprocess.run([sys.executable, '-B', '-X', 'utf8',
        str(ROOT / '.runtime/shield_lifecycle_read_r20.py'), '--session', session['session_file'],
        '--owner', OWNER, '--output', str(OUTPUT / ('lifecycle-%02d.json' % index))],
        cwd=ROOT, capture_output=True, encoding='utf8', timeout=20)
    assert observed.returncode == 0, observed.stderr
    assert result.returncode == 0, 'Normal stop timeout; do not force or resend while live'
    print(json.dumps({'owner': OWNER, 'stopped': True, 'forced': False}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'verify', 'launch', 'first', 'remaining', 'restore', 'stop'))
    parser.add_argument('--native-positive-reviewed', action='store_true')
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare()
    elif args.action == 'verify':
        print(json.dumps({'verified': True, 'started': (CONTROL / 'start.stdout.json').exists(),
            'source_contract_sha256': validate()['source_contract_sha256']}))
    elif args.action == 'launch':
        launch()
    elif args.action == 'first':
        first()
    elif args.action == 'remaining':
        remaining(args.native_positive_reviewed)
    elif args.action == 'restore':
        Probe().restore('explicit-%02d' % (len(list(OUTPUT.glob('explicit-*-restoration.json'))) + 1))
    else:
        stop()


if __name__ == '__main__':
    main()
