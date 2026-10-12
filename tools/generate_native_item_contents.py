"""Generate public item controls from independently placed native enchantments."""
import argparse
import base64
import hashlib
import json
from pathlib import Path, PureWindowsPath
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry as registry
from projection.entity_overlays import frame_item
from projection.nbt_spatial import root_payload, scalar

CASES = (('frame_filled', 'minecraft:frame', 'ItemFrame'),
         ('glow_frame_filled', 'minecraft:glow_frame', 'GlowItemFrame'))
ENCHANTMENT = (9, 3)
SNAPSHOT = ROOT / 'tools/data/native_item_contents_nemc_3.9.0.401155.json'
RUNTIME = ROOT / 'behavior_pack/modern_projection/projection/item_contents_data.py'
RAW_REPORT = ROOT / 'tools/data/native_item_contents_r11_raw.json'
FROZEN_SESSION = ROOT / 'tools/data/native_item_contents_r11_session.json'


def canonical(data):
    return json.dumps(data, ensure_ascii=True, sort_keys=True, separators=(',', ':')).encode('ascii')


def fingerprint(value):
    return isinstance(value, str) and len(value) == 64 and all(char in '0123456789abcdef' for char in value)


def evidence_path(root, value):
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('Native item source evidence must remain inside the repository')
    return path


def runtime_identity(report, session_record, root=ROOT):
    if (session_record.get('schema') != 1 or session_record.get('source_kind') !=
            'selected_fields_from_stopped_owned_session_manifest' or
            not fingerprint(session_record.get('source_manifest_sha256'))):
        raise ValueError('Native item source needs an independently frozen owned session manifest')
    session = session_record['session']
    source_version = PureWindowsPath(session['game_executable']).parent.name
    if (source_version != registry.source_version().removeprefix('NEMC ') or
            PureWindowsPath(report['session_file']) != PureWindowsPath(session['session_file']) or
            report['owner'] != session['owner'] or session['world'] != 'PYR_' + session['id'] or
            not all(session.get(field) for field in
                    ('game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity',
                     'background_safe', 'window_noactivate'))):
        raise ValueError('Native item report differs from the independent launch identity')
    startup = session_record['startup_log']
    raw = evidence_path(root, startup['file']).read_bytes()
    if (startup.get('hash_format') != 'raw_file_bytes' or
            hashlib.sha256(raw).hexdigest() != startup.get('sha256') or
            ('PyreactSession_' + session['id']).encode('ascii') not in raw):
        raise ValueError('Native item source startup log differs from its frozen session')
    if 'runtime_version' in report or 'runtime_minecraft_version' in report:
        raise ValueError('Unbound native runtime identity is not a registry version')
    versions = report.get('native_runtime_versions')
    native_version = session_record.get('native_runtime_version')
    verified = session_record.get('native_runtime_verified')
    if versions is None:
        if (native_version is not None or verified is not False or
                session_record.get('executable_at_capture_verified') is not False or
                session_record.get('executable_at_capture_sha256') is not None):
            raise ValueError('The original report did not record a native runtime API version')
    elif (verified is not True or not isinstance(native_version, str) or
          versions != {'server': native_version, 'client': native_version}):
        raise ValueError('Native server/client runtime identity differs from its independent source')
    if versions is not None:
        evidence = report.get('native_runtime_evidence', {})
        fields = ('id', 'owner', 'session_file', 'game_executable', 'game_pid',
                  'game_identity', 'mcdk_pid', 'mcdk_identity')
        recorded = evidence.get('session', {})
        if (evidence.get('native_runtime_versions') != versions or
                evidence.get('manifest_hash_format') != 'raw_file_bytes' or
                not fingerprint(evidence.get('manifest_sha256')) or
                evidence['manifest_sha256'] != session_record.get('in_run_manifest_sha256') or
                any(PureWindowsPath(recorded.get(field, '')) != PureWindowsPath(session[field])
                    if field in ('session_file', 'game_executable') else recorded.get(field) != session[field]
                    for field in fields)):
            raise ValueError('Native runtime readback is not bound to its independently frozen run')
    return {'build_directory_version': source_version,
            'build_directory_source': 'independent_owned_launch_manifest',
            'native_runtime_version': native_version,
            'native_runtime_verified': verified,
            'executable_at_capture_verified': session_record['executable_at_capture_verified']}


