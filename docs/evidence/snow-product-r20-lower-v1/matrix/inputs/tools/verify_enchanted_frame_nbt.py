"""Read public enchanted frame data from native writes or physical item use."""
import argparse
import hashlib
import json
import os
from pathlib import Path

from verify_debug_blueprints import Client, write_json
from verify_native_entity_appearances import execute, replicated_palettes, native_runtime_evidence

ROOT = Path(__file__).resolve().parents[1]
WRITE_PHYSICAL = '''import json,sys
import mod.server.extraServerApi as api
from modern_projection.projection.debug_item_blueprints import ENCHANTMENT,PAIRS
from modern_projection.projection.nbt_spatial import field_key,root_payload,scalar
from modern_projection.projection.entity_overlays import frame_item
saved=sys._p0_entity_appearances
factory=api.GetEngineCompFactory()
items,info=factory.CreateItem(saved['player']),factory.CreateBlockInfo(saved['player'])
item_type=api.GetMinecraftEnum().ItemPosType.INVENTORY
assert ENCHANTMENT[0]==api.GetMinecraftEnum().EnchantType.WeaponDamage
results=[]
for row in saved['rows']:
 pair=next(pair for pair in PAIRS if pair['source_case']==row['case'])
 assert items.SetInvItemNum(saved['slot'],0)
 spawn=items.SpawnItemToPlayerInv({'itemName':row['fill_item'],'count':1,'auxValue':0},saved['player'],saved['slot'])
 before=items.GetPlayerItem(item_type,saved['slot'],True)
 before_enchants=items.GetInvItemEnchantData(saved['slot'])
 added=items.AddEnchantToInvItem(saved['slot'],ENCHANTMENT[0],ENCHANTMENT[1])
 after=items.GetPlayerItem(item_type,saved['slot'],True)
 after_enchants=items.GetInvItemEnchantData(saved['slot'])
 used=False
 if spawn and before and added and tuple(map(tuple,after_enchants or ()))==(ENCHANTMENT,):
  used=info.PlayerUseItemToPos(tuple(row['pos']),item_type,saved['slot'],row['face'])
 actual=info.GetBlockEntityData(saved['dimension'],tuple(row['pos']))
 root=root_payload(actual)
 actual_item=root.get(field_key(root,'Item')) if root else None
 tag=root_payload(root_payload(actual_item).get('tag')) if actual_item else None
 actual_ench=tag.get(field_key(tag,'ench')) if tag else None
 entries=scalar(tag,'ench') if tag else None
 observed=tuple((scalar(entry,'id'),scalar(entry,'lvl')) for entry in (entries or ()))
 material=row['block']['name'],row['block']['aux']
 read_item=frame_item(material,actual)
 result={'case':row['case'],'public_source':pair['enchanted'],'world_target':row['pos'],
  'native_spawn_return':spawn,'inventory_before':before,'inventory_before_enchants':before_enchants,
  'native_add_enchant_return':added,'inventory_after':after,'inventory_after_enchants':after_enchants,
  'native_interaction_return':used,'expected_enchantment':ENCHANTMENT,'actual_item':actual_item,
  'actual_ench':actual_ench,'observed_enchantments':observed,
  'readback_is_enchanted':bool(read_item and read_item['isEnchanted'])}
 result['passed']=bool(spawn and added and used and observed==(ENCHANTMENT,) and result['readback_is_enchanted'])
 results.append(result)
 row['entity_nbt']=actual
 row['cell_nbt']=[{'pos':row['pos'],'nbt':actual}]
 row['block']=info.GetBlockNew(tuple(row['pos']),saved['dimension'])
_result=json.dumps({'rows':saved['rows'],'results':results,
 'source_version':saved['game_version'],'palette_sha256':saved['palette_sha256']})
'''

