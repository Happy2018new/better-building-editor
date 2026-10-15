"""Capture untouched native pots before NBT or the first projection.

Run in a fresh owned disposable instance through run_live_check.py. Both native
placement controls are captured before any fixture NBT, state/layer alignment,
editor opening or projection. Missing client fields are evidence, not a reason
to skip later independent captures. This does not certify a material cause.
"""
import argparse
import hashlib
import json
import os
import time
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

from camera_projection import project_box_corners
from context_test_environment import SETUP as ENVIRONMENT, RESTORE as RESTORE_ENVIRONMENT
from verify_debug_blueprints import Client, write_json
from verify_missing_neighbor_visuals import camera_matches, hull, maximum
from verify_native_entity_appearances import execute
from verify_native_pot_fields import SHERDS
from verify_sign_visuals import SignCheck

CLIENT = '''import json,sys
import mod.client.extraClientApi as api
factory=api.GetEngineCompFactory()
level=api.GetLevelId()
'''

COLD_STATE = '''owner=api.GetSystem('ModernProjection','ModernProjectionClientSystem')
assert owner is not None and owner.bridge is not None and owner.session is not None
b,s=owner.bridge,owner.session
module=sys.modules.get('modern_projection.pyreact')
nav=getattr(module,'navigator',None)
state={'projection_serial':b.projection_serial,'entity':b.entity,
 'projection_entities':dict(b.projection_entities),'preparing_entity':b.preparing_entity,
 'projection_work':b.projection_work is not None,'projection_shader':b.projection_shader is not None,
 'projection_occupancy':b.projection_occupancy is not None,'projection_active':s.projection_active,
 'projection_requested':b.projection_requested,'model_name':s.model_name,'models':len(b.models),
 'bootstrap_context_models':len(getattr(b,'context_models',{})),
 'bootstrap_model_layouts':len(getattr(b,'model_layouts',{})),
 'workspace_open':bool(nav and nav.contains('modern_projection_workspace')),
 'navigation_top':nav.top.key if nav and nav.top else None,
 'navigator_transitioning':bool(nav and nav.is_transitioning)}
state['cold']=(state['projection_serial']==0 and not any(state[key] for key in
 ('entity','projection_entities','preparing_entity','projection_work','projection_shader',
  'projection_occupancy','projection_active','projection_requested','models',
  'workspace_open','navigation_top','navigator_transitioning')))
_result=json.dumps(state)
'''

SETUP = '''import json,math,sys
import mod.server.extraServerApi as api
assert not hasattr(sys,'_cold_native_actor_saved'),'Previous cold probe needs cleanup'
factory=api.GetEngineCompFactory()
player=api.GetPlayerList()[0]
dimension=factory.CreateDimension(player).GetEntityDimensionId()
assert dimension==0,'Cold probe requires the owned overworld'
position=factory.CreatePos(player)
rotation=factory.CreateRot(player)
foot=position.GetFootPos()
height=min(int(math.floor(foot[1]))+24,300)
base=(int(math.floor(foot[0]))+8,height,int(math.floor(foot[2]))+8)
targets={'item':base,'set_block':(base[0]+4,base[1],base[2])}
platform=(base[0]+2,base[1]-1,base[2]+6)
supports=[(pos[0],pos[1]-1,pos[2]) for pos in targets.values()]
reserved=set(supports+[platform])
for target in targets.values():
 for dx in (-1,0,1):
  for dy in (0,1,2):
   for dz in (-1,0,1):reserved.add((target[0]+dx,target[1]+dy,target[2]+dz))
info=factory.CreateBlockInfo(player)
for pos in reserved:
 before=info.GetBlockNew(pos,dimension)
 assert before and before.get('name')=='minecraft:air',(pos,before)
 liquid=info.GetLiquidBlock(pos,dimension)
 assert liquid is None or liquid.get('name')=='minecraft:air',(pos,liquid)
items=factory.CreateItem(player)
kind=api.GetMinecraftEnum().ItemPosType.INVENTORY
slot=None
for candidate in range(36):
 item=items.GetPlayerItem(kind,candidate,True)
 if not item or not item.get('count'):
  slot=candidate
  break
assert slot is not None,'Cold native item control needs an empty inventory slot'
saved={'player':player,'dimension':dimension,'foot_before':foot,'rotation_before':rotation.GetRot(),
 'slot':slot,'targets':targets,'supports':supports,'platform':platform,'reserved':list(reserved),
 'nbt_writes':0,'native_writes':[]}
sys._cold_native_actor_saved=saved
for pos in supports+[platform]:
 assert info.SetBlockNew(pos,{'name':'minecraft:stone','aux':0},0,dimension,True,False)
assert position.SetFootPos((platform[0]+.5,platform[1]+1.,platform[2]+.5))
_result=json.dumps(saved)
'''

