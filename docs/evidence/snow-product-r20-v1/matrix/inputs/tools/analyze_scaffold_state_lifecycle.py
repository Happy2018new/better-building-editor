"""Summarize native lifecycle timing without inferring scaffold capabilities."""
import argparse
import hashlib
import json
from pathlib import Path

import probe_scaffold_state_lifecycle as probe


def _same_cell(left, right):
    return (left['front'] == right['front']
            and probe.state_key(left['states']) == probe.state_key(right['states'])
            and left['liquid'] == right['liquid'])


def analyze(report):
    """Require complete true-state observations; keep changed supports unknown."""
    validation = probe.validate_report(report)
    rows = []
    methods = {}
    for row in report['native']['rows']:
        supports = [probe.cell_at(sample, (0, 0, 0)) for sample in row['samples']]
        upper = [probe.cell_at(sample, (0, 1, 0)) for sample in row['samples']]
        actual_support = [{'front': cell['front'], 'states': cell['states'], 'liquid': cell['liquid']}
                          for cell in supports]
        actual_upper = [{'front': cell['front'], 'states': cell['states'], 'liquid': cell['liquid']}
                        for cell in upper]
        desired = {'name': row['requested'][0], 'aux': row['requested'][1]}
        exact = [cell['front'] == desired
                 and probe.state_key(cell['states']) == probe.state_key(row['expected_states'])
                 for cell in supports]
        before = row['writes'][2]['before']
        if not _same_cell(before, upper[0]):
            raise ValueError('Native upper cell changed between immediate sample and scaffold write')
        observed = {'id': row['id'], 'method': row['method'], 'requested': row['requested'],
                    'native_aux': row['native_aux'],
                    'native_aux_equals_dump': row['native_aux'] == row['requested'][1],
                    'support_exact': dict(zip(probe.PHASES, exact)),
                    'changed_before_scaffold': not exact[0],
                    'scaffold_write_changed_support': not _same_cell(supports[0], supports[1]),
                    'delayed_changed_support': not _same_cell(supports[1], supports[2]),
                    'upper_exists_before_scaffold': upper[0]['front']['name'] != 'minecraft:air',
                    'upper_before_scaffold': before,
                    'support_by_phase': dict(zip(probe.PHASES, actual_support)),
                    'upper_by_phase': dict(zip(probe.PHASES, actual_upper)),
                    'semantic_set_returned': row['semantic_set_returned'],
                    'capability': 'unknown_not_classified_by_lifecycle_diagnostic'}
        rows.append(observed)
        methods[row['id']] = observed
    pairs = []
    for control, unused_name, unused_aux in probe.CONTROLS:
        direct = methods[control + '_' + probe.DIRECT]
        semantic = methods[control + '_' + probe.SEMANTIC]
        differ = {phase: not _same_cell(direct['support_by_phase'][phase],
                                       semantic['support_by_phase'][phase]) for phase in probe.PHASES}
        pairs.append({'control': control, 'direct_and_semantic_differ': differ})
    return {'schema': 1, 'kind': 'scaffold_state_lifecycle_timing_analysis',
            'source_method': report['method'], 'probe_source_sha256': report['source_sha256'],
            'runtime': report['start']['runtime'], 'game_version': report['start']['game_version'],
            'palette_sha256': report['start']['palette_sha256'],
            'positive_control_matched': validation['positive_control_matched'],
            'actor_data': probe.ACTOR_SCOPE, 'scope': '17 SDK lifecycle controls; no support or visual acceptance',
            'acceptance': {'editor': 'pending', 'full': 'pending', 'missing': 'pending'},
            'counts': {key: sum(row[key] for row in rows) for key in
                       ('changed_before_scaffold', 'scaffold_write_changed_support',
                        'delayed_changed_support', 'upper_exists_before_scaffold')},
            'rows': rows, 'direct_semantic_pairs': pairs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    raw = args.input.read_bytes()
    result = analyze(json.loads(raw))
    result['input_sha256'] = hashlib.sha256(raw).hexdigest()
    result['analysis_source_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'counts': result['counts'], 'positive_control_matched': result['positive_control_matched'],
                      'acceptance': result['acceptance']}))


if __name__ == '__main__':
    main()
