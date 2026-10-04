"""Native pixel comparison of coincident grid, selection and spectrum edges.

Run with run_live_check.py. Uses an unsaved empty draft and restores the
previous draft/view. PNG captures avoid JPEG bleed around subpixel strokes.
"""
import json
import os
import subprocess
import sys
import time
import mss
import numpy as np
from PIL import Image
import verify_ui as ui
from verify_grid_depth import activate_game, game
from native_input_mode import open_workspace, set_touch, state as input_state
from verify_biome_tint import wait_preview
from verify_interaction import pointer
from projection.scene_lines import stroke_width
from projection.camera import OrbitCamera
from verify_global_cursor import hover
from verify_selection_scope import diagnostic
import capture_screen as capture


def main():
    capture.user32.SetProcessDPIAware()
    activate_game()
    open_workspace()
    window = capture._find_game_window(capture._list_windows(), pid=int(os.environ['MCDEV_GAME_PID']))
    original_size=capture._window_rect(window['hwnd'])[2:]
    resize=ui.ROOT/'.agents/skills/pyreact-debugging/scripts/resize_window.py'
    if '--small' in sys.argv:
        subprocess.run([sys.executable,str(resize),'--size','1280x960'],check=True,capture_output=True)
        time.sleep(.8)
    left, top, pixel_width, pixel_height = capture._window_rect(window['hwnd'])
    capture.user32.SetCursorPos(left+8, top+8)
    original_touch = input_state()['simulated']
    set_touch(False)
    game('''fields=('editor','name','page','tool','direct_mode','section','solo_layer',
                'focus_view','focused','camera_yaw','camera_pitch','zoom','camera_pan',
                'camera_pivot','camera_depth','camera_depth_pose','camera_pose','grid',
                'box_anchor','reduced_motion')
api._grid_strokes_saved=dict((key,getattr(s,key)) for key in fields)
from modern_projection.projection.model import Document
s._loaded(Document((8,8,8),{(0,0,0):('minecraft:quartz_block',0)}))
s.focus_view=False;s.focused=None;s.grid=True;s.box_anchor=None
s.reduced_motion=True;s.direct_mode='browse';s.layer(3);s.reset_camera(False)
s.emit()
_result=True''')
    results = []
    try:
        wait_preview()
        for yaw, pitch, zoom in ((35,25,1.2), (125,45,1.2), (215,65,1.7)):
            game('s.camera_view(%r,%r,%r)\ns.editor.select_box((1,3,1),(6,3,6))\ns.emit()\n_result=True' % (yaw,pitch,zoom))
            time.sleep(.7)
            native = ui.call('native_control', pointer()['id'])['result']
            root = ui.nodes('SafeArea')[0]['children'][0]['layout']
            gui = round(pixel_width/root['width'])
            camera = OrbitCamera(yaw,pitch,zoom)
            width,height = native['size']
            unit = min(width,height)*.72*zoom/8

            def project(point):
                x,y = camera.project(point,(8,8,8),width,height,unit)
                return np.array(((native['global'][0]+x)*gui,(native['global'][1]+y)*gui))

            def frame(label):
                activate_game()
                time.sleep(.2)
                with mss.MSS() as screen:
                    raw = screen.grab(dict(left=left,top=top,width=pixel_width,height=pixel_height))
                    image = Image.frombytes('RGB',raw.size,raw.bgra,'raw','BGRX')
                image.save(ui.OUT / ('grid_strokes_%s_%d.png' % (label,yaw)))
                return np.asarray(image).astype(int)

            # Clear the selection for grid-only pixels, then restore the exact
            # cuboid lower edges at Y=3, including internal grid boundaries.
            game('s.editor.selection=set();s.editor.selection_revision+=1\ns.emit()\n_result=True')
            grid = frame('grid')
            game('s.editor.select_box((1,3,1),(6,3,6))\ns.set("grid",False)\ns.emit()\n_result=True')
            blue = frame('blue')
            game('s.set("grid",True)\n_result=True')
            combined = frame('blue_grid')
            thickness = game('from modern_projection.projection.widgets import Theme\n_result=Theme.scale')
            thickness = stroke_width(thickness)*gui

            # Analyze every lower horizontal cuboid edge away from vertices
            # and crossing lines. A containing outline must cover the grid's
            # entire raster footprint at these coincident edges.
            yy,xx = np.mgrid[:pixel_height,:pixel_width]
            measurements = []
            for axis in (0,2):
                other = 2-axis
                for boundary in (1,7):
                    a,b = [1.,3.,1.],[1.,3.,1.]
                    a[axis]=b[axis]=boundary
                    a[other]=1.;b[other]=7.
                    start,end = project(a),project(b)
                    direction = end-start
                    length = np.linalg.norm(direction)
                    along = ((xx+.5-start[0])*direction[0]+(yy+.5-start[1])*direction[1])/length
                    across = ((xx+.5-start[0])*direction[1]-(yy+.5-start[1])*direction[0])/length
                    t = along/length
                    cell_fraction = np.mod(1+6*t,1)
                    mask = (t>.12)&(t<.88)&(cell_fraction>.35)&(cell_fraction<.65)&(np.abs(across)<thickness/2+4)
                    grid_mask = np.max(np.abs(grid-[155,172,204]),axis=2)<4
                    blue_mask = np.max(np.abs(blue-[71,122,244]),axis=2)<4
                    grid_count = int((grid_mask&mask).sum())
                    blue_count = int((blue_mask&mask).sum())
                    leak = np.max(np.abs(combined-blue),axis=2)[mask]
                    measurements.append(dict(axis=axis,boundary=boundary,grid_pixels=grid_count,
                                             outline_pixels=blue_count,leaked_pixels=int((leak>5).sum()),
                                             grid_offset=float(across[grid_mask&mask].mean()),
                                             outline_offset=float(across[blue_mask&mask].mean())))
                    if yaw==35:
                        midpoint=(start+end)/2
                        crop=Image.fromarray(combined.astype('uint8')).crop((int(midpoint[0])-30,int(midpoint[1])-30,
                                                                            int(midpoint[0])+30,int(midpoint[1])+30))
                        crop.resize((480,480),Image.Resampling.NEAREST).save(ui.OUT / ('grid_edge_%d_%d.png' % (axis,boundary)))
            print(json.dumps(dict(yaw=yaw,thickness=thickness,edges=measurements)),flush=True)
            if '--measure' in sys.argv:
                results.append(dict(yaw=yaw,pitch=pitch,zoom=zoom,thickness=thickness,edges=measurements))
                if '--first' in sys.argv:
                    break
                continue
            ui.check('yaw %d grid and blue strokes have equal raster width' % yaw,
                     all(m['grid_pixels']>0 and abs(m['grid_pixels']-m['outline_pixels'])<=max(3,m['outline_pixels']*.12)
                         for m in measurements))
            ui.check('yaw %d blue outline fully covers coincident grid edges' % yaw,
                     all(m['leaked_pixels']==0 for m in measurements))
            game('s.set("grid",False)\n_result=True')
            set_touch(True)
            spectrum = frame('spectrum')
            game('s.set("grid",True)\n_result=True')
            spectrum_grid = frame('spectrum_grid')
            spectrum_edges = []
            for axis in (0,2):
                for boundary in (1,7):
                    a,b=[1.,3.,1.],[1.,3.,1.]
                    a[axis]=b[axis]=boundary;a[2-axis]=1.;b[2-axis]=7.
                    start,end=project(a),project(b);direction=end-start
                    length=np.linalg.norm(direction)
                    t=((xx+.5-start[0])*direction[0]+(yy+.5-start[1])*direction[1])/length**2
                    across=((xx+.5-start[0])*direction[1]-(yy+.5-start[1])*direction[0])/length
                    fraction=np.mod(1+6*t,1)
                    mask=(t>.12)&(t<.88)&(fraction>.35)&(fraction<.65)&(np.abs(across)<thickness/2+4)
                    colorful=(spectrum.max(axis=2)-spectrum.min(axis=2)>60)&(spectrum.max(axis=2)>230)
                    count=int((colorful&mask).sum())
                    leak=int((np.max(np.abs(spectrum_grid-spectrum),axis=2)[mask]>5).sum())
                    spectrum_edges.append(dict(axis=axis,boundary=boundary,outline_pixels=count,leaked_pixels=leak))
            ui.check('yaw %d spectrum and grid have equal raster width' % yaw,
                     all(abs(a['grid_pixels']-b['outline_pixels'])<=max(3,a['grid_pixels']*.12)
                         for a,b in zip(measurements,spectrum_edges)))
            ui.check('yaw %d spectrum fully covers coincident grid edges' % yaw,
                     all(m['leaked_pixels']==0 for m in spectrum_edges))
            results.append(dict(yaw=yaw,pitch=pitch,zoom=zoom,thickness=thickness,
                                edges=measurements,spectrum_edges=spectrum_edges))
            set_touch(False)
        if '--measure' not in sys.argv:
            game('s.camera_view(35,25,1.2)\ns.editor.select_box((3,3,3),(3,3,3))\ns.emit()\n_result=True')
            time.sleep(.7)
            set_touch(True)
            spectrum_only=frame('single_spectrum')
            set_touch(False)
            diagnostic.identity=None
            hover((3.5,3,3.5))
            ui.check('native mouse hover coincides with the selected cell',
                     game('_result=s.cursor_cell')==[3,3,3])
            both=frame('single_both')
            colorful=(spectrum_only.max(axis=2)-spectrum_only.min(axis=2)>60)&(spectrum_only.max(axis=2)>230)
            blue_pixels=np.max(np.abs(both-[71,122,244]),axis=2)<4
            # Exclude the application toolbar and check the scene's real ink.
            native=ui.call('native_control',pointer()['id'])['result']
            yy,xx=np.mgrid[:pixel_height,:pixel_width]
            x,y=native['global'];w,h=native['size']
            camera=OrbitCamera(35,25,1.2)
            unit=min(w,h)*.72*1.2/8
            corners=[camera.project((a,b,c),(8,8,8),w,h,unit)
                     for a in (3,4) for b in (3,4) for c in (3,4)]
            low=np.min(corners,axis=0);high=np.max(corners,axis=0)
            mask=(xx>(x+low[0])*gui-8)&(xx<(x+high[0])*gui+8)&(yy>(y+low[1])*gui-8)&(yy<(y+high[1])*gui+8)
            ink=colorful&mask
            ui.check('coincident spectrum has priority over blue with no blue fringe',
                     int(ink.sum())>20 and not (blue_pixels&mask).any() and
                     np.max(np.abs(both-spectrum_only),axis=2)[ink].max()<=1)
            capture.user32.SetCursorPos(left+8,top+8)
        name='grid_strokes_small_checks.json' if '--small' in sys.argv else 'grid_strokes_checks.json'
        (ui.OUT / name).write_text(json.dumps(dict(checks=ui.checks,pixels=results),indent=2),encoding='utf8')
    finally:
        if '--small' in sys.argv:
            subprocess.run([sys.executable,str(resize),'--size','%dx%d'%original_size],check=True,capture_output=True)
            time.sleep(.5)
        set_touch(original_touch)
        game('''for key,value in api._grid_strokes_saved.items():setattr(s,key,value)
s.camera_revision+=1;s.refresh_preview();s.emit()
_result=True''')
        wait_preview()


if __name__ == '__main__':
    main()
