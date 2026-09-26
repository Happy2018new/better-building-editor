"""Bound MCDK regression for recipes, right-clicks, touch HUD and capture.

Use only an isolated development world. Temporarily equips tools, while local
library persistence is replaced with memory so the user's library is untouched.
"""
import base64
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from mcdk import Client, return_value


def call(name, args):
    with Client() as client:
        return client.call(name, args)


def game(code, server=False):
    side = 'server' if server else 'client'
    source = ('from __future__ import unicode_literals\n'
              'import mod.%s.extra%sApi as api\n' % (side, side.title()) +
              'owner=api.GetSystem("ModernProjection", "ModernProjection%sSystem")\n' % side.title() +
              ('player=api.GetPlayerList()[0]\n' if server else 's=owner.session\n') + code)
    return return_value(call('execute_code', {'code':source.encode('ascii','backslashreplace').decode('ascii'),
                                             'is_client':not server, 'direct_return':True}))


def input_step(op, **args):
    result = call('mc_input', {'op':op, 'args':args})
    value = result.get('structuredContent')
    if value is None:
        for block in result.get('content', []):
            if block.get('type') == 'text':
                try:
                    value = json.loads(block['text'])
                except ValueError:
                    continue
    assert value and value.get('ok'), result
    return value


def equip(name):
    return game('''factory=api.GetEngineCompFactory()
item=factory.CreateItem(player)
name=%r.encode('utf8')
item.SpawnItemToPlayerCarried({'itemName':name,'count':1,'auxValue':0},player)
carried=item.GetPlayerItem(api.GetMinecraftEnum().ItemPosType.CARRIED,0)
_result=bool(carried and carried.get('newItemName',carried.get('itemName'))==name)''' % name, server=True)


def state():
    return game('''from modern_projection.pyreact import navigator
_result={'open':navigator.contains('modern_projection_workspace'),
    'corners':s.bridge.corners,'busy':s.busy,'io':s.io_job is not None,
    'library':[(e['id'],e['data']['name'],e['data']['size']) for e in s.library],
    'message':s.editor.message,'touch':api.IsTouchWithMouse(),
    'hud':owner.hud.shown,'draft_same':s.editor is getattr(api,'_tools_draft',s.editor)}''')


def wait_ready(seconds=30):
    deadline=time.time()+seconds
    while time.time()<deadline:
        value=state()
        if not value['busy'] and not value['io']:
            return value
        time.sleep(.2)
    raise AssertionError(value)


def hud_click(clear=False):
    position=game('''control=owner.hud.screen.%s
pos,size=control.GetGlobalPosition(),control.GetSize()
screen=s.bridge.factory.CreateGame(s.bridge.level).GetScreenSize()
_result=[(pos[i]+size[i]/2.)/screen[i] for i in range(2)]''' % ('clear_button' if clear else 'button'))
    input_step('/click', at=position)
    time.sleep(.5)


def snapshot(name):
    response=call('capture_game_window',{})
    for item in response.get('content',[]):
        if item.get('type')=='image':
            target=ROOT/'.runtime'/('tools_'+name+'.jpg')
            target.write_bytes(base64.b64decode(item['data']))
            return str(target)


def touch_world_gestures():
    game('owner.tool_reset()\napi.GetEngineCompFactory().CreateRot(api.GetLocalPlayerId()).SetRot((65.,0.))\n_result=True')
    time.sleep(.5)
    facing=game('_result=s.bridge.factory.CreateCamera(s.bridge.level).PickFacing()')
    input_step('/click',at=[.30,.42])
    time.sleep(.4)
    before=state()['corners']
    assert before[0] is not None and before[1] is None,before
    if facing and facing.get('type')=='Block':
        assert before[0]!=[facing[a] for a in ('x','y','z')],(before,facing)
    assert state()['hud'][0] and state()['hud'][1],state()['hud']
    hud_click(clear=True)
    assert state()['corners']==[None,None],state()['corners']
    assert game('_result=player not in owner.world_points and player not in owner.world_regions',True)
    assert game('_result=not s.bridge.survey_effects.active()')
    assert state()['hud'][0] and state()['hud'][1],'Tool buttons must remain visible after reset'
    input_step('/click',at=[.30,.42])
    time.sleep(.4)
    before=state()['corners']
    assert before[0] is not None and before[1] is None,before
    input_step('/drag',**{'from':[.55,.4],'to':[.65,.45],'segments':12})
    time.sleep(.4)
    assert state()['corners']==before,'Camera drag unexpectedly selected a corner'
    input_step('/click',at=[.70,.42])
    time.sleep(.4)
    assert None not in state()['corners'],state()
    assert state()['hud'][0],'Import HUD missing after second touch point'
    print('PASS F11 off-centre world tap selects; dragging does not select',flush=True)


