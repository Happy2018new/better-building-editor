"""Generate versioned scaffold supports; unobserved states remain unknown."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry as registry
from generate_entity_blueprints import snapshot_fingerprint
from verify_scaffold_support_catalogue import METHOD as CATALOGUE_METHOD

SAMPLE_METHOD = 'Native legacy-state writes with neighbor updates; delayed readback'


def _sample_rows(report):
    native = report['native']
    rows = native.get('rows', [])
    if len(rows) != native.get('cases'):
        raise ValueError('Incomplete scaffold support sample observations')
    result = []
    for row in rows:
        metadata = row.get('metadata', {})
        if metadata.get('family') != 'support' or row.get('action') != 'place_scaffold':
            raise ValueError('Expected isolated scaffold support sample observations')
        cells = {tuple(cell['pos']): cell for cell in row.get('cells', [])}
        support = cells.get((0, 1, 0), {})
        scaffold = cells.get((0, 2, 0), {})
        result.append({'requested': metadata['support'], 'support': support.get('value'),
                       'scaffold': scaffold.get('value'), 'states': scaffold.get('states')})
    return result


def capabilities(report, manifest):
    method = report.get('method')
    if (report.get('schema') != 1 or method not in (CATALOGUE_METHOD, SAMPLE_METHOD) or
            report.get('game_version') != manifest['game_version'] or
            report.get('palette_sha256', '').lower() != manifest['source_sha256'].lower() or
            not report.get('completed') or not report.get('restored') or not report.get('native', {}).get('done')):
        raise ValueError('Incomplete or mismatching native scaffold support observations')
    expected = {(name, aux) for name in registry.BLOCKS for aux in registry.aux_values(name)}
    rows = report['native'].get('rows', []) if method == CATALOGUE_METHOD else _sample_rows(report)
    observed = [tuple(row['requested']) for row in rows]
    if not observed or len(set(observed)) != len(observed) or not set(observed) <= expected:
        raise ValueError('Duplicate or unknown scaffold support states')
    if method == CATALOGUE_METHOD and (set(observed) != expected or report['native'].get('states') != len(expected)):
        raise ValueError('Scaffold support catalogue does not cover the dumped states exactly')
    supporting, nonsupporting, unknown = defaultdict(set), defaultdict(set), defaultdict(set)
    for row in rows:
        name, aux = row['requested']
        actual, scaffold, states = row.get('support'), row.get('scaffold'), row.get('states')
        same = actual is not None and (actual.get('name'), actual.get('aux')) == (name, aux)
        isolated = scaffold is not None and scaffold.get('name') == 'minecraft:scaffolding'
        if not same or not isolated or not isinstance(states, dict) or states.get('stability') not in (0, 7):
            unknown[name].add(aux)
            continue
        if registry.states((scaffold['name'], scaffold['aux'])) != states:
            raise ValueError('Native scaffold state is absent from the current registry')
        (supporting if states['stability'] == 0 else nonsupporting)[name].add(aux)
    blocks, partial = [], {}
    for name, values in sorted(supporting.items()):
        if values == set(registry.aux_values(name)):
            blocks.append(name)
        else:
            partial[name] = tuple(sorted(values))
    pack = lambda values: dict((name, tuple(sorted(aux))) for name, aux in sorted(values.items()))
    return {'blocks': tuple(blocks), 'partial': partial, 'nonsupporting': pack(nonsupporting),
            'unknown': pack(unknown), 'observed_states': len(observed),
            'unobserved_states': len(expected - set(observed)),
            'scope': 'full_catalogue' if method == CATALOGUE_METHOD else 'measured_samples'}


def generate(check=False, root=ROOT):
    manifest = json.loads((root / 'tools/data/block_registry_manifest.json').read_text(encoding='utf8'))
    source = root / 'tools/data' / ('native_scaffold_supports_nemc_' + manifest['game_version'].split()[-1] + '.json')
    report = json.loads(source.read_text(encoding='utf8'))
    result = capabilities(report, manifest)
    content = ('"""Generated native scaffold supports; unobserved states retain their distance."""\n'
               'SOURCE_VERSION = %r\nPALETTE_SHA256 = %r\nEVIDENCE_SHA256 = %r\n'
               "EVIDENCE_HASH_FORMAT = 'canonical-json-v1'\n"
               'SOURCE_METHOD = %r\nOBSERVATION_SCOPE = %r\nOBSERVED_STATES = %r\n'
               'UNOBSERVED_STATES = %r\nSUPPORTING_BLOCKS = %r\nSUPPORTING_AUX = %r\n'
               'NONSUPPORTING_AUX = %r\nUNKNOWN_AUX = %r\n') % (
                   manifest['game_version'], manifest['source_sha256'].lower(),
                   snapshot_fingerprint(report), report['method'], result['scope'],
                   result['observed_states'], result['unobserved_states'], result['blocks'],
                   result['partial'], result['nonsupporting'], result['unknown'])
    target = root / 'behavior_pack/modern_projection/projection/scaffold_support_data.py'
    if check:
        if not target.is_file() or target.read_text(encoding='utf8') != content:
            raise ValueError('Generated scaffold supports are stale')
    else:
        target.write_text(content, encoding='utf8', newline='\n')
    return {'full_support_names': len(result['blocks']), 'partial_support_names': len(result['partial']),
            'unknown_states': sum(len(values) for values in result['unknown'].values()),
            'observed_states': result['observed_states'], 'unobserved_states': result['unobserved_states'],
            'scope': result['scope']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    print(json.dumps(generate(args.check), sort_keys=True))


if __name__ == '__main__':
    main()