PLACE = '''import json,sys
import mod.server.extraServerApi as api
saved=sys._cold_native_actor_saved
key,method=%r,%r
target=tuple(saved['targets'][key])
factory=api.GetEngineCompFactory()
info=factory.CreateBlockInfo(saved['player'])
assert saved['nbt_writes']==0,'Both untouched controls must precede every NBT write'
assert info.GetBlockNew(target,saved['dimension']).get('name')=='minecraft:air'
if method=='PlayerUseItemToPos':
 items=factory.CreateItem(saved['player'])
 assert factory.CreateRot(saved['player']).SetRot((0.,180.))
 assert items.SpawnItemToPlayerInv({'itemName':'minecraft:decorated_pot'.encode('utf8'),'count':1,'auxValue':0},saved['player'],saved['slot'])
 support=(target[0],target[1]-1,target[2])
 result=info.PlayerUseItemToPos(support,api.GetMinecraftEnum().ItemPosType.INVENTORY,saved['slot'],1)
 items.SetInvItemNum(saved['slot'],0)
else:
 assert method=='SetBlockNew',method
 result=info.SetBlockNew(target,{'name':'minecraft:decorated_pot','aux':0},0,saved['dimension'],True,False)
saved['native_writes'].append({'key':key,'method':method,'returned':result})
_result=json.dumps({'method':method,'returned':result,'position':target,
 'foreground':info.GetBlockNew(target,saved['dimension']),
 'states':factory.CreateBlockState(api.GetLevelId()).GetBlockStates(target,saved['dimension']),
 'liquid':info.GetLiquidBlock(target,saved['dimension']),
 'nbt':info.GetBlockEntityData(saved['dimension'],target),
 'state_writes':0,'liquid_writes':0,'nbt_writes':saved['nbt_writes']})
'''

READ_SERVER = '''import json,sys
import mod.server.extraServerApi as api
saved=sys._cold_native_actor_saved
factory=api.GetEngineCompFactory()
info=factory.CreateBlockInfo(saved['player'])
target=tuple(saved['targets'][%r])
_result=json.dumps({'foreground':info.GetBlockNew(target,saved['dimension']),
 'states':factory.CreateBlockState(api.GetLevelId()).GetBlockStates(target,saved['dimension']),
 'liquid':info.GetLiquidBlock(target,saved['dimension']),
 'nbt':info.GetBlockEntityData(saved['dimension'],target)})
'''

READ_CLIENT = '''target,expected=%r,%r
palette=factory.CreateBlock(level).GetBlockPaletteBetweenPos(target,target,False)
source=palette.SerializeBlockPalette() if palette is not None else {}
def text(value):
 return value.decode('utf8') if isinstance(value,bytes) else value
materials=[{'material':(text(material[0]),material[1]),'indexes':indexes}
 for material,indexes in source.get('common',{}).items()]
actors=[{'name':text(name),'index':index,'fields':fields}
 for name,entries in source.get('actor',{}).items() for index,fields in entries.items()]
pot=next((row['fields'] for row in actors if row['name']=='minecraft:decorated_pot'),None)
shreds=[pot.get('decoratedPotShredNames'+str(index)) for index in range(4)] if pot else []
placed=any(row['material'][0]=='minecraft:decorated_pot' for row in materials)
ready=placed and pot is not None and (expected is None or shreds==list(expected))
_result=json.dumps({'ready':ready,'placed':placed,'actor_present':pot is not None,
 'volume':source.get('volume'),'common':materials,'actors':actors,'pot_sherds':shreds,
 'expected_sherds':expected})
'''

