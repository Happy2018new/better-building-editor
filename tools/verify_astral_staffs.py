"""Capture both staff views and check bounded aura lifetime in an isolated world."""
import json
import subprocess
import time
from pathlib import Path
from verify_world_tools import game, equip, snapshot, call
from verify_survey_visuals import camera
from mcdk import load_session
from pyreact_legacy import capture_screen as capture

OUT=Path(__file__).resolve().parents[1]/'.runtime'


def main():
    binding=load_session(live=True)
    old=game('''from HelloScript.pyreact import navigator
if navigator.contains('modern_projection_workspace'):navigator.pop()
cam=s.bridge.factory.CreateCamera(s.bridge.level)
cam.ResetCameraPos()
cam.UnDepartCamera()
view=s.bridge.factory.CreatePlayerView(s.bridge.player)
_result={'perspective':view.GetPerspective(),'foot':s.bridge.factory.CreatePos(s.bridge.player).GetFootPos()}
''')
    carried=game('''item=api.GetEngineCompFactory().CreateItem(player)
_result=item.GetPlayerItem(api.GetMinecraftEnum().ItemPosType.CARRIED,0)''',True)
    report={}
    try:
        game('s.bridge.factory.CreatePlayerView(s.bridge.player).SetPerspective(0)\n_result=True')
        time.sleep(.3)
        for name in ('terminal','survey_wand'):
            assert equip('modern_projection:'+name)
            time.sleep(.85)
            report[name+'_first']=snapshot('astral_'+name+'_first')
            report[name+'_aura']=game('_result=owner.staff_aura.entity')
            assert report[name+'_aura']
        assert report['terminal_aura']==report['survey_wand_aura']
        game('s.bridge.factory.CreatePlayerView(s.bridge.player).SetPerspective(1)\n_result=True')
        time.sleep(.4)
        x,y,z=old['foot']
        camera((x+2.3,y+1.6,z+3.1),(x,y+1.,z))
        time.sleep(.3)
        report['third']=snapshot('astral_survey_third')
        capture.user32.SetProcessDPIAware()
        window=capture._find_game_window(capture._list_windows(),pid=binding['game_pid'])
        assert window
        unused_x,unused_y,w,h=capture._window_rect(window['hwnd'])
        capture._capture_window_windows(window['hwnd'],w,h,False,str(OUT/'astral_staff_native.png'))
        result=subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error',
            '-f','gdigrab','-framerate','24','-i','hwnd='+str(window['hwnd']),
            '-t','5','-vf','scale=960:-2','-c:v','libx264','-preset','veryfast',
            '-crf','18',str(OUT/'astral_staff_motion.mp4')],capture_output=True,text=True,timeout=15)
        assert result.returncode==0,result.stderr
        assert equip('minecraft:stick')
        time.sleep(.25)
        report['unequip_cleared']=game('_result=owner.staff_aura.entity is None')
        assert report['unequip_cleared']
        report['python_errors']=call('get_latest_error_logs',{'max_count':12,'order':'desc'})
    finally:
        game('''cam=s.bridge.factory.CreateCamera(s.bridge.level)
cam.ResetCameraPos()
cam.UnDepartCamera()
s.bridge.factory.CreatePlayerView(s.bridge.player).SetPerspective(%r)
_result=True'''%old['perspective'])
        game('''item=api.GetEngineCompFactory().CreateItem(player)
saved=%r
if saved:
 for key in ('itemName','newItemName'):
  if isinstance(saved.get(key),unicode):saved[key]=saved[key].encode('utf8')
 item.SpawnItemToPlayerCarried(saved,player)
else:item.SpawnItemToPlayerCarried({'itemName':'minecraft:air','count':0,'auxValue':0},player)
_result=True'''%carried,True)
    (OUT/'astral_staff_report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
