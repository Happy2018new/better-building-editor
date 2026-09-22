"""Native render-frame intervals during slow/large held orbits, with SDK FPS."""
import argparse
import json
import math
import time
import verify_ui as ui
import capture_screen as capture
from verify_font_share_polish import game
from verify_interaction import pointer
from verify_large_editor import snapshot
from native_input_mode import set_touch,state


def summary(values):
    values=sorted(values)
    return {'median':values[len(values)//2],'p95':values[int(len(values)*.95)],'max':max(values)} if values else {}


def main():
    p=argparse.ArgumentParser();p.add_argument('--label',default='before');p.add_argument('--pc',action='store_true');p.add_argument('--profile',action='store_true');p.add_argument('--depth',type=float,default=0.);p.add_argument('--zoom',type=float,default=1.)
    args=p.parse_args()
    capture.user32.SetProcessDPIAware()
    window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd'])
    original=state()['simulated']
    saved=game('import json\n_result=json.dumps(s.editor.document.to_data(),ensure_ascii=True)')
    if args.label=='before':(ui.OUT/'stage54_current_document.json').write_text(saved,encoding='utf8')
    print(game('_result={"size":s.editor.document.size,"blocks":len(s.editor.document.blocks),"depth":s.camera_depth,"zoom":s.zoom,"tiles":len(s.tiles.render_keys)}'),flush=True)
    set_touch(not args.pc)
    game('''import time
from HelloScript.pyreact import host
from HelloScript.projection import scene
api._orbit_saved=(s.camera_yaw,s.camera_pitch,s.zoom,s.camera_pan,s.camera_pivot,s.camera_depth,s.page,s.grid,host.notify_game_render_tick )
api._orbit_record={'active':False,'rows':[],'fps':0.,'poll':0.,'profile':False,'slow':[]}
def recorder(original,record,clock,session,component):
    import cProfile,pstats,cStringIO
    def frame():
        profile=cProfile.Profile() if record['active'] and record['profile'] else None
        start=clock()
        if profile:profile.enable()
        try:return original()
        finally:
            if profile:profile.disable()
            if record['active']:
                cost=(clock()-start)*1000.
                if profile and cost>50.:
                    stream=cStringIO.StringIO();pstats.Stats(profile,stream=stream).sort_stats('cumulative').print_stats(22)
                    record['slow'].append((session.camera_pose[0],cost,stream.getvalue()))
                if start-record['poll']>.25:
                    record['fps']=component.GetFps();record['poll']=start
                record['rows'].append((start,cost,session.camera_pose[0],session.camera_pose[1],record['fps'],session.camera_dragging))
    return frame
host.notify_game_render_tick=recorder(host.notify_game_render_tick,api._orbit_record,time.clock,s,s.bridge.factory.CreateGame(s.bridge.level))
s.set('page','workspace')
s.reset_camera(False)
_result=True''')
    reports=[]
    try:
        if args.profile:game('api._orbit_record["profile"]=True\n_result=True')
        for title,center,amplitude in (('small35',35.,6.),('small0',0.,6.),('wide',0.,45.)):
            game('s.reset_camera(False)\ns.camera_view(%r,0.,%r)\ns.camera_depth=%r\ns.emit("camera_depth")\n_result=True'%(center,args.zoom,args.depth))
            time.sleep(1.3)
            native=ui.call('native_control',pointer()['id'])['result']
            root=ui.nodes('SafeArea')[0]['children'][0]['layout']
            left,top,width,height=capture._window_rect(window['hwnd']);scale=width/root['width']
            design=game('from HelloScript.projection.widgets import Theme\n_result=Theme.scale')
            x=int(left+(native['global'][0]+native['size'][0]*.5)*scale)
            y=int(top+(native['global'][1]+native['size'][1]*.4)*scale)
            game('api._orbit_record["rows"]=[]\napi._orbit_record["slow"]=[]\napi._orbit_record["active"]=True\n_result=True')
            builds=game('_result=s.tiles.builds')
            capture.user32.SetCursorPos(x,y);time.sleep(.1);capture.user32.mouse_event(2,0,0,0,0)
            start=time.perf_counter()
            try:
                while True:
                    elapsed=time.perf_counter()-start
                    if elapsed>=6.:break
                    assert capture.user32.GetForegroundWindow()==window['hwnd'],'Game lost foreground'
                    dx=amplitude/.42*design*scale*math.sin(elapsed*math.pi*2./3.)
                    capture.user32.SetCursorPos(x+int(dx),y);time.sleep(.025)
            finally:capture.user32.mouse_event(4,0,0,0,0)
            time.sleep(.7)
            rows=game('api._orbit_record["active"]=False\n_result=api._orbit_record["rows"]')
            assert sum(r[5] for r in rows)>40,'No sustained native drag; do not count idle frames as orbit measurements'
            assert max(r[2] for r in rows)-min(r[2] for r in rows)>amplitude*.5,'Camera did not follow the intended orbit'
            assert game('_result=s.tiles.builds')==builds
            intervals=[(b[0]-a[0])*1000 for a,b in zip(rows,rows[1:]) if a[5] and b[5]]
            all_intervals=[(b[0]-a[0])*1000 for a,b in zip(rows,rows[1:])]
            report={'case':title,'depth':args.depth,'zoom':args.zoom,'frames':len(rows),'interval_ms':summary(intervals),'with_release_ms':summary(all_intervals),'python_ms':summary([r[1] for r in rows]),'sdk_fps':summary([r[4] for r in rows]),'slow_frames':sum(v>33.3 for v in all_intervals)}
            slow=game('_result=api._orbit_record["slow"]')
            reports.append({'summary':report,'rows':rows,'slow_profiles':slow});print(json.dumps(report),flush=True)
            if slow:print(slow[0][2],flush=True)
        snapshot('stage54_orbit_'+args.label)
    finally:
        capture.user32.mouse_event(4,0,0,0,0)
        game('''api._orbit_record['active']=False
s.camera_yaw,s.camera_pitch,s.zoom,s.camera_pan,s.camera_pivot,s.camera_depth,s.page,s.grid,host.notify_game_render_tick=api._orbit_saved
s.camera_pose=(s.camera_yaw,s.camera_pitch,s.zoom)
s.camera_revision+=1
s.emit()
_result=True''')
        set_touch(original)
        (ui.OUT/('stage54_orbit_'+args.label+'.json')).write_text(json.dumps(reports,indent=2),encoding='utf8')


if __name__=='__main__':main()
