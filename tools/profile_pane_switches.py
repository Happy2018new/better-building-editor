"""Measure cold/warm navigation and dialog commits in an owned game instance."""
import json
import sys
import time
import verify_ui as ui
import capture_screen as capture
from verify_materials_paste import game
from native_input_mode import key, set_touch


def main():
    window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd'])
    set_touch(False)
    game('from HelloScript.pyreact import navigator\ns.set("page","workspace")\ns.set("inspector","params")\nnavigator.pop()\n_result=True')
    time.sleep(.5);key('p');time.sleep(3.)
    game('''from HelloScript.pyreact import native
import time
h=api.GetTopScreen()
cls=type(h)
cls._pane_saved_flush=cls._pyreact_flush
native._pane_saved_clone=native.clone
h._pane_costs=[]
h._pane_clones=0
h._pane_hotspots=[]
h._pane_profile=None
def flush(self):
    started=time.clock()
    try:
        if self._pane_profile is not None:
            return self._pane_profile.runcall(self._pane_saved_flush)
        return self._pane_saved_flush()
    finally:
        cost=(time.clock()-started)*1000.
        if cost>.1:self._pane_costs.append(cost)
        if self._pane_profile is not None:
            if cost>50. and len(self._pane_hotspots)<12:
                import pstats
                stats=pstats.Stats(self._pane_profile).stats
                top=sorted(stats.items(),key=lambda pair:pair[1][3],reverse=True)[:18]
                self._pane_hotspots.append((cost,[(str(k),v[:4]) for k,v in top]))
            self._pane_profile.clear()
def clone(host,*args):
    host._pane_clones+=1
    return native._pane_saved_clone(host,*args)
cls._pyreact_flush=flush
native.clone=clone
_result=True
''')
    if '--hotspots' in sys.argv:
        game('import cProfile\nh._pane_profile=cProfile.Profile()\n_result=True')
    rows=[]
    operations=[('inspector','layers'),('inspector','history'),('inspector','params'),
                ('page','library'),('page','guide'),('page','projection'),('page','workspace')]
    try:
        for repeat in range(2):
            for field,value in operations:
                game('h=api.GetTopScreen()\nh._pane_costs=[]\nh._pane_clones=0\ns.set(%r,%r)\n_result=True'%(field,value))
                time.sleep(.6)
                data=game('_result={"commits":h._pane_costs[:],"clones":h._pane_clones}')
                rows.append(dict(field=field,value=value,repeat=repeat,**data))
                print(dict(field=field,value=value,repeat=repeat,peak_ms=round(max(data['commits'] or [0]),2),clones=data['clones']),flush=True)
        for opened in (True,False,True,False):
            game('h._pane_costs=[]\nh._pane_clones=0\ns.set("material_browser",%r)\n_result=True'%('material' if opened else None))
            time.sleep(.6)
            data=game('_result={"commits":h._pane_costs[:],"clones":h._pane_clones}')
            rows.append(dict(dialog=opened,**data))
            print(dict(dialog=opened,peak_ms=round(max(data['commits'] or [0]),2),clones=data['clones']),flush=True)
    finally:
        if '--hotspots' in sys.argv:
            (ui.OUT/'pane_hotspots.json').write_text(json.dumps(game('_result=h._pane_hotspots'),indent=2),encoding='utf8')
        game('cls._pyreact_flush=cls._pane_saved_flush\ndel cls._pane_saved_flush\nnative.clone=native._pane_saved_clone\ndel native._pane_saved_clone\ns.set("material_browser",None)\ns.set("page","workspace")\n_result=True')
        name='pane_switches_profiled.json' if '--hotspots' in sys.argv else 'pane_switches_before.json' if '--baseline' in sys.argv else 'pane_switches_after.json'
        (ui.OUT/name).write_text(json.dumps(rows,indent=2),encoding='utf8')


if __name__=='__main__':main()
