"""Exercise production edit/history/serialization paths in an owned game.

No desktop input, world writes or persistent archive changes. Blueprint cases
provide materials; rendering has its own independent visual acceptance tools.
"""
import argparse
import json
from pathlib import Path

from verify_debug_blueprints import BlueprintCheck, Client, INSTALL_PROBE, RESTORE, write_json

SETUP = '''from modern_projection.projection.model import Document
from modern_projection.projection.debug_blueprints import build,material
from modern_projection.projection.cell import AIR,foreground,background,make_cell
from modern_projection.projection import block_registry as registry
size=%r
doc=Document(size,name='Editor transaction acceptance')
s._loaded(doc)
e=s.editor
e.edit_layer=2
fixture=build('test.layers.water')
water=material('water')
fence=foreground(fixture.get((3,1,3)))
plant=material('short_grass')
snow=material('snow_layer',{'height':2,'covered_bit':False})
pos=(3,1,3)
def snapshot():
 return (e.document.blocks.copy(),set(e.selection),e.start,e.end)
def place(value,erase=False):
 e.material=value
 return s.action(e.paint_at,pos,erase,False)
_result=json.dumps({'size':size,'edit_layer':e.edit_layer,
 'fixtures':['test.layers.water','test.layers.snow','test.groups.parts','test.entities.appearances'],
 'registry_version':registry.source_version(),'registry_sha256':registry.fingerprint()})
'''

WATER = '''for first,second in ((fence,water),(water,fence)):
 assert place(first)>0
 assert place(second)>0
 assert e.document.get(pos)==make_cell(fence,water)
 before=snapshot()
 assert place(AIR,True)>0
 assert e.document.get(pos)==water
 assert s.action(e.undo) and snapshot()==before
 assert s.action(e.redo) and e.document.get(pos)==water
 assert place(AIR,True)>0 and e.document.get(pos)==AIR
place(fence)
place(water)
e.edit_layer=0
assert place(AIR,True)>0 and e.document.get(pos)==make_cell(AIR,water)
assert s.action(e.undo)
e.edit_layer=1
assert place(AIR,True)>0 and e.document.get(pos)==fence
assert s.action(e.undo)
e.edit_layer=2
place(AIR,True)
place(AIR,True)
_result=json.dumps({'passed':True,'orders':2,'strict_layers':2,'automatic_erase':'foreground_then_promoted_water'})
'''

SNOW = '''for first,second in ((plant,snow),(snow,plant)):
 place(first)
 place(second)
 value=e.document.get(pos)
 assert background(value)==plant
 assert registry.states(foreground(value))=={'height':2,'covered_bit':True}
 before=snapshot()
 e.edit_layer=0
 assert place(AIR,True)>0
 assert e.document.get(pos)==make_cell(AIR,plant)
 assert s.action(e.undo) and snapshot()==before
 e.edit_layer=1
 assert place(AIR,True)>0
 assert e.document.get(pos)==snow
 assert s.action(e.undo) and snapshot()==before
 e.edit_layer=2
 assert place(AIR,True)>0 and e.document.get(pos)==plant
 assert place(AIR,True)>0 and e.document.get(pos)==AIR
_result=json.dumps({'passed':True,'orders':2,'strict_layers':2,'automatic_erase':'snow_then_promoted_plant'})
'''

GROUPS = '''from modern_projection.projection.block_groups import group_partner
cases=[]
for name in ('wooden_door','bed','lilac'):
 value=material(name)
 relationship=group_partner(value)
 assert relationship is not None
 partner=tuple(pos[i]+relationship[0][i] for i in range(3))
 before=snapshot()
 assert place(value)>0
 assert foreground(e.document.get(pos))==value
 assert foreground(e.document.get(partner))==relationship[1]
 placed=snapshot()
 assert s.action(e.undo) and snapshot()==before
 assert s.action(e.redo) and snapshot()==placed
 assert place(AIR,True)>0
 assert e.document.get(pos)==AIR and e.document.get(partner)==AIR
 assert s.action(e.undo) and snapshot()==placed
 assert s.action(e.redo)
 cases.append({'material':name,'positions':[pos,partner]})
_result=json.dumps({'passed':True,'cases':cases})
'''

