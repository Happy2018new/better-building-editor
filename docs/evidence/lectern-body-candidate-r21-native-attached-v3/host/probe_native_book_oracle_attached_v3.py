"""Recover a native book oracle using the previously visible attached path."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time

import probe_native_book_oracle_short_v2 as short

base = short.oracle
native = base.native
HERE = Path(__file__).resolve().parent
PROJECT = base.ROOT / '.runtime/projects/book-r20-native-oracle-attached-v3'
MANIFEST = HERE / 'native-oracle-attached-v3/source-manifest.json'
MANIFEST_SHA256 = '9248eaf7a60689d33dc912083440e1d89937350b46528624657e74d44aa75f7e'
OWNER = 'book-r20-native-oracle-attached-v3'
REFERENCE = base.ROOT / '.runtime/book-r20-frontal-lectern-v1'
REFERENCE_FILES = ('08_native_placement/source.py', '09_authentic_use/source.py',
                   '11_attached_camera/source.py', 'report.json',
                   'native_lectern.book_motion0.png')
REFERENCE_SHA256 = ('a3d2ce69465c89818e89fead699b1a50ae46172fece064fea95bc0249ae4b3a3',
    '6748597344f8742684e9f3d3dfc46dc2b82a0258641deded3175b42e77a44054',
    '0fffe322464b5946ca8e02d5d7a5942802da8ca3d9e836209cdf2b993e00cd8f',
    '9ac4234c89eef6a10b9aae88206e701fdfe2574d8ea66f380b4ba216f027cd78',
    'f4f2fedef9e60c4bfcd3d8a48080a3bceba78b60f89947e7c2834356e955231c')

BUILD = base.SERVER + '''items=factory.CreateItem(saved['player'])
kind=api.GetMinecraftEnum().ItemPosType.INVENTORY
saved['oracle_inventory_before']=[items.GetPlayerItem(kind,index,True) for index in range(36)]
saved['oracle_slot']=next((index for index in range(36) if not saved['oracle_inventory_before'][index]),None)
assert saved['oracle_slot'] is not None
saved['rotation_before']=factory.CreateRot(saved['player']).GetRot()
for x in range(3):
 for y in range(3):
  for z in range(3):
   point=tuple(origin[axis]+(x,y,z)[axis] for axis in range(3))
   current=info.GetBlockNew(point,dimension)
   assert current is not None
   if current['name']!='minecraft:air':
    assert info.SetBlockNew(point,{'name':'minecraft:air','aux':0},0,dimension,True,True)
support=(target[0],target[1]-1,target[2])
assert info.SetBlockNew(support,{'name':'minecraft:cyan_concrete','aux':0},0,dimension,True,True)
assert info.SetBlockNew(target,{'name':'minecraft:lectern','aux':0},0,dimension,True,True)
platform=(target[0],target[1]-2,target[2]-3)
assert info.GetBlockNew(platform,dimension)['name']=='minecraft:air'
saved['region'].append(platform)
assert info.SetBlockNew(platform,{'name':'minecraft:stone','aux':0},0,dimension,True,False)
foot=(platform[0]+.5,platform[1]+1.,platform[2]+.5)
assert factory.CreatePos(saved['player']).SetFootPos(foot)
eye=(foot[0],foot[1]+1.62,foot[2])
aim=(target[0]+.5,target[1]+1.,target[2]+.5)
rotation=api.GetRotFromDir(tuple(aim[index]-eye[index] for index in range(3)))
assert factory.CreateRot(saved['player']).SetRot(rotation)
_result=json.dumps({'target':target,'support':support,'platform':platform,'foot':foot,'aim':aim,'rotation':rotation})
'''
PLACE = base.SERVER + '''items=factory.CreateItem(saved['player'])
kind=api.GetMinecraftEnum().ItemPosType.INVENTORY
slot=saved['oracle_slot']
assert not items.GetPlayerItem(kind,slot,True)
assert info.SetBlockNew(target,{'name':'minecraft:air','aux':0},0,dimension,True,True)
assert items.SpawnItemToPlayerInv({'itemName':'minecraft:lectern','count':1,'auxValue':0},saved['player'],slot)
placed=info.PlayerUseItemToPos((target[0],target[1]-1,target[2]),kind,slot,1)
assert placed
assert items.SetInvItemNum(slot,0)
actual=info.GetBlockNew(target,dimension)
states=factory.CreateBlockState(api.GetLevelId()).GetBlockStates(target,dimension)
assert actual=={'name':'minecraft:lectern','aux':2},(actual,states)
assert states=={'powered_bit':False,'minecraft:cardinal_direction':'north'},states
_result=json.dumps({'placed':placed,'block':actual,'states':states,'nbt':info.GetBlockEntityData(dimension,target)})
'''
ATTACH = '''cam=factory.CreateCamera(level)
cam.ResetCameraPos();cam.UnDepartCamera();cam.LockModCameraPitch(False);cam.LockModCameraYaw(False)
_result=json.dumps({'position':cam.GetPosition(),'rotation':cam.GetCameraRotation()})
'''
INITIAL_CAMERA = '''saved=sys._liquid_pose_client
player=api.GetLocalPlayerId()
foot=factory.CreatePos(player).GetFootPos()
eye=(foot[0],foot[1]+1.62,foot[2])
assert all(abs(saved['camera_pos'][index]-eye[index])<.02 for index in range(3)),(saved,foot)
_result=json.dumps({'position':saved['camera_pos'],'rotation':saved['camera_rot'],
 'pitch_lock':saved['pitch_lock'],'yaw_lock':saved['yaw_lock'],'attached_eye_verified':True})
'''
CHECK = base.CAMERA_CHECK + '''state=json.loads(_result)
player=api.GetLocalPlayerId()
state['foot']=factory.CreatePos(player).GetFootPos()
state['player_rotation']=factory.CreateRot(player).GetRot()
attached_eye=(state['foot'][0],state['foot'][1]+1.62,state['foot'][2])
assert all(abs(state['position'][index]-attached_eye[index])<.02 for index in range(3)),state
state['attached_eye_position_verified']=True
owner=api.GetSystem('ModernProjection','ModernProjectionClientSystem')
session=owner.session if owner is not None else None
preview=getattr(session,'book_preview',None) if session is not None else None
assert session is None or not session.projection_active
assert preview is None or not preview.groups
state['custom_projection_active']=False
state['custom_book_preview_groups']=0
_result=json.dumps(state)
'''
CLEAN_WORLD = '''import sys
import mod.server.extraServerApi as api
saved=getattr(sys,'_liquid_pose_world',None)
restore_player=saved['player'] if saved is not None else None
restore_foot=saved['foot_before'] if saved is not None else None
restore_rotation=saved.get('rotation_before') if saved is not None else None
if saved is not None and 'rotation_before' in saved:
 component=api.GetEngineCompFactory().CreateRot(saved['player'])
 assert component.SetRot(tuple(saved['rotation_before']))
 actual=component.GetRot()
 assert all(abs(actual[index]-saved['rotation_before'][index])<.01 for index in range(2))
''' + native.CLEAN_WORLD + '''result=json.loads(_result)
if restore_player is not None:
 actual_foot=api.GetEngineCompFactory().CreatePos(restore_player).GetFootPos()
 assert all(abs(actual_foot[index]-restore_foot[index])<.01 for index in range(3))
 result.update(foot_before=restore_foot,foot_after=actual_foot,rotation_before=restore_rotation)
 if restore_rotation is not None:
  result['rotation_after']=api.GetEngineCompFactory().CreateRot(restore_player).GetRot()
_result=json.dumps(result)
'''
CLEAN_CAMERA = '''saved=getattr(sys,'_liquid_pose_client',None)
expected_camera=dict(saved) if saved is not None else None
''' + native.CLEAN_CLIENT + '''result={'restored':True}
if expected_camera is not None:
 cam=factory.CreateCamera(level)
 position=cam.GetPosition()
 rotation=cam.GetCameraRotation()
 assert all(abs(position[index]-expected_camera['camera_pos'][index])<.02 for index in range(3)),(position,expected_camera)
 assert all(abs((rotation[index]-expected_camera['camera_rot'][index]+180.)%360.-180.)<.02 for index in range(3)),(rotation,expected_camera)
 assert cam.IsModCameraLockPitch()==expected_camera['pitch_lock']
 assert cam.IsModCameraLockYaw()==expected_camera['yaw_lock']
 result.update(position_before=expected_camera['camera_pos'],position_after=position,
  rotation_before=expected_camera['camera_rot'],rotation_after=rotation,
  pitch_lock=cam.IsModCameraLockPitch(),yaw_lock=cam.IsModCameraLockYaw())
_result=json.dumps(result)
'''


def verify():
    original = short.verify()
    assert base.sha(MANIFEST) == MANIFEST_SHA256
    frozen = json.loads(MANIFEST.read_bytes())
    assert frozen['files_sha256'] == original['source_digest']
    assert base.fingerprint(PROJECT) == frozen['files']
    assert all(frozen['config'][key] is False for key in ('auto_hot_reload_mods',
        'auto_hot_reload_ui','auto_hot_reload_shaders','auto_hot_reload_materials'))
    assert all(base.sha(REFERENCE / name) == expected for name,expected in zip(REFERENCE_FILES,REFERENCE_SHA256))
    reference = json.loads((REFERENCE / 'report.json').read_bytes())
    sample = reference['captures']['native_lectern.book_motion0']
    assert base.sha(REFERENCE / 'native_lectern.book_motion0.png') == sample['capture']['sha256']
    assert sample['book_models']['active'] is False and sample['book_models']['models'] == []
    assert sample['book_models']['preview_owned'] is False and sample['book_models']['preview_groups'] == 0
    assert reference['rows']['lectern.book']['used']['states'] == {
        'powered_bit': False, 'minecraft:cardinal_direction': 'north'}
    snippets = (native.PREPARE % 'minecraft:cyan_concrete', BUILD, PLACE, native.SAVE % ((0,0,0),),
                native.CLIENT + INITIAL_CAMERA, native.CLIENT + ATTACH, native.CLIENT + CHECK, base.ACQUIRE_INSERT,
                base.SERVER_STATE, native.CLIENT + base.CLIENT_STATE,
                base.RESTORE_INVENTORY, CLEAN_WORLD, native.CLIENT + CLEAN_CAMERA)
    for index, snippet in enumerate(snippets):
        compile(snippet, 'attached_native_book_' + str(index), 'exec')
    return {'schema': 1, 'owner': OWNER, 'project': str(PROJECT),
        'host_sha256': base.sha(Path(__file__)), 'source_digest': frozen['files_sha256'],
        'source_manifest_sha256': MANIFEST_SHA256, 'file_count': frozen['file_count'],
        'original_short_v2_binding': original, 'compiled_templates': len(snippets),
        'reference_sha256': {name: base.sha(REFERENCE / name) for name in REFERENCE_FILES},
        'planned_captures': 2, 'game_calls': 0, 'production_qualified': False,
        'native_book_pixel_oracle_qualified': False,
        'second_frame_requires_visible_native_book_review': True,
        'causal_isolation_claimed': False}


def run(args):
    binding = verify()
    session = base.load_session(args.session, OWNER, live=True)
    assert Path(session['project']).resolve() == PROJECT.resolve()
    assert base.sha(args.capture_exe) == base.SINGLE_FRAME_SHA256
    assert not args.output.exists()
    args.output.mkdir(parents=True)
    os.environ.update(MCDEV_SESSION_FILE=str(args.session), MCDEV_OWNER=OWNER, MCDEV_ALLOW_USER_FOREGROUND='1')
    report = {'schema':1, 'binding':binding, 'session':{key:session[key] for key in
        ('id','owner','game_pid','game_identity')}, 'created_at':datetime.now(timezone.utc).isoformat(),
        'completed':False,'restored':False,'cleanup_errors':[],'operations':[],'captures':[],
        'resource_boundaries':[],'native_book_pixel_oracle_qualified':False,
        'projection_tested':False,'production_qualified':False,'causal_isolation_claimed':False}
    started = time.monotonic()

    def persist():
        native.write(args.output / 'report.json', report)

    with native.Client(timeout=20) as client:
        world = camera = environment = False

        def call(label, code, server=False):
            row = {'label':label,'server':server,'code':code}
            report['operations'].append(row)
            persist()
            row['result'] = native.run(client, code, server)
            persist()
            return row['result']

        def boundary(label):
            handles = base.handles_at_boundary(args.session, OWNER)
            memory = base.commit_at_boundary()
            report['resource_boundaries'].append({'label':label,'handles':handles,'memory':memory})
            persist()
            reason = base.resource_stop(handles, memory, 200000, 6.)
            if reason or time.monotonic()-started >= 120.:
                raise RuntimeError(reason or 'Attached native oracle exceeded 120 seconds')

        def frame(label):
            boundary(label)
            before = call(label+' camera before',CHECK)
            receipt = native.capture(str(args.session),OWNER,args.output/(label+'.png'),args.capture_exe)
            after = call(label+' camera after',CHECK)
            assert receipt['reliable'] and before == after
            report['captures'].append({'label':label,'before':before,'after':after,'receipt':receipt})
            persist()

        def state(label):
            return {'server':call(label+' server',base.SERVER_STATE,True),
                    'client':call(label+' client',base.CLIENT_STATE)}

        try:
            boundary('before fixture')
            environment = True
            report['environment'] = call('save stable environment',native.ENVIRONMENT,True)
            world = True
            report['world'] = call('prepare native air region',native.PREPARE % 'minecraft:cyan_concrete',True)
            camera = True
            call('save camera',native.SAVE % (tuple(report['world']['origin']),))
            report['original_camera'] = call('verify initial attached camera',INITIAL_CAMERA)
            report['build'] = call('prepare successful sample platform and view',BUILD,True)
            time.sleep(1.)
            report['placement'] = call('actual inventory lectern placement north',PLACE,True)
            call('attached camera from successful sample',ATTACH)
            time.sleep(1.5)
            report['empty'] = state('empty native')
            assert report['empty']['client']['block'] == ['minecraft:lectern',2]
            assert base.book_signature(report['empty']['client']['nbt']) == base.book_signature(report['empty']['server']['nbt'])
            frame('native_attached_empty')
            boundary('before authored book')
            report['insert'] = call('native short authored item and actual use',base.ACQUIRE_INSERT,True)
            deadline = time.monotonic()+20.
            report['replication'] = []
            while True:
                current = state('authored native')
                report['replication'].append(current)
                expected = report['insert']['actual_inventory_item']
                if (base.book_signature(current['server']['nbt']) == base.book_signature(current['client']['nbt']) and
                    all(base.authored_data_preserved(row['nbt'],expected) for row in current.values())):
                    report['native_authored_data_and_client_replication_validated'] = True
                    break
                if time.monotonic() >= deadline:
                    raise RuntimeError('Complete authored book NBT did not converge')
                time.sleep(.4)
            time.sleep(1.5)
            frame('native_attached_authored')
            report['completed'] = len(report['captures']) == 2
            report['second_frame_requires_visible_native_book_review'] = True
        except Exception as error:
            report['error'] = type(error).__name__+': '+str(error)
            raise
        finally:
            actions = [('inventory_restore',base.RESTORE_INVENTORY,True),('world_rotation_restore',CLEAN_WORLD,True)] if world else []
            if camera:
                actions.append(('camera_restore',CLEAN_CAMERA,False))
            if environment:
                guarded = "import sys\nif hasattr(sys,'_context_environment_saved'):\n"+''.join(
                    ' '+line+'\n' for line in native.RESTORE_ENVIRONMENT.splitlines())+'\n_result=True'
                actions.append(('environment_restore',guarded,True))
            for label,code,server in actions:
                try:
                    result = call(label,code,server)
                    report[label] = result
                    if isinstance(result,dict) and result.get('restored') is False:
                        raise RuntimeError('Restoration readback differs')
                except Exception as error:
                    report['cleanup_errors'].append(label+': '+str(error))
            frozen = json.loads(MANIFEST.read_bytes())
            report['source_unchanged'] = base.fingerprint(PROJECT) == frozen['files']
            report['restored'] = not report['cleanup_errors']
            report['elapsed_seconds'] = time.monotonic()-started
            persist()
    print(json.dumps({key:report[key] for key in ('completed','restored','source_unchanged')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action',required=True)
    sub.add_parser('verify')
    command = sub.add_parser('run')
    command.add_argument('--session',type=Path,required=True)
    command.add_argument('--capture-exe',type=Path,required=True)
    command.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    print(json.dumps(verify())) if args.action == 'verify' else run(args)
