"""Observe native item interaction on one cell selected from a public blueprint."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import uuid

from verify_debug_blueprints import Client, write_json
from verify_native_entity_appearances import execute, replicated_palettes, native_runtime_evidence

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_PLAN = '''import sys
from modern_projection.projection import block_registry
from modern_projection.projection.block_groups import group_partner
from modern_projection.projection.cell import actor_data,foreground
from modern_projection.projection.debug_blueprints import build,entries
from modern_projection.projection.visible_actor import entity_nbt
request=%r
assert request['fixture'] in tuple(row[0] for row in entries('entities')), request
assert not hasattr(sys,'_p0_entity_appearances'), 'Clean up the previous entity fixture first'
assert not hasattr(sys,'_p0_entity_appearance_selected'), 'A different entity probe is selected'
assert not hasattr(sys,'_p0_entity_appearance_public_plans'), 'A public entity plan is already pending'
document=build(request['fixture'])
candidates=sorted(pos for pos,cell in document.blocks.items()
                  if foreground(cell)[0]==request['material'] and actor_data(cell) is not None)
source=request['source_cell']
if source is None:
 assert len(candidates)==1, ('Select one public source cell explicitly', candidates)
 source=candidates[0]
source=tuple(source)
assert source in candidates, ('Material is absent at the public source cell',source,candidates)
cell=document.get(source)
value=foreground(cell)
assert group_partner(value) is None, 'This probe samples one block, not a multiblock placement'
sys._p0_entity_appearance_public_plans=[{
 'case':'%%s@%%s'%%(request['fixture'],','.join(str(v) for v in source)),
 'name':value[0],'expected_block':value[0],
 'placement_item':request['placement_item'] or value[0],
 'face':request['placement_face'],'yaw':request['yaw'],'aux':request['placement_aux'],
 'content_probe':True,'public_fixture':request['fixture'],'public_source':source,
 'probe_nonce':request['nonce'],
 'public_material':value,'public_states':block_registry.states(value),
 'public_entity_nbt':entity_nbt(actor_data(cell))}]
'''
INTERACT = '''import json,sys
import mod.server.extraServerApi as api
request=%r
saved=sys._p0_entity_appearances
assert saved['rows'][0].get('probe_nonce')==request['nonce'], 'Native fixture ownership changed'
factory=api.GetEngineCompFactory()
items,info=factory.CreateItem(saved['player']),factory.CreateBlockInfo(saved['player'])
item_type=api.GetMinecraftEnum().ItemPosType.INVENTORY
row=saved['rows'][0]
target=tuple(row['pos'])
before=info.GetBlockEntityData(saved['dimension'],target)
before_block=info.GetBlockNew(target,saved['dimension'])
assert items.SetInvItemNum(saved['slot'],0), 'Temporary inventory slot did not clear'
spawn=items.SpawnItemToPlayerInv({'itemName':request['item'],'auxValue':request['item_aux'],
                                'count':1},saved['player'],saved['slot'])
inventory_before=items.GetPlayerItem(item_type,saved['slot'],True)
enchants_before=items.GetInvItemEnchantData(saved['slot'])
enchantment=request['enchantment']
added=None
if enchantment is not None and spawn and inventory_before:
 added=items.AddEnchantToInvItem(saved['slot'],enchantment[0],enchantment[1])
inventory_after=items.GetPlayerItem(item_type,saved['slot'],True)
enchants_after=items.GetInvItemEnchantData(saved['slot'])
item_confirmed=bool(inventory_after and inventory_after.get('itemName')==request['item']
                    and inventory_after.get('count',0)>=1)
enchantment_confirmed=(enchantment is None or bool(added and
                       tuple(map(tuple,enchants_after or ()))==(tuple(enchantment),)))
used=False
if spawn and item_confirmed and enchantment_confirmed:
 used=info.PlayerUseItemToPos(target,item_type,saved['slot'],request['interaction_face'])
after=info.GetBlockEntityData(saved['dimension'],target)
after_block=info.GetBlockNew(target,saved['dimension'])
result={'native_spawn_return':spawn,'inventory_before':inventory_before,
 'inventory_before_enchants':enchants_before,'native_add_enchant_return':added,
 'inventory_after':inventory_after,'inventory_after_enchants':enchants_after,
 'inventory_after_interaction':items.GetPlayerItem(item_type,saved['slot'],True),
 'inventory_item_confirmed':item_confirmed,'inventory_enchantment_confirmed':enchantment_confirmed,
 'native_interaction_return':used,'interaction_face':request['interaction_face'],
 'before_block':before_block,'before_nbt':before,'after_block':after_block,'after_nbt':after,
 'nbt_changed':before!=after,'block_changed':before_block!=after_block,
 'native_interaction_passed':bool(spawn and item_confirmed and enchantment_confirmed and used)}
row['block']=after_block
row['expected_block']=after_block['name']
row['entity_nbt']=after
row['cell_nbt']=[{'pos':target,'nbt':after}]
saved['content_interaction']=result
reserved=[{'pos':pos,'block':info.GetBlockNew(tuple(pos),saved['dimension']),
           'nbt':info.GetBlockEntityData(saved['dimension'],tuple(pos))} for pos in saved['reserved']]
_result=json.dumps({'rows':saved['rows'],'result':result,'reserved_after_interaction':reserved,
 'source_version':saved['game_version'],'palette_sha256':saved['palette_sha256']})
'''
CLIENT_FLAGS = ('_p0_entity_appearance_rows', '_p0_entity_appearance_palettes',
                '_p0_entity_appearance_entities', '_p0_entity_content_probe_nonce')
CLIENT_ROWS = ('import sys\nassert getattr(sys,"_p0_entity_content_probe_nonce",None)==%r, '
               '"Client fixture ownership changed"\nsys._p0_entity_appearance_rows=%r\n_result=True')
CLIENT_CLEANUP = '''import sys
if getattr(sys,'_p0_entity_content_probe_nonce',None)==%r:
 for name in %r:
  if hasattr(sys,name):delattr(sys,name)
_result=True
'''


def clean(client, report):
    errors = []
    nonce = report['request']['nonce']
    actions = (
        ('final_server_snapshot', 'import json,sys\n'
         '_result=json.dumps(getattr(sys,"_p0_entity_appearances",None))', False),
        ('native_cleaned', 'import sys\n'
         'saved=getattr(sys,"_p0_entity_appearances",{})\n'
         'rows=saved.get("rows",[])\n'
         'if rows and rows[0].get("probe_nonce")==%r:\n' % nonce +
         '\n'.join(' ' + line for line in (ROOT / 'tools/p0_entity_appearance_cleanup.py')
                   .read_text(encoding='utf8').splitlines()) + '\n_result=True', False),
        ('pending_plan_cleaned', 'import sys\n'
         'plans=getattr(sys,"_p0_entity_appearance_public_plans",[])\n'
         'if plans and plans[0].get("probe_nonce")==%r:'
         'del sys._p0_entity_appearance_public_plans\n_result=True' % nonce, False),
        ('client_cleaned', CLIENT_CLEANUP % (nonce, CLIENT_FLAGS), True),
    )
    for name, code, client_side in actions:
        try:
            report[name] = execute(client, code, client_side)
        except Exception as error:
            errors.append('%s: %s' % (name, error))
    report['cleanup_errors'] = errors
    report['restored'] = not errors


def collect(client, request, report):
    try:
        report['native_runtime_evidence'] = native_runtime_evidence(client)
        report['native_runtime_versions'] = report['native_runtime_evidence']['native_runtime_versions']
        setup = (ROOT / 'tools/p0_entity_appearance_setup.py').read_text(encoding='utf8')
        report['setup'] = execute(client, PUBLIC_PLAN % request + setup)
        read = (ROOT / 'tools/p0_entity_appearance_read.py').read_text(encoding='utf8')
        execute(client, 'import sys\n'
                'assert not any(hasattr(sys,name) for name in %r), "A client entity probe is pending"\n'
                'sys._p0_entity_content_probe_nonce=%r\n' % (CLIENT_FLAGS, request['nonce']) +
                CLIENT_ROWS % (request['nonce'], report['setup']['rows']), True)
        report['client_before_interaction'] = replicated_palettes(client, read)
        native = execute(client, INTERACT % request)
        report['native_readback'] = native
        report['native_interaction_passed'] = native['result']['native_interaction_passed']
        execute(client, CLIENT_ROWS % (request['nonce'], native['rows']), True)
        report['client_after_interaction'] = replicated_palettes(client, read)
        runtime = execute(client, 'import json\n'
            'from modern_projection.projection import block_registry\n'
            '_result=json.dumps({"source_version":block_registry.source_version(),'
            '"palette_sha256":block_registry.fingerprint()})', True)
        report['client_registry'] = runtime
        assert runtime['source_version'] == native['source_version']
        assert runtime['palette_sha256'].lower() == native['palette_sha256'].lower()
        report['completed'] = True
    finally:
        clean(client, report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--fixture', required=True)
    parser.add_argument('--material', required=True)
    parser.add_argument('--source-cell', type=int, nargs=3)
    parser.add_argument('--item', required=True)
    parser.add_argument('--item-aux', type=int, default=0)
    parser.add_argument('--placement-item')
    parser.add_argument('--placement-aux', type=int, default=0)
    parser.add_argument('--placement-face', type=int, choices=range(6), default=1)
    parser.add_argument('--interaction-face', type=int, choices=range(6), default=2)
    parser.add_argument('--yaw', type=float, default=0.)
    parser.add_argument('--enchantment', type=int, nargs=2, metavar=('ID', 'LEVEL'))
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh native content observation report')
    request = {key: value for key, value in vars(args).items() if key != 'output'}
    request['nonce'] = uuid.uuid4().hex
    paths = [Path(__file__), ROOT / 'tools/p0_entity_appearance_setup.py',
             ROOT / 'tools/p0_entity_appearance_read.py', ROOT / 'tools/p0_entity_appearance_cleanup.py',
             ROOT / 'tools/verify_native_entity_appearances.py',
             ROOT / 'behavior_pack/modern_projection/projection/debug_blueprints.py',
             ROOT / 'behavior_pack/modern_projection/projection/debug_entity_blueprints.py']
    report = {'schema': 1, 'completed': False, 'restored': False,
              'native_interaction_passed': False, 'native_content_schema_verified': False,
              'production_rendering_accepted': False, 'enchantment_glint_accepted': False,
              'scope': 'One native item interaction; complete data observation without slot inference',
              'cleanup_scope': 'Only native and client state with this request nonce',
              'session_file': os.environ.get('MCDEV_SESSION_FILE'), 'owner': os.environ.get('MCDEV_OWNER'),
              'request': request, 'source_sha256': {str(path.relative_to(ROOT)):
                  hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}}
    try:
        with Client(timeout=30) as client:
            collect(client, request, report)
    except Exception as error:
        report['error'] = '%s: %s' % (type(error).__name__, error)
        raise
    finally:
        write_json(args.output, report)
    print(json.dumps({key: report[key] for key in
                     ('completed', 'restored', 'native_interaction_passed')}))
    return 0 if report['completed'] and report['restored'] and report['native_interaction_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