WRITE_NBT = '''import json,sys
import mod.server.extraServerApi as api
saved=sys._cold_native_actor_saved
key,sherds=%r,%r
target=tuple(saved['targets'][key])
info=api.GetEngineCompFactory().CreateBlockInfo(saved['player'])
nbt=info.GetBlockEntityData(saved['dimension'],target)
result={'requested_sherds':sherds,'accepted':False,'nbt_before':json.loads(json.dumps(nbt)),'position':target}
if nbt and nbt.get('id',{}).get('__value__')=='DecoratedPot':
 nbt['sherds']=[{'__type__':8,'__value__':name} for name in sherds]
 result['requested_nbt']=json.loads(json.dumps(nbt))
 result['accepted']=info.SetBlockEntityData(saved['dimension'],target,nbt)
 saved['nbt_writes']+=1
result['nbt_after']=info.GetBlockEntityData(saved['dimension'],target)
_result=json.dumps(result)
'''

SAVE_CAMERA = '''assert not hasattr(sys,'_cold_native_camera_saved')
cam=factory.CreateCamera(level)
view=factory.CreatePlayerView(level)
cloud_option=api.GetMinecraftEnum().OptionId.RENDER_CLOUDS
saved={'position':cam.GetPosition(),'rotation':cam.GetCameraRotation(),
 'pitch_lock':cam.IsModCameraLockPitch(),'yaw_lock':cam.IsModCameraLockYaw(),
 'clouds':view.GetToggleOption(cloud_option)}
sys._cold_native_camera_saved=saved
assert view.SetToggleOption(cloud_option,False)
_result=json.dumps(saved)
'''

POSE = '''cell,offset=%r,%r
target=tuple(cell[i]+.5 for i in range(3))
position=tuple(target[i]+offset[i] for i in range(3))
direction=api.GetRotFromDir(tuple(target[i]-position[i] for i in range(3)))
rotation=(direction[0],direction[1]+180.,0.)
cam=factory.CreateCamera(level)
cam.DepartCamera()
cam.LockModCameraPitch(True)
cam.LockModCameraYaw(True)
assert cam.SetCameraPos(position)
assert cam.SetCameraRotation(rotation)
_result=json.dumps({'position':position,'rotation':rotation,'target':target,'cell':cell})
'''

CAMERA = '''cam=factory.CreateCamera(level)
_result=json.dumps({'position':cam.GetPosition(),'rotation':cam.GetCameraRotation(),
 'screen':factory.CreateGame(level).GetScreenSize(),'fov':cam.GetFov()})
'''

PROJECTION = '''owner=api.GetSystem('ModernProjection','ModernProjectionClientSystem')
b,s=owner.bridge,owner.session
assert b.projection_serial==0 and not b.entity and not b.projection_entities
assert not hasattr(sys,'_cold_native_projection_saved')
fields=('origin','opacity','projection_missing','projection_outline','name','model_name',
 'model_revision','content_revision','progress','preview_pending','preview_error')
sys._cold_native_projection_saved={'editor':s.editor,'fields':dict((name,getattr(s,name)) for name in fields)}
from modern_projection.projection.model import Document,Editor
from modern_projection.projection.debug_blueprints import build
from modern_projection.projection.debug_pot_blueprints import CASES
from modern_projection.projection.cell import rebase
source=build('test.entities.pottery')
point=CASES[0]['position']
doc=Document((1,1,1),name='Cold native material projection control')
doc.blocks[(0,0,0)]=rebase(source.get(point),tuple(-value for value in point))
s.editor=Editor(doc)
s.origin=%r
s.opacity=1.
s.projection_missing=False
s.projection_outline=False
b.project()
_result=json.dumps({'origin':s.origin,'serial':b.projection_serial,'document_cells':len(doc.blocks),
 'editor_opened':False,'editor_model_refresh':False})
'''

