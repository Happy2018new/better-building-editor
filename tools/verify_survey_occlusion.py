"""Occlusion evidence in the explicitly bound test world; restores every block."""
import json
import time
from pathlib import Path
from PIL import Image, ImageChops
from verify_world_tools import game
from verify_survey_visuals import camera, box
from mcdk import load_session
from pyreact_legacy import capture_screen as capture

OUT=Path(__file__).resolve().parents[1]/'.runtime'

def main():
 binding=load_session(live=True)
 capture.user32.SetProcessDPIAware()
 window=capture._find_game_window(capture._list_windows(),pid=binding['game_pid'])
 old=game('_result=s.bridge.corners')
 saved=game("""f=api.GetEngineCompFactory()
_result=[f.CreatePos(player).GetFootPos(),f.CreateFly(player).IsPlayerFlying(),f.CreateTime(api.GetLevelId()).GetTime()]""",True)
 blocks=game("""b=api.GetEngineCompFactory().CreateBlockInfo(api.GetLevelId())
_result=[((x,y,4),b.GetBlockNew((x,y,4),0)) for x in range(-5,6) for y in range(258,269)]""",True)
 def raw(name):
  time.sleep(.4)
  unused_x,unused_y,w,h=capture._window_rect(window['hwnd'])
  path=OUT/('survey75_'+name+'.png')
  capture._capture_window_windows(window['hwnd'],w,h,False,str(path))
  return path
 try:
  game("""f=api.GetEngineCompFactory()
f.CreateFly(player).ChangePlayerFlyState(True)
f.CreatePos(player).SetPos((0.,262.,-6.))
f.CreateTime(api.GetLevelId()).SetTimeOfDay(6000)
b=f.CreateBlockInfo(api.GetLevelId())
for x in range(-5,6):
 for y in range(258,269): b.SetBlockNew((x,y,4),{'name':'minecraft:stone','aux':0},0,0,True,False)
_result=True""",True)
  camera((0.,264.,-6.),(0.,264.,7.))
  time.sleep(.3)
  box((-2,262,5),(4,4,4))
  time.sleep(1.4)
  on=raw('occluded_guide')
  game('s.bridge.survey_effects.clear()\n_result=True')
  off=raw('occluded_without_guide')
  a,b=Image.open(on).convert('RGB'),Image.open(off).convert('RGB')
  # Central stone wall excludes HUD, sky, and independently moving world actors.
  crop=(a.width//3,a.height//4,a.width*2//3,a.height*3//5)
  diff=ImageChops.difference(a.crop(crop),b.crop(crop))
  changed=sum(max(pixel)>4 for pixel in diff.getdata())
  evidence={'guide':str(on),'without':str(off),'wall_pixels_changed':changed}
  (OUT/'survey75_occlusion.json').write_text(json.dumps(evidence,indent=2),encoding='utf8')
  print(json.dumps(evidence,indent=2))
  assert changed>50,'Occluded selection locator did not reach the framebuffer'
 finally:
  game("""f=api.GetEngineCompFactory()
b=f.CreateBlockInfo(api.GetLevelId())
for pos,data in %r:
 b.SetBlockNew(tuple(pos),data or {'name':'minecraft:air','aux':0},0,0,True,False)
f.CreatePos(player).SetPos(%r)
f.CreateFly(player).ChangePlayerFlyState(%r)
f.CreateTime(api.GetLevelId()).SetTime(%r)
_result=True"""%(blocks,tuple(saved[0]),saved[1],saved[2]),True)
  game("""s.bridge.survey_effects.clear()
s.bridge.corners=%r
s.bridge.draw_bounds()
cam=s.bridge.factory.CreateCamera(s.bridge.level)
cam.ResetCameraPos();cam.UnDepartCamera()
_result=True"""%old)

if __name__=='__main__':main()
