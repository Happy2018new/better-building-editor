"""Read actual native UI uniforms against owner records in an isolated project."""
import argparse
import json
import os
from pathlib import Path
import sys
import time


STATE = '''rows=[]
for key,entry in s.liquid_controls.registry.items():
 renderer=entry.get('renderer')
 if renderer is not None:
  for slot,model_id in enumerate(renderer.ids):
   if model_id is not None:
    rows.append({'key':repr(key),'slot':slot,'visible':renderer.visible[slot],
     'model_id':model_id,'native_id':renderer.dolls[slot].GetModelId(),
     'cached':renderer.uniforms[slot],
     'actual':dict((index,renderer.model_component.GetExtraUniformValue(model_id,index))
                   for index in (1,2,3,4))})
_result=json.dumps(rows)
'''
REAPPLY = '''updated=[]
for key,entry in s.liquid_controls.registry.items():
 renderer=entry.get('renderer')
 if renderer is not None:
  for slot,model_id in enumerate(renderer.ids):
   if model_id is not None and renderer.visible[slot]:
    for index,value in renderer.uniforms[slot].items():
     assert renderer.model_component.SetExtraUniformValue(model_id,index,value)
     updated.append((model_id,index,value))
_result=json.dumps(updated)
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--capture-exe', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose fresh diagnosis output')
    sys.path.insert(0, str(args.project.resolve(strict=True) / 'tools'))
    import probe_product_water as probe
    from _session import load_session
    from water_capture_contract import stable_scene_predicate
    os.environ.update(MCDEV_SESSION_FILE=str(Path(args.session).resolve(strict=True)), MCDEV_OWNER=args.owner)
    bound = load_session(args.session, args.owner, live=True)
    if Path(bound['project']).resolve() != args.project.resolve(strict=True):
        parser.error('Project differs from the bound game')
    report = {'completed': False, 'restored': False, 'session_id': bound['id'], 'captures': {}}
    with probe.base.Client(timeout=45) as client:
        check = probe.blueprints.BlueprintCheck(client, args.output, 45.)
        installed = False
        try:
            check.run(probe.blueprints.INSTALL_PROBE)
            installed = True
            check.run(probe.PROFILE % (True, True))
            check.run('owner.open_workspace()\n_result=True')
            check.wait('open Scene', lambda value: value['open'] and not value['transition'], check.navigation)
            check.run(probe.LOAD % (('pool', 'wet', (35., 25., 4.6)),))
            report['ready'] = check.wait('pool settled',
                stable_scene_predicate((35., 25., 4.6), (0., 0.), probe.workspace.scene_ready),
                lambda: check.run(probe.SCENE_STATE))
            for name in ('baseline', 'reapplied'):
                if name == 'reapplied':
                    report['writes'] = check.run(REAPPLY)
                report[name] = check.run(STATE)
                time.sleep(.35)
                report['captures'][name] = probe.base.capture(args.session, args.owner,
                    args.output.with_name(args.output.stem + '_' + name + '.png'), args.capture_exe)
            report['completed'] = True
        finally:
            if installed:
                if check.navigation()['open']:
                    check.run('navigator.pop()\n_result=True')
                    check.wait('close Scene', lambda value: not value['open'] and not value['transition'], check.navigation)
                check.run(probe.RESTORE_PROFILE)
                report['restored'] = True
            probe.base.write(args.output, report)
    print(json.dumps({'completed': report['completed'], 'restored': report['restored']}))


if __name__ == '__main__':
    main()