PROJECTION_STATUS = '''owner=api.GetSystem('ModernProjection','ModernProjectionClientSystem')
b,s=owner.bridge,owner.session
work=b.projection_work
_result=json.dumps({'active':s.projection_active,'ready':work is not None and work.ready,
 'error':work.error if work is not None else None,'entity':b.entity,
 'entities':list(b.projection_entities.values()),'preparing':bool(b.preparing_entity),
 'serial':b.projection_serial,'shader':b.projection_shader is not None,'mesh':b.projection_mesh})
'''

RESTORE_PROJECTION = '''saved=getattr(sys,'_cold_native_projection_saved',None)
if saved is not None:
 owner=api.GetSystem('ModernProjection','ModernProjectionClientSystem')
 b,s=owner.bridge,owner.session
 b.stop_projection()
 s.editor=saved['editor']
 for name,value in saved['fields'].items():setattr(s,name,value)
 del sys._cold_native_projection_saved
_result=True
'''

RESTORE_WORLD = '''import json,sys
import mod.server.extraServerApi as api
saved=getattr(sys,'_cold_native_actor_saved',None)
result={'restored':True}
if saved is not None:
 factory=api.GetEngineCompFactory()
 info=factory.CreateBlockInfo(saved['player'])
 items=factory.CreateItem(saved['player'])
 items.SetInvItemNum(saved['slot'],0)
 assert factory.CreateRot(saved['player']).SetRot(tuple(saved['rotation_before']))
 assert factory.CreatePos(saved['player']).SetFootPos(tuple(saved['foot_before']))
 for pos in list(saved['targets'].values())+saved['supports']+[saved['platform']]:
  info.SetBlockNew(tuple(pos),{'name':'minecraft:air','aux':0},0,saved['dimension'],True,False)
 remaining=[]
 for pos in saved['reserved']:
  block=info.GetBlockNew(tuple(pos),saved['dimension'])
  liquid=info.GetLiquidBlock(tuple(pos),saved['dimension'])
  if not block or block.get('name')!='minecraft:air' or (liquid and liquid.get('name')!='minecraft:air'):
   remaining.append({'position':pos,'foreground':block,'liquid':liquid})
 result={'restored':not remaining,'remaining':remaining,
  'player':factory.CreatePos(saved['player']).GetFootPos(),
  'rotation':factory.CreateRot(saved['player']).GetRot(),
  'slot':items.GetPlayerItem(api.GetMinecraftEnum().ItemPosType.INVENTORY,saved['slot'],True)}
 if not remaining:del sys._cold_native_actor_saved
_result=json.dumps(result)
'''

RESTORE_CAMERA = '''saved=getattr(sys,'_cold_native_camera_saved',None)
if saved is not None:
 cam=factory.CreateCamera(level)
 cam.ResetCameraPos()
 cam.UnDepartCamera()
 assert cam.SetCameraRotation(tuple(saved['rotation']))
 cam.LockModCameraPitch(saved['pitch_lock'])
 cam.LockModCameraYaw(saved['yaw_lock'])
 assert factory.CreatePlayerView(level).SetToggleOption(api.GetMinecraftEnum().OptionId.RENDER_CLOUDS,bool(saved['clouds']))
 del sys._cold_native_camera_saved
_result=True
'''


class ColdCheck(SignCheck):
    def __init__(self, client, output, timeout):
        super().__init__(client, output, timeout, native_resolution=True)

    def run(self, code):
        return execute(self.client, CLIENT + code, True)


def observe(check, code, timeout):
    deadline = time.monotonic() + timeout
    reads = 0
    while True:
        value = check.run(code)
        reads += 1
        if value.get('ready') or time.monotonic() >= deadline:
            return {'matched': bool(value.get('ready')), 'reads': reads, 'last': value,
                    'timed_out': not value.get('ready')}
        time.sleep(.2)


def capture_stage(check, target, offset, label, cold=False):
    requested = check.run(POSE % (tuple(target), tuple(offset)))
    stable = check.wait('cold native camera', lambda value: camera_matches(value, requested),
                        lambda: check.run(CAMERA))
    time.sleep(.4)
    state = check.run(COLD_STATE)
    if cold:
        assert state['cold'], state
    before = check.run(CAMERA)
    capture = check.capture(label)
    after = check.run(CAMERA)
    assert camera_matches(before, after), (before, after)
    assert before['screen'] == after['screen'], (before, after)
    return {'requested_camera': requested, 'camera': stable, 'camera_after': after,
            'client_state': state, 'capture': capture}


