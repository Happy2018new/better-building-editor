"""Survey VFX evidence in an isolated, explicitly bound MCDK world.

Creates only private visual bounds. Never edits blocks or the local library.
Run after cold loading the shaders/materials. Restores time, corners and camera.
"""
import json
import time
from pathlib import Path
from PIL import Image

from verify_world_tools import game, snapshot, call
from mcdk import load_session
from pyreact_legacy import capture_screen as capture

OUT = Path(__file__).resolve().parents[1] / '.runtime'


def camera(pos, target):
    return game('''cam=s.bridge.factory.CreateCamera(s.bridge.level)
cam.DepartCamera()
pos=%r;target=%r
rot=api.GetRotFromDir(tuple(target[i]-pos[i] for i in range(3)))
cam.SetCameraPos(pos)
cam.SetCameraRotation((rot[0],rot[1]+180.,0.))
_result=True''' % (pos,target))


def box(origin, size):
    high=tuple(origin[i]+size[i]-1 for i in range(3))
    result=game('''s.bridge.corners=[%r,%r]
s.bridge.draw_bounds()
_result=[r[0] for r in s.bridge.survey_effects.layers]''' % (origin,high))
    assert len(result)==3, result
    return result


def main():
    binding=load_session(live=True)
    capture.user32.SetProcessDPIAware()
    window=capture._find_game_window(capture._list_windows(),pid=binding['game_pid'])
    assert window
    old=game('_result=s.bridge.corners')
    clock=game('_result=api.GetEngineCompFactory().CreateTime(api.GetLevelId()).GetTime()',True)
    evidence={}
    try:
        ids=box((0,-60,2),(4,5,4))
        camera((7.,-54.,10.),(2.,-57.5,4.))
        time.sleep(.4)
        evidence['day']=snapshot('survey_final_day')
        x,y,w,h=capture._window_rect(window['hwnd'])
        capture._capture_window_windows(window['hwnd'],w,h,False,str(OUT/'survey_final_native.png'))
        # Record real rendered frames, with real timestamps (no synthesized
        # in-betweens); this is appearance evidence, not a GPU benchmark.
        frames=[];stamps=[]
        started=time.perf_counter()
        for unused in range(48):
            path=OUT/'survey_frame.png'
            capture._capture_window_windows(window['hwnd'],w,h,False,str(path))
            im=Image.open(path).convert('RGB')
            frames.append(im.resize((960,round(h*960/w)),Image.Resampling.LANCZOS))
            stamps.append(time.perf_counter())
            time.sleep(.10)
        durations=[max(20,int((stamps[i+1]-stamps[i])*1000)) for i in range(len(stamps)-1)]
        durations.append(durations[-1])
        frames[0].save(OUT/'survey_final_motion.webp',save_all=True,append_images=frames[1:],
                       duration=durations,loop=0,quality=85)
        evidence['recorded_seconds']=time.perf_counter()-started
        assert ids==game('_result=[r[0] for r in s.bridge.survey_effects.layers]')
        evidence['stationary_entities_reused']=True
        game('api.GetEngineCompFactory().CreateTime(api.GetLevelId()).SetTimeOfDay(18000)\n_result=True',True)
        time.sleep(.3)
        evidence['night']=snapshot('survey_final_night')
        box((0,-60,2),(1,1,1))
        camera((2.,-57.8,4.5),(.5,-59.5,2.5))
        time.sleep(.3)
        evidence['single']=snapshot('survey_final_single')
        ids=box((-32,-60,-32),(64,128,64))
        camera((60.,38.,64.),(0.,4.,0.))
        time.sleep(.3)
        evidence['maximum']=snapshot('survey_final_maximum')
        camera((2.,-57.,2.),(32.,-55.,32.))
        time.sleep(.3)
        evidence['inside']=snapshot('survey_final_inside')
        assert ids==game('_result=[r[0] for r in s.bridge.survey_effects.layers]')
        evidence['camera_entities_reused']=True
        entities=game("_result=[e for e in api.GetEngineActor().values() if e.get('identifier','').startswith('modern_projection:survey_')]",True)
        assert entities==[],entities
        evidence['server_effect_entities']=0
        game('''for unused in range(20):s.bridge.survey_effects.strike((0,-59,2))
_result=len(s.bridge.survey_effects.bursts)''')
        assert game('_result=len(s.bridge.survey_effects.bursts)')<=3
        time.sleep(2.)
        assert game('_result=len(s.bridge.survey_effects.bursts)')==0
        evidence['bounded_bursts_expire']=True
    finally:
        game('api.GetEngineCompFactory().CreateTime(api.GetLevelId()).SetTime(%r)\n_result=True'%clock,True)
        game('''s.bridge.corners=%r
s.bridge.draw_bounds()
cam=s.bridge.factory.CreateCamera(s.bridge.level)
cam.ResetCameraPos();cam.UnDepartCamera()
_result=True'''%old)
        (OUT/'survey72_visual_checks.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(evidence,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
