"""Record the live fragment formation and enlarged gold/starry orbit particles.

Run through run_live_check.py in an isolated MCDK development world. Only
temporary client VFX and the camera are changed; no blocks/library are written.
"""
import json
import subprocess
import time
from pathlib import Path
from PIL import Image
from verify_world_tools import game
from verify_survey_visuals import camera
from mcdk import load_session
from pyreact_legacy import capture_screen as capture

OUT = Path(__file__).resolve().parents[1] / '.runtime'


def main():
    binding = load_session(live=True)
    capture.user32.SetProcessDPIAware()
    window = capture._find_game_window(capture._list_windows(), pid=binding['game_pid'])
    assert window and not window['minimized']
    saved = game('_result=[s.bridge.corners,s.bridge.corner_faces,s.bridge.player_origin()]')
    x, y, z = saved[2]
    point = (x, y+2, z+3)
    centre = (x+.5, y+2.5, z+3.5)
    report = {}
    try:
        game('''s.bridge.survey_effects.clear()
s.bridge.corners=[%r,None]
s.bridge.corner_faces=[3,None]
s.bridge.survey_effects.sync_points(s.bridge.corners,s.bridge.corner_faces)
_result=True''' % (point,))
        camera((x+.5,y+2.6,z+7.), centre)
        time.sleep(.4)
        game('''e=s.bridge.survey_effects
api._fragment_review_id=e.points[0]['id']
s.bridge.later(1.,lambda:e.pulse_point(0))
s.bridge.later(3.6,lambda:e.pulse_point(0))
_result=True''')
        video = OUT / 'survey_fragment_formation.mp4'
        result = subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error',
            '-f','gdigrab','-framerate','24','-i','hwnd='+str(window['hwnd']),
            '-t','6','-vf','scale=960:-2','-c:v','libx264','-preset','veryfast',
            '-crf','18',str(video)], capture_output=True, text=True, timeout=20)
        assert result.returncode == 0, result.stderr
        report['replayed_on_same_actor'] = game(
            "_result=api._fragment_review_id==s.bridge.survey_effects.points[0]['id']")
        assert report['replayed_on_same_actor']
        # Use the same camera and shape for both colour variants.
        game('''from HelloScript.projection.survey_effects import WireEffects
from HelloScript.projection.outline_settings import defaults
s.bridge.survey_effects.clear()
api._fragment_review_outline=WireEffects(s.bridge)
_result=True''')
        orbit_camera=(x+6.,y+4.,z+9.)
        for style in ('golden','starry'):
            camera(orbit_camera,(x+1.,y+1.5,z+3.))
            game('''e=api._fragment_review_outline
e.configure_style(%r,defaults()[%r])
e.replace(%r,(4,3,4))
e.follow(%r,%r)
_result=True''' % (style,style,(x-1,y,z+1),orbit_camera,orbit_camera))
            time.sleep(1.4)
            # This detached fixture is not in the bridge's render-tick list.
            # Advance its entrance after waiting before judging particle size.
            game('api._fragment_review_outline.follow(%r,%r)\n_result=True' % (orbit_camera,orbit_camera))
            unused_x,unused_y,width,height=capture._window_rect(window['hwnd'])
            path=OUT/('survey_orbit_large_'+style+'.png')
            capture._capture_window_windows(window['hwnd'],width,height,False,str(path))
            with Image.open(path) as image:
                assert sum(hi-lo for lo,hi in image.convert('RGB').getextrema())>50
            motion=OUT/('survey_orbit_large_'+style+'.mp4')
            result=subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error',
                '-f','gdigrab','-framerate','24','-i','hwnd='+str(window['hwnd']),
                '-t','3','-vf','scale=960:-2','-c:v','libx264','-preset','veryfast',
                '-crf','18',str(motion)],capture_output=True,text=True,timeout=15)
            assert result.returncode==0,result.stderr
        report['video']=str(video)
    finally:
        game('''effect=getattr(api,'_fragment_review_outline',None)
if effect is not None:
 effect.clear()
 del api._fragment_review_outline
s.bridge.survey_effects.clear()
s.bridge.corners=%r
s.bridge.corner_faces=%r
s.bridge.draw_bounds()
cam=s.bridge.factory.CreateCamera(s.bridge.level)
cam.ResetCameraPos()
cam.UnDepartCamera()
_result=True''' % (saved[0],saved[1]))
    (OUT/'survey_fragment_review.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
