"""Measure exact 64x128x64 solid and building-like sparse single-actor updates."""
import json,time
import verify_projection_occupancy as qa
from verify_projection_outline import game,server


def main():
    origin=qa.setup_fixture()
    installed=False
    results={}
    try:
        qa.install_probe(origin);installed=True
        qa.wait_points((x,0,0) for x in range(8))
        server('''from modern_projection.server_system import WorldAdapter
a=WorldAdapter(p)
o='''+repr(tuple(origin))+'''
points=[(o[0]+x,o[1],o[2]) for x in range(64)]+[(o[0]+63,o[1]+127,o[2]+63)]
saved=[(pos,a.read(pos)) for pos in points]
assert all(value==("minecraft:air",0) for pos,value in saved), "Nonair fixture refused"
api._occupancy_qa_saved+=saved
_result=True''')
        for mode in ('solid','building'):
            started=time.monotonic()
            count=game('''b=s.bridge
b.stop_projection()
from modern_projection.projection.model import Document,Editor
from modern_projection.projection.storage import Selection
mode='''+repr(mode)+'''
d=Document((64,128,64))
if mode=="solid":
    for x in range(4):
        for y in range(8):
            for z in range(4):
                d.blocks.fill_chunk((x,y,z),("minecraft:quartz_block",0))
else:
    for y in range(128):
        for x in range(64):
            for z in range(64):
                if x in (0,63) or z in (0,63) or y%16==0 or y==127:
                    d.blocks[x,y,z]=("minecraft:quartz_block",0)
s.editor=Editor(d)
b.project()
_result=len(d.blocks)''')
            baseline=qa.wait_count(count,180)
            results[mode]={'blocks':count,'initial_wall_seconds':time.monotonic()-started,'initial':baseline}
            started=time.monotonic()
            qa.write_cells(origin,[(x,'minecraft:glass',0) for x in range(64)])
            game('o=s.bridge.projection_occupancy\nfor x in range(64):o.hint((o.origin[0]+x,o.origin[1],o.origin[2]))\n_result=True')
            changed=qa.wait_count(count-64,90)
            results[mode]['burst_wall_seconds']=time.monotonic()-started
            results[mode]['burst']=changed
            assert changed['actor']==baseline['actor'] and changed['actors']==1
            started=time.monotonic()
            server('''from modern_projection.server_system import WorldAdapter
a=WorldAdapter(p)
o='''+repr(tuple(origin))+'''
assert a.write((o[0]+63,o[1]+127,o[2]+63),("minecraft:glass",0))
_result=True''')
            remote=qa.wait_count(count-65,90)
            results[mode]['far_detection_seconds']=time.monotonic()-started
            results[mode]['remote']=remote
            assert remote['actor']==baseline['actor']
            qa.write_cells(origin,[(x,'minecraft:air',0) for x in range(64)])
            server('''from modern_projection.server_system import WorldAdapter
o='''+repr(tuple(origin))+'''
assert WorldAdapter(p).write((o[0]+63,o[1]+127,o[2]+63),("minecraft:air",0))
_result=True''')
            game('o=s.bridge.projection_occupancy\nfor x in range(64):o.hint((o.origin[0]+x,o.origin[1],o.origin[2]))\no.hint((o.origin[0]+63,o.origin[1]+127,o.origin[2]+63))\n_result=True')
            restored=qa.wait_count(count,90)
            results[mode]['restored']=restored
            print(mode,count,'initial',results[mode]['initial_wall_seconds'],'burst',results[mode]['burst_wall_seconds'],'far',results[mode]['far_detection_seconds'],flush=True)
        results['status']='passed'
    finally:
        if installed:
            game('s.bridge.stop_projection()\ns.editor,s.origin,s.projection_missing,s.projection_outline,s.solo_layer,s.bridge.geometry,s.bridge.factory=api._occupancy_qa_saved\ns.refresh_preview();s.emit()\n_result=True')
        server('''from modern_projection.server_system import WorldAdapter
a=WorldAdapter(p)
for pos,value in api._occupancy_qa_saved:assert a.write(pos,value)
_result=True''')
        qa.dump(qa.ui.OUT/'projection_full_volume_performance.json',results)

if __name__=='__main__':main()
