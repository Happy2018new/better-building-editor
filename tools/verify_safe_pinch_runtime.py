"""Check safe bounds and two-contact zoom in an isolated game instance."""
import json
import time
from verify_world_tools import game, snapshot


def main():
    original = game('''from modern_projection.pyreact import host, navigator
probe=host._SAFE_AREA_PROBE[0]
screen_control=probe.GetBaseUIControl(host._SCREEN_CONTROL_PATH)
safe_control=probe.GetBaseUIControl(host._SAFE_AREA_CONTROL_PATH)
g=s.bridge.factory.CreateGame(s.bridge.level)
_result={'safe':host.get_safe_area_size(),
         'insets':host.get_safe_area_insets().to_tuple() if host.get_safe_area_insets() else None,
         'screen':g.GetScreenSize(),
         'probe_screen':(screen_control.GetGlobalPosition(),screen_control.GetSize()),
         'probe_safe':(safe_control.GetGlobalPosition(),safe_control.GetSize()),
         'open':navigator.contains('modern_projection_workspace'),
         'pose':(s.camera_yaw,s.camera_pitch,s.zoom),'pan':s.camera_pan}''')
    assert not original['open'], 'Run with the workspace closed'
    try:
        game('''from modern_projection.pyreact import host
host._SAFE_AREA_PROBE[0]._next_measure=host.time.time()+30.
host._publish_safe_area((1.,1.),host.SafeAreaInsets(13.,24.,27.,48.))
owner.open_workspace()
_result=True''')
        time.sleep(1.5)
        result = game('''from modern_projection.pyreact import host
h=api.GetTopScreen()
def find_safe(f):
 if getattr(f.comp_type,'__name__',None)=='SafeArea':return f
 for child in f.child_fibers:
  result=find_safe(child)
  if result is not None:return result
 return None
safe=find_safe(h._root_fiber)
assert safe is not None
panel=safe.child_fibers[0].child_fibers[0]
control=h.GetBaseUIControl(panel.native_path)
screen=s.bridge.factory.CreateGame(s.bridge.level).GetScreenSize()
insets=host.get_safe_area_insets()
expected=host._safe_content_size(screen,insets)
rect=(control.GetGlobalPosition(),control.GetSize())
t=next(t for t in h._projection_pointer_surfaces if t.props.get('onPinch'))
c=h.GetBaseUIControl(t.slot['fiber'].native_path)
x,y=c.GetGlobalPosition();w,height=c.GetSize()
cx,cy=x+w*.5,y+height*.5;span=min(w,height)*.12
before=(s.zoom,len(s.editor.document.blocks))
for identity,dx in ((100,-span),(101,span)):
 t.native_touch({'TouchId':identity,'TouchEvent':1,'TouchPosX':cx+dx,'TouchPosY':cy})
t.native_touch({'TouchId':100,'TouchEvent':2,'TouchPosX':cx-span*2.,'TouchPosY':cy})
t.native_touch({'TouchId':101,'TouchEvent':2,'TouchPosX':cx+span*2.,'TouchPosY':cy})
held=t.pinching
for identity in (100,101):t.native_touch({'TouchId':identity,'TouchEvent':0})
_result={'screen':screen,'probe':host.get_safe_area_size(),'rect':rect,'expected':expected,
         'insets':insets.to_tuple(),'zoom_ratio':s.zoom/before[0],
         'held':held,'released':not t.pressed,'same_blocks':before[1]==len(s.editor.document.blocks)}''')
        position, size = result['rect']
        left, top = result['insets'][3], result['insets'][0]
        assert result['probe'] == [1., 1.], result
        assert abs(position[0]-left) < .1 and abs(position[1]-top) < .1, result
        assert all(abs(size[i]-result['expected'][i]) < .1 for i in range(2)), result
        assert abs(result['zoom_ratio']-2.) < .001, result
        assert result['held'] and result['released'] and result['same_blocks'], result
        result['original'] = original
        result['screenshot'] = snapshot('safe_pinch_runtime')
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        game('''from modern_projection.pyreact import host, navigator
if navigator.contains('modern_projection_workspace'):navigator.pop()
if %r is not None:
 host._publish_safe_area(%r,host.SafeAreaInsets(*%r))
host._SAFE_AREA_PROBE[0]._next_measure=0.
s.camera_view(yaw=%r,pitch=%r,zoom=%r)
s.camera_pan=%r
_result=True''' % (original['safe'], original['safe'], original['insets'],
                    original['pose'][0], original['pose'][1], original['pose'][2],
                    tuple(original['pan'])))


if __name__ == '__main__':
    main()