def analyze_body(stage, baseline, target, output, vertical_fov):
    shown, empty = stage['capture'], baseline['capture']
    for capture in (shown, empty):
        assert hashlib.sha256(Path(capture['path']).read_bytes()).hexdigest() == capture['sha256']
    assert camera_matches(stage['camera'], baseline['camera']), (stage, baseline)
    with Image.open(shown['path']) as first, Image.open(empty['path']) as second:
        image, background = first.convert('RGB'), second.convert('RGB')
    assert image.size == background.size, (image.size, background.size)
    pose = stage['requested_camera']
    corners = [(target[0]+x, target[1]+y, target[2]+z)
               for x in (.03,.97) for y in (0.,1.6) for z in (.03,.97)]
    points = project_box_corners(corners, pose['position'], pose['target'], image.size, vertical_fov)
    roi = Image.new('L', image.size)
    polygon = hull((row['screenX'], row['screenY']) for row in points)
    ImageDraw.Draw(roi).polygon(polygon, fill=255)
    delta = maximum(ImageChops.difference(image, background)).point(lambda value: 255 if value > 16 else 0)
    color = Image.new('L', image.size)
    color.putdata([255 if red > blue*1.1 and red > green*.9 else 0
                   for red, green, blue in image.getdata()])
    body = ImageChops.multiply(ImageChops.multiply(delta, color), roi)
    body.save(output)
    pixels = body.histogram()[255]
    return {'actor_pixels_above_16': pixels, 'mask': str(output.resolve()), 'roi': polygon,
            'threshold': 16, 'minimum_pixels': 80, 'positive_control_passed': pixels >= 80,
            'vertical_fov': vertical_fov,
            'limits': 'Existing brown actor mask and 80-pixel control; analytical ROI using prior native cube calibration. Appearance alone does not identify a cause.'}


def run_probe(check, report, output, args):
    state = check.run(COLD_STATE)
    report['initial_client_state'] = state
    assert state['cold'], state
    report['environment'] = execute(check.client, ENVIRONMENT)
    report.setdefault('events', []).append('environment_setup')
    report['camera_saved'] = check.run(SAVE_CAMERA)
    report['events'].append('camera_saved')
    report['setup'] = execute(check.client, SETUP)
    report['events'].append('world_reserved')
    time.sleep(args.weather_settle)
    targets = report['setup']['targets']
    for key in ('item', 'set_block'):
        report['controls'][key] = {'target': targets[key], 'stages': {}}
        report['controls'][key]['empty'] = capture_stage(check, targets[key], args.offset, key+'_empty', True)
        report['events'].append(key+'_empty_capture')
    for key, method in (('item', 'PlayerUseItemToPos'), ('set_block', 'SetBlockNew')):
        row = report['controls'][key]
        row['placement'] = execute(check.client, PLACE % (key, method))
        report['events'].append(key+'_native_write')
        row['placement_readback_passed'] = bool(row['placement']['returned'] and
                                              row['placement']['foreground'].get('name') == 'minecraft:decorated_pot')
        row['raw_replication'] = observe(check, READ_CLIENT % (tuple(targets[key]), None), args.replication_timeout)
        report['events'].append(key+'_raw_readback')
        row['stages']['native_raw'] = capture_stage(check, targets[key], args.offset, key+'_native_raw', True)
        report['events'].append(key+'_native_raw_capture')
        row['stages']['native_raw']['server'] = execute(check.client, READ_SERVER % key)
        write_json(output, report)
    for key in ('item', 'set_block'):
        row = report['controls'][key]
        row['nbt_assignment'] = execute(check.client, WRITE_NBT % (key, SHERDS))
        report['events'].append(key+'_fixture_nbt')
        row['nbt_replication'] = observe(check, READ_CLIENT % (tuple(targets[key]), SHERDS), args.replication_timeout)
        row['stages']['fixture_nbt'] = capture_stage(check, targets[key], args.offset, key+'_fixture_nbt', True)
        report['events'].append(key+'_fixture_nbt_capture')
        row['stages']['fixture_nbt']['server'] = execute(check.client, READ_SERVER % key)
        write_json(output, report)
    if not args.skip_projection:
        first = targets['item']
        origin = (first[0]+2, first[1], first[2])
        report['projection_started'] = check.run(PROJECTION % (origin,))
        report['projection'] = observe(check, PROJECTION_STATUS, args.timeout)
        report['projection']['ready'] = report['projection']['matched']
        report['events'].append('first_projection_requested')
        if report['projection']['matched']:
            for key in ('item', 'set_block'):
                row = report['controls'][key]
                row['stages']['after_first_projection'] = capture_stage(check, targets[key], args.offset, key+'_after_first_projection')
                row['stages']['after_first_projection']['server'] = execute(check.client, READ_SERVER % key)
                row['stages']['after_first_projection']['client'] = check.run(READ_CLIENT % (tuple(targets[key]), SHERDS))
                report['events'].append(key+'_after_first_projection_capture')
                write_json(output, report)
        else:
            report['projection']['capture_skipped'] = 'First projection did not become ready before timeout'
    for key, row in report['controls'].items():
        for name, stage in row['stages'].items():
            path = output.with_name(output.stem+'_'+key+'_'+name+'_body.png')
            stage['body'] = analyze_body(stage, row['empty'], targets[key], path, args.vertical_fov)
    report['completed'] = True
    report['native_positive_controls_passed'] = all(
        row['placement_readback_passed'] and row['raw_replication']['matched'] and
        row['stages']['native_raw']['body']['positive_control_passed']
        for row in report['controls'].values())
    report['passed'] = report['native_positive_controls_passed']


