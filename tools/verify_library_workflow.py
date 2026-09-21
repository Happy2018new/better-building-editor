"""Native library/rename checks with an isolated in-memory persistence fixture."""
import json
import subprocess
import sys
import time
import verify_ui as ui
import capture_screen as capture
from mcdk import Client
from verify_materials_paste import game
from verify_large_editor import snapshot
from native_input_mode import set_touch


def main():
    capture.user32.SetProcessDPIAware()
    window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd'])
    set_touch(False)
    game(r'''import copy
s._library_check=(s.library,s.library_serial,s.name,s.bridge.save_library)
def store(data):
    s._library_saved=copy.deepcopy(data)
    return True
s.bridge.save_library=store
s.library=[{'id':i,'data':{'version':1,'name':name,'size':[24,16,24], 'blocks':[]}}
           for i,name in enumerate(['\u72ec\u7acb','\u77f3\u82f1\u5854\u697c','\u5ead\u9662\u7ec3\u4e60','\u6c34\u8fb9\u5c0f\u5c4b'],1)]
s.name='\u8349\u7a3f\u540d\u79f0'
s.set('page','library')
s.emit()
_result=True
''')
    time.sleep(.6)

    def click(node):
        target=node if node['type'] in ('Input','Button') else ui.nodes('Button',node)[0]
        native=ui.call('native_control',target['id'])['result']
        left,top,width,height=capture._window_rect(window['hwnd'])
        scale=width/ui.nodes('SafeArea')[0]['children'][0]['layout']['width']
        x,y=[native['global'][i]+native['size'][i]/2. for i in (0,1)]
        assert capture.user32.GetForegroundWindow()==window['hwnd'],'Game lost foreground'
        capture.user32.SetCursorPos(int(left+x*scale),int(top+y*scale));time.sleep(.08)
        capture.user32.mouse_event(2,0,0,0,0)
        try:time.sleep(.07)
        finally:capture.user32.mouse_event(4,0,0,0,0)
        time.sleep(.4)

    def action(label,root=None):
        return next(n for n in ui.nodes('Action',root) if n['props'].get('label')==label)

    def dialog():
        return ui.nodes('RenameDialog')[0]

    try:
        for preset in ('4:3','16:9'):
            subprocess.run([sys.executable,str(ui.ROOT/'.agents/skills/pyreact-debugging/scripts/resize_window.py'),
                            '--preset',preset],check=True,capture_output=True)
            time.sleep(.7)
            lib=ui.nodes('Library')[0]
            scroll=ui.nodes('ScrollView',lib)[0]['layout']
            actions=[n for n in ui.nodes('Action',lib) if n['props'].get('label')=='重命名']
            fully_visible=[n for n in actions if scroll['y']<=ui.nodes('Button',n)[0]['layout']['y'] and
                           ui.nodes('Button',n)[0]['layout']['y']+ui.nodes('Button',n)[0]['layout']['height']<=scroll['y']+scroll['height']]
            ui.check(preset+' library gives two complete cards their own scrolling area',len(fully_visible)>=2)
            snapshot('library_expanded_'+preset.replace(':','_'))
        click(action('重命名',ui.nodes('Library')[0]))
        field=ui.nodes('Input',dialog())[0]
        ui.check('rename dialog is prefilled with the clicked building',field['props']['value']=='独立')
        click(field)
        with Client() as client:
            result=client.call('mc_input',{'op':'/run','args':{'steps':[{'do':'key','keys':'ctrl+a'},{'do':'text','value':'独立名称'}]}})
        assert not result.get('isError'),result
        time.sleep(.3)
        native=ui.call('native_control',field['id'])['result']
        ui.check('rename accepts native input and retains native placeholder',native['text']=='独立名称' and native['placeholderPresent'])
        snapshot('library_rename_dialog')
        click(action('保存名称',dialog()))
        ui.check('rename saves only the selected entry and leaves the draft name alone',
                 game('_result=(s.library[0]["data"]["name"],s.library[1]["data"]["name"],s.name,s.pending_rename)')==
                 ['独立名称','石英塔楼','草稿名称',None])
        ui.check('successful rename is shown immediately in library','独立名称' in ui.labels(ui.nodes('Library')[0]))
        title=next(n for n in ui.nodes('Label',ui.nodes('Library')[0]) if n['props'].get('content')=='独立名称')
        ui.check('renamed Chinese building uses smooth glyphs without native fallback',
                 title['props'].get('rasterText') and ui.call('native_control',title['id'])['result']['text']=='')
        snapshot('library_name_smooth')
        click(action('重命名',ui.nodes('Library')[0]))
        field=ui.nodes('Input',dialog())[0]
        ui.call('set_input',field['id'],'取消修改')
        click(action('取消',dialog()))
        ui.check('cancel preserves the saved name',game('_result=s.library[0]["data"]["name"]')=='独立名称')
        click(action('删除',ui.nodes('Library')[0]))
        ui.check('delete opens the shared confirmation dialog',bool(game('_result=s.pending_confirm is not None')))
        click(action('确认继续',ui.nodes('Confirmation')[0]))
        ui.check('confirmed deletion removes only the fixture entry and closes the dialog',
                 game('_result=([entry["id"] for entry in s.library],s.pending_confirm)')==[[2,3,4],None])
        ui.click('工作台')
        ui.check('selection is no longer a duplicate tool category','选区' not in ui.labels(ui.nodes('CategoryRail')[0]))
        ui.click('选择当前层')
        ui.check('current layer selection operates directly',game('_result=len(s.editor.selection)')==576)
        ui.click('调整选区')
        ui.check('advanced selection actions live in inspector',all(t in ui.labels(ui.nodes('Parameters')[0]) for t in
                 ('扩展选区','收缩选区','反向选择','选择表面')))
        ui.click('全选')
        ui.check('full selection restores entire document',game('_result=len(s.editor.selection)')==9216)
        ui.check('visible built-in captions have no middle dots',not any('·' in label for label in ui.labels()))
    finally:
        game('''s.library,s.library_serial,s.name,s.bridge.save_library=s._library_check
del s._library_check
s.pending_rename=None
s.page='workspace'
s.emit()
_result=True
''')
        (ui.OUT/'library_workflow_checks.json').write_text(json.dumps(ui.checks,ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':main()