WRITE_ENCHANTED = '''import json,sys
from modern_projection.server_system import WorldAdapter
from modern_projection.projection.debug_blueprints import Fixture
from modern_projection.projection.debug_item_blueprints import METADATA,PAIRS,populate
from modern_projection.projection.cell import actor_data,foreground
from modern_projection.projection.visible_actor import entity_nbt
from modern_projection.projection.nbt_spatial import field_key,root_payload
from modern_projection.projection.entity_overlays import frame_item
saved=sys._p0_entity_appearances
doc=populate(Fixture(METADATA))
adapter=WorldAdapter(saved['player'])
results=[]
for row in saved['rows']:
 pair=next(pair for pair in PAIRS if pair['source_case']==row['case'])
 source=tuple(pair['enchanted'])
 cell=doc.get(source)
 expected_root=root_payload(entity_nbt(actor_data(cell)))
 expected_item=expected_root[field_key(expected_root,'Item')]
 expected_ench=root_payload(root_payload(expected_item)['tag'])['ench']
 pos=tuple(row['pos'])
 delta=tuple(pos[axis]-source[axis] for axis in range(3))
 wrote=adapter.write(pos,cell,delta)
 actual=adapter.info.GetBlockEntityData(saved['dimension'],pos)
 actual_root=root_payload(actual)
 actual_item=actual_root.get(field_key(actual_root,'Item'))
 actual_tag=root_payload(root_payload(actual_item).get('tag')) if actual_item else None
 actual_ench=actual_tag.get('ench') if actual_tag else None
 read_item=frame_item(foreground(cell),actual)
 result={'case':row['case'],'public_source':source,'world_target':pos,
  'native_write_return':wrote,'expected_item':expected_item,'actual_item':actual_item,
  'expected_ench':expected_ench,'actual_ench':actual_ench,
  'whole_item_equal':actual_item==expected_item,
  'typed_ench_equal':actual_ench==expected_ench,
  'readback_is_enchanted':bool(read_item and read_item['isEnchanted'])}
 result['passed']=bool(wrote and result['typed_ench_equal'] and result['readback_is_enchanted'])
 results.append(result)
 row['entity_nbt']=actual
 row['cell_nbt']=[{'pos':row['pos'],'nbt':actual}]
 row['block']=adapter.info.GetBlockNew(pos,saved['dimension'])
_result=json.dumps({'rows':saved['rows'],'results':results,
 'source_version':saved['game_version'],'palette_sha256':saved['palette_sha256']})
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--physical', action='store_true',
                        help='Enchant a temporary inventory sword and use it on each native frame')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh native item readback report')
    paths = [Path(__file__), ROOT / 'behavior_pack/modern_projection/projection/debug_item_blueprints.py',
             ROOT / 'behavior_pack/modern_projection/server_system.py',
             ROOT / 'tools/verify_native_entity_appearances.py',
             ROOT / 'tools/p0_entity_appearance_setup.py', ROOT / 'tools/p0_entity_appearance_read.py',
             ROOT / 'tools/p0_entity_appearance_cleanup.py']
    evidence = {'schema': 2, 'completed': False, 'passed': False,
                'mode': 'physical_item_use' if args.physical else 'world_adapter_write',
                'scope': ('Public sharpness control independently produced by native inventory enchantment and item interaction'
                          if args.physical else
                          'Synthetic public enchanted NBT written through WorldAdapter; server native readback and client palette'),
                'production_rendering_accepted': False, 'enchantment_glint_accepted': False,
                'client_palette_independently_contains_item_nbt': False,
                'public_fixture': 'test.entities.item_contents',
                'session_file': os.environ.get('MCDEV_SESSION_FILE'),
                'owner': os.environ.get('MCDEV_OWNER'),
                'source_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}}
    try:
        with Client(timeout=30) as client:
            evidence['native_runtime_evidence'] = native_runtime_evidence(client)
            evidence['native_runtime_versions'] = evidence['native_runtime_evidence']['native_runtime_versions']
            try:
                setup = (ROOT / 'tools/p0_entity_appearance_setup.py').read_text(encoding='utf8')
                evidence['setup'] = execute(client, 'import sys\n'
                    'sys._p0_entity_appearance_selected=("frame_filled","glow_frame_filled")\n' + setup)
                read = (ROOT / 'tools/p0_entity_appearance_read.py').read_text(encoding='utf8')
                if args.physical:
                    execute(client, 'import sys\nsys._p0_entity_appearance_rows=%r\n_result=True' %
                            evidence['setup']['rows'], True)
                    evidence['client_before_interaction'] = replicated_palettes(client, read)
                written = execute(client, WRITE_PHYSICAL if args.physical else WRITE_ENCHANTED)
                evidence['native_readback'] = written
                execute(client, 'import sys\nsys._p0_entity_appearance_rows=%r\n_result=True' % written['rows'], True)
                evidence['client_palette'] = replicated_palettes(client, read)
                runtime = execute(client, 'import json\n'
                    'from modern_projection.projection import block_registry\n'
                    '_result=json.dumps({"source_version":block_registry.source_version(),'
                    '"palette_sha256":block_registry.fingerprint()})', True)
                evidence['client_registry'] = runtime
                assert runtime['source_version'] == written['source_version']
                assert runtime['palette_sha256'].lower() == written['palette_sha256'].lower()
                evidence['completed'] = True
                evidence['passed'] = (len(written['results']) == 2 and
                                      all(row['passed'] for row in written['results']))
            finally:
                errors = []
                try:
                    evidence['final_server_snapshot'] = execute(client,
                        'import json,sys\n_result=json.dumps(getattr(sys,"_p0_entity_appearances",None))')
                except Exception as error:
                    errors.append('final_server_snapshot: ' + str(error))
                try:
                    if execute(client, 'import sys\n_result=hasattr(sys,"_p0_entity_appearances")'):
                        evidence['native_cleaned'] = execute(client,
                            (ROOT / 'tools/p0_entity_appearance_cleanup.py').read_text(encoding='utf8'))
                    else:
                        evidence['native_cleaned'] = True
                except Exception as error:
                    errors.append('native_fixture: ' + str(error))
                try:
                    evidence['client_cleaned'] = execute(client, 'import sys\n'
                        'for name in ("_p0_entity_appearance_rows","_p0_entity_appearance_palettes",'
                        '"_p0_entity_appearance_entities"):\n'
                        ' if hasattr(sys,name):delattr(sys,name)\n_result=True', True)
                except Exception as error:
                    errors.append('client_state: ' + str(error))
                evidence['cleanup_errors'] = errors
                evidence['restored'] = not errors
                evidence['passed'] = evidence['passed'] and evidence['restored']
    except Exception as error:
        evidence['error'] = '%s: %s' % (type(error).__name__, error)
        raise
    finally:
        write_json(args.output, evidence)
    print(json.dumps({'completed': evidence['completed'], 'passed': evidence['passed'],
                      'restored': evidence.get('restored', False)}))
    return 0 if evidence['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
