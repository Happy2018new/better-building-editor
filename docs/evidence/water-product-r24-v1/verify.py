"""Verify this compact review bundle; raw GPU replay needs retained local evidence."""
import argparse
import ast
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path)
    args = parser.parse_args()
    base = Path(__file__).resolve().parent
    manifest = json.loads((base / 'manifest.json').read_bytes())
    for row in manifest['files']:
        path = (base / row['path']).resolve()
        assert path.is_relative_to(base), row['path']
        assert path.stat().st_size == row['bytes'], row['path']
        assert digest(path) == row['sha256'], row['path']
    qualification = json.loads((base / 'qualification.json').read_bytes())
    gate = {}
    for node in ast.parse((base / 'qualification_data.py').read_text('ascii')).body:
        if isinstance(node, ast.Assign):
            assert len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
            gate[node.targets[0].id] = ast.literal_eval(node.value)
    assert qualification['stage'] == gate['QUALIFICATION_STAGE'] == 'product'
    assert gate['PRODUCT_QUALIFIED'] is True
    assert len(gate['GATES']) == 16 and gate['GATES'] == qualification['gates']
    assert all(value is True for value in gate['GATES'].values())
    assert digest(base / 'qualification.json') == gate['QUALIFICATION_SHA256']
    assert len(qualification['implementation_sha256']) == 39
    if args.project is not None:
        project = args.project.resolve(strict=True)
        for relative, expected in qualification['implementation_sha256'].items():
            path = (project / relative).resolve()
            assert path.is_relative_to(project), relative
            assert digest(path) == expected, relative
        for relative, expected in (
            ('tools/data/liquid_product_owner_contract_v1.json', qualification['implementation_contract_sha256']),
            ('tools/data/liquid_product_resource_contract_v1.json', qualification['resource_contract_sha256']),
            ('tools/qualify_water_product_r16.py', qualification['qualifier_sha256']),
            ('behavior_pack/modern_projection/projection/liquid_product_qualification_data.py',
             digest(base / 'qualification_data.py')),
        ):
            assert digest(project / relative) == expected, relative
    print(json.dumps({'bundle_integrity': True, 'stage': 'product', 'gates': 16,
                      'files': len(manifest['files']), 'source_files_checked': 39 if args.project else 0,
                      'raw_pixel_replay_performed': False}))


if __name__ == '__main__':
    main()
