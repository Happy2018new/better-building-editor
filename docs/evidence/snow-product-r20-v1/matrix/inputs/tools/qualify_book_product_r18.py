"""Combine unchanged native book artwork evidence with the independent owner.

An audit never enables a product gate. A reviewed disposable admission permits
the missing cold-start default-path run; final admission requires that run and
binds its provisional manifest. Geometry evidence is reused only byte for byte.
"""
import argparse
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import pprint

from analyze_book_surface_r17 import analyze as surface_analysis, ENGINE_VERSION
from analyze_lectern_book_r17 import analyze as page_analysis
from analyze_book_body_boundary_r19 import analyze as body_analysis
from analyze_book_motion_r20 import analyze as motion_analysis
from probe_book_native_r16 import book_sources, BODY_SOURCES, OWNER_SOURCES

ROOT = Path(__file__).resolve().parents[1]
MODULE = 'behavior_pack/modern_projection/projection/'
RESOURCE_KEYS = ('contract_present', 'contract_sha256', 'files', 'models', 'materials')
REQUIRED_GATES = ('owner_matrix', 'raster_regression', 'lectern_page_surface',
                  'body_boundary_pixels', 'dense_cover_motion', 'source_closure', 'default_path')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2)+'\n', encoding='ascii', newline='\n')


def load(path):
    report = json.loads(path.read_bytes())
    require(report.get('engine') == ENGINE_VERSION, 'Book evidence engine differs: '+str(path))
    require(all(report.get(key) is True for key in ('completed', 'restored', 'source_unchanged')) and
            report.get('cleanup_errors') == [], 'Book evidence did not complete and restore: '+str(path))
    require(report.get('model_prefix') == '', 'Book evidence uses diagnostic aliases: '+str(path))
    return report


def resource_binding(reports, current):
    """The old raster/page owner may differ; its complete render assets may not."""
    errors = []
    for label, report in reports.items():
        installed = report.get('installed_sources', {})
        for key in RESOURCE_KEYS:
            if not current.get(key) or installed.get(key) != current[key]:
                errors.append(label+': resource snapshot differs: '+key)
    return errors


def source_binding(report, current):
    installed = report.get('installed_sources', {})
    errors = []
    recorded = installed.get('owner_files', {})
    if set(recorded) != set(OWNER_SOURCES):
        errors.append('Independent book evidence omits its complete owner source closure')
    if (set(installed.get('body_files', {})) != set(BODY_SOURCES) or
            set(current.get('body_files', {})) != set(BODY_SOURCES)):
        errors.append('Book body evidence omits its independent context source closure')
    for category in ('owner_files', 'body_files'):
        if not installed.get(category) or set(installed[category]) != set(current.get(category, {})):
            errors.append('Book source set differs: '+category)
        for relative, expected in installed.get(category, {}).items():
            if current.get(category, {}).get(relative) != expected:
                errors.append('Book implementation changed: '+relative)
    for key in ('resource_pack/blocks.json', 'resource_pack/textures/terrain_texture.json'):
        if key not in installed or installed[key] != current.get(key):
            errors.append('Book body registration changed: '+key)
    return errors


def body_binding(path, current, owner, output, default=False):
    if path is None:
        return False, ['Native bottom and four-side body pixel evidence is missing']
    report = json.loads(path.read_bytes())
    errors = source_binding(report, current)+resource_binding({'body': report}, current)
    if report.get('installed_sources', {}).get('body_files') != owner['installed_sources'].get('body_files'):
        errors.append('Body pixel evidence belongs to another table implementation')
    if default and (report.get('production_default_requested') is not True or
                    report.get('profile_assignment_performed') is not False):
        errors.append('Default body pixels were captured through a candidate assignment')
    measured = body_analysis(path, output)
    return measured['body_boundary_pixels_passed'] is True and not errors, errors


def motion_binding(path, current, output):
    if path is None:
        return False, ['Dense fixed-camera book motion evidence is missing']
    report = json.loads(path.read_bytes())
    wrapped = {'installed_sources': report.get('source_before', {})}
    errors = source_binding(wrapped, current)+resource_binding({'motion': wrapped}, current)
    if report.get('alias_sources'):
        errors.append('Dense book motion uses diagnostic aliases')
    with redirect_stdout(io.StringIO()):
        measured = motion_analysis(path, output)
    return measured['dense_cover_motion_passed'] is True and not errors, errors


