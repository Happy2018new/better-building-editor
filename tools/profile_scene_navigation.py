"""Bound scene navigation baseline; restore the user's camera and draft."""
import json
import sys
import time
import verify_ui as ui
from verify_materials_paste import game
from mcdk import Client


def main():
    label = 'before' if '--baseline' in sys.argv else 'after'
    if '--restore-fixture' in sys.argv:
        payload=(ui.OUT/'stage51_current_document.json').read_text(encoding='utf8')
        game('import json\nfrom HelloScript.projection.model import Document\ns._loaded(Document.from_data(json.loads('+repr(payload)+')))\n_result=True')
        for unused in range(240):
            if not game('_result=s.preview_pending'):break
            time.sleep(.25)
    payload=game('import json\nfrom HelloScript.projection.codec import to_data\n_result=json.dumps(to_data(s.editor.document),ensure_ascii=True)')
    if label=='before':(ui.OUT/'stage51_current_document.json').write_text(payload,encoding='utf8')
    game('''import time
api._navigation_saved=(s.camera_yaw,s.camera_pitch,s.zoom,s.camera_pan,s.camera_pivot,s.page)
s.set('page','workspace')
s.reset_camera(False)
h=api.GetTopScreen()
cls=type(h)
cls._navigation_original=cls._pyreact_tick_animation_frames
h._navigation_samples=[]
def tick(self,now=None):
    started=time.clock()
    try:return self._navigation_original(now)
    finally:self._navigation_samples.append((time.time(),(time.clock()-started)*1000))
cls._pyreact_tick_animation_frames=tick
_result=True''')
    time.sleep(.5)
    with Client() as client:
        prof=client.call('mc_profiler',{'op':'/start','args':{'kind':'python.cpu','target':'client','clock':'wall','duration_seconds':9,'storage':'disk'}})
    (ui.OUT/('stage51_profiler_'+label+'.json')).write_text(json.dumps(prof),encoding='utf8')
    job=prof['structuredContent']['job']['id']
    try:
        game('h._navigation_samples=[]\n_result=True')
        for yaw,pitch,zoom,pan in ((90,35,1,(0,0)),(150,15,3,(0,0)),(220,45,8,(.4,-.2)),(270,25,3,(0,0)),(35,25,1,(0,0))):
            game('s.camera_pan='+repr(pan)+'\ns.camera_view(yaw=%r,pitch=%r,zoom=%r)\n_result=True'%(yaw,pitch,zoom))
            time.sleep(1.35)
        samples=game('_result=h._navigation_samples')
        costs=sorted(v[1] for v in samples)
        intervals=sorted((samples[i][0]-samples[i-1][0])*1000 for i in range(1,len(samples)))
        summary={'frames':len(samples),'frame_work_ms':{'median':costs[len(costs)//2],'p95':costs[int(len(costs)*.95)],'max':max(costs)},
                 'interval_ms':{'median':intervals[len(intervals)//2],'p95':intervals[int(len(intervals)*.95)]}}
        print(json.dumps(summary),flush=True)
        (ui.OUT/('stage51_navigation_'+label+'.json')).write_text(json.dumps({'summary':summary,'samples':samples}),encoding='utf8')
        time.sleep(2.)
        with Client() as client:result=client.call('mc_profiler',{'op':'/query','args':{'job_id':job,'view':'hotspots','limit':25}})
        (ui.OUT/('stage51_hotspots_'+label+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
        print('Profiler job '+job,flush=True)
    finally:
        game('''cls=type(api.GetTopScreen())
cls._pyreact_tick_animation_frames=cls._navigation_original
del cls._navigation_original
s.camera_yaw,s.camera_pitch,s.zoom,s.camera_pan,s.camera_pivot,s.page=api._navigation_saved
s.camera_pose=(s.camera_yaw,s.camera_pitch,s.zoom)
s.camera_revision+=1
s.emit('view')
_result=True''')


if __name__=='__main__':main()
