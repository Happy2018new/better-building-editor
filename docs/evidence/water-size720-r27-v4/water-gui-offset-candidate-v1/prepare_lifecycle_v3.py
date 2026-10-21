"""Retain v2 static refusal; pin launcher PROJECT independently of owner naming."""
import ast
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OLD = Path(__file__).resolve().parent.with_name('water-gui-offset-lifecycle-v2')
WORK = OLD.with_name('water-gui-offset-lifecycle-v3')
OWNER = 'water-r27-gui-scene-v3'


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
    for name in hosts['host_sha256']:
        if not name.endswith('.py'):
            continue
        raw = (OLD / name).read_bytes()
        if name != 'candidate_bootstrap.py':
            text = raw.decode('utf-8').replace(binding['owner'], OWNER)
            text = text.replace('_water_r27_gui_offset_bootstrap_v2', '_water_r27_gui_scene_bootstrap_v3')
            if name == 'launch_r25.py':
                node = next(node for node in ast.parse(text).body if isinstance(node, ast.Assign)
                            and any(isinstance(target, ast.Name) and target.id == 'PROJECT' for target in node.targets))
                text = text.replace(ast.get_source_segment(text, node),
                                    'PROJECT = Path(' + repr(binding['project']) + ')')
            raw = text.encode('utf-8')
        (WORK / name).write_bytes(raw)
    (WORK / 'private-source-v1.json').write_bytes((OLD / 'private-source-v1.json').read_bytes())
    binding.update(owner=OWNER, bootstrap_receipt_marker='_water_r27_gui_scene_bootstrap_v3')
    write('final-source-binding-v1.json', binding)
    spec = importlib.util.spec_from_file_location('gui_scene_v3_bootstrap', WORK / 'bootstrap_payload.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    payload = module.dispatch_code((WORK / 'candidate_bootstrap.py').read_text('utf-8'), binding)
    (WORK / 'dispatched-bootstrap-payload.py').write_bytes(payload.encode('utf-8'))
    for name in ('product-v2-launch-inputs.json', 'plan-v1.json'):
        data = json.loads((OLD / name).read_bytes())
        data['owner'] = OWNER
        if name == 'plan-v1.json':
            data.update(declared_at_utc=datetime.now(timezone.utc).isoformat(),
                        host_code_sha256={name: sha(WORK / name) for name in data['host_code_sha256']})
        write(name, data)
    stage = json.loads((OLD / 'stage-r25.json').read_bytes())
    stage.update(owner=OWNER, plan_sha256=sha(WORK / 'plan-v1.json'))
    write('stage-r25.json', stage)
    hosts.update(source_binding_sha256=sha(WORK / 'final-source-binding-v1.json'),
                 host_sha256={name: sha(WORK / name) for name in hosts['host_sha256']},
                 frozen_at_utc=datetime.now(timezone.utc).isoformat())
    write('prelaunch-host-binding-v1.json', hosts)
    for name in ('verify_static_scene_v2.py', 'verify_scene_controls.py'):
        (WORK / name).write_bytes((OLD / name).read_bytes())
    write('preparation-v3.json', {'schema': 1, 'MC_started': False,
        'previous_v2_static_refusal_retained': True,
        'cause': 'A textual owner replacement also matched the source project basename; original pre-Popen project identity gate rejected it',
        'correction': 'Launcher PROJECT is pinned from the exact original source binding after owner replacement',
        'product_candidate_source_and_archive_unchanged': True,
        'source_project': binding['project'], 'plan_sha256': sha(WORK / 'plan-v1.json'),
        'host_binding_sha256': sha(WORK / 'prelaunch-host-binding-v1.json'),
        'formal_A_accepted': False, 'default_path_evidence': False})
    print(json.dumps({'prepared': True, 'MC_started': False, 'owner': OWNER,
                      'plan_sha256': sha(WORK / 'plan-v1.json')}))


if __name__ == '__main__':
    main()
