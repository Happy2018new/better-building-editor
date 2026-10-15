"""Archive and independently replay restored frame-block holdouts without a game."""
import argparse
import ast
import copy
from datetime import datetime, timedelta
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = ('tools', 'behavior_pack/modern_projection',
                '.agents/skills/pyreact-debugging/scripts')
REPORT_FIELDS = ('schema', 'completed', 'production_qualified', 'engine', 'cases',
    'captures', 'cleanup_errors', 'launch_sources', 'launch_sources_sha256',
    'host_tool_sha256', 'host_dependency_sha256', 'candidate_geometry',
    'profile_mode', 'view_configuration', 'resource_contract', 'camera_calibration',
    'native_item_shader_errors', 'frame_block_batch', 'requested_cases',
    'remaining_cases', 'matrix_completed', 'environment_restored', 'sources_after',
    'source_unchanged', 'process_samples')
SESSION_FIELDS = ('id', 'owner', 'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity')
NS = {'e': 'http://schemas.microsoft.com/win/2004/08/events/event'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='ascii')


def contained(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('Evidence path escapes its bundle: ' + str(relative))
    return path


def sanitize(value, session, paths):
    if isinstance(value, list):
        return [sanitize(row, session, paths) for row in value]
    if isinstance(value, dict):
        result = {}
        for key, row in value.items():
            if key in ('token', 'mcp_url', 'port', 'appdata', 'world_link', 'world_path'):
                continue
            if key == 'session':
                result[key] = session
            elif key == 'session_file':
                result[key] = session['session_file']
            elif key in ('foreground', 'foreground_before', 'foreground_after'):
                result[key] = {name: row[name] for name in ('hwnd', 'pid') if name in row}
            else:
                result[key] = sanitize(row, session, paths)
        return result
    if isinstance(value, str):
        return paths.get(value, value)
    return value


def import_closure(root, entries):
    """Resolve local imports statically, including possible imported submodules."""
    pending, selected = list(entries), set()
    while pending:
        relative = pending.pop()
        if relative in selected:
            continue
        selected.add(relative)
        path = contained(root, relative)
        tree = ast.parse(path.read_text(encoding='utf-8-sig'), filename=relative)
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    base = path.parent
                    for _ in range(node.level - 1):
                        base = base.parent
                    prefixes = [base]
                else:
                    prefixes = [root / folder for folder in SOURCE_ROOTS]
                module = (node.module or '').replace('.', '/')
                for prefix in prefixes:
                    targets = [prefix / module]
                    targets += [prefix / module / alias.name for alias in node.names]
                    for target in targets:
                        for candidate in (target.with_suffix('.py'), target / '__init__.py'):
                            if candidate.is_file() and candidate.is_relative_to(root):
                                pending.append(candidate.relative_to(root).as_posix())
            for name in names:
                for folder in SOURCE_ROOTS:
                    target = root / folder / name.replace('.', '/')
                    for candidate in (target.with_suffix('.py'), target / '__init__.py'):
                        if candidate.is_file():
                            pending.append(candidate.relative_to(root).as_posix())
    return selected


def event_data(xml):
    tree = ET.fromstring(xml)
    data = {row.attrib['Name']: row.text for row in tree.findall('e:EventData/e:Data', NS)}
    return tree, data


def matching_wer(events, process):
    matched = []
    report_ids = set()
    for xml in events:
        tree, data = event_data(xml)
        if tree.findtext('e:System/e:EventID', namespaces=NS) != '1000':
            continue
        if (int(data.get('ProcessId', '0'), 16) == process['pid'] and
                int(data.get('ProcessCreationTime', '0'), 16) == int(process['identity'])):
            matched.append(xml)
            report_ids.add(data['IntegratorReportId'])
    matched += [xml for xml in events if event_data(xml)[0].findtext(
        'e:System/e:EventID', namespaces=NS) == '1001' and any(value in xml for value in report_ids)]
    return matched


def collect_wer(exits, output):
    start = datetime.fromisoformat(exits['opened_at'])
    end = datetime.fromisoformat(exits['processes']['game']['observed_at']) + timedelta(minutes=2)
    command = ("[Console]::OutputEncoding=[Text.UTF8Encoding]::new(); "
        "$a=[DateTimeOffset]::Parse('" + start.isoformat() + "').LocalDateTime; "
        "$b=[DateTimeOffset]::Parse('" + end.isoformat() + "').LocalDateTime; "
        "@((Get-WinEvent -FilterHashtable @{LogName='Application';Id=1000,1001;"
        "StartTime=$a;EndTime=$b} -ErrorAction SilentlyContinue) | "
        "ForEach-Object {$_.ToXml()}) | ConvertTo-Json -Compress")
    run = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', command],
                         check=True, capture_output=True, encoding='utf-8')
    events = json.loads(run.stdout.lstrip('\ufeff'))
    events = [events] if isinstance(events, str) else events or []
    matched = matching_wer(events, exits['processes']['game'])
    rows = []
    for xml in matched:
        tree, data = event_data(xml)
        record = tree.findtext('e:System/e:EventRecordID', namespaces=NS)
        relative = 'wer/event-' + record + '.xml'
        path = output / relative
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(xml.encode('utf-8'))
        rows.append({'path': relative, 'event_id': int(tree.findtext('e:System/e:EventID', namespaces=NS)),
            'record_id': int(record), 'time': tree.find('e:System/e:TimeCreated', NS).attrib['SystemTime'],
            'data': data})
    write_json(output / 'wer.json', {'schema': 1, 'process': exits['processes']['game'],
        'matched_by': ['ProcessId', 'ProcessCreationTime'], 'events': rows,
        'xml_encoding': 'UTF-8 export of EventLogRecord.ToXml(); not an EVTX byte copy',
        'cause_established': False})


