"""Observe native cauldron data and clean palette rendering in one owned world.

This is an audit tool, not a production adapter. It preserves typed NBT, raw
palette data, PNG capture receipts and native interaction results independently.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / '.agents/skills/pyreact-debugging/scripts'), str(ROOT / 'tools')]
from _session import load_session, process_identity
from mcdk import Client, return_value
from capture_native_window import capture
from run_nemc_clean_projection_demo import WGC, mount_inventory

OWNER = 'cauldron-runtime-audit-r15'
VERSION = '1.21.130.0'
ENGINE = '3.10.0.420447'


def cases():
    rows = []
    for liquid in ('water', 'lava', 'powder_snow'):
        for fill in range(7):
            rows.append({'id': '%s_fill_%d' % (liquid, fill),
                         'states': {'cauldron_liquid': liquid, 'fill_level': fill}})
    for item in ('water_bucket', 'lava_bucket', 'powder_snow_bucket'):
        rows.append({'id': 'native_' + item, 'use': [{'name': item, 'aux': 0}]})
    for aux in range(47):
        rows.append({'id': 'potion_%d' % aux,
                     'use': [{'name': 'potion', 'aux': aux}] * 3})
    rows.append({'id': 'dyed_red', 'use': [{'name': 'water_bucket', 'aux': 0},
                                          {'name': 'red_dye', 'aux': 0}]})
    rows.append({'id': 'dyed_red_blue', 'use': [{'name': 'water_bucket', 'aux': 0},
                                               {'name': 'red_dye', 'aux': 0},
                                               {'name': 'blue_dye', 'aux': 0}]})
    for name in ('splash_potion', 'lingering_potion'):
        for aux in range(43, 47):
            rows.append({'id': '%s_%d' % (name, aux),
                         'use': [{'name': name, 'aux': aux}] * 3})
    for index, row in enumerate(rows):
        row['index'] = index
        row['local'] = [1 + index % 9 * 2, 0, 1 + index // 9 * 2]
    return rows


SETUP = '''import mod.server.extraServerApi as api
import json,math
assert api.GetMinecraftVersion()==%r
assert not hasattr(api,'_cauldron_audit')
factory=api.GetEngineCompFactory()
player=api.GetPlayerList()[0]
info=factory.CreateBlockInfo(player)
state=factory.CreateBlockState(api.GetLevelId())
foot=factory.CreatePos(player).GetFootPos()
origin=(int(math.floor(foot[0]))-8,int(math.floor(foot[1])),int(math.floor(foot[2]))+8)
rows=json.loads(%r)
saved={'origin':origin,'rows':rows,'journal':[],'player':player}
api._cauldron_audit=saved
def write(pos,name,states):
 values=dict((str(k),v.encode('utf8') if isinstance(v,unicode) else v) for k,v in states.items())
 aux=state.GetBlockAuxValueFromStates(name,values)
 if aux==-1:return {'unsupported':True,'aux':aux,'states':states}
 saved['journal'].append({'pos':pos,'block':info.GetBlockNew(pos,0),'nbt':info.GetBlockEntityData(0,pos)})
 changed=info.SetBlockNew(pos,{'name':name,'aux':aux},0,0,True,False)
 return {'changed':changed,'requested_aux':aux,'actual':info.GetBlockNew(pos,0),'states':state.GetBlockStates(pos,0),'nbt':info.GetBlockEntityData(0,pos)}
for z in range(19):
 for x in range(19):write((origin[0]+x,origin[1]-1,origin[2]+z),'minecraft:stone',{})
for row in rows:
 pos=tuple(origin[i]+row['local'][i] for i in range(3))
 row['pos']=pos
 row['write']=write(pos,'minecraft:cauldron',row.get('states',{'cauldron_liquid':'water','fill_level':0}))
command=factory.CreateCommand(api.GetLevelId())
saved['commands']=[(s,command.SetCommand(s,player,False)) for s in ('/gamerule domobspawning false','/gamerule randomtickspeed 0','/time set noon','/weather clear')]
_result={'runtime':api.GetMinecraftVersion(),'origin':origin,'rows':rows,'commands':saved['commands'],'journal_count':len(saved['journal'])}
'''

CONTENT = '''import mod.server.extraServerApi as api
factory=api.GetEngineCompFactory()
saved=api._cauldron_audit
player=saved['player']
info=factory.CreateBlockInfo(player)
state=factory.CreateBlockState(api.GetLevelId())
items=factory.CreateItem(player)
slot=35
item_type=api.GetMinecraftEnum().ItemPosType.INVENTORY
assert not items.GetPlayerItem(item_type,slot,True)
results=[]
for row in saved['rows']:
 if not row.get('use'):continue
 pos=tuple(row['pos'])
 record={'id':row['id'],'pos':pos,'steps':[]}
 for spec in row['use']:
  item={'itemName':str('minecraft:'+spec['name']),'count':1,'auxValue':spec['aux']}
  items.SetInvItemNum(slot,0)
  spawned=items.SpawnItemToPlayerInv(item,player,slot)
  before=items.GetPlayerItem(item_type,slot,True)
  used=info.PlayerUseItemToPos(pos,item_type,slot,1)
  record['steps'].append({'requested':item,'spawned':spawned,'native_item_before':before,'used':used,'native_item_after':items.GetPlayerItem(item_type,slot,True),'actual':info.GetBlockNew(pos,0),'states':state.GetBlockStates(pos,0),'nbt':info.GetBlockEntityData(0,pos)})
 results.append(record)
items.SetInvItemNum(slot,0)
assert not items.GetPlayerItem(item_type,slot,True)
saved['content']=results
_result={'rows':results,'inventory_restored':True,'runtime':api.GetMinecraftVersion()}
'''

READ = '''import mod.server.extraServerApi as api
factory=api.GetEngineCompFactory()
saved=api._cauldron_audit
info=factory.CreateBlockInfo(saved['player'])
state=factory.CreateBlockState(api.GetLevelId())
_result={'origin':saved['origin'],'runtime':api.GetMinecraftVersion(),'rows':[{'id':r['id'],'pos':r['pos'],'local':r['local'],'block':info.GetBlockNew(tuple(r['pos']),0),'states':state.GetBlockStates(tuple(r['pos']),0),'nbt':info.GetBlockEntityData(0,tuple(r['pos']))} for r in saved['rows']]}
'''

ADMISSION = '''import mod.client.extraClientApi as api
import sys
system=api.GetSystem('NemcProjectionCleanDemo','Client')
_result={'runtime':api.GetMinecraftVersion(),'engine':api.GetEngineVersion(),'ui_initialized':bool(system and system.ui_initialized),'render_ticks':system.render_ticks if system else None,'top_ui':api.GetTopUI(),'foot':api.GetEngineCompFactory().CreatePos(api.GetLocalPlayerId()).GetFootPos(),'modern_projection_modules':[n for n in sys.modules if n=='modern_projection' or n.startswith('modern_projection.')]}
'''

SYNC = '''import mod.client.extraClientApi as api
import json
rows=json.loads(%r)
factory=api.GetEngineCompFactory()
info=factory.CreateBlockInfo(api.GetLocalPlayerId())
state=factory.CreateBlockState(api.GetLevelId())
_result={'rows':[{'id':r['id'],'block':info.GetBlockNew(tuple(r['pos']),0),'states':state.GetBlockStates(tuple(r['pos']),0),'nbt':info.GetBlockEntityData(0,tuple(r['pos']))} for r in rows],'render_ticks':api.GetSystem('NemcProjectionCleanDemo','Client').render_ticks}
'''

PROJECT = '''import mod.client.extraClientApi as api
factory=api.GetEngineCompFactory()
system=api.GetSystem('NemcProjectionCleanDemo','Client')
origin=%r
start=(origin[0],origin[1]-1,origin[2])
end=(origin[0]+18,origin[1]+1,origin[2]+18)
palette=factory.CreateBlock(api.GetLevelId()).GetBlockPaletteBetweenPos(start,end,False)
assert palette is not None
source=palette.SerializeBlockPalette()
name=%r
geometry=factory.CreateBlockGeometry(api.GetLevelId()).CombineBlockPaletteToGeometry(palette,name,0)
assert geometry is not None
actor_origin=(origin[0]+24,origin[1]-1,origin[2])
entity=system.CreateClientEntityByTypeStr('minecraft:armor_stand',actor_origin,(0.,0.))
assert entity is not None
system.cauldron_audit={'entity':entity,'origin':origin,'actor_origin':actor_origin,'geometry_name':name}
attached=factory.CreateActorRender(entity).AddActorBlockGeometry(name,(-.5,0.,-.5),(0.,180.,0.))
_result={'entity':entity,'name':name,'geometry_result':geometry,'attached':attached,'actor_origin':actor_origin,'source':source,'ticks':system.render_ticks,'runtime':api.GetMinecraftVersion()}
'''

VIEW = '''import mod.client.extraClientApi as api
system=api.GetSystem('NemcProjectionCleanDemo','Client')
origin=%r
local=%r
offset=%r
point=tuple(origin[i]+local[i] for i in range(3))
position=tuple(point[i]+offset[i] for i in range(3))
rot=api.GetRotFromDir(tuple(point[i]-position[i] for i in range(3)))
cam=api.GetEngineCompFactory().CreateCamera(api.GetLevelId())
cam.LockModCameraPitch(True)
cam.LockModCameraYaw(True)
cam.DepartCamera()
_result={'position':position,'target':point,'requested_rotation':(rot[0],rot[1]+180.,0.),'set':(cam.SetCameraPos(position),cam.SetCameraRotation((rot[0],rot[1]+180.,0.))),'ticks':system.render_ticks}
'''

MOVE_PROJECTED = '''import mod.client.extraClientApi as api
system=api.GetSystem('NemcProjectionCleanDemo','Client')
saved=system.cauldron_audit
target=(saved['actor_origin'][0],saved['actor_origin'][1]+8.,saved['actor_origin'][2])
moved=api.GetEngineCompFactory().CreatePos(saved['entity']).SetPosForClientEntity(target)
saved['actor_origin']=target
_result={'moved':moved,'target':target,'entity':saved['entity'],'ticks':system.render_ticks}
'''

RESTORE_SERVER = '''import mod.server.extraServerApi as api
saved=getattr(api,'_cauldron_audit',None)
results=[]
if saved:
 info=api.GetEngineCompFactory().CreateBlockInfo(saved['player'])
 for entry in reversed(saved['journal']):
  pos=tuple(entry['pos'])
  changed=info.SetBlockNew(pos,entry['block'],0,0,True,False)
  nbt_write=info.SetBlockEntityData(0,pos,entry['nbt']) if entry['nbt'] is not None else None
  results.append({'pos':pos,'changed':changed,'nbt_write':nbt_write,'actual':info.GetBlockNew(pos,0),'expected':entry['block']})
_result={'rows':results,'restored':bool(saved)}
'''

CUSTOM_COLOR = '''import mod.server.extraServerApi as api
saved=api._cauldron_audit
info=api.GetEngineCompFactory().CreateBlockInfo(saved['player'])
rows=dict((r['id'],r) for r in saved['rows'])
results=[]
for name, value in (('dyed_red', -65536), ('dyed_red_blue', 16711680)):
 pos=tuple(rows[name]['pos'])
 nbt=info.GetBlockEntityData(0,pos)
 nbt['CustomColor']={'__type__':3,'__value__':value}
 written=info.SetBlockEntityData(0,pos,nbt)
 read=info.GetBlockEntityData(0,pos)
 results.append({'id':name,'value_written':value,'set_result':written,'readback':read})
_result={'rows':results}
'''

RESTORE_CLIENT = '''import mod.client.extraClientApi as api
system=api.GetSystem('NemcProjectionCleanDemo','Client')
saved=getattr(system,'cauldron_audit',None)
factory=api.GetEngineCompFactory()
cam=factory.CreateCamera(api.GetLevelId())
cam.ResetCameraPos()
cam.UnDepartCamera()
cam.LockModCameraPitch(False)
cam.LockModCameraYaw(False)
_result={'destroy':system.DestroyClientEntity(saved['entity']) if saved else None,'pitch_locked':cam.IsModCameraLockPitch(),'yaw_locked':cam.IsModCameraLockYaw(),'ticks':system.render_ticks}
'''


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + '\n', encoding='ascii')


def execute(code, client_side, output):
    output.mkdir(parents=True, exist_ok=False)
    (output / 'source.py').write_text(code, encoding='ascii')
    receipt = {'at': datetime.now(timezone.utc).isoformat(), 'client': client_side,
               'code_sha256': hashlib.sha256(code.encode('ascii')).hexdigest(),
               'pixel_acceptance': False}
    try:
        with Client(timeout=45) as client:
            receipt['result'] = return_value(client.call('execute_code', {
                'code': code, 'is_client': client_side, 'direct_return': True}))
        return receipt['result']
    except Exception as error:
        receipt['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        save(output / 'result.json', receipt)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['admission', 'setup', 'content', 'custom_color', 'read',
        'sync', 'project', 'move_projected', 'view', 'capture', 'restore_client',
        'restore_server', 'exit'])
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--setup-result', type=Path)
    parser.add_argument('--target', default='9,0.5,9')
    parser.add_argument('--offset', default='0,19,-22')
    args = parser.parse_args()
    os.environ.update(MCDEV_SESSION_FILE=str(args.session), MCDEV_OWNER=OWNER,
                      MCDEV_ALLOW_USER_FOREGROUND='1')
    session = load_session(args.session, OWNER, live=args.action != 'exit')
    if args.action == 'exit':
        result = {'game_pid': session['game_pid'], 'game_identity': session['game_identity'],
            'game_current_identity': process_identity(session['game_pid']),
            'mcdk_pid': session['mcdk_pid'], 'mcdk_identity': session['mcdk_identity'],
            'mcdk_current_identity': process_identity(session['mcdk_pid'])}
        save(args.output, result)
    elif args.action == 'capture':
        result = capture(args.session, OWNER, args.output, WGC)
    else:
        setup = json.loads(args.setup_result.read_text(encoding='ascii'))['result'] if args.setup_result else None
        if args.action == 'setup':
            code, side = SETUP % (VERSION, json.dumps(cases(), ensure_ascii=True)), False
        elif args.action == 'project':
            code, side = PROJECT % (tuple(setup['origin']), 'cauldron_audit_r15'), True
        elif args.action == 'sync':
            code, side = SYNC % json.dumps(setup['rows'], ensure_ascii=True), True
        elif args.action == 'view':
            code, side = VIEW % (tuple(setup['origin']), tuple(float(v) for v in args.target.split(',')), tuple(float(v) for v in args.offset.split(','))), True
        elif args.action == 'move_projected':
            code, side = MOVE_PROJECTED, True
        elif args.action == 'custom_color':
            code, side = CUSTOM_COLOR, False
        else:
            code, side = {'admission': (ADMISSION, True), 'content': (CONTENT, False),
                'custom_color': (CUSTOM_COLOR, False),
                'read': (READ, False), 'restore_client': (RESTORE_CLIENT, True),
                'restore_server': (RESTORE_SERVER, False)}[args.action]
        result = execute(code, side, args.output)
        if args.action == 'admission':
            assert result['runtime'] == VERSION and result['engine'] == ENGINE
            assert result['ui_initialized'] and not result['modern_projection_modules']
            save(args.output / 'mounted-packs.json', mount_inventory(session))
    print(json.dumps({'action': args.action, 'output': str(args.output),
        'result': {key: result.get(key) for key in ('runtime', 'render_ticks', 'ok', 'path', 'origin', 'rows') if key in result}}, ensure_ascii=True))


if __name__ == '__main__':
    main()
