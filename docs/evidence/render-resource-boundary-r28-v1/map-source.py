"""Read Git blobs only; map declared resources and Scene owner effects, no SDK import."""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
COMMIT = 'b70ce7bf13ad6a4472f2b089ac812c162b174861'
CONTRACTS = {
    'water': 'liquid_product_resource_contract_v1.json',
    'cauldron': 'cauldron_resource_contract_nemc310_v1.json',
    'portal': 'portal_resource_contract_nemc310_v1.json',
    'book': 'book_resource_contract_nemc310_v1.json',
}

class GitSource:
    def __init__(self):
        self.tree = {}
        for row in subprocess.check_output(['git', 'ls-tree', '-rz', COMMIT], cwd=ROOT).split(b'\0'):
            if row:
                header, path = row.split(b'\t', 1)
                self.tree[path.decode('utf8')] = header.split()[2].decode('ascii')
        self.proc = subprocess.Popen(['git', 'cat-file', '--batch'], cwd=ROOT,
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        self.cache = {}

    def read(self, path):
        if path not in self.cache:
            oid = self.tree[path]
            self.proc.stdin.write((oid + '\n').encode('ascii'))
            self.proc.stdin.flush()
            actual, kind, size = self.proc.stdout.readline().split()
            data = self.proc.stdout.read(int(size))
            assert self.proc.stdout.read(1) == b'\n' and actual.decode() == oid and kind == b'blob'
            self.cache[path] = data
        return self.cache[path]

    def json(self, path):
        return json.loads(self.read(path))

    def close(self):
        self.proc.stdin.close()
        assert self.proc.wait() == 0


def map_resources(source):
    model_path = 'resource_pack/models/netease_models.json'
    material_path = 'resource_pack/materials/entity.material'
    actual_models = source.json(model_path)
    actual_materials = source.json(material_path)['materials']
    by_base = {}
    for name in actual_materials:
        if name != 'version':
            by_base.setdefault(name.split(':')[0], []).append(name)
    rows, unresolved = [], []
    shared_contract_hashes = []
    for family, name in CONTRACTS.items():
        contract_path = 'tools/data/' + name
        contract = source.json(contract_path)
        for path, expected in contract['output_sha256'].items():
            data = source.read(path)
            actual = hashlib.sha256(data).hexdigest()
            if actual != expected:
                shared_contract_hashes.append({'family': family, 'path': path,
                    'expected_sha256': expected, 'actual_raw_sha256': actual,
                    'shared_registry': path in (model_path, material_path)})
        for identifier, expected in sorted(contract['models'].items()):
            actual = actual_models.get(identifier)
            entry = {'family': family, 'identifier': identifier, 'contract': contract_path,
                     'registry': model_path, 'definition_equal_to_contract': actual == expected,
                     'local_files': [], 'material_chain': [], 'external_material_parents': []}
            if actual is None:
                unresolved.append({'kind': 'missing_model', 'identifier': identifier})
                rows.append(entry)
                continue
            paths = [('mesh', 'resource_pack/models/' + actual['mesh']),
                     ('skeleton', 'resource_pack/models/' + actual['skeleton'])]
            paths.extend(('texture:' + slot, 'resource_pack/textures/models/' + value + '.png')
                         for slot, value in actual.get('texture', {}).items())
            for slot, value in actual.get('animation', {}).items():
                unresolved.append({'kind': 'animation_reference_not_resolved', 'model': identifier,
                                   'slot': slot, 'value': value})
            pending, seen = [actual['material']], set()
            while pending:
                base = pending.pop()
                if base in seen:
                    unresolved.append({'kind': 'material_cycle', 'model': identifier, 'base': base})
                    continue
                seen.add(base)
                matches = by_base.get(base, [])
                if not matches:
                    entry['external_material_parents'].append(base)
                    continue
                if len(matches) != 1:
                    unresolved.append({'kind': 'ambiguous_material', 'model': identifier, 'names': matches})
                    continue
                key = matches[0]
                material = actual_materials[key]
                expected_material = contract.get('materials', {}).get(key)
                entry['material_chain'].append({'key': key, 'registry': material_path,
                    'matches_declared_contract': material == expected_material if expected_material is not None else None})
                paths.extend((field, 'resource_pack/' + material[field])
                             for field in ('vertexShader', 'fragmentShader') if field in material)
                if ':' in key:
                    pending.append(key.split(':', 1)[1])
            for kind, path in paths:
                exists = path in source.tree
                entry['local_files'].append({'kind': kind, 'path': path, 'in_exact_commit': exists})
                if exists:
                    data = source.read(path)
                    if kind in ('vertexShader', 'fragmentShader'):
                        entry.setdefault('shader_includes', []).extend(
                            {'source': path, 'include': inc, 'resolution': 'engine_or_include_search_path_unproven'}
                            for inc in re.findall(r'^\s*#include\s+["<]([^">]+)[">]', data.decode('utf8'), re.M))
                else:
                    unresolved.append({'kind': 'missing_local_resource', 'model': identifier, 'path': path})
            rows.append(entry)
    return {'model_rows': rows, 'unresolved_edges': unresolved,
            'whole_output_hash_differences': shared_contract_hashes,
            'registry_entry_checks_must_not_be_replaced_by_historical_whole_file_hashes': True}


def owner_effects(source):
    path = 'behavior_pack/modern_projection/projection/scene.py'
    text = source.read(path).decode('utf8')
    scene = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == 'Scene')
    rows = []
    for node in scene.body:
        if isinstance(node, ast.FunctionDef) and node.name in (
                'own_liquid', 'own_items', 'own_cauldrons', 'own_portals', 'own_books'):
            cleanup = next(n for n in node.body if isinstance(n, ast.FunctionDef) and n.name == 'cleanup')
            rows.append({'function': node.name, 'path': path, 'line': node.lineno,
                'source': ast.get_source_segment(text, node),
                'cleanup_call_order_syntax': [ast.get_source_segment(text, n.value.func)
                    for n in cleanup.body if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)],
                'late_cleanup_has_identity_guard': any(isinstance(n, ast.If) and isinstance(n.test, ast.Compare)
                    and any(isinstance(op, ast.Is) for op in n.test.ops) for n in cleanup.body)})
    assert len(rows) == 5
    return {'effects': rows, 'session_source': 'behavior_pack/modern_projection/projection/session.py',
        'scope': 'Source syntax only. Callback execution order, hook lifecycle, SDK resource registration, runtime input closure and GPU resolution are not established by this map.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    source = GitSource()
    try:
        resources = map_resources(source)
        owners = owner_effects(source)
        source.read(owners['session_source'])
        pins = {path: {'git_blob_sha1': source.tree[path], 'bytes': len(data),
                      'sha256': hashlib.sha256(data).hexdigest()} for path, data in sorted(source.cache.items())}
    finally:
        source.close()
    report = {'schema': 1, 'source_commit': COMMIT, 'at_utc': datetime.now(timezone.utc).isoformat(),
        'resources': resources, 'owner_input_boundary': owners, 'read_source_pins': pins,
        'MC_started': False, 'SDK_imported': False, 'runtime_qualification_created': False,
        'manual_issues_closed': 0,
        'scope': 'Four explicit generation contracts, registered model/material references and five Scene owner effects. Diagnostic and frozen variants are included; presence is not proof of production selection. Engine material parents and shader include search paths remain external and unqualified.'}
    (args.output / 'map.json').write_text(json.dumps(report, sort_keys=True, indent=2) + '\n', encoding='utf8')
    rows = resources['model_rows']
    print(json.dumps({'models': len(rows), 'families': len(CONTRACTS), 'source_files': len(pins),
        'model_entry_mismatches': sum(not r['definition_equal_to_contract'] for r in rows),
        'unresolved_edges': len(resources['unresolved_edges']),
        'whole_output_hash_differences': len(resources['whole_output_hash_differences']),
        'effects': len(owners['effects']), 'MC_started': False}))

if __name__ == '__main__':
    main()
