"""Compare material-only publications without touching the document or storage."""
import json
import sys
import time
import verify_ui as ui
from verify_font_share_polish import game
from profile_orbit_angles import summary


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else 'before'
    game('''import time,json
from HelloScript.pyreact import host,navigator
from HelloScript.projection.ui import Workspace
if not navigator.contains('modern_projection_workspace'):
    navigator.push(Workspace(session=s),key='modern_projection_workspace')
api._material_saved=(s.editor.material,s.page,s.direct_mode,s.inspector,host.notify_game_render_tick)
api._material_document=json.dumps(s.editor.document.to_data(),sort_keys=True,ensure_ascii=True)
s.page='workspace';s.direct_mode='place';s.inspector='params';s.emit()
_result=True''')
    time.sleep(4.)
    try:
        game('''api._material_record={'rows':[],'calls':[],'last':0.,'count':0,'active':True,'profile':False,'profiles':[]}
def instrument(original,record,session,clock):
    import cProfile,pstats,cStringIO
    def frame():
        profile=cProfile.Profile() if record['profile'] and len(record['profiles'])<3 else None
        if profile:profile.enable()
        start=clock()
        if record['active'] and start-record['last']>.09 and record['count']<48:
            record['last']=start
            session.set_editor('material',session.palette[record['count']%min(8,len(session.palette))])
            record['count']+=1
            record['calls'].append((clock()-start)*1000.)
        try:return original()
        finally:
            if profile:
                profile.disable()
                if (clock()-start)>.020:
                    stream=cStringIO.StringIO();pstats.Stats(profile,stream=stream).sort_stats('cumulative').print_stats(32)
                    record['profiles'].append(stream.getvalue())
            if record['active']:record['rows'].append((start,(clock()-start)*1000.))
            if record['count']>=48:record['active']=False
    return frame
api._material_before=(s.content_revision,s.tiles.builds)
host.notify_game_render_tick=instrument(host.notify_game_render_tick,api._material_record,s,time.clock)
_result=True''')
        if '--profile' in sys.argv:game('api._material_record["profile"]=True\n_result=True')
        for unused in range(100):
            time.sleep(.15)
            if not game('_result=api._material_record["active"]'):
                break
        data=game('''_result=dict(api._material_record,content_updates=s.content_revision-api._material_before[0],
model_builds=s.tiles.builds-api._material_before[1])''')
        assert not data['active'], 'Frame callback did not finish workload'
        rows=data['rows']
        data['summary']={'frame_interval_ms':summary([(b[0]-a[0])*1000 for a,b in zip(rows,rows[1:])]),
                         'python_frame_ms':summary([r[1] for r in rows]),'publication_ms':summary(data['calls'])}
        (ui.OUT/('stage56_material_'+label+'.json')).write_text(json.dumps(data,indent=2),encoding='utf8')
        print(json.dumps(dict(data['summary'],content_updates=data['content_updates'],model_builds=data['model_builds'])),flush=True)
        for value in data['profiles']:print(value,flush=True)
    finally:
        game('''s.editor.material,s.page,s.direct_mode,s.inspector,host.notify_game_render_tick=api._material_saved
s.emit()
assert json.dumps(s.editor.document.to_data(),sort_keys=True,ensure_ascii=True)==api._material_document
_result=True''')


if __name__=='__main__':main()
