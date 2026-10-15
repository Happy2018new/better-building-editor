"""Pixel regression for offscreen native control culling and exact work grids."""
import json
import sys
import time
import numpy as np
from PIL import Image
import mss
import verify_ui as ui
import capture_screen as capture
from verify_interaction import pointer
from verify_selection_scope import diagnostic, wait_preview
from verify_large_editor import snapshot


def centre_pixels():
    box=pointer()['layout']; root=ui.nodes('SafeArea')[0]['children'][0]['layout']
    window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
    assert capture._activate_window(window['hwnd'])
    time.sleep(.12)
    left,top,width,height=capture._window_rect(window['hwnd']); scale=width/root['width']
    region=dict(left=int(left+(box['x']+box['width']*.35)*scale),
                top=int(top+(box['y']+box['height']*.35)*scale),
                width=int(box['width']*.3*scale),height=int(box['height']*.3*scale))
    with mss.MSS() as screen:
        raw=screen.grab(region)
    im=Image.frombytes('RGB',raw.size,raw.bgra,'raw','BGRX')
    rgb=np.array(im).astype('int16')
    # Quartz is warmer than the blue-white viewport, including its bright face.
    coverage=float(((rgb[:,:,0]-rgb[:,:,2])>3).mean())
    return im,coverage


def main():
    capture.user32.SetProcessDPIAware()
    ui.click('工作台');ui.click('完整');ui.click('浏览')
    diagnostic({'fixture':'solid','size':[24,16,24],'camera':[0,90,8],'pan':[0,0]});wait_preview()
    if diagnostic()['grid']:ui.click('网格')
    before=diagnostic(); images=[]; coverage=[]
    for i in range(15):
        if i:ui.click('下移')
        im,ratio=centre_pixels();images.append(im);coverage.append(ratio)
        ui.check('downward move %d keeps the magnified model visible'%i,ratio>.8)
    after=diagnostic()
    ui.check('panning does not submit geometry',after['previewBuilds']==before['previewBuilds'])
    ui.check('native renderer still intersects viewport after 14 moves',all(
        n['position'][1]<=0 and n['position'][1]+n['size'][1]>=pointer()['layout']['height']
        for n in [ui.call('native_control',d['id'])['result'] for d in ui.nodes('PaperDoll')]))
    sheet=Image.new('RGB',(images[0].width*5,images[0].height*3))
    for i,im in enumerate(images):sheet.paste(im,((i%5)*im.width,(i//5)*im.height))
    sheet.save(ui.OUT/'panned_model_contact.png')
    diagnostic({'camera':[35,25,1],'pan':[0,0]});time.sleep(.7)
    before=diagnostic()
    for unused in range(8):ui.click('前移')
    near=diagnostic()
    for unused in range(8):ui.click('后移')
    far=diagnostic()
    ui.check('approach enlarges and recede restores scale',near['pose'][2]>4 and abs(far['pose'][2]-1)<.002)
    ui.check('distance never filters or rebuilds any block',all(
        s['blocks']==before['blocks'] and s['previewBuilds']==before['previewBuilds'] and s['depthPlane'] is None
        for s in (near,far)))
    verify_grid()
    (ui.OUT/'viewport_distance_checks.json').write_text(json.dumps({'checks':ui.checks,'coverage':coverage},ensure_ascii=False,indent=2),encoding='utf8')


def verify_grid():
    ui.new_region((64,100,64));wait_preview()
    diagnostic({'camera':[0,90,1],'pan':[0,0]});time.sleep(.7)
    if not diagnostic()['grid']:ui.click('网格')
    raw=ui.call('dump_tree')['tree']; scene=ui.nodes('Scene',raw)[0]
    lines=[n for n in ui.nodes('Image',scene) if n['id'].startswith('grid')]
    native=[ui.call('native_control',n['id'])['result'] for n in lines]
    ui.check('64 by 64 grid has 130 visible boundary lines',len(native)==130 and all(n['visible'] for n in native))
    xs=sorted((n['rect'][0][0]+n['rect'][3][0])/2. for n in native[:65])
    gaps=np.diff(xs)
    ui.check('every grid column has equal one-block spacing',float(gaps.max()-gaps.min())<.001 and gaps.min()>0)
    ui.check('camera reset has a text label','复位' in ui.labels())
    snapshot('grid_64_exact')
    (ui.OUT/'exact_grid_checks.json').write_text(json.dumps(ui.checks,ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':
    capture.user32.SetProcessDPIAware()
    verify_grid() if '--grid' in sys.argv else main()
