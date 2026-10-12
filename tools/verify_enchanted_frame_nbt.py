"""Read back public enchanted frame NBT through the existing native writer."""
import argparse
import hashlib
import json
import os
from pathlib import Path

from verify_debug_blueprints import Client, write_json
from verify_native_entity_appearances import execute, replicated_palettes

ROOT = Path(__file__).resolve().parents[1]
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
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh native item readback report')
    paths = [Path(__file__), ROOT / 'behavior_pack/modern_projection/projection/debug_item_blueprints.py',
             ROOT / 'behavior_pack/modern_projection/server_system.py',
             ROOT / 'tools/p0_entity_appearance_setup.py', ROOT / 'tools/p0_entity_appearance_read.py',
             ROOT / 'tools/p0_entity_appearance_cleanup.py']
    evidence = {'schema': 1, 'completed': False, 'passed': False,
                'scope': 'Synthetic public enchanted NBT written through WorldAdapter; server native readback and client palette',
                'production_rendering_accepted': False, 'enchantment_glint_accepted': False,
                'client_palette_independently_contains_item_nbt': False,
                'public_fixture': 'test.entities.item_contents',
                'session_file': os.environ.get('MCDEV_SESSION_FILE'),
                'owner': os.environ.get('MCDEV_OWNER'),
                'source_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}}
    try:
        with Client(timeout=30) as client:
            try:
                setup = (ROOT / 'tools/p0_entity_appearance_setup.py').read_text(encoding='utf8')
                evidence['setup'] = execute(client, 'import sys\n'
                    'sys._p0_entity_appearance_selected=("frame_filled","glow_frame_filled")\n' + setup)
                written = execute(client, WRITE_ENCHANTED)
                evidence['native_readback'] = written
                execute(client, 'import sys\nsys._p0_entity_appearance_rows=%r\n_result=True' % written['rows'], True)
                read = (ROOT / 'tools/p0_entity_appearance_read.py').read_text(encoding='utf8')
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
                      'restored': evidence['restored']}))
    return 0 if evidence['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
