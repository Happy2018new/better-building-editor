"""F11 single-touch plus injected two-contact/native-Back routing; not phone QA."""
import json
import time
from pathlib import Path
from verify_world_tools import game,input_step


def main():
    original=game('''from modern_projection.pyreact import navigator
_result={'touch':api.IsTouchWithMouse(),'mode':s.direct_mode,
         'pose':(s.camera_yaw,s.camera_pitch,s.zoom),'pan':s.camera_pan}
if navigator.contains('modern_projection_workspace'):navigator.pop()''')
    report={}
    try:
        time.sleep(.4)
        if not original['touch']:input_step('/key',keys='f11')
        time.sleep(.3)
        assert game('_result=api.IsTouchWithMouse()')
        game('s.choose_mode("browse")\nowner.open_workspace()\n_result=True')
        time.sleep(1.5)
        coordinates=game('''h=api.GetTopScreen()
t=next(t for t in h._projection_pointer_surfaces if t.props.get('onPinch'))
c=h.GetBaseUIControl(t.slot['fiber'].native_path)
x,y=c.GetGlobalPosition();w,hgt=c.GetSize()
sw,sh=s.bridge.factory.CreateGame(s.bridge.level).GetScreenSize()
api._mobile_review_yaw=s.camera_yaw
h._projection_trace_touch=True
_result=[[(x+w*.4)/sw,(y+hgt*.5)/sh],[(x+w*.6)/sw,(y+hgt*.55)/sh]]''')
        input_step('/drag',**{'from':coordinates[0],'to':coordinates[1],'segments':12})
        time.sleep(.3)
        report['f11_single_drag']=game('_result=s.camera_yaw!=api._mobile_review_yaw')
        assert report['f11_single_drag']
        report['injected_pinch']=game('''h=api.GetTopScreen()
t=next(t for t in h._projection_pointer_surfaces if t.props.get('onPinch'))
c=h.GetBaseUIControl(t.slot['fiber'].native_path)
x,y=c.GetGlobalPosition();w,hgt=c.GetSize()
cx,cy=x+w*.5,y+hgt*.5;span=min(w,hgt)*.12
before=(s.zoom,len(s.editor.document.blocks))
for identity,dx in ((100,-span),(101,span)):
 t.native_touch({'TouchId':identity,'TouchEvent':1,'TouchPosX':cx+dx,'TouchPosY':cy})
for identity,dx in ((100,-span*2.),(101,span*2.)):
 t.native_touch({'TouchId':identity,'TouchEvent':4,'TouchPosX':cx+dx,'TouchPosY':cy})
held=t.pinching
t.native_touch({'TouchId':101,'TouchEvent':6,'TouchPosX':cx+span*2.,'TouchPosY':cy})
outside=t.pinching
for identity in (100,101):t.native_touch({'TouchId':identity,'TouchEvent':0})
_result={'ratio':s.zoom/before[0],'held':held,'outside':outside,'released':not t.pressed,
         'same_blocks':before[1]==len(s.editor.document.blocks),
         'native_trace':getattr(h,'_projection_touch_trace',[])}''')
        p=report['injected_pinch']
        assert abs(p['ratio']-2.)<.001 and all(p[k] for k in ('held','outside','released','same_blocks')),p
        game('s.set("pending_confirm",(u"Back route regression",lambda:None))\n_result=True')
        time.sleep(.5)
        report['android_callback_deduplicated']=game('''from modern_projection.pyreact import host,navigator
h=api.GetTopScreen()
host._RUNTIME_EVENT_HANDLER.on_android_back({})
h._native_back({})
_result=s.pending_confirm is None and navigator.contains('modern_projection_workspace')''')
        assert report['android_callback_deduplicated']
    finally:
        game('''from modern_projection.pyreact import navigator
if navigator.contains('modern_projection_workspace'):navigator.pop()
s.pending_confirm=None
s.choose_mode(%r)
s.camera_view(yaw=%r,pitch=%r,zoom=%r)
s.camera_pan=%r
_result=True'''%(original['mode'],original['pose'][0],original['pose'][1],original['pose'][2],tuple(original['pan'])))
        time.sleep(.4)
        if game('_result=api.IsTouchWithMouse()')!=original['touch']:input_step('/key',keys='f11')
    path=Path(__file__).resolve().parents[1]/'.runtime/mobile_routes_report.json'
    path.write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