SELECTION = '''value=material('oak_stairs',{'weirdo_direction':0,'upside_down_bit':False})
place(value)
e.select_box(pos,(pos[0]+1,pos[1],pos[2]))
e.step=1
sys._transaction_states=[snapshot()]
_result=True
'''

ROUND_TRIP = '''from modern_projection.projection.sharing_codec import encode_steps,decode_steps
from modern_projection.projection.transfer import Receiver,packets
from modern_projection.projection.cell import actor_data
fixture=build('test.entities.appearances')
actor_cell=fixture.get((9,1,20))
e.document.blocks[(1,1,1)]=actor_cell
e.document.blocks[(2,1,1)]=make_cell(fence,water)
e.document.blocks[(3,1,1)]=make_cell(material('snow_layer',{'height':5,'covered_bit':True}),plant)
doc=e.document
data=doc.to_data()
assert data['version']==6
restored=Document.from_data(json.loads(json.dumps(data)))
assert restored.size==doc.size and restored.blocks==doc.blocks
text=next(row['text'] for row in encode_steps(doc) if 'text' in row)
assert text.startswith('MP4:')
restored=next(row['document'] for row in decode_steps(text) if 'document' in row)
assert restored.blocks==doc.blocks
receiver=Receiver()
for packet in packets(doc):receiver.feed(json.loads(json.dumps(packet)))
assert receiver.result.blocks==doc.blocks
assert actor_data(receiver.result.get((1,1,1)))==actor_data(actor_cell)
legacy={'version':1,'size':[4,4,4],'name':'Legacy acceptance','blocks':[[1,1,1,'minecraft:stone',0]]}
assert Document.from_data(legacy).get((1,1,1))==material('stone')
_result=json.dumps({'passed':True,'config_version':6,'share_prefix':text[:4],
 'share_bytes':len(text),'typed_actor_preserved':True,'legacy_config_version':1})
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    evidence = {'schema': 1, 'completed': False, 'passed': False, 'rows': [],
                'scope': 'Production Session actions in embedded Python; no visual or world-write assertion'}
    installed = False
    try:
        with Client(timeout=30) as client:
            check = BlueprintCheck(client, args.output, 60)
            check.run(INSTALL_PROBE)
            installed = True
            try:
                for size in ((8, 5, 8), (32, 16, 32)):
                    row = {'source': check.run(SETUP % (size,))}
                    if size[0] > 16:
                        check.run('pos=(15,7,15)\n_result=True')
                    row['water'] = check.run(WATER)
                    row['snow'] = check.run(SNOW)
                    row['groups'] = check.run(GROUPS)
                    check.run(SELECTION)
                    for unused in range(3):
                        check.run('assert s.action(e.run,"move_xp")\n_result=True')
                        check.wait('production move complete', lambda status: status['done'],
                                   lambda: check.run('_result={"done":s.edit_job is None}'))
                        check.run('sys._transaction_states.append(snapshot())\n_result=True')
                    row['history'] = check.run('''for expected in reversed(sys._transaction_states[:-1]):
 assert s.action(e.undo) and snapshot()==expected, 'Undo did not restore blocks and blue selection'
for expected in sys._transaction_states[1:]:
 assert s.action(e.redo) and snapshot()==expected, 'Redo did not restore blocks and blue selection'
_result=json.dumps({'passed':True,'consecutive_moves':3,'selection_bounds':(e.start,e.end)})''')
                    row['serialization'] = check.run(ROUND_TRIP)
                    evidence['rows'].append(row)
                    write_json(args.output, evidence)
                evidence['completed'] = evidence['passed'] = True
            finally:
                if installed:
                    check.run(RESTORE)
                    check.run('if hasattr(sys,"_transaction_states"):del sys._transaction_states\n_result=True')
                    evidence['restored'] = True
    except Exception as error:
        evidence['error'] = '%s: %s' % (type(error).__name__, error)
        raise
    finally:
        write_json(args.output, evidence)
    print(json.dumps({'evidence': str(args.output.resolve()), 'passed': evidence['passed']}))


if __name__ == '__main__':
    main()
