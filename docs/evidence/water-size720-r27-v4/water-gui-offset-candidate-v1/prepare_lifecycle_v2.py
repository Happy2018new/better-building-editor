"""Retain draft v1; fix explicit payload import and bound the Scene child in v2."""
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OLD = Path(__file__).resolve().parent
WORK = OLD.with_name('water-gui-offset-lifecycle-v2')
OWNER = 'water-r27-gui-offset-v2'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    with (WORK / name).open('x', encoding='utf-8', newline='\n') as output:
        json.dump(value, output, indent=2)
        output.write('\n')


def main():
    assert not WORK.exists()
    WORK.mkdir()
    hosts = json.loads((OLD / 'prelaunch-host-binding-v1.json').read_bytes())
    binding = json.loads((OLD / 'final-source-binding-v1.json').read_bytes())
    patches = []
    for name in hosts['host_sha256']:
        if not name.endswith('.py'):
            continue
        raw = (OLD / name).read_bytes()
        revised = raw
        if name != 'candidate_bootstrap.py':
            text = raw.decode('utf-8').replace(binding['owner'], OWNER)
            text = text.replace('_water_r27_gui_offset_bootstrap_v1', '_water_r27_gui_offset_bootstrap_v2')
            if name == 'scene_game.py':
                old = "EXTRA_STATE = '''row=json.loads(_result)\n"
                assert text.count(old) == 1
                text = text.replace(old,
                    "EXTRA_STATE = '''from modern_projection.projection.widgets import Theme\nrow=json.loads(_result)\n")
            if name == 'run_scene_group.py':
                old = "'--root-grant',str(args.root_grant.resolve(strict=True))))"
                assert text.count(old) == 1
                text = text.replace(old, "'--root-grant',str(args.root_grant.resolve(strict=True))),timeout=900)")
            revised = text.encode('utf-8')
        (WORK / name).write_bytes(revised)
        if revised != raw:
            patches.extend(difflib.unified_diff(raw.decode('utf-8').splitlines(True), revised.decode('utf-8').splitlines(True),
                            fromfile='draft-v1/' + name, tofile='lifecycle-v2/' + name))
    # Exact manifest/source/archive reuse; the three candidate product files are
    # unchanged from the reviewed v1. The host owner and bootstrap marker are new.
    (WORK / 'private-source-v1.json').write_bytes((OLD / 'private-source-v1.json').read_bytes())
    binding.update(owner=OWNER, bootstrap_receipt_marker='_water_r27_gui_offset_bootstrap_v2',
                   diagnostic_manifest_sha256=sha(WORK / 'private-source-v1.json'))
    write('final-source-binding-v1.json', binding)
    inputs = json.loads((OLD / 'product-v2-launch-inputs.json').read_bytes())
    inputs['owner'] = OWNER
    write('product-v2-launch-inputs.json', inputs)
    plan = json.loads((OLD / 'plan-v1.json').read_bytes())
    plan.update(owner=OWNER, declared_at_utc=datetime.now(timezone.utc).isoformat(),
        host_code_sha256={name: sha(WORK / name) for name in plan['host_code_sha256']},
        scene_child_timeout_seconds=900)
    write('plan-v1.json', plan)
    stage = json.loads((OLD / 'stage-r25.json').read_bytes())
    stage.update(owner=OWNER, plan_sha256=sha(WORK / 'plan-v1.json'))
    write('stage-r25.json', stage)
    hosts.update(source_binding_sha256=sha(WORK / 'final-source-binding-v1.json'),
        host_sha256={name: sha(WORK / name) for name in hosts['host_sha256']},
        frozen_at_utc=datetime.now(timezone.utc).isoformat())
    write('prelaunch-host-binding-v1.json', hosts)
    (WORK / 'draft-v1-to-lifecycle-v2.patch').write_bytes(''.join(patches).encode('utf-8'))
    write('preparation-v2.json', {'schema': 1, 'MC_started': False, 'original_v1_retained': True,
        'offline_v1_review_findings': ['EXTRA_STATE used Theme without an explicit import in that RPC',
                                     'Scene subprocess needed a fixed 900-second group timeout'],
        'product_candidate_files_unchanged': True, 'archive_reused': binding['archive'],
        'plan_sha256': sha(WORK / 'plan-v1.json'), 'host_binding_sha256': sha(WORK / 'prelaunch-host-binding-v1.json'),
        'production_admission_performed': False, 'formal_A_accepted': False})
    print(json.dumps({'MC_started': False, 'owner': OWNER, 'work': str(WORK),
        'plan_sha256': sha(WORK / 'plan-v1.json'), 'host_binding_sha256': sha(WORK / 'prelaunch-host-binding-v1.json')}))


if __name__ == '__main__':
    main()
