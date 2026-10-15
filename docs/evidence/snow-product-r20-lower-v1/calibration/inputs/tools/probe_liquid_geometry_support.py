"""Record native liquid tessellation API results without modifying the world.

API success is diagnostic only and never establishes visible water pixels.
Use run_live_check.py to enforce the owned instance and route.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

from verify_debug_blueprints import BlueprintCheck, Client, write_json


PROBE = '''from modern_projection.projection.model import Document
from modern_projection.projection import block_registry as registry
from modern_projection.projection.debug_blueprints import material
from modern_projection.projection.geometry_palette import prepare_palette
from modern_projection.projection.render_context import prepare_context_batches
from modern_projection.projection.bridge import _native_palette
from modern_projection.projection.cell import freeze
import uuid
doc=Document((1,1,1))
doc.blocks[(0,0,0)]=material('water')
raw=doc.palette_data()
sources=[('document',raw),('prepared',prepare_palette(raw))]
context=prepare_context_batches(doc,raw)
for origin,is_context,data in context['_context_batches']:
 sources.append(('context' if is_context else 'overlay',data))
for control in ('stone','glass','flowing_water','lava','flowing_lava'):
 document=Document((1,1,1))
 document.blocks[(0,0,0)]=material(control)
 sources.append((control,prepare_palette(document.palette_data())))
liquid_states=[]
for name in ('water','flowing_water','lava','flowing_lava'):
 native_name='minecraft:'+name
 for aux in registry.aux_values(native_name):
  document=Document((1,1,1))
  document.blocks[(0,0,0)]=(native_name,aux)
  kind='%s[%d]' % (name,aux)
  sources.append((kind,document.palette_data()))
  liquid_states.append({'kind':kind,'name':native_name,'aux':aux,
                        'states':registry.states((native_name,aux))})
rows=[]
block=b.factory.CreateBlock(b.level)
geometry=b.factory.CreateBlockGeometry(b.level)
for kind,data in sources:
 palette=block.GetBlankBlockPalette()
 assert palette is not None
 accepted=palette.DeserializeBlockPalette(_native_palette(data))
 row={'kind':kind,'deserialized':accepted,'input':freeze(data),'results':[]}
 if accepted:
  row['roundtrip']=freeze(palette.SerializeBlockPalette())
  for mode in (0,1):
   name='liquid_support_'+uuid.uuid4().hex
   result=geometry.CombineBlockPaletteToGeometry(palette,name,mode)
   row['results'].append({'unsupported_mode':mode,'requested_name':name,'returned':result})
 rows.append(row)
_result=json.dumps({'rows':rows,'runtime':api.GetMinecraftVersion(),
 'liquid_states':liquid_states,'coverage':'all registry states of four vanilla liquids',
 'game_version':registry.source_version(),'palette_sha256':registry.fingerprint(),
 'visible_water_accepted':False,'world_untouched':True})
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    with Client(timeout=30) as client:
        check = BlueprintCheck(client, args.output, 60)
        report = check.run(PROBE)
        report.update(schema_version=1, session_file=os.environ.get('MCDEV_SESSION_FILE'),
                      owner=os.environ.get('MCDEV_OWNER'),
                      source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        write_json(args.output, report)
    print(json.dumps({'world_untouched': True, 'visible_water_accepted': False,
                      'paths': [(row['kind'], row['results']) for row in report['rows']]}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
