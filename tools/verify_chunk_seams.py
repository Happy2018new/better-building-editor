"""Detect false internal walls across the roof of an exact solid draft."""
import json
import time
import cv2
import numpy as np
from PIL import Image
import verify_ui as ui
from verify_selection_scope import diagnostic, wait_preview
from verify_interaction import pointer
from verify_large_editor import snapshot
from projection.camera import OrbitCamera


def coverage(path, state, box, root):
    image = np.asarray(Image.open(path).convert('RGB')).astype('int16')
    scale = image.shape[1]/root['width']
    camera = OrbitCamera(*state['pose']); camera.pan = tuple(state['pan'])
    unit = min(box['width'],box['height'])*.72*state['pose'][2]/max(state['sceneSize'])
    corners = [(2,128,2),(62,128,2),(62,128,62),(2,128,62)]
    projected = [(np.array(camera.project(p,state['sceneSize'],box['width'],box['height'],unit))+
                  (box['x'],box['y']))*scale for p in corners]
    mask = np.zeros(image.shape[:2],dtype='uint8')
    cv2.fillConvexPoly(mask,np.array(projected,dtype='int32'),1)
    # Exclude the fixed navigation strip, viewport clipping and blue cursor.
    mask[:int((box['y']+12)*scale),:] = 0
    mask[int((box['y']+box['height']-40)*scale):,:] = 0
    wire = (image[:,:,2]-image[:,:,0]>30) & (image[:,:,2]-image[:,:,1]>20)
    usable = (mask>0) & ~wire
    top = (image.mean(2)>210) & (image[:,:,0]>=image[:,:,2])
    return float(top[usable].mean())


def main():
    ui.click('工作台'); ui.click('浏览')
    diagnostic({'fixture':'solid'}); wait_preview()
    diagnostic({'camera':[35,25,4],'pan':[0,1.305]}); time.sleep(1)
    snapshot('chunk_roof_continuity')
    state=diagnostic(); box=pointer()['layout']; root=ui.nodes('SafeArea')[0]['children'][0]['layout']
    ratio=coverage(ui.OUT/'chunk_roof_continuity.png',state,box,root)
    ui.check('solid roof has no false internal chunk walls',ratio>.98)
    print('roof surface coverage',ratio,flush=True)
    (ui.OUT/'chunk_seam_checks.json').write_text(json.dumps({'coverage':ratio,'checks':ui.checks},indent=2),encoding='utf8')


if __name__=='__main__': main()
