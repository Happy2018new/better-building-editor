"""Capture custom block-actor pose transport without assuming renderer fields."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import uuid

from PIL import ImageChops, Image

from capture_native_window import capture
from context_test_environment import SETUP as ENVIRONMENT, RESTORE as RESTORE_ENVIRONMENT

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from mcdk import Client, return_value

BLOCK = 'modern_projection:liquid_payload_pose_poc'
CLIENT = '''import json,sys
import mod.client.extraClientApi as api
factory=api.GetEngineCompFactory()
level=api.GetLevelId()
'''
PREPARE = '''import json,math,sys
import mod.server.extraServerApi as api
assert not hasattr(sys,'_liquid_pose_world')
factory=api.GetEngineCompFactory()
player=api.GetPlayerList()[0]
dimension=factory.CreateDimension(player).GetEntityDimensionId()
assert dimension==0
foot=factory.CreatePos(player).GetFootPos()
origin=(int(math.floor(foot[0]))+6,min(int(math.floor(foot[1]))+24,300),int(math.floor(foot[2]))+6)
info=factory.CreateBlockInfo(player)
region=[(origin[0]+x,origin[1]+y,origin[2]+z) for x in range(-2,4) for y in range(-2,4) for z in range(-2,4)]
for pos in region:
 front=info.GetBlockNew(pos,dimension)
 back=info.GetLiquidBlock(pos,dimension)
 assert front and front.get('name')=='minecraft:air',(pos,front)
 assert back is None or back.get('name')=='minecraft:air',(pos,back)
sys._liquid_pose_world={'origin':origin,'region':region,'player':player,'dimension':dimension,'foot_before':foot}
assert info.SetBlockNew(origin,{'name':%r,'aux':0},0,dimension,True,False)
_result=json.dumps({'origin':origin,'player':player,'dimension':dimension,'region':region,
 'placed':info.GetBlockNew(origin,dimension),'nbt':info.GetBlockEntityData(dimension,origin)})
'''
NEAR_PLAYER = '''import json,sys
import mod.server.extraServerApi as api
saved=sys._liquid_pose_world
origin=tuple(saved['origin'])
platform=(origin[0]-4,origin[1]-1,origin[2]-4)
info=api.GetEngineCompFactory().CreateBlockInfo(saved['player'])
before=info.GetBlockNew(platform,saved['dimension'])
assert before and before.get('name')=='minecraft:air',(platform,before)
back=info.GetLiquidBlock(platform,saved['dimension'])
assert back is None or back.get('name')=='minecraft:air',(platform,back)
saved['region'].append(platform)
assert info.SetBlockNew(platform,{'name':'minecraft:stone','aux':0},0,saved['dimension'],True,False)
point=(platform[0]+.5,platform[1]+1.,platform[2]+.5)
assert api.GetEngineCompFactory().CreatePos(saved['player']).SetFootPos(point)
_result=json.dumps({'before':saved['foot_before'],'after':point,'platform':platform})
'''
REPLICATION = '''origin=%r
palette=factory.CreateBlock(level).GetBlockPaletteBetweenPos(origin,origin,False)
raw=palette.SerializeBlockPalette() if palette is not None else {}
materials=[{'name':key[0],'aux':key[1],'indices':indices} for key,indices in raw.get('common',{}).items()]
_result=json.dumps({'foot':factory.CreatePos(api.GetLocalPlayerId()).GetFootPos(),'materials':materials})
'''
SAVE = '''assert not hasattr(sys,'_liquid_pose_client')
cam=factory.CreateCamera(level)
sys._liquid_pose_client={'origin':%r,'entity':None,'attached':None,
 'standalone':None,
 'camera_pos':cam.GetPosition(),'camera_rot':cam.GetCameraRotation(),
 'pitch_lock':cam.IsModCameraLockPitch(),'yaw_lock':cam.IsModCameraLockYaw()}
_result=True
'''
READ = '''saved=sys._liquid_pose_client
origin=tuple(saved['origin'])
block=factory.CreateBlock(level)
palette=block.GetBlockPaletteBetweenPos(origin,origin,False)
raw=palette.SerializeBlockPalette() if palette is not None else None
def tagged(value):
 if isinstance(value,dict):return {'type':'dict','items':[[tagged(k),tagged(v)] for k,v in sorted(value.items(),key=lambda item:repr(item[0]))]}
 if isinstance(value,(tuple,list)):return {'type':'tuple' if isinstance(value,tuple) else 'list','items':[tagged(v) for v in value]}
 if isinstance(value,str):return {'type':'bytes','value':value.decode('utf8')}
 if isinstance(value,unicode):return {'type':'unicode','value':value}
 if value is None or isinstance(value,(bool,int,long,float)):return {'type':type(value).__name__,'value':value}
 raise TypeError(repr(type(value)))
saved['raw']=raw
_result=json.dumps({'exists':palette is not None,'raw':tagged(raw)})
'''
TRANSFORM = '''origin=tuple(sys._liquid_pose_client['origin'])
info=factory.CreateBlockInfo(level)
operations=%r
rows=[]
for method,args in operations:
 returned=getattr(info,method)(origin,*args)
 rows.append({'method':method,'args':args,'returned':returned})
_result=json.dumps(rows)
'''
SPAWN_STANDALONE = '''saved=sys._liquid_pose_client
saved['standalone']=api.GetSystem('ModernProjection','ModernProjectionClientSystem').CreateClientEntityByTypeStr(
 %r,tuple(saved['origin']),(0.,0.))
assert saved['standalone']
render=factory.CreateActorRender(saved['standalone'])
assert render.SetNotRenderAtAll(False)
_result=json.dumps({'entity':saved['standalone']})
'''
REMOVE_STANDALONE = '''saved=sys._liquid_pose_client
if saved['standalone']:
 api.GetSystem('ModernProjection','ModernProjectionClientSystem').DestroyClientEntity(saved['standalone'])
 saved['standalone']=None
_result=True
'''
GENERATE = '''saved=sys._liquid_pose_client
origin=tuple(saved['origin'])
name=%r
position=%r
block=factory.CreateBlock(level)
live=block.GetBlockPaletteBetweenPos(origin,origin,False)
raw=live.SerializeBlockPalette()
if any(position):
 assert tuple(raw['volume'])==(1,1,1) and not raw.get('actor')
 assert all(indices==[0] for indices in raw['common'].values())
 x,y,z=position
 sx,sy,sz=x+1,y+1,z+1
 index=(y*sx+x)*sz+z
 raw=dict(raw,volume=(sz,sx,sy),common=dict((key,[index]) for key in raw['common']))
 live=block.GetBlankBlockPalette()
 assert live.DeserializeBlockPalette(raw)
copy=block.GetBlankBlockPalette()
deserialized=copy.DeserializeBlockPalette(raw)
geometry=factory.CreateBlockGeometry(level)
paths=[]
for key,palette in (('live',live),('roundtrip',copy)):
 requested=name+'_'+key
 returned=geometry.CombineBlockPaletteToGeometry(palette,requested,0) if key=='live' or deserialized else None
 paths.append({'path':key,'requested':requested,'returned':returned})
saved['paths']=paths
saved['entity']=api.GetSystem('ModernProjection','ModernProjectionClientSystem').CreateClientEntityByTypeStr('modern_projection:anchor',origin,(0.,0.))
assert saved['entity']
_result=json.dumps({'deserialized':deserialized,'roundtrip_equal':copy.SerializeBlockPalette()==raw,
 'paths':paths,'entity':saved['entity'],'carrier_position':position,
 'source':'constructed_from_live_single_cell' if any(position) else 'native_live_single_cell'})
'''
ATTACH = '''saved=sys._liquid_pose_client
render=factory.CreateActorRender(saved['entity'])
if saved['attached'] is not None:
 assert render.DeleteActorBlockGeometry(saved['attached'])
 saved['attached']=None
path=next(row for row in saved['paths'] if row['path']==%r)
if path['returned'] is not None:
 name=path['returned']
 assert render.AddActorBlockGeometry(name,%r,(0.,180.,0.))
 saved['attached']=name
 assert render.EnableActorBlockGeometryTransparent(name,True)
 assert render.SetActorBlockGeometryTransparency(name,1.)
 assert render.SetEntityExtraUniforms(4,%r)
 for group,value in %r:
  assert render.SetEntityExtraUniforms(group,value)
 assert render.SetNotRenderAtAll(False)
_result=json.dumps({'attached':saved['attached']})
'''
CAMERA = '''origin=tuple(sys._liquid_pose_client['origin'])
target=(origin[0]+.5,origin[1]+.5,origin[2]+.5)
offset=(3.,3.,5.)
position=tuple(target[i]+offset[i] for i in range(3))
direction=api.GetRotFromDir(tuple(target[i]-position[i] for i in range(3)))
rotation=(direction[0],direction[1]+180.,0.)
cam=factory.CreateCamera(level)
cam.DepartCamera();cam.LockModCameraPitch(True);cam.LockModCameraYaw(True)
assert cam.SetCameraPos(position) and cam.SetCameraRotation(rotation)
_result=json.dumps({'position':position,'rotation':rotation,'target':target})
'''
CAMERA_CHECK = '''cam=factory.CreateCamera(level)
origin=tuple(sys._liquid_pose_client['origin'])
target=tuple(axis+.5 for axis in origin)
_result=json.dumps({'position':cam.GetPosition(),'rotation':cam.GetCameraRotation(),
 'target':target,'target_screen':cam.WorldToScreenPoint(*target) if hasattr(cam,'WorldToScreenPoint') else None,
 'native_target_projection_available':hasattr(cam,'WorldToScreenPoint'),
 'screen':factory.CreateGame(level).GetScreenSize()})
'''
CLEAR = '''import json,sys
import mod.server.extraServerApi as api
saved=sys._liquid_pose_world
info=api.GetEngineCompFactory().CreateBlockInfo(saved['player'])
assert info.SetBlockNew(tuple(saved['origin']),{'name':'minecraft:air','aux':0},0,saved['dimension'],True,False)
_result=True
'''
CLEAN_CLIENT = '''saved=getattr(sys,'_liquid_pose_client',None)
if saved is not None:
 if saved['entity']:api.GetSystem('ModernProjection','ModernProjectionClientSystem').DestroyClientEntity(saved['entity'])
 if saved['standalone']:api.GetSystem('ModernProjection','ModernProjectionClientSystem').DestroyClientEntity(saved['standalone'])
 cam=factory.CreateCamera(level)
 cam.ResetCameraPos();cam.UnDepartCamera()
 assert cam.SetCameraRotation(saved['camera_rot'])
 cam.LockModCameraPitch(saved['pitch_lock']);cam.LockModCameraYaw(saved['yaw_lock'])
 del sys._liquid_pose_client
_result=True
'''
CLEAN_WORLD = '''import json,sys
import mod.server.extraServerApi as api
saved=getattr(sys,'_liquid_pose_world',None)
rows=[]
if saved is not None:
 info=api.GetEngineCompFactory().CreateBlockInfo(saved['player'])
 assert api.GetEngineCompFactory().CreatePos(saved['player']).SetFootPos(tuple(saved['foot_before']))
 for pos in saved['region']:
  before=info.GetBlockNew(tuple(pos),saved['dimension'])
  if before.get('name')!='minecraft:air':
   assert info.SetBlockNew(tuple(pos),{'name':'minecraft:air','aux':0},0,saved['dimension'],True,False)
  after=info.GetBlockNew(tuple(pos),saved['dimension'])
  rows.append({'pos':pos,'after':after})
 assert all(row['after'].get('name')=='minecraft:air' for row in rows)
 del sys._liquid_pose_world
_result=json.dumps({'restored':True,'rows':rows})
'''


def run(client, code, server=False):
    value = return_value(client.call('execute_code', {'code': code if server else CLIENT + code,
                                 'is_client': not server, 'direct_return': True}))
    return json.loads(value) if isinstance(value, str) else value


def write(path, report):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=True, indent=2) + '\n', encoding='ascii')


def difference(first, second, destination):
    with Image.open(first).convert('RGB') as a, Image.open(second).convert('RGB') as b:
        assert a.size == b.size
        delta = ImageChops.difference(a, b)
        delta.save(destination)
        maximum = ImageChops.lighter(ImageChops.lighter(*delta.split()[:2]), delta.split()[2])
        crop = (a.width // 4, a.height // 4, a.width * 3 // 4, a.height * 3 // 4)
        histogram = maximum.crop(crop).histogram()
        return {'center_pixels_gt_12': sum(histogram[13:]),
                'path': str(destination.resolve()), 'sha256': hashlib.sha256(destination.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--capture-exe', type=Path, required=True)
    parser.add_argument('--block', default=BLOCK, help='Ordinary stone is a camera positive control')
    parser.add_argument('--actor-uniform', nargs=4, type=float, default=(19487., 0., 0., 0.),
                        metavar=('TAG', 'Y', 'Z', 'W'), help='Explicit isolated shader discriminator')
    parser.add_argument('--carrier-address', type=int, default=0,
                        help='Construct a sparse palette from one native cell at this Y address')
    parser.add_argument('--carrier-position', nargs=3, type=int,
                        help='Explicit sparse palette XYZ; independent from logical cell position')
    parser.add_argument('--attachment-offset', nargs=3, type=float,
                        help='Explicit offset; default recenters the Y-address compatibility mode')
    parser.add_argument('--uniform-payload', type=Path,
                        help='JSON object containing explicit uniforms 1..3 as four numeric components each')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('The report must be fresh: ' + str(args.output))
    if not 0 <= args.carrier_address <= 447:
        parser.error('The isolated carrier address must be in 0..447')
    if args.carrier_position is not None and args.carrier_address:
        parser.error('Choose --carrier-position or --carrier-address')
    position = tuple(args.carrier_position or (0, args.carrier_address, 0))
    if any(axis < 0 or axis > 447 for axis in position):
        parser.error('The isolated XYZ position must be in 0..447')
    attachment = tuple(args.attachment_offset or (-.5, -float(args.carrier_address), -.5))
    payload = json.loads(args.uniform_payload.read_bytes()) if args.uniform_payload else {}
    if any(key not in ('1', '2', '3') or not isinstance(value, list) or len(value) != 4 or
           any(isinstance(component, bool) or not isinstance(component, (int, float)) for component in value)
           for key, value in payload.items()):
        parser.error('Explicit payload groups must be 1..3, with four numeric components')
    uniforms = [(int(key), tuple(value)) for key, value in sorted(payload.items())]
    args.capture_exe = args.capture_exe.resolve(strict=True)
    os.environ['MCDEV_SESSION_FILE'] = str(Path(args.session).resolve(strict=True))
    os.environ['MCDEV_OWNER'] = args.owner
    report = {'schema': 1, 'completed': False, 'restored': False, 'native_pose_accepted': False,
              'native_geometry_accepted': False, 'accuracy_accepted': False,
              'production_memory_accepted': False, 'animated_sampling_accepted': False,
              'scope': 'Isolated custom actor transport; no native liquid height rule', 'rows': [],
              'carrier_address': args.carrier_address, 'actor_uniform': args.actor_uniform,
              'carrier_position': position, 'attachment_offset': attachment,
              'uniform_payload': payload,
              'probe_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    with Client(timeout=45) as client:
        try:
            report['environment'] = run(client, ENVIRONMENT, True)
            report['world_setup'] = run(client, PREPARE % args.block, True)
            origin = tuple(report['world_setup']['origin'])
            report['near_player'] = run(client, NEAR_PLAYER, True)
            expected_foot = report['near_player']['after']
            deadline = time.monotonic() + 10.
            while True:
                replica = run(client, REPLICATION % (origin,))
                ready = (replica['foot'] is not None and
                         all(abs(replica['foot'][i] - expected_foot[i]) < .1 for i in range(3)) and
                         any(row['name'] == args.block and row['aux'] == 0 and row['indices'] == [0]
                             for row in replica['materials']))
                if ready or time.monotonic() >= deadline:
                    break
                time.sleep(.2)
            report['replication'] = dict(replica, ready=ready)
            assert ready, report['replication']
            report['saved'] = run(client, SAVE % (origin,))
            time.sleep(3.)
            report['camera'] = run(client, CAMERA)
            time.sleep(2.)
            report['camera_check'] = run(client, CAMERA_CHECK)
            report['baseline'] = run(client, READ)
            def frame(label):
                target = args.output.with_name(args.output.stem + '_' + label + '.png')
                return capture(args.session, args.owner, target, args.capture_exe)
            report['baseline_shown'] = frame('baseline')
            if args.block == BLOCK:
                for label, identifier in (('entity_control', 'modern_projection:liquid_payload_entity_control_poc'),
                                          ('standalone', BLOCK)):
                    report[label] = run(client, SPAWN_STANDALONE % identifier)
                    time.sleep(.5)
                    report[label + '_shown'] = frame(label)
                    report[label + '_removed'] = run(client, REMOVE_STANDALONE)
            operations = [('SetBlockEntityModelScale', [(1., 4., .5)]),
                          ('SetBlockEntityModelRotation', [30., 'x']),
                          ('SetBlockEntityModelRotation', [20., 'y']),
                          ('SetBlockEntityModelPosOffset', [(.25, .125, -.25)])]
            if args.block != BLOCK:
                operations = []
            for operation in operations:
                row = {'operation': operation, 'returned': run(client, TRANSFORM % ([operation],))}
                time.sleep(.25)
                row['palette'] = run(client, READ)
                row['shown'] = frame('step_' + str(len(report['rows'])))
                report['rows'].append(row)
                write(args.output, report)
            report['world_shown'] = frame('world')
            report['geometry'] = run(client, GENERATE % ('liquid_pose_' + uuid.uuid4().hex, position))
            report['source_cleared'] = run(client, CLEAR, True)
            time.sleep(.5)
            report['world_hidden'] = frame('empty')
            for key in ('live', 'roundtrip'):
                row = {'attachment': run(client, ATTACH % (key, attachment, tuple(args.actor_uniform), uniforms))}
                time.sleep(.4)
                row['shown'] = frame(key)
                if key == 'live':
                    time.sleep(1.1)
                    row['animation_later'] = frame(key + '_later')
                row['signal'] = difference(row['shown']['path'], report['world_hidden']['path'],
                    args.output.with_name(args.output.stem + '_' + key + '_signal.png'))
                report[key] = row
                write(args.output, report)
            report['world_signal'] = difference(report['world_shown']['path'], report['world_hidden']['path'],
                args.output.with_name(args.output.stem + '_world_signal.png'))
            report['completed'] = True
        except Exception as error:
            report['error'] = '%s: %s' % (type(error).__name__, error)
            raise
        finally:
            restore_environment = ('import sys\nif hasattr(sys, "_context_environment_saved"):\n' +
                                   ''.join(' ' + line + '\n' for line in RESTORE_ENVIRONMENT.splitlines()) +
                                   'else:\n _result=True\n')
            cleanup_errors = []
            for key, code, server in (('client_cleanup', CLEAN_CLIENT, False),
                                      ('world_cleanup', CLEAN_WORLD, True),
                                      ('environment_cleanup', restore_environment, True)):
                try:
                    report[key] = run(client, code, server)
                except Exception as error:
                    report[key] = False
                    cleanup_errors.append({'step': key, 'error': '%s: %s' % (type(error).__name__, error)})
            report['cleanup_errors'] = cleanup_errors
            world_cleanup = report['world_cleanup']
            report['restored'] = bool(report['client_cleanup'] and isinstance(world_cleanup, dict) and
                                      world_cleanup.get('restored') and report['environment_cleanup'])
            write(args.output, report)
            if cleanup_errors:
                raise RuntimeError('Native fixture cleanup failed: ' + repr(cleanup_errors))
    print(json.dumps({'completed': report['completed'], 'restored': report['restored'],
                      'geometry': report['geometry'], 'output': str(args.output.resolve())}))
    return 0 if report['completed'] and report['restored'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
