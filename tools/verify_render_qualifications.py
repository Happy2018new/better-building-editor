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
}


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
    for source, expected in sorted(sources.items()):
        if source_digest(source, read(source)) != expected:
            errors.append('Qualified implementation changed: ' + source)
    return {'bundle': name, 'enabled': True, 'verified': not errors,
            'source_count': len(sources), 'engine': manifest.get('engine_version'),
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
