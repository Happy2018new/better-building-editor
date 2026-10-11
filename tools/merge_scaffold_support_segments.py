"""Plan remaining scaffold ranges or merge complete, restored native segments.

Planning never produces capability evidence. A catalogue is emitted only when
the segments cover the current dump exactly, without overlaps or failed runs.
"""
import argparse
import hashlib
import json
from pathlib import Path

from verify_debug_blueprints import write_json
from verify_scaffolding_native import ROOT, registry
from verify_scaffold_support_catalogue import METHOD, SEGMENT_METHOD, MAX_SEGMENT_STATES


def dump_states():
    return [(name, aux) for name in sorted(registry.BLOCKS) for aux in registry.aux_values(name)]


def validate_segment(report, manifest, expected):
    native = report.get('native', {})
    if (report.get('schema') != 1 or report.get('method') != SEGMENT_METHOD or
            report.get('game_version') != manifest['game_version'] or
            report.get('palette_sha256', '').lower() != manifest['source_sha256'].lower() or
            report.get('completed') is not True or report.get('restored') is not True or
            native.get('done') is not True or report.get('error') or report.get('cleanup_error')):
        raise ValueError('Incomplete, unrestored or mismatching scaffold segment')
    bounds = native.get('range', [])
    if (len(bounds) != 2 or any(type(value) is not int for value in bounds) or
            not 0 <= bounds[0] < bounds[1] <= len(expected) or
            bounds[1] - bounds[0] > MAX_SEGMENT_STATES or
            native.get('index') != bounds[1] or native.get('states') != len(expected)):
        raise ValueError('Invalid scaffold segment range or progress')
    rows = native.get('rows', [])
    requested = [tuple(row.get('requested', ())) for row in rows]
    if requested != expected[bounds[0]:bounds[1]]:
        raise ValueError('Scaffold segment does not match its dump range exactly')
    fingerprint = report.get('source_sha256', '')
    if len(fingerprint) != 64 or any(char not in '0123456789abcdef' for char in fingerprint):
        raise ValueError('Missing scaffold probe source fingerprint')
    return bounds, rows


def collect_segments(reports, manifest, expected):
    collected = [None] * len(expected)
    fingerprints = set()
    for report in reports:
        bounds, rows = validate_segment(report, manifest, expected)
        fingerprints.add(report['source_sha256'])
        for index, row in enumerate(rows, bounds[0]):
            if collected[index] is not None:
                raise ValueError('Overlapping scaffold segments at dump index %s' % index)
            collected[index] = row
    if len(fingerprints) > 1:
        raise ValueError('Scaffold segments used different probe sources')
    return collected


def missing_ranges(collected, size=MAX_SEGMENT_STATES):
    if not 0 < size <= MAX_SEGMENT_STATES:
        raise ValueError('Invalid scaffold segment size')
    ranges, index = [], 0
    while index < len(collected):
        if collected[index] is not None:
            index += 1
            continue
        start = index
        while index < len(collected) and collected[index] is None and index - start < size:
            index += 1
        ranges.append({'start_index': start, 'count': index - start})
    return ranges


def merge_segments(reports, manifest, expected):
    rows = collect_segments(reports, manifest, expected)
    missing = missing_ranges(rows)
    if missing:
        raise ValueError('Incomplete scaffold catalogue; first missing range: %r' % missing[0])
    return {'schema': 1, 'method': METHOD, 'completed': True, 'restored': True,
            'game_version': manifest['game_version'], 'palette_sha256': manifest['source_sha256'].lower(),
            'source_sha256': reports[0]['source_sha256'],
            'collection': 'Complete union of independently restored bounded-range-v1 observations',
            'limits': ['SDK placement, not item use.', 'No pixel or editor falling acceptance.',
                       'Changed support states remain unknown.'],
            'native': {'done': True, 'states': len(expected), 'index': len(expected), 'rows': rows}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('segments', type=Path, nargs='*')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--plan', action='store_true', help='List missing ranges; emit no capability evidence')
    args = parser.parse_args()
    if not args.plan and (not args.segments or args.output is None):
        parser.error('Merging requires segment files and --output')
    manifest = json.loads((ROOT / 'tools/data/block_registry_manifest.json').read_text(encoding='utf8'))
    if (registry.SOURCE_VERSION, registry.SOURCE_SHA256.lower()) != (
            manifest['game_version'], manifest['source_sha256'].lower()):
        raise ValueError('Local registry and dump manifest differ')
    expected = dump_states()
    reports = [json.loads(path.read_text(encoding='utf8')) for path in args.segments]
    if args.plan:
        rows = collect_segments(reports, manifest, expected)
        output = {'schema': 1, 'planned_only': True, 'states': len(expected),
                  'observed_states': sum(row is not None for row in rows),
                  'ranges': missing_ranges(rows)}
    else:
        output = merge_segments(reports, manifest, expected)
        output['segments'] = [{'path': str(path.resolve()),
                               'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                               'range': report['native']['range']}
                              for path, report in zip(args.segments, reports)]
    if args.output:
        if args.output.resolve() in [path.resolve() for path in args.segments]:
            parser.error('Output must not overwrite an original segment')
        write_json(args.output, output)
    print(json.dumps(output if args.plan else {'completed': True, 'states': len(expected)}, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
