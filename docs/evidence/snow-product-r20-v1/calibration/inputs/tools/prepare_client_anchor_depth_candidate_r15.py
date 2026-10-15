"""Prepare an offline ordinary-depth candidate; this tool never calls the SDK."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import uuid


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'docs/evidence/client-anchor-world-ui-r14-v1'
ORIGINAL = ARCHIVE / 'full-evidence'
PREFIX = 'client-anchor-world-ui-r14-v1'
BUNDLE = ORIGINAL / (PREFIX + '.sources/bundle')
PLAN_SHA256 = '3b9c2a9ea2a11c3d7c136b6c5f7c3b08ab599e93c2ffc5257781965a5fb258df'
ATTRIBUTE = '_client_anchor_depth_probe'
STATES = ('ui_cow_positive', 'ui_empty', 'ui_plain_depth15',
          'ui_plain_depth50', 'ui_plain_depth15_repeat',
          'ui_empty_restored', 'ui_cow_positive_restored')
UI = {'scale': .35, 'render_depth': -15, 'init_rot_x': 0.,
      'init_rot_y': 0., 'init_rot_z': 0.}
FILES = ('install_client.py', 'actor_ready_client.py', 'open_ui_client.py',
         'status_client.py', 'remove_client.py', 'navigation_client.py',
         'pop_client.py', 'destroy_client.py', 'absent_client.py', 'verify_client.py')


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def archived_files():
    index = json.loads((ARCHIVE / 'complete-archive-index.json').read_bytes())
    for row in index['files']:
        payload = (ORIGINAL / row['path']).read_bytes()
        if len(payload) != row['bytes'] or digest(payload) != row['sha256']:
            raise ValueError('Original R14 archive changed: ' + row['path'])
    plan = (BUNDLE / 'plan.json').read_bytes()
    if digest(plan) != PLAN_SHA256:
        raise ValueError('Original R14 plan changed')
    return json.loads(plan)


def replace_once(code, old, new):
    if code.count(old) != 1:
        raise ValueError('Frozen snippet adaptation is ambiguous: ' + old)
    return code.replace(old, new)


def snippets(nonce):
    old = archived_files()['nonce']

    def source(name):
        code = (BUNDLE / name).read_bytes().decode('ascii').replace('\r\n', '\n')
        return code.replace(old, nonce).replace('_client_anchor_world_ui_probe', ATTRIBUTE)

    programs = {name: source(name) for name in FILES}
    programs['install_client.py'] = replace_once(
        programs['install_client.py'], "'render_depth': -50", "'render_depth': -15")
    programs['install_client.py'] = programs['install_client.py'].replace(
        "'client_anchor_ui_'", "'client_anchor_depth_'")
    programs['open_ui_client.py'] = replace_once(
        programs['open_ui_client.py'], 'renderDepth=-50', 'renderDepth=-15')
    programs['status_client.py'] += "row=json.loads(_result)\nrow['last_submission']=saved.get('last_submission')\n_result=json.dumps(row)\n"
    control = source('ui_plain_client.py')
    control = replace_once(control, "label='ui_plain'", 'label=%r')
    control = replace_once(control, "if label=='ui_plain':", "if label=='ui_plain_depth15':")
    control = replace_once(control, "elif label=='world_empty_restored':", "elif label=='ui_empty_restored':")
    control = replace_once(control, "if label=='world_plain':",
                           "if label in ('ui_plain_depth15','ui_plain_depth50','ui_plain_depth15_repeat'):")
    submission = """params=dict(saved['ui_params'])
 params['render_depth']=-50 if label=='ui_plain_depth50' else -15
 if label in ('ui_cow_positive','ui_cow_positive_restored'):
  assert saved['current'] is None and all(row['state']=='removed' for row in saved['attachments'])
  del params['entity_id']
  params['entity_identifier']='minecraft:cow'
  params['init_rot_y']=60.
 saved['last_submission']=params