def build(source, control, analysis, frozen, output):
    output.mkdir(parents=True, exist_ok=False)
    raw = json.loads(source.read_bytes())
    session = {key: raw['session'][key] for key in SESSION_FIELDS}
    session['session_file'] = 'session:' + session['id']
    paths = {}
    receipts = [row['capture'] for row in raw['captures']]
    receipts += [row[mode] for row in raw['camera_calibration']['views'] for mode in ('shown', 'hidden')]
    for receipt in receipts:
        original = Path(receipt['path'])
        assert digest(original) == receipt['sha256'], original
        relative = 'captures/' + original.name
        assert relative not in paths.values(), relative
        destination = contained(output, relative)
        destination.parent.mkdir(exist_ok=True)
        shutil.copyfile(original, destination)
        paths[str(original)] = relative
    report = {key: raw[key] for key in REPORT_FIELDS if key in raw}
    report['session'] = session
    report = sanitize(report, session, paths)
    write_json(output / 'report.json', report)
    for name in ('artificial-enchantment-probe.json', 'exact-exit.json', 'normal-stop.json'):
        shutil.copyfile(control / name, output / name)
    shutil.copytree(analysis, output / 'analysis-v1')
    candidate = Path(raw['candidate_geometry']['path'])
    assert digest(candidate) == raw['candidate_geometry']['sha256']
    shutil.copyfile(candidate, output / 'candidate.json')
    entries = ['tools/analyze_frame_block_multiview_r21.py', 'tools/verify_camera_projection.py']
    closure = import_closure(ROOT, entries)
    candidate_files = raw['candidate_geometry']['data']['files']
    closure.update(candidate_files)
    closure.update(('tools/probe_frame_block_enchantment_r21.py', 'tools/item_sprite_native_reference.py',
                    'tools/frame_block_capture_matrix_r21.py', 'tools/run_visible_items_r16.py',
                    'tools/item_sprite_calibration.py', 'tools/watch_intrinsic_glint_exit_r21.py'))
    bindings = {}
    original_analysis = json.loads((analysis / 'multiview.json').read_bytes())
    for relative in sorted(closure):
        original = contained(frozen if relative in candidate_files else ROOT, relative)
        actual = digest(original)
        binding = 'analysis_dependency_snapshot'
        expected = raw['launch_sources'].get(relative)
        if actual == expected:
            binding = 'launch_sources'
        if relative == 'tools/analyze_frame_block_multiview_r21.py':
            expected = original_analysis['analyzer_sha256']
            binding = 'original_analyzer_self_hash'
        elif relative == 'tools/run_visible_items_r16.py':
            expected = raw['host_tool_sha256']
            binding = 'capture_host_tool'
        elif Path(relative).name in raw['host_dependency_sha256']:
            expected = raw['host_dependency_sha256'][Path(relative).name]
            binding = 'capture_host_dependency'
        elif relative in candidate_files:
            expected = candidate_files[relative]
            binding = 'candidate_resource'
        if binding != 'analysis_dependency_snapshot':
            assert actual == expected, relative
        bindings[relative] = {'sha256': actual, 'binding': binding}
        destination = contained(output / 'sources', relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, destination)
    shutil.copyfile(Path(__file__), output / 'replay.py')
    collect_wer(json.loads((control / 'exact-exit.json').read_bytes()), output)
    files = {path.relative_to(output).as_posix(): digest(path)
             for path in sorted(output.rglob('*')) if path.is_file()}
    write_json(output / 'manifest.json', {'schema': 1, 'production_qualified': False,
        'engine': raw['engine'], 'files': files, 'source_subset': bindings,
        'launch_sources_sha256': raw['launch_sources_sha256'],
        'private_inputs_sha256': {'capture_report': digest(source)},
        'png_count': len(receipts), 'source_scope': 'Analysis import closure plus exact candidate resources and capture host tools; per-file bindings distinguish launch sources from retrospectively recorded analysis dependencies; complete launch hash map retained',
        'redactions': ['Session routing token, endpoint and unrelated session records omitted',
            'Session file replaced consistently by opaque session identity',
            'Unrelated foreground titles, process names and identities omitted; PID/HWND guard data retained'],
        'limitations': ['Original ideal support-only geometry aggregate remains false',
            'Frame-board occlusion confounds absolute pose identification from this model',
            'Only stone and artificially enchanted quartz_block, north-facing rotation zero, front and +/-75 degrees',
            'Lighting, texture fidelity, UI, glint motion/phase/brightness and production acceptance remain open',
            'Game exited 0xC0000409 after normal-only stop request; no clean exit claim',
            'Original analyzer recorded its own hash but not every dependency; additional analysis dependency bytes are frozen retrospectively and labeled separately']})
    return {'bundle': str(output), 'files': len(files), 'png_count': len(receipts), 'source_files': len(closure)}


