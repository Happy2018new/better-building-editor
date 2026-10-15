"""Preserve a compact, explicitly unqualified checkpoint from completed water runs."""
import argparse
import hashlib
import json
from pathlib import Path

from qualify_water_product_r16 import frozen_coverage

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'docs/evidence/water-product-r16-v1'
RUNS = (
    ('editor-core-v9', 'editor-core-product-analysis-v9', 'editor-core-acceptance-v9'),
    ('editor-neighbors-v9', 'editor-neighbors-product-analysis-v9', 'editor-neighbors-acceptance-v9'),
    ('full-core-v14', 'full-core-product-analysis-v14', 'full-core-acceptance-v14'),
    ('full-neighbors-v15', 'full-neighbors-product-analysis-v15', 'full-neighbors-acceptance-v15'),
    ('missing-all-v17', 'missing-all-product-analysis-v17', 'missing-all-acceptance-v17'),
)


def read(name):
    path = EVIDENCE / (name + '.json')
    return json.loads(path.read_bytes()), {'path': path.name,
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh checkpoint')
    reports, result, methods, alpha, visibility, lifecycle = [], [], {}, {}, {}, {}
    for raw_name, product_name, acceptance_name in RUNS:
        raw, raw_receipt = read(raw_name)
        product, product_receipt = read(product_name)
        acceptance, acceptance_receipt = read(acceptance_name)
        if not (raw.get('completed') and raw.get('restored') and raw.get('source_unchanged')
                and product.get('evidence_valid') and acceptance.get('evidence_valid')):
            raise ValueError('Only completed, restored and source-bound evidence: ' + raw_name)
        reports.append(raw)
        alpha.update(product['alpha_controls'])
        visibility.update(acceptance['visibility'])
        lifecycle.update(acceptance['lifecycle'])
        for method, values in raw['owner_timing_ms'].items():
            if values:
                methods.setdefault(method, []).append(max(values))
        result.append({'report': raw_receipt, 'product_analysis': product_receipt,
            'acceptance_analysis': acceptance_receipt, 'elapsed_seconds': raw['elapsed_seconds'],
            'captures': len(raw['captures']), 'rows': len(raw['rows']),
            'geometry_passed': product['observed_product_gates']['geometry'],
            'body_alpha': {key: value['passed'] for key, value in product['alpha_controls'].items()},
            'visibility_passed': all(row['passed'] for row in acceptance['visibility'].values()),
            'side_uv': acceptance['side_uv'], 'budgets': acceptance['budgets']})
    owner = json.loads((ROOT / 'tools/data/liquid_product_owner_contract_v1.json').read_bytes())
    runtime = [{name: report['source_file_sha256_before'][name] for name in owner['source_sha256']}
               for report in reports]
    coverage = frozen_coverage(reports)
    payload = {'schema': 1, 'round': 16, 'product_qualified': False,
        'scope': 'Completed public frozen near-field controls; this is not a product admission.',
        'case_route_coverage': len(coverage), 'public_cases': 19, 'routes': ['editor', 'full', 'missing'],
        'runtime_owner_sources': len(runtime[0]), 'runtime_owner_sources_identical': all(row == runtime[0] for row in runtime),
        'geometry_all_passed': all(row['geometry_passed'] for row in result),
        'alpha_control_count': len(alpha), 'alpha_all_passed': all(row['passed'] for row in alpha.values()),
        'independent_section_control_count': len(visibility),
        'independent_section_all_passed': all(row['passed'] for row in visibility.values()),
        'world_lifecycle_sample_count': len(lifecycle), 'world_lifecycle_all_passed': all(lifecycle.values()),
        'maximum_owner_ms': {method: max(values) for method, values in methods.items()}, 'runs': result,
        'open': ['world_side_uv_failed', 'cold_world_advance_over_100ms',
                 'free_model_native_entity_distance_or_world_context_mismatch',
                 'animated_physical_flow_three_routes', 'frozen_biome_three_routes',
                 'missing_pool_exact_occupancy_transitions', 'opposite_angle_neighbors_and_overlap',
                 'complete_public_gallery', 'cold_start_ordinary_default_entry']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + '\n', encoding='ascii')
    print(json.dumps({key: payload[key] for key in ('case_route_coverage', 'alpha_control_count',
        'independent_section_control_count', 'world_lifecycle_sample_count', 'product_qualified')}))


if __name__ == '__main__':
    main()
