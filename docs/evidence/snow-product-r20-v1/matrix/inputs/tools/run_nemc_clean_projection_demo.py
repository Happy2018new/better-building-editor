"""Create isolated native demonstration worlds without any editor packs."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / '.agents/skills/pyreact-debugging/scripts'), str(ROOT / 'tools')]
from _session import load_session, process_identity
from mcdk import Client, return_value
from capture_native_window import capture

SHARED = Path('D:/Happy2018new\u306e\u4e2a\u4eba\u6587\u4ef6/GitHub/better-building-editor')
MCDK = SHARED / '.runtime/mcdk-retry-r11/build-ipc-framing-r11/tools/mcdk/mcdk.exe'
GUARD = SHARED / 'docs/evidence/background-focus-r13-v1/inputs/native_focus_guard.dll'
WGC = SHARED / '.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/.runtime/native_wgc/build/Release/native_wgc_capture.exe'
FIXTURE = ROOT / 'tools/data/nemc_clean_projection_fixture_r14.json'
VERSIONS = {'39': ('3.9.0.401155', '1.21.120.0'), '310': ('3.10.0.420447', '1.21.130.0')}
MOD_MAIN = '''from mod.common.mod import Mod
import mod.client.extraClientApi as api
@Mod.Binding(name='NemcProjectionCleanDemo',version='1.0.0')
class NemcProjectionCleanDemo(object):
 @Mod.InitClient()
 def init_client(self):
  api.RegisterSystem('NemcProjectionCleanDemo','Client','nemc_projection_clean.client.CleanClient')
'''
CLIENT_SYSTEM = '''import mod.client.extraClientApi as api
Base=api.GetClientSystemCls()
class CleanClient(Base):
 def __init__(self,namespace,systemName):
  Base.__init__(self,namespace,systemName)
  self.ui_initialized=False
  self.render_ticks=0
  self.ListenForEvent(api.GetEngineNamespace(),api.GetEngineSystemName(),'UiInitFinished',self,self.ui_init)
  self.ListenForEvent(api.GetEngineNamespace(),api.GetEngineSystemName(),'GameRenderTickEvent',self,self.tick)
 def ui_init(self,args):self.ui_initialized=True
 def tick(self,args):self.render_ticks+=1
 def Destroy(self):
  self.UnListenForEvent(api.GetEngineNamespace(),api.GetEngineSystemName(),'UiInitFinished',self,self.ui_init)
  self.UnListenForEvent(api.GetEngineNamespace(),api.GetEngineSystemName(),'GameRenderTickEvent',self,self.tick)
'''
ADMISSION = '''import mod.client.extraClientApi as api
import sys
system=api.GetSystem('NemcProjectionCleanDemo','Client')
_result={'runtime':api.GetMinecraftVersion(),'engine':api.GetEngineVersion(),
 'ui_initialized':system is not None and system.ui_initialized,'ticks':system.render_ticks if system else None,
 'modern_projection_modules':[name for name in sys.modules if name=='modern_projection' or name.startswith('modern_projection.')],
 'demo_module_path':sys.modules['nemc_projection_clean.client'].__file__ if system else None,
 'foot':api.GetEngineCompFactory().CreatePos(api.GetLocalPlayerId()).GetFootPos()}
'''
SETUP = '''import mod.server.extraServerApi as api
import json,math
fixture=json.loads(%r)
assert api.GetMinecraftVersion()==%r
factory=api.GetEngineCompFactory()
player=api.GetPlayerList()[0]
info=factory.CreateBlockInfo(player)
state=factory.CreateBlockState(api.GetLevelId())
items=factory.CreateItem(player)
foot=factory.CreatePos(player).GetFootPos()
delta=fixture['layout']['origin_offset']
origin=tuple(int(math.floor(foot[i]))+delta[i] for i in range(3))
assert not hasattr(api,'_nemc_clean_demo')
saved={'origin':origin,'journal':[],'rows':[],'fixture':fixture}
api._nemc_clean_demo=saved
def write(pos,name,states=None):
 name=str(name)
 values={} if states is None else dict((str(k),v.encode('utf8') if isinstance(v,unicode) else v) for k,v in states.items())
 aux=state.GetBlockAuxValueFromStates(name,values)
 result={'requested_name':name,'requested_states':states or {},'resolved_aux':aux}
 if aux==-1:
  result['unsupported']=True
  return result
 saved['journal'].append({'pos':pos,'block':info.GetBlockNew(pos,0),'nbt':info.GetBlockEntityData(0,pos)})
 result['changed']=info.SetBlockNew(pos,{'name':name,'aux':aux},0,0,True,False)
 result['actual']=info.GetBlockNew(pos,0)
 result['actual_states']=state.GetBlockStates(pos,0)
 return result
for z in range(18):
 for x in range(18):write((origin[0]+x,origin[1]-1,origin[2]+z),'minecraft:stone')
for index,case in enumerate(fixture['cases']):
 local=(1+index%%6*3,0,1+index//6*3)
 pos=tuple(origin[i]+local[i] for i in range(3))
 if case.get('wall'):write((pos[0],pos[1],pos[2]+1),'minecraft:stone')
 if case.get('overhead'):write((pos[0],pos[1]+1,pos[2]),'minecraft:stone')
 if case.get('contained'):
  for offset in ((-1,0,0),(1,0,0),(0,0,-1),(0,0,1)):
   write(tuple(pos[i]+offset[i] for i in range(3)),'minecraft:stone')
 if case.get('flow_source_above'):
  for offset in ((-1,1,0),(1,1,0),(0,1,-1),(0,1,1)):
   write(tuple(pos[i]+offset[i] for i in range(3)),'minecraft:stone')
  write((pos[0],pos[1]+1,pos[2]),'minecraft:water',{'liquid_depth':0})
 row={'id':case['id'],'case':case,'local':local,'pos':pos}
 if not case.get('placement'):
  row['write']=write(pos,'minecraft:'+case['block'],case.get('states'))
 if case.get('wet'):row['background_write']=info.SetLiquidBlock(pos,{'name':'minecraft:water','aux':0},0)
 saved['rows'].append(row)
command=factory.CreateCommand(api.GetLevelId())
saved['commands']=[(text,command.SetCommand(text,player,False)) for text in
 ('/gamerule dofiretick false','/gamerule randomtickspeed 0','/gamerule domobspawning false','/time set noon','/weather clear')]
_result={'origin':origin,'rows':saved['rows'],'journal_count':len(saved['journal']),'commands':saved['commands']}
'''
CONTENT = '''import mod.server.extraServerApi as api
factory=api.GetEngineCompFactory()
player=api.GetPlayerList()[0]
info=factory.CreateBlockInfo(player)
items=factory.CreateItem(player)
state=factory.CreateBlockState(api.GetLevelId())
saved=api._nemc_clean_demo
fixture=saved['fixture']
slot=35
item_type=api.GetMinecraftEnum().ItemPosType.INVENTORY
assert not items.GetPlayerItem(item_type,slot,True)
results=[]
for row in saved['rows']:
 case=row['case']
 pos=tuple(row['pos'])
 result={'id':row['id'],'pos':pos,'local':row['local']}
 if case.get('placement'):
  user_data={}
  if case.get('ominous'):user_data['Type']=1
  if case.get('patterns'):
   user_data['Patterns']=[{'Pattern':entry['Pattern'].encode('utf8'),'Color':entry['Color']} for entry in fixture['banner_patterns']]
  items.SetInvItemNum(slot,0)
  item_name='minecraft:banner' if case['placement']=='banner' else 'minecraft:frame'
  item={'itemName':item_name,'count':1,'auxValue':case.get('base',0),'userData':user_data}
  result['spawned']=items.SpawnItemToPlayerInv(item,player,slot)
  support=(pos[0],pos[1],pos[2]+1) if case.get('wall') else (pos[0],pos[1]-1,pos[2])
  saved['journal'].append({'pos':pos,'block':info.GetBlockNew(pos,0),'nbt':info.GetBlockEntityData(0,pos)})
  result['placed']=info.PlayerUseItemToPos(support,item_type,slot,2 if case.get('wall') else 1)
 if case.get('container_item'):
  item={'itemName':'minecraft:'+case['container_item'],'count':1,'auxValue':0}
  result['container_write']=items.SpawnItemToContainer(item,0,pos,0)
 if case.get('use_item'):
  items.SetInvItemNum(slot,0)
  item={'itemName':'minecraft:'+case['use_item'],'count':1,'auxValue':0}
  result['content_spawned']=items.SpawnItemToPlayerInv(item,player,slot)
  if case.get('enchanted'):
   result['enchant_added']=items.AddEnchantToInvItem(slot,api.GetMinecraftEnum().EnchantType.WeaponDamage,1)
  result['native_item']=items.GetPlayerItem(item_type,slot,True)
  result['content_used']=info.PlayerUseItemToPos(pos,item_type,slot,2 if case.get('wall') else 1)
 if case.get('sign_text'):
  nbt=info.GetBlockEntityData(0,pos)
  if nbt is None:
   result['sign_error']='Native sign NBT missing'
  else:
   for side,entry in (('FrontText',fixture['sign_front']),('BackText',fixture['sign_back'])):
    text=entry['text'].encode('utf8')
    nbt[side]['Text']['__value__']=text
    nbt[side]['FilteredText']['__value__']=text
    nbt[side]['SignTextColor']['__value__']=entry['color']
    nbt[side]['IgnoreLighting']['__value__']=1
   result['sign_write']=info.SetBlockEntityData(0,pos,nbt)
 result['actual']=info.GetBlockNew(pos,0)
 result['actual_states']=state.GetBlockStates(pos,0)
 result['actual_nbt']=info.GetBlockEntityData(0,pos)
 results.append(result)
items.SetInvItemNum(slot,0)
assert not items.GetPlayerItem(item_type,slot,True)
saved['content']=results
_result={'rows':results,'inventory_restored':True,'runtime':api.GetMinecraftVersion()}
'''
REPAIR = '''import mod.server.extraServerApi as api
factory=api.GetEngineCompFactory()
player=api.GetPlayerList()[0]
info=factory.CreateBlockInfo(player)
state=factory.CreateBlockState(api.GetLevelId())
items=factory.CreateItem(player)
saved=api._nemc_clean_demo
slot=35
item_type=api.GetMinecraftEnum().ItemPosType.INVENTORY
assert not items.GetPlayerItem(item_type,slot,True)
results=[]
for row in saved['rows']:
 case=row['case']
 pos=tuple(row['pos'])
 if row['id']=='flowing_water':
  for offset in ((-1,1,0),(1,1,0),(0,1,-1),(0,1,1)):
   info.SetBlockNew(tuple(pos[i]+offset[i] for i in range(3)),{'name':'minecraft:stone','aux':0},0,0,True,False)
  info.SetBlockNew((pos[0],pos[1]+1,pos[2]),{'name':'minecraft:water','aux':0},0,0,True,False)
  aux=state.GetBlockAuxValueFromStates('minecraft:flowing_water',{'liquid_depth':8})
  changed=info.SetBlockNew(pos,{'name':'minecraft:flowing_water','aux':aux},0,0,True,False)
 elif case.get('patterns'):
  info.SetBlockNew(pos,{'name':'minecraft:air','aux':0},0,0,True,False)
  patterns=[{'Pattern':entry['Pattern'].encode('utf8'),'Color':entry['Color']} for entry in saved['fixture']['banner_patterns']]
  spawned=items.SpawnItemToPlayerInv({'itemName':'minecraft:banner','count':1,'auxValue':case['base'],'userData':{'Patterns':patterns}},player,slot)
  support=(pos[0],pos[1],pos[2]+1) if case.get('wall') else (pos[0],pos[1]-1,pos[2])
  changed=info.PlayerUseItemToPos(support,item_type,slot,2 if case.get('wall') else 1)
  items.SetInvItemNum(slot,0)
 else:continue
 results.append({'id':row['id'],'changed':changed,'actual':info.GetBlockNew(pos,0),'states':state.GetBlockStates(pos,0),'nbt':info.GetBlockEntityData(0,pos)})
assert not items.GetPlayerItem(item_type,slot,True)
_result={'rows':results,'inventory_restored':True}
'''
PROJECT = '''import mod.client.extraClientApi as api
import json
fixture=json.loads(%r)
origin=%r
name=%r
assert api.GetMinecraftVersion()==%r
factory=api.GetEngineCompFactory()
level=api.GetLevelId()
system=api.GetSystem('NemcProjectionCleanDemo','Client')
assert system and system.ui_initialized
if hasattr(system,'demo'):system.DestroyClientEntity(system.demo['entity'])
start=(origin[0],origin[1]-1,origin[2])
end=(origin[0]+17,origin[1]+2,origin[2]+17)
palette=factory.CreateBlock(level).GetBlockPaletteBetweenPos(start,end,False)
assert palette is not None
source=palette.SerializeBlockPalette()
result=factory.CreateBlockGeometry(level).CombineBlockPaletteToGeometry(palette,name,0)
assert result is not None
actor_origin=tuple(origin[i]+fixture['projection_offset'][i] for i in range(3))
entity=system.CreateClientEntityByTypeStr('minecraft:armor_stand',actor_origin,(0.,0.))
assert entity is not None
system.demo={'entity':entity,'name':name,'origin':origin,'source':source}
render=factory.CreateActorRender(entity)
attached=render.AddActorBlockGeometry(name,(-.5,0.,-.5),(0.,180.,0.))
_result={'entity':entity,'name':name,'attached':attached,'actor_origin':actor_origin,'source':source,'runtime':api.GetMinecraftVersion()}
'''
VIEW = '''import mod.client.extraClientApi as api
system=api.GetSystem('NemcProjectionCleanDemo','Client')
origin=system.demo['origin']
target=%r
offset=%r
point=tuple(origin[i]+target[i] for i in range(3))
position=tuple(point[i]+offset[i] for i in range(3))
rot=api.GetRotFromDir(tuple(point[i]-position[i] for i in range(3)))
cam=api.GetEngineCompFactory().CreateCamera(api.GetLevelId())
cam.LockModCameraPitch(True)
cam.LockModCameraYaw(True)
cam.DepartCamera()
_result={'position':position,'target':point,'set':(cam.SetCameraPos(position),cam.SetCameraRotation((rot[0],rot[1]+180.,0.)))}
'''
FREE = '''import mod.client.extraClientApi as api
factory=api.GetEngineCompFactory()
level=api.GetLevelId()
cam=factory.CreateCamera(level)
cam.ResetCameraPos()
cam.UnDepartCamera()
cam.LockModCameraPitch(False)
cam.LockModCameraYaw(False)
op=factory.CreateOperation(level)
_result={'move_unlock':op.SetMoveLock(False),'can_move':op.SetCanMove(True),'can_jump':op.SetCanJump(True),
 'perspective':factory.CreatePlayerView(api.GetLocalPlayerId()).SetPerspective(0),
 'pitch_locked':cam.IsModCameraLockPitch(),'yaw_locked':cam.IsModCameraLockYaw()}
'''
CREATIVE = '''import mod.server.extraServerApi as api
player=api.GetPlayerList()[0]
_result={'creative':api.GetEngineCompFactory().CreatePlayer(player).SetPlayerGameType(api.GetMinecraftEnum().GameType.Creative)}
'''
UI_STATUS = '''import mod.client.extraClientApi as api
_result={'top_ui':api.GetTopUI()}
'''
RESUME = '''import mod.client.extraClientApi as api
top=api.GetTopUI()
assert top=='pause_screen',repr(top)
_result={'top_ui_before':top,'popped':api.PopTopUI()}
'''
READ = '''import mod.server.extraServerApi as api
import sys
factory=api.GetEngineCompFactory()
saved=api._nemc_clean_demo
info=factory.CreateBlockInfo(api.GetPlayerList()[0])
state=factory.CreateBlockState(api.GetLevelId())
_result={'runtime':api.GetMinecraftVersion(),'origin':saved['origin'],
 'modern_projection_modules':[name for name in sys.modules if name=='modern_projection' or name.startswith('modern_projection.')],
 'rows':[{'id':row['id'],'pos':row['pos'],'actual':info.GetBlockNew(tuple(row['pos']),0),'states':state.GetBlockStates(tuple(row['pos']),0),'nbt':info.GetBlockEntityData(0,tuple(row['pos']))} for row in saved['rows']]}
'''


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value,ensure_ascii=True,indent=2)+'\n',encoding='ascii')


def project_root(version):
    return ROOT / ('.runtime/nemc-clean-'+version)


def prepare(version):
    project=project_root(version)
    package=project/'behavior_pack/nemc_projection_clean'
    package.mkdir(parents=True,exist_ok=False)
    (package/'__init__.py').write_bytes(b'')
    (package/'modMain.py').write_text(MOD_MAIN,encoding='ascii')
    (package/'client.py').write_text(CLIENT_SYSTEM,encoding='ascii')
    manifest={'format_version':2,'header':{'name':'NEMC '+version+' Clean Native Projection Demo',
      'description':'Official native geometry only; no editor resource pack or compatibility renderer',
      'uuid':str(uuid.uuid4()),'version':[1,0,0],'min_engine_version':[1,21,0]},
      'modules':[{'type':'data','uuid':str(uuid.uuid4()),'version':[1,0,0]}]}
    save(project/'behavior_pack/manifest.json',manifest)
    executable='D:/MCStudioDownload/game/MinecraftPE_Netease/'+VERSIONS[version][0]+'/Minecraft.Windows.exe'
    config={'included_mod_dirs':[str(project.resolve())],'game_executable_path':executable,
      'world_seed':0,'world_type':2,'game_mode':1,'auto_hot_reload_mods':False,'auto_hot_reload_ui':False,
      'auto_hot_reload_materials':False,'auto_hot_reload_shaders':False}
    save(project/'.mcdev.json',config)
    plan={'at':datetime.now(timezone.utc).isoformat(),'version':version,'runtime':VERSIONS[version][1],
      'project':str(project.resolve()),'fixture':str(FIXTURE),'fixture_sha256':digest(FIXTURE),
      'files':{str(path.relative_to(project)):digest(path) for path in sorted(project.rglob('*')) if path.is_file()},
      'own_resource_pack':False,'editor_packs':False,'activation_resize_input':False,'launches_permitted':1}
    save(project/'plan.json',plan)
    return plan


def execute(code,is_client,output):
    output.mkdir(parents=True,exist_ok=False)
    (output/'source.py').write_text(code,encoding='ascii')
    receipt={'at':datetime.now(timezone.utc).isoformat(),'is_client':is_client,'code_sha256':hashlib.sha256(code.encode('ascii')).hexdigest(),
             'pixel_acceptance':False}
    try:
        with Client(timeout=40) as client:
            receipt['result']=return_value(client.call('execute_code',{'code':code,'is_client':is_client,'direct_return':True}))
        return receipt['result']
    except Exception as error:
        receipt['error']=type(error).__name__+': '+str(error)
        raise
    finally:
        save(output/'result.json',receipt)


def mount_inventory(session):
    world=Path(session['world_path'])
    result={'world':str(world),'lists':{},'packs':[]}
    for name in ('world_behavior_packs.json','world_resource_packs.json',
                 'netease_world_behavior_packs.json','netease_world_resource_packs.json'):
        result['lists'][name]=json.loads((world/name).read_text(encoding='utf8')) if (world/name).exists() else None
    for kind in ('behavior_packs','resource_packs'):
        for linked in sorted((world/kind).iterdir()):
            resolved=linked.resolve()
            manifest=resolved/'manifest.json'
            data=json.loads(manifest.read_text(encoding='utf8'))
            result['packs'].append({'kind':kind,'linked':str(linked),'resolved':str(resolved),
                'manifest':data,'manifest_sha256':digest(manifest),
                'files':{str(path.relative_to(resolved)):digest(path) for path in sorted(resolved.rglob('*')) if path.is_file()}})
    result['modern_projection_paths']=[pack['resolved']+'/'+name for pack in result['packs']
        for name in pack['files'] if 'modern_projection' in name.lower() or 'modern_projection' in pack['resolved'].lower()]
    result['own_resource_pack']=any(pack['kind']=='resource_packs' for pack in result['packs'])
    if result['modern_projection_paths'] or result['own_resource_pack']:
        raise RuntimeError('Unexpected compatibility content/resource pack in clean world')
    return result


def archive(version, session, output, user_confirmed_closed=False):
    output.mkdir(parents=True,exist_ok=False)
    project=project_root(version)
    evidence=project/'evidence'
    copied={}
    for path in sorted(evidence.rglob('*')):
        if not path.is_file() or path.name=='source.py':
            continue
        relative=path.relative_to(evidence)
        target=output/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(path,target)
        copied[str(relative)]=digest(target)
    for name in ('plan.json','.mcdev.json','prelaunch-capacity.json'):
        target=output/name.lstrip('.')
        shutil.copy2(project/name,target)
        copied[target.name]=digest(target)
    save(output/'index.json',{'at':datetime.now(timezone.utc).isoformat(),'owner':session['owner'],
        'version':version,'project':str(project),'session_file':session['session_file'],
        'game_pid':session['game_pid'],'game_identity':session['game_identity'],
        'mcdk_pid':session['mcdk_pid'],'mcdk_identity':session['mcdk_identity'],
        'world_path':session['world_path'],'fixture_sha256':digest(FIXTURE),'files':copied,
        'user_confirmed_closed':user_confirmed_closed,'automatic_relaunch':False,
        'game_current_identity':process_identity(session['game_pid']),
        'mcdk_current_identity':process_identity(session['mcdk_pid'])})
    return {'path':str(output),'files':len(copied)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','start','admission','setup','content','repair','project','view','free','creative','ui_status','resume','read','capture','inventory','archive','exit_receipt'])
    parser.add_argument('--version',choices=list(VERSIONS),required=True)
    parser.add_argument('--session',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--setup-result',type=Path)
    parser.add_argument('--target')
    parser.add_argument('--offset')
    parser.add_argument('--user-confirmed-closed',action='store_true')
    args=parser.parse_args()
    owner='nemc-clean-'+args.version+'-r14'
    project=project_root(args.version)
    if args.action=='prepare':
        print(json.dumps(prepare(args.version),indent=2))
        return
    os.environ['MCDEV_ALLOW_USER_FOREGROUND']='1'
    if args.action=='start':
        if (project/'launch-stdout.json').exists():
            raise RuntimeError('This clean generation already has a launch receipt; do not relaunch it automatically')
        census=subprocess.run(['powershell.exe','-NoProfile','-Command',
          "@(Get-CimInstance Win32_Process -Filter \"Name='Minecraft.Windows.exe'\" | Where-Object { $_.ThreadCount -gt 0 -or $_.HandleCount -gt 0 } | Select-Object ProcessId,ThreadCount,HandleCount,ExecutablePath)|ConvertTo-Json -Compress"],
          capture_output=True,timeout=8,creationflags=subprocess.CREATE_NO_WINDOW)
        if census.returncode:raise RuntimeError('Capacity census failed')
        rows=json.loads(census.stdout.decode('utf-8-sig') or '[]')
        rows=rows if isinstance(rows,list) else [rows]
        if len(rows)>=5:raise RuntimeError('No capacity for owned clean game')
        if digest(MCDK)!='b8eb8959f97a4348006837bb7897d1e5cb957855d1746145974d8f37c00be9f9' or digest(GUARD)!='04b073e1aea6fe16a70573e64c6aac31940431409ac90c79f250e02f35a3ec93':
            raise RuntimeError('Noactivation binary pin mismatch')
        save(project/'prelaunch-capacity.json',{'at':datetime.now(timezone.utc).isoformat(),'active_count':len(rows),'rows':rows})
        command=[sys.executable,'-X','utf8',str(ROOT/'.agents/skills/pyreact-debugging/scripts/instances.py'),
          'start','--project',str(project),'--owner',owner,'--name',owner,'--preset','ui','--wait','120',
          '--mcdk',str(MCDK),'--noactivate-dll',str(GUARD),'--noactivate-sha256',digest(GUARD),
          '--noactivate-mcdk-sha256',digest(MCDK),'--game-exe','D:/MCStudioDownload/game/MinecraftPE_Netease/'+VERSIONS[args.version][0]+'/Minecraft.Windows.exe']
        with (project/'launch-stdout.json').open('wb') as stdout,(project/'launch-stderr.txt').open('wb') as stderr:
            result=subprocess.run(command,cwd=project,stdout=stdout,stderr=stderr,timeout=190,creationflags=subprocess.CREATE_NO_WINDOW)
        print(json.dumps({'owner':owner,'returncode':result.returncode,'launch_output':str(project/'launch-stdout.json')}))
        return
    if not args.session or not args.output:parser.error('This action requires --session and --output')
    os.environ.update(MCDEV_SESSION_FILE=str(args.session),MCDEV_OWNER=owner)
    if args.action in ('inventory','archive'):
        data=load_session(args.session,owner)
        if args.action=='inventory':
            args.output.parent.mkdir(parents=True,exist_ok=True)
            result=mount_inventory(data)
            save(args.output,result)
        else:
            result=archive(args.version,data,args.output,args.user_confirmed_closed)
        print(json.dumps(result,indent=2))
        return
    if args.action=='exit_receipt':
        data=load_session(args.session,owner)
        result={'session_file':str(args.session),'game_pid':data['game_pid'],'game_identity':data['game_identity'],
                'game_current_identity':process_identity(data['game_pid']),'mcdk_pid':data['mcdk_pid'],
                'mcdk_identity':data['mcdk_identity'],'mcdk_current_identity':process_identity(data['mcdk_pid'])}
        save(args.output,result)
        print(json.dumps(result,indent=2))
        return
    session=load_session(args.session,owner,live=True)
    if VERSIONS[args.version][0] not in session['game_executable'] or Path(session['project']).resolve()!=project.resolve():
        raise RuntimeError('Wrong owned clean project/executable')
    fixture=json.loads(FIXTURE.read_text(encoding='ascii'))
    wire=json.dumps(fixture,ensure_ascii=True,separators=(',',':'))
    if args.action=='capture':
        result=capture(args.session,owner,args.output,WGC)
        print(json.dumps({key:result.get(key) for key in ('ok','path','width','height','sha256','game_pid')},indent=2))
        return
    if args.action=='setup':code,is_client=SETUP % (wire,VERSIONS[args.version][1]),False
    elif args.action=='project':
        if not args.setup_result:parser.error('Project requires --setup-result')
        origin=tuple(json.loads(args.setup_result.read_text(encoding='ascii'))['result']['origin'])
        code,is_client=PROJECT % (wire,origin,'nemc_clean_'+args.version+'_'+uuid.uuid4().hex[:12],VERSIONS[args.version][1]),True
    elif args.action=='view':
        target=tuple(float(v) for v in args.target.split(',')) if args.target else tuple(fixture['camera']['target'])
        offset=tuple(float(v) for v in args.offset.split(',')) if args.offset else tuple(fixture['camera']['offset'])
        code,is_client=VIEW % (target,offset),True
    else:
        code,is_client={'admission':(ADMISSION,True),'content':(CONTENT,False),'repair':(REPAIR,False),'free':(FREE,True),'creative':(CREATIVE,False),'ui_status':(UI_STATUS,True),'resume':(RESUME,True),'read':(READ,False)}[args.action]
    result=execute(code,is_client,args.output)
    if args.action=='admission':
        if result['runtime']!=VERSIONS[args.version][1] or result['engine']!=VERSIONS[args.version][0] or result['modern_projection_modules'] or not result['ui_initialized']:
            raise RuntimeError('Clean native version/module admission failed')
        save(args.output/'mounted-packs.json',mount_inventory(session))
    print(json.dumps({'action':args.action,'version':args.version,'owner':owner,'output':str(args.output),
                     'fixture_sha256':digest(FIXTURE)},indent=2))


if __name__=='__main__':main()
