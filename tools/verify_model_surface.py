"""Pixel checks for fractional-angle alignment and native surface restoration."""
import itertools
import json
import subprocess
import sys
import time
import cv2
import mss
import numpy as np
from PIL import Image
import verify_ui as ui
import capture_screen as capture
from verify_selection_scope import diagnostic, wait_preview
from verify_interaction import pointer
from projection.camera import OrbitCamera


def pixels(name):
    state = diagnostic()
    box = pointer()['layout']
    root = ui.nodes('SafeArea')[0]['children'][0]['layout']
    window = capture._find_game_window(capture._list_windows(), process_name='Minecraft.Windows.exe')
    assert capture._activate_window(window['hwnd'])
    time.sleep(.3)
    left, top, width, height = capture._window_rect(window['hwnd'])
    scale = width / root['width']
    with mss.MSS() as screen:
        raw = screen.grab(dict(left=left, top=top, width=width, height=height))
    frame = Image.frombytes('RGB', raw.size, raw.bgra, 'raw', 'BGRX')
    camera = OrbitCamera(*state['pose'])
    camera.pan = tuple(state['pan'])
    unit = min(box['width'], box['height']) * .72 * state['pose'][2] / max(state['sceneSize'])
    corners = np.array([camera.project(p, state['sceneSize'], box['width'], box['height'], unit)
                        for p in itertools.product((2, 6), (1, 4), (3, 9))])
    corners += (box['x'], box['y'])
    corners *= scale
    lo, hi = corners.min(0), corners.max(0)
    a, b = np.floor(lo-8).astype(int), np.ceil(hi+8).astype(int)
    crop = frame.crop((a[0], a[1], b[0], b[1]))
    rgb = np.array(crop).astype('int16')
    # Actual quartz pixels; saturated blue selection edges are excluded.
    mask = ((rgb.max(2)-rgb.min(2)<55) & (rgb[:,:,2]<235) & (rgb[:,:,0]>15)).astype('uint8')
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3,3),'uint8'))
    ys, xs = np.where(mask)
    ui.check(name + ': model is actually drawn', len(xs)>1000)
    observed = np.array([[xs.min(), ys.min()], [xs.max()+1, ys.max()+1]]) + a
    error = float(np.max(np.abs(observed-np.array([lo,hi]))))
    ui.check(name + ': model silhouette agrees with overlay within 3 screen pixels', error<=3.)
    print('pixel bound error', round(error,3), flush=True)
    return crop, {'name':name, 'errorPixels':error, 'modelPixels':len(xs)}


def main():
    capture.user32.SetProcessDPIAware()
    ui.click('工作台'); ui.click('浏览')
    diagnostic({'fixture':'offset_odd', 'selection':[[2,1,3],[5,3,8]],
                'camera':[35.9,25.9,3], 'pan':[.15,-.1]})
    wait_preview()
    if diagnostic()['grid']: ui.click('网格')
    images, report = [], []
    def sample(name):
        im, result = pixels(name)
        im.thumbnail((440,340)); images.append(im); report.append(result)
    sample('fractional camera')
    for page in ('建筑库','入门指南','投影'):
        ui.click(page); ui.click('工作台'); sample('return from '+page)
    ui.click('逐层'); ui.click('三维'); sample('return from layer view')
    for preset in ('20:9','4:3','16:10','16:9'):
        result = subprocess.run([sys.executable, str(ui.ROOT/'.agents/skills/pyreact-debugging/scripts/resize_window.py'),
                                 '--preset',preset],capture_output=True,text=True,encoding='utf8',check=True)
        resized=json.loads(result.stdout)
        assert resized['ok'] and resized['actualClient']==resized['requestedClient'],resized
        time.sleep(.6); sample('resize '+preset)
    sheet=Image.new('RGB',(440*3,340*3),'white')
    for i,im in enumerate(images):sheet.paste(im,((i%3)*440,(i//3)*340))
    sheet.save(ui.OUT/'model_surface_contact.png')
    (ui.OUT/'model_surface_checks.json').write_text(json.dumps({'checks':ui.checks,'pixels':report},ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__': main()
