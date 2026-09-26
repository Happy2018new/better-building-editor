"""Capture one stationary aura crystal in an isolated ModPC world."""
import json
import sys
import time
from pathlib import Path

from verify_world_tools import equip, game
from verify_survey_visuals import camera
from mcdk import load_session
from pyreact_legacy import capture_screen as capture


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else 'aura_stars'
    binding = load_session(live=True)
    out = Path(__file__).resolve().parents[1] / '.runtime' / (label + '.png')
    old = game('''from modern_projection.pyreact import navigator
if navigator.contains('modern_projection_workspace'): navigator.pop()
view=s.bridge.factory.CreatePlayerView(s.bridge.player)
_result={'perspective':view.GetPerspective(),
         'reduced_motion':s.reduced_motion,
         'foot':s.bridge.factory.CreatePos(s.bridge.player).GetFootPos()}''')
    carried = game('''item=api.GetEngineCompFactory().CreateItem(player)
_result=item.GetPlayerItem(api.GetMinecraftEnum().ItemPosType.CARRIED,0)''', True)
    try:
        game('s.reduced_motion=True\n_result=True')
        assert equip('modern_projection:terminal')
        x, y, z = old['foot']
        camera((x + 2.65, y + 1.25, z + .05),
               (x + 1.2, y + 1.18, z))
        time.sleep(1.2)
        state = game('''_result={'aura':owner.staff_aura.entity,
                   'foot':s.bridge.factory.CreatePos(s.bridge.player).GetFootPos()}''')
        assert state['aura'], state
        capture.user32.SetProcessDPIAware()
        window = capture._find_game_window(capture._list_windows(), pid=binding['game_pid'])
        assert window
        unused_x, unused_y, width, height = capture._window_rect(window['hwnd'])
        capture._capture_window_windows(window['hwnd'], width, height, False, str(out))
        print(json.dumps({'image':str(out), 'size':[width,height],
                          'state':state}, ensure_ascii=False))
    finally:
        game('''cam=s.bridge.factory.CreateCamera(s.bridge.level)
cam.ResetCameraPos()
cam.UnDepartCamera()
s.reduced_motion=%r
s.bridge.factory.CreatePlayerView(s.bridge.player).SetPerspective(%r)
_result=True''' % (old['reduced_motion'], old['perspective']))
        game('''item=api.GetEngineCompFactory().CreateItem(player)
saved=%r
if saved:
 for key in ('itemName','newItemName'):
  if isinstance(saved.get(key),unicode): saved[key]=saved[key].encode('utf8')
 item.SpawnItemToPlayerCarried(saved,player)
else:
 item.SpawnItemToPlayerCarried({'itemName':'minecraft:air','count':0,'auxValue':0},player)
_result=True''' % carried, True)


if __name__ == '__main__':
    main()
