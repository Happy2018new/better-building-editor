"""Real survey VFX in a bound isolated game; never edits the building library.
All stills and videos use the live animation and bounded burst lifetimes.
"""
import json
import subprocess
import time
from pathlib import Path
from verify_world_tools import game, snapshot, equip
from verify_survey_visuals import box, camera
from mcdk import load_session
from pyreact_legacy import capture_screen as capture
OUT = Path(__file__).resolve().parents[1] / '.runtime'


def main():
    binding = load_session(live=True)
    capture.user32.SetProcessDPIAware()
    window = capture._find_game_window(capture._list_windows(), pid=binding['game_pid'])
    assert window
    old = game('_result=s.bridge.corners')
    saved = game('''f=api.GetEngineCompFactory()
_result=[f.CreatePos(player).GetFootPos(),f.CreateFly(player).IsPlayerFlying(),
         f.CreateTime(api.GetLevelId()).GetTime()]''', True)
    x, base, z = int(saved[0][0]), max(300, int(saved[0][1]) + 70), int(saved[0][2])
    evidence = {}

    def raw(name):
        # Let native actor registration and the camera anchor reach a render
        # tick before collecting pixels after an asynchronous camera change.
        time.sleep(.4)
        unused_x, unused_y, width, height = capture._window_rect(window['hwnd'])
        path = OUT / ('survey75_' + name + '.png')
        capture._capture_window_windows(window['hwnd'], width, height, False, str(path))
        return str(path)

    def video(name):
        path = OUT / ('survey75_' + name + '.mp4')
        # Capture only the verified game's HWND, never desktop/other apps.
        run = subprocess.run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
            '-f', 'gdigrab', '-framerate', '30', '-i', 'hwnd=' + str(window['hwnd']),
            '-t', '9', '-vf', 'scale=1280:-2', '-c:v', 'libx264', '-preset', 'veryfast',
            '-crf', '20', str(path)], capture_output=True, text=True, timeout=25)
        assert run.returncode == 0, run.stderr
        return str(path)

    try:
        equip('modern_projection:survey_wand')
        game('''f=api.GetEngineCompFactory()
f.CreateFly(player).ChangePlayerFlyState(True)
f.CreatePos(player).SetPos(%r)
f.CreateTime(api.GetLevelId()).SetTimeOfDay(18000)
_result=True''' % ((x, base, z),), True)
        camera((x, base+4., z+8.), (x+.5, base+6.5, z+4.5))
        game('''e=s.bridge.survey_effects
e.clear()
s.bridge.corners=[None,None]
e.strike(%r)
_result=True''' % ((x, base+6, z+4),))
        time.sleep(.35)
        evidence['comet_live'] = raw('comet_final')
        game('''from functools import partial
e=s.bridge.survey_effects
e.clear()
for delay in (1.,3.5,6.):s.bridge.later(delay,partial(e.strike,%r))
_result=True''' % ((x, base+6, z+4),))
        evidence['comet_video'] = video('comet_motion')
        camera((x+7.,base+9.,z+11.),(x+2.,base+5.5,z+5.))
        time.sleep(.2)
        ids = box((x,base+3,z+3),(4,5,4))
        evidence['orbits_video'] = video('orbits_motion')
        evidence['night'] = raw('orbits_night')
        # Inspect glow thickness and genuine crystal faces in a close view.
        camera((x+4.8,base+8.,z+9.),(x+2.,base+5.5,z+5.))
        evidence['detail'] = raw('detail')
        assert ids == game('_result=[r[0] for r in s.bridge.survey_effects.layers]')
        evidence['static_entities_reused'] = True
        game('api.GetEngineCompFactory().CreateTime(api.GetLevelId()).SetTimeOfDay(6000)\n_result=True',True)
        time.sleep(.4)
        evidence['day'] = raw('orbits_day')
        box((x,base+3,z+3),(1,1,1))
        camera((x+2.,base+5.,z+6.),(x+.5,base+3.5,z+3.5))
        time.sleep(1.3)
        evidence['single'] = snapshot('survey75_single')
        ids = box((x-32,base-32,z-32),(64,128,64))
        # A detached camera does not load distant actor chunks. Move the test
        # player with this far camera so it matches real player observation.
        game('api.GetEngineCompFactory().CreatePos(player).SetPos(%r)\n_result=True' % ((x+85.,base+80.,z+90.),),True)
        camera((x+85.,base+80.,z+90.),(x,base+32.,z))
        time.sleep(1.3)
        evidence['maximum'] = raw('maximum')
        game('api.GetEngineCompFactory().CreatePos(player).SetPos(%r)\n_result=True' % ((x,base,z),),True)
        camera((x,base,z),(x+32,base,z+32))
        evidence['inside'] = raw('inside')
        assert ids == game('_result=[r[0] for r in s.bridge.survey_effects.layers]')
        evidence['camera_entities_reused'] = True
        assert game("_result=[e for e in api.GetEngineActor().values() if e.get('identifier','').startswith('modern_projection:survey_')]",True)==[]
        evidence['server_effect_entities'] = 0
        game('for unused in range(20):s.bridge.survey_effects.strike(%r)\n_result=True' % ((x,base,z),))
        assert game('_result=len(s.bridge.survey_effects.bursts)') <= 3
        time.sleep(2.)
        assert game('_result=len(s.bridge.survey_effects.bursts)') == 0
        evidence['bounded_bursts_expire'] = True
    finally:
        game('''s.bridge.survey_effects.clear()
s.bridge.corners=%r
s.bridge.draw_bounds()
cam=s.bridge.factory.CreateCamera(s.bridge.level)
cam.ResetCameraPos();cam.UnDepartCamera()
_result=True''' % old)
        game('''f=api.GetEngineCompFactory()
f.CreatePos(player).SetPos(%r)
f.CreateFly(player).ChangePlayerFlyState(%r)
f.CreateTime(api.GetLevelId()).SetTime(%r)
_result=True''' % (tuple(saved[0]),saved[1],saved[2]),True)
        (OUT/'survey75_evidence.json').write_text(json.dumps(evidence,indent=2),encoding='utf8')
    print(json.dumps(evidence,indent=2))


if __name__ == '__main__':
    main()
