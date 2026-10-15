"""Read-only maximum-size capture in a bound, isolated flat development world.

Exercises the real server/network/archive flow while replacing local writes
with memory. Never imports into the user's persistent building library.
"""
import json
import time
from verify_world_tools import game, state, wait_ready


def main():
    game('''api._capture_saved=(s.library,s.library_serial,s.bridge.save_library,
    s.bridge.save_archive_page,s.world_import_document,s.world_import_origin,s.bridge.corners)
api._tools_draft=s.editor
api._capture_pages={}
def save_index(value):
    api._capture_index=value
    return True
def save_page(identity,part,value):
    api._capture_pages[(identity,part)]=value
    return True
s.library=[];s.library_serial=0
s.bridge.save_library=save_index;s.bridge.save_archive_page=save_page
_result=True''')
    try:
        game('''api._capture_region_saved=owner.world_regions.get(player)
owner.world_regions[player]=(0,(-16,-64,-16),(64,128,64))
_result=True''', server=True)
        game('''s.bridge.corners=[(-16,-64,-16),(47,63,47)]
s.bridge.capture_new()
_result=True''')
        time.sleep(.3)
        game('s.bridge.cancel_world()\n_result=True')
        value=wait_ready()
        assert not value['library'] and value['draft_same'], value
        print('PASS maximum capture cancellation', flush=True)
        started=time.monotonic()
        game('s.bridge.capture_new()\n_result=True')
        for unused in range(90):
            time.sleep(1)
            value=state()
            if not value['busy'] and not value['io']:
                break
            if unused % 5 == 0:
                print('Reading',round(time.monotonic()-started,2),value['message'],flush=True)
        assert len(value['library'])==1 and value['draft_same'], value
        result=game('''from modern_projection.projection.transfer import Receiver
receiver=Receiver()
entry=s.library[0]
for part in range(entry['data']['parts']):
    for packet in api._capture_pages[(entry['id'],part)]['packets']:
        receiver.feed(packet)
doc=receiver.result
_result={'size':doc.size,'blocks':len(doc.blocks),
    'ground':sum(doc.get((x,y,z))[0]!='minecraft:air' for x in range(64) for y in range(4) for z in range(64)),
    'sample':[(pos,doc.get(pos))
    for pos in [(0,0,0),(0,3,0),(63,3,63),(63,127,63)]],
    'draft_same':s.editor is api._tools_draft,'index':entry['data']}''')
        assert result['size']==[64,128,64],result
        # The preset may add a chest / command blocks above the flat terrain.
        assert result['ground']==64*64*4,result
        assert result['sample'][2][1][0]=='minecraft:grass_block',result
        assert result['sample'][3][1][0]=='minecraft:air',result
        print('PASS maximum world capture',round(time.monotonic()-started,2),
              json.dumps(result,ensure_ascii=False),flush=True)
    finally:
        value=state()
        if value['busy']:
            game('s.bridge.cancel_world()\n_result=True')
        if value['busy'] or value['io']:
            wait_ready()
        game('''s.library,s.library_serial,s.bridge.save_library,s.bridge.save_archive_page,\
s.world_import_document,s.world_import_origin,s.bridge.corners=api._capture_saved
s.bridge.draw_bounds();s.emit()
_result=True''')
        game('''owner.world_regions.pop(player,None)
if api._capture_region_saved is not None:
    owner.world_regions[player]=api._capture_region_saved
_result=True''',server=True)


if __name__=='__main__':
    main()
