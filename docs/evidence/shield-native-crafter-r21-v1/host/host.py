"""Prepare-only by default; launch and run require separate explicit actions."""
import argparse
from collections import Counter
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
ROUND = 'v6-crafter'
OWNER = 'shield-r20-' + ROUND
PROJECT = ROOT / ('.runtime/projects/shield-r20-' + ROUND)
CONTROL = ROOT / ('.runtime/shield-r20-control-' + ROUND)
OUTPUT = ROOT / '.runtime/shield-crafter-r20-v6'
SCRIPTS = ROOT / '.agents/skills/pyreact-debugging/scripts'
ENGINE = Path('D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.420447/data')
sys.path[:0] = [str(SCRIPTS), str(ROOT / 'tools'),
               str(ROOT / 'behavior_pack/modern_projection')]
from _session import load_session, process_identity
from mcdk import Client, return_value
from probe_product_water import snapshot_sources, snapshot_digest
from census_intrinsic_glint_ui_r21 import commit_at_boundary
from projection import block_registry, entity_defaults
from projection.nbt_spatial import root_payload, scalar

RELOADS = ('auto_hot_reload_mods', 'auto_hot_reload_ui',
           'auto_hot_reload_shaders', 'auto_hot_reload_materials')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def save(name, value):
    path = OUTPUT / name
    with path.open('x', encoding='ascii') as handle:
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
    games = census()
    commit = commit_at_boundary()
    receipt = {'label': label, 'games': games, 'commit': commit,
               'launch': launch, 'observed_at': datetime.now(timezone.utc).isoformat()}
    save(label + '-resources.json', receipt)
    assert len(games) <= (1 if launch else 2), 'Global MC cap would be exceeded'
    assert commit['commit_available_bytes'] >= 6 * 1024 ** 3, 'Free commit below 6 GiB'
    if not launch:
        session = bound()
        own = [row for row in games if row['ProcessId'] == session['game_pid']
               and row['identity'] == session['game_identity']]
        assert len(own) == 1 and own[0]['HandleCount'] < 210000, 'Recycle owned handle budget'
    return receipt


