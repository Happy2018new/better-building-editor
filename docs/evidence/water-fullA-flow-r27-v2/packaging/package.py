"""Exact selected-PNG evidence, keeping original failures and host replay apart."""
import argparse
import base64
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
HOST = WORK.with_name('water-merged-fullA-v2')
OUT = WORK.with_name('water-merged-fullA-v2-package-v1')
LIMIT = 240000


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def build_inputs(anchor_analysis, extras):
    inputs = {}

    def add(label, path):
        path = Path(path).resolve()
        assert label not in inputs and path.is_file(), (label, path)
        assert path.is_relative_to(ROOT), path
        inputs[label] = path

    names = (
        'product-v2-a-v1.json', 'product-v2-a-v1-host.json', 'product-v2-a-v1-handles.json',
        'product-v2-camera-seam-v1.json', 'product-v2-camera-seam-v1-host.json',
        'product-v2-camera-seam-v1-handles.json', 'group-execution-v1.json',
        'final-source-binding-v1.json', 'prelaunch-host-binding-v1.json', 'dependency-inventory-v1.json',
        'plan-v1.json', 'root-grant-v1.json', 'cold-default-observation-v1.json',
        'resize-background-v1.json', 'world-baseline-v1.json', 'independent-restore-after-camera.json',
        'independent-restore-v1.json', 'continuous-handle-guard-v1.json', 'helper-retirement-v1.json',
        'launch/launch.json', 'launch/exact-exit.json', 'postrun-whitelist-v1.json',
        'host-changes-v2.patch', 'camera.stdout.txt', 'camera.stderr.txt', 'A.stdout.txt', 'A.stderr.txt')
    for name in names:
        add('capture/' + name, HOST / name)
    for path in sorted(HOST.glob('*.py')):
        add('host/' + path.name, path)
    for view in ('front', 'right', 'tilted'):
        prefix = 'product-v2-camera-seam-v1_' + view
        for suffix in ('shown', 'hidden', 'signal', 'signal_outline_comparison'):
            add('camera/' + prefix + '_' + suffix + '.png', HOST / (prefix + '_' + suffix + '.png'))
        for suffix in ('shown', 'hidden'):
            add('camera/' + prefix + '_' + suffix + '.capture.json', HOST / (prefix + '_' + suffix + '.capture.json'))
    product = json.loads((HOST / 'product-v2-a-v1.json').read_bytes())
    selected_png_count = 12
    for key, burst in product['flow_bursts'].items():
        capture = burst['capture']
        native_file = capture['native_manifest_file']
        native_path = Path(native_file['path'])
        assert sha(native_path.read_bytes()) == native_file['sha256']
        assert native_path.stat().st_size == native_file['bytes']
        add('bursts/' + key + '/manifest.json', native_path)
        add('bursts/' + key + '/capture.json', HOST / ('product-v2-a-v1_' + key + '_burst.capture.json'))
        frames = [frame['png'] for frame in capture['frames'] if frame.get('png')]
        for phase, png in (('first', frames[0]), ('last', frames[-1])):
            path = Path(png['path'])
            assert sha(path.read_bytes()) == png['sha256'] and path.stat().st_size == png['bytes']
            add('bursts/' + key + '/' + phase + '_' + path.name, path)
            selected_png_count += 1
        for name in (key, key + '_later'):
            receipt = product['captures'][name]
            path = Path(receipt['path'])
            assert sha(path.read_bytes()) == receipt['sha256'] and path.stat().st_size == receipt['bytes']
            add('static/' + name + '.png', path)
            add('static/' + name + '.capture.json', HOST / ('product-v2-a-v1_' + name + '.capture.json'))
            selected_png_count += 1
    directories = (
        ('strict-original', WORK.with_name('root-water-fullA-v2-strict-analysis-v2')),
        ('timelines', WORK.with_name('root-water-fullA-v2-timelines-v1')),
        ('strict-gui-anchor', anchor_analysis),
        ('original-roi-diagnosis', WORK.with_name('water-editor-roi-readonly-v1')),
        ('anchor-proposal', WORK.with_name('water-editor-anchor-candidate-v1')),
    )
    for prefix, directory in directories:
        for path in sorted(directory.iterdir()):
            if path.is_file() and path.suffix in ('.json', '.py', '.png', '.patch', '.md'):
                add(prefix + '/' + path.name, path)
    analysis = WORK.with_name('water-merged-fullA-analysis-v2')
    for name in ('run_analysis.py', 'inspect_all_timelines.py', 'run_analysis_anchor_v1.py',
                 'anchor-wrapper-changes-v1.patch'):
        add('analysis-host/' + name, analysis / name)
    for name in ('root_water_strict_session_v1.py', 'root-water-strict-session-binding-v1.json'):
        add('strict-original-launch/' + name, WORK.parent / name)
    add('sampling/startup-host-contract-v1.json',
        ROOT / '.runtime/round-20261021/water-startup-protocol-v2/host-contract-v1.json')
    add('sampling/inspect_timeline.py', WORK.with_name('water-next-A-workflow-v1') / 'inspect_timeline.py')
    binding = json.loads((HOST / 'final-source-binding-v1.json').read_bytes())
    project = Path(binding['project'])
    for name in ('tools/analyze_product_water.py', 'tools/analyze_product_water_flow.py',
                 'tools/water_capture_contract.py', 'behavior_pack/modern_projection/projection/camera.py',
                 'behavior_pack/modern_projection/projection/liquid_product_deployment.py',
                 'behavior_pack/modern_projection/projection/liquid_deployment.py',
                 'behavior_pack/modern_projection/projection/liquid_viewport.py',
                 'behavior_pack/modern_projection/projection/scene.py'):
        assert sha((project / name).read_bytes()) == binding['source_sha256'][name]
        add('frozen-source-selected/' + name, project / name)
    add('calibration/candidate_extractor.py',
        WORK.with_name('water-camera-extractor-seam-candidate-v1') / 'candidate_extractor.py')
    if extras:
        extra_inputs = json.loads(extras.read_bytes())
        if isinstance(extra_inputs, list):
            extra_inputs = {Path(value).name: value for value in extra_inputs}
        assert isinstance(extra_inputs, dict)
        for label, value in extra_inputs.items():
            add('root-extra/' + label, value)
        add('packaging/root-extras-inputs.json', extras)
    add('packaging/package.py', Path(__file__))
    return inputs, selected_png_count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--anchor-analysis', type=Path, required=True)
    parser.add_argument('--root-extras', type=Path)
    args = parser.parse_args()
    assert not OUT.exists(), 'Use a new package version; never overwrite evidence'
    inputs, selected_png_count = build_inputs(args.anchor_analysis.resolve(), args.root_extras)
    redactor_path = WORK.with_name('water-evidence-redaction-v4') / 'package_v4_optimized.py'
    scanner_path = WORK.parent / 'root_review_wire_bundle_v3.py'
    scanner = load('reviewed_original_scanner', scanner_path)
    assert sha(scanner_path.read_bytes()) == '6c5bbd86dcf5fdcbf36ab709806beff4cb0230cbc0dad1d505b8fc172f95429e'
    redactor = load('reviewed_v4_recursive_redactor', redactor_path)
    inputs['packaging/reviewed_recursive_redactor.py'] = redactor_path
    inputs['packaging/original_independent_scanner.py'] = scanner_path
    supplements = {}
    for name in ('water-size720-r27-v4', 'water-merged-flow-editor-r27-v1', 'water-fullA-camera-failure-r27-v1'):
        path = ROOT / 'docs/evidence' / name / 'index.json'
        assert path.is_file()
        supplements[name] = {'path': str(path), 'sha256': sha(path.read_bytes())}
    assert supplements['water-size720-r27-v4']['sha256'] == '1cb4a95ef9a57ed659471ec243d34e0dc848ba40ad4f1700d146ef8a3c458deb'
    original = {label: path.read_bytes() for label, path in inputs.items()}
    for label, raw in original.items():
        if inputs[label].suffix == '.json':
            redactor.discover(json.loads(raw))
    for path in (Path.home() / '.pyreact-debug/instances').glob('*/session.json'):
        redactor.discover(json.loads(path.read_bytes()))
    redactor.SECRET_PATTERN = redactor.compile_secret_pattern(redactor.secrets)
    fixtures = [
        json.dumps({'stdout': json.dumps({'token': 'synthetic-fullA-token'})}).encode(),
        json.dumps({'payload': base64.b64encode(json.dumps({'mcp_url': 'http://localhost/private'}).encode()).decode()}).encode(),
        ('"' + ''.join('\\u%04x' % ord(c) for c in 'sk-' + 'X' * 32) + '"').encode()]
    for raw in fixtures:
        assert scanner.credentials(raw)
        clean, unused = redactor.sanitize_raw(raw)
        assert not redactor.combined_credentials(scanner, clean)
    negative = b'{"sha256":"' + b'a' * 64 + b'","record_count":649}'
    assert redactor.sanitize_raw(negative)[0] == negative
    prepared = {}
    for label, raw in original.items():
        if inputs[label].suffix == '.png':
            prepared[label] = raw, []
        else:
            clean, locations = redactor.sanitize_raw(raw)
            assert not redactor.combined_credentials(scanner, clean), label
            prepared[label] = clean, locations
    OUT.mkdir()
    entries = []
    for label, path in sorted(inputs.items()):
        raw = original[label]
        clean, locations = prepared[label]
        encoding = 'png' if path.suffix == '.png' else ('gzip' if len(clean) > 100000 else 'utf8')
        encoded = gzip.compress(clean, mtime=0) if encoding == 'gzip' else clean
        entry = {'logical_name': label, 'original_raw_path': str(path.resolve()),
                 'original_raw_sha256': sha(raw), 'original_raw_bytes': len(raw),
                 'decoded_sanitized_sha256': sha(clean), 'decoded_sanitized_bytes': len(clean),
                 'original_bytes_reconstructable': clean == raw, 'encoding': encoding,
                 'redacted_fields': locations, 'redaction_occurrences': len(locations), 'derived_parts': []}
        stem = label + ('.gz' if encoding == 'gzip' else '')
        pieces = [encoded[offset:offset + LIMIT] for offset in range(0, len(encoded), LIMIT)] or [b'']
        for index, piece in enumerate(pieces, 1):
            name = stem + ('.%03d' % index if len(pieces) > 1 else '')
            target = OUT / name
            target.parent.mkdir(exist_ok=True, parents=True)
            with target.open('xb') as stream:
                stream.write(piece)
            entry['derived_parts'].append({'path': name, 'bytes': len(piece), 'sha256': sha(piece)})
        entries.append(entry)
    png_count = sum(entry['encoding'] == 'png' for entry in entries)
    index = {'schema': 3, 'created_at_utc': datetime.now(timezone.utc).isoformat(),
             'scope': '15-cell capture; original legacy-anchor failure and separate host GUI-anchor replay retained.',
             'supplements': supplements, 'entry_count': len(entries), 'entries': entries,
             'single_file_limit_bytes': LIMIT,
             'source_contract_sha256': '027f11186bb5e50b4d9a0dc80a5ba4d06342104e1be4c2cc6de51a9f206bcf1a',
             'selected_original_PNGs': selected_png_count, 'PNG_entries_including_explicit_overlays': png_count,
             'derived_overlay_count': png_count - selected_png_count,
             'full_burst_PNGs_included': False, 'source_archive_included': False,
             'lossy_visual_references': 0, 'original_raws_modified': False,
             'redaction_policy': 'Reviewed recursive JSON/base64/unescape and exact credentials; [REDACTED]; original/new SHA separate.',
             'redactor_sha256': sha(redactor_path.read_bytes()), 'independent_scanner_sha256': sha(scanner_path.read_bytes()),
             'credential_findings': 0, 'redaction_control_count': 4,
             'formal_A_accepted': False, 'world_A_accepted': False, 'production_admission_performed': False,
             'default_path_evidence': False, 'source_release_qualification_granted': False, 'manual_closures_added': 0}
    index_raw = (json.dumps(index, indent=2) + '\n').encode('ascii')
    if len(index_raw) >= LIMIT:
        index_raw = (json.dumps(index, separators=(',', ':')) + '\n').encode('ascii')
    assert len(index_raw) < LIMIT
    with (OUT / 'index.json').open('xb') as stream:
        stream.write(index_raw)
    expected_files = {'index.json'}
    exact = redactions = 0
    for entry in entries:
        encoded = b''
        for part in entry['derived_parts']:
            piece = (OUT / part['path']).read_bytes()
            assert len(piece) == part['bytes'] <= LIMIT and sha(piece) == part['sha256']
            expected_files.add(part['path'])
            encoded += piece
        clean = gzip.decompress(encoded) if entry['encoding'] == 'gzip' else encoded
        assert sha(clean) == entry['decoded_sanitized_sha256'] and len(clean) == entry['decoded_sanitized_bytes']
        if entry['encoding'] != 'png':
            assert not redactor.combined_credentials(scanner, clean), entry['logical_name']
        if entry['original_bytes_reconstructable']:
            assert clean == original[entry['logical_name']]
            exact += 1
        redactions += entry['redaction_occurrences']
    assert all(path.read_bytes() == original[label] for label, path in inputs.items())
    for name, supplement in supplements.items():
        assert sha(Path(supplement['path']).read_bytes()) == supplement['sha256'], name
    actual_files = {path.relative_to(OUT).as_posix() for path in OUT.rglob('*') if path.is_file()}
    assert actual_files == expected_files
    assert not redactor.combined_credentials(scanner, (OUT / 'index.json').read_bytes())
    review = {'schema': 1, 'passed': True, 'package_path': str(OUT), 'index_sha256': sha(index_raw),
              'entries': len(entries), 'stored_files': len(actual_files),
              'stored_bytes': sum((OUT / name).stat().st_size for name in actual_files),
              'maximum_file_bytes': max((OUT / name).stat().st_size for name in actual_files),
              'originals_reconstructed': exact, 'selected_original_PNGs': selected_png_count,
              'derived_overlays': png_count - selected_png_count, 'redaction_occurrences': redactions,
              'credential_findings': 0, 'original_inputs_unchanged': True, 'supplement_indexes_unchanged': True,
              'formal_A_accepted': False, 'manual_closures_added': 0}
    with (WORK / 'package-review-v1.json').open('x', encoding='ascii') as stream:
        json.dump(review, stream, indent=2)
    print(json.dumps(review))


if __name__ == '__main__':
    main()
