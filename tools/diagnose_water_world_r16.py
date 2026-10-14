"""Inspect world-native water payloads without changing renderer source files."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

STATE = '''renderer=liquid.renderer
rows=[]
for key,record in sorted(renderer.active.items(),key=lambda item:repr(item[0])):
 rows.append({'key':repr(key),'id':record['model_id'],'visible':record['visible'],
  'anchor':record['anchor'],'center':renderer.center(record['anchor'],record['group'].origin),
  'group':record['group'],'actual':dict((index,renderer.model.GetExtraUniformValue(record['model_id'],index))
   for index in (1,2,3,4))})
_result=json.dumps({'groups':rows,'dimension':renderer.dimension,'scale':renderer.scale,
 'player_foot':b.factory.CreatePos(api.GetLocalPlayerId()).GetFootPos(),
 'rotation':renderer.rotation,'native_methods':[name for name in dir(renderer.model) if 'FreeModel' in name]})
'''
REAPPLY = '''renderer=liquid.renderer
rows=[]
for record in renderer.active.values():
 values=[]
 for index,value in enumerate(record['group'].uniforms,1):
  values.append(renderer.model.SetExtraUniformValue(record['model_id'],index,value))
 rows.append((record['model_id'],values))
_result=json.dumps(rows)
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--capture-exe', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--origin-y', type=int, default=3)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh diagnostic')
    sys.path.insert(0, str(args.project.resolve(strict=True) / 'tools'))
    import probe_product_water as probe
    from _session import load_session
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
            report['saved_view'] = check.run(probe.visuals.SAVE_VISUAL)
            check.run(probe.LOAD % (('pool', 'wet', (35., 25., 4.6)),))
            check.run('s.origin=(3,%r,3)\ns.opacity=1.\ns.projection_missing=False\nb.project()\n_result=True' % args.origin_y)
            report['ready'] = check.wait('world water ready', probe.workspace.world_ready,
                                        lambda: check.run(probe.WORLD_STATE))
            report['camera'] = check.run(probe.CAMERA % (((6.5, args.origin_y + 3.5, 6.5), (3., 2.5, 4.)),))
            for phase in ('baseline', 'reapplied'):
                if phase == 'reapplied':
                    report['writes'] = check.run(probe.workspace.WATER_OWNER + REAPPLY)
                report[phase] = check.run(probe.workspace.WATER_OWNER + STATE)
                time.sleep(.35)
                report['captures'][phase] = probe.base.capture(args.session, args.owner,
                    args.output.with_name(args.output.stem + '_' + phase + '.png'), args.capture_exe)
            report['completed'] = True
        finally:
            if installed:
                check.run('b.stop_projection()\n_result=True')
                check.run(probe.visuals.camera_restore_code(False))
                check.run("saved=sys._blueprint_visual_saved\ns.origin=saved['origin'];s.opacity=saved['opacity'];s.projection_missing=saved['missing'];s.projection_outline=saved['outline']\ndel sys._blueprint_visual_saved\n_result=True")
                check.run(probe.RESTORE_PROFILE)
                report['restored'] = True
            probe.base.write(args.output, report)
    print(json.dumps({'completed': report['completed'], 'restored': report['restored']}))


if __name__ == '__main__':
    main()
