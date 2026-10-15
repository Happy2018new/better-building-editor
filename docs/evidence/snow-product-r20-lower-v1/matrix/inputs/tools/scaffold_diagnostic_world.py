"""Build and admit an isolated SDK world before native scaffold diagnostics."""
import json
from pathlib import Path
import shutil
import uuid

from probe_scaffold_state_lifecycle import OFFSETS, RUNTIME

CLIENT_SYSTEM = '''import mod.client.extraClientApi as api
ClientSystem=api.GetClientSystemCls()
class ScaffoldDiagnosticClientSystem(ClientSystem):
 def __init__(self,namespace,systemName):
  ClientSystem.__init__(self,namespace,systemName)
  self.ui_initialized=False
  self.render_ticks=0
  self.ListenForEvent(api.GetEngineNamespace(),api.GetEngineSystemName(),'UiInitFinished',self,self.ui_init)
  self.ListenForEvent(api.GetEngineNamespace(),api.GetEngineSystemName(),'GameRenderTickEvent',self,self.render_tick)
 def ui_init(self,unused):
  self.ui_initialized=True
  self.render_ticks=0
 def render_tick(self,unused):
  if self.ui_initialized:self.render_ticks+=1
 def Destroy(self):
  self.UnListenForEvent(api.GetEngineNamespace(),api.GetEngineSystemName(),'UiInitFinished',self,self.ui_init)
  self.UnListenForEvent(api.GetEngineNamespace(),api.GetEngineSystemName(),'GameRenderTickEvent',self,self.render_tick)
'''

MOD_MAIN = '''from mod.common.mod import Mod
import mod.client.extraClientApi as clientApi
@Mod.Binding(name='ScaffoldLifecycleDiagnostic',version='1.0.0')
class ScaffoldLifecycleDiagnostic(object):
 @Mod.InitClient()
 def client(self):
  clientApi.RegisterSystem('ScaffoldLifecycleDiagnostic','Client','modern_projection.client_system.ScaffoldDiagnosticClientSystem')
 @Mod.InitServer()
 def server(self):
  print('ScaffoldLifecycleDiagnostic server library ready')
'''

CLIENT = '''def _scaffold_world_client():
 import mod.client.extraClientApi as api
 player=api.GetLocalPlayerId()
 system=api.GetSystem('ScaffoldLifecycleDiagnostic','Client')
 return {'player':player,'foot':api.GetEngineCompFactory().CreatePos(player).GetFootPos() if player else None,
  'runtime':api.GetMinecraftVersion(),'ui_initialized':system is not None and system.ui_initialized,
  'render_ticks':system.render_ticks if system is not None else 0}
_result=_scaffold_world_client()
del _scaffold_world_client
'''

SERVER = '''def _scaffold_world_server():
 import mod.server.extraServerApi as api
 import math
 players=api.GetPlayerList()
 if not players:return {'player':None,'foot':None,'dimension':None,'runtime':api.GetMinecraftVersion(),'ground':None,'reserve':[]}
 player=players[0]
 factory=api.GetEngineCompFactory()
 foot=factory.CreatePos(player).GetFootPos()
 dimension=factory.CreateDimension(player).GetEntityDimensionId()
 value={'player':player,'foot':foot,'dimension':dimension,'runtime':api.GetMinecraftVersion(),
        'ground':None,'reserve':[]}
 if foot is None or not -64<=foot[1]<=320:return value
 info=factory.CreateBlockInfo(api.GetLevelId())
 state=factory.CreateBlockState(api.GetLevelId())
 ground=(int(math.floor(foot[0])),int(math.floor(foot[1]))-1,int(math.floor(foot[2])))
 value['ground']={'front':info.GetBlockNew(ground,dimension),'states':state.GetBlockStates(ground,dimension)}
 origin=(ground[0]+4,ground[1]+19,ground[2]+4)
 for offset in __OFFSETS__:
  pos=tuple(origin[i]+offset[i] for i in range(3))
  value['reserve'].append({'offset':offset,'front':info.GetBlockNew(pos,dimension),
                         'states':state.GetBlockStates(pos,dimension),'liquid':info.GetLiquidBlock(pos,dimension)})
 return value
_result=_scaffold_world_server()
del _scaffold_world_server
'''.replace('__OFFSETS__', repr(OFFSETS))


def foot_valid(foot):
    return (isinstance(foot, (tuple, list)) and len(foot) == 3
            and all(type(value) in (int, float) for value in foot)
            and -64 <= foot[1] <= 320 and all(-1000000 <= value <= 1000000 for value in foot))


def ready(client, server):
    """Loading sentinels and IPC availability are not world readiness."""
    if not isinstance(client, dict) or not isinstance(server, dict):
        return False
    if (client.get('runtime') != RUNTIME or server.get('runtime') != RUNTIME
            or client.get('ui_initialized') is not True
            or type(client.get('render_ticks')) is not int or client['render_ticks'] < 2
            or not client.get('player') or client['player'] != server.get('player')
            or type(server.get('dimension')) is not int or server['dimension'] != 0 or not foot_valid(client.get('foot'))
            or not foot_valid(server.get('foot'))):
        return False
    if any(abs(left - right) > .125 for left, right in zip(client['foot'], server['foot'])):
        return False
    ground = server.get('ground')
    if not isinstance(ground, dict) or not isinstance(ground.get('front'), dict):
        return False
    front = ground['front']
    if (not isinstance(ground.get('states'), dict)
            or not isinstance(front.get('name'), str) or front['name'] in ('minecraft:unknown', 'minecraft:air')
            or type(front.get('aux')) is not int):
        return False
    reserve = server.get('reserve', [])
    if (not isinstance(reserve, (list, tuple)) or len(reserve) != len(OFFSETS)
            or any(not isinstance(cell, dict) for cell in reserve)
            or {tuple(cell.get('offset', ())) for cell in reserve} != set(OFFSETS)):
        return False
    for cell in reserve:
        liquid = cell.get('liquid')
        if (cell.get('front') != {'name': 'minecraft:air', 'aux': 0}
                or type(cell['front'].get('aux')) is not int or cell.get('states') != {}
                or 'liquid' not in cell or liquid is not None
                and (not isinstance(liquid, dict) or liquid.get('name') != 'minecraft:air'
                     or type(liquid.get('aux', 0)) is not int or liquid.get('aux', 0) != 0)):
            return False
    return True


def build_pack(root, target):
    """Copy exact registry bytes; isolate game systems and manifest identities."""
    root, target = Path(root), Path(target)
    package = target / 'behavior_pack/modern_projection'
    (package / 'projection').mkdir(parents=True, exist_ok=False)
    for name in ('block_registry.py', 'block_registry_data.py'):
        shutil.copyfile(root / 'behavior_pack/modern_projection/projection' / name, package / 'projection' / name)
    for path in (package / '__init__.py', package / 'projection/__init__.py'):
        path.write_bytes(b'')
    (package / 'modMain.py').write_text(MOD_MAIN, encoding='ascii')
    (package / 'client_system.py').write_text(CLIENT_SYSTEM, encoding='ascii')
    manifest = {'format_version': 2,
                'header': {'name': 'Scaffold lifecycle SDK diagnostic',
                           'description': 'Native lifecycle only; no editor or projection qualification',
                           'uuid': str(uuid.uuid4()), 'version': [1, 0, 0], 'min_engine_version': [1, 21, 0]},
                'modules': [{'type': 'data', 'uuid': str(uuid.uuid4()), 'version': [1, 0, 0]}]}
    (target / 'behavior_pack/manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='ascii')