def prepare():
    assert not OUTPUT.exists() and not PROJECT.exists() and not CONTROL.exists()
    OUTPUT.mkdir()
    blocks = {}
    for label, name, properties in (
            ('crafter', 'minecraft:crafter', {'crafting': False, 'orientation': 'north_up', 'triggered_bit': False}),
            ('hopper', 'minecraft:hopper', {'facing_direction': 0, 'toggle_bit': False}),
            ('chest', 'minecraft:chest', {'minecraft:cardinal_direction': 'north'})):
        value = block_registry.from_states(name, properties)
        assert value is not None
        blocks[label] = {'name': name, 'aux': value[1], 'states': properties,
                         'observed_default_nbt': entity_defaults.nbt(name, (0, 0, 0))}
    inputs = read(ROOT / 'docs/evidence/banner-item-shield-r20/v4/craft-fill.json') if (ROOT / 'docs/evidence/banner-item-shield-r20/v4/craft-fill.json').exists() else read(ROOT / '.runtime/shield-craft-event-r20-v4/craft-fill.json')
    target = inputs['result']['inputs']
    save('inputs.json', {'blocks': blocks,
        'positive': [{'itemName': 'minecraft:oak_log', 'count': 1, 'auxValue': 0}],
        'target': [target['shield'], target['banner']],
        'target_provenance': {'path': '.runtime/shield-craft-event-r20-v4/craft-fill.json',
                              'sha256': sha(ROOT / '.runtime/shield-craft-event-r20-v4/craft-fill.json')},
        'native_banner_readback': read(ROOT / 'docs/evidence/banner-item-shield-r20/v4/restore-input.json')['result']['banner'],
        'defaults_evidence': entity_defaults.evidence()})
    result = subprocess.run([sys.executable, '-X', 'utf8',
        str(ROOT / '.runtime/prepare_shield_r20.py'), '--round', ROUND,
        '--native-discovery', '--prepare-only'], cwd=ROOT, capture_output=True,
        encoding='utf8', check=True, timeout=120)
    save('clone-prepare.json', json.loads(result.stdout))
    config = read(PROJECT / '.mcdev.json')
    assert all(config[key] is False for key in RELOADS)
    native = ENGINE / 'behavior_packs/mq_gametest/scripts/mq_gametest.js'
    text = native.read_text(encoding='utf8')
    begin = text.index('const CRAFTER = \'generic:crafter\';')
    end = text.index('//#region Crafting recepies for BVT', begin)
    source = text[begin:end]
    assert 'test.pulseRedstone(crafterPowerLoc, 2)' in source
    assert 'await test.idle(8)' in source
    recipes = []
    for path in sorted((ENGINE / 'behavior_packs/vanilla/recipes').glob('*.json')):
        raw = path.read_bytes()
        if 'shield' in path.name or 'shield' in raw.decode('utf8', 'replace').lower():
            recipes.append({'path': str(path.relative_to(ENGINE)).replace('\\', '/'),
                            'sha256': hashlib.sha256(raw).hexdigest()})
    save('native-contract.json', {'runtime': '3.10.0.420447',
        'source': str(native), 'sha256': sha(native), 'exact_crafter_test': source,
        'matching_shield_recipes': recipes,
        'oak_planks_recipe': read(ENGINE / 'behavior_packs/vanilla/recipes/oak_planks.json'),
        'shield_decoration_support': 'not established by inspected native recipe resources or crafter tests',
        'api_support': {'SpawnItemToContainer': 'hopper/chest documented, crafter not listed',
                        'GetContainerItem': 'chest documented; getUserData=True',
                        'GetBlockEntityData': 'native crafter readback only; no NBT injection'},
        'readback_before_pulse': ['native orientation/states', 'hopper drain',
                                  'crafter exact Name/Count/Damage/tag.Patterns', 'empty output chest']})
    files = [Path(__file__), HERE / 'server_fixture.py', HERE / 'client_state.py',
             ROOT / '.runtime/prepare_shield_r20.py', ROOT / '.runtime/shield_instances_native_discovery_r20.py',
             ROOT / '.runtime/shield_stop_owned_r20.py', ROOT / '.runtime/shield_lifecycle_read_r20.py',
             SCRIPTS / 'instances.py', SCRIPTS / '_session.py', SCRIPTS / '_window.py', SCRIPTS / 'mcdk.py',
             OUTPUT / 'inputs.json', OUTPUT / 'native-contract.json']
    launch = read(CONTROL / 'launch-inputs.json')
    plan = {'schema': 1, 'prepared_only': True, 'owner': OWNER, 'project': str(PROJECT),
            'source_contract_sha256': launch['source_contract_sha256'],
            'config_sha256': sha(PROJECT / '.mcdev.json'),
            'host_files_sha256': {str(path.relative_to(ROOT)).replace('\\', '/'): sha(path) for path in files},
            'all_four_reload_flags_false': True, 'maximum_active_mc': 2,
            'minimum_free_commit_gib': 6, 'handle_boundary': 210000,
            'max_fixture_seconds': 120, 'owned_world_cells': 4, 'air_guard_cells': 64,
            'native_crafter_nbt_writes': False, 'inventory_writes_planned': False,
            'camera_writes_planned': False, 'desktop_input': False,
            'cases': ['oak_log_to_four_oak_planks_positive', 'plain_shield_plus_patterned_blue_banner'],
            'target': 'authentic native output raw item and output-container NBT',
            'production_qualified': False, 'started': False,
            'next_action': 'Wait for parent slot, then explicit launch and run actions'}
    save('plan.json', plan)
    print(json.dumps({'prepared_only': True, 'started': False, 'owner': OWNER,
                      'plan': str(OUTPUT / 'plan.json'), 'source_contract_sha256': launch['source_contract_sha256']}))


def validate():
    plan = read(OUTPUT / 'plan.json')
    assert plan['owner'] == OWNER and not plan['production_qualified']
    for relative, expected in plan['host_files_sha256'].items():
        assert sha(ROOT / relative) == expected, 'Prepared host changed: ' + relative
    sources = snapshot_sources(PROJECT)
    frozen = read(CONTROL / 'launch-inputs.json')
    assert sources == frozen['files'] and snapshot_digest(sources) == plan['source_contract_sha256']
    assert sha(PROJECT / '.mcdev.json') == plan['config_sha256']
    assert all(read(PROJECT / '.mcdev.json')[key] is False for key in RELOADS)
    return plan


