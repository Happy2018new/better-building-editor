"""Native outline acceptance in an isolated MCDK development world.

Requires the standard MCDEV_SESSION_FILE / MCDEV_OWNER instance binding.
Uses actual mouse/F11 events for UI; direct SDK calls only prepare fixtures.
"""
import json
import sys
import time
from pathlib import Path

from PIL import Image
from verify_world_tools import game, input_step, call
from mcdk import load_session

OUT = Path(__file__).resolve().parents[1] / '.runtime' / 'outline_acceptance'


def raw(name, require_foreground=True):
    sys.path.insert(0, str(Path(__file__).resolve().parent / 'pyreact_legacy'))
    import capture_screen as capture
    OUT.mkdir(parents=True, exist_ok=True)
    binding = load_session(live=True)
    capture.user32.SetProcessDPIAware()
    window = capture._find_game_window(capture._list_windows(), pid=binding['game_pid'])
    assert window
    if require_foreground:
        assert capture.user32.GetForegroundWindow() == window['hwnd'], 'Game is not foreground'
    else:
        overview=call('jsonui_debugger',{'cmd':'/overview --screen=top'})
        data=json.loads(next(c['text'] for c in overview['content'] if c.get('type')=='text'))['data']
        assert data['top_screen_fullname']=='hud.hud_screen', data['top_screen_fullname']
    unused_x, unused_y, width, height = capture._window_rect(window['hwnd'])
    path = OUT / (name + '.png')
    for attempt in range(5):
        capture._capture_window_windows(window['hwnd'], width, height, False, str(path))
        with Image.open(path) as frame:
            if sum(hi-lo for lo,hi in frame.convert('RGB').getextrema()) > 40:
                return str(path)
        time.sleep(.15)
    raise AssertionError('Blank native screenshot: ' + str(path))


def camera(position, target):
    return game('''cam=s.bridge.factory.CreateCamera(s.bridge.level)
pos=%r;target=%r
rot=api.GetRotFromDir(tuple(target[i]-pos[i] for i in range(3)))
cam.DepartCamera();cam.SetCameraPos(pos);cam.SetCameraRotation((rot[0],rot[1]+180.,0.))
s.bridge.follow_projection()
_result=True''' % (tuple(position), tuple(target)))


def native_click(node, fraction=.5):
    import verify_ui as ui
    control = ui.call('native_control', node['id'])['result']
    screen = game('_result=s.bridge.factory.CreateGame(s.bridge.level).GetScreenSize()')
    point = [(control['global'][i] + control['size'][i]*(fraction if i==0 else .5))/screen[i] for i in range(2)]
    if point[0] > .78 and not .44 < point[1] < .82:
        scroll = ui.nodes('VisibleScroll')[-1]
        current = ui.call('get_scroll', scroll['id'])['result']
        position = current['position'] + (point[1]-.60)*screen[1]
        ui.call('scroll', scroll['id'], max(0.,position))
        time.sleep(.2)
        control = ui.call('native_control', node['id'])['result']
        point = [(control['global'][i]+control['size'][i]*(fraction if i==0 else .5))/screen[i] for i in range(2)]
    assert all(0. <= v <= 1. for v in point), (point, control)
    input_step('/click', at=point)
    time.sleep(.35)


