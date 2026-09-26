"""F11 held orbit of the exact current ellipsoid, front view and depth view."""
import ctypes
from ctypes import wintypes
import json
import sys
import time
import verify_ui as ui
import capture_screen as capture
from verify_materials_paste import game
from verify_interaction import pointer
from native_input_mode import set_touch, state
from mcdk import Client


def main():
    label='before' if '--baseline' in sys.argv else 'after'
    capture.user32.SetProcessDPIAware()
    window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd'])
    original=state()['simulated']
    payload=(ui.OUT/'stage51_current_document.json').read_text(encoding='utf8')
    game('import json\nfrom modern_projection.projection.model import Document\ns._loaded(Document.from_data(json.loads('+repr(payload)+')))\ns.set("page","workspace")\ns.emit()\n_result=True')
    for unused in range(150):
        if not game('_result=s.preview_pending or getattr(s.tiles,"mounting",False)'):break
        time.sleep(.2)
    set_touch(True);time.sleep(1)
    game('''import time
h=api.GetTopScreen()
cls=type(h)
cls._ellipsoid_original=cls._pyreact_tick_animation_frames
def make_tick(clock,wall):
    def tick(self,now=None):
        start=clock()
        try:return self._ellipsoid_original(now)
        finally:
            if getattr(self,'_ellipsoid_record',False):self._ellipsoid_samples.append((wall(),(clock()-start)*1000.))
    return tick
cls._pyreact_tick_animation_frames=make_tick(time.clock,time.time)
_result=True''')
    reports=[]
    try:
        for depth in (0,40):
            game('s.reset_camera(False)\ns.camera_view(0.,0.,1.)\ns.camera_depth=%r\ns.emit("camera_depth")\n_result=True'%depth)
            time.sleep(1.2)
            native=ui.call('native_control',pointer()['id'])['result']
            root=ui.nodes('SafeArea')[0]['children'][0]['layout']
            left,top,width,height=capture._window_rect(window['hwnd']);scale=width/root['width']
            x=int(left+(native['global'][0]+native['size'][0]*.5)*scale)
            y=int(top+(native['global'][1]+native['size'][1]*.45)*scale)
            with Client() as client:
                job=client.call('mc_profiler',{'op':'/start','args':{'kind':'python.cpu','target':'client','clock':'wall','duration_seconds':7,'storage':'disk'}})['structuredContent']['job']['id']
            game('h=api.GetTopScreen()\nh._ellipsoid_samples=[]\nh._ellipsoid_record=True\n_result=True')
            builds=game('_result=s.tiles.builds')
            capture.user32.SetCursorPos(x,y);time.sleep(.1);capture.user32.mouse_event(2,0,0,0,0)
            try:
                for i in range(120):
                    assert capture.user32.GetForegroundWindow()==window['hwnd'],'Game lost foreground'
                    dx=(i if i<60 else 120-i)*1.7*scale
                    capture.user32.SetCursorPos(x+int(dx),y+int(i*.1*scale));time.sleep(.035)
            finally:capture.user32.mouse_event(4,0,0,0,0)
            samples=game('h._ellipsoid_record=False\n_result=h._ellipsoid_samples')
            assert game('_result=s.tiles.builds')==builds
            costs=sorted(v[1] for v in samples)
            row={'depth':depth,'samples':len(samples),'median_ms':costs[len(costs)//2], 'p95_ms':costs[int(len(costs)*.95)],'max_ms':max(costs),'job':job}
            reports.append(row);print(json.dumps(row),flush=True)
            time.sleep(2)
            with Client() as client:report=client.call('mc_profiler',{'op':'/query','args':{'job_id':job,'view':'hotspots','limit':30}})
            (ui.OUT/('stage53_touch_%s_%d_hotspots.json'%(label,depth))).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    finally:
        game('cls=type(api.GetTopScreen())\ncls._pyreact_tick_animation_frames=cls._ellipsoid_original.im_func\ndel cls._ellipsoid_original\ns.reset_camera(False)\n_result=True')
        set_touch(original)
        (ui.OUT/('stage53_touch_'+label+'.json')).write_text(json.dumps(reports,indent=2),encoding='utf8')


if __name__=='__main__':main()
