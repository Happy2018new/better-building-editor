"""Qualify native banner poses with real item payloads and editor transforms.

Runs only in the assigned disposable production world. World blocks and the
inventory slot are journaled; background screenshots never activate a window.
"""
import argparse
import json
import os
from pathlib import Path
import sys

import audit_native_coordinates_r15 as coordinates
from audit_native_visual_r15 import Audit, ROOT, SERVER, WGC, save
from capture_native_window import capture
from verify_debug_blueprints import CLIENT

PATTERNS = ((), ((1, 'bo'), (14, 'cr'), (11, 'mc')),
            ((1, 'bs'), (14, 'ts'), (11, 'ls'), (3, 'rs'), (8, 'cs'), (0, 'bo')))
SOURCE_POSITIONS = ((1, -56, 20), (6, -56, 20), (11, -56, 20),
                    (1, -55, 23), (6, -55, 23), (11, -55, 23))
LOCAL_POSITIONS = ((1, 1, 1), (6, 1, 1), (11, 1, 1),
                   (1, 2, 7), (6, 2, 7), (11, 2, 7))

SETUP = SERVER + '''assert not hasattr(api,'_native_banner_items'), 'Restore first'
positions=%r
patterns=%r
saved={'journal':[],'rows':[]}
api._native_banner_items=saved
items=factory.CreateItem(player)
slot=35
inventory_type=api.GetMinecraftEnum().ItemPosType.INVENTORY
original=items.GetPlayerItem(inventory_type,slot,True)
try:
 for index,pos in enumerate(positions):
  wall=index>=3
  support=(pos[0],pos[1],pos[2]+1) if wall else (pos[0],pos[1]-1,pos[2])
  for target in (support,pos):
   saved['journal'].append({'pos':target,'block':info.GetBlockNew(target,dimension),
    'nbt':info.GetBlockEntityData(dimension,target)})
  assert info.GetBlockNew(pos,dimension)['name']=='minecraft:air'
  assert info.SetBlockNew(support,{'name':'minecraft:stone','aux':0},0,dimension,True,True)
  items.SetInvItemNum(slot,0)
  style=patterns[index%%3]
  item={'itemName':'minecraft:banner','count':1,'auxValue':4,
   'userData':{'Patterns':[{'Color':color,'Pattern':pattern} for color,pattern in style]}}
  assert items.SpawnItemToPlayerInv(item,player,slot)
  used=info.PlayerUseItemToPos(support,inventory_type,slot,2 if wall else 1)
  actual=info.GetBlockNew(pos,dimension)
  assert used and actual['name']=='minecraft:'+('wall_banner' if wall else 'standing_banner'),actual
  saved['rows'].append({'name':actual['name'],'pos':pos,'style':style,
   'actual':actual,'states':state.GetBlockStates(pos,dimension),
   'nbt':info.GetBlockEntityData(dimension,pos)})
finally:
 items.SetInvItemNum(slot,0)
 if original:items.SpawnItemToPlayerInv(original,player,slot)
_result=json.dumps({'rows':saved['rows'],'inventory_restored':items.GetPlayerItem(inventory_type,slot,True)==original})
'''

PALETTE = CLIENT + '''low=(0,-57,19)
high=(12,-54,24)
palette=b.factory.CreateBlock(b.level).GetBlockPaletteBetweenPos(low,high,False)
raw=palette.SerializeBlockPalette()
assert not raw.get('extra'),raw.get('extra')
rows=[]
depth,width,height=raw['volume']
for pos in %r:
 local=tuple(pos[i]-low[i] for i in range(3))
 index=local[1]*width*depth+local[0]*depth+local[2]
 found=[(name,actor[index]) for name,actor in raw.get('actor',{}).items() if index in actor]
 assert len(found)==1,(pos,index,raw.get('actor'))
 name,actor=found[0]
 rows.append({'name':name,'pos':pos,'actor':actor})
_result=json.dumps({'engine':api.GetEngineVersion(),'rows':rows,'extra':raw.get('extra')})
'''

RESTORE = SERVER + '''saved=api._native_banner_items
for entry in reversed(saved['journal']):
 info.SetBlockNew(entry['pos'],entry['block'],0,dimension,True,True)
 if entry['nbt']:info.SetBlockEntityData(dimension,entry['pos'],entry['nbt'])
del api._native_banner_items
_result=True
'''