def ui_settings():
    import verify_ui as ui
    from native_input_mode import set_touch
    results = {}
    for touch in (False, True):
        set_touch(touch)
        if game('_result=s.page') != 'projection':
            action = next(n for n in ui.nodes('Button') if ui.labels(n) == ['\u6295\u5f71'])
            native_click(action)
        # The app retains its custom native scroll, including its current offset.
        for style, label in [('golden','\u91d1\u8272'), ('starry','\u661f\u7a7a'), ('rainbow','\u70ab\u5f69')]:
            panel = ui.nodes('ProjectionOutlineSettings')[0]
            segment = next(n for n in ui.nodes('Button', panel) if label in ui.labels(n))
            native_click(segment)
            assert game('_result=s.outline_style') == style
            panel = ui.nodes('ProjectionOutlineSettings')[0]
            ranges = ui.nodes('Range', panel)
            assert len(ranges) == (3 if style=='rainbow' else 5)
            # Bottom control is brightness for rainbow, density for luminous styles.
            native_click(ui.nodes('Slider', ranges[-1])[0], .72)
            parameter = 'brightness' if style=='rainbow' else 'density'
            value = game('_result=s.outline_options[%r][%r]' % (style, parameter))
            assert value > 1., value
            results[('touch_' if touch else 'pc_')+style] = {'parameter':parameter,'value':value,'screenshot':raw(('touch_' if touch else 'pc_')+style+'_settings')}
            print('PASS native %s %s controls' % ('F11' if touch else 'PC', style), flush=True)
        # Restore defaults before visual comparison.
        game('from modern_projection.projection.outline_settings import defaults\ns.outline_options=defaults()\ns.set("outline_style","rainbow")\ns.save_preferences()\ns.emit("outline_options")\n_result=True')
    set_touch(False)
    (OUT/'ui.json').write_text(json.dumps(results, indent=2), encoding='utf8')
    return results


def weather(ticks=6000, mode='clear'):
    assert mode in ('clear', 'rain', 'thunder')
    return game('''f=api.GetEngineCompFactory()
f.CreateTime(api.GetLevelId()).SetTimeOfDay(%d)
w=f.CreateWeather(api.GetLevelId())
a=w.SetRaining(%r,200000);b=w.SetThunder(%r,200000)
_result=a and b''' % (ticks, float(mode!='clear'),float(mode=='thunder')), True)


def survey(origin=(0,-58,2), size=(4,5,4), points=True):
    corners = [tuple(origin), tuple(origin[i]+size[i]-1 for i in range(3))]
    return game('''s.bridge.corners=%r
s.bridge.draw_bounds()
if not %r:s.bridge.survey_effects.sync_points([None,None])
s.bridge.follow_projection()
_result=[r['id'] for r in s.bridge.survey_effects._records()]''' % (corners, points))


def panel(block):
    """A bounded screen of terrain crosses half the effect at close range."""
    return game('''f=api.GetEngineCompFactory();b=f.CreateBlockInfo(api.GetLevelId())
if not hasattr(api,'_outline86_blocks'):api._outline86_blocks={}
count=0
for x in range(-4,10):
 for y in range(-60,-47):
  pos=(x,y,7)
  if pos not in api._outline86_blocks:api._outline86_blocks[pos]=b.GetBlockNew(pos,0)
  count+=bool(b.SetBlockNew(pos,{'name':%r,'aux':0},0,0,True,False))
_result=count''' % ('minecraft:'+block), True)


