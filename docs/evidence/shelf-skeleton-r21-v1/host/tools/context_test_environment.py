"""Save and restore clear-noon settings in an owned disposable test world."""
import json
from verify_debug_blueprints import return_value

SETUP = '''import mod.server.extraServerApi as api
import json,sys
factory=api.GetEngineCompFactory()
level=api.GetLevelId()
clock=factory.CreateTime(level)
game=factory.CreateGame(level)
weather=factory.CreateWeather(level)
saved={'time':clock.GetTime(),'rules':game.GetGameRulesInfoServer()['cheat_info'],
 'raining':weather.IsRaining(),'thunder':weather.IsThunder()}
assert not hasattr(sys,'_context_environment_saved')
sys._context_environment_saved=saved
assert game.SetGameRulesInfoServer({'cheat_info':{'daylight_cycle':False,'weather_cycle':False}})
assert clock.SetTime((saved['time']//24000)*24000+6000)
assert weather.SetRaining(0.,200000) and weather.SetThunder(0.,200000)
_result=json.dumps(saved)
'''

RESTORE = '''import mod.server.extraServerApi as api
import json,sys
saved=sys._context_environment_saved
factory=api.GetEngineCompFactory()
level=api.GetLevelId()
clock=factory.CreateTime(level)
game=factory.CreateGame(level)
weather=factory.CreateWeather(level)
assert clock.SetTime(saved['time'])
assert game.SetGameRulesInfoServer({'cheat_info':dict((k,saved['rules'][k]) for k in ('daylight_cycle','weather_cycle'))})
assert weather.SetRaining(float(saved['raining']),200000) and weather.SetThunder(float(saved['thunder']),200000)
del sys._context_environment_saved
_result=True
'''


def run(client, code):
    response=client.call('execute_code',{'code':code,'is_client':False,'direct_return':True})
    if response.get('isError'):
        raise RuntimeError(response)
    value=return_value(response)
    return json.loads(value) if isinstance(value,str) else value
