"""Native depth, anchored zoom and voxel picking at close editing distances."""
import json
import time
import numpy as np
from types import SimpleNamespace
from PIL import Image
import verify_ui as ui
import capture_screen as capture
from verify_selection_scope import diagnostic, wait_preview, click_point
from verify_interaction import pointer, tap
from verify_viewport_distance import centre_pixels
from verify_large_editor import snapshot
from projection.camera import OrbitCamera, raycast


class Solid:
    def __contains__(self, unused):
        return True


def main():
    capture.user32.SetProcessDPIAware()
    ui.click('工作台'); ui.click('完整'); ui.click('选取')
    diagnostic({'fixture': 'solid', 'camera': [35, 25, 1.42], 'pan': [0, 0]})
    wait_preview()
    builds = diagnostic()['previewBuilds']
    images, report = [], []
    for yaw, pitch, zoom in ((35,25,8.72), (35,25,19.2763), (35,25,100),
                             (35,25,1000), (125,40,25), (225,-25,25)):
        diagnostic({'camera': [yaw,pitch,zoom], 'pan': [0,0]})
        time.sleep(1.1)
        im, coverage = centre_pixels()
        rgb = np.asarray(im).astype('int16')
        # Side-face mortar is neutral gray; the empty viewport is blue-white.
        # A previous ray-pick leaves a saturated blue selection wire in this
        # crop. Exclude that known overlay, not the pale empty background.
        wire = (rgb[:,:,2]-rgb[:,:,0] > 30) & (rgb[:,:,2]-rgb[:,:,1] > 20)
        coverage = float((rgb[:,:,0] >= rgb[:,:,2])[~wire].mean())
        im.thumbnail((320,200)); images.append(im)
        ui.check('solid surface stays visible at %s' % ((yaw,pitch,zoom),), coverage > .98)
        state = diagnostic(); box = pointer()['layout']
        camera = OrbitCamera(*state['pose']); camera.pan = tuple(state['pan'])
        unit = min(box['width'],box['height']) * .72 * state['pose'][2] / 100.
        ray = camera.ray(box['width']/2.,box['height']/2.,state['sceneSize'],box['width'],box['height'],unit)
        expected = raycast(SimpleNamespace(size=state['size'], blocks=Solid(), contains=lambda p: all(0<=p[i]<state['size'][i] for i in range(3))), *ray)[0]
        tap(box['width']/2.,box['height']/2.)
        ui.check('visible voxel is picked exactly at %s' % ((yaw,pitch,zoom),), diagnostic()['focused']==list(expected))
        report.append({'pose':[yaw,pitch,zoom], 'surfaceCoverage':coverage, 'picked':expected})
    ui.check('zoom and rotation do not rebuild geometry',diagnostic()['previewBuilds']==builds)
    sheet=Image.new('RGB',(960,400),'white')
    for i,im in enumerate(images):sheet.paste(im,((i%3)*320,(i//3)*200))
    sheet.save(ui.OUT/'close_editing_surfaces.png')
    diagnostic({'camera':[35,25,1.42], 'pan':[0,0]});time.sleep(1)
    click_point((40.5,72.5,64.))
    ui.check('overview picks far wall voxel',diagnostic()['focused']==[40,72,63])
    ui.click('定位选中');time.sleep(.9)
    state=diagnostic();box=pointer()['layout']
    camera=OrbitCamera(*state['pose']);camera.pan=tuple(state['pan'])
    unit=min(box['width'],box['height'])*.72*state['pose'][2]/100.
    screen=camera.project((40.5,72.5,63.5),state['sceneSize'],box['width'],box['height'],unit)
    ui.check('locate centers selected voxel without cropping the document',
             abs(screen[0]-box['width']/2.)<.02 and abs(screen[1]-box['height']/2.)<.02 and state['sceneSize']==[64,100,64])
    ui.check('locate gives 20 design pixels per block',abs(unit / (box['width']/ui.nodes('Scene')[0]['props']['width']) - 20.)<.01)
    before=state['blocks'];ui.click('擦除');ui.click('单格');tap(box['width']/2.,box['height']/2.);wait_preview()
    ui.check('located voxel can be erased',diagnostic()['blocks']==before-1)
    ui.click('历史');ui.click('撤销');wait_preview();ui.click('参数');ui.click('选取')
    ui.check('close edit undo restores the building',diagnostic()['blocks']==before)
    snapshot('close_editing_located')
    # Real native wheel, away from the center, must keep its world ray fixed.
    box=pointer()['layout'];root=ui.nodes('SafeArea')[0]['children'][0]['layout']
    window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
    assert capture._activate_window(window['hwnd'])
    left,top,width,height=capture._window_rect(window['hwnd']);scale=width/root['width']
    x,y=box['width']*.62,box['height']*.42
    capture.user32.SetCursorPos(int(left+(box['x']+x)*scale),int(top+(box['y']+y)*scale));time.sleep(.2)
    tap(x,y);before=diagnostic()
    for unused in range(10):
        capture.user32.mouse_event(0x0800,0,0,120,0);time.sleep(.06)
    time.sleep(.8);tap(x,y);after=diagnostic()
    ui.check('native wheel zoom keeps the same voxel under the cursor',after['focused']==before['focused'] and after['pose'][2]>before['pose'][2]*2)
    ui.check('wheel zoom does not rebuild native geometry',after['previewBuilds']==before['previewBuilds'])
    ui.click('复位');time.sleep(.8)
    ui.check('reset clears anchored pan and zoom',diagnostic()['pan']==[0.,0.] and abs(diagnostic()['pose'][2]-1)<.001)
    (ui.OUT/'close_editing_checks.json').write_text(json.dumps({'checks':ui.checks,'surfaces':report},ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':main()
