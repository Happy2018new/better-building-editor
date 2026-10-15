"""Bind reviewed public spawner captures to an exact native marker bundle."""
import argparse
import hashlib
import json
from pathlib import Path
import pprint
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import spawner_marker_data
from projection.spawner_marker import REQUIRED_GATES
from generate_spawner_markers import generated_outputs, identity

GATE = 'behavior_pack/modern_projection/projection/spawner_marker_qualification.py'
SOURCES = tuple('behavior_pack/modern_projection/projection/' + name + '.py' for name in (
    'spawner_presence', 'spawner_marker', 'spawner_marker_data', 'debug_spawner_blueprints',
    'geometry_palette', 'render_context', 'occupancy', 'tiles', 'world_projection',
    'bridge', 'scene', 'session'))
DATA = 'tools/data/spawner_configuration_nemc_3.10.0.420447.json'
CASES = ('mob_spawner_empty', 'mob_spawner_pig_spawn_egg', 'mob_spawner_unknown',
         'trial_spawner_empty', 'trial_spawner_pig_spawn_egg', 'trial_spawner_unknown')


def capture_matrix(production_default):
    required, followups = set(), set()
    for identity in CASES:
        for route in ('editor', 'full', 'missing'):
            label = route + '_' + identity + '_badge'
            required.add(label)
            if not production_default:
                required.add(route + '_' + identity + '_native')
            if route == 'editor':
                required.update(label + '_' + mode for mode in ('hidden', 'restored', 'section', 'full'))
                followups.update(label + '_' + mode + '_later_' + delay
                                 for mode in ('hidden', 'section') for delay in ('0.5', '1.5'))
            elif route == 'missing':
                required.update((label + '_occupied', label + '_restored'))
    return required, followups


def validate_matrix(captures, analysis, production_default):
    required, followups = capture_matrix(production_default)
    actual = set(captures)
    if not required <= actual or actual - required - followups:
        raise ValueError('Spawner acceptance is missing declared cases or contains unknown captures')
    visible = {name for name in required if name.endswith(('_badge', '_restored', '_full'))}
    retained = {name for name in actual if name.endswith(('_hidden', '_section')) or name in followups}
    if (set(analysis['rows']) != visible or set(analysis['retained_support']) != retained or
            not all(row['observed_badge_difference'] for row in analysis['rows'].values()) or
            not all(row['retained_support_observed'] for row in analysis['retained_support'].values())):
        raise ValueError('Spawner pixel analysis omits or fails a required visible/retained frame')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect(report_path, project, destination=None):
    report = json.loads(report_path.read_bytes())
    if (not all(report.get(key) is True for key in ('completed', 'restored', 'source_unchanged'))
            or report['cleanup_errors'] or report['fixture'] != 'test.entities.spawners'):
        raise ValueError('Spawner run failed or was not restored')
    for relative in SOURCES:
        if report['source_sha256'].get(relative) != digest(project / relative):
            raise ValueError('Spawner evidence source differs: ' + relative)
    captures = {}
    for label, receipt in report['captures'].items():
        path = report_path.parent / Path(receipt['path']).name
        if (not receipt['ok'] or not receipt['reliable'] or
                receipt.get('agent_activation_allowed') is not False or
                receipt.get('activation_fallback') is not False or digest(path) != receipt['sha256']):
            raise ValueError('Invalid spawner capture receipt: ' + label)
        captures[label] = receipt['sha256']
        if destination is not None:
            destination.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination / path.name)
            shutil.copyfile(path.with_suffix('.capture.json'), destination / path.with_suffix('.capture.json').name)
    if destination is not None:
        shutil.copyfile(report_path, destination / 'report.json')
    return {'report_sha256': digest(report_path), 'captures': captures,
            'production_default': report['profile']['production_default']}


def set_gate(project, qualification_sha256):
    values = {'SCHEMA_VERSION': 1, 'PRODUCT_QUALIFIED': True,
              'RESOURCE_CONTRACT_SHA256': spawner_marker_data.RESOURCE_CONTRACT_SHA256,
              'QUALIFICATION_SHA256': qualification_sha256,
              'GATES': dict((name, True) for name in sorted(REQUIRED_GATES))}
    content = '"""Exact-version spawner marker deployment backed by reviewed captures."""\n'
    content += ''.join('%s = %s\n' % (name, pprint.pformat(values[name], width=100))
                       for name in ('SCHEMA_VERSION', 'PRODUCT_QUALIFIED',
                                    'RESOURCE_CONTRACT_SHA256', 'QUALIFICATION_SHA256', 'GATES'))
    (project / GATE).write_text(content, encoding='ascii', newline='\n')


