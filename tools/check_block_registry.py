"""Check generated registry provenance and audit transforms for every native state."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))

from generate_block_registry import generate
from projection import block_registry as registry
from projection import state_transform


def audit_transforms():
    resolved = dict((operation, 0) for operation in state_transform.OPERATIONS)
    unrepresentable = dict((operation, 0) for operation in state_transform.OPERATIONS)
    for name in registry.BLOCKS:
        for aux in registry.aux_values(name):
            value = (name, aux)
            properties = registry.states(value)
            for operation in state_transform.OPERATIONS:
                try:
                    target_properties = state_transform.transform_states(properties, operation)
                except state_transform.UnrepresentableTransform:
                    try:
                        state_transform.transform(value, operation)
                    except state_transform.UnrepresentableTransform:
                        unrepresentable[operation] += 1
                        continue
                    raise AssertionError('Unrepresentable state was silently retained: %r %s' %
                                         (value, operation))
                target = registry.from_states(name, target_properties)
                if target is None:
                    try:
                        state_transform.transform(value, operation)
                    except state_transform.UnrepresentableTransform:
                        unrepresentable[operation] += 1
                        continue
                    raise AssertionError('Missing target state was silently retained: %r %s' %
                                         (value, operation))
                actual = state_transform.transform(value, operation)
                if registry.states(actual) != target_properties:
                    raise AssertionError('Transform did not produce the resolved native state: %r %s' %
                                         (value, operation))
                resolved[operation] += 1
    print('Audited %d records across %d operations' %
          (registry.RECORD_COUNT, len(state_transform.OPERATIONS)))
    for operation in state_transform.OPERATIONS:
        print('%s: %d resolved, %d explicitly unrepresentable' %
              (operation, resolved[operation], unrepresentable[operation]))


if __name__ == '__main__':
    manifest = json.loads((ROOT / 'tools/data/block_registry_manifest.json').read_text(encoding='utf8'))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', nargs='?', type=Path, default=ROOT / manifest['source_file'])
    parser.add_argument('--source-version', help='override version inferred from nemc_<version>.json')
    args = parser.parse_args()
    generate(args.source, args.source_version, check=True)
    audit_transforms()
