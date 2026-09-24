"""Verify that P stays in-world and the terminal still opens the workspace."""
import json
import time
import verify_ui as ui
import capture_screen as capture
from verify_world_tools import game, input_step, state, equip


def key(hwnd, code):
    capture.user32.PostMessageW(hwnd, 0x100, code, 1)
    time.sleep(.1)
    capture.user32.PostMessageW(hwnd, 0x101, code, 0xC0000001)
    time.sleep(.4)


def main():
    original = state()
    game('''item=api.GetEngineCompFactory().CreateItem(player)
api._entry_carried=item.GetPlayerItem(api.GetMinecraftEnum().ItemPosType.CARRIED,0)
_result=True''',server=True)
    try:
        if original['open']:
            game('from HelloScript.pyreact import navigator\nnavigator.pop()\n_result=True')
            time.sleep(.6)
        if original['touch']:
            input_step('/key',keys='f11')
            time.sleep(.3)
        assert equip('modern_projection:terminal')
        time.sleep(.4)
        input_step('/key',keys='p')
        time.sleep(.5)
        ui.check('P leaves workspace closed while holding terminal',not state()['open'])
        input_step('/click',button='right',at=[.5,.4])
        time.sleep(2.)
        ui.check('Terminal right-click opens workspace',state()['open'])
        ui.save('ui_entry_verified')
    finally:
        if state()['open']:
            game('from HelloScript.pyreact import navigator\nnavigator.pop()\n_result=True')
            time.sleep(.6)
        if state()['touch'] != original['touch']:
            input_step('/key',keys='f11')
        game('''item=api.GetEngineCompFactory().CreateItem(player)
item.SpawnItemToPlayerCarried(api._entry_carried or {'itemName':'minecraft:air','count':0,'auxValue':0},player)
del api._entry_carried
_result=True''',server=True)
        if original['open']:
            game('owner.open_workspace()\n_result=True')
        (ui.OUT / 'entry_checks.json').write_text(json.dumps(ui.checks, indent=2), encoding='utf8')


if __name__ == '__main__':
    main()