def default_binding(report, measured, admission, owner):
    profile = report.get('default_profile', {})
    require(report.get('stage') == 'production_default' and
            report.get('production_default_requested') is True and
            report.get('profile_assignment_performed') is False and
            profile.get('qualified') is True and profile.get('stage') == 'isolated_default_test' and
            profile.get('qualification_sha256') == sha(admission),
            'Default book report assigned a candidate or used an unbound admission')
    temporary = json.loads(admission.read_bytes())
    require(temporary.get('engine_version') == ENGINE_VERSION and
            temporary.get('stage') == 'isolated_default_test' and
            temporary.get('reviewed') is True and
            temporary.get('implementation_sha256') == owner['installed_sources']['owner_files'] and
            temporary.get('resource_snapshot') ==
                {key: owner['installed_sources'][key] for key in RESOURCE_KEYS} and
            all(temporary.get('gates', {}).get(name) is True
                for name in REQUIRED_GATES if name != 'default_path'),
            'Default book admission belongs to another implementation or incomplete matrix')
    return (measured['owner_matrix_passed'] is True and
            measured['owner_matrix']['occupancy_included'] is True)


def gate_text(manifest_path, manifest):
    values = {'SCHEMA_VERSION': 1, 'PRODUCT_QUALIFIED': True,
              'QUALIFICATION_SHA256': sha(manifest_path), 'QUALIFICATION_STAGE': manifest['stage'],
              'QUALIFICATION_ENGINE_VERSION': ENGINE_VERSION,
              'QUALIFICATION_RESOURCE_CONTRACT_SHA256': manifest['resource_contract_sha256'],
              'GATES': manifest['gates']}
    return ('"""Generated by tools/qualify_book_product_r18.py from reviewed evidence."""\n'+
            ''.join('%s = %s\n' % (name, pprint.pformat(value, width=100, sort_dicts=True))
                    for name, value in values.items()))


def body_admission_binding(path, current):
    admitted = json.loads(path.read_bytes())
    require(admitted.get('engine_version') == ENGINE_VERSION and admitted.get('stage') == 'product'
            and admitted.get('reviewed') is True and admitted.get('product_qualified') is True
            and admitted.get('qualified_sources') == current
            and admitted.get('gates') == dict(body_boundary_pixels=True, source_closure=True, default_path=True),
            'Independent table body admission differs from the installed implementation')