def bound():
    ready = read(CONTROL / 'ready-summary.json')
    session = load_session(ready['session_file'], OWNER)
    assert Path(session['project']).resolve() == PROJECT.resolve()
    for key in ('owner', 'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity'):
        assert ready[key] == session[key], 'Owned identity changed: ' + key
    for kind in ('game', 'mcdk'):
        assert process_identity(session[kind + '_pid']) == session[kind + '_identity']
    return session


def launch():
    validate()
    assert not (CONTROL / 'start.stdout.json').exists()
    resource_guard('prelaunch', launch=True)
    result = subprocess.run([sys.executable, '-X', 'utf8',
        str(ROOT / '.runtime/prepare_shield_r20.py'), '--round', ROUND,
        '--native-discovery', '--launch-prepared'], cwd=ROOT, capture_output=True,
        encoding='utf8', timeout=320)
    save('launch-host-result.json', {'returncode': result.returncode,
                                   'stdout': result.stdout, 'stderr': result.stderr})
    assert result.returncode == 0, 'Inspect owned launch before any retry'
    session = bound()
    print(json.dumps({key: session[key] for key in ('owner', 'session_file', 'game_pid',
                                                   'game_identity', 'mcdk_pid', 'mcdk_identity')}))


class Probe:
    def __init__(self):
        self.inputs = read(OUTPUT / 'inputs.json')
        self.started = time.monotonic()
        self.sequence = max([int(path.name.split('-', 1)[0]) for path in OUTPUT.glob('[0-9][0-9]-*.json')] + [0])

    def call(self, action, client=False):
        session = bound()
        os.environ.update(MCDEV_SESSION_FILE=session['session_file'], MCDEV_OWNER=OWNER,
                          MCDEV_ALLOW_USER_FOREGROUND='1')
        code_path = HERE / ('client_state.py' if client else 'server_fixture.py')
        code = 'ACTION = %r\nINPUTS = %r\n' % (action, self.inputs) + code_path.read_text(encoding='utf8')
        self.sequence += 1
        label = '%02d-%s-%s' % (self.sequence, 'client' if client else 'server', action)
        with Client(timeout=30) as connection:
            raw = connection.call('execute_code', {'code': code, 'is_client': client, 'direct_return': True})
            value = return_value(raw)
        if isinstance(value, str):
            value = json.loads(value)
        save(label + '.json', {'code_sha256': hashlib.sha256(code.encode('utf8')).hexdigest(),
                              'code': code, 'result': value})
        assert isinstance(value, dict), label
        return value

    def poll(self, predicate, timeout=12):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            assert time.monotonic() - self.started < 120, 'Bounded fixture deadline'
            row = self.call('inspect')
            if predicate(row):
                return row
            time.sleep(.25)
        raise RuntimeError('Bounded native readback predicate did not pass')


def crafter_entries(row):
    root = root_payload(row['blocks']['crafter']['nbt'])
    assert root is not None and 'Items' in root
    values = root['Items']
    if isinstance(values, dict):
        assert values.get('__type__') == 9
        values = values['__value__']
    return values


def item_name(row):
    return None if not row else row.get('newItemName', row.get('itemName'))


