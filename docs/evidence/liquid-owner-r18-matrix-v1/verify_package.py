"""Verify and optionally preserve the closed-gate R18 frozen water evidence."""
import argparse
from contextlib import ExitStack
import copy
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
REPORTS = ('liquid-r18-core-v1', 'liquid-r18-neighbors-v1')
ROUTES = ('editor', 'full', 'missing')
MAX_ARCHIVE_BYTES = 48_000_000
PART_TARGET_BYTES = 32 * 1024 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n', encoding='ascii')


def capture_archive(stem, route):
    family = 'core' if stem == REPORTS[0] else 'neighbors'
    return 'captures-%s-%s.zip' % (family, route)


def split_oversized(backup_root):
    """Keep each PNG beside its receipt; retain oversized originals outside ROOT."""
    backup_root = backup_root.resolve()
    if backup_root == ROOT.resolve() or ROOT.resolve() in backup_root.parents:
        raise ValueError('Archive backup must be outside the evidence package')
    index = json.loads((ROOT / 'capture-index.json').read_bytes())
    changed = False
    for name in sorted({row['archive'] for row in index}):
        if not re.fullmatch(r'captures-(core|neighbors)-(editor|full|missing)\.zip', name):
            continue
        original = ROOT / name
        if original.stat().st_size < MAX_ARCHIVE_BYTES:
            continue
        backup = backup_root / name
        if backup.exists():
            raise ValueError('Archive backup already exists: ' + str(backup))
        replacements = {}
        with zipfile.ZipFile(original) as source:
            members = {info.filename: info for info in source.infolist()}
            assert len(members) == len(source.infolist()), name
            chunks, chunk, chunk_bytes, paired = [], [], 0, set()
            for image in (info for info in source.infolist() if info.filename.endswith('.png')):
                receipt = str(Path(image.filename).with_suffix('.capture.json'))
                if receipt not in members:
                    receipt = str(Path(image.filename).with_suffix('.json'))
                pair = (image, members[receipt])
                pair_bytes = sum(info.file_size + 512 for info in pair)
                if pair_bytes >= PART_TARGET_BYTES:
                    raise ValueError('One PNG/receipt pair exceeds archive target: ' + image.filename)
                if chunk and chunk_bytes + pair_bytes >= PART_TARGET_BYTES:
                    chunks.append(chunk)
                    chunk, chunk_bytes = [], 0
                chunk.extend(pair)
                chunk_bytes += pair_bytes
                paired.update(info.filename for info in pair)
            if chunk:
                chunks.append(chunk)
            assert paired == set(members), name
            assert len(chunks) > 1, name
            for number, chunk in enumerate(chunks, 1):
                part_name = '%s-%02d.zip' % (original.stem, number)
                target = ROOT / part_name
                if target.exists():
                    raise ValueError('Archive part already exists: ' + part_name)
                with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED,
                                     compresslevel=9) as output:
                    for info in chunk:
                        output.writestr(copy.copy(info), source.read(info),
                                        compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
                        replacements[info.filename] = part_name
                assert target.stat().st_size < MAX_ARCHIVE_BYTES, part_name
                with zipfile.ZipFile(target) as output:
                    for info in chunk:
                        assert output.read(info.filename) == source.read(info), info.filename
        backup_root.mkdir(parents=True, exist_ok=True)
        original.rename(backup)
        for row in index:
            if row['archive'] == name:
                row['archive'] = replacements[row['member']]
        changed = True
    if changed:
        write(ROOT / 'capture-index.json', index)


def split_existing():
    original = ROOT / 'captures.zip'
    index = json.loads((ROOT / 'capture-index.json').read_bytes())
    with zipfile.ZipFile(original) as source, ExitStack() as stack:
        targets = {}
        for stem in REPORTS:
            for route in ROUTES:
                name = capture_archive(stem, route)
                assert not (ROOT / name).exists(), name
                targets[(stem, route)] = stack.enter_context(zipfile.ZipFile(ROOT / name, 'w'))
        for member in source.infolist():
            matches = [(stem, route) for stem in REPORTS for route in ROUTES
                       if member.filename.startswith(stem + '_' + route + '_')]
            assert len(matches) == 1, member.filename
            targets[matches[0]].writestr(member, source.read(member))
    for row in index:
        row['archive'] = capture_archive(Path(row['report']).stem, row['label'].split('_', 1)[0])
    write(ROOT / 'capture-index.json', index)


def archive():
    reports = ROOT / 'reports'
    reports.mkdir(exist_ok=True)
    files = []
    with ExitStack() as stack:
        targets = {}
        for stem in REPORTS:
            for route in ROUTES:
                name = capture_archive(stem, route)
                if (ROOT / name).exists():
                    raise ValueError('Capture archive already exists: ' + name)
                targets[(stem, route)] = stack.enter_context(zipfile.ZipFile(ROOT / name, 'w'))
        for stem in REPORTS:
            source = REPO / '.runtime' / (stem + '.json')
            report = json.loads(source.read_bytes())
            shutil.copy2(source, reports / source.name)
            for label, receipt in report['captures'].items():
                route = label.split('_', 1)[0]
                target = targets[(stem, route)]
                image = Path(receipt['path'])
                data = image.read_bytes()
                assert digest(data) == receipt['sha256'], image
                target.writestr(image.name, data)
                native_receipt = image.with_suffix('.capture.json')
                if not native_receipt.exists():
                    native_receipt = image.with_suffix('.json')
                if native_receipt.exists():
                    target.write(native_receipt, native_receipt.name)
                files.append({'report': source.name, 'label': label, 'archive': capture_archive(stem, route),
                              'member': image.name, 'sha256': digest(data), 'bytes': len(data)})
    write(ROOT / 'capture-index.json', files)


def verify():
    rows = []
    pairs = set()
    captures = 0
    external_receipts = 0
    foreground_changes = []
    archive_sizes = {}
    index = json.loads((ROOT / 'capture-index.json').read_bytes())
    indexed = {(row['report'], row['label']): row for row in index}
    assert len(indexed) == len(index) == 348
    with ExitStack() as stack:
        archives = {}
        expected_members = {}
        for name in sorted({row['archive'] for row in index}):
            assert re.fullmatch(r'captures-(core|neighbors)-(editor|full|missing)(-[0-9]{2})?\.zip', name), name
            archive_sizes[name] = (ROOT / name).stat().st_size
            assert archive_sizes[name] < MAX_ARCHIVE_BYTES, name
            archives[name] = stack.enter_context(zipfile.ZipFile(ROOT / name))
            expected_members[name] = set()
        for stem in REPORTS:
            report = json.loads((ROOT / 'reports' / (stem + '.json')).read_bytes())
            assert all(report[name] is True for name in ('completed', 'restored', 'source_unchanged'))
            assert report['cleanup_errors'] == []
            assert report['frozen'] is True
            assert report['product_style_accepted'] is False
            current = {(route, case) for route in report['routes'] for case in report['cases']}
            assert not pairs & current
            pairs.update(current)
            for label, receipt in report['captures'].items():
                entry = indexed[(stem + '.json', label)]
                base = capture_archive(stem, label.split('_', 1)[0])[:-4]
                assert re.fullmatch(re.escape(base) + r'(-[0-9]{2})?\.zip', entry['archive'])
                assert entry['member'] == Path(receipt['path']).name
                archive_file = archives[entry['archive']]
                data = archive_file.read(entry['member'])
                assert digest(data) == receipt['sha256'] and len(data) == receipt['bytes']
                assert entry['sha256'] == receipt['sha256'] and entry['bytes'] == receipt['bytes']
                native_receipt = str(Path(entry['member']).with_suffix('.capture.json'))
                if native_receipt not in archive_file.namelist():
                    native_receipt = str(Path(entry['member']).with_suffix('.json'))
                original_receipt = json.loads(archive_file.read(native_receipt))
                assert all(receipt.get(key) == value for key, value in original_receipt.items()), native_receipt
                assert set(receipt) - set(original_receipt) <= {
                    'scene_before', 'scene_after', 'camera_expected', 'camera_before', 'camera_after'}
                expected_members[entry['archive']].update((entry['member'], native_receipt))
                external_receipts += 1
                assert receipt['ok'] and receipt['reliable'] and receipt['guarded_no_activation']
                assert receipt['agent_activation_allowed'] is False and receipt['activation_fallback'] is False
                assert receipt['background_safe']
                if not receipt['foreground_unchanged']:
                    assert receipt['user_foreground_allowed'] is True
                    assert receipt['foreground_policy'] == 'allow_user_foreground'
                    foreground_changes.append({'report': stem, 'label': label})
                assert (receipt['width'], receipt['height']) == (1994, 1105)
                captures += 1
            rows.append({'report': stem, 'rows': len(report['rows']),
                         'captures': len(report['captures']), 'route_cases': len(current),
                         'source_contract_sha256': report['source_contract_sha256']})
        for name, archive_file in archives.items():
            assert set(archive_file.namelist()) == expected_members[name], name
            assert len(archive_file.namelist()) == len(expected_members[name]), name
    assert len(pairs) == 57 and captures == external_receipts == 348
    launch = json.loads((ROOT / 'reports' / 'liquid-r18-launch-inputs-v6.json').read_bytes())
    assert all(row['source_contract_sha256'] == launch['source_contract_sha256'] for row in rows)
    cold = json.loads((ROOT / 'reports' / 'archived-launch.json').read_bytes())
    assert cold['source_sha256'] == launch['source_sha256']
    with zipfile.ZipFile(ROOT / 'launch-inputs.zip') as archive_file:
        assert set(archive_file.namelist()) == set(launch['source_sha256'])
        for name, expected in launch['source_sha256'].items():
            assert digest(archive_file.read(name)) == expected, name
    result = {'verified': True, 'product_qualified': False, 'reports': rows,
              'route_case_pairs': len(pairs), 'verified_capture_pngs': captures,
              'verified_external_receipts': external_receipts,
              'capture_archive_sizes': archive_sizes, 'archive_limit_bytes': MAX_ARCHIVE_BYTES,
              'frozen_launch_files': len(launch['source_sha256']),
              'foreground_changed_during_capture': foreground_changes}
    write(ROOT / 'verification.json', result)
    return result


def manifest():
    files = {path.relative_to(ROOT).as_posix(): digest(path.read_bytes())
             for path in sorted(ROOT.rglob('*')) if path.is_file()
             and path.name != 'manifest.json' and '__pycache__' not in path.parts}
    write(ROOT / 'manifest.json', {'schema': 1, 'files': files})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', action='store_true')
    parser.add_argument('--split-existing', action='store_true')
    parser.add_argument('--split-oversized', action='store_true')
    parser.add_argument('--archive-backup', type=Path,
                        default=REPO / '.runtime' / 'liquid-evidence-oversized-archive-backups')
    parser.add_argument('--refresh-manifest', action='store_true')
    args = parser.parse_args()
    if args.archive:
        archive()
    if args.split_existing:
        split_existing()
    if args.archive or args.split_existing or args.split_oversized:
        split_oversized(args.archive_backup)
    print(json.dumps(verify(), sort_keys=True))
    if args.refresh_manifest:
        manifest()
    else:
        declared = json.loads((ROOT / 'manifest.json').read_bytes())['files']
        for name, expected in declared.items():
            assert digest((ROOT / name).read_bytes()) == expected, name


if __name__ == '__main__':
    main()
