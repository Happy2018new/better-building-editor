"""Measure game-thread mount/flush cost of workspace reopens, not IPC latency."""
import json
import sys
import time
import verify_ui as ui
import capture_screen as capture
from verify_materials_paste import game
from native_input_mode import open_workspace


def main():
    window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd'])
    game('''from modern_projection.pyreact import native, navigator, host
from modern_projection.pyreact.navigator import NavigatorScreen
import time
NavigatorScreen._open_saved_flush=NavigatorScreen._pyreact_flush
native._open_saved_clone=native.clone
api._open_stats={'commits':[], 'clones':0, 'mounts':[]}
host._open_saved_mount=host._mount_element
def mount(*args):
    started=time.clock()
    try:return host._open_saved_mount(*args)
    finally:api._open_stats['mounts'].append((time.clock()-started)*1000.)
host._mount_element=mount
def flush(self):
    started=time.clock()
    try:return self._open_saved_flush()
    finally:
        cost=(time.clock()-started)*1000.
        if cost>.1:api._open_stats['commits'].append(cost)
def clone(host,*args):
    api._open_stats['clones']+=1
    return native._open_saved_clone(host,*args)
NavigatorScreen._pyreact_flush=flush
native.clone=clone
_result=True
''')
    rows=[]
    try:
        for repeat in range(3):
            game('from modern_projection.pyreact import navigator\nif navigator.contains("modern_projection_workspace"): navigator.pop()\n_result=True')
            time.sleep(.6)
            game("api._open_stats={'commits':[], 'clones':0, 'mounts':[]}\n_result=True")
            open_workspace()
            time.sleep(2.)
            result=game('_result=api._open_stats')
            rows.append(result)
            print(json.dumps(result), flush=True)
            ui.check('Workspace reopens %d' % repeat, bool(ui.nodes('Workspace')))
    finally:
        game('''from modern_projection.pyreact import native, host
from modern_projection.pyreact.navigator import NavigatorScreen
NavigatorScreen._pyreact_flush=NavigatorScreen._open_saved_flush
del NavigatorScreen._open_saved_flush
native.clone=native._open_saved_clone
del native._open_saved_clone
host._mount_element=host._open_saved_mount
del host._open_saved_mount
_result=True
''')
    (ui.OUT/('workspace_open_'+('before' if '--baseline' in sys.argv else 'after')+'.json')).write_text(
        json.dumps(rows,indent=2),encoding='utf8')


if __name__=='__main__':main()