def verify_files(bundle):
    manifest = json.loads((bundle / 'manifest.json').read_bytes())
    actual = {path.relative_to(bundle).as_posix() for path in bundle.rglob('*')
              if path.is_file() and path.name != 'manifest.json' and '__pycache__' not in path.parts}
    assert actual == set(manifest['files']), 'Unindexed or missing evidence files'
    for relative, expected in manifest['files'].items():
        assert digest(contained(bundle, relative)) == expected, relative
    report = json.loads((bundle / 'report.json').read_bytes())
    for relative, row in manifest['source_subset'].items():
        assert digest(contained(bundle / 'sources', relative)) == row['sha256'], relative
        if row['binding'] == 'launch_sources':
            assert row['sha256'] == report['launch_sources'][relative], relative
    return manifest, report


def compare(expected, actual, where='result'):
    if isinstance(expected, dict):
        assert isinstance(actual, dict) and expected.keys() == actual.keys(), where
        for key in expected:
            compare(expected[key], actual[key], where + '/' + key)
    elif isinstance(expected, list):
        assert isinstance(actual, (list, tuple)) and len(expected) == len(actual), where
        for index, (left, right) in enumerate(zip(expected, actual)):
            compare(left, right, where + '/' + str(index))
    elif type(expected) in (float, int) and type(actual) in (float, int):
        assert math.isclose(expected, actual, rel_tol=1e-8, abs_tol=1e-7), (where, expected, actual)
    else:
        assert expected == actual, (where, expected, actual)