"""
    control = replace_once(control, " event['value']=saved['ref'].current.asNeteasePaperDoll().RenderEntity(saved['ui_params'])",
                           ' ' + submission + " event['value']=saved['ref'].current.asNeteasePaperDoll().RenderEntity(params)")
    # The literal modulo operators are from the frozen code; interpolate only
    # the one label placeholder rather than treating the whole program as a format.
    programs.update({label + '_client.py': control.replace('label=%r', 'label=' + repr(label)) for label in STATES})
    for name, code in programs.items():
        ast.parse(code, filename=name)
    return programs


def contract():
    return {'schema': 1, 'candidate': 'ordinary_entity_ui_depth',
            'states': list(STATES), 'frames_per_state': 2,
            'physical_size': [1994, 1105], 'fixed_ui_roi': [0, 111, 1994, 1105],
            'ui': UI, 'old_depth_control': -50,
            'positive_control': {'entity_identifier': 'minecraft:cow', 'scale': .35,
                                 'render_depth': -15, 'init_rot_x': 0.,
                                 'init_rot_y': 60., 'init_rot_z': 0.},
            'same_owned_page_visible_for_every_capture': True,
            'world_captures': 0, 'binding_count': 1, 'bone': 'root',
            'is_client_entity': True, 'item_offset': [0., 0., 0.],
            'item_rotation_zyx': [0., 0., 0.], 'item_scale': 1.,
            'ordinary_minimum_stable_pixels': 80, 'difference_channel_threshold': 25,
            'marker_contract': 'Unchanged V4 training/holdout corners and one-physical-pixel gate',
            'normal_budget_seconds': 90, 'cleanup_deadline_seconds': 120,
            'outer_budget_seconds': 150, 'native_retries': 0,
            'sdk_dispatch_authorized': False, 'owner_runner_ready': False,
            'original_r14_plan_sha256': PLAN_SHA256,
            'source_sha256': digest(Path(__file__).read_bytes()),
            'resources_modified': False, 'production_modified': False,
            'player_or_camera_mutation': False, 'world_or_inventory_mutation': False,
            'enchantment_tested': False, 'production_rendering_accepted': False,
            'editor_frame_content_accepted': False, 'shared_depth_accepted': False,
            'enchantment_glint_accepted': False}


def prepare(output):
    output = Path(output).absolute()
    if output.exists():
        raise ValueError('Preserve existing candidate bundle')
    nonce = uuid.uuid4().hex
    files = {name: code.encode('ascii') for name, code in snippets(nonce).items()}
    files['source.py'] = Path(__file__).read_bytes()
    files['original-r14-plan.json'] = (BUNDLE / 'plan.json').read_bytes()
    files['plain.json'] = (BUNDLE / 'plain.json').read_bytes()
    plan = dict(contract(), nonce=nonce, files=[
        {'path': name, 'bytes': len(payload), 'sha256': digest(payload)}
        for name, payload in sorted(files.items())])
    output.mkdir(parents=True)
    for name, payload in files.items():
        (output / name).write_bytes(payload)
    (output / 'plan.json').write_bytes((json.dumps(plan, indent=2) + '\n').encode('ascii'))
    verify(output)
    return plan


def verify(bundle):
    bundle = Path(bundle).resolve(strict=True)
    plan = json.loads((bundle / 'plan.json').read_bytes())
    if any(plan.get(key) != value for key, value in contract().items()):
        raise ValueError('Candidate contract changed')
    nonce = plan['nonce']
    if len(nonce) != 32 or any(value not in '0123456789abcdef' for value in nonce):
        raise ValueError('Candidate nonce is invalid')
    programs = snippets(nonce)
    expected = set(programs) | {'source.py', 'original-r14-plan.json', 'plain.json'}
    if {row['path'] for row in plan['files']} != expected or len(plan['files']) != len(expected):
        raise ValueError('Candidate file inventory changed')
    for row in plan['files']:
        payload = (bundle / row['path']).read_bytes()
        if len(payload) != row['bytes'] or digest(payload) != row['sha256']:
            raise ValueError('Candidate bytes changed: ' + row['path'])
    for name, code in programs.items():
        if (bundle / name).read_bytes() != code.encode('ascii'):
            raise ValueError('Candidate generated program changed: ' + name)
    if ((bundle / 'source.py').read_bytes() != Path(__file__).read_bytes() or
            (bundle / 'original-r14-plan.json').read_bytes() != (BUNDLE / 'plan.json').read_bytes() or
            (bundle / 'plain.json').read_bytes() != (BUNDLE / 'plain.json').read_bytes()):
        raise ValueError('Candidate provenance changed')
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'verify'))
    parser.add_argument('path')
    args = parser.parse_args()
    plan = prepare(args.path) if args.command == 'prepare' else verify(args.path)
    print(json.dumps({'files': len(plan['files']), 'states': plan['states'],
                      'plan_sha256': digest((Path(args.path) / 'plan.json').read_bytes()),
                      'sdk_dispatch_authorized': False, 'owner_runner_ready': False}))


if __name__ == '__main__':
    main()
