"""Native clipboard/share/import checks with in-memory archive writes and restoration."""
import json
import time
import verify_ui as ui
import capture_screen as capture
from verify_materials_paste import game
from verify_large_editor import snapshot
from native_input_mode import key, set_touch, state
from assess_clipboard_runtime import ClipboardBackup


def main():
    capture.user32.SetProcessDPIAware()
    window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd'])
    original_touch=state()['simulated']
    backup=ClipboardBackup()
    assert backup.save(),'Clipboard has unsupported formats; do not mutate it'
    game('''import copy
api._sharing_saved=(s.library,s.library_serial,s.page,s.bridge.save_library,s.bridge.save_archive_page,s.bridge.load_archive_page)
api._sharing_pages={}
api._sharing_index=None
def storage(pages,state):
    def page(identity,part,data):pages[(identity,part)]=copy.deepcopy(data);return True
    def load(identity,part):return pages.get((identity,part))
    def index(data):state['index']=copy.deepcopy(data);return True
    return page,load,index
s.bridge.save_archive_page,s.bridge.load_archive_page,s.bridge.save_library=storage(api._sharing_pages,{})
s.library=[]
s.library_serial=90000
s.set('page','library')
s.emit()
_result=True''')

    def wait():
        for unused in range(160):
            value=game('q=s.sharing\n_result={"opened":q.opened,"busy":q.busy,"error":q.error,"message":q.message,"parts":len(q.parts),"doc":q.document.size if q.document else None,"text":len(q.text) if q.text else None}')
            if not value['busy']:return value
            time.sleep(.08)
        raise AssertionError(value)

    def click(label):
        action=next(n for n in ui.nodes('Action') if n['props'].get('label')==label)
        button=ui.nodes('Button',action)[0]
        native=ui.call('native_control',button['id'])['result']
        left,top,width,height=capture._window_rect(window['hwnd'])
        scale=width/ui.nodes('SafeArea')[0]['children'][0]['layout']['width']
        point=tuple(int(a+(b+c/2.)*scale) for a,b,c in zip((left,top),native['global'],native['size']))
        assert capture.user32.GetForegroundWindow()==window['hwnd'],'Game lost foreground'
        capture.user32.SetCursorPos(*point);time.sleep(.1)
        capture.user32.mouse_event(2,0,0,0,0)
        try:time.sleep(.09)
        finally:capture.user32.mouse_event(4,0,0,0,0)
        time.sleep(.4)

    try:
        for touch in (False,True):
            set_touch(touch);time.sleep(.6)
            game('s.set("page","library")\n_result=True');time.sleep(1.2)
            click('分享当前草稿');value=wait()
            ui.check(('touch' if touch else 'PC')+' opens export and encodes current maximum draft',value['doc']==[64,128,64] and value['text']>0 and not value['error'])
            click('复制完整编码')
            ui.check('SDK copied complete archive',game('_result=s.bridge.get_clipboard()==s.sharing.text'))
            snapshot('stage52_share_ready')
            key('esc');time.sleep(.4)
            ui.check('Esc closes share dialog without closing workspace',not game('_result=s.sharing.opened'))
            click('导入分享码');click('从剪贴板读取');value=wait()
            ui.check('import validates all exact blocks before confirmation',not value['error'] and game('_result=s.sharing.document.blocks==s.editor.document.blocks'))
            count=game('_result=len(s.library)')
            snapshot('stage52_import_preview')
            click('确认加入建筑库');value=wait()
            ui.check('confirmed import appends one archive and preserves draft',game('_result=len(s.library)==%d and s.sharing.saved and s.io_job is None and s.sharing.document.blocks==s.editor.document.blocks'%(count+1)))
            key('esc');time.sleep(.4)
        # Export a paged saved config, then corrupt clipboard and prove atomic rejection.
        game('s.sharing.open_export(s.library[0]["id"])\n_result=True');value=wait()
        ui.check('saved paged archive export reads complete data',not value['error'] and game('_result=s.sharing.document.blocks==s.editor.document.blocks'))
        game('s.bridge.set_clipboard("MP2:broken:00000000")\ns.sharing.open_import()\ns.sharing.paste()\n_result=True');value=wait()
        ui.check('invalid clipboard leaves library and draft intact',value['error'] and game('_result=len(s.library)==2 and s.sharing.document is None'))
        # Force several real-sized fragments using a maximum random16 fixture.
        source=(ui.ROOT/'tools/assess_clipboard_sharing.py').read_text(encoding='utf8').split("if __name__=='__main__':")[0]
        game('import types\napi._share_fixture=types.ModuleType("fixture".encode("ascii"))\nexec(compile('+repr(source)+',"fixture","exec"),api._share_fixture.__dict__)\napi._share_large=api._share_fixture.fixture("random16")\nfrom HelloScript.projection.sharing_codec import encode_steps,split_text\napi._share_parts=split_text(list(encode_steps(api._share_large))[-1]["text"])\ns.sharing.open_import()\n_result=True')
        value=game('_result=len(api._share_parts)')
        game('_result=s.bridge.set_clipboard(api._share_parts[-1])')
        time.sleep(.2)
        game('s.sharing.paste()\n_result=True')
        time.sleep(.2)
        game('s.sharing.paste()\n_result=True')
        value_state=game('_result={"parts":len(s.sharing.inbox.parts),"error":s.sharing.error,"message":s.sharing.message}')
        print(value_state,flush=True)
        ui.check('segmented duplicate is ignored',value_state['parts']==1 and not value_state['error'])
        for index in range(value-1):
            game('_result=s.bridge.set_clipboard(api._share_parts[%d])'%index)
            time.sleep(.15)
            game('s.sharing.paste()\n_result=True')
            time.sleep(.15)
        result=wait()
        ui.check('out-of-order large fragments reassemble exact 524288 cells',not result['error'] and game('_result=s.sharing.document.blocks==api._share_large.blocks and len(s.sharing.document.blocks)==524288'))
        game('s.sharing.close()\n_result=True')
    finally:
        try:
            game('''s.sharing.close()
s.library,s.library_serial,s.page,s.bridge.save_library,s.bridge.save_archive_page,s.bridge.load_archive_page=api._sharing_saved
s.emit()
_result=True''')
            set_touch(original_touch)
        finally:
            backup.restore();backup.discard()
            (ui.OUT/'stage52_sharing_checks.json').write_text(json.dumps(ui.checks,ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':main()