def cleanup(check, report):
    errors = []
    steps = (('projection', True, RESTORE_PROJECTION), ('world', False, RESTORE_WORLD),
             ('camera', True, RESTORE_CAMERA), ('environment', False,
              'import sys\n' + 'if hasattr(sys,"_context_environment_saved"):\n' +
              '\n'.join(' '+line for line in RESTORE_ENVIRONMENT.splitlines()) + '\n_result=True'))
    report['cleanup'] = {}
    for name, client_side, code in steps:
        try:
            value = check.run(code) if client_side else execute(check.client, code)
            report['cleanup'][name] = value
            if isinstance(value, dict) and not value.get('restored', True):
                errors.append(name+': '+repr(value))
        except Exception as error:
            errors.append('%s: %s: %s' % (name, type(error).__name__, error))
    report['cleanup_errors'] = errors
    report['restored'] = not errors
    report['passed'] = bool(report.get('passed') and report['restored'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--timeout', type=float, default=30.)
    parser.add_argument('--replication-timeout', type=float, default=6.)
    parser.add_argument('--weather-settle', type=float, default=10.)
    parser.add_argument('--offset', type=float, nargs=3, default=(0.,.4,4.))
    parser.add_argument('--vertical-fov', type=float, default=66.5)
    parser.add_argument('--skip-projection', action='store_true')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output already exists; choose a new path to preserve previous evidence')
    if min(args.timeout, args.replication_timeout) <= 0 or args.weather_settle < 0:
        parser.error('Timeouts must be positive and settle duration nonnegative')
    report = {'schema': 1, 'completed': False, 'passed': False, 'restored': False, 'controls': {},
              'session_file': os.environ.get('MCDEV_SESSION_FILE'),
              'scope': 'Untouched native pots, then fixture NBT, then first projection; normal bootstrap preview geometry is recorded; no SetBlockStates/SetLiquidBlock or editor opening',
              'native_body_capture': {'native_resolution': True, 'format': 'Lossless client-area PNG with SHA256'},
              'causal_claim': None}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with Client(timeout=30) as client:
        check = ColdCheck(client, args.output, args.timeout)
        try:
            run_probe(check, report, args.output, args)
        except Exception as error:
            report['error'] = '%s: %s' % (type(error).__name__, error)
        finally:
            cleanup(check, report)
            write_json(args.output, report)
    print(json.dumps({'completed': report['completed'], 'passed': report['passed'],
                      'restored': report['restored'], 'report': str(args.output.resolve())}))
    return 0 if report['completed'] and report['restored'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