def validate_nbt(probe, cases):
    assert probe['completed'] and probe['passed'] and probe['restored'] and not probe['cleanup_errors']
    rows = [(probe['fill']['observed'][0], probe['client'])]
    rows += [(case['native_reference']['fill']['observed'][0], case['native_reference']['client'])
             for case in cases if case['source']['item'] == ['minecraft:quartz_block', 0]]
    assert len(rows) == 4
    for server, client in rows:
        original = server['source']['plain_native_item']
        actual = server['typed_nbt']['Item']
        observed = client['root']['Item']
        assert original['Block'] == actual['Block'] == observed['Block']
        for item in (original, actual, observed):
            for key, expected in (('Name', 'minecraft:quartz_block'), ('Damage', 0), ('Count', 1)):
                assert item[key]['__value__'] == expected
        assert actual == observed
        assert 'tag' not in original
        enchants = [(row['id']['__value__'], row['lvl']['__value__']) for row in actual['tag']['ench']]
        assert enchants == [(9, 3)] and client['enchantments'] == [[9, 3]]
        assert server['item_api']['enchantData'] == [[9, 3]]
    return {'independent_probe_and_matrix_readbacks': len(rows), 'native_block_preserved': True,
            'server_client_item_equal': True, 'enchantments': [[9, 3]], 'pixel_glint_motion_accepted': False}


def replay(bundle, output):
    bundle = bundle.resolve()
    manifest, report = verify_files(bundle)
    output.mkdir(parents=True, exist_ok=False)
    source_root = bundle / 'sources'
    for folder in SOURCE_ROOTS:
        sys.path.insert(0, str(source_root / folder))
    from analyze_frame_block_multiview_r21 import analyze
    from analyze_liquid_workspace import capture_failures
    from item_sprite_capture_contract import camera_matches, snapshot_digest
    from verify_camera_projection import analyze_calibration

    assert report['launch_sources'] == report['sources_after']
    assert snapshot_digest(report['launch_sources']) == manifest['launch_sources_sha256']
    receipts = [row['capture'] for row in report['captures']]
    receipts += [row[mode] for row in report['camera_calibration']['views'] for mode in ('shown', 'hidden')]
    for receipt in receipts:
        receipt['path'] = str(contained(bundle, receipt['path']))
    assert not capture_failures({str(index): row for index, row in enumerate(receipts)}, report['session'])
    calibration = report['camera_calibration']
    expected_calibration = copy.deepcopy(calibration)
    assert {row['view'] for row in calibration['views']} == {'front', 'right', 'tilted'}
    for row in calibration['views']:
        assert camera_matches(row['camera'], row['camera_after'])
        assert camera_matches(row['camera'], dict(row['pose'], screen=row['camera']['screen'], fov=row['camera']['fov']))
        row['signal'] = str(output / ('camera-' + row['view'] + '-signal.png'))
        row['outline_comparison'] = str(output / ('camera-' + row['view'] + '-outline.png'))
    analyze_calibration(calibration)
    for key in ('passed', 'vertical_fov', 'individual_fitted_vertical_fov'):
        compare(expected_calibration[key], calibration[key], 'calibration/' + key)
    for expected, actual in zip(expected_calibration['views'], calibration['views']):
        compare(expected['fit'], actual['fit'], 'calibration/' + actual['view'])
    write_json(output / 'input.json', report)
    actual = analyze(output / 'input.json', output / 'multiview')
    expected = json.loads((bundle / 'analysis-v1/multiview.json').read_bytes())
    for key in ('source', 'source_sha256'):
        expected.pop(key)
        actual.pop(key)
    compare(expected, actual)
    nbt = validate_nbt(json.loads((bundle / 'artificial-enchantment-probe.json').read_bytes()), report['cases'])
    exact = json.loads((bundle / 'exact-exit.json').read_bytes())
    stop = json.loads((bundle / 'normal-stop.json').read_bytes())
    assert exact['completed'] and exact['process_or_window_mutation'] is False
    assert stop['normal_only'] and not stop['force_used'] and stop['stopped'] and stop['restored']
    for role in ('game', 'mcdk'):
        assert exact['processes'][role]['pid'] == stop['processes'][role]['pid'] == report['session'][role + '_pid']
        assert exact['processes'][role]['identity'] == stop['processes'][role]['identity'] == report['session'][role + '_identity']
    wer = json.loads((bundle / 'wer.json').read_bytes())
    xml = [contained(bundle, row['path']).read_text(encoding='utf-8') for row in wer['events']]
    assert len(matching_wer(xml, exact['processes']['game'])) == len(xml) and xml
    result = {'schema': 1, 'completed': True, 'production_qualified': False,
        'files_verified': len(manifest['files']), 'captures_verified': len(receipts),
        'calibration_replayed': True, 'vertical_fov': calibration['vertical_fov'],
        'original_analysis_reproduced': True, 'cases': len(actual['cases']),
        'paired_visible_geometry_passed': all(row['passed'] for case in actual['cases'] for row in case['native_product'].values()),
        'paired_comparisons': sum(len(case['native_product']) for case in actual['cases']),
        'ideal_support_model_holdouts_passed': actual['geometry_holdouts_passed'],
        'ideal_model_rejects_native_cases': [case['id'] for case in actual['cases'] if not case['routes']['native']['candidate']['passed']],
        'nbt': nbt, 'exit_codes': {role: row['exit_code_hex'] for role, row in exact['processes'].items()},
        'wer_exact_identity_events': len(xml)}
    write_json(output / 'replay.json', result)
    return result