def run():
    validate()
    assert not (OUTPUT / 'run-started.json').exists()
    resource_guard('pre-fixture')
    save('run-started.json', {'owner': OWNER, 'at': datetime.now(timezone.utc).isoformat()})
    probe = Probe()
    error = None
    try:
        probe.call('journal', client=True)
        probe.call('journal')
        probe.call('place')
        for case, expected in (('positive', ['minecraft:oak_log']),
                               ('target', ['minecraft:shield', 'minecraft:banner'])):
            resource_guard('before-' + case)
            probe.call('feed_' + case)
            fed = probe.poll(lambda row: not any(row['hopper']) and
                Counter(scalar(root_payload(entry), 'Name') for entry in crafter_entries(row)) == Counter(expected))
            save(case + '-loaded.json', fed)
            probe.call('pulse_on')
            time.sleep(.15)
            probe.call('pulse_off')
            time.sleep(.6)
            result = probe.poll(lambda row: bool(row['chest'][0]))
            save(case + '-output.json', result)
            assert not any(result['hopper']) and not crafter_entries(result)
            output = [item for item in result['chest'] if item]
            assert len(output) == 1
            if case == 'positive':
                assert item_name(output[0]) == 'minecraft:oak_planks' and output[0]['count'] == 4
                probe.call('clear_output')
            else:
                assert item_name(output[0]) == 'minecraft:shield' and output[0]['count'] == 1
                save('authentic-shield.json', {'native_crafting_output_acquired': True,
                    'user_data_requested': True, 'item': output[0],
                    'container_nbt': result['blocks']['chest']['nbt'],
                    'input_crafter_empty': True, 'native_nbt_injection': False,
                    'production_qualified': False})
    except BaseException as exc:
        error = {'type': type(exc).__name__, 'message': str(exc)}
        save('run-error.json', error)
    finally:
        cleanup_errors = []
        for client in (False, True):
            try:
                probe.call('restore', client=client)
            except Exception as exc:
                cleanup_errors.append({'client': client, 'type': type(exc).__name__, 'message': str(exc)})
        save('run-restoration.json', {'success': not cleanup_errors, 'errors': cleanup_errors})
        save('source-final.json', {'unchanged': snapshot_sources(PROJECT) == read(CONTROL / 'launch-inputs.json')['files']})
    assert not cleanup_errors, cleanup_errors
    assert error is None, error
    print(json.dumps({'owner': OWNER, 'authentic_shield': str(OUTPUT / 'authentic-shield.json'),
                      'restoration': str(OUTPUT / 'run-restoration.json'), 'production_qualified': False}))


def restore():
    probe = Probe()
    result = []
    for client in (False, True):
        result.append(probe.call('restore', client=client))
    print(json.dumps({'owner': OWNER, 'restoration': result}))


def stop():
    ready = read(CONTROL / 'ready-summary.json')
    session = load_session(ready['session_file'], OWNER)
    assert Path(session['project']).resolve() == PROJECT.resolve()
    for key in ('owner', 'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity'):
        assert ready[key] == session[key]
    index = len(list(OUTPUT.glob('stop-*.json'))) + 1
    command = [sys.executable, '-X', 'utf8', str(ROOT / '.runtime/shield_stop_owned_r20.py'),
               '--session', session['session_file'], '--owner', OWNER, '--normal-only']
    result = subprocess.run(command, cwd=ROOT, capture_output=True, encoding='utf8', timeout=60)
    save('stop-%02d.json' % index, {'returncode': result.returncode,
                                   'stdout': result.stdout, 'stderr': result.stderr, 'forced': False})
    lifecycle = OUTPUT / ('lifecycle-%02d.json' % index)
    observed = subprocess.run([sys.executable, '-X', 'utf8',
        str(ROOT / '.runtime/shield_lifecycle_read_r20.py'), '--session', session['session_file'],
        '--owner', OWNER, '--output', str(lifecycle)], cwd=ROOT, capture_output=True,
        encoding='utf8', timeout=20)
    assert observed.returncode == 0, observed.stderr
    row = read(lifecycle)
    if result.returncode and all(item['live_identity'] is None for item in row['processes']):
        finalized = subprocess.run(command, cwd=ROOT, capture_output=True, encoding='utf8', timeout=30)
        save('stop-final-%02d.json' % index, {'returncode': finalized.returncode,
            'stdout': finalized.stdout, 'stderr': finalized.stderr, 'forced': False})
        assert finalized.returncode == 0
    elif result.returncode:
        raise RuntimeError('Owned normal stop timed out; exact process remains live; no force performed')
    print(json.dumps({'owner': OWNER, 'forced': False, 'lifecycle': row}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'verify', 'launch', 'run', 'restore', 'stop'), default='prepare', nargs='?')
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare()
    elif args.action == 'verify':
        plan = validate()
        print(json.dumps({'prepared_only': True, 'started': (CONTROL / 'start.stdout.json').exists(),
                          'owner': OWNER, 'verified_source_contract': plan['source_contract_sha256']}))
    elif args.action == 'launch':
        launch()
    elif args.action == 'run':
        run()
    elif args.action == 'restore':
        restore()
    else:
        stop()


if __name__ == '__main__':
    main()
