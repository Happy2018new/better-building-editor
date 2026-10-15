"""Admit the independent table body after reviewed native boundary evidence."""
import argparse
import ast
import hashlib
import json
from pathlib import Path

from analyze_book_body_boundary_r19 import analyze
from probe_book_native_r16 import book_sources
from qualify_book_product_r18 import (ENGINE_VERSION, resource_binding, source_binding,
                                      require, sha, write_json)

ROOT = Path(__file__).resolve().parents[1]
DATA = 'behavior_pack/modern_projection/projection/static_table_data.py'


def qualified_data(content):
    """Change only the generated metadata's parsed qualification literal."""
    tree = ast.parse(content)
    nodes = [node.value for node in tree.body if isinstance(node, ast.Assign)
             and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
             and node.targets[0].id == 'PRODUCT_QUALIFIED']
    require(len(nodes) == 1 and isinstance(nodes[0], ast.Constant)
            and type(nodes[0].value) is bool, 'Table metadata needs one literal qualification flag')
    node = nodes[0]
    lines = content.splitlines(keepends=True)
    start = sum(map(len, lines[:node.lineno-1])) + node.col_offset
    end = sum(map(len, lines[:node.end_lineno-1])) + node.end_col_offset
    return content[:start] + b'True' + content[end:]


def check_report(path, current, output, default=False):
    report = json.loads(path.read_bytes())
    require(report.get('engine') == ENGINE_VERSION and report.get('model_prefix', '') == '',
            'Table evidence needs the final models and exact engine')
    errors = source_binding(report, current) + resource_binding({'body': report}, current)
    require(not errors, '; '.join(errors))
    if default:
        require(report.get('production_default_requested') is True and
                report.get('profile_assignment_performed') is False and
                report.get('default_profile', {}).get('body_candidate_override') is False,
                'Default table evidence assigned a candidate')
    measured = analyze(path, output)
    require(measured['body_boundary_pixels_passed'] is True, 'Table boundary pixels failed')
    return report


def qualify(args):
    project = args.project.resolve(strict=True)
    require(not args.output.exists(), 'Choose a fresh immutable table admission directory')
    require(not args.admit_default_test or project != ROOT,
            'Temporary table admission may only enable a disposable project')
    require(not args.write_gate or args.accept_reviewed, 'Writing requires reviewed native pixels')
    require(args.admit_default_test or args.default_report is not None,
            'Final table admission needs the cold-start default report')
    current = book_sources(project)
    content = (project/DATA).read_bytes()
    planned = qualified_data(content)
    future = dict(current, body_files=dict(current['body_files']))
    future['body_files'][DATA] = hashlib.sha256(planned).hexdigest()
    args.output.mkdir(parents=True)
    check_report(args.body_report, current, args.output/'candidate-analysis.json')
    if args.default_report is not None:
        check_report(args.default_report, future, args.output/'default-analysis.json', default=True)
        require(args.default_admission is not None, 'Final table admission needs its temporary manifest')
        temporary = json.loads(args.default_admission.read_bytes())
        require(temporary.get('stage') == 'isolated_default_test' and temporary.get('reviewed') is True
                and temporary.get('engine_version') == ENGINE_VERSION
                and temporary.get('qualified_sources') == future,
                'Temporary table admission belongs to different installed sources')
    manifest = {'schema_version': 1, 'engine_version': ENGINE_VERSION,
        'stage': 'isolated_default_test' if args.admit_default_test else 'product',
        'reviewed': bool(args.accept_reviewed),
        'product_qualified': bool(args.write_gate and not args.admit_default_test),
        'source_before': current, 'qualified_sources': future,
        'gates': {'body_boundary_pixels': True, 'source_closure': True,
                  'default_path': args.default_report is not None},
        'evidence': {'candidate': {'path': str(args.body_report.resolve()), 'sha256': sha(args.body_report)}},
        'tool_sha256': sha(Path(__file__)),
        'analyzer_sha256': sha(ROOT/'tools/analyze_book_body_boundary_r19.py'),
        'scope': 'Independent native-textured table body and target-only occupancy; no book qualification.'}
    for name in ('default_report', 'default_admission'):
        path = getattr(args, name)
        if path is not None:
            manifest['evidence'][name] = {'path': str(path.resolve()), 'sha256': sha(path)}
    write_json(args.output/'qualification.json', manifest)
    if args.write_gate:
        (project/DATA).write_bytes(planned)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=ROOT)
    parser.add_argument('--body-report', type=Path, required=True)
    parser.add_argument('--default-report', type=Path)
    parser.add_argument('--default-admission', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--admit-default-test', action='store_true')
    parser.add_argument('--accept-reviewed', action='store_true')
    parser.add_argument('--write-gate', action='store_true')
    result = qualify(parser.parse_args())
    print(json.dumps({'stage': result['stage'], 'gates': result['gates']}))


if __name__ == '__main__':
    main()
