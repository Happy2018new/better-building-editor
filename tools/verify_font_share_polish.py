"""Native atlas, short clipboard segments, missing-page layout and status cards."""
import json
import subprocess
import sys
import time
import verify_ui as ui
import capture_screen as capture
from verify_materials_paste import game as execute
from verify_large_editor import snapshot
from assess_clipboard_runtime import ClipboardBackup


def game(source):
    # The embedded Python 2 execute-code endpoint misdecodes non-ASCII source.
    # Escaped unicode literals exercise actual Chinese, not UTF-8 mojibake.
    return execute(source.encode('ascii','backslashreplace').decode('ascii'))


def wait():
    for unused in range(160):
        value=game('_result={"busy":s.sharing.busy,"error":s.sharing.error,"message":s.sharing.message}')
        if not value['busy']:
            assert not value['error'],value
            return
        time.sleep(.1)
    raise AssertionError(value)


def main(background=False):
    capture.user32.SetProcessDPIAware()
    window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
    assert window and (background or capture._activate_window(window['hwnd']))
    left,top,width,height=capture._window_rect(window['hwnd'])
    resize=str(ui.ROOT/'.agents/skills/pyreact-debugging/scripts/resize_window.py')
    if '--reload-typography' in sys.argv:
        import base64
        source=(ui.ROOT/'behavior_pack/HelloScript/projection/typography.py').read_bytes()
        game('import base64\nfrom HelloScript.projection import typography\nold_glyph=typography.glyph\nexec(compile(base64.b64decode('+repr(base64.b64encode(source).decode('ascii'))+'),"typography.py","exec"),typography.__dict__)\nold_glyph.func_code=typography.glyph.func_code\n_result=True')
    backup=ClipboardBackup()
    native_clipboard=False if background else backup.save()
    if not native_clipboard:
        backup.discard()
        print('SKIP OS clipboard: '+('background check requested' if background else 'unsupported or locked clipboard')+'; use memory bridge',flush=True)
    game('''api._font_saved=(s.library,s.page,s.preview_error,s.camera_depth,s.name,s.bridge.get_clipboard,s.bridge.set_clipboard,s.editor.document.name)
s.library=[{"id":90001,"data":{"name":"annnn币","size":[64,128,64],"blockCount":20649}}]
s.name='annnn币'
s.set('page','library')
s.emit()
_result=True''')
    try:
        if not native_clipboard:
            game('''def memory_clipboard():
    content=['']
    def read():return content[0]
    def write(value):content[0]=value;return True
    return read,write
s.bridge.get_clipboard,s.bridge.set_clipboard=memory_clipboard()
_result=True''')
        time.sleep(.5)
        labels=ui.nodes('Label',ui.nodes('Library')[0])
        snapshot('stage53_library_font')
        for value in ('annnn币','分享当前草稿','导入分享码'):
            matches=[n for n in labels if n['props'].get('content')==value]
            ui.check(value+' uses complete font atlas',bool(matches) and all(ui.nodes('Image',n) for n in matches))
        game('s.sharing.open_export()\n_result=True');wait()
        for size in (256,512,1024):
            game('s.sharing.set_part_size(%d)\ns.sharing.copy(True)\n_result=True'%size)
            time.sleep(.2)
            value=game('_result={"length":len(s.bridge.get_clipboard()),"exact":s.bridge.get_clipboard()==s.sharing.parts[0]}')
            ui.check('%d-character segment crosses %s clipboard'%(size,'native' if native_clipboard else 'memory'),0<value['length']<=size+40 and value['exact'])
        game('s.sharing.set_part_size(512)\napi._font_parts=list(s.sharing.parts)\n_result=True')
        snapshot('stage53_share_short')
        game('s.sharing.close()\ns.sharing.open_import()\n_result=True')
        count=game('_result=len(api._font_parts)')
        assert count>24,count
        for index in (-1,1,3,1):
            game('s.bridge.set_clipboard(api._font_parts[%d])\n_result=True'%index)
            time.sleep(.17)
            game('s.sharing.paste()\n_result=True');time.sleep(.17)
        ui.check('inbox marks exact missing parts and ignores duplicate',game('_result=len(s.sharing.inbox.parts)==3 and s.sharing.inbox.missing()[:3]==[1,3,5] and not s.sharing.error'))
        for preset in (('current',) if background else ('4:3','16:9')):
            if not background:
                subprocess.run([sys.executable,resize,'--preset',preset],check=True,capture_output=True)
            time.sleep(.7)
            dialog=ui.nodes('SharingDialog')[0]
            root=ui.nodes('SafeArea')[0]['children'][0]['layout']
            for action in ui.nodes('Action',dialog):
                box=ui.nodes('Button',action)[0]['layout']
                assert box['x']>=0 and box['y']>=0 and box['x']+box['width']<=root['width']+1 and box['y']+box['height']<=root['height']+1,(preset,box,root)
            ui.check(preset+' missing grid fits screen',True)
            ui.check(preset+' missing grid has no long missing-number sentence',not any('缺少第' in value for value in ui.labels(dialog)))
            snapshot('stage53_missing_'+preset.replace(':','_'))
        game('s.sharing.inbox_move(1)\n_result=True');time.sleep(.2)
        ui.check('missing grid changes page',game('_result=s.sharing.inbox_page==1'))
        game('s.sharing.first_missing()\n_result=True');time.sleep(.2)
        ui.check('locate missing returns to first missing part',game('_result=s.sharing.inbox_page==0'))
        # Complete all remaining pieces in the codec without hundreds of host IPCs.
        exact=game('''for part in api._font_parts:
    result=s.sharing.inbox.add(part)
api._font_complete=result
from HelloScript.projection.sharing_codec import decode_steps
result=list(decode_steps(result))[-1]
_result=result['document'].blocks==s.editor.document.blocks''')
        ui.check('short pieces reconstruct exact maximum ellipsoid',exact and game('_result=not s.sharing.inbox.missing()'))
        game('s.sharing.close()\ns.set("page","workspace")\ns.camera_depth=40.\ns.emit("camera_depth")\n_result=True');time.sleep(.6)
        ui.check('forward depth hint restored','视线已深入 40 格' in ui.labels())
        snapshot('stage53_depth_font')
        game('''api._font_progress=(s.preview_pending,s.tiles.report_progress,s.tiles.progress)
s.preview_pending=True
s.tiles.report_progress=True
s.tiles.progress=lambda:(24,128)
_result=True''');time.sleep(.3)
        progress=ui.nodes('PreviewProgress',ui.call('dump_tree')['tree'])[0]
        cancel=next(n for n in ui.nodes('PreviewAction',progress) if n['props'].get('label')=='取消')
        cancel_button=ui.nodes('Pointer',cancel)[0]
        label=next(n for n in ui.nodes('Label',progress) if '24 / 128' in n['props'].get('content',''))
        ui.check('progress and cancel share a compact row',abs(cancel_button['layout']['y']-label['layout']['y'])<12)
        snapshot('stage54_preview_progress')
        for phase in ('down','up'):
            ui.call('pointer',cancel_button['id'],{'phase':phase,'x':cancel_button['layout']['width']/2.,'y':cancel_button['layout']['height']/2.})
        time.sleep(.2)
        ui.check('cancel stops preview rather than pausing it',game('_result=not s.preview_pending and not s.tiles.running and s.tiles.iterator is None and "取消" in s.preview_error'))
        game('s.preview_pending,s.tiles.report_progress,s.tiles.progress=api._font_progress\ndel api._font_progress\n_result=True')
        game('s.preview_error="已取消更新，可重试"\n_result=True');time.sleep(.3)
        status=ui.nodes('Label',ui.nodes('PreviewProgress',ui.call('dump_tree')['tree'])[0])
        ui.check('compact progress paints imperative atlas caption',any(n['props'].get('content')=='已取消更新，可重试' for n in status))
        if not background:
            subprocess.run([sys.executable,resize,'--preset','4:3'],check=True,capture_output=True)
        time.sleep(.5)
        status=ui.nodes('Label',ui.nodes('PreviewProgress',ui.call('dump_tree')['tree'])[0])
        ui.check('progress caption remains stable'+(' across resize' if not background else ''),any(n['props'].get('content')=='已取消更新，可重试' for n in status))
        for name in ('annnn币','未命名建筑'):
            game('s.editor.document.name='+repr(name)+'\ns.emit()\n_result=True');time.sleep(.4)
        snapshot('stage53_progress_card')
        game('s.preview_error=""\ns.confirm("新建 64 × 128 × 64 区域将替换当前草稿。\\n请先保存需要保留的作品。",lambda:None)\n_result=True');time.sleep(.5)
        snapshot('stage53_confirm_wrap')
    finally:
        try:
            game('''s.sharing.close()
if hasattr(api,'_font_progress'):
    s.preview_pending,s.tiles.report_progress,s.tiles.progress=api._font_progress
    del api._font_progress
s.pending_confirm=None
s.library,s.page,s.preview_error,s.camera_depth,s.name,s.bridge.get_clipboard,s.bridge.set_clipboard,s.editor.document.name=api._font_saved
s.emit()
del api._font_saved
_result=True''')
            if not background:
                subprocess.run([sys.executable,resize,'--size','%dx%d'%(width,height)],check=True,capture_output=True)
        finally:
            try:
                if native_clipboard:backup.restore()
            finally:backup.discard()
            (ui.OUT/'stage53_font_share_checks.json').write_text(json.dumps(ui.checks,ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':main()