def run(args):
    project = args.project.resolve(strict=True)
    if args.output.exists():
        raise ValueError('Choose fresh qualification output')
    if args.admit_candidate and project == ROOT:
        raise ValueError('Isolated admission cannot change repository defaults')
    if not args.accept_reviewed or (not args.admit_candidate and args.default is None):
        raise ValueError('Admission requires reviewed candidate and default-path captures')
    outputs = generated_outputs()
    contract = {}
    registrations = json.loads((project / 'resource_pack/blocks.json').read_bytes())
    for relative, expected in outputs.items():
        actual = json.loads((project / relative).read_bytes())
        if actual != expected:
            raise ValueError('Spawner marker resource changed: ' + relative)
        contract[relative] = identity(actual)
    for marker in spawner_marker_data.MARKERS.values():
        if registrations[marker] != {'netease_model': marker, 'sound': 'stone'}:
            raise ValueError('Spawner marker registration differs')
    if (identity(contract) != spawner_marker_data.RESOURCE_CONTRACT_SHA256 or
            digest(ROOT / DATA) != spawner_marker_data.SOURCE_SHA256):
        raise ValueError('Spawner resource or measured NBT contract differs')
    analysis = json.loads(args.analysis.read_bytes())
    if (analysis['schema'] != 3 or analysis['report_sha256'] != digest(args.candidate)
            or not analysis['all_matched_badges_observed']
            or not analysis['all_retained_support_observed']):
        raise ValueError('Reviewed spawner matrix is incomplete')
    destination = None if args.admit_candidate else args.output / 'candidate'
    candidate = collect(args.candidate, project, destination)
    if candidate['production_default']:
        raise ValueError('Candidate requires six cases, three routes and visibility/occupancy controls')
    validate_matrix(candidate['captures'], analysis, False)
    evidence = {'candidate': candidate, 'analysis_sha256': digest(args.analysis)}
    if args.default is not None:
        default_analysis = json.loads(args.default_analysis.read_bytes())
        if (default_analysis['schema'] != 3 or default_analysis['report_sha256'] != digest(args.default)
                or default_analysis['control_report_sha256'] != digest(args.candidate)
                or not default_analysis['all_matched_badges_observed']
                or not default_analysis['all_retained_support_observed']):
            raise ValueError('Default spawner matrix lacks matched visible controls')
        evidence['default'] = collect(args.default, project, args.output / 'default')
        if not evidence['default']['production_default']:
            raise ValueError('Default run requires six cases, three routes and visibility/occupancy controls')
        validate_matrix(evidence['default']['captures'], default_analysis, True)
        evidence['default_analysis_sha256'] = digest(args.default_analysis)
        shutil.copyfile(args.default_analysis, args.output / 'default/analysis.json')
    manifest = {'schema': 1, 'engine_version': spawner_marker_data.ENGINE_VERSION,
                'fixture': 'test.entities.spawners',
                'stage': 'isolated_candidate' if args.admit_candidate else 'product',
                'resource_contract_sha256': identity(contract),
                'implementation_sha256': {name: digest(project / name) for name in SOURCES},
                'evidence': evidence, 'gates': {name: True for name in sorted(REQUIRED_GATES)},
                'limits': ['Configured presence uses authentic typed NBT, not current spawned entities.',
                           'Markers indicate present, empty or unknown; creature models are excluded.',
                           'An earlier isolated default run had one blank hidden-layer frame; '
                           'it failed retained-support acceptance. A fresh cold start and the '
                           'complete replacement default matrix passed without runtime changes; '
                           'this does not prove a GPU readiness fence.',
                           'Gate metadata is excluded from renderer hashes for isolated default qualification.']}
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / 'qualification.json'
    path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n', encoding='ascii', newline='\n')
    if not args.admit_candidate:
        shutil.copyfile(args.analysis, args.output / 'candidate/analysis.json')
    set_gate(project if args.admit_candidate else ROOT, digest(path))
    print(json.dumps({'stage': manifest['stage'], 'qualification_sha256': digest(path)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--analysis', type=Path, required=True)
    parser.add_argument('--default', type=Path)
    parser.add_argument('--default-analysis', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--accept-reviewed', action='store_true')
    parser.add_argument('--admit-candidate', action='store_true')
    run(parser.parse_args())


if __name__ == '__main__':
    main()
