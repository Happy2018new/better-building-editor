"""Short native visual check for the three outline widths and survey marker."""
import json
import time

from verify_outline_styles import camera, raw
from verify_world_tools import game


def main():
    for unused in range(40):
        if game('_result=owner.session is not None'):
            break
        time.sleep(.25)
    else:
        raise RuntimeError('Client UI did not initialize after addon reload')
    saved = game('''f=api.GetEngineCompFactory()
_result=[f.CreatePos(player).GetFootPos(),f.CreateFly(player).IsPlayerFlying(),
f.CreateTime(api.GetLevelId()).GetTime()]''', True)
    active = game('_result=s.projection_active')
    if active:
        raise RuntimeError('Expected an idle isolated test world')
    game('''api._targeted_client=(s.outline_style,s.projection_outline,list(s.bridge.corners),list(s.bridge.corner_faces))
_result=True''')
    results = {}
    try:
        game('''f=api.GetEngineCompFactory()
f.CreateFly(player).ChangePlayerFlyState(True)
f.CreatePos(player).SetFootPos((48.,310.,52.))
f.CreateTime(api.GetLevelId()).SetTimeOfDay(6000)
b=f.CreateBlockInfo(api.GetLevelId())
api._targeted_glass={}
api._targeted_wall=[]
for x in range(36,49):
 for y in range(300,310):
  p=(x,y,40)
  api._targeted_wall.append(p)
  api._targeted_glass[p]=b.GetBlockNew(p,0)
  b.SetBlockNew(p,{'name':'minecraft:glass','aux':0},0,0,True,False)
# Enclose the water fixture on all five sides; it must not flow into the world.
for x in range(38,47):
 for z in range(41,50):
  for y in (301,302):
   p=(x,y,z)
   api._targeted_glass[p]=b.GetBlockNew(p,0)
   edge=x in (38,46) or z in (41,49)
   name='minecraft:glass' if edge or y==301 else 'minecraft:air'
   b.SetBlockNew(p,{'name':name,'aux':0},0,0,True,False)
_result=True''', True)
        camera((48.,310.,52.), (42.,305.5,44.))
        for style in ('rainbow','golden','starry'):
            game('''s.outline_style=%r
s.projection_active=True
s.projection_outline=True
s.bridge.projection_outline.replace((40,303,42),(4,5,4))
s.bridge.follow_projection()
_result=[s.bridge.projection_outline.entity,len(s.bridge.projection_outline.effects.layers)]''' % style)
            time.sleep(1.3)
            results[style] = raw('targeted_'+style, require_foreground=False)
        game('''s.outline_style='golden'
s.bridge.projection_outline.sync()
_result=True''')
        game('''b=api.GetEngineCompFactory().CreateBlockInfo(api.GetLevelId())
for p in api._targeted_wall:
 b.SetBlockNew(p,{'name':'minecraft:oak_leaves','aux':0},0,0,True,False)
for x in range(39,46):
 for z in range(42,49):
  b.SetBlockNew((x,302,z),{'name':'minecraft:water','aux':0},0,0,True,False)
_result=True''', True)
        for style in ('rainbow','golden','starry'):
            game('s.outline_style=%r\ns.bridge.projection_outline.sync()\ns.bridge.follow_projection()\n_result=True' % style)
            time.sleep(.7)
            results[style+'_background'] = raw('targeted_'+style+'_background', require_foreground=False)
        game('''b=api.GetEngineCompFactory().CreateBlockInfo(api.GetLevelId())
# Remove water sources before the basin's walls/floor.
for x in range(39,46):
 for z in range(42,49):b.SetBlockNew((x,302,z),{'name':'minecraft:air','aux':0},0,0,True,False)
for p,value in api._targeted_glass.items():
 b.SetBlockNew(p,value,0,0,True,False)
api._targeted_glass={}
_result=True''',True)
        game('''s.bridge.projection_outline.clear()
s.projection_active=False
s.bridge.world_tool_point({'index':0,'pos':(42,307,44),'face':1})
s.bridge.follow_projection()
_result=[s.bridge.survey_effects.points[0]['face'],
         s.bridge.survey_effects.points[0]['id']]''')
        time.sleep(.18)
        results['click'] = raw('targeted_click', require_foreground=False)
        time.sleep(1.1)
        results['settled'] = raw('targeted_settled', require_foreground=False)
        results['face'] = game('_result=s.bridge.survey_effects.points[0]["face"]')
        assert results['face'] == 3
    finally:
        game('''s.bridge.projection_outline.clear()
s.projection_active=False
s.bridge.corners=[None,None]
s.bridge.corner_faces=[None,None]
s.bridge.draw_bounds()
s.outline_style,s.projection_outline,s.bridge.corners,s.bridge.corner_faces=api._targeted_client
s.bridge.draw_bounds()
cam=s.bridge.factory.CreateCamera(s.bridge.level)
cam.ResetCameraPos()
cam.UnDepartCamera()
_result=True''')
        game('''f=api.GetEngineCompFactory()
b=f.CreateBlockInfo(api.GetLevelId())
if getattr(api,'_targeted_glass',{}):
 for x in range(39,46):
  for z in range(42,49):b.SetBlockNew((x,302,z),{'name':'minecraft:air','aux':0},0,0,True,False)
for p,value in getattr(api,'_targeted_glass',{}).items():
 b.SetBlockNew(p,value,0,0,True,False)
api._targeted_glass={}
f.CreatePos(player).SetFootPos(%r)
f.CreateFly(player).ChangePlayerFlyState(%r)
f.CreateTime(api.GetLevelId()).SetTime(%r)
_result=True''' % (tuple(saved[0]),saved[1],saved[2]),True)
    return results


if __name__ == '__main__':
    print(json.dumps(main(),ensure_ascii=False,indent=2))
