"""Bound live checks: catalogue UI, native picking, paste preview and spectrum speed."""
import json
import time
import verify_ui as ui
import capture_screen as capture
from mcdk import Client, return_value
from verify_selection_scope import diagnostic, wait_preview
from verify_selection_outline import click_voxel, outline, same_outline
from verify_global_cursor import hover
from verify_large_editor import snapshot
from native_input_mode import set_touch


def game(code):
    with Client() as client:
        return return_value(client.call('execute_code', {'code':
            'from __future__ import unicode_literals\nimport mod.client.extraClientApi as api\n'
            's=api.GetSystem("ModernProjection", "HelloClientSystem").session\n'+code,
            'is_client': True, 'direct_return': True}))


def main():
    capture.user32.SetProcessDPIAware()
    window = capture._find_game_window(capture._list_windows(), process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd'])
    left, top, width, height = capture._window_rect(window['hwnd'])
    capture.user32.SetCursorPos(left+30, top+40)

    def native_click(node):
        button = node if node['type']=='Button' else ui.nodes('Button', node)[0]
        control = ui.call('native_control', button['id'])['result']
        scale = width/ui.nodes('SafeArea')[0]['children'][0]['layout']['width']
        x = int(left+(control['global'][0]+control['size'][0]/2.)*scale)
        y = int(top+(control['global'][1]+control['size'][1]/2.)*scale)
        assert left<=x<left+width and top<=y<top+height, (x,y,control)
        assert capture.user32.GetForegroundWindow()==window['hwnd']
        capture.user32.SetCursorPos(x,y); time.sleep(.12)
        capture.user32.mouse_event(2,0,0,0,0)
        try:
            time.sleep(.08)
        finally:
            capture.user32.mouse_event(4,0,0,0,0)
        time.sleep(.4)

    def action(label, root=None):
        return next(n for n in ui.nodes('Action',root) if n['props'].get('label')==label)

    original = game('_result={"palette":s.palette[:],"speed":s.spectrum_speed}')
    try:
        game('s.set("material_browser",None)\n_result=True');time.sleep(.3)
        set_touch(False)
        ui.click('工作台'); ui.click('参数'); ui.click('放置')
        diagnostic({'fixture':'offset','camera':[0,90,1]});wait_preview()
        ui.call('scroll',ui.nodes('ScrollView',ui.nodes('Parameters')[0])[0]['id'],10000)
        time.sleep(.3)
        plus = next(n for n in ui.nodes('JellyButton',ui.nodes('MaterialPicker')[0]) if n.get('key')=='add_material')
        native_click(plus)
        ui.check('palette plus opens native block inventory',bool(ui.nodes('BlockInventory')))
        deadline=time.time()+25
        while game('_result=s.catalogue_loading') and time.time()<deadline:
            time.sleep(.3)
        catalogue=game('_result={"ready":s.catalogue_ready,"count":len(s.block_catalogue),"names":[i["name"] for i in s.block_catalogue]}')
        ui.check('SDK block catalogue loads localized names',catalogue['ready'] and catalogue['count']>200)
        (ui.OUT/'block_catalogue_names.json').write_text(json.dumps(catalogue,ensure_ascii=False),encoding='utf8')
        inv=ui.nodes('BlockInventory')[0]
        ui.check('inventory pages bound native item controls',len(ui.nodes('Item',inv))<=41)
        native_click(action('木材',inv))
        ui.check('category filters wood',any('木' in t for t in ui.labels(ui.nodes('BlockInventory')[0])))
        inp=ui.nodes('Input',ui.nodes('BlockInventory')[0])[0]
        ui.call('set_input',inp['id'],'混凝土');time.sleep(.5)
        inv=ui.nodes('BlockInventory')[0]
        grid=[n for n in ui.nodes('JellyButton',inv) if str(n.get('key','')).startswith('block') and ui.nodes('Button',n)]
        ui.check('Chinese name search finds block variants',len(grid)>=16 and all('混凝土' in ''.join(ui.labels(n)) for n in grid))
        snapshot('block_inventory_search')
        cell=next(n for n in grid if '红色混凝土' in ui.labels(n))
        props=ui.nodes('Item',cell)[0]['props']
        expected=[props['identifier'],props.get('aux',0)]
        native_click(cell)
        before=diagnostic()['blocks']
        native_click(action('添加并使用',ui.nodes('BlockInventory')[0]))
        ui.check('native inventory selection adds and equips full block data',game('_result=s.editor.material')==expected and
                 not ui.nodes('BlockInventory') and diagnostic()['blocks']==before)
        picker=ui.nodes('MaterialPicker')[0]
        if '整理' in ui.labels(picker):
            native_click(action('整理',picker))
        ui.call('scroll',ui.nodes('ScrollView',ui.nodes('Parameters')[0])[0]['id'],10000)
        time.sleep(.3)
        # These are preference changes, never edits to the building.
        palette=game('_result=s.palette')
        target=next(n for n in ui.nodes('JellyButton',ui.nodes('MaterialPicker')[0]) if n.get('key')=='mat%d'%(len(palette)-1))
        native_click(target)
        snapshot('palette_management_spacing')
        native_click(action('前移',ui.nodes('MaterialPicker')[0]))
        ui.check('palette reorders selected shortcut',game('_result=s.palette[-2]')==expected)
        native_click(action('移除',ui.nodes('MaterialPicker')[0]))
        ui.check('palette removal preserves current material and document',expected not in game('_result=s.palette') and
                 diagnostic()['blocks']==before)
        ui.click('完成')
        # Default period and slider changes update UVs without rebuilding meshes.
        ui.click('图层')
        speed=next(n for n in ui.nodes('Range') if n['props'].get('label')=='炫彩流动速度')
        builds=diagnostic()['previewBuilds']
        ui.call('set_slider',ui.nodes('Slider',speed)[0]['id'],(4.-.25)/5.75);time.sleep(.4)
        ui.check('speed slider updates setting without rebuilding meshes',abs(game('_result=s.spectrum_speed')-4.)<.02 and diagnostic()['previewBuilds']==builds)
        deadline=time.time()+3.
        while abs(game('_result=s.bridge.load_preferences()["spectrum_speed"]')-4.)>=.02 and time.time()<deadline:
            time.sleep(.2)
        ui.check('settings persist speed and palette together',abs(game('_result=s.bridge.load_preferences()["spectrum_speed"]')-4.)<.02)
        ui.click('参数')
        game('s.editor.select_box((2,1,3),(5,3,8))\ns.editor.run("copy")\ns.choose_tool("paste")\n_result=s.editor.clipboard["size"]')
        time.sleep(.5)
        hover((14.5,0,12.5));preview=outline('cursor')
        ui.check('paste previews full clipboard cuboid',any(n['visible'] for n in preview) and not any(n['visible'] for n in outline()))
        before=diagnostic()
        click_voxel((14.5,0,12.5)); pinned=outline('cursor')
        ui.check('paste click fixes origin without editing or resizing source selection',game('_result=s.paste_origin')==[14,0,12] and diagnostic()['blocks']==before['blocks'])
        text_labels=ui.labels(ui.nodes('PasteControls')[0])
        ui.check('paste inspector shows current extent and fixed origin',
                 '尺寸  4 × 3 × 6' in text_labels and '已固定起点' in text_labels and '14' in text_labels and '12' in text_labels)
        hover((18.5,0,14.5))
        ui.check('fixed paste preview stays at clicked origin',same_outline(pinned,outline('cursor')))
        snapshot('paste_region_preview')
        native_click(action('确认粘贴'))
        wait_preview()
        ui.check('pasting does not clip to old selection',diagnostic()['blocks']==before['blocks']+72 and diagnostic()['selection']==72)
        game('s.action(s.editor.undo)\n_result=s.editor.revision');wait_preview()
        ui.check('entire paste undoes in one step',diagnostic()['blocks']==before['blocks'])
        game('s.set_paste_origin((23,0,23))\ns.run()\n_result=s.editor.message')
        ui.check('out of bounds paste refuses entire operation',diagnostic()['blocks']==before['blocks'] and '边界' in game('_result=s.editor.message'))
        # Reuse the current source, but select a destination with real F11 touch.
        set_touch(True)
        from verify_native_touch import touch
        touch((14.5,0,12.5))
        ui.check('native touch tap places paste origin without editing',game('_result=s.paste_origin')==[14,0,12] and diagnostic()['blocks']==before['blocks'])
        native_click(action('确认粘贴'));wait_preview()
        ui.check('touch confirmation pastes complete copied region',diagnostic()['blocks']==before['blocks']+72)
        set_touch(False)
        ui.click('放置')
        labels=ui.nodes('Label',ui.nodes('PlacementControls')[0])
        ui.check('placement help uses smooth existing typography',bool(labels) and all(n['props'].get('rasterText') for n in labels))
        game('s.choose_group("transform")\n_result=True');time.sleep(.3)
        xs=ui.nodes('Image',action('沿 X 阵列'));zs=ui.nodes('Image',action('沿 Z 阵列'))
        ui.check('array axes use distinct icon orientations',any(n['props'].get('rotate')==90 for n in zs) and
                 not any(n['props'].get('rotate')==90 for n in xs))
        snapshot('materials_paste_final')
    finally:
        game('s.palette=[tuple(v) for v in '+repr(original['palette'])+']\ns.spectrum_speed='+repr(original['speed'])+
             '\ns.material_browser=None\ns.save_preferences()\ns.emit()\n_result=True')
        set_touch(False)
        (ui.OUT/'materials_paste_checks.json').write_text(json.dumps(ui.checks,ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':
    main()
