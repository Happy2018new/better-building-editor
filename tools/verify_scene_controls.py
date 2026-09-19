"""Shared 3D display modes, variable cut height and native navigation buttons."""
import json
import time
import verify_ui as ui
import capture_screen as capture
from verify_interaction import pointer
from verify_selection_scope import diagnostic, wait_preview, click_point


def native_click(label):
    target = ui._resolve_label(ui.tree(), label)
    assert len(target) == 1, target
    box = target[0]['layout']
    root = ui.nodes('SafeArea')[0]['children'][0]['layout']
    win = capture._find_game_window(capture._list_windows(), process_name='Minecraft.Windows.exe')
    assert capture._activate_window(win['hwnd'])
    left, top, width, height = capture._window_rect(win['hwnd'])
    scale = width/root['width']
    capture.user32.SetCursorPos(int(left+(box['x']+box['width']/2)*scale), int(top+(box['y']+box['height']/2)*scale))
    time.sleep(.1)
    capture.user32.mouse_event(2,0,0,0,0);time.sleep(.1)
    capture.user32.mouse_event(4,0,0,0,0);time.sleep(.3)


def main():
    capture.user32.SetProcessDPIAware()
    ui.click('工作台');ui.click('浏览')
    diagnostic({'fixture':'offset_odd','camera':[0,90,2],'layer':0});wait_preview()
    ui.check('one 3D canvas replaces the old layer editor', len(ui.nodes('Scene'))==1 and not ui.nodes('LayerCanvas'))
    ui.click('单层');wait_preview()
    ui.check('empty Y=0 really hides the raised quartz', diagnostic()['model'] is None)
    field = ui.nodes('Input',ui.nodes('Viewport')[0])[0]
    ui.call('set_input', field['id'], '2');wait_preview()
    ui.check('changing Y updates single layer without changing the draft',
             diagnostic()['layer']==2 and diagnostic()['blocks']==72 and diagnostic()['model'])
    ui.click('切面');wait_preview();click_point((3.5,4.,4.5))
    ui.check('cut height uses the same Y and exposes the correct top voxel', diagnostic()['focused']==[3,2,4])
    ui.click('完整');wait_preview();click_point((3.5,4.,4.5))
    ui.check('full view restores upper voxels and preserves workplane height',
             diagnostic()['focused']==[3,3,4] and diagnostic()['layer']==2)
    box=pointer()['layout'];unit=min(box['width'],box['height'])*.72/23.
    diagnostic({'camera':[0,0,1], 'pan':[(11.5-4.)*unit/box['width'],(2.-7.5)*unit/box['height']]})
    time.sleep(.8);ui.click('放置')
    before=diagnostic()
    native_click('前移');wait_preview();after=diagnostic()
    ui.check('first forward click crosses empty front margin', after['depth']>=13)
    ui.check('navigation cannot place a block through its button', after['blocks']==before['blocks'])
    native_click('后移');wait_preview()
    ui.check('back returns to the preceding view depth', diagnostic()['depth']==0)
    ui.click('图层');before=diagnostic()
    brightness=next(n for n in ui.nodes('Range') if n['props']['label']=='场景亮度')
    slider=ui.nodes('Slider',brightness)[0]['id']
    ui.call('set_slider',slider,.5);time.sleep(.3)
    after=diagnostic()
    ui.check('brightness changes immediately without a mesh build',
             abs(after['brightness']-.6)<.001 and before['previewBuilds']==after['previewBuilds'])
    ui.call('set_slider',slider,1.);ui.click('参数')
    (ui.OUT/'scene_controls_checks.json').write_text(json.dumps(ui.checks,ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':main()
