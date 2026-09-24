"""Persistent gold markers and all projection styles in a bound test world.

Uses clear air above terrain, saves/restores temporary SDK fixtures, and never
writes building libraries. Real PC/F11 controls use verify_outline_styles.
"""
import json
import time
from verify_world_tools import game
from verify_outline_styles import camera, survey, weather, raw, OUT


def main(persistence_seconds=125):
    saved = game('''f=api.GetEngineCompFactory()
_result=[f.CreatePos(player).GetFootPos(),f.CreateFly(player).IsPlayerFlying(),
f.CreateTime(api.GetLevelId()).GetTime()]''', True)
    previous = game('''api._gold_saved=(s.editor,s.origin,s.outline_style,s.outline_options,s.projection_outline)
_result=s.bridge.corners''')
    results = {}

    def view(pos, target):
        game('api.GetEngineCompFactory().CreatePos(player).SetFootPos(%r)\n_result=True' % (pos,), True)
        camera(pos, target)

    def shot(label):
        results[label] = raw('final_'+label, require_foreground=False)
        print('CAPTURE '+label, flush=True)

    def wall(block):
        return game('''b=api.GetEngineCompFactory().CreateBlockInfo(api.GetLevelId())
if not hasattr(api,'_gold_blocks'):api._gold_blocks={}
for x in range(-4,10):
 for y in range(301,314):
  p=(x,y,8)
  if p not in api._gold_blocks:api._gold_blocks[p]=b.GetBlockNew(p,0)
  b.SetBlockNew(p,{'name':%r,'aux':0},0,0,True,False)
_result=True''' % ('minecraft:'+block), True)

    try:
        game('from HelloScript.pyreact import navigator\nif navigator.contains("modern_projection_workspace"):navigator.pop()\ns.bridge.stop_projection()\n_result=True')
        game('api.GetEngineCompFactory().CreateFly(player).ChangePlayerFlyState(True)\n_result=True', True)
        view((8.,310.,12.),(2.,305.5,4.))
        ids=survey((0,303,2),(4,5,4))
        started=time.time()
        for label,ticks,mode in [('day',6000,'clear'),('night',18000,'clear'),('rain',6000,'rain'),('thunder',18000,'thunder')]:
            weather(ticks,mode);time.sleep(5.)
            shot(label)
        weather()
        for block in ('glass','leaves','quartz_block','air'):
            wall(block);time.sleep(1.)
            shot('foreground_'+block)
        for block in ('glass','leaves'):
            wall(block);view((-5.,310.,-5.),(2.,305.5,4.));time.sleep(.7)
            shot('background_'+block)
        wall('air')
        view((8.,310.,12.),(2.,305.5,4.))
        while time.time()-started<persistence_seconds:
            time.sleep(min(5.,persistence_seconds-(time.time()-started)))
        assert ids==game("_result=[r['id'] for r in s.bridge.survey_effects._records()]")
        results['persistent_seconds']=round(time.time()-started,2)
        shot('permanent')
        game('s.bridge.survey_effects.pulse_point(0)\n_result=True')
        time.sleep(.18);shot('point_entrance')
        time.sleep(1.4);shot('point_settled')
        for label,origin,size,pos,target in [
            ('single',(0,303,2),(1,1,1),(2.,305.,6.),(.5,303.5,2.5)),
            ('thin',(0,303,2),(1,12,1),(7.,312.,12.),(.5,309.,2.5)),
            ('maximum',(-32,303,-32),(64,128,64),(90.,418.,95.),(0.,367.,0.)),
            ('inside',(-32,303,-32),(64,128,64),(0.,367.,0.),(32.,387.,32.)),
            ('near_edge',(-32,303,-32),(64,128,64),(31.9,367.,31.9),(32.,382.,32.)),
            ('horizon',(0,303,2),(4,5,4),(8.,304.,12.),(2.,304.,4.)),
        ]:
            view(pos,target);survey(origin,size);time.sleep(1.4);shot(label)
        game('''s.bridge.corners=[None,None];s.bridge.draw_bounds()
from HelloScript.projection.model import Document,Editor
from HelloScript.projection.outline_settings import defaults
blocks={}
for x in range(6):
 for z in range(6):blocks[(x,0,z)]=('minecraft:quartz_block',0)
for y in range(1,5):
 for x,z in [(0,0),(0,5),(5,0),(5,5)]:blocks[(x,y,z)]=('minecraft:quartz_block',0)
s.editor=Editor(Document((6,6,6),blocks));s.origin=(0,303,0)
s.outline_options=defaults();s.projection_outline=True;s.outline_style='rainbow'
_result=True''')
        view((10.,313.,14.),(3.,306.,3.))
        game('s.bridge.project()\n_result=True')
        time.sleep(3.)
        for unused in range(60):
            if game('_result=s.projection_active'):break
            time.sleep(.25)
        assert game('_result=s.projection_active')
        mesh=game('_result=s.bridge.entity')
        for style in ('rainbow','golden','starry'):
            game('s.outline_style=%r\ns.bridge.projection_outline.sync()\n_result=True'%style)
            time.sleep(1.4)
            for label,ticks in [('day',6000),('night',18000)]:
                weather(ticks);time.sleep(.7);shot(style+'_'+label)
            assert mesh==game('_result=s.bridge.entity')
        results['server_effect_actors']=game("_result=[e for e in api.GetEngineActor().values() if e.get('identifier','').startswith('modern_projection:survey_') or e.get('identifier','')=='modern_projection:outline']",True)
        assert not results['server_effect_actors']
    finally:
        game('''s.bridge.stop_projection()
s.editor,s.origin,s.outline_style,s.outline_options,s.projection_outline=api._gold_saved
s.bridge.corners=%r;s.bridge.draw_bounds()
cam=s.bridge.factory.CreateCamera(s.bridge.level);cam.ResetCameraPos();cam.UnDepartCamera()
_result=True'''%previous)
        game('''f=api.GetEngineCompFactory();b=f.CreateBlockInfo(api.GetLevelId())
for pos,block in getattr(api,'_gold_blocks',{}).items():b.SetBlockNew(pos,block,0,0,True,False)
api._gold_blocks={}
f.CreatePos(player).SetFootPos(%r);f.CreateFly(player).ChangePlayerFlyState(%r)
f.CreateTime(api.GetLevelId()).SetTime(%r)
_result=True'''%(tuple(saved[0]),saved[1],saved[2]),True)
        weather()
        OUT.mkdir(parents=True,exist_ok=True)
        (OUT/'final_visuals.json').write_text(json.dumps(results,indent=2),encoding='utf8')
    return results


if __name__=='__main__': print(json.dumps(main(),indent=2))