def _validate_structure(data):
    if (data.get('schema') != 2 or data.get('game_version') != registry.source_version() or
            data.get('palette_sha256') != registry.fingerprint()):
        raise ValueError('Native item content source does not match this registry')
    if data.get('source_kind') != 'native_inventory_enchantment_and_block_interaction':
        raise ValueError('Native item controls require independent physical item use')
    if (not fingerprint(data.get('source_sha256')) or
            data.get('source_hash_format') != 'raw_file_bytes' or
            not fingerprint(data.get('source_session_manifest_sha256'))):
        raise ValueError('Native item source needs its original report fingerprint')
    rows = data.get('rows', ())
    if tuple(row.get('case') for row in rows) != tuple(case[0] for case in CASES):
        raise ValueError('Native item source case associations need updating')
    for row, (case, name, identity) in zip(rows, CASES):
        material = row['block']['name'], row['block']['aux']
        if material[0] != name or registry.states(material) is None:
            raise ValueError('Native item source contains an unverified block state: ' + case)
        cells = row.get('cell_nbt', ())
        if len(cells) != 1:
            raise ValueError('Native item source needs one complete tagged actor per case')
        actor = root_payload(cells[0]['nbt'])
        if scalar(actor, 'id') != identity:
            raise ValueError('Native item source entity association changed: ' + case)
        for axis, coordinate in zip(('x', 'y', 'z'), cells[0]['pos']):
            if actor[axis] != {'__type__': 3, '__value__': coordinate}:
                raise ValueError('Native item source root coordinates changed: ' + case)
        item = frame_item(material, cells[0]['nbt'])
        if not item or item['newItemName'] != 'minecraft:diamond_sword' or not item['isEnchanted']:
            raise ValueError('Native item source lacks its enchanted sword: ' + case)
        ench = item['userData'].get('ench')
        if not isinstance(ench, list) or len(ench) != 1:
            raise ValueError('Native enchantment list schema changed: ' + case)
        entry = ench[0]
        if (entry.get('id') != {'__type__': 2, '__value__': ENCHANTMENT[0]} or
                entry.get('lvl') != {'__type__': 2, '__value__': ENCHANTMENT[1]}):
            raise ValueError('Native item source enchantment types or values changed: ' + case)
        if row.get('inventory_enchantments') != [list(ENCHANTMENT)]:
            raise ValueError('Native item enchantment lacks independent inventory readback: ' + case)
        if not all(row.get(field) is True for field in
                   ('native_spawn_return', 'native_add_enchant_return', 'native_interaction_return')):
            raise ValueError('Native item source has a failed physical operation: ' + case)
    return data


def validate(data, root=ROOT):
    _validate_structure(data)
    payload = evidence_path(root, data['source_report_file']).read_bytes()
    session_payload = evidence_path(root, data['source_session_manifest_file']).read_bytes()
    if hashlib.sha256(payload).hexdigest() != data['source_sha256']:
        raise ValueError('Native item source original report bytes changed')
    if hashlib.sha256(canonical(json.loads(session_payload))).hexdigest() != data['source_session_manifest_sha256']:
        raise ValueError('Native item source independently frozen session manifest changed')
    rebuilt = snapshot(json.loads(payload), payload, json.loads(session_payload), root=root)
    if rebuilt != data:
        raise ValueError('Native item source snapshot differs from its independent original evidence')
    return data


