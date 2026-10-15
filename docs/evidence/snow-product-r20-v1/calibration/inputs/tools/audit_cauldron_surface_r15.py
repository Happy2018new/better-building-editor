"""Owner-bound native cauldron surface/color calibration, preserving its fixture.

WorldToScreenPoint samples calibrate the screenshot independently of remembered
cauldron geometry. All block writes request native neighbor updates. State and
typed NBT readback accompany every image; pixels are analyzed separately.
"""
import argparse
import json
import os
from pathlib import Path

from audit_native_visual_r15 import Audit, WGC, save
from capture_native_window import capture

SERVER = '''import mod.server.extraServerApi as api
import json
factory=api.GetEngineCompFactory()
player=api.GetPlayerList()[0]
info=factory.CreateBlockInfo(player)
states=factory.CreateBlockState(api.GetLevelId())
'''
CLIENT = '''import mod.client.extraClientApi as api
import json
factory=api.GetEngineCompFactory()
player=api.GetLocalPlayerId()
cam=factory.CreateCamera(api.GetLevelId())
info=factory.CreateBlockInfo(player)
'''
SETUP = SERVER + '''assert api.GetMinecraftVersion()=='1.21.130.0'
assert not hasattr(api,'_cauldron_surface_r15')
origin=%r
saved={'origin':origin,'journal':[]}
api._cauldron_surface_r15=saved
for x in range(-1,2):
 for z in range(-1,2):
  pos=(origin[0]+x,origin[1]-1,origin[2]+z)
  saved['journal'].append((pos,info.GetBlockNew(pos,0),info.GetBlockEntityData(0,pos),info.GetLiquidBlock(pos,0)))
  info.SetBlockNew(pos,{'name':'minecraft:stone','aux':0},0,0,False,True)
saved['journal'].append((origin,info.GetBlockNew(origin,0),info.GetBlockEntityData(0,origin),info.GetLiquidBlock(origin,0)))
assert info.GetLiquidBlock(origin,0) is None, 'Choose a dry calibration position'
info.SetBlockNew(origin,{'name':'minecraft:cauldron','aux':0},0,0,False,True)
_result=json.dumps({'origin':origin,'journal':saved['journal'],'runtime':api.GetMinecraftVersion()})
'''
FILL = SERVER + '''saved=api._cauldron_surface_r15
pos=tuple(saved['origin'])
liquid,fill=%r,%r
aux=states.GetBlockAuxValueFromStates('minecraft:cauldron',{'cauldron_liquid':liquid,'fill_level':fill})
assert aux>=0
# Clear actors between cases; the second call occurs in this test's setup, and
# the client is read in a subsequent request after native synchronization.
info.SetBlockNew(pos,{'name':'minecraft:air','aux':0},0,0,False,True)
changed=info.SetBlockNew(pos,{'name':'minecraft:cauldron','aux':aux},0,0,True,True)
_result=json.dumps({'requested':{'liquid':liquid,'fill':fill,'aux':aux},'changed':changed,'block':info.GetBlockNew(pos,0),'states':states.GetBlockStates(pos,0),'nbt':info.GetBlockEntityData(0,pos)})
'''
ITEM = SERVER + '''saved=api._cauldron_surface_r15
pos=tuple(saved['origin'])
name,aux,count=%r,%r,%r
items=factory.CreateItem(player)
slot=35
kind=api.GetMinecraftEnum().ItemPosType.INVENTORY
original=items.GetPlayerItem(kind,slot,True)
results=[]
for unused in range(count):
 items.SetInvItemNum(slot,0)
 assert items.SpawnItemToPlayerInv({'itemName':name,'count':1,'auxValue':aux},player,slot)
 used=info.PlayerUseItemToPos(pos,kind,slot,1)
 results.append({'used':used,'block':info.GetBlockNew(pos,0),'states':states.GetBlockStates(pos,0),'nbt':info.GetBlockEntityData(0,pos)})
items.SetInvItemNum(slot,0)
if original:items.SpawnItemToPlayerInv(original,player,slot)
_result=json.dumps({'steps':results,'inventory_restored':items.GetPlayerItem(kind,slot,True)==original})
'''
COLOR = SERVER + '''pos=tuple(api._cauldron_surface_r15['origin'])
nbt=info.GetBlockEntityData(0,pos)
assert nbt is not None
nbt['CustomColor']={'__type__':3,'__value__':%r}
written=info.SetBlockEntityData(0,pos,nbt)
_result=json.dumps({'written':written,'nbt':info.GetBlockEntityData(0,pos)})
'''
LIGHT = SERVER + '''command=factory.CreateCommand(api.GetLevelId())
saved=api._cauldron_surface_r15
if 'lighting_rules' not in saved:
 saved['lighting_rules']=factory.CreateGame(api.GetLevelId()).GetGameRulesInfoServer()['cheat_info']
_result={'time':command.SetCommand('/time set noon',player,False),'weather':command.SetCommand('/weather clear',player,False),'daylight':command.SetCommand('/gamerule dodaylightcycle false',player,False),'weather_cycle':command.SetCommand('/gamerule doweathercycle false',player,False),'original_rules':saved['lighting_rules']}
'''
CONTROL = SERVER + '''pos=tuple(api._cauldron_surface_r15['origin'])
changed=info.SetBlockNew(pos,{'name':'minecraft:red_concrete','aux':0},0,0,False,True)
_result={'changed':changed,'block':info.GetBlockNew(pos,0)}
'''
REFERENCES = SERVER + '''saved=api._cauldron_surface_r15
origin=tuple(saved['origin'])
assert 'references' not in saved
saved['references']=[]
for offset in (2,4):
 pos=(origin[0]+offset,origin[1],origin[2])
 below=(pos[0],pos[1]-1,pos[2])
 for point in (below,pos):
  assert info.GetLiquidBlock(point,0) is None, 'Choose dry color reference positions'
  saved['journal'].append((point,info.GetBlockNew(point,0),info.GetBlockEntityData(0,point),info.GetLiquidBlock(point,0)))
 info.SetBlockNew(below,{'name':'minecraft:stone','aux':0},0,0,False,True)
 info.SetBlockNew(pos,{'name':'minecraft:cauldron','aux':6},0,0,True,True)
 saved['references'].append(pos)
_result={'positions':saved['references']}
'''
REFERENCE_COLORS = SERVER + '''rows=[]
for pos,color in zip(api._cauldron_surface_r15['references'],(16777215,0)):
 nbt=info.GetBlockEntityData(0,tuple(pos))
 nbt['CustomColor']={'__type__':3,'__value__':color}
 written=info.SetBlockEntityData(0,tuple(pos),nbt)
 rows.append({'pos':pos,'color':color,'written':written,'nbt':info.GetBlockEntityData(0,tuple(pos))})
_result=json.dumps({'rows':rows})
'''
BIOME = SERVER + '''saved=api._cauldron_surface_r15
pos=tuple(saved['origin'])
biome=factory.CreateBiome(player)
if 'original_biome' not in saved:saved['original_biome']=biome.GetBiomeName(pos)
changed=biome.SetBiomeByPos(pos,%r,0)
_result={'changed':changed,'original':saved['original_biome'],'current':biome.GetBiomeName(pos)}
'''
VIEW = CLIENT + '''origin=%r
target=tuple(origin[i]+%r[i] for i in range(3))
position=tuple(target[i]+%r[i] for i in range(3))
rotation=api.GetRotFromDir(tuple(target[i]-position[i] for i in range(3)))
cam.LockModCameraPitch(True)
cam.LockModCameraYaw(True)
cam.DepartCamera()
assert cam.SetCameraPos(position)
assert cam.SetCameraRotation((rotation[0],rotation[1]+180.,0.))
_result=json.dumps({'target':target,'position':position,'rotation':rotation})
'''
READ = CLIENT + '''origin=%r
material=info.GetBlock(origin)
palette=factory.CreateBlock(api.GetLevelId()).GetBlockPaletteBetweenPos(origin,origin,False).SerializeBlockPalette()
points=[]
for x in (0.,.125,.5,.875,1.):
 for y in (0.,.25,.5,.75,1.):
  for z in (0.,.125,.5,.875,1.):
   p=tuple(origin[i]+(x,y,z)[i] for i in range(3))
   points.append({'local':(x,y,z),'screen':cam.WorldToScreenPoint(*p)})
_result=json.dumps({'origin':origin,'points':points,'block':material,'palette_states':palette.get('states',{}).get(material),'actor':palette.get('actor',{}),'biome':factory.CreateBiome(api.GetLevelId()).GetBiomeName(origin),'camera_position':cam.GetPosition(),'camera_rotation':cam.GetCameraRotation(),'runtime':api.GetMinecraftVersion(),'engine':api.GetEngineVersion()})
'''
SERVER_READ = SERVER + '''pos=tuple(api._cauldron_surface_r15['origin'])
_result=json.dumps({'block':info.GetBlockNew(pos,0),'states':states.GetBlockStates(pos,0),'nbt':info.GetBlockEntityData(0,pos)})
'''
RESTORE = SERVER + '''saved=getattr(api,'_cauldron_surface_r15',None)
result=[]
if saved:
 for pos,block,nbt,liquid in reversed(saved['journal']):
  result.append(info.SetBlockNew(tuple(pos),block,0,0,True,True))
  if nbt:info.SetBlockEntityData(0,tuple(pos),nbt)
  if liquid and liquid!=block:info.SetLiquidBlock(tuple(pos),liquid,0)
 rules=saved.get('lighting_rules')
 if rules:
  command=factory.CreateCommand(api.GetLevelId())
  command.SetCommand('/gamerule dodaylightcycle '+str(rules['daylight_cycle']).lower(),player,False)
  command.SetCommand('/gamerule doweathercycle '+str(rules['weather_cycle']).lower(),player,False)
 if 'original_biome' in saved:factory.CreateBiome(player).SetBiomeByPos(tuple(saved['origin']),saved['original_biome'],0)
 del api._cauldron_surface_r15
_result={'restored':bool(saved),'writes':result}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('setup', 'fill', 'item', 'color', 'light', 'control', 'references', 'reference_colors', 'biome', 'view', 'read', 'capture', 'restore'))
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--origin', default='6,-58,0')
    parser.add_argument('--offset', default='0,2,-1.6')
    parser.add_argument('--target', default='.5,.6,.5')
    parser.add_argument('--liquid', default='water', choices=('water', 'lava', 'powder_snow'))
    parser.add_argument('--fill', type=int, choices=range(7), default=6)
    parser.add_argument('--item', default='minecraft:potion')
    parser.add_argument('--aux', type=int, default=5)
    parser.add_argument('--count', type=int, default=3)
    parser.add_argument('--color', type=int, default=16711680)
    parser.add_argument('--biome', default='minecraft:plains')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    origin = tuple(int(v) for v in args.origin.split(','))
    audit = Audit(args)
    if args.action == 'capture':
        server_before = audit.execute('server_before', SERVER_READ, False)
        before = audit.execute('before', READ % (origin,))
        os.environ['MCDEV_ALLOW_USER_FOREGROUND'] = '1'
        image = capture(args.session, args.owner, args.output / 'frame.png', WGC)
        after = audit.execute('after', READ % (origin,))
        server_after = audit.execute('server_after', SERVER_READ, False)
        before.update(states=server_before['states'], nbt=server_before['nbt'])
        after.update(states=server_after['states'], nbt=server_after['nbt'])
        result = {'before': before, 'capture': image, 'after': after,
                  'server_before': server_before, 'server_after': server_after}
    else:
        code, client = {
            'setup': (SETUP % (origin,), False),
            'fill': (FILL % (args.liquid, args.fill), False),
            'item': (ITEM % (args.item, args.aux, args.count), False),
            'color': (COLOR % args.color, False),
            'light': (LIGHT, False),
            'control': (CONTROL, False),
            'references': (REFERENCES, False),
            'reference_colors': (REFERENCE_COLORS, False),
            'biome': (BIOME % args.biome, False),
            'view': (VIEW % (origin, tuple(float(v) for v in args.target.split(',')),
                             tuple(float(v) for v in args.offset.split(','))), True),
            'read': (READ % (origin,), True),
            'restore': (RESTORE, False),
        }[args.action]
        result = audit.execute(args.action, code, client)
    save(args.output / 'report.json', result)
    print(json.dumps({'action': args.action, 'output': str(args.output)}, ensure_ascii=True))


if __name__ == '__main__':
    main()
