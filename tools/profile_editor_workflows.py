"""Maximum-size edit/preview/undo and optional native orbit audit; restore draft."""
import argparse
import json
import sys
import time
import verify_ui as ui
from verify_font_share_polish import game
from profile_orbit_angles import summary


def settle():
    deadline=time.monotonic()+90
    while time.monotonic()<deadline:
        result=game('''_result={'busy':s.edit_job is not None or s.preview_pending,
'error':s.preview_error,'blocks':len(s.editor.document.blocks),'tiles':len(s.tiles.render_keys),
'builds':s.tiles.builds,'extractions':s.tiles.extractions,'performance':s.performance,
'waiting':sum(bool(p['pending']) for p in s.tiles.parts.values())}''')
        if not result['busy'] and not result['waiting']:
            assert not result['error'],result
            return result
        time.sleep(.15)
    raise AssertionError(result)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--label',default='after')
    parser.add_argument('--orbit',action='store_true')
    parser.add_argument('--navigation',action='store_true')
    parser.add_argument('--hotspots',action='store_true')
    args=parser.parse_args()
    rows=[]
    game('''from HelloScript.projection.model import Document
from HelloScript.pyreact import host
import time
fields=('editor','name','page','tool','direct_mode','group','inspector','section','solo_layer',
'canvas_x','canvas_z','focused','box_anchor','paste_origin','paste_pinned','camera_yaw','camera_pitch',
'zoom','camera_pan','camera_pivot','camera_depth','camera_depth_pose','camera_pose','focus_view')
api._workflow_saved=dict((k,getattr(s,k)) for k in fields)
api._workflow_tick=host.notify_game_render_tick
api._workflow_rows=[]
api._workflow_active=False
api._workflow_profile=False
api._workflow_hotspots=[]
def record_frame(original,clock):
    def tick():
        import cProfile,pstats
        profile=cProfile.Profile() if api._workflow_active and api._workflow_profile else None
        if profile:profile.enable()
        start=clock()
        try:return original()
        finally:
            if profile:
                profile.disable()
                if clock()-start>.04 and len(api._workflow_hotspots)<32:
                    top=sorted(pstats.Stats(profile).stats.items(),key=lambda pair:pair[1][3],reverse=True)[:24]
                    api._workflow_hotspots.append([(str(k),v[:4]) for k,v in top])
            if api._workflow_active:api._workflow_rows.append((start,(clock()-start)*1000.))
    return tick
host.notify_game_render_tick=record_frame(host.notify_game_render_tick,time.clock)
s._loaded(Document((64,128,64)))
s.direct_mode='browse';s.focus_view=False;s.inspector='params';s.emit()
_result=True''')
    try:
        settle()
        if args.hotspots:game('api._workflow_profile=True\n_result=True')
        operations=[('shell','s.choose_tool("shell");s.start_edit("shell")'),
                    ('undo','s.action(s.editor.undo)'),('redo','s.action(s.editor.redo)'),
                    ('point_burst','\n'.join('s.point_edit((30,%d,30))'%y for y in range(10,30))),
                    ('undo_burst','\n'.join('s.action(s.editor.undo)' for unused in range(20)))]
        for name,source in operations:
            before=game('api._workflow_rows=[]\napi._workflow_active=True\n_result=(s.tiles.builds,s.tiles.extractions)')
            start=time.monotonic()
            game(source+'\n_result=True')
            result=settle()
            frames=game('api._workflow_active=False\n_result=api._workflow_rows')
            result.update(case=name,observed_wall_s=time.monotonic()-start,
                          new_builds=result['builds']-before[0],new_extractions=result['extractions']-before[1],
                          python_ms=summary([r[1] for r in frames]),
                          interval_ms=summary([(b[0]-a[0])*1000. for a,b in zip(frames,frames[1:])]))
            rows.append(result);print(json.dumps(result),flush=True)
        assert result['blocks']==39944,result
        if args.navigation:
            before=game('api._workflow_rows=[]\napi._workflow_active=True\n_result=s.tiles.builds')
            for yaw,pitch,zoom,pan,depth in ((0,0,1,(0,0),0),(35,20,2,(.2,-.2),16),
                                          (90,35,8,(-.4,.4),48),(170,-20,4,(.1,0),24),
                                          (35,25,1,(0,0),0)):
                game('s.camera_pan='+repr(pan)+'\ns.camera_depth='+repr(depth)+
                     '\ns.camera_view(%r,%r,%r)\ns.emit("camera_depth")\n_result=True'%(yaw,pitch,zoom))
                time.sleep(.9)
            frames=game('api._workflow_active=False\n_result=api._workflow_rows')
            result=game('_result={"new_builds":s.tiles.builds-'+str(before)+',"blocks":len(s.editor.document.blocks),"pose":s.camera_pose}')
            result.update(case='navigation',python_ms=summary([r[1] for r in frames]),
                          interval_ms=summary([(b[0]-a[0])*1000. for a,b in zip(frames,frames[1:])]))
            rows.append(result);print(json.dumps(result),flush=True)
            assert result['new_builds']==0 and result['blocks']==39944,result
        if args.orbit:
            import profile_orbit_angles
            previous=sys.argv
            try:
                for pc in (True,False):
                    sys.argv=['profile_orbit_angles.py','--label',args.label+'_max_'+('pc' if pc else 'touch'),
                              '--zoom','2','--depth','32']+(['--pc'] if pc else [])
                    profile_orbit_angles.main()
            finally:sys.argv=previous
    finally:
        if args.hotspots:
            (ui.OUT/'perf67_workflow_hotspots.json').write_text(json.dumps(game('_result=api._workflow_hotspots'),indent=2),encoding='utf8')
        game('''api._workflow_active=False
host.notify_game_render_tick=api._workflow_tick
s.cancel_edit()
s.edit_job=None
for k,v in api._workflow_saved.items():setattr(s,k,v)
s.camera_revision+=1
s.refresh_preview();s.emit()
_result=True''')
        settle()
        (ui.OUT/('perf67_workflows_'+args.label+'.json')).write_text(json.dumps(rows,indent=2),encoding='utf8')


if __name__=='__main__':main()