def qualify(args):
    project = args.project.resolve(strict=True)
    require(not args.output.exists(), 'Keep book qualification output immutable; choose a fresh directory')
    require(not args.admit_default_test or project != ROOT,
            'Disposable default-test admission may not enable the repository')
    require(not args.write_gate or args.accept_reviewed, 'Writing a book gate requires reviewed pixel acceptance')
    reports = {'owner': load(args.owner_report), 'surface': load(args.surface_reference),
               'lectern': load(args.lectern_reference)}
    require(reports['owner'].get('owner_path') == 'independent_book', 'Book owner evidence borrows another owner')
    current = book_sources(project)
    errors = resource_binding(reports, current)+source_binding(reports['owner'], current)
    body_admission = getattr(args, 'body_admission', None)
    if args.default_report is not None and args.write_gate:
        require(body_admission is not None, 'Final book admission needs the independent table body admission')
    if body_admission is not None:
        body_admission_binding(body_admission, current)
    args.output.mkdir(parents=True)
    body, body_errors = body_binding(getattr(args, 'body_report', None), current,
                                     reports['owner'], args.output/'body-analysis.json')
    errors += body_errors
    motion, motion_errors = motion_binding(getattr(args, 'motion_report', None), current,
                                           args.output/'motion-analysis.json')
    errors += motion_errors
    with redirect_stdout(io.StringIO()):
        owners = surface_analysis(args.owner_report, args.output/'owner-analysis.json')
        raster = surface_analysis(args.surface_reference, args.output/'surface-analysis.json')
        pages = page_analysis(args.lectern_reference, args.output/'lectern-analysis.json')
    default = False
    if args.default_report is not None:
        require(args.default_admission is not None, 'Default evidence needs its disposable admission manifest')
        reports['default'] = load(args.default_report)
        errors += resource_binding({'default': reports['default']}, current)
        errors += source_binding(reports['default'], current)
        with redirect_stdout(io.StringIO()):
            measured = surface_analysis(args.default_report, args.output/'default-analysis.json')
        default = default_binding(reports['default'], measured, args.default_admission, reports['owner'])
        default_body, default_body_errors = body_binding(getattr(args, 'default_body_report', None),
            current, reports['default'], args.output/'default-body-analysis.json', default=True)
        errors += default_body_errors
        default = default and default_body
    gates = {'owner_matrix': (owners['owner_matrix_passed'] is True and
                              owners['owner_matrix']['occupancy_included'] is True),
             'raster_regression': raster['raster_regression_passed'] is True,
             'lectern_page_surface': pages['page_surface_parity_passed'] is True,
             'body_boundary_pixels': body,
             'dense_cover_motion': motion,
             'source_closure': not errors, 'default_path': default}
    stage = 'isolated_default_test' if args.admit_default_test else ('product' if default else 'audit')
    manifest = {'schema_version': 1, 'engine_version': ENGINE_VERSION, 'stage': stage,
        'product_qualified': bool(args.write_gate and stage == 'product'),
        'reviewed': bool(args.accept_reviewed), 'gates': gates, 'errors': errors,
        'resource_contract_sha256': current['contract_sha256'],
        'resource_snapshot': {key: current[key] for key in RESOURCE_KEYS},
        'implementation_sha256': reports['owner']['installed_sources'].get('owner_files', {}),
        'body_sha256': reports['owner']['installed_sources'].get('body_files', {}),
        'owned_registries': [
            {'path': 'resource_pack/blocks.json', 'section': None,
             'entries': {'modern_projection:preview_enchanting_body': current['resource_pack/blocks.json']}},
            {'path': 'resource_pack/textures/terrain_texture.json', 'section': 'texture_data',
             'entries': {'modern_projection_enchanting_body': current['resource_pack/textures/terrain_texture.json']}}],
        'evidence': {name: {'path': str(getattr(args, name+'_report' if name in ('owner', 'default') else
                        ('surface_reference' if name == 'surface' else 'lectern_reference')).resolve()),
                        'sha256': sha(getattr(args, name+'_report' if name in ('owner', 'default') else
                        ('surface_reference' if name == 'surface' else 'lectern_reference')))} for name in reports},
        'analyzer_sha256': {name: sha(ROOT/'tools'/name) for name in
            ('analyze_book_surface_r17.py', 'analyze_lectern_book_r17.py',
             'analyze_book_body_boundary_r19.py', 'analyze_book_motion_r20.py', 'qualify_book_product_r18.py')},
        'limits': ['Project hinged book geometry using native artwork; no player-proximity reaction, page text or interaction.',
                   'Lectern page parity is the matched stationary reference view; other directions share the same rigid geometry.',
                   'The independent owner matrix and native close-up resource evidence are separately bound.']}
    for name in ('body_report', 'default_body_report', 'motion_report', 'body_admission'):
        evidence = getattr(args, name, None)
        if evidence is not None:
            manifest['evidence'][name] = {'path': str(evidence.resolve()), 'sha256': sha(evidence)}
    path = args.output/'qualification.json'
    write_json(path, manifest)
    if args.write_gate:
        required = [name for name in REQUIRED_GATES if not args.admit_default_test or name != 'default_path']
        require(all(gates[name] is True for name in required),
                'Book qualification is incomplete: '+', '.join(name for name in required if not gates[name]))
        require(stage != 'audit', 'Final book gate requires a cold-start default report')
        (project/MODULE/'book_qualification_data.py').write_text(gate_text(path, manifest), encoding='ascii', newline='\n')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=ROOT)
    parser.add_argument('--owner-report', type=Path, required=True)
    parser.add_argument('--surface-reference', type=Path, required=True)
    parser.add_argument('--lectern-reference', type=Path, required=True)
    parser.add_argument('--default-report', type=Path)
    parser.add_argument('--default-admission', type=Path)
    parser.add_argument('--body-report', type=Path)
    parser.add_argument('--body-admission', type=Path)
    parser.add_argument('--motion-report', type=Path)
    parser.add_argument('--default-body-report', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--admit-default-test', action='store_true')
    parser.add_argument('--accept-reviewed', action='store_true')
    parser.add_argument('--write-gate', action='store_true')
    manifest = qualify(parser.parse_args())
    print(json.dumps({'stage': manifest['stage'], 'gates': manifest['gates'], 'errors': manifest['errors']}))


if __name__ == '__main__':
    main()
