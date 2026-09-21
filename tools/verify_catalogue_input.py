"""Native search typing, modal isolation and rapid result/empty transitions.

No world or library writes. Numeric keys preserve the user's current IME;
Chinese text uses MCDK's native text injection, not Pyreact set_input.
"""
import json
import time
import mss
from PIL import Image
import verify_ui as ui
import capture_screen as capture
from mcdk import Client
from verify_materials_paste import game
from verify_large_editor import snapshot
from native_input_mode import key, set_touch
from verify_input_scale import inspect


def main():
    capture.user32.SetProcessDPIAware()
    window = capture._find_game_window(capture._list_windows(), process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd'])
    if not ui.nodes('ToolList'):
        key('p'); time.sleep(1)
    original=game('_result=s.query')
    samples=[]

    def foreground():
        assert capture.user32.GetForegroundWindow()==window['hwnd'], 'Game lost foreground'

    def click(node):
        foreground()
        control=ui.call('native_control',node['id'])['result']
        left,top,width,height=capture._window_rect(window['hwnd'])
        scale=width/ui.nodes('SafeArea')[0]['children'][0]['layout']['width']
        x,y=control['global'];w,h=control['size']
        capture.user32.SetCursorPos(int(left+(x+w*.4)*scale),int(top+(y+h/2)*scale))
        time.sleep(.1)
        capture.user32.mouse_event(2,0,0,0,0)
        try:time.sleep(.08)
        finally:capture.user32.mouse_event(4,0,0,0,0)
        time.sleep(.3)
        return control

    def press(vk):
        foreground()
        capture.user32.keybd_event(vk,0,0,0)
        try:time.sleep(.028)
        finally:capture.user32.keybd_event(vk,0,2,0)
        time.sleep(.038)

    def rapid(field, name):
        control=click(field)
        inspect(field,name)
        left,top,width,height=capture._window_rect(window['hwnd'])
        scale=width/ui.nodes('SafeArea')[0]['children'][0]['layout']['width']
        x,y=control['global'];w,h=control['size']
        area=dict(left=int(left+(x+w*.8)*scale),top=int(top+(y+h/2)*scale),width=3,height=3)
        colors=[]
        with mss.MSS() as screen:
            for unused in range(8):
                for vk in (49,49,49,8,8,8):
                    press(vk)
                    raw=screen.grab(area)
                    colors.append(Image.frombytes('RGB',raw.size,raw.bgra,'raw','BGRX').getpixel((1,1)))
            # Also let each filter settle. This exercises both the result and
            # empty layouts, in addition to the rapid burst above.
            for unused in range(4):
                for vk in (49,8):
                    press(vk);time.sleep(.4)
                    raw=screen.grab(area)
                    colors.append(Image.frombytes('RGB',raw.size,raw.bgra,'raw','BGRX').getpixel((1,1)))
        final=ui.call('native_control',field['id'])['result']
        samples.append(dict(name=name,colors=colors,final=final))
        ui.check(name+': real rapid typing/deletion retains focus and ends empty',
                 final['text']=='' and final['displayText']['properties'].get('#text_edit_selected'))
        ui.check(name+': focused gray persists through all 56 key samples',
                 all(all(55<=v<=90 for v in rgb) for rgb in colors))
        press(49);time.sleep(.15)
        following=ui.call('native_control',field['id'])['result']
        if following['text']!='1':
            samples.append(dict(name=name+'_following_key',final=following))
            print(json.dumps(following,ensure_ascii=False),flush=True)
            snapshot(name+'_following_key_failed')
        ui.check(name+': further native keyboard input still works',following['text']=='1')
        snapshot(name)
        press(8)

    def pale(field, name):
        native=ui.call('native_control',field['id'])['result']
        left,top,width,height=capture._window_rect(window['hwnd'])
        scale=width/ui.nodes('SafeArea')[0]['children'][0]['layout']['width']
        x,y=native['global'];w,h=native['size']
        with mss.MSS() as screen:
            raw=screen.grab(dict(left=int(left+(x+w*.8)*scale),top=int(top+(y+h/2)*scale),width=3,height=3))
            color=Image.frombytes('RGB',raw.size,raw.bgra,'raw','BGRX').getpixel((1,1))
        ui.check(name+': unfocused field uses original pale background',min(color)>200)

    def open_inventory():
        game('s.open_materials("material")\n_result=True');time.sleep(.7)
        deadline=time.time()+25
        while game('_result=s.catalogue_loading') and time.time()<deadline:time.sleep(.3)
        return ui.nodes('BlockInventory')[0]

    def close_inventory():
        close=next(n for n in ui.nodes('Action',ui.nodes('BlockInventory')[0]) if n['props'].get('glyph')=='close' and not n['props'].get('label'))
        click(ui.nodes('Button',close)[0])
        ui.check('native close restores workspace input',not ui.nodes('BlockInventory'))

    try:
        set_touch(False)
        game('s.set("material_browser",None)\ns.set("query", "")\n_result=True');time.sleep(.5)
        pale(ui.nodes('Input',ui.nodes('ToolList')[0])[0],'initial toolbox')
        inv=open_inventory()
        field=ui.nodes('Input',inv)[0]
        pale(field,'initial catalogue')
        rapid(field,'catalogue_pc_search')
        ui.check('empty query restores populated inventory without replacing input',
                 ui.nodes('Input',ui.nodes('BlockInventory')[0])[0]['id']==field['id'] and
                 len(ui.nodes('Item',ui.nodes('BlockInventory')[0]))>20)
        with Client() as client:
            result=client.call('mc_input',{'op':'/run','args':{'steps':[{'do':'text','value':'混凝土'}]}})
        assert not result.get('isError'),result
        time.sleep(.4)
        inv=ui.nodes('BlockInventory')[0]
        cells=[n for n in ui.nodes('JellyButton',inv) if n.get('key')=='block' and ui.nodes('Button',n)]
        ui.check('native Chinese text filters localized block names',
                 ui.call('native_control',field['id'])['result']['text']=='混凝土' and
                 len(cells)>=16 and all('混凝土' in ''.join(ui.labels(n)) for n in cells))
        snapshot('catalogue_chinese_native_search')
        before=game('_result=(s.page,s.editor.revision,s.query)')
        tab=next(n for n in ui.nodes('Button') if '建筑库' in ui.labels(n))
        click(tab)
        ui.check('modal blocks clicks on underlying page navigation',game('_result=(s.page,s.editor.revision,s.query)')==before)
        pale(field,'blurred catalogue')
        close_inventory()
        field=ui.nodes('Input',ui.nodes('ToolList')[0])[0]
        rapid(field,'toolbox_pc_search')
        ui.check('toolbox returns from empty results to tools',len(ui.nodes('Action',ui.nodes('ToolList')[0]))>4)
        set_touch(True)
        inv=open_inventory()
        rapid(ui.nodes('Input',inv)[0],'catalogue_f11_search')
        close_inventory()
    finally:
        game('s.set("material_browser",None)\ns.set("query",'+repr(original)+')\n_result=True')
        time.sleep(.3)
        set_touch(False)
        (ui.OUT/'catalogue_native_input.json').write_text(json.dumps({'checks':ui.checks,'samples':samples},ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':main()
