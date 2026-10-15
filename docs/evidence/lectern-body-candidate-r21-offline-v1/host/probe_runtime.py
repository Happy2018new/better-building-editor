"""Prepared owner-bound experiment. Never starts or activates a game."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import probe_liquid_pose_channel as native
from probe_product_water import snapshot_sources
from verify_debug_blueprints import CLIENT

SINGLE_FRAME_SHA256 = 'cb9122a6713e9c627ee9ea7658e7610e7f72d7b451412b0c6331a5bb1fbcb5a8'
VIEWS = {'south': (0., 1.8, 5.8), 'north': (0., 1.8, -5.8),
         'east': (5.8, 1.8, 0.), 'west': (-5.8, 1.8, 0.)}
SCENES = {'plain': (), 'upper': ((0, 2, 1), (2, 2, 1)), 'side': ((1, 1, 1),)}

INSTALL = CLIENT + '''from modern_projection.projection import lectern_body
assert api.GetEngineVersion()=='3.10.0.420447'
assert not s.busy and s.edit_job is None and s.io_job is None
assert not s.projection_active and not b.preparing_entity
assert not navigator.is_transitioning
assert navigator.top is None or navigator.top.key=='modern_projection_workspace'
assert not hasattr(sys,'_lectern_body_r21')
assert lectern_body.CANDIDATE_ENABLED is False
assert s.book_profile is not None
fields=('page','name','view','focus_view','section','solo_layer','focused','box_anchor',
 'canvas_x','canvas_z','paste_origin','paste_pinned','camera_pose','camera_yaw',
 'camera_pitch','zoom','camera_pan','camera_pivot','camera_depth','camera_depth_pose',
 'camera_focus_request','camera_reset_animated','progress','direct_mode',
 'origin','opacity','projection_missing','projection_outline','grid')
saved={'editor':s.editor,'fields':dict((key,getattr(s,key)) for key in fields),
 'factory':b.factory,'workspace':navigator.top is not None,'book_profile':s.book_profile,
 'gate':lectern_body.CANDIDATE_ENABLED,'receipts':[]}
sys._lectern_body_r21=saved
lectern_body.CANDIDATE_ENABLED=True
class LecternGeometryReceipt(object):
 def __init__(self,target):self.target=target
 def __getattr__(self,name):return getattr(self.target,name)
 def CombineBlockPaletteToGeometry(self,palette,name,mode=0):
  data=palette.SerializeBlockPalette()
  result=self.target.CombineBlockPaletteToGeometry(palette,name,mode)
  saved=sys._lectern_body_r21
  saved['receipts'].append({'name':name,'result':result,'volume':data['volume'],
   'common':repr(data.get('common',{})),'actor':repr(data.get('actor',{})),
   'lectern_indices':[index for material,indices in data.get('common',{}).items()
    if material[0]=='minecraft:lectern' for index in indices]})
  return result
class LecternFactoryReceipt(object):
 def __init__(self,target):self.target=target
 def __getattr__(self,name):return getattr(self.target,name)
 def CreateBlockGeometry(self,level):return LecternGeometryReceipt(self.target.CreateBlockGeometry(level))
b.factory=LecternFactoryReceipt(b.factory)
if navigator.top is not None:navigator.pop()
_result={'engine':api.GetEngineVersion(),'book_profile':s.book_profile.identity,'candidate':True}
'''

SERVER = '''import json,sys
import mod.server.extraServerApi as api
saved=sys._liquid_pose_world
factory=api.GetEngineCompFactory()
info=factory.CreateBlockInfo(saved['player'])
dimension=saved['dimension']
origin=tuple(saved['origin'])
def world(pos):return tuple(origin[axis]+pos[axis] for axis in range(3))
'''

BUILD_WORLD = SERVER + '''for x in range(4):
 for y in range(4):
  for z in range(3):
   assert info.SetBlockNew(world((x,y,z)),{'name':'minecraft:air','aux':0},0,dimension,True,False)
for x in (0,2):
 assert info.SetBlockNew(world((x,0,1)),{'name':'minecraft:cyan_concrete','aux':0},0,dimension,True,False)
 assert info.SetBlockNew(world((x,1,1)),{'name':'minecraft:lectern','aux':1},0,dimension,True,False)
extras=%r
for position in extras:
 assert info.SetBlockNew(world(position),{'name':'minecraft:stone','aux':0},0,dimension,True,False)
_result=True
'''

USE_BOOK = SERVER + '''
items=factory.CreateItem(saved['player'])
item_type=api.GetMinecraftEnum().ItemPosType.INVENTORY
slot=next((index for index in range(36) if not items.GetPlayerItem(item_type,index,True)),None)
assert slot is not None
saved['book_slot']=slot
assert items.SpawnItemToPlayerInv({'itemName':'minecraft:writable_book','count':1,'auxValue':0},saved['player'],slot)
used=info.PlayerUseItemToPos(world((2,1,1)),item_type,slot,1)
assert items.SetInvItemNum(slot,0)
_result=json.dumps({'used':used,'rows':[{'position':pos,
 'block':info.GetBlockNew(world(pos),dimension),
 'states':factory.CreateBlockState(api.GetLevelId()).GetBlockStates(world(pos),dimension),
 'nbt':info.GetBlockEntityData(dimension,world(pos))} for pos in ((0,1,1),(2,1,1))]})
'''

READ_DOCUMENT = CLIENT + '''from modern_projection.projection.model import Document
from modern_projection.projection.cell import AIR,make_cell,actor_data,foreground
from modern_projection.projection.visible_actor import compose_actor
from modern_projection.projection.entity_render import native_actor
from modern_projection.projection.nbt_spatial import rebase
from modern_projection.projection.book_render_plan import appearance
saved=sys._lectern_body_r21
origin=tuple(sys._liquid_pose_client['origin'])
rows=json.loads(%r)
high=tuple(origin[axis]+(3,3,2)[axis] for axis in range(3))
palette=factory.CreateBlock(level).GetBlockPaletteBetweenPos(origin,high,False)
assert palette is not None
raw=palette.SerializeBlockPalette()
assert tuple(raw['volume'])==(3,4,4),raw['volume']
common=dict((index,material) for material,indices in raw['common'].items() for index in indices)
extra=dict((index,material) for material,indices in raw.get('extra',{}).items() for index in indices)
actors=dict((index,payload) for name,entries in raw.get('actor',{}).items() for index,payload in entries.items())
nbt=dict((tuple(row['position']),row['nbt']) for row in rows)
doc=Document((4,4,3))
for index,material in common.items():
 if material==AIR:continue
 position=(index//3%%4,index//12,index%%3)
 actor=actors.get(index)
 if position in nbt:
  assert material[0]=='minecraft:lectern'
  assert material==(rows[0]['block']['name'],rows[0]['block']['aux'])
  assert actor=={},(position,actor)
  actor=compose_actor(actor,rebase(nbt[position],tuple(-value for value in origin)))
 doc.set_cell(position,make_cell(material,extra.get(index,AIR),actor))
inputs=[(foreground(doc.get(pos)),native_actor(foreground(doc.get(pos)),actor_data(doc.get(pos))))
 for pos in ((0,1,1),(2,1,1))]
assert inputs[0]==inputs[1] and inputs[0][1]=={},inputs
books=[appearance(foreground(doc.get(pos)),actor_data(doc.get(pos)),api.GetEngineVersion())
 for pos in ((0,1,1),(2,1,1))]
assert books[0] is None and books[1] is not None and books[1][0]=='lectern',books
saved['document']=doc.to_data()
_result=json.dumps({'document':doc.to_data(),'raw_common':repr(raw['common']),
 'raw_actor':repr(raw.get('actor',{})),'native_body_inputs':inputs,'logical_book_appearance':books,
 'native_input_equal_for_empty_and_book':inputs[0]==inputs[1],
 'native_render_actor_empty':all(item[1]=={} for item in inputs)})
'''

REMOVE_WORLD = SERVER + '''keep=%r
for x in range(4):
 for y in range(4):
  for z in range(3):
   if keep and (x,y,z) in ((0,0,1),(2,0,1),(0,1,1),(2,1,1)):continue
   assert info.SetBlockNew(world((x,y,z)),{'name':'minecraft:air','aux':0},0,dimension,True,False)
_result=True
'''

CLEAN_INVENTORY = '''import sys
import mod.server.extraServerApi as api
saved=getattr(sys,'_liquid_pose_world',None)
if saved is not None and 'book_slot' in saved:
 assert api.GetEngineCompFactory().CreateItem(saved['player']).SetInvItemNum(saved['book_slot'],0)
_result=True
'''

LOAD_DOCUMENT = CLIENT + '''from modern_projection.projection.model import Document
saved=sys._lectern_body_r21
b.stop_projection()
s.book_profile=saved['book_profile'] if %r else None
s.tiles.cancel();s.tiles.parts.clear();s.tiles.context=None
s._loaded(Document.from_data(saved['document']))
s.grid=False;s.opacity=1.;s.projection_outline=False
owner.open_workspace()
s.emit()
_result=True
'''

PROJECT = CLIENT + '''if navigator.top is not None:navigator.pop()
s.origin=tuple(sys._liquid_pose_client['origin'])
s.projection_missing=%r
b.project()
_result=True
'''

STATE = CLIENT + '''work=b.projection_work
companion=b.projection_liquid
owners=getattr(companion,'companions',(companion,)) if companion else ()
tracker=b.projection_occupancy
shader=tracker.shader if tracker is not None else getattr(b,'projection_shader',None)
_result=json.dumps({'preview_ready':s.ready and not s.preview_pending and not s.tiles.running and not s.tiles.dirty,
 'preview_error':s.preview_error,'work_ready':bool(work and work.ready),'error':work.error if work else None,
 'active':s.projection_active,'preparing':bool(b.preparing_entity),
 'parts':b.context_models.get(b.projection_mesh[1],()) if b.projection_mesh else (),
 'shader_uniforms':getattr(shader,'uniforms',{}),
 'book_models':sum(len(value.renderer.active) for value in owners if type(value).__name__=='BookProjection'),
 'book_ready':all(value.ready and not value.error for value in owners if type(value).__name__=='BookProjection'),
 'logical_source_unchanged':s.editor.document.to_data()==sys._lectern_body_r21['document'],
 'top':navigator.top.key if navigator.top is not None else None,
 'occupancy':list(tracker.state) if tracker is not None else None})
'''

RESTORE = CLIENT + '''from modern_projection.projection import lectern_body
saved=getattr(sys,'_lectern_body_r21',None)
if saved is not None:
 b.stop_projection()
 b.factory=saved['factory']
 s.tiles.cancel()
 s.editor=saved['editor']
 s.book_profile=saved['book_profile']
 lectern_body.CANDIDATE_ENABLED=saved['gate']
 for key,value in saved['fields'].items():setattr(s,key,value)
 s.model_revision=None;s.camera_reset_revision+=1
 s.refresh_preview();s.emit()
 if saved['workspace'] and navigator.top is None:owner.open_workspace()
 if not saved['workspace'] and navigator.top is not None:navigator.pop()
 del sys._lectern_body_r21
_result=True
'''


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--capture-exe', type=Path, required=True)
    parser.add_argument('--scene', action='append', choices=tuple(SCENES))
    args = parser.parse_args()
    session = json.loads(args.session.read_bytes())
    if session['owner'] != args.owner or Path(session['project']).resolve() != args.project.resolve():
        parser.error('Use the exact owned session/project')
    if args.output.exists() or sha(args.capture_exe) != SINGLE_FRAME_SHA256:
        parser.error('Use a fresh output and the verified single-frame helper')
    args.output.mkdir(parents=True)
    os.environ.update(MCDEV_SESSION_FILE=str(args.session.resolve()), MCDEV_OWNER=args.owner,
                      MCDEV_ALLOW_USER_FOREGROUND='1')
    sources = snapshot_sources(args.project)
    config = json.loads((args.project / '.mcdev.json').read_bytes())
    if any(config.get(key) is not False for key in ('auto_hot_reload_mods', 'auto_hot_reload_ui',
                                                   'auto_hot_reload_shaders', 'auto_hot_reload_materials')):
        parser.error('The cold candidate must keep all hot reload settings false')
    report = dict(schema=1, stage='isolated_native_lectern_candidate',
        created_at=datetime.now(timezone.utc).isoformat(), completed=False, restored=False,
        product_qualified=False, pixel_acceptance_claimed=False, source_sha256=sources,
        host_sha256=sha(Path(__file__)), capture_exe_sha256=sha(args.capture_exe),
        config_sha256=sha(args.project / '.mcdev.json'),
        host_dependencies={name: sha(ROOT/'tools'/name) for name in (
            'probe_liquid_pose_channel.py', 'probe_product_water.py', 'capture_native_window.py',
            'verify_debug_blueprints.py', 'context_test_environment.py', 'verify_biome_shader.py')},
        session={key: session[key] for key in ('id', 'owner', 'game_pid', 'game_identity')},
        captures={}, scenes={}, cleanup_errors=[],
        limits=['Cyan-only independent positive control is a separate base-host run.',
                'Body candidate changes target-only native routing; shared shaders and book meshes are unchanged.',
                'Genuine native book and empty lectern coexist in each scene.'])
    def persist():
        native.write(args.output / 'report.json', report)
    with native.Client(timeout=40) as client:
        installed = world = saved = environment = False
        def call(code, server=False):
            return native.run(client, code, server)
        def wait(predicate, timeout=35.):
            deadline = time.monotonic()+timeout
            while True:
                state = call(STATE)
                if state['preview_error'] or state['error']:
                    raise RuntimeError('Public route failed: '+repr(state))
                if predicate(state):
                    return state
                if time.monotonic()>deadline:
                    raise TimeoutError('Public route did not settle: '+repr(state))
                time.sleep(.25)
        def frame(label, view, projected=False):
            camera = native.CAMERA.replace('target=(origin[0]+.5,origin[1]+.5,origin[2]+.5)',
                'target=(origin[0]+1.5,origin[1]+1.5,origin[2]+1.5)')
            camera = camera.replace('offset=(3.,3.,5.)', 'offset='+repr(VIEWS[view]))
            camera_state = call(camera)
            time.sleep(.5)
            check = native.CAMERA_CHECK.replace('target=tuple(axis+.5 for axis in origin)',
                'target=(origin[0]+1.5,origin[1]+1.5,origin[2]+1.5)')
            before = call(check)
            path = args.output/(label+'_'+view+'.png')
            receipt = native.capture(str(args.session), args.owner, path, args.capture_exe)
            after = call(check)
            if before != after or receipt.get('reliable') is not True:
                raise RuntimeError('Unreliable capture or camera changed')
            report['captures'][label+'_'+view] = dict(receipt=receipt, camera=camera_state,
                before=before, after=after, route_state=call(STATE) if projected else None)
            persist()
        def build_world(scene):
            call(BUILD_WORLD % (SCENES[scene],), True)
            for position in ((0, 1, 1), (2, 1, 1)):
                target = tuple(origin[axis]+position[axis] for axis in range(3))
                deadline = time.monotonic()+20.
                while True:
                    value = call(native.REPLICATION % (target,))
                    if any(row['name']=='minecraft:lectern' and row['aux']==1
                           for row in value['materials']):
                        break
                    if time.monotonic()>deadline:
                        raise TimeoutError('Lectern placement did not reach the client')
                    time.sleep(.25)
            return call(USE_BOOK, True)
        try:
            installed = True
            report['installed'] = call(INSTALL)
            environment = True
            report['environment'] = call(native.ENVIRONMENT, True)
            world = True
            report['world'] = call(native.PREPARE % 'minecraft:cyan_concrete', True)
            origin = tuple(report['world']['origin'])
            report['near_player'] = call(native.NEAR_PLAYER, True)
            saved = True
            call(native.SAVE % (origin,))
            for scene in args.scene or SCENES:
                call(CLIENT+'b.stop_projection()\n_result=True')
                reference = build_world(scene)
                time.sleep(1.2)
                row = report['scenes'][scene] = {'world': reference}
                row['source'] = call(READ_DOCUMENT % json.dumps(reference['rows']))
                for view in VIEWS:
                    frame(scene+'_world', view)
                for phase, books, missing in (('body_only', False, False),
                        ('full', True, False), ('missing', True, True),
                        ('excluded', True, False), ('present', True, True)):
                    call(CLIENT+'b.stop_projection()\n_result=True')
                    if phase == 'present':
                        row['present_world'] = build_world(scene)
                    call(REMOVE_WORLD % (phase == 'present'), True)
                    time.sleep(.7)
                    call(LOAD_DOCUMENT % books)
                    wait(lambda state: state['preview_ready'])
                    if phase == 'excluded':
                        call(CLIENT+"s.toggle_layer('hide',1)\ns.emit()\n_result=True")
                        wait(lambda state: state['preview_ready'])
                    call(CLIENT+"sys._lectern_body_r21['receipts']=[]\n_result=True")
                    call(PROJECT % missing)
                    expected_books = int(books and phase not in ('present', 'excluded'))
                    state = wait(lambda state: state['work_ready'] and not state['preparing']
                        and state['book_ready'] and state['book_models'] == expected_books)
                    if not state['logical_source_unchanged']:
                        raise RuntimeError('Public route mutated logical source')
                    receipts = call(CLIENT+"_result=json.dumps(sys._lectern_body_r21['receipts'])")
                    active = {part[0]: part[2] for part in state['parts']}
                    body_count = 0
                    for receipt in receipts:
                        if receipt['result'] not in active:
                            continue
                        if active[receipt['result']] and receipt['lectern_indices']:
                            raise RuntimeError('Native lectern leaked into a packed context part')
                        body_count += len(receipt['lectern_indices'])
                    if body_count != (0 if phase in ('present', 'excluded') else 2):
                        raise RuntimeError('Unexpected target-only lectern body count: '+repr(receipts))
                    row[phase] = {'state': state, 'receipts': receipts, 'target_body_count': body_count}
                    for view in VIEWS:
                        frame(scene+'_'+phase, view, True)
            report['completed'] = True
        except Exception as error:
            report['error'] = type(error).__name__+': '+str(error)
            persist()
            raise
        finally:
            actions = [('projection_stop', CLIENT+'b.stop_projection()\n_result=True', False)] if installed else []
            if world:
                actions.append(('inventory_restore', CLEAN_INVENTORY, True))
                actions.append(('world_restore', native.CLEAN_WORLD, True))
            if saved:
                actions.append(('camera_restore', native.CLEAN_CLIENT, False))
            if environment:
                guarded = "if hasattr(sys,'_context_environment_saved'):\n" + ''.join(
                    ' '+line+'\n' for line in native.RESTORE_ENVIRONMENT.splitlines()) + '\n_result=True'
                actions.append(('environment_restore', 'import sys\n'+guarded, True))
            if installed:
                actions.append(('session_restore', RESTORE, False))
            for label, code, server in actions:
                try:
                    report[label] = call(code, server)
                except Exception as error:
                    report['cleanup_errors'].append(label+': '+str(error))
            report['source_unchanged'] = sources == snapshot_sources(args.project)
            report['restored'] = not report['cleanup_errors']
            persist()
    print(json.dumps({key: report[key] for key in ('completed', 'restored', 'source_unchanged')}))


if __name__ == '__main__':
    main()
