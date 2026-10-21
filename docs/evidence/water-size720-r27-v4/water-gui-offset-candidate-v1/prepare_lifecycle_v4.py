"""Add unchanged-document visible-water resize observations before the next load."""
import ast
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path

OLD = Path(__file__).resolve().parent.with_name('water-gui-offset-lifecycle-v3')
WORK = OLD.with_name('water-gui-offset-lifecycle-v4')
OWNER = 'water-r27-gui-scene-v4'


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
            text = text.replace('_water_r27_gui_scene_bootstrap_v3', '_water_r27_gui_scene_bootstrap_v4')
            if name == 'launch_r25.py':
                node = next(node for node in ast.parse(text).body if isinstance(node, ast.Assign)
                            and any(isinstance(target, ast.Name) and target.id == 'PROJECT' for target in node.targets))
                text = text.replace(ast.get_source_segment(text, node), 'PROJECT = Path(' + repr(binding['project']) + ')')
            if name == 'run_scene_observation.py':
                assert text.count("for control in ('wet', 'dry'):") == 1
                text = text.replace("for control in ('wet', 'dry'):", "for control in plan['controls']:")
                anchor = "                if index == 0:\n                    check.run('owner.open_workspace()\\n_result=True')"
                assert text.count(anchor) == 1
                addition = '''                if index > 0:
                    previous = report['phases'][index - 1]['rows'][-1]
                    seam = {'before_previous_GUI': previous['after'],
                            'document_reloaded': False, 'same_request_required': False}
                    phase['resize_existing_water'] = seam
                    previous_pose = tuple(previous['case']['pose'])
                    previous_pan = (.15, -.08) if previous_pose[:2] == (0., 0.) else (0., 0.)
                    stable_resize = stable_scene_predicate(previous_pose, previous_pan, product.workspace.scene_ready)
                    def resize_ready(state):
                        return stable_resize(state) and describe_scene(state, stage['expected_integer_gui'], True)['complete']
                    seam['after_actual_event_refresh'] = check.wait('same-document visible water after resize',
                        resize_ready, lambda: check.run(state_code))
                    after_resize = seam['after_actual_event_refresh']
                    assert after_resize['document_id'] == previous['after']['document_id']
                    assert after_resize['source_cells'] == previous['after']['source_cells']
                    assert [value['key'] for value in after_resize['native_water_controls']] == [value['key'] for value in previous['after']['native_water_controls']]
                    seam['request_values_unchanged'] = [value['ready_request'] for value in after_resize['liquid_control_requests']] == [value['ready_request'] for value in previous['after']['liquid_control_requests']]
                    resource(stage['label'] + '_resize_existing_water_before_capture')
                    seam['capture'] = base.capture(args.session, plan['owner'], WORK / 'captures' / (stage['label'] + '_same_document_resize.png'), capture_exe)
                    resource(stage['label'] + '_resize_existing_water_after_capture')
                    seam['after_capture'] = check.run(state_code)
                    seam['capture_layout_unchanged'] = scene_capture_state(after_resize) == scene_capture_state(seam['after_capture'])
                    save()
                    assert seam['capture_layout_unchanged']
'''
                text = text.replace(anchor, addition + anchor)
                text = text.replace("'images': sum(len(phase['rows']) for phase in report['phases']),",
                                    "'images': sum(len(phase['rows']) + int('resize_existing_water' in phase) for phase in report['phases']),")
            raw = text.encode('utf-8')
        (WORK / name).write_bytes(raw)
    (WORK / 'private-source-v1.json').write_bytes((OLD / 'private-source-v1.json').read_bytes())
    binding.update(owner=OWNER, bootstrap_receipt_marker='_water_r27_gui_scene_bootstrap_v4')
    write('final-source-binding-v1.json', binding)
    spec = importlib.util.spec_from_file_location('gui_scene_v4_bootstrap', WORK / 'bootstrap_payload.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    (WORK / 'dispatched-bootstrap-payload.py').write_bytes(module.dispatch_code((WORK / 'candidate_bootstrap.py').read_text('utf-8'), binding).encode('utf-8'))
    for name in ('product-v2-launch-inputs.json', 'plan-v1.json'):
        data = json.loads((OLD / name).read_bytes())
        data['owner'] = OWNER
        if name == 'plan-v1.json':
            data.update(declared_at_utc=datetime.now(timezone.utc).isoformat(), controls=['dry', 'wet'],
                        captures_declared=26, existing_water_resize_observations=2,
                        same_ready_request_not_assumed=True,
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
    write('preparation-v4.json', {'schema': 1, 'MC_started': False, 'previous_unlaunched_v3_retained': True,
        'scope_addition': 'Visible water remains mounted at GUI transition; same document/cells/keys recorded before next LOAD',
        'ready_request_values': 'Recorded equality; GUI-dependent pose changes are allowed and cannot be mislabeled unchanged',
        'source_and_archive_unchanged': True, 'plan_sha256': sha(WORK / 'plan-v1.json'),
        'host_binding_sha256': sha(WORK / 'prelaunch-host-binding-v1.json'), 'formal_A_accepted': False})
    print(json.dumps({'prepared': True, 'MC_started': False, 'owner': OWNER,
                      'plan_sha256': sha(WORK / 'plan-v1.json'),
                      'host_binding_sha256': sha(WORK / 'prelaunch-host-binding-v1.json')}))


if __name__ == '__main__':
    main()
