"""Admit custom water only after reproducible, reviewed public-fixture checks.

An isolated admission permits a fresh default-path test. Final admission also
requires that cold-start default report; it never assigns a candidate profile
inside that report. Raw captures and their exact launch archives stay retained.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import pprint
import sys

import numpy as np

from analyze_product_water import analyze, expected_mask, rgb
from analyze_product_water_biome import biome_analysis
from analyze_product_water_flow import analyze_flow
from analyze_water_acceptance_r16 import LIMITS, budget_checks, replay
from generate_liquid_product_owner_contract import SOURCES, generated
from generate_liquid_product_resources import verify_contract

ROOT = Path(__file__).resolve().parents[1]
MODULE = 'behavior_pack/modern_projection/projection/'
RESOURCE = 'tools/data/liquid_product_resource_contract_v1.json'
OWNER = 'tools/data/liquid_product_owner_contract_v1.json'
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.debug_product_water_blueprints import CASES, METADATA, source_document
from projection.liquid_product_deployment import REQUIRED_GATES
from projection.liquid_render_target_data import TARGET_ENGINE_VERSION, TARGET_MINECRAFT_VERSION

ROUTES = frozenset(('editor', 'full', 'missing'))
OWNER_METHODS = frozenset(('LiquidPreview.advance', 'LiquidProjection.advance',
                           'LiquidControls.update', 'WorldLiquidRenderer.advance'))
FLOW_CASES = frozenset(('flow_east', 'flow_south', 'flow_west', 'flow_north', 'falling'))
NEIGHBORS = frozenset(('neighbor_oak_slab', 'neighbor_oak_stairs', 'neighbor_glass_pane',
                       'neighbor_stone', 'transparent_overlap'))
REGISTRATIONS = frozenset(('resource_pack/models/netease_models.json',
                            'resource_pack/materials/entity.material'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_module(project, name):
    spec = importlib.util.spec_from_file_location(name, project / MODULE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n', encoding='ascii', newline='\n')


def source_closure(project, report, contract):
    captured = report['source_file_sha256_before']
    for relative in SOURCES + (MODULE + 'liquid_product_resource_data.py',):
        require(captured.get(relative) == sha(project / relative),
                'Water evidence belongs to a different implementation: ' + relative)
    for relative, expected in contract['output_sha256'].items():
        if relative in REGISTRATIONS:
            require(captured.get(relative) == sha(project / relative),
                    'Captured water model/material registration bundle differs: ' + relative)
        else:
            require(captured.get(relative) == expected and sha(project / relative) == expected,
                    'Water artwork differs from its actual capture: ' + relative)
    launch = json.loads(Path(report['launch_inputs_path']).read_bytes()) if 'launch_inputs_path' in report else None
    if launch is not None:
        require(launch.get('source_sha256') == captured, 'Launch archive differs from the capture')


def collect(path, project, contract):
    report = json.loads(path.read_bytes())
    measured = analyze(path)
    require(measured['evidence_valid'], 'Invalid water capture/cleanup/source binding: ' + str(path))
    require(not report.get('owned_native_assertions') and
            report.get('owned_native_assertion_checks', 0) >= len(report['captures']),
            'Water capture omitted owner-specific native assertion checks')
    source_closure(project, report, contract)
    calibration = report.get('camera_calibration')
    if set(report['routes']) - {'editor'}:
        near = report.get('near_player', {})
        restored = report.get('player_restore', {})
        require(near.get('replicated') and restored.get('restored') is True and
                max(abs(near['replicated'][axis] - near['after'][axis]) for axis in range(3)) < .1 and
                max(abs(restored['foot'][axis] - near['before'][axis]) for axis in range(3)) < .05,
                'World water lacks replicated near-player placement and original-foot restoration')
        require(isinstance(calibration, dict), 'World water lacks camera calibration')
        calibration_path = Path(calibration['path'])
        require(sha(calibration_path) == calibration['sha256'], 'Water camera calibration changed')
        camera = json.loads(calibration_path.read_bytes())
        require(camera.get('runtime_minecraft_version') == TARGET_MINECRAFT_VERSION and
                all(camera.get(field) is True for field in ('passed', 'completed', 'restored')) and
                not camera.get('cleanup_errors') and
                Path(camera['session_file']).resolve() == Path(report['session_binding']['session_file']).resolve(),
                'Water camera calibration did not qualify and restore in this exact version/session')
    for row in report['rows'].values():
        require(row['source']['cells'] == row['ready']['source_cells'],
                'Water owner changed logical source cells')
    return report, measured


def visible_rows(report, cases, routes):
    rows = {}
    for route in routes:
        for case in cases:
            label = route + '_' + case + '_wet'
            require(label in report['rows'] and route + '_' + case + '_dry' in report['captures'],
                    'Missing paired public water case: ' + label)
            wet = rgb(report['captures'][label]['path'])
            dry = rgb(report['captures'][route + '_' + case + '_dry']['path'])
            mask = expected_mask(report['rows'][label], report, (wet.shape[1], wet.shape[0]))
            count = int(np.count_nonzero(mask & (np.max(np.abs(wet - dry), axis=2) >= 8)))
            require(count >= 24, 'No independently visible water: ' + label)
            rows[label] = count
    return rows


def published_positions(state):
    result = set()
    for record in state['liquid_groups']:
        if record['visible'] is not True:
            continue
        group = record['group']
        origin, uniforms = group[2], group[3]
        for value in uniforms[0]:
            code = int(value)
            if not (code // 64) % 64:
                continue
            address = code % 64
            local = address % 4, address // 16, (address // 4) % 4
            result.add(tuple(origin[axis] + local[axis] for axis in range(3)))
    return result


def occupancy(report):
    label = 'missing_pool_wet'
    original = report['rows'][label]['ready']
    occupied = report['extra_rows'].get(label + '_occupied')
    restored = report['extra_rows'].get(label + '_restored')
    require(occupied is not None and restored is not None, 'Missing water occupancy/restore pair')
    require(occupied['occupancy']['rendered_keep'] == 2 and
            restored['occupancy']['rendered_keep'] != 2 and
            occupied['source_cells'] == original['source_cells'] == restored['source_cells'],
            'Occupied water did not preserve and restore its source')
    before, during, after = (published_positions(state) for state in (original, occupied, restored))
    require(before == {(3, 3, 3), (4, 3, 3), (3, 3, 4), (4, 3, 4)} and
            during == before - {(3, 3, 3)} and after == before,
            'Occupied water did not remove exactly one published cell and restore all four')


def default_path(report, measured):
    profile = report.get('profile', {})
    require(report.get('production_default_requested') is True and report.get('frozen') is False and
            profile.get('production_default') is True and
            profile.get('profile_assignment_performed') is False and
            profile.get('engine_version') == TARGET_ENGINE_VERSION and set(report['routes']) == ROUTES,
            'Default acceptance assigned a candidate or omitted a display route')
    visible_rows(report, ('source', 'pool', 'wet_oak_fence'), ROUTES)
    require(measured['observed_product_gates']['animation'], 'Default water lacks visible animation')
    occupancy(report)


def frozen_matrix(paths, reports):
    result = {'visibility': {}, 'side_uv': {}, 'lifecycle': {}, 'budgets': {},
              'maximum_observed_groups': 0, 'reports': [], 'passed': False}
    samples = {}
    for path, report in zip(paths, reports):
        measured = replay(path)
        require(measured['evidence_valid'], 'Invalid completed frozen water report: ' + str(path))
        result['reports'].append({'path': str(path.resolve()), 'sha256': sha(path)})
        for field in ('visibility', 'side_uv', 'lifecycle'):
            require(not set(measured[field]) & set(result[field]), 'Frozen reports duplicate display-route cases')
            result[field].update(measured[field])
        result['maximum_observed_groups'] = max(result['maximum_observed_groups'],
                                               measured['maximum_observed_groups'])
        for method, values in report.get('owner_timing_ms', {}).items():
            samples.setdefault(method, []).extend(values)
    result['budgets'] = budget_checks({'owner_timing_ms': samples})
    result['passed'] = (0 < result['maximum_observed_groups'] <= LIMITS['maximum_groups'] and
        set(result['budgets']) == OWNER_METHODS and
        all(result[field] for field in ('visibility', 'side_uv', 'lifecycle', 'budgets')) and
        all(row['passed'] for field in ('visibility', 'side_uv', 'budgets') for row in result[field].values()) and
        all(result['lifecycle'].values()))
    return result


def frozen_coverage(reports):
    expected = {(route, row['id']) for route in ROUTES for row in CASES}
    observed = set()
    for report in reports:
        require(report.get('frozen') is True, 'Frozen water matrix contains an animated report')
        pairs = {(route, case) for route in report['routes'] for case in report['cases']}
        require(not observed & pairs, 'Frozen reports duplicate display-route cases')
        require(pairs <= expected, 'Frozen water matrix contains unknown cases/routes')
        for route, case in pairs:
            require(all(route + '_' + case + '_' + control in report['rows']
                        for control in ('wet', 'dry')), 'Frozen batch lacks paired public controls')
        observed.update(pairs)
    require(observed == expected, 'Frozen water matrix lacks public cases/routes')
    return observed


def set_gate(project, manifest, provisional):
    resources = load_module(project, 'liquid_product_resource_data')
    rules = load_module(project, 'liquid_product_shape_data')
    owners = load_module(project, 'liquid_product_owner_data')
    values = (
        ('SCHEMA_VERSION', 2), ('PRODUCT_QUALIFIED', True),
        ('QUALIFICATION_SHA256', sha(manifest)),
        ('QUALIFICATION_STAGE', 'isolated_candidate' if provisional else 'product'),
        ('QUALIFICATION_ENGINE_VERSION', TARGET_ENGINE_VERSION),
        ('QUALIFICATION_RESOURCE_CONTRACT_SHA256', resources.PRODUCT_RESOURCE_CONTRACT_SHA256),
        ('QUALIFICATION_RULES_SHA256', rules.PRODUCT_RULES_SHA256),
        ('QUALIFICATION_STYLE_VERSION', rules.PRODUCT_STYLE_VERSION),
        ('QUALIFICATION_IMPLEMENTATION_CONTRACT_SHA256', owners.IMPLEMENTATION_CONTRACT_SHA256),
        ('GATES', dict((name, True) for name in sorted(REQUIRED_GATES))))
    text = '"""Generated by tools/qualify_water_product_r16.py; do not edit."""\n'
    if provisional:
        text += '# Disposable admission for a cold-start default test; never copy this gate into the repository.\n'
    text += ''.join('%s = %s\n' % (name, pprint.pformat(value, width=100, sort_dicts=True))
                    for name, value in values)
    (project / MODULE / 'liquid_product_qualification_data.py').write_text(text, encoding='ascii', newline='\n')


def qualify(args):
    project = args.project.resolve(strict=True)
    require(not args.output.exists(), 'Choose a fresh qualification directory')
    require(args.accept_reviewed, 'Water pixels need explicit reviewed-product acceptance')
    require(not args.admit_candidate or project != ROOT, 'Provisional admission requires a disposable project')
    require(args.admit_candidate or args.default_report is not None, 'Final water qualification needs a cold-start default report')
    contract = json.loads((project / RESOURCE).read_bytes())
    verify_contract(contract, project, ROOT)
    expected_owner, expected_module = generated()
    require((project / OWNER).read_bytes().replace(b'\r\n', b'\n') == expected_owner and
            (project / MODULE / 'liquid_product_owner_data.py').read_bytes().replace(b'\r\n', b'\n') == expected_module,
            'Regenerate the current water owner contract before qualification')
    reports, analyses, provenance = {}, {}, {}
    reports['frozen'], analyses['frozen'], provenance['frozen'] = [], [], []
    for path in args.frozen_report:
        report, measured = collect(path, project, contract)
        reports['frozen'].append(report)
        analyses['frozen'].append(measured)
        provenance['frozen'].append({'path': str(path.resolve()), 'sha256': sha(path),
                                    'source_contract_sha256': report['source_contract_sha256']})
    for name in ('animated', 'biome', 'reverse', 'gallery', 'default'):
        path = getattr(args, name + '_report')
        if path is None:
            continue
        reports[name], analyses[name] = collect(path, project, contract)
        provenance[name] = {'path': str(path.resolve()), 'sha256': sha(path),
                            'source_contract_sha256': reports[name]['source_contract_sha256']}
    frozen_reports = reports['frozen']
    frozen_coverage(frozen_reports)
    acceptance = frozen_matrix(args.frozen_report, frozen_reports)
    require(acceptance['passed'], 'Water side/visibility/budget/lifecycle matrix failed')
    geometry = {label: row for measured in analyses['frozen'] for label, row in measured['geometry'].items()}
    transparency = {label: row for measured in analyses['frozen'] for label, row in measured['transparency'].items()}
    alpha = {label: row for measured in analyses['frozen'] for label, row in measured['alpha_controls'].items()}
    require(bool(geometry) and all(row['passed'] for row in geometry.values()) and
            set(transparency) == {route + '_wet_oak_fence_wet' for route in ROUTES} and
            all(row['passed'] for row in transparency.values()) and len(alpha) == 12 and
            all(row['passed'] for row in alpha.values()),
            'Water geometry or independent alpha controls failed')
    animated = reports['animated']
    require(animated.get('frozen') is False and set(animated['routes']) == ROUTES and
            FLOW_CASES <= set(animated['cases']), 'Animated water omits directions or routes')
    require(analyses['animated']['observed_product_gates']['animation'], 'Water animation lacks visible pixels')
    flow = analyze_flow(args.animated_report)
    require(flow['passed'], 'Physical water flow direction failed')
    biome = biome_analysis(args.biome_report)
    require(biome['passed'] and set(reports['biome']['routes']) == ROUTES, 'Frozen water biome controls failed')
    occupancy(reports['biome'])
    reverse = reports['reverse']
    require(reverse['fixture_view']['reverse_view'] is True and set(reverse['routes']) == ROUTES and
            NEIGHBORS <= set(reverse['cases']), 'Opposite-angle water neighbors/overlap are absent')
    neighbor_pixels = {}
    for report in frozen_reports:
        neighbor_pixels.update(visible_rows(report, NEIGHBORS & set(report['cases']), report['routes']))
    reverse_pixels = visible_rows(reverse, NEIGHBORS, ROUTES)
    frozen_rows = {label: row for report in frozen_reports for label, row in report['rows'].items()}
    for label, row in reverse['rows'].items():
        require(row['source']['cells'] == frozen_rows[label]['source']['cells'] and
                row['ready']['shapes'] == frozen_rows[label]['ready']['shapes'],
                'Opposite-angle control changed the public water geometry')
    gallery = reports['gallery']
    require(set(gallery['routes']) == {'editor'} and set(gallery['cases']) == {'gallery'},
            'Public water gallery was not opened in the editor')
    expected = source_document('gallery')
    require(tuple(gallery['rows']['editor_gallery_wet']['ready']['scene_size']) == METADATA[3] and
            len(gallery['rows']['editor_gallery_wet']['source']['cells']) == len(expected.blocks),
            'Public water gallery was cropped logically or omitted cells')
    gallery_pixels = visible_rows(gallery, ('gallery',), ('editor',))
    if 'default' in reports:
        default_path(reports['default'], analyses['default'])
    manifest = {'schema_version': 2, 'stage': 'isolated_candidate' if args.admit_candidate else 'product',
        'engine_version': TARGET_ENGINE_VERSION, 'minecraft_version': TARGET_MINECRAFT_VERSION,
        'fixture': METADATA[0], 'native_parity_claimed': False,
        'resource_contract_sha256': sha(project / RESOURCE),
        'implementation_contract_sha256': sha(project / OWNER),
        'implementation_sha256': {name: sha(project / name) for name in SOURCES},
        'evidence': provenance, 'gates': {name: name != 'default_path' or 'default' in reports
                                        for name in sorted(REQUIRED_GATES)},
        'neighbor_pixels': neighbor_pixels, 'reverse_pixels': reverse_pixels,
        'gallery_pixels': gallery_pixels,
        'limits': ['Declared Java-style water geometry and biome presets; exact native parity is not claimed.',
                   'CPU owner timings exclude host IPC/capture but include game-thread scheduling pauses.',
                   'Measured model budget is the observed public fixtures, not the configured capacity of 256.',
                   'Candidate admission is disposable and must be followed by a cold-start default test.']}
    args.output.mkdir(parents=True)
    for name, measured in dict(analyses, acceptance=acceptance, flow=flow, biome_pixels=biome).items():
        write_json(args.output / (name + '-analysis.json'), measured)
    write_json(args.output / 'qualification.json', manifest)
    set_gate(project if args.admit_candidate else ROOT, args.output / 'qualification.json', args.admit_candidate)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--frozen-report', type=Path, required=True, action='append',
                        help='Completed route-specific reports covering the full three-route public matrix')
    for name in ('animated', 'biome', 'reverse', 'gallery'):
        parser.add_argument('--' + name + '-report', type=Path, required=True)
    parser.add_argument('--default-report', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--admit-candidate', action='store_true')
    parser.add_argument('--accept-reviewed', action='store_true')
    manifest = qualify(parser.parse_args())
    print(json.dumps({'stage': manifest['stage'], 'gates': manifest['gates']}))


if __name__ == '__main__':
    main()