def finalize(bundle, result):
    manifest, _ = verify_files(bundle)
    replayed = json.loads(result.read_bytes())
    assert replayed['completed'] and replayed['original_analysis_reproduced']
    assert replayed['captures_verified'] == manifest['png_count']
    shutil.copyfile(result, bundle / 'replay-result.json')
    (bundle / '.gitattributes').write_text(
        '* -text whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol\n', encoding='ascii')
    (bundle / 'README.md').write_text('''# Native frame-block holdouts R21

Status: unqualified. This restored six-case run compares the fixed quarter-cube
candidate with independently inserted native stone and artificially enchanted
quartz block. The production gates remain false.

## Reproduce

Requires Python, NumPy, SciPy and Pillow. No game, MCDK connection, credentials
or original runtime directory is needed. From the repository root, choose a new
output directory:

```powershell
python -B -X utf8 docs/evidence/frame-block-holdouts-r21-v1/replay.py replay docs/evidence/frame-block-holdouts-r21-v1 .runtime/frame-block-replay-new
```

The frozen replayer checks every manifest byte and all 80 original PNG receipts,
recomputes independent three-view stone calibration, runs the original analyzer,
and compares its full numerical output with the preserved analysis. It also
checks native Item.Block preservation, enchantment readbacks, restoration,
retained process identities and matching exported WER events. Output goes into
the new directory. `replay-result.json` records the first successful replay.

## Observed Results

All 12 full/missing versus native silhouette comparisons pass the unchanged
thresholds. Five cases have IoU 1.0, edge P95 0 and maximum edge error 0.
Stone -75 degrees has IoU 0.9991575400168492, P95 0 and maximum error 1 pixel
on both routes: 4748 native pixels and 4744 product pixels. Native masks are
identical between stone and enchanted quartz at each view angle.

| View | Native pixels | Native bounds | Ideal-model RMS / max pixels |
| --- | ---: | --- | --- |
| 0 degrees | 5693 | [960,515,1035,593] | 0.86861649 / 1.51850453 |
| -75 degrees | 4748 | [955,512,1016,595] | 3.97533451 / 8.22946059 |
| +75 degrees | 4737 | [979,512,1040,595] | 4.51406 / 9.22902 |

Independent camera calibration passes at vertical FOV 66.6 degrees; individual
fits are 66.3, 66.3 and 66.6. The 74 main captures and six calibration captures
retain original PNG bytes, owner/PID/creation identity, QPC freshness and strict
schema-3 foreground guard records. Unrelated foreground titles are omitted.

`analysis-v1/multiview.json` is unchanged and keeps
`geometry_holdouts_passed=false`. Its support-only model fails on oblique native
silhouettes by the same 8-9 pixels as product silhouettes. Hull images show the
cyan model extending into the brown frame backboard while the green observed
outline is occluded. The native frame backboard is absent from the ideal model.
Its fitted scale 0.24000481 and depth 0.42508008 are consequently diagnostics,
not accepted dimensions. Keep the declared scale 0.25 and center Z 0.4375.

## Artificial Enchantment Chain

`artificial-enchantment-probe.json` retains the full actual typed Item compound,
server GetFrameItem result, client readback and restoration. Each of three
quartz matrix cases independently repeats the same native insertion chain in
`report.json`. A plain inventory quartz block is inserted by PlayerUseItemToPos;
only the observed native sword enchantment tag is then copied through
SetBlockEntityData. The original Item.Block is preserved, not synthesized.
Both server and client read Name minecraft:quartz_block, Damage 0, Count 1,
enchantment (9,3), Block name minecraft:quartz_block, pillar_axis y, val 0 and
version 18168865. This explicit synthetic enchantment write does not convert
the earlier public manufacturing API failures into success.

Actual native and product screenshots visibly contain pink/purple glint.
Single shown frames do not accept glint direction, time, phase or brightness.
Ordinary minecraft:quartz remains a distinct flat item.

## Source And Exit Bindings

`report.json` retains equal complete launch/before-after source hash maps and
their digest 36d897c8bd8e190c83d117b2c5ddc3c9feb454092b0e7f0a145c061c410c2c49.
`candidate.json` preserves original pre-run candidate metadata unchanged;
its old pending limitations are historical. Exact candidate resource bytes,
capture host tools and an offline analysis import closure are in `sources/`.
Manifest per-file bindings distinguish actual launch/capture hashes from
additional analysis dependencies recorded retrospectively. The original
analyzer recorded its own hash but not every dependency hash. This package
replays the pixels independently; it does not include every launch file byte
or claim to recreate a complete game installation.

`normal-stop.json` retains the 2026-10-15 18:14:12.268872 UTC normal-only close
request, initial timeout, successful prior fixture restoration and eventual
stopped registration. `exact-exit.json` retains handles opened before capture:
game PID 15144 / creation identity 134365611080856581 exited 0xC0000409 at
18:14:41.838365 UTC; MCDK PID 52476 / identity 134365611078631953 exited 0.
WER record 80432 matches both game PID and creation time, reporting
ucrtbase.dll / c0000409 at 18:14:17.8046502 UTC. Record 80433 has the same report
ID. XML files are UTF-8 EventLogRecord.ToXml exports, not original EVTX bytes.
No force stop was used. This was an abnormal exit; its cause is unresolved.

## Remaining Work

Model the independently measured frame backboard before interpreting absolute
depth fits. Repeat unchanged candidates for grass, log and planks; measure
glass separately. Cover six frame faces, eight rotations, editor pixels,
lighting, native glint timing and world lifecycle before production admission.
Production admission needs an explicit validated (name, aux) whitelist; material
acceptance alone must not admit all 324 opaque resource candidates.
''', encoding='ascii')
    manifest['files'] = {path.relative_to(bundle).as_posix(): digest(path)
        for path in sorted(bundle.rglob('*')) if path.is_file() and path != bundle / 'manifest.json'
        and '__pycache__' not in path.parts}
    write_json(bundle / 'manifest.json', manifest)
    verify_files(bundle)
    return {'files': len(manifest['files']), 'finalized': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    build_parser = commands.add_parser('build')
    for name in ('source', 'control', 'analysis', 'frozen', 'output'):
        build_parser.add_argument('--' + name, type=Path, required=True)
    replay_parser = commands.add_parser('replay')
    replay_parser.add_argument('bundle', type=Path)
    replay_parser.add_argument('output', type=Path)
    final_parser = commands.add_parser('finalize')
    final_parser.add_argument('bundle', type=Path)
    final_parser.add_argument('result', type=Path)
    args = vars(parser.parse_args())
    command = args.pop('command')
    actions = {'build': build, 'replay': replay, 'finalize': finalize}
    print(json.dumps(actions[command](**args)))


if __name__ == '__main__':
    main()