def snapshot(report, payload, session_record=None, root=ROOT):
    if json.loads(payload) != report:
        raise ValueError('Native item report object differs from its original raw bytes')
    if session_record is None:
        session_record = json.loads((root / FROZEN_SESSION.relative_to(ROOT)).read_bytes())
    identity = runtime_identity(report, session_record, root=root)
    if (report.get('schema') != 2 or report.get('mode') != 'physical_item_use' or
            not all(report.get(field) is True for field in
                    ('completed', 'passed', 'restored', 'native_cleaned', 'client_cleaned')) or
            report.get('cleanup_errors')):
        raise ValueError('Use a completed and restored physical item readback report')
    if not report.get('client_before_interaction', {}).get('ready'):
        raise ValueError('Native frame interaction requires prior client block replication')
    observed = report['native_readback']
    if report['client_registry'] != {'source_version': observed['source_version'],
                                      'palette_sha256': observed['palette_sha256']}:
        raise ValueError('Native item source client and server registries differ')
    client = report['client_palette']
    if not client.get('ready'):
        raise ValueError('Native item source lacks final client palette replication')
    result_rows = {row['case']: row for row in observed['results']}
    client_rows = {row['case']: row for row in client['rows']}
    if len(result_rows) != len(CASES) or len(client_rows) != len(CASES):
        raise ValueError('Native item source contains incomplete or extra controls')
    rows = []
    for case, unused_name, unused_identity in CASES:
        source, result = client_rows[case], result_rows[case]
        if not result.get('passed'):
            raise ValueError('Native item source control did not pass: ' + case)
        if (source['cell_nbt'][0]['nbt']['Item'] != result['actual_item'] or
                result['expected_enchantment'] != list(ENCHANTMENT)):
            raise ValueError('Native item source differs from independent readback: ' + case)
        row = {key: source[key] for key in ('case', 'block', 'face', 'cell_nbt', 'palette')}
        for field in ('native_spawn_return', 'native_add_enchant_return', 'native_interaction_return'):
            row[field] = result[field]
        row['inventory_enchantments'] = result['inventory_after_enchants']
        rows.append(row)
    return _validate_structure({'schema': 2, 'game_version': observed['source_version'],
                     'palette_sha256': observed['palette_sha256'],
                     'source_sha256': hashlib.sha256(payload).hexdigest(),
                     'source_hash_format': 'raw_file_bytes',
                     'source_report_file': str(RAW_REPORT.relative_to(ROOT)).replace('\\', '/'),
                     'source_session_manifest_file': str(FROZEN_SESSION.relative_to(ROOT)).replace('\\', '/'),
                     'source_session_manifest_sha256': hashlib.sha256(canonical(session_record)).hexdigest(),
                     'source_original_session_manifest_sha256': session_record['source_manifest_sha256'],
                     'runtime_identity': identity,
                     'source_session': report['session_file'], 'source_owner': report['owner'],
                     'source_kind': 'native_inventory_enchantment_and_block_interaction',
                     'scope': 'Native enchanted item data; pixels, glint and world writer remain separate',
                     'rows': rows})


def runtime(data, root=ROOT):
    validate(data, root=root)
    packed = base64.b64encode(zlib.compress(canonical(data['rows']), 9)).decode('ascii')
    return ('"""Generated native item content fixtures; do not edit."""\n'
            'SCHEMA_VERSION = 2\nSOURCE_VERSION = %r\nPALETTE_SHA256 = %r\n'
            'SOURCE_SHA256 = %r\nPROBE_SHA256 = %r\nSESSION_MANIFEST_SHA256 = %r\n'
            'NATIVE_BUILD_DIRECTORY_VERSION = %r\nNATIVE_RUNTIME_VERSION = %r\n'
            'NATIVE_RUNTIME_VERIFIED = %r\nROWS = %r\n' %
            (data['game_version'], data['palette_sha256'], hashlib.sha256(canonical(data)).hexdigest(),
             data['source_sha256'], data['source_session_manifest_sha256'],
             data['runtime_identity']['build_directory_version'],
             data['runtime_identity']['native_runtime_version'],
             data['runtime_identity']['native_runtime_verified'], packed))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-report', type=Path)
    parser.add_argument('--source-session-manifest', type=Path, default=FROZEN_SESSION)
    parser.add_argument('--snapshot', type=Path, default=SNAPSHOT)
    parser.add_argument('--runtime-output', type=Path, default=RUNTIME)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.source_report:
        payload = args.source_report.read_bytes()
        data = snapshot(json.loads(payload), payload, json.loads(args.source_session_manifest.read_bytes()))
    else:
        data = validate(json.loads(args.snapshot.read_bytes()))
    text = json.dumps(data, ensure_ascii=True, sort_keys=True, indent=2) + '\n'
    generated = runtime(data)
    if args.check:
        if args.snapshot.read_text(encoding='ascii') != text:
            raise SystemExit('Native item content snapshot is stale')
        if args.runtime_output.read_text(encoding='ascii') != generated:
            raise SystemExit('Native item content runtime fixtures are stale')
    else:
        args.snapshot.parent.mkdir(parents=True, exist_ok=True)
        args.snapshot.write_text(text, encoding='ascii')
        args.runtime_output.write_text(generated, encoding='ascii')
    print('Native item contents: %d independently enchanted controls' % len(data['rows']))


if __name__ == '__main__':
    main()
