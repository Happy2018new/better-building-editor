"""Live shared bounds, custom dimensions, navigation and clipping regression."""
import json
import time
import verify_ui as ui
import capture_screen as capture
from verify_selection_scope import diagnostic, wait_preview, click_point
from verify_interaction import pointer
from verify_large_editor import snapshot


def action(**props):
    item = next(n for n in ui.nodes('Action') if all(n['props'].get(k) == v for k,v in props.items()))
    ui.call('click', ui.nodes('Button', item)[0]['id'])
    time.sleep(.35)


def outline_edges():
    scene=ui.nodes('Scene',ui.call('dump_tree')['tree'])[0]
    return [n for n in ui.nodes('Image',scene) if 'rotatePivot' in n['props']][52:]


def main():
    capture.user32.SetProcessDPIAware()
    window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd'])
    ui.click('工作台')
    diagnostic({'fixture':'offset_odd','selection':[[2,1,3],[5,3,8]],'camera':[35,25,3]})
    wait_preview();time.sleep(.8)
    ui.click('浏览'); click_point((3.5,4,5.5))
    edges=outline_edges()
    ui.check('exactly twelve edges, with no extra clicked-cell box',len(edges)==12)
    ui.check('browsing locates a single cell in the shared selection',diagnostic()['selection']==1)
    snapshot('viewport_aligned_odd')
    ui.click('选取');click_point((3.5,4,5.5))
    ui.check('selection does not move the Y workplane',diagnostic()['layer']==0)
    diagnostic({'selection':[[2,1,3],[5,3,8]]})
    before=diagnostic()
    boundary=ui.nodes('Action',ui.nodes('SelectionBounds')[0])[0]
    ui.call('click',ui.nodes('Button',boundary)[0]['id']);time.sleep(.35)
    after=diagnostic()
    ui.check('boundary buttons include empty space without changing blocks',after['start']==[1,1,3] and after['blocks']==before['blocks'])
    ui.click('坐标设置')
    field=next(n for n in ui.nodes('Coordinates') if n['props'].get('label')=='选区起点  X, Y, Z')
    ui.check('coordinates immediately reflect boundary buttons',field['props']['value']==[1,1,3])
    diagnostic({'camera':[35,25,4]});time.sleep(.8)
    action(glyph='arrow_right',width=27,height=27)
    time.sleep(.6)
    ui.check('zoom exceeds the old 3x limit and view pans',diagnostic()['pose'][2]>3.9 and diagnostic()['pan'][0]==.12)
    ui.click('浏览');click_point((3.5,4,5.5))
    ui.check('picking remains aligned after pan and zoom',diagnostic()['focused'] is not None)
    action(glyph='home')
    diagnostic({'layer':2});ui.click('切面');wait_preview()
    ui.check('section preserves document and selection',diagnostic()['section'] and diagnostic()['blocks']==72)
    ui.click('俯视');time.sleep(.8);click_point((3.5,3,5.5))
    ui.check('section picking hits exposed interior layer',diagnostic()['focused'][1]==2)
    snapshot('viewport_section')
    ui.click('切面');wait_preview()
    diagnostic({'fixture':'demo','camera':[35,25,6]});wait_preview();time.sleep(.8)
    snapshot('viewport_high_zoom')
    box=pointer()['layout']
    edges=outline_edges()
    visible=[]
    for edge in edges:
        native=ui.call('native_control',edge['id'])['result']
        if native['visible']:
            visible.append(native)
            cx=sum(p[0] for p in native['rect'])/4-box['x']
            cy=sum(p[1] for p in native['rect'])/4-box['y']
            assert -.1<=cx<=box['width']+.1 and -.1<=cy<=box['height']+.1
    ui.check('high zoom clipped edges keep their centres inside the viewport',len(visible)>0)
    for raw,size in [('3，8，3',[3,8,3]),('３７×１３×６５',[37,13,65]),('256,384,256',[256,384,256])]:
        ui.click('建筑库')
        field=ui.nodes('Input',ui.nodes('Library')[0])[-1]
        ui.call('set_input',field['id'],raw);time.sleep(.25)
        ui.click('新建空白');ui.click('确认继续');time.sleep(.5)
        ui.check('new dimensions '+raw,diagnostic()['size']==size)
    ui.click('建筑库')
    field=ui.nodes('Input',ui.nodes('Library')[0])[-1]
    ui.call('set_input',field['id'],'3,,8');time.sleep(.25)
    button=next(n for n in ui.nodes('Action') if n['props'].get('label')=='新建空白')
    ui.check('invalid dimensions disable creation instead of reusing old size',not button['props']['enabled'])
    ui.call('set_input',field['id'],'3,8,3');time.sleep(.25)
    ui.click('新建空白');ui.click('确认继续');time.sleep(.5)
    ui.click('俯视');time.sleep(.8);ui.click('放置');click_point((1.5,0,1.5));time.sleep(.5)
    ui.check('new empty document accepts a first block',diagnostic()['blocks']==1)
    diagnostic({'fixture':'demo','camera':[35,25,1]});wait_preview();ui.click('浏览')
    (ui.OUT/'viewport_revision_checks.json').write_text(json.dumps(ui.checks,ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':main()