def main():
    print('Initial',json.dumps(state(),ensure_ascii=False),flush=True)
    if '--help-input' in sys.argv:
        return
    original=game('''api._tools_saved=(s.library,s.library_serial,s.bridge.save_library,s.bridge.save_archive_page,
    s.world_import_document,s.world_import_origin,s.bridge.corners,s.page)
api._tools_draft=s.editor
api._tools_pages={}
def save_index(value):
    api._tools_index=value
    return True
def save_page(identity,part,value):
    api._tools_pages[(identity,part)]=value
    return True
s.library=[];s.library_serial=0
s.bridge.save_library=save_index;s.bridge.save_archive_page=save_page
_result={'touch':api.IsTouchWithMouse()}''')
    game('''api._tools_server_saved=[mapping.get(player) for mapping in
    (owner.world_points,owner.world_regions,owner.tool_last_use)]
_result=True''',server=True)
    try:
        game('owner.world_points.pop(player,None)\nowner.world_regions.pop(player,None)\nowner.tool_last_use.pop(player,None)\n_result=True',server=True)
        game('s.bridge.corners=[None,None]\ns.bridge.draw_bounds()\n_result=True')
        if state()['open']:
            game('from modern_projection.pyreact import navigator\nnavigator.pop()\n_result=True')
            time.sleep(.6)
        if state()['touch']:
            input_step('/key',keys='f11');time.sleep(.3)
        assert equip('modern_projection:terminal')
        time.sleep(.4)
        input_step('/click',button='right',at=[.5,.4])
        time.sleep(2)
        assert state()['open'],'Terminal right-click did not open'
        print('PASS PC terminal right-click',flush=True)
        game('from modern_projection.pyreact import navigator\nnavigator.pop()\n_result=True')
        time.sleep(.6)
        assert equip('modern_projection:survey_wand')
        game('api.GetEngineCompFactory().CreateRot(api.GetLocalPlayerId()).SetRot((70.,0.))\n_result=True')
        time.sleep(.5)
        print('Facing',game('_result=s.bridge.factory.CreateCamera(s.bridge.level).PickFacing()'),flush=True)
        input_step('/click',button='right',at=[.5,.4])
        time.sleep(.5)
        assert state()['corners'][0] is not None,'Native wand point missing'
        # Sneaking is a game-tick state; a same-packet modifier chord can
        # dispatch right-click before the player's pose has updated.
        input_step('/run',steps=[{'do':'key','keys':'shift','action':'down'},
            {'do':'wait','ms':250},{'do':'click','button':'right','at':[.5,.4]},
            {'do':'wait','ms':150},{'do':'key','keys':'shift','action':'up'}])
        time.sleep(.4)
        assert state()['corners']==[None,None],'Sneak right-click did not clear'
        assert game('_result=player not in owner.world_points and player not in owner.world_regions',True)
        input_step('/click',button='right',at=[.5,.4])
        time.sleep(.4)
        assert state()['corners'][0] is not None,'First point after clear missing'
        game('api.GetEngineCompFactory().CreateRot(api.GetLocalPlayerId()).SetRot((60.,90.))\n_result=True')
        time.sleep(.5)
        input_step('/click',button='right',at=[.5,.4])
        time.sleep(.5)
        assert None not in state()['corners'],'Second point missing'
        print('PASS PC two native world corners',json.dumps(state()['corners']),flush=True)
        assert state()['hud'][0],'PC import button missing'
        assert state()['hud'][1],'PC clear selection button missing'
        input_step('/click',button='left',at=[.5,.4])
        value=wait_ready()
        assert value['open'] and len(value['library'])==1 and value['draft_same'],value
        print('PASS PC left-click capture and draft protection',flush=True)
        game('from modern_projection.pyreact import navigator\nnavigator.pop()\n_result=True')
        time.sleep(.6)
        input_step('/key',keys='f11');time.sleep(.5)
        assert state()['touch'],'F11 touch simulation missing'
        touch_world_gestures()
        before=state()['corners']
        print('HUD',snapshot('wand_selection'),flush=True)
        hud_click()
        value=wait_ready()
        assert len(value['library'])==2 and value['draft_same'] and value['corners']==before,value
        print('PASS F11 HUD capture and draft protection',json.dumps(value,ensure_ascii=False),flush=True)
        game('from modern_projection.pyreact import navigator\nnavigator.pop()\n_result=True')
        time.sleep(.6)
        hud_click(clear=True)
        assert state()['corners']==[None,None],'Completed region did not clear'
        assert game('_result=player not in owner.world_points and player not in owner.world_regions',True)
        assert equip('modern_projection:terminal')
        time.sleep(.4)
        print('HUD',snapshot('terminal'),flush=True)
        hud_click()
        time.sleep(1.8)
        assert state()['open'],'F11 terminal HUD missing'
        print('PASS F11 terminal opens workspace',flush=True)
    finally:
        value=state()
        if value['busy']:
            game('s.bridge.cancel_world()\n_result=True')
        if value['busy'] or value['io']:
            wait_ready()
        game('''saved=api._tools_saved
s.library,s.library_serial,s.bridge.save_library,s.bridge.save_archive_page,s.world_import_document,s.world_import_origin,s.bridge.corners,s.page=saved
s.bridge.draw_bounds();s.emit()
_result=True''')
        game('''for mapping,value in zip((owner.world_points,owner.world_regions,owner.tool_last_use),api._tools_server_saved):
    mapping.pop(player,None)
    if value is not None: mapping[player]=value
_result=True''',server=True)
        if state()['touch']!=original['touch']:
            if state()['open']:
                game('from modern_projection.pyreact import navigator\nnavigator.pop()\n_result=True');time.sleep(.6)
            input_step('/key',keys='f11')


if __name__=='__main__':
    main()
