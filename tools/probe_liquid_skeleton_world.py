"""Native free-skeleton placement/artwork controls next to ordinary stone."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

import probe_liquid_pose_channel as base
import probe_liquid_uniform_transport as transport
from _session import load_session

STONES = '''import json,sys
import mod.server.extraServerApi as api
saved=sys._liquid_pose_world
info=api.GetEngineCompFactory().CreateBlockInfo(saved['player'])
origin=saved['origin']
positions=[tuple(origin[i]+offset[i] for i in range(3)) for offset in ((0,0,2),(2,0,0),(2,0,2))]
for position in positions:
 assert position in saved['region']
 assert info.SetBlockNew(position,{'name':'minecraft:stone','aux':0},0,saved['dimension'],True,False)
_result=json.dumps({'stone_positions':[origin]+positions})
'''
REFERENCE = '''import sys,json
import mod.server.extraServerApi as api
saved=sys._liquid_pose_world
info=api.GetEngineCompFactory().CreateBlockInfo(saved['player'])
positions,visible=%r
rows=[]
for offset in positions:
 position=tuple(saved['origin'][i]+offset[i] for i in range(3))
 assert position in saved['region']
 name='minecraft:stone' if visible else 'minecraft:air'
 assert info.SetBlockNew(position,{'name':name,'aux':0},0,saved['dimension'],True,False)
 rows.append({'position':position,'name':name})
_result=json.dumps(rows)
'''
CAMERA = '''origin=tuple(sys._liquid_pose_client['origin'])
target=(origin[0]+2.,origin[1]+.5,origin[2]+1.5)
position=tuple(target[i]+(6.,5.,8.)[i] for i in range(3))
direction=api.GetRotFromDir(tuple(target[i]-position[i] for i in range(3)))
rotation=(direction[0],direction[1]+180.,0.)
cam=factory.CreateCamera(level)
cam.DepartCamera();cam.LockModCameraPitch(True);cam.LockModCameraYaw(True)
assert cam.SetCameraPos(position) and cam.SetCameraRotation(rotation)
_result=json.dumps({'position':position,'rotation':rotation,'target':target,'offset':(6.,5.,8.)})
'''
CREATE = '''saved=sys._liquid_pose_client
assert not saved.get('free_ids')
saved['free_ids']=[]
model=factory.CreateModel(level)
rows=[]
origin=saved['origin']
center=tuple(axis+2. for axis in origin)
names,scale,rotation=%r
for name in names:
 model_id=model.CreateFreeModel(name,0)
 assert model_id
 saved['free_ids'].append(model_id)
 assert model.SetFreeModelScale(model_id,scale,scale,scale)
 assert model.SetFreeModelBoundingBox(model_id,(-4.,-4.,-4.),(4.,4.,4.))
 assert model.SetFreeModelRot(model_id,*rotation)
 assert model.SetFreeModelPos(model_id,*center)
 rows.append({'model':name,'model_id':model_id,'center':center,'scale':(scale,)*3,
  'rotation':rotation,'bounding_box':((-4.,-4.,-4.),(4.,4.,4.))})
assert len(set(saved['free_ids']))==2
_result=json.dumps(rows)
'''
PAYLOAD = '''from collections import namedtuple
from modern_projection.projection import biomes
from modern_projection.projection.liquid_transport import pack_group
Surface=namedtuple('WorldWaterSurface','position layer heights faces texture_key flow_uv')
height,opacity,faces,positions,black=%r
color,native_opacity=biomes.water_appearance('plains')
if black:color,native_opacity=(0,0,0),1.
rows=[]
model=factory.CreateModel(None)
for model_id,cells in zip(sys._liquid_pose_client['free_ids'],positions):
 surfaces=tuple(Surface(position,0,(height,)*4,faces,'still_water_grey',None) for position in cells)
 payload=pack_group((0,0,0),surfaces,color,native_opacity,opacity)
 for index,value in enumerate(payload,1):assert model.SetExtraUniformValue(model_id,index,value)
 rows.append({'model_id':model_id,'local_positions':cells,'uniforms':payload})
_result=json.dumps(rows)
'''
CHECK = '''saved=sys._liquid_pose_client
origin=saved['origin']
cam=factory.CreateCamera(level)
points=[tuple(origin[i]+offset[i] for i in range(3)) for offset in ((.5,.5,.5),(1.5,.5,.5),(2.5,.5,.5),(3.5,.5,.5))]
_result=json.dumps({'camera_position':cam.GetPosition(),'camera_rotation':cam.GetCameraRotation(),
 'screen':factory.CreateGame(level).GetScreenSize(),'centers':points,
 'projected_centers':[cam.WorldToScreenPoint(*point) for point in points] if hasattr(cam,'WorldToScreenPoint') else None,
 'free_ids':saved['free_ids']})
'''
CLEAN_FREE = '''saved=getattr(sys,'_liquid_pose_client',None)
rows=[]
if saved is not None:
 model=factory.CreateModel(None)
 for model_id in list(saved.get('free_ids',())):
  returned=model.RemoveFreeModel(model_id)
  assert returned,(model_id,returned)
  saved['free_ids'].remove(model_id)
  rows.append({'model_id':model_id,'removed':returned})
_result=json.dumps({'removed':rows,'remaining':saved.get('free_ids',[]) if saved is not None else []})
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--capture-exe', type=Path, required=True)
    parser.add_argument('--model-name', action='append')
    parser.add_argument('--scale', type=float, default=1.)
    parser.add_argument('--rotation', type=float, nargs=3, default=(0., 0., 0.))
    parser.add_argument('--reference-cells', action='store_true')
    parser.add_argument('--raised-cells', action='store_true')
    parser.add_argument('--black', action='store_true')
    parser.add_argument('--reverse-z', action='store_true')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh report')
    names = tuple(args.model_name or ('modern_projection_liquid_still_water_grey',
                                     'modern_projection_liquid_still_water_grey_frozen'))
    if len(names) != 2 or args.scale <= 0.:
        parser.error('Supply exactly two models and a positive scale')
    cells = (((1, 0, 0), (1, 1 if args.raised_cells else 0, 2)),
             ((3, 0, 0), (3, 2 if args.raised_cells else 0, 2)))
    encoded_cells = tuple(tuple((x, y, 3 - z) for x, y, z in row) for row in cells) if args.reverse_z else cells
    os.environ.update(MCDEV_SESSION_FILE=str(Path(args.session).resolve(strict=True)), MCDEV_OWNER=args.owner)
    session = load_session(args.session, args.owner, live=True)
    if Path(session['project']).resolve() != base.ROOT:
        parser.error('The session belongs to another project')
    report = {'schema': 1, 'completed': False, 'restored': False, 'captures': {}, 'observations': {},
              'metrics': [], 'cleanup_errors': [], 'probe_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'scope': 'Native CreateFreeModel skeleton API and supplied-size placement candidate',
              'native_shape_accepted': False, 'native_uv_accepted': False, 'native_alpha_accepted': False,
              'world_skeleton_placement_accepted': False, 'production_world_accepted': False,
              'production_memory_accepted': False}

    def record():
        base.write(args.output, report)

    def frame(label):
        report['captures'][label] = base.capture(args.session, args.owner,
            args.output.with_name(args.output.stem + '_' + label + '.png'), args.capture_exe)
        record()

    with base.Client(timeout=45) as client:
        try:
            report['metrics'].append(dict(transport.metrics(args.session, args.owner), label='before_setup'))
            report['environment'] = base.run(client, base.ENVIRONMENT, True)
            report['world_setup'] = base.run(client, base.PREPARE % 'minecraft:stone', True)
            origin = tuple(report['world_setup']['origin'])
            report['stones'] = base.run(client, STONES, True)
            report['near_player'] = base.run(client, base.NEAR_PLAYER, True)
            time.sleep(2.)
            report['saved'] = base.run(client, base.SAVE % (origin,))
            report['camera'] = base.run(client, CAMERA)
            time.sleep(.5)
            frame('stones')
            if args.reference_cells:
                stakes = ((0, 0, 0), (0, 0, 2), (2, 0, 0), (2, 0, 2))
                report['stakes_cleanup'] = base.run(client, REFERENCE % ((stakes, False),), True)
                time.sleep(.3)
                frame('reference_empty')
                positions = tuple(position for row in cells for position in row)
                report['reference_cells'] = base.run(client, REFERENCE % ((positions, True),), True)
                time.sleep(.3)
                frame('reference_cells')
                report['reference_cleanup'] = base.run(client, REFERENCE % ((positions, False),), True)
                time.sleep(.3)
                frame('reference_restored')
            report['free_models'] = base.run(client, CREATE % ((names, args.scale, tuple(args.rotation)),))
            report['coordinates'] = base.run(client, CHECK)
            time.sleep(.2)
            frame('default_zero')
            for label, values in (('full_height', (1., 1., 63)), ('height70', (.7, 1., 63)),
                                  ('half', (.7, .5, 63)), ('top', (.7, 1., 1)), ('hidden', (.7, 0., 63))):
                report['observations'][label] = base.run(client, PAYLOAD % (values + (encoded_cells, args.black),))
                time.sleep(.3)
                frame(label)
                if label in ('full_height', 'height70'):
                    time.sleep(.7)
                    frame(label + '_later')
            report['metrics'].append(dict(transport.metrics(args.session, args.owner), label='after_frames'))
            report['completed'] = True
        except Exception as error:
            report['error'] = '%s: %s' % (type(error).__name__, error)
            raise
        finally:
            restore_environment = ('import sys\nif hasattr(sys,"_context_environment_saved"):\n' +
                '\n'.join(' ' + line for line in base.RESTORE_ENVIRONMENT.splitlines()) + '\nelse:_result=True')
            for label, code, server in (('free_cleanup', CLEAN_FREE, False), ('client_cleanup', base.CLEAN_CLIENT, False),
                                        ('world_cleanup', base.CLEAN_WORLD, True), ('environment_cleanup', restore_environment, True)):
                try:
                    report[label] = base.run(client, code, server)
                except Exception as error:
                    report['cleanup_errors'].append('%s: %s: %s' % (label, type(error).__name__, error))
                record()
            report['restored'] = bool(not report['cleanup_errors'] and report.get('world_cleanup', {}).get('restored')
                                      and report.get('free_cleanup', {}).get('remaining') == [])
            report['metrics'].append(dict(transport.metrics(args.session, args.owner), label='after_cleanup'))
            record()
    print(json.dumps({'completed': report['completed'], 'restored': report['restored'],
                      'captures': len(report['captures']), 'output': str(args.output.resolve())}))
    return 0 if report['completed'] and report['restored'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
