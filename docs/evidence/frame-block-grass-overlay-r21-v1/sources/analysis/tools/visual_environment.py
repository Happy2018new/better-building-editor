"""Reversible lighting fixture for pixel comparisons in owned test worlds."""
SETUP_DAYLIGHT = '''import json,sys
import mod.server.extraServerApi as api
assert not hasattr(sys,'_p0_visual_daylight'), 'Restore previous visual lighting fixture first'
factory=api.GetEngineCompFactory()
level=api.GetLevelId()
clock= factory.CreateTime(level)
game=factory.CreateGame(level)
saved={'time':clock.GetTime(),'daylight_cycle':game.GetGameRulesInfoServer()['cheat_info']['daylight_cycle']}
sys._p0_visual_daylight=saved
assert game.SetGameRulesInfoServer({'cheat_info':{'daylight_cycle':False}})
assert clock.SetTime((saved['time']//24000)*24000+6000)
_result=json.dumps({'saved':saved,'measured':clock.GetTime(),
 'daylight_cycle':game.GetGameRulesInfoServer()['cheat_info']['daylight_cycle']})
'''
RESTORE_DAYLIGHT = '''import json,sys
import mod.server.extraServerApi as api
saved=sys._p0_visual_daylight
factory=api.GetEngineCompFactory()
clock=factory.CreateTime(api.GetLevelId())
game=factory.CreateGame(api.GetLevelId())
results={'time':bool(clock.SetTime(saved['time'])),
 'daylight_cycle':bool(game.SetGameRulesInfoServer({'cheat_info':{'daylight_cycle':saved['daylight_cycle']}}))}
assert all(results.values()), results
del sys._p0_visual_daylight
_result=json.dumps(results)
'''
