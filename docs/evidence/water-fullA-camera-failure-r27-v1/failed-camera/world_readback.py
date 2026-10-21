"""Read-only server/player baseline and independent final restoration gate."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time

WORK = Path(__file__).resolve().parent

SERVER_CODE = '''import json,sys
import mod.server.extraServerApi as api
factory=api.GetEngineCompFactory()
level=api.GetLevelId()
player=api.GetPlayerList()[0]
weather=factory.CreateWeather(level)
_result=json.dumps({'player':player,'dimension':factory.CreateDimension(player).GetEntityDimensionId(),
 'foot':factory.CreatePos(player).GetFootPos(),
 'rules':factory.CreateGame(level).GetGameRulesInfoServer()['cheat_info'],
 'time':factory.CreateTime(level).GetTime(),'raining':weather.IsRaining(),'thunder':weather.IsThunder(),
 'remaining_markers':[name for name in ('_liquid_pose_world','_context_environment_saved') if hasattr(sys,name)]})
'''

CLIENT_CODE = '''import json,sys
import mod.client.extraClientApi as api
owner=api.GetSystem('ModernProjection','ModernProjectionClientSystem')
b=owner.bridge
cam=b.factory.CreateCamera(b.level)
_result=json.dumps({'rotation':cam.GetCameraRotation(),'pitch_lock':cam.IsModCameraLockPitch(),
 'yaw_lock':cam.IsModCameraLockYaw(),
 'remaining_markers':[name for name in ('_blueprint_visual_saved','_sign_visual_hud_saved',
 '_neighbor_visual_options_saved','_product_water_saved_profile','_product_water_timing',
 '_blueprint_qa_saved','_liquid_pose_client') if hasattr(sys,name)]})
'''


def readback(client, run):
    return {'server':run(client,SERVER_CODE,True),'client':run(client,CLIENT_CODE)}


def compare(actual, expected):
    before=expected['server'];after=actual['server']
    camera_before=expected['client'];camera_after=actual['client']
    checks={
        'server_markers_clear':not after['remaining_markers'],
        'client_markers_clear':not camera_after['remaining_markers'],
        'same_player_dimension':all(after[key]==before[key] for key in ('player','dimension')),
        'player_foot_restored':bool(after['foot'] and before['foot'] and
            max(abs(after['foot'][axis]-before['foot'][axis]) for axis in range(3))<.05),
        'environment_rules_restored':all(after['rules'][key]==before['rules'][key]
            for key in ('daylight_cycle','weather_cycle')),
        'weather_restored':all(after[key]==before[key] for key in ('raining','thunder')),
        'camera_locks_restored':all(camera_after[key]==camera_before[key] for key in ('pitch_lock','yaw_lock')),
        'camera_rotation_restored':all(abs(camera_after['rotation'][axis]-camera_before['rotation'][axis])<.0001
            for axis in range(len(camera_before['rotation']))),
    }
    return {'restored':all(checks.values()),'checks':checks,
            'time_readback_only':{'before':before['time'],'after':after['time'],
                'note':'Ordinary world time may advance after restoration; no exact-time gate is invented.'}}


def main():
    binding=json.loads((WORK/'final-source-binding-v1.json').read_bytes())
    launch=json.loads((WORK/'launch/launch.json').read_bytes())
    os.environ.update(MCDEV_SESSION_FILE=launch['session_file'],MCDEV_OWNER=binding['owner'],MCDEV_ALLOW_USER_FOREGROUND='0')
    sys.path.insert(0,str(Path(binding['project'])/'tools'))
    import probe_liquid_pose_channel as base
    output=WORK/'world-baseline-v1.json'
    assert not output.exists()
    with base.Client(timeout=20) as client:
        state=readback(client,base.run)
    assert not state['server']['remaining_markers'] and not state['client']['remaining_markers'],state
    with output.open('x',encoding='utf8') as stream:
        json.dump({'schema':1,'owner':binding['owner'],'at':time.time(),'state':state,
            'host_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'read_only':True},stream,indent=2)
    print(json.dumps({'baseline_recorded':True,'read_only':True}))


if __name__=='__main__':
    main()
