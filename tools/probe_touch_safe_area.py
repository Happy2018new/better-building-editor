"""Compare native safe-area measurements before and after F11 touch mode."""
import json
import time
from native_input_mode import set_touch, state
from verify_world_tools import game, snapshot


def metrics():
    return game('''from HelloScript.pyreact import host
probe=host._SAFE_AREA_PROBE[0]
screen=probe.GetBaseUIControl(host._SCREEN_CONTROL_PATH)
safe=probe.GetBaseUIControl(host._SAFE_AREA_CONTROL_PATH)
h=api.GetTopScreen()
root=h.GetBaseUIControl('/root')
def find_safe(f):
 if getattr(f.comp_type,'__name__',None)=='SafeArea':return f
 for child in f.child_fibers:
  result=find_safe(child)
  if result is not None:return result
 return None
safe_fiber=find_safe(h._root_fiber)
content=h.GetBaseUIControl(safe_fiber.child_fibers[0].child_fibers[0].native_path)
g=s.bridge.factory.CreateGame(s.bridge.level)
insets=host.get_safe_area_insets()
_result={'touch':api.IsTouchWithMouse(), 'screen':g.GetScreenSize(),
         'root':(root.GetGlobalPosition(),root.GetSize()),
         'content':(content.GetGlobalPosition(),content.GetSize()),
         'probe_screen':(screen.GetGlobalPosition(),screen.GetSize()),
         'probe_safe':(safe.GetGlobalPosition(),safe.GetSize()),
         'safe_size':host.get_safe_area_size(),
         'insets':insets.to_tuple() if insets else None}''')


def main():
    original = state()['simulated']
    game('owner.open_workspace()\n_result=True')
    time.sleep(1.)
    try:
        before = metrics()
        assert before['insets'] == [0., 0., 0., 0.], before
        assert before['content'] == before['root'], before
        screenshot = snapshot('safe_area_pc_after_fix')
        set_touch(True)
        time.sleep(.8)
        after = metrics()
        assert after['insets'] == [0., 0., 0., 0.], after
        assert after['content'] == after['root'], after
        print(json.dumps({'before': before, 'after': after,
                          'screenshot': screenshot}, ensure_ascii=False, indent=2))
    finally:
        set_touch(original)
        game('''from HelloScript.pyreact import navigator
if navigator.contains('modern_projection_workspace'):navigator.pop()
_result=True''')


if __name__ == '__main__':
    main()
