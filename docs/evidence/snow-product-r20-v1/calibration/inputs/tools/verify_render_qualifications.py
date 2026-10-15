"""Check that deployed render gates bind the actual worktree or staged bytes.

This verifies provenance, not visual correctness. Original pixel reports still
need their own analyzers and human review before a gate can be enabled.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'behavior_pack/modern_projection/projection/'
BUNDLES = {
    'cauldron': ('cauldron_qualification_data.py', 'cauldron-product-r15'),
    'banner': ('banner_render_contract.py', 'banner-product-r16'),
    'portal': ('portal_profile.py', 'portal-product-r16'),
    'spawner': ('spawner_marker_qualification.py', 'spawner-product-r16'),
    'book': ('book_qualification_data.py', 'book-product-r18'),
}
RESOURCE_CONTRACTS = {
    'cauldron': 'tools/data/cauldron_resource_contract_nemc310_v1.json',
    'banner': 'tools/data/banner_render_contract_nemc310_v1.json',
    'portal': 'tools/data/portal_resource_contract_nemc310_v1.json',
    'book': 'tools/data/book_resource_contract_nemc310_v1.json',
}
SHARED_REGISTRIES = frozenset(('resource_pack/materials/entity.material',
                               'resource_pack/models/netease_models.json',
                               'resource_pack/blocks.json'))


def literal_assignments(content):
    values = {}
    for node in ast.parse(content).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                values[node.targets[0].id] = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                continue
    return values


def source_digest(name, content):
    # Portal admission hashes its own implementation without circular gate data.
    if name == PREFIX + 'portal_profile.py':
        text = content.decode('ascii')
        text = re.sub(r'^PRODUCT_QUALIFIED = .*$', 'PRODUCT_QUALIFIED = False', text, flags=re.M)
        text = re.sub(r'^QUALIFICATION_SHA256 = .*$', "QUALIFICATION_SHA256 = 'Pending'", text, flags=re.M)
        content = text.encode('ascii')
    return hashlib.sha256(content).hexdigest()


def json_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True,
                                    separators=(',', ':')).encode('ascii')).hexdigest()


def verify_owned_entries(read, relative, section, expected, errors):
    registry = json.loads(read(relative))
    if section is not None:
        registry = registry[section]
    for key, value in sorted(expected.items()):
        if registry.get(key) != value:
            errors.append('Qualified registration changed: ' + relative + ':' + key)
    return len(expected)


def verify_resources(name, manifest, read, errors):
    contract_path = RESOURCE_CONTRACTS.get(name)
    if contract_path is None:
        if name != 'spawner':
            return 0
        # The original spawner admission freezes canonical asset hashes and
        # requires this exact render-only block registration for each marker.
        data = literal_assignments(read(PREFIX + 'spawner_marker_data.py'))
        markers = data['MARKERS']
        contract = {}
        for marker in markers.values():
            stem = marker.split(':', 1)[1]
            for relative in ('resource_pack/models/netease_block/' + stem + '.json',
                             'behavior_pack/netease_blocks/' + stem + '.json'):
                contract[relative] = json_digest(json.loads(read(relative)))
        if (json_digest(contract) != manifest.get('resource_contract_sha256') or
                json_digest(contract) != data.get('RESOURCE_CONTRACT_SHA256')):
            errors.append('Qualified spawner assets differ from their frozen contract')
        registrations = dict((marker, {'netease_model': marker, 'sound': 'stone'})
                             for marker in markers.values())
        return len(contract) + verify_owned_entries(
            read, 'resource_pack/blocks.json', None, registrations, errors)

    content = read(contract_path)
    contract = json.loads(content)
    if hashlib.sha256(content).hexdigest() != manifest.get('resource_contract_sha256'):
        errors.append('Qualification resource contract differs: ' + contract_path)
    if contract.get('engine_version') != manifest.get('engine_version'):
        errors.append('Qualification resource engine differs: ' + contract_path)
    fingerprints = dict(contract.get('output_sha256', {}))
    fingerprints.update(contract.get('source_sha256', {}))
    count = 0
    for relative, expected in sorted(fingerprints.items()):
        if relative in SHARED_REGISTRIES:
            continue
        count += 1
        if hashlib.sha256(read(relative)).hexdigest() != expected:
            errors.append('Qualified resource changed: ' + relative)
    for section, relative, nested in (
            ('materials', 'resource_pack/materials/entity.material', 'materials'),
            ('models', 'resource_pack/models/netease_models.json', None)):
        entries = contract.get(section, {})
        if entries:
            count += verify_owned_entries(read, relative, nested, entries, errors)
    return count


def verify_bundle(name, gate_path, folder, read):
    gate = literal_assignments(read(PREFIX + gate_path))
    if gate.get('PRODUCT_QUALIFIED') is not True:
        return {'bundle': name, 'enabled': False, 'verified': False, 'errors': []}
    relative = 'docs/evidence/' + folder + '/qualification.json'
    content = read(relative)
    manifest = json.loads(content)
    errors = []
    if hashlib.sha256(content).hexdigest() != gate.get('QUALIFICATION_SHA256'):
        errors.append('Qualification fingerprint differs: ' + relative)
    gates = manifest.get('gates', {})
    if not gates or any(value is not True for value in gates.values()):
        errors.append('An enabled bundle has incomplete acceptance gates')
    sources = manifest.get('implementation_sha256', {})
    if not sources:
        errors.append('An enabled bundle has no implementation provenance')
    body_sources = manifest.get('body_sha256', {})
    if name == 'book' and (not body_sources or not manifest.get('owned_registries')):
        errors.append('Qualified book bundle omits its static body provenance')
    fingerprints = dict(sources)
    for source, expected in body_sources.items():
        if source in fingerprints and fingerprints[source] != expected:
            errors.append('Qualification has conflicting implementation fingerprints: ' + source)
        fingerprints[source] = expected
    for source, expected in sorted(fingerprints.items()):
        if source_digest(source, read(source)) != expected:
            errors.append('Qualified implementation changed: ' + source)
    resource_count = verify_resources(name, manifest, read, errors)
    for registration in manifest.get('owned_registries', ()):
        resource_count += verify_owned_entries(read, registration['path'],
            registration['section'], registration['entries'], errors)
    return {'bundle': name, 'enabled': True, 'verified': not errors,
            'source_count': len(fingerprints), 'resource_count': resource_count,
            'engine': manifest.get('engine_version'),
            'qualification_sha256': hashlib.sha256(content).hexdigest(), 'errors': errors}


def reader(root, staged=False):
    def read(relative):
        if staged:
            return subprocess.run(['git', 'show', ':' + relative], cwd=root,
                                  check=True, capture_output=True).stdout
        return (root / relative).read_bytes()
    return read


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--staged', action='store_true')
    parser.add_argument('--bundle', choices=tuple(BUNDLES), action='append')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    read = reader(args.root.resolve(), args.staged)
    rows = []
    for name in args.bundle or BUNDLES:
        try:
            rows.append(verify_bundle(name, *BUNDLES[name], read))
        except (OSError, ValueError, SyntaxError, subprocess.CalledProcessError) as error:
            rows.append({'bundle': name, 'enabled': None, 'verified': False,
                         'errors': [type(error).__name__ + ': ' + str(error)]})
    report = {'schema': 1, 'source': 'index' if args.staged else 'worktree',
              'verified': not any(row['errors'] for row in rows), 'bundles': rows,
              'pixel_acceptance_claimed': False}
    content = json.dumps(report, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding='ascii', newline='\n')
    print(content)
    return 0 if report['verified'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