def visual_matrix():
    results = {}
    game('''from modern_projection.pyreact import navigator
if navigator.contains('modern_projection_workspace'):navigator.pop()
s.bridge.stop_projection()
_result=True''')
    game('''f=api.GetEngineCompFactory()
api._outline86_player=(f.CreatePos(player).GetFootPos(),f.CreateFly(player).IsPlayerFlying())
f.CreateFly(player).ChangePlayerFlyState(True)
f.CreatePos(player).SetFootPos((0.,-55.,10.))
_result=True''', True)
    camera((8.,-51.,12.),(2.,-55.5,4.))
    try:
        ids = survey()
        time.sleep(1.4)
        for label, ticks, mode in [('day',6000,'clear'),('night',18000,'clear'),('rain',6000,'rain'),('thunder',18000,'thunder')]:
            assert weather(ticks,mode)
            time.sleep(2.5)
            results[label] = raw('survey_'+label)
            assert ids == game("_result=[r['id'] for r in s.bridge.survey_effects._records()]")
            print('PASS survey weather '+label, flush=True)
        weather()
        time.sleep(2.)
        for name in ('glass','leaves','quartz_block','stone','air'):
            assert panel(name) == 182
            time.sleep(1.)
            results[name] = raw('survey_background_'+name)
            print('CAPTURE background '+name, flush=True)
        # See-through backgrounds behind the whole outline, viewed from the other side.
        for name in ('glass','leaves'):
            panel(name)
            camera((-5.,-52.,-5.),(2.,-55.5,4.))
            time.sleep(.7)
            results[name+'_behind'] = raw('survey_'+name+'_behind')
        panel('air')
        for name,origin,size,pos,target in [
            ('single',(0,-58,2),(1,1,1),(2.,-56.,6.),(.5,-57.5,2.5)),
            ('thin',(0,-58,2),(1,12,1),(7.,-49.,12.),(.5,-52.,2.5)),
            ('maximum',(-32,-59,-32),(64,128,64),(90.,56.,95.),(0.,5.,0.)),
            ('inside',(-32,-59,-32),(64,128,64),(0.,5.,0.),(32.,25.,32.)),
            ('near_edge',(-32,-59,-32),(64,128,64),(31.9,5.,31.9),(32.,20.,32.)),
            ('horizon',(0,-58,2),(4,5,4),(8.,-58.,12.),(2.,-58.,4.)),
        ]:
            game('api.GetEngineCompFactory().CreatePos(player).SetFootPos(%r)\n_result=True' % (pos,), True)
            camera(pos,target)
            survey(origin,size)
            time.sleep(1.3)
            results[name] = raw('survey_'+name)
            print('CAPTURE bounds '+name, flush=True)
        game('''s.bridge.corners=[None,None];s.bridge.draw_bounds()
from modern_projection.projection.model import Document,Editor
blocks={}
for x in range(6):
 for z in range(6):blocks[(x,0,z)]=('minecraft:quartz_block',0)
for y in range(1,5):
 for x,z in [(0,0),(0,5),(5,0),(5,5)]:blocks[(x,y,z)]=('minecraft:quartz_block',0)
s.editor=Editor(Document((6,6,6),blocks));s.origin=(0,-58,0)
s.projection_outline=True;s.outline_style='rainbow'
s.bridge.project()
_result=True''')
        game('api.GetEngineCompFactory().CreatePos(player).SetFootPos((0.,-55.,10.))\n_result=True', True)
        camera((10.,-49.,14.),(3.,-55.,3.))
        for unused in range(60):
            if game('_result=s.projection_active'):break
            time.sleep(.25)
        assert game('_result=s.projection_active')
        mesh = game('_result=s.bridge.entity')
        for style in ('rainbow','golden','starry'):
            game('s.set("outline_style",%r)\n_result=True' % style)
            time.sleep(1.4)
            for label,ticks in [('day',6000),('night',18000)]:
                weather(ticks)
                time.sleep(.5)
                results[style+'_'+label] = raw('projection_'+style+'_'+label)
                assert mesh == game('_result=s.bridge.entity')
            print('PASS projection '+style+' preserves building actor', flush=True)
        results['server_effect_actors'] = game("_result=[e for e in api.GetEngineActor().values() if e.get('identifier','').startswith('modern_projection:survey_') or e.get('identifier','')=='modern_projection:outline']",True)
        assert results['server_effect_actors'] == []
    finally:
        game('''b=api.GetEngineCompFactory().CreateBlockInfo(api.GetLevelId())
for pos,value in getattr(api,'_outline86_blocks',{}).items():b.SetBlockNew(pos,value,0,0,True,False)
api._outline86_blocks={}
f=api.GetEngineCompFactory()
f.CreatePos(player).SetFootPos(api._outline86_player[0])
f.CreateFly(player).ChangePlayerFlyState(api._outline86_player[1])
_result=True''', True)
        weather()
        game('''s.bridge.stop_projection();s.bridge.corners=[None,None];s.bridge.draw_bounds()
s.set('outline_style','rainbow')
cam=s.bridge.factory.CreateCamera(s.bridge.level);cam.ResetCameraPos();cam.UnDepartCamera()
_result=True''')
        OUT.mkdir(parents=True,exist_ok=True)
        (OUT/'visuals.json').write_text(json.dumps(results,indent=2),encoding='utf8')
    return results


if __name__ == '__main__':
    print(json.dumps(ui_settings(), indent=2))
