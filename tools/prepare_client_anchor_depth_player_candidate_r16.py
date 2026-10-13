"""Freeze the R15 depth matrix with the existing local player as positive control."""
import argparse
import ast
import json
from pathlib import Path
import uuid

import prepare_client_anchor_depth_candidate_r15 as previous

ROOT, UI, FILES = previous.ROOT, previous.UI, previous.FILES
digest = previous.digest
archived_files = previous.archived_files
POSITIVE_STATES = ('ui_player_positive', 'ui_player_positive_restored')
POSITIVE_TARGET, POSITIVE_NAME = 'existing_local_player', 'player'
ZERO_CLASSIFICATION = 'custom_anchor_ui_zero_with_existing_player_renderer_positive'
STATES = (POSITIVE_STATES[0], 'ui_empty', 'ui_plain_depth15', 'ui_plain_depth50',
          'ui_plain_depth15_repeat', 'ui_empty_restored', POSITIVE_STATES[1])
ORIGINAL = ROOT / 'docs/evidence/client-anchor-depth-r15-v1/candidate-bundle'
PREVIOUS_SOURCE_SHA256 = digest((ORIGINAL / 'source.py').read_bytes())


def snippets(nonce):
    if digest(Path(previous.__file__).read_bytes()) != PREVIOUS_SOURCE_SHA256:
        raise ValueError('Frozen R15 generation source changed')
    programs = previous.snippets(nonce)
    changed = {}
    old = "  del params['entity_id']\n  params['entity_identifier']='minecraft:cow'\n  params['init_rot_y']=60."
    new = "  params['entity_id']=saved['player']\n  params['scale']=1.\n  params['render_depth']=-50\n  params['init_rot_y']=60."
    for name, source in programs.items():
        source = source.replace('ui_cow_positive', 'ui_player_positive')
        if name.endswith('_client.py') and name[:-10] in previous.STATES:
            source = previous.replace_once(source, old, new)
        name = name.replace('ui_cow_positive', 'ui_player_positive')
        ast.parse(source, filename=name)
        changed[name] = source
    return changed


def contract():
    value = previous.contract()
    value.update(candidate='existing_player_positive_ordinary_entity_ui_depth', states=list(STATES),
                 positive_control={'target': POSITIVE_TARGET, 'scale': 1., 'render_depth': -50,
                                   'init_rot_x': 0., 'init_rot_y': 60., 'init_rot_z': 0.},
                 source_sha256=digest(Path(__file__).read_bytes()),
                 r15_source_sha256=PREVIOUS_SOURCE_SHA256,
                 r15_plan_sha256='533521976e014d1c7606010060c2ad111e40aac8b3f1dcea64cd8f58a720e55a',
                 no_positive_entity_creation=True, player_inventory_mutated=False,
                 actorless_identifier_submission=False)
    return value


def prepare(output):
    output = Path(output).absolute()
    if output.exists():
        raise ValueError('Preserve previous player-positive candidate')
    nonce = uuid.uuid4().hex
    files = {name: source.encode('ascii') for name, source in snippets(nonce).items()}
    files.update({'source.py': Path(__file__).read_bytes(), 'r15-source.py': (ORIGINAL / 'source.py').read_bytes(),
                  'original-r15-plan.json': (ORIGINAL / 'plan.json').read_bytes(),
                  'original-r14-plan.json': (ORIGINAL / 'original-r14-plan.json').read_bytes(),
                  'plain.json': (ORIGINAL / 'plain.json').read_bytes()})
    plan = dict(contract(), nonce=nonce, files=[{'path': name, 'bytes': len(raw), 'sha256': digest(raw)}
                                             for name, raw in sorted(files.items())])
    output.mkdir(parents=True)
    for name, raw in files.items():
        (output / name).write_bytes(raw)
    (output / 'plan.json').write_bytes((json.dumps(plan, indent=2)+'\n').encode('ascii'))
    verify(output)
    return plan


def verify(bundle):
    bundle = Path(bundle).resolve(strict=True)
    plan = json.loads((bundle / 'plan.json').read_bytes())
    if any(plan.get(key) != value for key, value in contract().items()):
        raise ValueError('Frozen player-positive contract changed')
    nonce = plan['nonce']
    if len(nonce) != 32 or any(char not in '0123456789abcdef' for char in nonce):
        raise ValueError('Candidate nonce changed')
    generated = snippets(nonce)
    expected = set(generated) | {'source.py', 'r15-source.py', 'original-r15-plan.json', 'original-r14-plan.json', 'plain.json'}
    if {row['path'] for row in plan['files']} != expected or len(plan['files']) != len(expected):
        raise ValueError('Candidate inventory changed')
    for row in plan['files']:
        raw = (bundle / row['path']).read_bytes()
        if len(raw) != row['bytes'] or digest(raw) != row['sha256']:
            raise ValueError('Candidate bytes changed: '+row['path'])
    for name, source in generated.items():
        if (bundle / name).read_bytes() != source.encode('ascii'):
            raise ValueError('Generated candidate changed: '+name)
    originals = {'source.py': Path(__file__), 'r15-source.py': ORIGINAL/'source.py',
                 'original-r15-plan.json': ORIGINAL/'plan.json', 'original-r14-plan.json': ORIGINAL/'original-r14-plan.json',
                 'plain.json': ORIGINAL/'plain.json'}
    if any((bundle/name).read_bytes() != source.read_bytes() for name, source in originals.items()):
        raise ValueError('Candidate generation provenance changed')
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'verify'))
    parser.add_argument('path')
    args = parser.parse_args()
    plan = prepare(args.path) if args.command == 'prepare' else verify(args.path)
    print(json.dumps({'files': len(plan['files']), 'plan_sha256': digest((Path(args.path)/'plan.json').read_bytes()),
                      'sdk_dispatch_attempted': False}))


if __name__ == '__main__':
    main()
