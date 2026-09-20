"""Measure game-thread UI commits and native control churn, not IPC latency."""
import json
import sys
import time
import verify_ui as ui
from verify_materials_paste import game


def main():
    game('s.set("material_browser",None)\n_result=True');time.sleep(.4)
    game('s.open_materials("material")\n_result=True');time.sleep(2)
    if '--hotspots' in sys.argv:
        game('''import cProfile
import pstats
import StringIO
h=api.GetTopScreen()
cls=type(h)
cls._profile_saved_flush=cls._pyreact_flush
h._switch_profile=cProfile.Profile()
def profiled(self):
    return self._switch_profile.runcall(self._profile_saved_flush)
cls._pyreact_flush=profiled
_result=True
''')
        try:
            ui.click('木材')
            print(game('''h=api.GetTopScreen()
out=StringIO.StringIO()
pstats.Stats(h._switch_profile,stream=out).sort_stats('cumulative').print_stats(32)
_result=out.getvalue()
'''))
        finally:
            game('cls=type(api.GetTopScreen())\ncls._pyreact_flush=cls._profile_saved_flush\ndel cls._profile_saved_flush\n_result=True')
        return
    game('''from HelloScript.pyreact import native
import time
h=api.GetTopScreen()
cls=type(h)
if not hasattr(cls, '_catalogue_original_flush'):
    cls._catalogue_original_flush=cls._pyreact_flush
    def flush(self):
        started=time.clock()
        try:return self._catalogue_original_flush()
        finally:
            duration=(time.clock()-started)*1000.
            if duration>.1:self._catalogue_times.append(duration)
    cls._pyreact_flush=flush
if not hasattr(native,'_catalogue_original_clone'):
    native._catalogue_original_clone=native.clone
    def clone(host,*args):
        host._catalogue_clones+=1
        return native._catalogue_original_clone(host,*args)
    native.clone=clone
h._catalogue_times=[]
h._catalogue_clones=0
_result=True
''')
    records=[]
    try:
        for label in ['下一页','下一页','上一页','木材','彩色方块','模组方块','全部方块']:
            inv=ui.nodes('BlockInventory')[0]
            action=next(n for n in ui.nodes('Action',inv) if n['props'].get('label')==label)
            game('h=api.GetTopScreen()\nh._catalogue_times=[]\nh._catalogue_clones=0\n_result=True')
            ui.call('click',ui.nodes('Button',action)[0]['id']);time.sleep(.35)
            result=game('h=api.GetTopScreen()\n_result={"commits":h._catalogue_times[:],"clones":h._catalogue_clones}')
            records.append(dict(action=label,**result))
            print({'action':label,'clones':result['clones'],'peak_commit_ms':round(max(result['commits'] or [0]),2)},flush=True)
    finally:
        game('''from HelloScript.pyreact import native
cls=type(api.GetTopScreen())
cls._pyreact_flush=cls._catalogue_original_flush
del cls._catalogue_original_flush
native.clone=native._catalogue_original_clone
del native._catalogue_original_clone
_result=True
''')
    (ui.OUT/('catalogue_perf_'+('before' if '--baseline' in sys.argv else 'after')+'.json')).write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf8')
    game('s.set("material_browser",None)\n_result=True');time.sleep(.3)


if __name__=='__main__':main()
