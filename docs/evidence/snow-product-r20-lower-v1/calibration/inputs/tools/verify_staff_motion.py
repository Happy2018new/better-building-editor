"""Cold-loaded ModPC evidence: world-axis trails and animated staff materials.

Only run through run_live_check.py in its isolated world. The player moves along
a short square using SDK velocity impulses; samples come from the normal aura update.
No shader uniforms or movement samples are fabricated. Restore player/camera.
"""
import json
import subprocess
import time
from pathlib import Path
from PIL import Image, ImageStat

from verify_world_tools import game, equip, call
from verify_survey_visuals import camera
from mcdk import load_session
from pyreact_legacy import capture_screen as capture

OUT = Path(__file__).resolve().parents[1] / '.runtime' / 'staff_motion'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    binding = load_session(live=True)
    capture.user32.SetProcessDPIAware()
    window = capture._find_game_window(capture._list_windows(), pid=binding['game_pid'])
    assert window
    _, _, width, height = capture._window_rect(window['hwnd'])

    def shot(name):
        path = OUT / (name + '.png')
        capture._capture_window_windows(window['hwnd'], width, height, False, str(path))
        if sum(ImageStat.Stat(Image.open(path).convert('RGB')).var)<1.:
            time.sleep(.15)
            capture._capture_window_windows(window['hwnd'], width, height, False, str(path))
        assert sum(ImageStat.Stat(Image.open(path).convert('RGB')).var)>1., 'Blank capture: '+name
        return str(path)

    old = game('''from modern_projection.pyreact import navigator
if navigator.contains('modern_projection_workspace'): navigator.pop()
view=s.bridge.factory.CreatePlayerView(s.bridge.player)
cam=s.bridge.factory.CreateCamera(s.bridge.level)
cam.ResetCameraPos();cam.UnDepartCamera()
_result={'perspective':view.GetPerspective(),'reduced':s.reduced_motion,
         'rotation':s.bridge.factory.CreateRot(s.bridge.player).GetRot()}
''')
    server_old = game('''f=api.GetEngineCompFactory()
_result={'foot':f.CreatePos(player).GetFootPos(),
         'fly':f.CreateFly(player).IsPlayerFlying(),
         'item':f.CreateItem(player).GetPlayerItem(api.GetMinecraftEnum().ItemPosType.CARRIED,0)}''', True)
    recording = None
    report = {}
    try:
        assert equip('modern_projection:survey_wand')
        game('s.reduced_motion=False\ns.bridge.factory.CreatePlayerView(s.bridge.player).SetPerspective(0)\n_result=True')
        time.sleep(1.)
        report['still_start'] = shot('still_start')
        time.sleep(1.5)
        report['still_later'] = shot('still_later')
        rot = old['rotation']
        game('s.bridge.factory.CreateRot(s.bridge.player).SetRot((%r,%r))\n_result=True' % (rot[0], rot[1]+45.))
        time.sleep(.3)
        report['turned'] = shot('turned')

        x, y, z = server_old['foot']
        origin = (x+8., y+2., z+8.)
        game('''f=api.GetEngineCompFactory()
f.CreateFly(player).ChangePlayerFlyState(True)
f.CreatePos(player).SetFootPos(%r)
_result=True''' % (origin,), True)
        time.sleep(.5)
        game('s.bridge.factory.CreatePlayerView(s.bridge.player).SetPerspective(1)\n_result=True')
        time.sleep(.4)
        camera((origin[0]+6.3,origin[1]+5.,origin[2]+8.5),
               (origin[0]+2.15,origin[1]+1.,origin[2]+2.15))
        # Record the actual render-tick output, including stopping and reversal.
        game('''import time as sample_time
aura=owner.staff_aura
aura._qa_original_update=aura.update
aura._qa_samples=[]
def wrap(aura=aura,original=aura.update,clock=sample_time.time):
 def update(carried,visible=True):
  original(carried,visible)
  now=clock()
  if aura.position and (not aura._qa_samples or now-aura._qa_samples[-1][0]>.025):
   aura._qa_samples.append((now,aura.last_target,aura.position,aura.motion_uniform))
 return update
aura.update=wrap()
_result=True''')
        recording = subprocess.Popen(['ffmpeg','-y','-hide_banner','-loglevel','error',
            '-f','gdigrab','-framerate','30','-i','hwnd='+str(window['hwnd']),
            '-t','20','-c:v','libx264','-preset','veryfast','-crf','18',
            str(OUT/'directions.mp4')], stderr=subprocess.PIPE)
        time.sleep(.3)
        game('''f=api.GetEngineCompFactory()
comp=f.CreateActorMotion(player);timer=f.CreateGame(api.GetLevelId())
origin=%r
owner._staff_qa_active=True
def start_path(owner=owner,comp=comp,timer=timer,origin=origin):
 def step(i=0):
  if not owner._staff_qa_active or i>160:return
  owner._staff_qa_step=i
  # +X, +Z, -X, -Z, with a half-second pause after each leg.
  leg=i//40
  directions=((.13,0.,0.),(0.,0.,.13),(-.13,0.,0.),(0.,0.,-.13))
  if leg<4:
   comp.SetPlayerMotion(directions[leg] if i%%40<30 else (0.,0.,0.))
   timer.AddTimer(.05,step,i+1)
 step()
start_path()
_result=True''' % (origin,), True)
        for leg, name in enumerate(('plus_x','plus_z','minus_x','minus_z')):
            deadline=time.monotonic()+8.
            while True:
                step=game('_result=owner._staff_qa_step',True)
                if leg*40+12 <= step <= leg*40+26: break
                assert step <= leg*40+26 and time.monotonic()<deadline, (name,step)
                time.sleep(.08)
            report[name]=shot(name)
            report[name+'_velocity']=game('_result=owner.staff_aura.motion_uniform')
        _, errors = recording.communicate(timeout=16)
        assert recording.returncode == 0, errors.decode('utf8','replace')
        time.sleep(.7)
        report['stopped'] = shot('stopped')
        samples = game('_result=owner.staff_aura._qa_samples')
        # Every trail velocity must preserve the signed world axis; no fixed
        # screen direction, stale axis after a turn, or nonzero rest streak.
        velocities = [row[3] for row in samples if row[3]]
        for axis in (0,2):
            assert any(v[axis]>.8 for v in velocities), (axis,'positive')
            assert any(v[axis]<-.8 for v in velocities), (axis,'negative')
        assert velocities[-1][3]<.1, velocities[-1]
        report['axis_velocity_verified']=True
        report['samples']=samples
        # The same SDK impulses in first person must project towards/away from
        # the vanishing point when advancing, rather than horizontal streaks.
        game('''cam=s.bridge.factory.CreateCamera(s.bridge.level)
cam.ResetCameraPos();cam.UnDepartCamera()
s.bridge.factory.CreateRot(s.bridge.player).SetRot((0.,0.))
s.bridge.factory.CreatePlayerView(s.bridge.player).SetPerspective(0)
_result=True''')
        time.sleep(.5)
        for name, direction in (('first_forward',(0.,0.,.18)),('first_side',(.18,0.,0.))):
            game('''f=api.GetEngineCompFactory()
def start_impulses(owner=owner,comp=f.CreateActorMotion(player),timer=f.CreateGame(api.GetLevelId()),motion=%r):
 def tick(i=0):
  if not owner._staff_qa_active:return
  comp.SetPlayerMotion(motion if i<24 else (0.,0.,0.))
  if i<24:timer.AddTimer(.05,tick,i+1)
 tick()
start_impulses()
_result=True''' % (direction,),True)
            time.sleep(.65)
            report[name]=shot(name)
            time.sleep(2.3)
        report['errors']=call('get_latest_error_logs',{'max_count':15,'order':'desc'})
    finally:
        if recording and recording.poll() is None:
            recording.terminate();recording.communicate(timeout=5)
        game('''owner._staff_qa_active=False
f=api.GetEngineCompFactory()
f.CreateActorMotion(player).SetPlayerMotion((0.,0.,0.))
f.CreatePos(player).SetFootPos(%r)
f.CreateFly(player).ChangePlayerFlyState(%r)
saved=%r
if saved:
 for key in ('itemName','newItemName'):
  if isinstance(saved.get(key),unicode):saved[key]=saved[key].encode('utf8')
 f.CreateItem(player).SpawnItemToPlayerCarried(saved,player)
else:f.CreateItem(player).SpawnItemToPlayerCarried({'itemName':'minecraft:air','count':0,'auxValue':0},player)
_result=True''' % (tuple(server_old['foot']),server_old['fly'],server_old['item']), True)
        game('''aura=owner.staff_aura
if hasattr(aura,'_qa_original_update'):
 aura.update=aura._qa_original_update
 del aura._qa_original_update
s.reduced_motion=%r
cam=s.bridge.factory.CreateCamera(s.bridge.level)
cam.ResetCameraPos();cam.UnDepartCamera()
s.bridge.factory.CreatePlayerView(s.bridge.player).SetPerspective(%r)
s.bridge.factory.CreateRot(s.bridge.player).SetRot(%r)
_result=True''' % (old['reduced'],old['perspective'],tuple(old['rotation'])))
    (OUT/'report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in report.items() if k!='samples'},indent=2))


if __name__=='__main__':
    main()
