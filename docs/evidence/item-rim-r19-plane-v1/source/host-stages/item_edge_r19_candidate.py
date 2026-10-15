import hashlib
import json
from pathlib import Path
import sys
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from generate_item_icon_catalog import icon_mesh
from item_sprite_capture_contract import snapshot_sources,snapshot_digest
project=Path('D:/bbe-r18-item-glint')
control=ROOT/'.runtime/item-edge-r19-candidate-control'
control.mkdir(exist_ok=False)
catalog=json.loads((ROOT/'tools/data/item_icon_catalog_nemc_3.10.0.420447.json').read_bytes())
resource='cf75a6e96b2d3e06'
relative='resource_pack/models/modern_projection/item_icons/'+resource+'_mesh.json'
path=project/relative
before=path.read_bytes()
expected=hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()
assert hashlib.sha256(before).hexdigest()==expected
(control/'original-mesh.json').write_bytes(before)
pose=dict(catalog['pose'],front_z_pixels=14.75)
with Image.open(ROOT/'resource_pack/textures/models/modern_projection/item_icons'/(resource+'.png')) as image:
    generated=icon_mesh(image,pose,'modern_projection/item_icons/'+resource)
path.write_bytes((json.dumps(generated,separators=(',',':'))+'\n').encode('ascii'))
candidate={'schema':1,'production_qualified':False,'item':['minecraft:diamond_sword',0],
    'pose':pose,'base_pose':catalog['pose'],'source_mesh_sha256':expected,
    'mesh_sha256':{relative:hashlib.sha256(path.read_bytes()).hexdigest()},
    'change':'Only frame front plane moves0.25 model pixels toward the viewer; scale/thickness/glint unchanged',
    'generator_sha256':hashlib.sha256((ROOT/'tools/generate_item_icon_catalog.py').read_bytes()).hexdigest()}
(control/'candidate.json').write_text(json.dumps(candidate,indent=2)+'\n',encoding='ascii')
sources=snapshot_sources(project)
(control/'launch-sources.json').write_text(json.dumps({'project':str(project),'files':sources,'sha256':snapshot_digest(sources)},indent=2)+'\n',encoding='ascii')
print(json.dumps({'files':len(sources),'sha256':snapshot_digest(sources),'candidate':candidate}))
