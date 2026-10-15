"""Isolate custom-alpha versus native-water contribution at a frozen phase."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
import probe_liquid_pose_channel as base
import probe_liquid_workspace as workspace
import probe_product_water as product
import verify_debug_blueprints as blueprints
from _session import load_session

INSTALL_FILTER = '''sys._water_duplicate_strip=False
sys._water_duplicate_calls=[]
sys._water_duplicate_original=BlueprintNativeGeometryProbe.CombineBlockPaletteToGeometry
sys._water_duplicate_geometry=b.geometry
sys._water_duplicate_geometry_serial=0
def water_duplicate_geometry(*args,**kwargs):
 sys._water_duplicate_geometry_serial+=1
 kwargs['name']='water_duplicate_%d_%s' % (sys._water_duplicate_geometry_serial,kwargs.get('name','mesh'))
 return sys._water_duplicate_geometry(*args,**kwargs)
b.geometry=water_duplicate_geometry
def water_duplicate_combine(self,palette,name,mode=0):
 data=palette.SerializeBlockPalette()
 rows=[]
 for layer in ('common','extra'):
  for material,indices in data.get(layer,{}).items():
   if material[0] in ('minecraft:water','minecraft:flowing_water'):
    rows.append({'layer':layer,'material':material,'indices':list(indices)})
 sys._water_duplicate_calls.append({'strip':sys._water_duplicate_strip,'name':name,'water':rows})
 if sys._water_duplicate_strip:
  for layer,states in (('common','states'),('extra','extraStates')):
   data[layer]=dict((value,indices) for value,indices in data.get(layer,{}).items()
    if value[0] not in ('minecraft:water','minecraft:flowing_water'))
   data[states]=dict((value,state) for value,state in data.get(states,{}).items()
    if value in data[layer])
  assert palette.DeserializeBlockPalette(data)
 return sys._water_duplicate_original(self,palette,name,mode)
BlueprintNativeGeometryProbe.CombineBlockPaletteToGeometry=water_duplicate_combine
_result=True
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--capture-exe', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh report')
    os.environ.update(MCDEV_SESSION_FILE=str(args.session), MCDEV_OWNER=args.owner,
                      MCDEV_ALLOW_USER_FOREGROUND='1')
    session = load_session(args.session, args.owner, live=True)
    if Path(session['project']).resolve() != args.project.resolve():
        parser.error('Project identity mismatch')
    report = dict(schema=1, completed=False, restored=False, rows={}, captures={}, cleanup_errors=[],
                  game_pid=session['game_pid'], game_identity=session['game_identity'],
                  session_file=session['session_file'], clock='frozen_frame_zero')

    def record():
        base.write(args.output, report)

    with base.Client(timeout=45) as client:
        check = blueprints.BlueprintCheck(client, args.output, 45.)
        installed = False
        try:
            check.run(blueprints.INSTALL_PROBE)
            installed = True
            if check.navigation()['open']:
                check.run('navigator.pop()\n_result=True')
                check.wait('close', lambda row: not row['open'] and not row['transition'], check.navigation)
            report['profile'] = check.run(product.PROFILE % (True, True))
            check.run(INSTALL_FILTER)
            check.run('owner.open_workspace()\n_result=True')
            check.wait('open', lambda row: row['open'] and not row['transition'], check.navigation)
            for strip in (False, True):
                check.run('sys._water_duplicate_strip=%r\ns.tiles.parts.clear()\ns.tiles.context=None\ns.tiles.document_size=None\n_result=True' % strip)
                report['rows'][str(strip)] = check.run(product.LOAD % (('wet_oak_fence', 'wet', (0., 0., 3.)),))
                check.wait('settled', workspace.scene_ready, lambda: check.run(product.SCENE_STATE))
                for alpha in (-1., 0., 1.):
                    label = ('stripped' if strip else 'original') + '_alpha_' + str(alpha)
                    check.run(workspace.SCENE_ALPHA % alpha + 's.emit()\n_result=True')
                    time.sleep(.35)
                    report['rows'][label] = check.run(product.SCENE_STATE)
                    report['captures'][label] = base.capture(args.session, args.owner,
                        args.output.with_name(args.output.stem + '_' + label + '.png'), args.capture_exe)
                    record()
            report['native_calls'] = check.run('_result=json.dumps(sys._water_duplicate_calls)')
            if not all(any(row['strip'] == value and row['water']
                           for row in report['native_calls']) for value in (False, True)):
                raise AssertionError('Both independent native mesh submissions must contain source water')
            report['completed'] = True
        except Exception as error:
            report['error'] = type(error).__name__ + ': ' + str(error)
            raise
        finally:
            if installed:
                try:
                    check.run('BlueprintNativeGeometryProbe.CombineBlockPaletteToGeometry=sys._water_duplicate_original\nb.geometry=sys._water_duplicate_geometry\n_result=True')
                    if check.navigation()['open']:
                        check.run('navigator.pop()\n_result=True')
                        check.wait('close', lambda row: not row['open'] and not row['transition'], check.navigation)
                    check.run(product.RESTORE_PROFILE)
                    check.run('del sys._water_duplicate_strip\ndel sys._water_duplicate_calls\ndel sys._water_duplicate_original\ndel sys._water_duplicate_geometry\ndel sys._water_duplicate_geometry_serial\n_result=True')
                    report['restored'] = True
                except Exception as error:
                    report['cleanup_errors'].append(type(error).__name__ + ': ' + str(error))
            record()
    print(json.dumps({key: report[key] for key in ('completed', 'restored', 'cleanup_errors')}))
    return 0 if report['completed'] and report['restored'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
