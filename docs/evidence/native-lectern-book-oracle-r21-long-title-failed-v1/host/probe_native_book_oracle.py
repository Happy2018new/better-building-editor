"""Offline-prepared native lectern book control; never starts a game."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / '.agents/skills/pyreact-debugging/scripts')]
import probe_liquid_pose_channel as native
from census_intrinsic_glint_ui_r21 import commit_at_boundary, handles_at_boundary, resource_stop
from freeze_intrinsic_glint_project_r21 import fingerprint
from _session import load_session


PROJECT = ROOT / '.runtime/projects/root-signed-book-r21-v1'
SOURCE_MANIFEST = ROOT / '.runtime/signed-book-r21/source-manifest.json'
SOURCE_MANIFEST_SHA256 = 'cc57450722012534f51238d4442a96021ea26bd447066f1a0f6bef953f342d25'
SOURCE_DIGEST = '2db60ade9dae57a155f6da01f715abee5cc2aa5abae4506ac40a3003e1b42e4a'
OWNER = 'book-r20-native-oracle-v1'
SINGLE_FRAME_SHA256 = 'cb9122a6713e9c627ee9ea7658e7610e7f72d7b451412b0c6331a5bb1fbcb5a8'
SERVER = '''import json,sys,copy
import mod.server.extraServerApi as api
saved=sys._liquid_pose_world
factory=api.GetEngineCompFactory()
info=factory.CreateBlockInfo(saved['player'])
dimension=saved['dimension']
origin=tuple(saved['origin'])
target=tuple(origin[axis]+(1,1,1)[axis] for axis in range(3))
'''
BUILD = SERVER + '''for x in range(3):
 for y in range(3):
  for z in range(3):
   point=tuple(origin[axis]+(x,y,z)[axis] for axis in range(3))
   current=info.GetBlockNew(point,dimension)
   assert current is not None
   if current['name']!='minecraft:air':
    assert info.SetBlockNew(point,{'name':'minecraft:air','aux':0},0,dimension,True,False)
assert info.SetBlockNew((origin[0]+1,origin[1],origin[2]+1),{'name':'minecraft:cyan_concrete','aux':0},0,dimension,True,False)
assert info.SetBlockNew(target,{'name':'minecraft:lectern','aux':3},0,dimension,True,False)
items=factory.CreateItem(saved['player'])
kind=api.GetMinecraftEnum().ItemPosType.INVENTORY
saved['oracle_inventory_before']=[items.GetPlayerItem(kind,index,True) for index in range(36)]
saved['oracle_slot']=next((index for index in reversed(range(36)) if not saved['oracle_inventory_before'][index]),None)
assert saved['oracle_slot'] is not None
_result=True
'''
ACQUIRE_INSERT = SERVER + '''from modern_projection.projection.nbt_spatial import root_payload,field_key,scalar
loot=factory.CreateLoot(saved['player']).GetLootItems('loot_tables/modern_projection/r21_signed_book.json','-1','-1',0.0,True)
assert len(loot)==2,loot
source=copy.deepcopy(loot[0])
submitted=copy.deepcopy(source)
submitted['itemName']=submitted.get('newItemName',submitted.get('itemName'))
submitted['auxValue']=submitted.get('newAuxValue',submitted.get('auxValue',0))
assert submitted['itemName']=='minecraft:written_book' and submitted['count']==1,submitted
tags=root_payload(submitted.get('userData')) or {}
assert scalar(tags,'title')=='R21 Native Authored Book A',tags
assert scalar(tags,'author')=='R21 Native Loot',tags
assert field_key(tags,'pages') is not None,tags
items=factory.CreateItem(saved['player'])
kind=api.GetMinecraftEnum().ItemPosType.INVENTORY
slot=saved['oracle_slot']
assert items.SpawnItemToPlayerInv(submitted,saved['player'],slot)
actual=items.GetPlayerItem(kind,slot,True)
enchantments=items.GetInvItemEnchantData(slot)
assert actual.get('userData')==source.get('userData'),(actual,source)
assert not enchantments,enchantments
saved['oracle_actual_item']=copy.deepcopy(actual)
used=info.PlayerUseItemToPos(target,kind,slot,1)
remaining=items.GetPlayerItem(kind,slot,True)
assert used
_result=json.dumps({'native_loot_items':loot,'submitted_native_item':submitted,'actual_inventory_item':actual,
 'actual_enchantments':enchantments,'native_use_return':used,'inventory_after_use':remaining,
 'item_data_manufactured':False,'nbt_setter_used':False})
'''
SERVER_STATE = SERVER + '''_result=json.dumps({'block':info.GetBlockNew(target,dimension),
 'states':factory.CreateBlockState(api.GetLevelId()).GetBlockStates(target,dimension),
 'nbt':info.GetBlockEntityData(dimension,target)})
'''
CLIENT_STATE = '''origin=tuple(sys._liquid_pose_client['origin'])
target=tuple(origin[axis]+(1,1,1)[axis] for axis in range(3))
info=factory.CreateBlockInfo(level)
palette=factory.CreateBlock(level).GetBlockPaletteBetweenPos(target,target,False)
raw=palette.SerializeBlockPalette() if palette is not None else {}
_result=json.dumps({'block':info.GetBlock(target),'nbt':info.GetBlockEntityData(target),
 'raw_common':repr(raw.get('common',{})),'raw_actor':repr(raw.get('actor',{}))})
'''
RESTORE_INVENTORY = SERVER + '''items=factory.CreateItem(saved['player'])
kind=api.GetMinecraftEnum().ItemPosType.INVENTORY
if 'oracle_slot' in saved:
 slot=saved['oracle_slot']
 current=items.GetPlayerItem(kind,slot,True)
 if current:assert items.SetInvItemNum(slot,0)
after=[items.GetPlayerItem(kind,index,True) for index in range(36)]
before=saved.get('oracle_inventory_before',after)
_result=json.dumps({'restored':after==before,'before':before,'after':after})
'''
CAMERA = native.CAMERA.replace('target=(origin[0]+.5,origin[1]+.5,origin[2]+.5)',
    'target=(origin[0]+1.5,origin[1]+1.5,origin[2]+1.5)').replace('offset=(3.,3.,5.)','offset=(3.,2.4,5.)')
CAMERA_CHECK = native.CAMERA_CHECK.replace('target=tuple(axis+.5 for axis in origin)',
    'target=(origin[0]+1.5,origin[1]+1.5,origin[2]+1.5)')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compound(data):
    if not isinstance(data, dict):
        return {}
    if data.get('__type__') in (10, 'TAG_Compound'):
        return data.get('__value__', {})
    return data


def value(data, key):
    result = compound(data).get(key)
    return result.get('__value__') if isinstance(result, dict) else result


def book_signature(nbt):
    root = compound(nbt)
    return {'hasBook': value(root, 'hasBook'), 'page': value(root, 'page'),
            'totalPages': value(root, 'totalPages'), 'book': root.get('book')}


def authored_data_preserved(nbt, native_item):
    root = compound(nbt)
    book = compound(root.get('book'))
    tags = compound(book.get('tag'))
    expected = compound(native_item.get('userData'))
    pages = value(expected, 'pages')
    return bool(value(root, 'hasBook') == 1 and value(root, 'totalPages') and
        value(book, 'Name') == 'minecraft:written_book' and value(book, 'Count') == 1 and
        pages and all(tags.get(key) == entry for key, entry in expected.items()))


def verify():
    assert sha(SOURCE_MANIFEST) == SOURCE_MANIFEST_SHA256
    frozen = json.loads(SOURCE_MANIFEST.read_bytes())
    assert frozen['files_sha256'] == SOURCE_DIGEST and fingerprint(PROJECT) == frozen['files']
    config = json.loads((PROJECT / '.mcdev.json').read_bytes())
    assert all(config.get(key) is False for key in ('auto_hot_reload_mods', 'auto_hot_reload_ui',
                                                   'auto_hot_reload_shaders', 'auto_hot_reload_materials'))
    snippets = (SERVER, BUILD, ACQUIRE_INSERT, SERVER_STATE, native.CLIENT + CLIENT_STATE,
                RESTORE_INVENTORY, native.CLIENT + CAMERA, native.CLIENT + CAMERA_CHECK)
    for index, snippet in enumerate(snippets):
        compile(snippet, 'native_oracle_' + str(index), 'exec')
    return {'schema': 1, 'project': str(PROJECT), 'owner': OWNER, 'source_digest': SOURCE_DIGEST,
        'source_manifest_sha256': sha(SOURCE_MANIFEST), 'host_sha256': sha(Path(__file__)),
        'compiled_templates': len(snippets), 'game_calls': 0, 'planned_captures': 5,
        'projection_tested': False, 'production_qualified': False,
        'dependencies': {name: sha(ROOT / 'tools' / name) for name in (
            'probe_liquid_pose_channel.py', 'capture_native_window.py',
            'census_intrinsic_glint_ui_r21.py', 'freeze_intrinsic_glint_project_r21.py')}}


def run(args):
    binding = verify()
    session = load_session(args.session, OWNER, live=True)
    assert Path(session['project']).resolve() == PROJECT.resolve()
    assert sha(args.capture_exe) == SINGLE_FRAME_SHA256
    assert not args.output.exists()
    args.output.mkdir(parents=True)
    os.environ.update(MCDEV_SESSION_FILE=str(args.session), MCDEV_OWNER=OWNER, MCDEV_ALLOW_USER_FOREGROUND='1')
    report = {'schema': 1, 'binding': binding, 'session': {key: session[key] for key in
        ('id', 'owner', 'game_pid', 'game_identity')}, 'created_at': datetime.now(timezone.utc).isoformat(),
        'completed': False, 'restored': False, 'cleanup_errors': [], 'operations': [], 'captures': [],
        'resource_boundaries': [], 'projection_tested': False, 'production_qualified': False,
        'native_book_pixel_oracle_qualified': False}
    started = time.monotonic()

    def persist():
        native.write(args.output / 'report.json', report)

    with native.Client(timeout=20) as client:
        world = camera = environment = False

        def call(label, code, server=False):
            row = {'label': label, 'server': server, 'code': code}
            report['operations'].append(row)
            persist()
            row['result'] = native.run(client, code, server)
            persist()
            return row['result']

        def boundary(label):
            handles = handles_at_boundary(args.session, OWNER)
            memory = commit_at_boundary()
            report['resource_boundaries'].append({'label': label, 'handles': handles, 'memory': memory})
            persist()
            reason = resource_stop(handles, memory, 200000, 6.)
            if reason or time.monotonic() - started >= 120.:
                raise RuntimeError(reason or 'Native book oracle exceeded 120 seconds')

        def frame(label):
            boundary(label)
            before = call(label + ' camera before', CAMERA_CHECK)
            receipt = native.capture(str(args.session), OWNER, args.output / (label + '.png'), args.capture_exe)
            after = call(label + ' camera after', CAMERA_CHECK)
            assert receipt['reliable'] and before == after
            report['captures'].append({'label': label, 'before': before, 'after': after, 'receipt': receipt})
            persist()

        try:
            boundary('before fixture')
            environment = True
            report['environment'] = call('save stable environment', native.ENVIRONMENT, True)
            world = True
            report['world'] = call('prepare native air region', native.PREPARE % 'minecraft:cyan_concrete', True)
            report['near_player'] = call('move to owned support', native.NEAR_PLAYER, True)
            camera = True
            call('save native camera', native.SAVE % (tuple(report['world']['origin']),))
            call('single east unpowered empty lectern', BUILD, True)
            call('fixed native camera', CAMERA)
            time.sleep(2.)
            report['empty_server'] = call('empty complete server NBT', SERVER_STATE, True)
            report['empty_client'] = call('empty complete client NBT and palette', CLIENT_STATE)
            for phase in range(2):
                time.sleep(.7)
                frame('native_empty_' + str(phase))
            boundary('before actual authored book')
            report['insert'] = call('native authored A and real inventory insertion', ACQUIRE_INSERT, True)
            deadline = time.monotonic() + 20.
            report['replication'] = []
            while True:
                server_state = call('authored complete server NBT', SERVER_STATE, True)
                client_state = call('authored complete client NBT and palette', CLIENT_STATE)
                equal = book_signature(server_state['nbt']) == book_signature(client_state['nbt'])
                report['replication'].append({'server': server_state, 'client': client_state, 'book_signature_equal': equal})
                actual = report['insert']['actual_inventory_item']
                if equal and all(authored_data_preserved(state['nbt'], actual) for state in (server_state, client_state)):
                    report['native_authored_data_and_client_replication_validated'] = True
                    break
                if time.monotonic() >= deadline:
                    raise RuntimeError('Complete authored native book NBT did not converge; no oracle qualification')
                time.sleep(.4)
            for phase in range(3):
                time.sleep(.7)
                frame('native_authored_' + str(phase))
            report['completed'] = len(report['captures']) == 5
        except Exception as error:
            report['error'] = type(error).__name__ + ': ' + str(error)
            raise
        finally:
            actions = [('inventory_restore', RESTORE_INVENTORY, True), ('world_restore', native.CLEAN_WORLD, True)] if world else []
            if camera:
                actions.append(('camera_restore', native.CLEAN_CLIENT, False))
            if environment:
                guarded = "import sys\nif hasattr(sys,'_context_environment_saved'):\n" + ''.join(
                    ' ' + line + '\n' for line in native.RESTORE_ENVIRONMENT.splitlines()) + '\n_result=True'
                actions.append(('environment_restore', guarded, True))
            for label, code, server in actions:
                try:
                    result = call(label, code, server)
                    report[label] = result
                    if isinstance(result, dict) and result.get('restored') is False:
                        raise RuntimeError('Restoration readback differs')
                except Exception as error:
                    report['cleanup_errors'].append(label + ': ' + str(error))
            frozen = json.loads(SOURCE_MANIFEST.read_bytes())
            report['source_unchanged'] = fingerprint(PROJECT) == frozen['files']
            report['restored'] = not report['cleanup_errors']
            report['elapsed_seconds'] = time.monotonic() - started
            persist()
    print(json.dumps({key: report[key] for key in ('completed', 'restored', 'source_unchanged')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('verify')
    command = sub.add_parser('run')
    command.add_argument('--session', type=Path, required=True)
    command.add_argument('--capture-exe', type=Path, required=True)
    command.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.action == 'verify':
        print(json.dumps(verify()))
    else:
        run(args)
