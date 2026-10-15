"""Small, native-only Combine flipbook comparisons in an assigned clean 3.10 world.

Never starts a game, activates/resizes a window, or sends desktop input. Runtime
calls use instances.py exec with the assigned session and owner. The raw native
palette, world readback, camera, timed PNGs and hidden-geometry control are kept
separate from manual pixel qualification.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

from PIL import Image, ImageChops, ImageDraw, ImageStat

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / '.agents/skills/pyreact-debugging/scripts'
sys.path.insert(0, str(SCRIPTS))
from mcdk import return_value
from capture_native_window import capture
from run_nemc_clean_projection_demo import WGC, mount_inventory

GROUPS = {
    'fire': ('fire', 'soul_fire'),
    'lantern': ('lantern', 'soul_lantern', 'copper_lantern'),
    'copper_a': ('exposed_copper_lantern', 'weathered_copper_lantern', 'oxidized_copper_lantern'),
    'copper_b': ('waxed_copper_lantern', 'waxed_exposed_copper_lantern'),
    'copper_c': ('waxed_weathered_copper_lantern', 'waxed_oxidized_copper_lantern'),
    'prismarine_a': ('prismarine', 'prismarine_slab'),
    'prismarine_b': ('prismarine_double_slab', 'prismarine_stairs'),
    'prismarine_c': ('prismarine_wall', 'sea_lantern'),
    'sculk': ('sculk', 'sculk_vein'),
    'sensor': ('sculk_sensor', 'calibrated_sculk_sensor'),
    'sculk_nbt': ('sculk_catalyst', 'sculk_shrieker'),
    'water_plants': ('kelp', 'seagrass'),
    'plants': ('firefly_bush',),
    'stem': ('crimson_stem', 'warped_stem'),
    'hyphae': ('crimson_hyphae', 'warped_hyphae'),
    'nether': ('magma', 'respawn_anchor'),
    'utility': ('stonecutter_block', 'chemical_heat'),
    'command': ('command_block', 'chain_command_block', 'repeating_command_block'),
    'furnaces': ('lit_smoker', 'lit_blast_furnace'),
    'campfire': ('campfire', 'soul_campfire'),
    'portals': ('portal', 'end_portal', 'end_gateway'),
    'special_nbt': ('enchanting_table', 'beacon', 'conduit'),
    'containers': ('chest', 'copper_chest', 'ender_chest'),
    'shulker_bed': ('purple_shulker_box', 'bed', 'dragon_head'),
    'heads': ('piglin_head', 'player_head', 'skeleton_skull'),
    'signs': ('standing_sign', 'wall_sign', 'oak_hanging_sign'),
    'banners': ('standing_banner', 'wall_banner'),
    'pottery': ('flower_pot', 'decorated_pot'),
    'contents': ('lectern', 'oak_shelf', 'chiseled_bookshelf'),
    'frames': ('frame', 'glow_frame', 'brewing_stand'),
    'special_states': ('bell', 'copper_golem_statue', 'big_dripleaf'),
    'pistons': ('piston', 'sticky_piston', 'moving_block'),
    'trial': ('vault', 'trial_spawner', 'mob_spawner'),
    'brushable': ('suspicious_sand', 'suspicious_gravel'),
    'functional': ('barrel', 'hopper', 'dispenser'),
    'functional_b': ('dropper', 'crafter', 'crafting_table'),
    'functional_c': ('furnace', 'blast_furnace', 'smoker'),
    'functional_d': ('bee_nest', 'beehive', 'creaking_heart'),
    'functional_e': ('daylight_detector', 'daylight_detector_inverted', 'unpowered_comparator'),
    'functional_f': ('jukebox', 'noteblock', 'lodestone'),
    'functional_g': ('jigsaw', 'structure_block', 'netherreactor'),
    'functional_h': ('spore_blossom', 'compound_creator', 'cauldron'),
}
OVERRIDES = {
    'respawn_anchor': {'respawn_anchor_charge': 4},
    'sculk_vein': {'multi_face_direction_bits': 1},
    'prismarine_wall': {'wall_post_bit': 1},
    'lit_smoker': {'minecraft:cardinal_direction': 'north'},
    'lit_blast_furnace': {'minecraft:cardinal_direction': 'north'},
    'bed': {'head_piece_bit': False, 'occupied_bit': False, 'direction': 0},
    'portal': {'portal_axis': 'x'},
    'wall_sign': {'facing_direction': 2},
    'wall_banner': {'facing_direction': 2},
    'standing_sign': {'ground_sign_direction': 8},
    'standing_banner': {'ground_sign_direction': 8},
    'frame': {'facing_direction': 2},
    'glow_frame': {'facing_direction': 2},
    'piglin_head': {'facing_direction': 1},
    'player_head': {'facing_direction': 1},
    'skeleton_skull': {'facing_direction': 1},
    'dragon_head': {'facing_direction': 1},
}

CLIENT = '''import json,sys,time
import mod.client.extraClientApi as api
factory=api.GetEngineCompFactory()
level=api.GetLevelId()
system=api.GetSystem('NemcProjectionCleanDemo','Client')
assert system and system.ui_initialized
assert api.GetEngineVersion()=='3.10.0.420447'
assert not [k for k in sys.modules if k=='modern_projection' or k.startswith('modern_projection.')]
'''
SERVER = '''import json,sys
import mod.server.extraServerApi as api
factory=api.GetEngineCompFactory()
level=api.GetLevelId()
player=api.GetPlayerList()[0]
info=factory.CreateBlockInfo(player)
state=factory.CreateBlockState(level)
dimension=factory.CreateDimension(player).GetEntityDimensionId()
assert dimension==0
'''
ADMISSION = CLIENT + '''_result=json.dumps({'runtime':api.GetMinecraftVersion(),'engine':api.GetEngineVersion(),
 'ticks':system.render_ticks,'foot':factory.CreatePos(api.GetLocalPlayerId()).GetFootPos(),
 'top_ui':api.GetTopUI(),'module':sys.modules['nemc_projection_clean.client'].__file__})
'''
SETUP = SERVER + '''rows=%r
origin=%r
if hasattr(api,'_astra_dynamic'):
 for entry in reversed(api._astra_dynamic['journal']):
  info.SetBlockNew(entry['pos'],entry['block'],0,dimension,True,True)
  if entry['nbt']:info.SetBlockEntityData(dimension,entry['pos'],entry['nbt'])
saved={'journal':[],'rows':[],'origin':origin}
api._astra_dynamic=saved
def write(pos,name,states):
 aux=state.GetBlockAuxValueFromStates(name,states)
 assert aux>=0,(name,states,aux)
 saved['journal'].append({'pos':pos,'block':info.GetBlockNew(pos,dimension),'nbt':info.GetBlockEntityData(dimension,pos)})
 changed=info.SetBlockNew(pos,{'name':name,'aux':aux},0,dimension,True,True)
 return {'changed':changed,'aux':aux,'actual':info.GetBlockNew(pos,dimension),'states':state.GetBlockStates(pos,dimension)}
for z in range(-1,7):
 for x in range(-1,len(rows)*3):
  write((origin[0]+x,origin[1]-1,origin[2]+z),'minecraft:stone',{})
for i,row in enumerate(rows):
 pos=(origin[0]+i*3,origin[1],origin[2])
 if row['name']=='minecraft:soul_fire':write((pos[0],pos[1]-1,pos[2]),'minecraft:soul_soil',{})
 if row['name']=='minecraft:fire':write((pos[0],pos[1]-1,pos[2]),'minecraft:netherrack',{})
 if row['name']=='minecraft:firefly_bush':write((pos[0],pos[1]-1,pos[2]),'minecraft:grass_block',{})
 if row['name'] in ('minecraft:wall_sign','minecraft:wall_banner','minecraft:frame','minecraft:glow_frame'):
  write((pos[0],pos[1],pos[2]+1),'minecraft:stone',{})
 placed=write(pos,row['name'],row['states'])
 if row['name']=='minecraft:bed':
  head=dict(row['states'],head_piece_bit=True)
  placed['head']=write((pos[0],pos[1],pos[2]+1),row['name'],head)
 if row['name'] in ('minecraft:kelp','minecraft:seagrass'):
  placed['water']=info.SetLiquidBlock(pos,{'name':'minecraft:water','aux':0},dimension)
 saved['rows'].append(dict(row,pos=pos,placed=placed))
commands=('/gamerule dofiretick false','/gamerule randomtickspeed 0','/gamerule domobspawning false',
 '/gamerule dodaylightcycle false','/time set noon','/weather clear')
saved['commands']=[(c,factory.CreateCommand(level).SetCommand(c,player,False)) for c in commands]
_result=json.dumps({'origin':origin,'rows':saved['rows'],'commands':saved['commands']})
'''
READ = SERVER + '''_result=json.dumps({'rows':[dict(row,actual=info.GetBlockNew(row['pos'],dimension),
 states=state.GetBlockStates(row['pos'],dimension),nbt=info.GetBlockEntityData(dimension,row['pos'])) for row in api._astra_dynamic['rows']]})
'''
CONTENT = SERVER + '''items=factory.CreateItem(player)
slot=35
inventory_type=api.GetMinecraftEnum().ItemPosType.INVENTORY
original=items.GetPlayerItem(inventory_type,slot,True)
results=[]
try:
 for row in api._astra_dynamic['rows']:
  name,pos=row['name'],row['pos']
  nbt=info.GetBlockEntityData(dimension,pos)
  changed=False
  if nbt and 'FrontText' in nbt:
   for side,text,color in (('FrontText','R15 FRONT',-65536),('BackText','R15 BACK',-16711936)):
    nbt[side]['Text']['__value__']=text
    nbt[side]['SignTextColor']['__value__']=color
    nbt[side]['IgnoreLighting']['__value__']=1
   changed=info.SetBlockEntityData(dimension,pos,nbt)
  if nbt and nbt.get('id',{}).get('__value__')=='Banner':
   # Native item placement synchronizes banner render data; raw NBT writes in
   # this engine leave the client with the previous base/pattern payload.
   info.SetBlockNew(pos,{'name':'minecraft:air','aux':0},0,dimension,True,True)
   items.SetInvItemNum(slot,0)
   patterns=[{'Color':color,'Pattern':pattern} for color,pattern in ((1,'bs'),(14,'ts'))]
   items.SpawnItemToPlayerInv({'itemName':'minecraft:banner','count':1,'auxValue':4,
     'userData':{'Patterns':patterns}},player,slot)
   wall=name=='minecraft:wall_banner'
   support=(pos[0],pos[1],pos[2]+1) if wall else (pos[0],pos[1]-1,pos[2])
   changed=info.PlayerUseItemToPos(support,inventory_type,slot,2 if wall else 1)
  item=None
  if name=='minecraft:flower_pot':item='minecraft:poppy'
  if name in ('minecraft:frame','minecraft:glow_frame','minecraft:oak_shelf'):item='minecraft:diamond_sword'
  if name in ('minecraft:campfire','minecraft:soul_campfire'):item='minecraft:beef'
  if item:
   items.SetInvItemNum(slot,0)
   spawned=items.SpawnItemToPlayerInv({'itemName':item,'count':1,'auxValue':0},player,slot)
   changed=info.PlayerUseItemToPos(pos,inventory_type,slot,2 if name in ('minecraft:frame','minecraft:glow_frame') else 1)
  results.append({'name':name,'pos':pos,'content_changed':changed,'nbt':info.GetBlockEntityData(dimension,pos)})
finally:
 items.SetInvItemNum(slot,0)
 if original:items.SpawnItemToPlayerInv(original,player,slot)
_result=json.dumps({'rows':results,'inventory_restored':items.GetPlayerItem(inventory_type,slot,True)==original})
'''
PROJECT = CLIENT + '''origin=%r
rows=%r
name=%r
if hasattr(system,'astra_dynamic'):system.DestroyClientEntity(system.astra_dynamic['entity'])
low=(origin[0],origin[1]-1,origin[2])
high=(origin[0]+(len(rows)-1)*3,origin[1]+1,origin[2]+1)
palette=factory.CreateBlock(level).GetBlockPaletteBetweenPos(low,high,False)
assert palette is not None
raw=palette.SerializeBlockPalette()
result=factory.CreateBlockGeometry(level).CombineBlockPaletteToGeometry(palette,name,0)
assert result==name,result
# Keep the render entity in the player's loaded chunk and above ground.
# Geometry may extend across chunk boundaries independently of this anchor.
foot=factory.CreatePos(api.GetLocalPlayerId()).GetFootPos()
actor=(origin[0],origin[1]+6,origin[2]+4)
offset=(actor[0]-origin[0]-.5,origin[1]-actor[1]-1.,actor[2]-origin[2]-4-.5)
entity=system.CreateClientEntityByTypeStr('minecraft:armor_stand',actor,(0.,0.))
assert entity
render=factory.CreateActorRender(entity)
attached=render.AddActorBlockGeometry(name,offset,(0.,180.,0.))
assert attached
system.astra_dynamic={'entity':entity,'name':name,'origin':origin,'rows':rows}
def tagged(v):
 if isinstance(v,dict):return {'dict':[[tagged(k),tagged(x)] for k,x in v.items()]}
 if isinstance(v,(list,tuple)):return [tagged(x) for x in v]
 return v
_result=json.dumps({'origin':origin,'actor':actor,'entity':entity,'name':name,'attached':attached,
 'offset':offset,'rotation':(0.,180.,0.),'palette':tagged(raw)})
'''
CAMERA = CLIENT + '''origin=system.astra_dynamic['origin']
count=len(system.astra_dynamic['rows'])
target=(origin[0]+(count-1)*1.5+.5,origin[1]+.45,origin[2]+2.5)
offset=(4.5,5.,-8.5)
position=tuple(target[i]+offset[i] for i in range(3))
rot=api.GetRotFromDir(tuple(target[i]-position[i] for i in range(3)))
cam=factory.CreateCamera(level)
cam.DepartCamera()
cam.LockModCameraPitch(True)
cam.LockModCameraYaw(True)
assert cam.SetCameraPos(position) and cam.SetCameraRotation((rot[0],rot[1]+180.,0.))
top=api.GetTopUI()
if top=='pause_screen':api.PopTopUI()
_result=json.dumps({'target':target,'position':position,'rotation':cam.GetCameraRotation(),'top_ui_before':top})
'''
STATE = CLIENT + '''cam=factory.CreateCamera(level)
saved=system.astra_dynamic
origin=saved['origin']
rois=[]
for i,row in enumerate(saved['rows']):
 for kind,dz in (('world',0),('projection',4)):
  pos=(origin[0]+i*3,origin[1],origin[2]+dz)
  corners=[cam.WorldToScreenPoint(pos[0]+x,pos[1]+y,pos[2]+z) for x in (.1,.9) for y in (.1,.9) for z in (.1,.9)]
  rois.append({'kind':kind,'name':row['name'],'pos':pos,'points':corners})
_result=json.dumps({'ticks':system.render_ticks,'time':time.time(),'position':cam.GetPosition(),
 'rotation':cam.GetCameraRotation(),'screen':factory.CreateGame(level).GetScreenSize(),'fov':cam.GetFov(),
 'top_ui':api.GetTopUI(),'rois':rois})
'''
HIDE = CLIENT + "_result=factory.CreateActorRender(system.astra_dynamic['entity']).SetNotRenderAtAll(%r)\n"
RESTORE_CLIENT = CLIENT + '''if hasattr(system,'astra_dynamic'):
 system.DestroyClientEntity(system.astra_dynamic['entity'])
 del system.astra_dynamic
cam=factory.CreateCamera(level)
cam.ResetCameraPos()
cam.UnDepartCamera()
cam.LockModCameraPitch(False)
cam.LockModCameraYaw(False)
_result=True
'''
RESTORE_SERVER = SERVER + '''if hasattr(api,'_astra_dynamic'):
 for entry in reversed(api._astra_dynamic['journal']):
  info.SetBlockNew(entry['pos'],entry['block'],0,dimension,True,True)
  if entry['nbt']:info.SetBlockEntityData(dimension,entry['pos'],entry['nbt'])
 del api._astra_dynamic
_result=True
'''


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + '\n', encoding='ascii')


def fixture(group):
    raw = json.loads((ROOT / 'docs/reference/block_palettes/nemc_3.9.0.401155.json').read_bytes())
    first = {}
    for row in raw['blocks']:
        first.setdefault(row['name'], {s['name']: s['value'] for s in row['states']})
    rows = []
    for name in GROUPS[group] + ('stone',):
        states = dict(first.get('minecraft:' + name, {}))
        states.update(OVERRIDES.get(name, {}))
        rows.append({'name': 'minecraft:' + name, 'states': states, 'static_control': name == 'stone'})
    return rows


class Audit:
    def __init__(self, args):
        self.args, self.counter = args, 0
        self.env = dict(os.environ, MCDEV_ALLOW_USER_FOREGROUND='1')

    def execute(self, label, code, client=True):
        self.counter += 1
        folder = self.args.output / ('%02d_' % self.counter + label)
        folder.mkdir(parents=True, exist_ok=False)
        (folder / 'source.py').write_text(code, encoding='ascii')
        args_file = folder / 'args.json'
        save(args_file, {'code': code, 'is_client': client, 'direct_return': True})
        command = [sys.executable, '-X', 'utf8', str(SCRIPTS / 'instances.py'), 'exec',
                   '--session', self.args.session, '--owner', self.args.owner, '--',
                   'mcdk.py', '--timeout', '35', 'call', 'execute_code', '--args-file', str(args_file)]
        result = subprocess.run(command, cwd=ROOT, env=self.env, capture_output=True,
                                text=True, encoding='utf8', timeout=45)
        (folder / 'stdout.txt').write_text(result.stdout, encoding='utf8')
        (folder / 'stderr.txt').write_text(result.stderr, encoding='utf8')
        if result.returncode:
            raise RuntimeError('Runtime call failed: ' + str(folder) + ': ' + result.stderr[-1500:])
        value = return_value(json.loads(result.stdout))
        value = json.loads(value) if isinstance(value, str) else value
        save(folder / 'result.json', value)
        return value

    def frame(self, label):
        before = self.execute(label + '_before', STATE)
        os.environ['MCDEV_ALLOW_USER_FOREGROUND'] = '1'
        receipt = capture(self.args.session, self.args.owner, self.args.output / (label + '.png'), WGC)
        after = self.execute(label + '_after', STATE)
        assert before['position'] == after['position'] and before['rotation'] == after['rotation']
        assert before['screen'] == after['screen']
        return {'capture': receipt, 'before': before, 'after': after}


def score(frames, hidden, output):
    images = [Image.open(f['capture']['path']).convert('RGB') for f in frames]
    blank = Image.open(hidden['capture']['path']).convert('RGB')
    width, height = images[0].size
    screen = frames[0]['before']['screen']
    # SDK WorldToScreenPoint returns physical pixels, not GetScreenSize UI units.
    scale = (1.0, 1.0)
    annotated = images[0].copy()
    draw = ImageDraw.Draw(annotated)
    rows = []
    for roi in frames[0]['before']['rois']:
        xs = [p['screenX'] * scale[0] for p in roi['points']]
        ys = [p['screenY'] * scale[1] for p in roi['points']]
        box = (max(0, int(min(xs))), max(0, int(min(ys))), min(width, int(max(xs))), min(height, int(max(ys))))
        if box[2] <= box[0] or box[3] <= box[1]:
            rows.append(dict(roi, error='ROI outside frame'))
            continue
        crops = [im.crop(box) for im in images]
        metrics = []
        for im in crops[1:]:
            delta = ImageChops.difference(crops[0], im)
            mask = ImageChops.lighter(ImageChops.lighter(*delta.split()[:2]), delta.split()[2])
            metrics.append({'changed_gt12': sum(mask.point(lambda p: 255 if p > 12 else 0).histogram()[1:]),
                            'mean_rgb_difference': ImageStat.Stat(delta).mean})
        hide_delta = ImageChops.difference(crops[0], blank.crop(box))
        hide_mask = ImageChops.lighter(ImageChops.lighter(*hide_delta.split()[:2]), hide_delta.split()[2])
        row = {'kind': roi['kind'], 'name': roi['name'], 'box': box, 'pixel_area': crops[0].width*crops[0].height,
               'temporal': metrics, 'hidden_changed_gt12': sum(hide_mask.point(lambda p:255 if p>12 else 0).histogram()[1:]),
               'manual_pixel_acceptance': False}
        rows.append(row)
        draw.rectangle(box, outline='red' if roi['kind']=='projection' else 'lime', width=2)
        draw.text((box[0],box[1]-12), roi['kind']+':'+roi['name'].split(':')[-1], fill='white')
    annotated.save(output / 'rois.png')
    return {'rows': rows, 'scale': scale, 'automatic_acceptance': False,
            'limits': 'Bounding boxes include background; manual crops and static control must validate texture-local changes.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('plan', 'run', 'restore'))
    parser.add_argument('--session')
    parser.add_argument('--owner')
    parser.add_argument('--group', choices=tuple(GROUPS), default='fire')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--origin', default='0,-58,0')
    parser.add_argument('--content', action='store_true', help='Use observed sign/banner fields and real item interactions')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if args.action == 'plan':
        save(args.output / 'plan.json', {'groups': {k:fixture(k) for k in GROUPS},
             'public_blueprint': 'test.registry.vanilla; NBT associations in test.entities.classic/mechanisms/recent',
             'state_source': '3.9 registry states used as requests only; aux resolved and states read back in native 3.10',
             'delegated': ['water','flowing_water','bubble_column','lava','flowing_lava','portal','cauldron'],
             'pixel_acceptance': False})
        return
    if not args.session or not args.owner:
        parser.error('An assigned session and owner are required')
    audit = Audit(args)
    report = {'schema':1,'group':args.group,'started_at':datetime.now(timezone.utc).isoformat(),
              'session':args.session,'owner':args.owner,'pixel_acceptance':False,'completed':False,
              'tool_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    try:
        if args.action == 'restore':
            report['client']=audit.execute('restore_client',RESTORE_CLIENT)
            report['server']=audit.execute('restore_server',RESTORE_SERVER,False)
        else:
            report['admission']=audit.execute('admission',ADMISSION)
            session=json.loads(Path(args.session).read_text(encoding='utf8'))
            report['mount_inventory']=mount_inventory(session)
            rows=fixture(args.group)
            origin=tuple(int(v) for v in args.origin.split(','))
            report['setup']=audit.execute('setup',SETUP % (rows,origin),False)
            if args.content:
                report['content']=audit.execute('content',CONTENT,False)
            time.sleep(.6)
            report['readback']=audit.execute('readback',READ,False)
            report['project']=audit.execute('project',PROJECT % (origin,rows,'astra_dynamic_'+uuid.uuid4().hex))
            report['camera']=audit.execute('camera',CAMERA)
            time.sleep(2.0)
            report['frames']=[audit.frame('frame_0')]
            delay=16 if args.group.startswith('prismarine') else 1.3
            time.sleep(delay)
            report['frames'].append(audit.frame('frame_1'))
            time.sleep(1.7)
            report['frames'].append(audit.frame('frame_2'))
            report['hidden']=audit.execute('hide',HIDE % True)
            time.sleep(.3)
            report['hidden_frame']=audit.frame('hidden')
            report['unhidden']=audit.execute('unhide',HIDE % False)
            report['final_readback']=audit.execute('final_readback',READ,False)
            report['score']=score(report['frames'],report['hidden_frame'],args.output)
            controls=[row for row in report['score']['rows']
                      if row['kind']=='projection' and row['name']=='minecraft:stone']
            report['projection_control_visible']=bool(controls and
                controls[0].get('hidden_changed_gt12',0)>controls[0].get('pixel_area',1)*.1)
            if not report['projection_control_visible']:
                raise RuntimeError('Projected stone control was not observed; no family support verdict is valid')
        report['completed']=True
    except Exception as error:
        report['error']=type(error).__name__+': '+str(error)
        raise
    finally:
        save(args.output / 'report.json',report)


if __name__ == '__main__':
    main()