def document(source, transform, form='both', supports=True):
    sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
    from projection.debug_blueprints import material
    from projection.cell import make_cell, foreground, actor_data
    from projection.entity_render import native_actor
    from projection.model import Document, Editor
    from projection.nbt_spatial import rebase
    from projection.visible_actor import compose_actor
    from projection.block_registry import states
    rows = source['setup']['rows']
    actors = source['palette']['rows']
    blocks = {}
    for row, raw, local in zip(rows, actors, LOCAL_POSITIONS):
        assert row['name'] == raw['name']
        wall = row['name'].endswith('wall_banner')
        if form == 'standing' and wall or form == 'wall' and not wall:
            continue
        actor = compose_actor(raw['actor'], rebase(row['nbt'], tuple(local[i] - row['pos'][i] for i in range(3))))
        blocks[local] = make_cell(material(row['name'], row['states']), nbt=actor)
        if supports:
            support = (local[0], local[1], local[2] + 1) if wall else (local[0], 0, local[2])
            blocks[support] = material('stone')
    editor = Editor(Document((16, 4, 16), blocks, name='R15 real patterned banners'))
    if transform != 'identity':
        from projection.storage import Selection
        editor.selection = Selection(blocks)
        editor._transform(transform)
    records = []
    for pos, value in sorted(editor.document.blocks.items()):
        value_material = foreground(value)
        if not value_material[0].endswith(('standing_banner', 'wall_banner')):
            continue
        actor = native_actor(value_material, actor_data(value))
        records.append({'pos': pos, 'material': value_material, 'states': states(value_material), 'render_actor': actor})
    return editor.document.to_data(), records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('setup', 'palette', 'load', 'project', 'camera', 'capture', 'occupy', 'restore_occupancy', 'restore_source'))
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--transform', choices=('identity', 'rotate_y90', 'rotate_y180', 'rotate_y270', 'mirror_x', 'mirror_z'), default='identity')
    parser.add_argument('--form', choices=('both', 'standing', 'wall'), default='both')
    parser.add_argument('--no-supports', action='store_true')
    parser.add_argument('--missing', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    audit = Audit(args)
    report = {'schema': 1, 'action': args.action, 'transform': args.transform,
              'public_blueprint': 'test.entities.appearances', 'pixel_acceptance': False,
              'form': args.form, 'supports': not args.no_supports}
    if args.action == 'setup':
        report['setup'] = audit.execute('setup', SETUP % (SOURCE_POSITIONS, PATTERNS), False)
        save(args.output / 'report.json', report)
        report['palette'] = audit.execute('palette', PALETTE % (SOURCE_POSITIONS,))
    elif args.action == 'palette':
        if args.source:
            source = json.loads(args.source.read_text(encoding='utf8'))
            report['setup'] = source.get('setup', source)
        report['palette'] = audit.execute('palette', PALETTE % (SOURCE_POSITIONS,))
    elif args.action == 'load':
        source = json.loads(args.source.read_text(encoding='utf8'))
        data, expected = document(source, args.transform, args.form, not args.no_supports)
        names = ('minecraft:standing_banner', 'minecraft:wall_banner')
        report['expected'] = expected
        report['document'] = data
        report['result'] = audit.execute('load', coordinates.LOAD % ('model_local', names, json.dumps(data)))
        report['pose_receipt'] = audit.execute('pose', CLIENT + '''from modern_projection.projection.cell import foreground,actor_data
from modern_projection.projection.entity_render import native_actor
from modern_projection.projection.block_registry import states
rows=[]
for pos,value in sorted(s.editor.document.blocks.items()):
 material=foreground(value)
 if material[0] in ('minecraft:standing_banner','minecraft:wall_banner'):
  rows.append({'pos':pos,'material':material,'states':states(material),'actor':native_actor(material,actor_data(value))})
sys._native_banner_positions=[tuple(row['pos']) for row in rows]
_result=json.dumps(rows)
''')
    elif args.action == 'project':
        report['result'] = audit.execute('project', coordinates.PROJECT % args.missing)
    elif args.action == 'camera':
        report['result'] = audit.execute('camera', coordinates.CAMERA.replace('target=(7.5,-55.8,1.5)', 'target=(7.5,-55.8,7.5)').replace('position=(9.5,-49.,-15.5)', 'position=(16.5,-45.,-11.5)'))
    elif args.action in ('occupy', 'restore_occupancy'):
        local = audit.execute('positions', CLIENT + '_result=json.dumps(sys._native_banner_positions)')
        positions = tuple((p[0], p[1] - 57, p[2]) for p in local)
        report['result'] = audit.execute('occupancy', coordinates.OCCUPY % (positions, args.action == 'restore_occupancy'), False)
    elif args.action == 'restore_source':
        report['result'] = audit.execute('restore', RESTORE, False)
    else:
        report['before'] = audit.execute('before', coordinates.STATUS)
        report['capture'] = capture(args.session, args.owner, args.output / 'frame.png', WGC)
        report['after'] = audit.execute('after', coordinates.STATUS)
    save(args.output / 'report.json', report)
    print(json.dumps(report, ensure_ascii=True))


if __name__ == '__main__':
    main()
