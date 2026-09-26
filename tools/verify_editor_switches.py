"""Native tool/mode clicks, retained inventory motion and air preview checks."""
import json
import sys
import time
import verify_ui as ui
import capture_screen as capture
from verify_materials_paste import game
from verify_large_editor import snapshot
from native_input_mode import set_touch


def main():
    capture.user32.SetProcessDPIAware()
    window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd'])
    set_touch(False)
    game('s.set("material_browser",None)\ns.set("page","workspace")\ns.set("inspector","params")\n_result=True')
    time.sleep(.4)

    def click(node):
        target=node if node['type']=='Button' else ui.nodes('Button',node)[0]
        native=ui.call('native_control',target['id'])['result']
        left,top,width,height=capture._window_rect(window['hwnd'])
        scale=width/ui.nodes('SafeArea')[0]['children'][0]['layout']['width']
        x,y=[native['global'][i]+native['size'][i]/2. for i in (0,1)]
        assert capture.user32.GetForegroundWindow()==window['hwnd'],'Game lost foreground'
        expected=(int(left+x*scale),int(top+y*scale))
        capture.user32.SetCursorPos(*expected);time.sleep(.09)
        capture.user32.mouse_event(2,0,0,0,0)
        try:time.sleep(.06)
        finally:capture.user32.mouse_event(4,0,0,0,0)
        time.sleep(.45)
        point=capture.POINT();capture.user32.GetCursorPos(capture.ctypes.byref(point))
        assert capture.user32.GetForegroundWindow()==window['hwnd'],'Game lost foreground after click'
        assert abs(point.x-expected[0])<3 and abs(point.y-expected[1])<3,('Pointer moved during native click',expected,(point.x,point.y))

    for mode,label in [('select','选取'),('place','放置'),('paint','换材质'),('erase','擦除'),('pick','吸管'),('box','框选'),('browse','浏览')]:
        if '--tail' in sys.argv:break
        segments=next(n for n in ui.nodes('Segments') if ['select','选取'] in n['props'].get('items',[]))
        button=next(n for n in ui.nodes('JellyButton',segments) if n.get('key')==mode)
        click(button)
        ui.check('native mode '+mode+' synchronizes inspector and controls',
                 game('_result=s.direct_mode')==mode and (label in ui.labels(ui.nodes('Parameters')[0]) if mode!='browse' else True))
    for group,tool,title in [('edit','erase','清空选区'),('edit','replace','替换材质'),('transform','mirror_x','沿 X 镜像'),
                             ('shape','shell','空心长方体'),('pattern','checker','棋盘拼色'),('finish','hollow','掏空内部')]:
        if '--tail' in sys.argv and group not in ('pattern','finish'):continue
        glyph={'edit':'brush','transform':'move','shape':'cube','pattern':'grid','finish':'spark'}[group]
        category=next(n for n in ui.nodes('Action',ui.nodes('CategoryRail')[0]) if n['props'].get('glyph')==glyph)
        click(category)
        action=next(n for n in ui.nodes('Action',ui.nodes('ToolList')[0]) if n['props'].get('label')==title)
        click(action)
        state=game('_result=s.tool')
        current=ui.tree()
        parameter_labels=ui.labels(ui.nodes('Parameters',current)[0])
        footer_labels=ui.labels(current)
        passed=state==tool and title in parameter_labels and '执行：'+title in footer_labels
        if not passed:print({'tool':state,'params':parameter_labels[:8],'footer':[v for v in footer_labels if v.startswith('执行')]},flush=True)
        ui.check('native tool '+tool+' synchronizes title and execution',passed)

    game('s.choose_tool("fill")\ns.set_editor("material",("minecraft:air",0))\n_result=True');time.sleep(.4)
    ui.call('scroll',ui.nodes('ScrollView',ui.nodes('Parameters')[0])[0]['id'],10000);time.sleep(.3)
    picker=ui.nodes('MaterialPicker')[0]
    summary=ui.nodes('MaterialIcon',picker)[0]
    ui.check('air summary has outline with no visible Item renderer',not ui.nodes('Item',summary) and '空气' in ui.labels(picker))
    snapshot('air_material_fixed')
    before=game('_result=(s.editor.revision,s.editor.document.size)')
    game('s.open_materials("material")\n_result=True');time.sleep(.7)
    inv=ui.nodes('BlockInventory')[0]
    identities=[n['id'] for n in ui.nodes('Input',inv)]
    snapshot('inventory_retained_open')
    game('s.set("material_browser",None)\n_result=True');time.sleep(.35)
    game('''import time
from modern_projection.pyreact.debug import _type_name
h=api.GetTopScreen()
def find(f,name):
    if _type_name(f)==name:return f
    for c in f.child_fibers:
        hit=find(c,name)
        if hit:return hit
inv=find(h._root_fiber,'BlockInventory')
moving=inv.parent_fiber
control=h.GetBaseUIControl(moving.native_path)
h._inventory_motion=[]
def sample(now):
    if len(h._inventory_motion)<120:
        h._inventory_motion.append((now,control.GetPosition()[1]))
h._inventory_probe={'fiber':moving,'active':True,'callback':sample}
h.pyreact_register_animation_frame(h._inventory_probe)
s.open_materials('material')
_result=True
''')
    try:
        time.sleep(.7)
        opened=game('_result=api.GetTopScreen()._inventory_motion[:]')
        game('api.GetTopScreen()._inventory_motion=[]\ns.set("material_browser",None)\n_result=True')
        time.sleep(.5)
        closed=game('_result=api.GetTopScreen()._inventory_motion[:]')
    finally:
        game('h=api.GetTopScreen()\nh.pyreact_unregister_animation_frame(h._inventory_probe)\n_result=True')
    for name,samples in [('open',opened),('close',closed)]:
        values=sorted(set(round(p[1],2) for p in samples))
        ui.check('inventory '+name+' traverses compact native intermediate positions',len(values)>=5 and values[-1]-values[0]>3)
    game('s.open_materials("secondary")\n_result=True');time.sleep(.5)
    inv=ui.nodes('BlockInventory')[0]
    ui.check('reopening retains native input control and syncs target channel',identities==[n['id'] for n in ui.nodes('Input',inv)] and inv['props']['channel']=='secondary')
    ui.check('mode/tool/catalogue switches do not edit document',before==game('_result=(s.editor.revision,s.editor.document.size)'))
    close=next(n for n in ui.nodes('Action',inv) if n['props'].get('glyph')=='close' and not n['props'].get('label'))
    click(close)
    ui.check('native close releases modal visibility',not ui.nodes('BlockInventory'))
    game('s.choose_mode("box")\ns.box_anchor=(1,1,1)\ns.emit()\n_result=True');time.sleep(.4)
    ui.check('pending corner appears immediately','起点已设置，请点击终点' in ui.labels())
    game('s.choose_mode("box")\n_result=True');time.sleep(.4)
    ui.check('reselecting box mode clears pending corner from inspector','起点已设置，请点击终点' not in ui.labels())
    game('s.choose_tool("fill")\n_result=True')
    (ui.OUT/'editor_switch_checks.json').write_text(json.dumps(dict(checks=ui.checks,opened=opened,closed=closed),ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':main()
