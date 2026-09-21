"""Compare game-thread commits for tools, modes and inventory lifecycle."""
import json
import sys
import time
import verify_ui as ui
from verify_materials_paste import game


def main():
    game('s.set("material_browser",None)\ns.set("page","workspace")\n_result=True')
    time.sleep(.5)
    game('''from HelloScript.pyreact import native
import time
h=api.GetTopScreen()
cls=type(h)
cls._switch_saved_flush=cls._pyreact_flush
native._switch_saved_clone=native.clone
h._switch_times=[]
h._switch_clones=0
def flush(self):
    started=time.clock()
    try:return self._switch_saved_flush()
    finally:
        duration=(time.clock()-started)*1000.
        if duration>.1:self._switch_times.append(duration)
def clone(host,*args):
    host._switch_clones+=1
    return native._switch_saved_clone(host,*args)
cls._pyreact_flush=flush
native.clone=clone
_result=True
''')
    records=[]
    operations=[('mode:'+m,'s.choose_mode(%r)'%m) for m in ('select','place','paint','erase','pick','box','browse')]
    operations += [('tool:'+t,'s.choose_tool(%r)'%t) for t in ('fill','erase','replace','copy','cut','shell','sphere','checker','noise','hollow','paste','fill')]
    operations += [('open:first','s.open_materials("material")'),('close:first','s.set("material_browser",None)'),
                   ('open:repeat','s.open_materials("material")'),('close:repeat','s.set("material_browser",None)')]
    try:
        for name,code in operations:
            game('h=api.GetTopScreen()\nh._switch_times=[]\nh._switch_clones=0\n'+code+'\n_result=True')
            time.sleep(1.5 if 'first' in name else .8)
            data=game('h=api.GetTopScreen()\n_result={"commits":h._switch_times[:],"clones":h._switch_clones}')
            records.append(dict(action=name,**data))
            print({'action':name,'clones':data['clones'],'peak_ms':round(max(data['commits'] or [0]),2)},flush=True)
    finally:
        game('''from HelloScript.pyreact import native
cls=type(api.GetTopScreen())
cls._pyreact_flush=cls._switch_saved_flush
del cls._switch_saved_flush
native.clone=native._switch_saved_clone
del native._switch_saved_clone
s.set('material_browser',None)
s.choose_tool('fill')
_result=True
''')
    (ui.OUT/('editor_switches_'+('before' if '--baseline' in sys.argv else 'after')+'.json')).write_text(
        json.dumps(records,ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':main()
